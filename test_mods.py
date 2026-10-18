"""Optional system installation, physical labels, coordinate isolation and packaged CLI."""
from datetime import timedelta
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
import zipfile

from catalog import BODIES
from engine import Simulation
from mod_manager import LIMIT, MOD_URL, ModError, install, load, validate
from navigation import Navigation, body_item
from solar_sim import completions
from tools.build_release import build

ROOT = Path(__file__).resolve().parent
PACKAGE = (ROOT/'mod_catalogue/proxima-centauri.json').read_bytes()


class ModTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'app with spaces'
        (self.root/'mod_catalogue').mkdir(parents=True)
        (self.root/'mod_catalogue/proxima-centauri.json').write_bytes(PACKAGE)
        (self.root/'VERSION.txt').write_text((ROOT/'VERSION.txt').read_text())
        self.sim = Simulation(mods_path=self.root/'mods',settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')

    def activate(self, spelling='/proxima centauri'):
        install(self.root,'proxima centauri',offline=True)
        text = self.sim.command(spelling)
        self.assertNotIn('Could not run', text)
        return text

    def test_not_installed_has_terminal_instructions(self):
        self.assertIn('sol-sim -m"proxima centauri"', self.sim.command('/proxima centari'))
        self.assertFalse(self.sim.proxima_mode)

    def test_install_remote_and_offline_fallback(self):
        seen = []
        def fetch(url, limit):
            seen.append((url,limit))
            return PACKAGE
        self.assertIn('repository', install(self.root,'proxima centauri',fetch=fetch))
        self.assertEqual(seen, [(MOD_URL,LIMIT)])
        self.assertEqual(load(self.root/'mods')['version'], '1.0.0')
        with patch('mod_manager.os.replace', wraps=__import__('os').replace) as replace:
            result = install(self.root,'proxima centari',fetch=lambda *_: (_ for _ in ()).throw(URLError('offline')))
        self.assertIn('bundled package', result)
        replace.assert_called_once()
        self.assertEqual(list((self.root/'mods').glob('*.tmp')), [])

    def test_invalid_remote_does_not_replace_good_install(self):
        install(self.root,'proxima centauri',offline=True)
        target=self.root/'mods/proxima-centauri.json'
        before=target.read_bytes()
        for payload in (b'not json', b'{}', b'x'*(LIMIT+1)):
            with self.assertRaises(ModError):
                install(self.root,'proxima centauri',fetch=lambda *_,p=payload:p)
            self.assertEqual(target.read_bytes(),before)

    def test_schema_rejects_code_bad_frames_and_nonfinite_values(self):
        for key,value in (('mass',float('nan')),('radius',-1),('parent','Earth'),('period',0),('features','\x1b[0m'),('rotation',24),('color',99),('exec','anything')):
            data=json.loads(PACKAGE)
            data['bodies'][1][key]=value
            with self.assertRaises(ModError,msg=key):validate(json.dumps(data).encode())
        data=json.loads(PACKAGE);data['frame']='heliocentric'
        with self.assertRaises(ModError):validate(json.dumps(data).encode())

    def test_app_compatibility_and_name_validation(self):
        (self.root/'VERSION.txt').write_text('1.6.0')
        with self.assertRaisesRegex(ModError,'needs Solar Sim'):install(self.root,'proxima centauri',offline=True)
        with self.assertRaisesRegex(ModError,'Unknown mod'):install(self.root,'../../bad',offline=True)
        self.assertFalse((self.root/'mods/proxima-centauri.json').exists())

    def test_failed_replace_preserves_previous_package(self):
        install(self.root,'proxima centauri',offline=True)
        with patch('mod_manager.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):install(self.root,'proxima centauri',offline=True)
        self.assertEqual((self.root/'mods/proxima-centauri.json').read_bytes(),PACKAGE)
        self.assertEqual(list((self.root/'mods').glob('*.tmp')),[])

    def test_do_not_downgrade_newer_installed_mod(self):
        install(self.root,'proxima centauri',offline=True)
        data=json.loads(PACKAGE);data['version']='2.0.0'
        (self.root/'mods/proxima-centauri.json').write_text(json.dumps(data))
        self.assertIn('Kept installed',install(self.root,'proxima centauri',offline=True))

    @unittest.skipIf(sys.platform=='win32','Symlink permissions differ on Windows')
    def test_reject_symlink_install_folder(self):
        outside=self.root/'outside';outside.mkdir()
        (self.root/'mods').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ModError,'symbolic links'):install(self.root,'proxima centauri',offline=True)
        self.assertEqual(list(outside.iterdir()),[])

    def test_catalogue_isolation_switching_and_aliases(self):
        original=dict(BODIES)
        self.activate('/proxima centari')
        self.assertEqual(len(self.sim.visible_bodies),3)
        self.assertEqual([b.name for b in self.sim.primary_bodies],['Proxima Centauri d','Proxima Centauri b'])
        self.assertIn('RV minimum',self.sim.command('/proxima b'))
        self.assertIn('M dwarf star',self.sim.command('/star'))
        self.assertIn('/proxima exit',self.sim.command('/earth'))
        other=Simulation(mods_path=self.root/'mods')
        self.assertFalse(other.proxima_mode)
        self.assertEqual(len(other.primary_bodies),8)
        self.assertEqual(BODIES,original)
        self.sim.command('/dwarf')
        self.assertFalse(self.sim.proxima_mode)
        self.assertTrue(self.sim.dwarf_mode)
        self.sim.command('/proxima centauri')
        self.assertFalse(self.sim.dwarf_mode)
        self.sim.command('/proxima exit')
        self.assertEqual(self.sim.selected.name,'Earth')
        self.assertEqual(len(self.sim.primary_bodies),8)

    def test_planet_profiles_unknown_day_and_candidate(self):
        self.activate()
        for name in ('b','d'):
            profile=self.sim.command('/proxima '+name)
            for text in ('Unknown','estimate','minimum','None confirmed'):
                self.assertIn(text,profile)
            self.assertIn('unknown',self.sim.command('/day "proxima '+name+'"'))
            self.assertIn('no confirmed moons',self.sim.command('/mooons "proxima '+name+'"'))
        self.assertIn('unconfirmed',self.sim.command('/proxima c'))
        self.assertNotIn('Proxima Centauri c',[b.name for b in self.sim.visible_bodies])
        self.assertIn('unknown',self.sim.command('/weight 70 "proxima b"'))

    def test_orbits_focus_motion_zoom_and_moon_absence(self):
        self.activate()
        self.sim.command('/time 2026/10/18 13:45')
        text=self.sim.command('/orbit')
        self.assertIn('Proxima Centauri d',text)
        self.assertIn('Illustrative',text)
        planet=self.sim.body('proxima b')
        start=self.sim.position(planet)
        self.assertAlmostEqual(math.dist(start,(0,0,0)),planet.orbit,places=6)
        self.sim.date+=timedelta(days=planet.period/2)
        self.assertAlmostEqual(math.dist(start,self.sim.position(planet)),2*planet.orbit,places=5)
        self.sim.date+=timedelta(days=planet.period/2)
        self.assertLess(math.dist(start,self.sim.position(planet)),.001)
        self.sim.command('/proxima b')
        center,children=self.sim.map_system()
        self.assertEqual(center.name,'Proxima Centauri')
        self.assertEqual(children,[planet])
        self.assertIn('[2]',self.sim.text_map())
        map_only='\n'.join(''.join(c[0] for c in row) for row in self.sim.map_cells(88,25))
        self.assertIn('[2]',map_only)
        for target in ('/star','/proxima b','/proxima d'):
            self.sim.command(target)
            for camera in ('close','body','high','wide','system'):
                self.sim.command('/camera '+camera)
                self.assertEqual(len(self.sim.map_cells(80,20)),20)
        self.sim.command('/camera system')
        self.assertIn('no confirmed moons',self.sim.command('/mooons "proxima b"'))
        self.assertEqual(self.sim.map_system()[1],[])
        self.assertIn('unknown',self.sim.text_map())

    def test_comparisons_never_mix_solar_and_local_frames(self):
        self.activate()
        self.sim.command('/orbit')
        text=self.sim.command('/compare "proxima b" "proxima d"')
        self.assertEqual(self.sim.screen,'dashboard')
        for token in ('distance:', 'RV minimum','model estimate','arbitrary phases'):
            self.assertIn(token,text)
        self.assertIn('not modeled',self.sim.command('/distance earth "proxima b"'))
        self.assertIn('0.0 km',self.sim.command('/distance "proxima b" "proxima b"'))

    def test_export_local_frame_and_mission_reset(self):
        self.activate()
        with patch('proxima.ROOT',self.root):
            self.sim.command('/export')
        data=json.loads(next((self.root/'exports').glob('*.json')).read_text())
        self.assertIn('Proxima Centauri centered',data['frame'])
        self.assertEqual(len(data['bodies']),3)
        self.assertIn('local_position_km',data['bodies'][1])
        self.assertNotIn('heliocentric_position_km',data['bodies'][1])
        self.sim.command('/mission Apollo 11 30 seconds')
        self.assertFalse(self.sim.proxima_mode)
        self.assertIsNotNone(self.sim.mission)
        self.assertEqual(self.sim.selected.name,'Earth')
        self.sim.command('/proxima centauri')
        self.assertIsNone(self.sim.mission)
        self.assertTrue(self.sim.proxima_mode)
        self.sim.command('/reset')
        self.assertFalse(self.sim.proxima_mode)

    def test_menu_and_completion(self):
        self.activate()
        self.assertIn('/proxima centauri',completions('/proxima c',self.sim))
        nav=Navigation();nav.section=nav.sections.index('Planets')
        self.assertEqual([item.label for item in nav.items(self.sim)],[b.name for b in self.sim.proxima_bodies])
        item=body_item(self.sim.body('proxima b')).children[1]
        self.sim.command('/proxima exit')
        self.assertNotIn('Could not run',nav.execute(item,self.sim))
        self.assertTrue(self.sim.proxima_mode)
        self.assertEqual(self.sim.screen,'orbit')

    def test_downloaded_zip_cli_install_and_restart(self):
        archive,_=build(self.root/'dist')
        with zipfile.ZipFile(archive) as package:package.extractall(self.root/'download')
        app=self.root/'download/solar-sim'
        result=subprocess.run([sys.executable,str(app/'solar_sim.py'),'--offline','-mproxima centauri'],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertIn('Installed Proxima',result.stdout)
        result=subprocess.run([sys.executable,str(app/'solar_sim.py'),'--offline','-c','/proxima centari','-c','/orbit','-c','/proxima b','-c','/camera wide','-c','/map','-c','/compare "proxima b" "proxima d"','-c','/proxima exit','-c','/planet'],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('Could not run',result.stdout)
        self.assertIn('Proxima Centauri b',result.stdout)
        self.assertIn('/neptune',result.stdout)


if __name__=='__main__':unittest.main()
