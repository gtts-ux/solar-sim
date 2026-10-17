"""Numerical invariants and end-to-end command regression checks."""
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from catalog import AU_KM, BODIES, DWARF_PLANETS, MOONS, PLANETS, SUN, lookup, satellites
import engine
from engine import EPOCH, MAX_DATE, MIN_DATE, Simulation, moon_offset, osculating_ellipse, planet_position, position, solve_kepler
from solar_sim import completions, wrap_lines
from ephemeris import IDS, Ephemeris, fetch_vectors, interpolate, parse_vectors
from missions import SPACECRAFT, Spacecraft, orbiters
from day_lengths import day_info, solar_hours
from flight_replay import FLIGHTS, Playback, find_flight, parse_duration, parse_request


class PhysicsTests(unittest.TestCase):
    def test_current_state_path_preserves_ellipse_and_orbital_plane(self):
        mu = 398600.4
        speed = math.sqrt(mu*1.2/7000)
        path = osculating_ellipse((7000,0,0),(0,speed*.5,speed*math.sqrt(.75)),mu)
        self.assertIsNotNone(path)
        self.assertLess(math.dist(path(0),(7000,0,0)),1e-7)
        self.assertLess(math.dist(path(math.pi),(-10500,0,0)),1e-7)
        x,y,z = path(math.pi/2)
        self.assertAlmostEqual(z/y,math.sqrt(3))
        self.assertAlmostEqual(x,-1750)

    def test_kepler_residual_including_high_eccentricity(self):
        for e in (0, .0167, .206, .7507, .95):
            for mean in (-100., -math.pi, -.01, 0., 2., 125.):
                with self.subTest(e=e, mean=mean):
                    anomaly = solve_kepler(mean,e)
                    expected = (mean+math.pi) % math.tau-math.pi
                    self.assertAlmostEqual(anomaly-e*math.sin(anomaly),expected,places=10)

    def test_physical_quantities_have_expected_earth_values(self):
        earth = lookup("earth")
        self.assertAlmostEqual(earth.gravity,9.82,delta=.02)
        self.assertAlmostEqual(earth.density,5514,delta=5)
        self.assertAlmostEqual(earth.escape,11.19,delta=.02)
        self.assertLess(lookup("saturn").density,1000)
        self.assertGreater(lookup("ganymede").radius,lookup("mercury").radius)

    def test_catalogue_complete_for_requested_systems(self):
        self.assertEqual(len(PLANETS),8)
        self.assertEqual(len([m for m in MOONS if lookup(m.parent) in PLANETS]),25)
        self.assertEqual(len(DWARF_PLANETS),5)
        for body in BODIES.values():
            self.assertGreater(body.mass,0)
            self.assertGreater(body.radius,0)
            if body is not SUN:
                self.assertIsNotNone(lookup(body.parent))
                self.assertGreater(body.period,0)
        for giant in ("jupiter","saturn","uranus","neptune"):
            self.assertGreaterEqual(len(satellites(giant)),3)

    def test_planet_positions_and_earth_velocity(self):
        for body in PLANETS:
            for date in (MIN_DATE,EPOCH,MAX_DATE-timedelta(days=1)):
                xyz = planet_position(body,date)
                self.assertTrue(all(math.isfinite(v) for v in xyz))
                radius = math.sqrt(sum(v*v for v in xyz))
                self.assertGreater(radius,body.orbit*.75)
                self.assertLess(radius,body.orbit*1.25)
        # Independent approximate Earth state at J2000, ecliptic coordinates.
        x,y,z = planet_position(lookup("earth"),EPOCH)
        self.assertAlmostEqual(x/AU_KM,-.1772,delta=.0002)
        self.assertAlmostEqual(y/AU_KM,.9672,delta=.0002)
        before = planet_position(lookup("earth"),EPOCH-timedelta(seconds=30))
        after = planet_position(lookup("earth"),EPOCH+timedelta(seconds=30))
        self.assertAlmostEqual(math.dist(before,after)/60,30.3,delta=.2)
        self.assertEqual(position(SUN,EPOCH),(0.,0.,0.))

    def test_moon_orbit_period_and_parent_translation(self):
        for body in MOONS:
            local = moon_offset(body,EPOCH)
            after_period = moon_offset(body,EPOCH+timedelta(days=body.period))
            self.assertLess(math.dist(local,after_period),.01)
            absolute = position(body,EPOCH)
            parent = position(lookup(body.parent),EPOCH)
            self.assertLess(math.dist(tuple(a-p for a,p in zip(absolute,parent)),local),1e-5)

    def test_retrograde_motion(self):
        for name,sign in (("triton",-1),("phoebe",-1),("io",1)):
            body = lookup(name)
            a = moon_offset(body,EPOCH)
            b = moon_offset(body,EPOCH+timedelta(seconds=10))
            self.assertGreater(sign*(a[0]*b[1]-a[1]*b[0]),0)


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation()
        self.sim.paused = True
        self.sim.set_date(EPOCH)

    def test_all_body_profiles_and_quoted_aliases(self):
        for body in BODIES.values():
            is_dwarf = body in DWARF_PLANETS or lookup(body.parent or '') in DWARF_PLANETS
            self.sim.command('/dwarf' if is_dwarf else '/dwarf exit')
            result = self.sim.command('/'+body.name)
            self.assertIn(body.name.upper(),result)
            if isinstance(body,Spacecraft):
                self.assertIn("MISSION PROFILE",result)
                self.assertIn("Approximate mass",result)
            else:
                self.assertIn("Mean diameter",result)
                self.assertIn("Mass",result)
        self.sim.command('/dwarf exit')
        self.assertIn("EARTH",self.sim.command('/"Earth"'))
        self.assertIn("MOON",self.sim.command('/"the moon"'))
        self.assertIn("TITAN",self.sim.command('/moon titan'))

    def test_planets_moons_search_and_comparison(self):
        self.assertIn('/neptune',self.sim.command('/planet'))
        self.assertIn("115 known moons; 5 included",self.sim.command('/moons jupiter'))
        self.assertIn("No moons",self.sim.command('/moons venus'))
        self.assertIn('/europa',self.sim.command('/search ocean'))
        self.assertIn("COMPARE",self.sim.command('/compare earth titan'))
        self.assertIn("70",self.sim.command('/weight 70 earth'))
        self.assertIn("no solid surface",self.sim.command('/weight 70 jupiter'))
        self.assertIn("0.00 km",self.sim.command('/distance earth earth'))

    def test_orbit_navigation_realtime_and_quoted_comparison(self):
        result = self.sim.command('/orbit inner')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertIn('NUMBERED ORBITS',result)
        self.assertIn('[1] Mercury',result)
        self.assertIn('[4] Mars',result)
        self.sim.command('/back')
        self.assertEqual(self.sim.screen,'dashboard')
        self.sim.command('/orbit jupiter')
        result = self.sim.command('/compare "Earth" "the moon"')
        self.assertEqual(self.sim.screen,'dashboard')
        for word in ('Center-to-center distance','light travel time','Composition','Atmosphere','Earth','Moon'):
            self.assertIn(word,result)
        self.sim.command('/realtime')
        self.assertEqual(self.sim.clock_mode,'realtime')
        self.assertFalse(self.sim.paused)
        self.assertEqual(self.sim.speed,1/86400)
        self.sim.command('/speed 3')
        self.assertEqual(self.sim.clock_mode,'simulation')
        self.sim.command('/now')
        self.assertEqual(self.sim.clock_mode,'realtime')
        self.sim.command('/date 2020-01-01')
        self.assertEqual(self.sim.clock_mode,'simulation')

    def test_comparison_uses_same_vectors_as_map(self):
        with patch.object(self.sim.ephemeris,'position',side_effect=lambda body,date:
                          {'Earth':(0,0,0),'Moon':(300000,400000,0)}.get(body.name)):
            result = self.sim.command('/compare earth moon')
            self.assertIn('500,000.00 km',result)
            self.assertIn('JPL Horizons',result)
            self.assertEqual(math.dist(self.sim.position(lookup('earth')),self.sim.position(lookup('moon'))),500000)

    def test_artificial_satellites_and_markers(self):
        self.sim.command('/date 2026-10-16')
        self.sim.command('/orbit')
        self.sim.command('/iss')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.map_system(),(lookup('earth'),[lookup('iss')]))
        distance = math.dist(self.sim.position(lookup('iss')),self.sim.position(lookup('earth')))
        self.assertGreater(distance,lookup('earth').radius+399)
        self.assertLess(distance,lookup('earth').radius+421)
        for parent in ('earth','mars','jupiter','venus','moon'):
            self.sim.command('/satellites '+parent)
            self.assertEqual(self.sim.screen,'orbit')
            self.assertEqual(self.sim.map_system()[0],lookup(parent))
            self.assertTrue(all(isinstance(b,Spacecraft) for b in self.sim.map_system()[1]))
        cells=self.sim.map_cells(90,25)
        self.assertFalse(any(char in '█▓▒░' for row in cells for char,_,_ in row))
        self.sim.command('/moons mars')
        self.assertEqual(self.sim.map_system()[1],satellites('mars'))
        self.sim.command('/orbit mars')
        names={b.name for b in self.sim.map_system()[1]}
        self.assertTrue({'Phobos','Deimos','MRO','MAVEN','Hope'}.issubset(names))
        self.assertIn('not live tracking',self.sim.ephemeris.source(lookup('iss'),self.sim.date))

    def test_upcoming_mercury_mission_is_only_drawn_in_preview(self):
        self.sim.command('/date 2026-10-16')
        self.sim.command('/orbit')
        result=self.sim.command('/satellites mercury')
        self.assertEqual(self.sim.map_system()[1],[])
        self.assertIn('2026-11-21',result)
        self.assertIn('no confirmed current orbiters',self.sim.orbit_notice)
        self.sim.command('/satellites mercury preview')
        self.assertEqual({s.name for s in self.sim.map_system()[1]},{'MPO','Mio'})
        self.assertIn('PLANNED PREVIEW',self.sim.orbit_notice)
        result=self.sim.command('/mpo')
        self.assertEqual(self.sim.screen,'dashboard')
        self.assertFalse(self.sim.preview_missions)
        self.assertIn('not confirmed',result)
        self.assertNotIn('ILLUSTRATIVE POSITION /',result)
        self.assertIn('no present distance',self.sim.command('/distance mercury mpo'))
        self.sim.command('/orbit')
        self.sim.command('/satellites saturn')
        self.assertEqual(self.sim.map_system()[1],[])
        self.assertEqual(orbiters('mercury',self.sim.date),[])

    def test_spacecraft_profiles_comparisons_and_dwarf_separation(self):
        self.sim.command('/date 2026-10-16')
        result=self.sim.command('/compare earth iss')
        self.assertIn('n/a',result)
        self.assertIn('Illustrative spacecraft',result)
        self.assertIn('no model surface gravity',self.sim.command('/weight 70 iss'))
        self.assertIn('Inactive',self.sim.command('/maven'))
        self.assertIn('2025-09-18',self.sim.command('/akatsuki'))
        self.assertEqual(completions('/is',self.sim),['/iss'])
        self.assertEqual(completions('/satellites mercury pr',self.sim),['/satellites mercury preview'])
        self.sim.command('/dwarf')
        self.assertIn('remains in Ceres orbit',self.sim.command('/dawn'))
        self.sim.command('/orbit')
        self.sim.command('/satellites ceres')
        self.assertEqual(self.sim.map_system()[1],[lookup('dawn')])
        self.assertNotIn(lookup('iss'),self.sim.visible_bodies)

    def test_body_commands_focus_own_orbit_only_in_orbit_mode(self):
        self.sim.command('/orbit')
        for command,name,parent in (('/earth','Earth','Sun'),
                                    ('/mercury','Mercury','Sun'),
                                    ('/europa','Europa','Jupiter'),
                                    ('/moon titan','Titan','Saturn'),
                                    ('/planet mars','Mars','Sun'),
                                    ('/"the moon"','Moon','Earth')):
            with self.subTest(command=command):
                result = self.sim.command(command)
                self.assertEqual(self.sim.screen,'orbit')
                self.assertEqual(self.sim.selected.name,name)
                center,bodies = self.sim.map_system()
                self.assertEqual(center.name,parent)
                self.assertEqual([b.name for b in bodies],[name])
                self.assertIn('ORBIT MAP',result)
                self.assertIn(name,result)
        self.sim.command('/orbit jupiter')
        self.assertIsNone(self.sim.orbit_focus)
        self.assertEqual(len(self.sim.map_system()[1]),5)
        self.sim.command('/sun')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(len(self.sim.map_system()[1]),8)
        self.sim.command('/back')
        self.assertIn('PHYSICAL PROFILE',self.sim.command('/europa'))
        self.assertEqual(self.sim.screen,'dashboard')

    def test_moon_commands_show_whole_system_in_orbit_mode(self):
        self.sim.command('/orbit')
        for planet in PLANETS:
            with self.subTest(planet=planet.name):
                result = self.sim.command('/moons '+planet.name)
                self.assertEqual(self.sim.screen,'orbit')
                center,children = self.sim.map_system()
                self.assertEqual(center,planet)
                self.assertEqual(children,satellites(planet.name))
                self.assertIsNone(self.sim.orbit_focus)
                if planet.known_moons == 0:
                    self.assertIn('has no moons',result)
                    self.sim.command('/pause')
                    self.assertIn('has no moons',self.sim.orbit_notice)
        result = self.sim.command('/mooons jupiter')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(len(self.sim.map_system()[1]),5)
        self.assertIn('5 included moon orbits',result)
        self.sim.command('/europa')
        self.assertEqual(len(self.sim.map_system()[1]),1)
        self.sim.command('/moons jupiter')
        self.assertEqual(len(self.sim.map_system()[1]),5)

    def test_dwarf_mode_is_separate_and_exit_restores_normal_planets(self):
        self.assertNotIn('Pluto',self.sim.command('/planet'))
        self.assertEqual(completions('/plu',self.sim),[])
        self.assertIn('Use /dwarf',self.sim.command('/pluto'))
        self.sim.command('/orbit')
        result = self.sim.command('/dwarf')
        self.assertTrue(self.sim.dwarf_mode)
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.map_system()[1],DWARF_PLANETS)
        self.assertIn('Pluto',result)
        self.assertNotIn('Jupiter',result)
        self.assertEqual(completions('/plu',self.sim),['/pluto'])
        self.assertEqual(completions('/ear',self.sim),[])
        self.assertEqual(completions('/dwarf ex',self.sim),['/dwarf exit'])
        self.sim.command('/pluto')
        self.assertEqual(self.sim.map_system()[1],[lookup('pluto')])
        self.sim.command('/moons pluto')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual([b.name for b in self.sim.map_system()[1]],['Charon'])
        self.assertIn('2 known moons',self.sim.command('/moons haumea'))
        self.assertNotIn('has no moons',self.sim.orbit_notice)
        self.assertIn('Ceres has no moons',self.sim.command('/moons ceres'))
        for dwarf in DWARF_PLANETS:
            self.sim.command('/'+dwarf.name)
            self.assertTrue(all(math.isfinite(v) for v in self.sim.position(dwarf)))
            self.assertEqual(len(self.sim.map_cells(70,15)),15)
        self.sim.command('/dwarf exit')
        self.assertFalse(self.sim.dwarf_mode)
        self.assertEqual(self.sim.map_system()[1],PLANETS)
        self.assertIsNone(self.sim.orbit_focus)
        self.assertIn('/earth',self.sim.command('/planet'))
        self.assertNotIn('Pluto',self.sim.command('/planet'))
        result = self.sim.command('/dwarf')
        self.assertIn('DWARF PLANETS',result)
        self.assertEqual(self.sim.screen,'dashboard')
        self.assertIn('PHYSICAL PROFILE',self.sim.command('/eris'))

    def test_clock_controls_and_validation(self):
        self.sim.command('/date 2030-01-01')
        self.assertEqual(self.sim.date.year,2030)
        start = self.sim.date
        self.sim.command('/step -30')
        self.assertEqual(self.sim.date,start-timedelta(days=30))
        self.sim.command('/speed -2.5')
        self.assertEqual(self.sim.speed,-2.5)
        for cmd in ('/speed nan','/speed inf','/step -999999999','/date 2050-01-01','/date 1799-01-01','/date rubbish'):
            with self.subTest(command=cmd):
                self.assertIn('Could not run command',self.sim.command(cmd))
        self.sim.command('/resume')
        self.assertFalse(self.sim.paused)
        self.sim.command('/pause')
        self.assertTrue(self.sim.paused)
        self.sim.set_date(MAX_DATE,clamp=True)
        self.assertLess(self.sim.date,MAX_DATE)
        self.assertTrue(self.sim.paused)

    def test_time_sets_exact_utc_instant_and_preserves_orbit_view(self):
        self.sim.command('/orbit jupiter')
        self.sim.command('/speed 10')
        self.sim.paused=False
        result=self.sim.command('/time 1969/12/03 13:45')
        expected=datetime(1969,12,3,13,45,tzinfo=timezone.utc)
        self.assertIn('1969-12-03 13:45:00 UTC',result)
        self.assertEqual(self.sim.date,expected)
        self.assertEqual(self.sim.clock_mode,'simulation')
        self.assertTrue(self.sim.paused)
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.view,'jupiter')
        self.assertEqual(self.sim.selected,lookup('jupiter'))
        self.assertEqual(self.sim.speed,10)
        self.assertEqual(self.sim.position(lookup('earth')),position(lookup('earth'),expected))
        with patch('engine.time.monotonic',return_value=self.sim.last_tick+60):
            self.sim.tick()
            self.assertIn('1969-12-03 13:45:00 UTC',self.sim.command('/time'))
        self.assertEqual(self.sim.date,expected)
        self.sim.command('/resume')
        with patch('engine.time.monotonic',return_value=self.sim.last_tick+1):
            self.sim.tick()
        self.assertEqual(self.sim.date,expected+timedelta(days=10))

    def test_time_defaults_to_midnight_and_accepts_leap_days_and_limits(self):
        self.sim.command('/now')
        for text,expected in (
                ('1969/12/03',datetime(1969,12,3,tzinfo=timezone.utc)),
                ('2000/02/29 23:59',datetime(2000,2,29,23,59,tzinfo=timezone.utc)),
                ('1800/01/01',MIN_DATE),
                ('2049/12/31 23:59',MAX_DATE-timedelta(minutes=1))):
            with self.subTest(text=text):
                self.assertNotIn('Could not run command',self.sim.command('/time '+text))
                self.assertEqual(self.sim.date,expected)
                self.assertTrue(self.sim.paused)

    def test_invalid_time_does_not_replace_clock(self):
        for text in ('1969/02/29','1969/04/31','1969/13/03','1969/00/03',
                     '1969/12/03 24:00','1969/12/03 13:60','1969/12/03 13:45:30',
                     '1799/12/31','2050/01/01','1969/12/03 13:45 extra',
                     'tomorrow','13:45','1969/12/03 invalid'):
            with self.subTest(text=text):
                self.assertIn('Could not run command',self.sim.command('/time '+text))
                self.assertEqual(self.sim.date,EPOCH)
                self.assertEqual(self.sim.clock_mode,'simulation')

    def test_tick_advances_exactly_at_configured_rate(self):
        self.sim.paused = False
        self.sim.speed = 2
        self.sim.last_tick = 100
        with patch('engine.time.monotonic',return_value=101):
            self.sim.tick()
        self.assertEqual(self.sim.date,EPOCH+timedelta(days=2))
        self.sim.paused = True
        with patch('engine.time.monotonic',return_value=102):
            self.sim.tick()
        self.assertEqual(self.sim.date,EPOCH+timedelta(days=2))

    def test_view_focus_and_map_dimensions(self):
        self.sim.command('/focus europa')
        self.assertEqual(self.sim.view,'jupiter')
        self.assertEqual(self.sim.selected.name,'Europa')
        for view in ('solar','inner','outer','earth','jupiter','saturn','uranus','neptune','mercury'):
            self.sim.command('/view '+view)
            for width,height in ((60,6),(80,15),(120,30)):
                cells = self.sim.map_cells(width,height)
                self.assertEqual(len(cells),height)
                self.assertTrue(all(len(row)==width for row in cells))
        self.assertIn('ORBIT MAP',self.sim.command('/map'))
        self.sim.command('/scale linear')
        self.assertEqual(self.sim.scale,'linear')
        self.sim.command('/labels off')
        self.assertFalse(self.sim.labels)
        self.sim.command('/trails off')
        self.assertFalse(self.sim.trails)

    def test_bad_commands_are_readable_and_do_not_execute(self):
        for raw in ('/jupitr','/nonsense','/"bad quote','/moon earth','/planet moon',
                    '/weight -1 earth','/weight nan earth','/scale wrong','/date',
                    '/compare earth missing','/moons titan','/export /tmp/x'):
            with self.subTest(command=raw):
                self.assertIn('Could not run command',self.sim.command(raw))

    def test_snapshot_writes_valid_json_and_all_bodies(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(engine,'ROOT',Path(folder)):
                result = self.sim.command('/export')
            self.assertIn('Snapshot saved',result)
            files = list((Path(folder)/'exports').glob('*.json'))
            self.assertEqual(len(files),1)
            data = json.loads(files[0].read_text())
            self.assertEqual(len(data['bodies']),len(BODIES))
            self.assertEqual(data['simulation_utc'],EPOCH.isoformat())
            self.assertTrue(next(b for b in data['bodies'] if b['name']=='Nereid')['mass_is_estimate'])

    def test_help_sources_info_and_quit(self):
        self.assertIn('/planet',self.sim.command('/help'))
        self.assertIn('jpl.nasa.gov',self.sim.command('/sources'))
        self.assertIn(f'{len(MOONS)} selected moons',self.sim.command('/info'))
        self.assertEqual(self.sim.command('/clear'),'')
        self.sim.command('/quit')
        self.assertFalse(self.sim.running)

    def test_completion_and_wrapping(self):
        self.assertEqual(completions('/jup'),['/jupiter'])
        self.assertIn('/view jupiter',completions('/view jup'))
        self.assertIn('/compare earth titan',completions('/compare earth ti'))
        self.assertEqual(completions('/labels of'),['/labels off'])
        self.assertEqual(completions('/orb'),['/orbit'])
        self.assertIn('/orbit inner',completions('/orbit in'))
        self.assertTrue(all(len(row)<=30 for row in wrap_lines('  A long sentence '*20,30)))

    def test_cli_runs_from_another_working_directory(self):
        script = Path(__file__).with_name('solar_sim.py')
        result = subprocess.run([sys.executable,str(script),'-c','/date 2030-01-01','-c','/earth'],
                                cwd=tempfile.gettempdir(),capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('2030-01-01',result.stdout)
        self.assertIn('EARTH / Terrestrial planet',result.stdout)


class EphemerisTests(unittest.TestCase):
    def payload(self):
        return {'signature':{'version':'1.3'},'result':
                'header\n$$SOE\n2451545.0,A.D. 2000-Jan-01 12:00,1,2,3,4,5,6,\n'
                '2451545.0104166665,A.D. 2000-Jan-01 12:15,3601,4502,5403,4,5,6,\n$$EOE\nfooter'}

    def test_parser_and_http_query_match_horizons_contract(self):
        rows = parse_vectors(self.payload())
        self.assertEqual(rows[0][1:],[1,2,3,4,5,6])
        self.assertEqual(len(rows),2)
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(self.payload()).encode()
        with patch('ephemeris.urlopen',return_value=response) as network:
            result = fetch_vectors(399,EPOCH,EPOCH+timedelta(minutes=15))
        query = parse_qs(urlparse(network.call_args.args[0].full_url).query)
        self.assertEqual(query['CENTER'],["'500@10'"])
        self.assertEqual(query['TIME_TYPE'],["'UT'"])
        self.assertEqual(query['VEC_TABLE'],["'2'"])
        self.assertEqual(query['COMMAND'],["'399'"])
        self.assertEqual(result,rows)

    def test_invalid_payloads_are_rejected(self):
        for payload in ({'signature':{'version':'9'}},
                        {'signature':{'version':'1.3'},'error':'No ephemeris'},
                        {'signature':{'version':'1.3'},'result':'nothing'}):
            with self.assertRaises(ValueError):
                parse_vectors(payload)

    def test_hermite_interpolation_exact_cubic_and_no_extrapolation(self):
        # x=t^3, y=2t, z=7; endpoint velocities are independent derivatives.
        rows = [[0,0,0,7,0,2,0],[10,1000,20,7,300,2,0]]
        self.assertEqual(interpolate(rows,5),(125,10,7))
        self.assertEqual(interpolate(rows,5,velocity=True),(75,2,0))
        self.assertEqual(interpolate(rows,0),(0,0,7))
        self.assertEqual(interpolate(rows,10),(1000,20,7))
        self.assertIsNone(interpolate(rows,-1))
        self.assertIsNone(interpolate(rows,11))

    def test_cache_sync_and_offline_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'cache.json'
            client = Ephemeris(cache_path=path)
            with patch('ephemeris.fetch_vectors',return_value=parse_vectors(self.payload())),patch.object(client.cancel,'wait',return_value=False):
                client._sync(EPOCH,force=True)
            self.assertEqual(len(client.records),len(IDS))
            self.assertEqual(client.position(lookup('earth'),EPOCH),(1,2,3))
            self.assertEqual(len(Ephemeris(cache_path=path).records),len(IDS))
            with patch('ephemeris.fetch_vectors',side_effect=OSError('connection unavailable')):
                client._sync(EPOCH,force=True)
            self.assertIn('some offline',client.message)
            self.assertEqual(len(client.errors),3)
            self.assertIn('connection unavailable',client.details())
            # Previously good data survives a network error, but expires normally.
            self.assertEqual(client.position(lookup('earth'),EPOCH),(1,2,3))
            self.assertIsNone(client.position(lookup('earth'),EPOCH+timedelta(days=2)))


class DayLengthTests(unittest.TestCase):
    def test_solar_day_matches_reference_values_and_differs_from_spin(self):
        for name,hours,tolerance in [('earth',24,.001),('mercury',4222.6,1),
                                     ('venus',2802,1),('moon',708.7,.1),('mars',24.66,.02)]:
            with self.subTest(name=name):
                self.assertAlmostEqual(solar_hours(lookup(name)),hours,delta=tolerance)
        self.assertIn('retrograde',day_info(lookup('venus')))
        self.assertIsNone(solar_hours(SUN))
        self.assertIsNone(solar_hours(lookup('hyperion')))
        self.assertIsNone(solar_hours(lookup('iss')))

    def test_profiles_and_day_command_explain_both_periods(self):
        sim=Simulation()
        self.assertIn('Length of solar day',sim.command('/earth'))
        self.assertIn('24.00 hours',sim.command('/day'))
        for name in ('earth','venus','moon','sun','hyperion','iss'):
            result=sim.command('/day '+name)
            self.assertIn(name.upper(),result)
            self.assertIn('solar day',result.lower())
        self.assertIn('Sidereal rotation',sim.command('/day mercury'))
        self.assertIn('Unknown body',sim.command('/day nonexistent'))


class FlightReplayTests(unittest.TestCase):
    def setUp(self):
        self.clock=patch('engine.time.monotonic',return_value=100.)
        self.time=self.clock.start()
        self.addCleanup(self.clock.stop)
        self.sim=Simulation()

    def test_duration_parsing_and_mission_aliases(self):
        for text,expected in [('1 minute',60),('30 seconds',30),('1m30s',90),
                              ('1 hour 2 minutes 3 seconds',3723),('1.5 min',90),('24h',86400)]:
            self.assertEqual(parse_duration(text),expected)
        for text in ('-30 seconds','0s','0.5 seconds','25 hours','nan seconds','inf s','1 day','1 minute garbage','30'):
            with self.subTest(text=text),self.assertRaises(ValueError):
                parse_duration(text)
        self.assertEqual(parse_request(['Apollo','11','1','minute']), (find_flight('apollo11'),60))
        self.assertEqual(parse_request(['Apollo 11','30','seconds'])[1],30)
        self.assertEqual(parse_request(['Artemis','2'])[0].name,'Artemis II')
        self.assertEqual(parse_request(['Demo-2'])[0].name,'SpaceX Demo-2')

    def test_catalogue_has_ten_distinct_flights_with_correct_routes(self):
        self.assertEqual(len(FLIGHTS),10)
        self.assertEqual(len({f.name for f in FLIGHTS}),10)
        for flight in FLIGHTS:
            self.assertEqual(flight.stages[0].visual,'launch')
            self.assertEqual(flight.stages[-1].visual,'splash')
            self.assertTrue(all(a.date<b.date for a,b in zip(flight.stages,flight.stages[1:])))
            self.assertTrue(flight.sources)
        for name in ('Apollo 11','Apollo 17'):
            self.assertTrue({'surface','ascent','lunar_orbit'} <= {s.visual for s in find_flight(name).stages})
        for name in ('Apollo 8','Apollo 13','Artemis I','Artemis II'):
            self.assertNotIn('surface',{s.visual for s in find_flight(name).stages})
        for name in ('Apollo 13','Artemis II'):
            self.assertNotIn('lunar_orbit',{s.visual for s in find_flight(name).stages})
            self.assertIn('flyby',{s.visual for s in find_flight(name).stages})
        self.assertEqual(find_flight('Apollo 11').start.isoformat(),'1969-07-16T13:32:00+00:00')
        self.assertEqual(find_flight('Artemis II').end.isoformat(),'2026-04-11T00:07:00+00:00')

    def test_playback_hits_every_milestone_and_finishes_at_requested_duration(self):
        for flight in FLIGHTS:
            replay=Playback(flight,30)
            self.assertEqual(replay.date,flight.start)
            self.assertEqual(replay.boundaries[-1],30)
            previous=flight.start
            for i,boundary in enumerate(replay.boundaries):
                replay.elapsed=boundary
                self.assertEqual(replay.index,i)
                self.assertEqual(replay.date,flight.stages[i].date)
                self.assertGreaterEqual(replay.date,previous)
                previous=replay.date
            for a,b in zip(replay.boundaries,replay.boundaries[1:]):
                self.assertGreater(b-a,.8)  # short events remain visible in a 30-second replay
            replay.elapsed=0
            replay.advance(29.999)
            self.assertFalse(replay.complete)
            replay.advance(1)
            self.assertTrue(replay.complete)
            self.assertEqual(replay.elapsed,30)
            self.assertEqual(replay.date,flight.end)

    def test_start_pause_resume_seek_restart_complete_and_stop(self):
        result=self.sim.command('/mission Apollo 11 1 minute')
        self.assertIn('PLAYING',result)
        self.assertEqual(self.sim.screen,'mission')
        self.assertEqual(self.sim.date,find_flight('Apollo 11').start)
        self.time.return_value=110
        self.sim.tick()
        self.assertEqual(self.sim.mission.elapsed,10)
        self.sim.command('/pause')
        self.time.return_value=120
        self.sim.tick()
        self.assertEqual(self.sim.mission.elapsed,10)
        self.sim.command('/resume')
        self.time.return_value=125
        self.sim.tick()
        self.assertEqual(self.sim.mission.elapsed,15)
        self.assertIn('PLAYING',self.sim.command('/time'))
        self.assertIsNotNone(self.sim.mission)
        self.sim.command('/mission seek 50')
        self.assertEqual(self.sim.mission.elapsed,30)
        self.sim.command('/mission restart')
        self.assertEqual(self.sim.mission.elapsed,0)
        self.time.return_value=185
        self.sim.tick()
        self.assertTrue(self.sim.mission.complete)
        self.assertTrue(self.sim.paused)
        self.assertEqual(self.sim.date,find_flight('Apollo 11').end)
        self.assertIn('Mission complete',self.sim.command('/resume'))
        self.time.return_value=500
        self.sim.tick()
        self.assertEqual(self.sim.date,find_flight('Apollo 11').end)
        self.sim.command('/mission stop')
        self.assertIsNone(self.sim.mission)
        self.assertTrue(self.sim.paused)
        self.assertEqual(self.sim.screen,'dashboard')
        self.assertEqual(self.sim.clock_mode,'simulation')

    def test_seek_to_landing_and_safe_navigation_out(self):
        self.sim.command('/mission "Apollo 11" 30 seconds')
        replay=self.sim.mission
        landing=next(i for i,s in enumerate(replay.flight.stages) if s.name=='Moon landing')
        percent=(replay.boundaries[landing]+.01)/replay.duration*100
        self.assertIn('Moon landing',self.sim.command(f'/mission seek {percent}'))
        self.assertEqual(self.sim.mission.stage.visual,'surface')
        date=self.sim.date
        self.sim.command('/day moon')
        self.assertIsNone(self.sim.mission)
        self.assertEqual(self.sim.date,date)
        self.assertTrue(self.sim.paused)
        self.sim.command('/now')
        self.assertEqual(self.sim.clock_mode,'realtime')

    def test_errors_preserve_loaded_flight_and_validate_seek(self):
        for command in ('/mission imaginary 1 minute','/mission Apollo 11 -30 seconds',
                        '/mission seek 50','/mission Apollo 11 25 hours'):
            self.assertIn('Could not run command',self.sim.command(command))
            self.assertIsNone(self.sim.mission)
        self.sim.command('/mission Apollo 13 1 minute')
        replay=self.sim.mission
        for command in ('/mission seek nan','/mission seek -1','/mission seek 101',
                        '/mission seek','/speed 1','/step 1','/mission wrong'):
            self.assertIn('Could not run command',self.sim.command(command))
            self.assertIs(self.sim.mission,replay)
            self.assertTrue(self.sim.paused)
        self.sim.command('/mission resume')
        self.assertEqual(self.sim.screen,'mission')
        self.assertFalse(self.sim.paused)

    def test_time_exits_mission_only_after_validating_requested_instant(self):
        self.sim.command('/mission Apollo 11 1 minute')
        replay=self.sim.mission
        for command in ('/time 1969/02/29','/time 2050/01/01','/time 1969/12/03 24:00'):
            self.assertIn('Could not run command',self.sim.command(command))
            self.assertIs(self.sim.mission,replay)
            self.assertEqual(self.sim.date,replay.date)
        self.sim.command('/mission resume')
        self.assertIn('PLAYING',self.sim.command('/time'))
        self.assertIs(self.sim.mission,replay)
        self.sim.overlay='live'
        result=self.sim.command('/time 1969/12/03 13:45')
        self.assertIn('1969-12-03 13:45:00 UTC',result)
        self.assertEqual(self.sim.date,datetime(1969,12,3,13,45,tzinfo=timezone.utc))
        self.assertIsNone(self.sim.mission)
        self.assertIsNone(self.sim.overlay)
        self.assertEqual(self.sim.screen,'dashboard')
        self.assertEqual(self.sim.clock_mode,'simulation')
        self.assertTrue(self.sim.paused)
        self.sim.command('/now')
        self.assertEqual(self.sim.clock_mode,'realtime')
        self.assertFalse(self.sim.paused)

    def test_scenes_render_every_stage_and_keep_missions_distinct(self):
        for flight in FLIGHTS:
            replay=Playback(flight,60)
            for width,height in ((60,6),(116,14)):
                for start,end in zip(replay.boundaries,replay.boundaries[1:]):
                    replay.elapsed=(start+end)/2
                    cells=replay.scene(width,height)
                    self.assertEqual(len(cells),height)
                    self.assertTrue(all(len(row)==width for row in cells))
                    text='\n'.join(''.join(c[0] for c in row) for row in cells)
                    self.assertIn('Earth',text)
                    self.assertTrue('>' in text or '!' in text)
                    self.assertEqual('Moon' in text,flight.lunar)
                    self.assertEqual('ISS' in text,any(s.visual=='docked' for s in flight.stages))

    def test_catalogue_chronology_completion_and_export(self):
        for flight in FLIGHTS:
            self.assertIn(flight.name,self.sim.command('/mission list'))
            info=self.sim.command('/mission info '+flight.name)
            self.assertIn(flight.summary,info)
            self.assertIn(flight.sources[0],info)
        self.assertIn('/mission Apollo 11',completions('/mission Apo'))
        self.assertIn('/mission "Artemis II"',completions('/mission "Artemis'))
        self.assertIn('/mission info SpaceX Demo-2',completions('/mission info SpaceX'))
        self.sim.command('/mission Demo-2 30 seconds')
        with tempfile.TemporaryDirectory() as folder,patch('engine.ROOT',Path(folder)):
            self.sim.command('/export')
            data=json.loads(next((Path(folder)/'exports').glob('*.json')).read_text())
        self.assertEqual(data['flight_replay']['name'],'SpaceX Demo-2')
        self.assertEqual(data['flight_replay']['duration_seconds'],30)
        self.assertEqual(data['simulation_utc'],self.sim.mission.flight.start.isoformat())
        self.assertEqual(len(data['bodies']),len(BODIES))


if __name__ == '__main__':
    unittest.main()
