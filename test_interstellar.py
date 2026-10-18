"""Install the film catalogue and verify frame isolation, navigation and model labels."""
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
from mod_manager import LIMIT, REGISTRY, ModError, install, load, validate
from navigation import Navigation, body_item
from solar_sim import completions
from tools.build_release import build

ROOT = Path(__file__).resolve().parent
PACKAGE = (ROOT/'mod_catalogue/interstellar.json').read_bytes()


class InterstellarTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'app with spaces'
        (self.root/'mod_catalogue').mkdir(parents=True)
        for name in ('interstellar','proxima-centauri'):
            (self.root/'mod_catalogue'/f'{name}.json').write_bytes((ROOT/'mod_catalogue'/f'{name}.json').read_bytes())
        (self.root/'VERSION.txt').write_text((ROOT/'VERSION.txt').read_text())
        self.sim=Simulation(mods_path=self.root/'mods',settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')

    def activate(self):
        install(self.root,'interstellar',offline=True)
        text=self.sim.command('/interstellar')
        self.assertNotIn('Could not run',text)
        return text

    def test_missing_mod_and_minimum_app_version(self):
        self.assertIn('sol-sim -m"interstellar"',self.sim.command('/interstellar'))
        self.assertFalse(self.sim.mod_mode)
        (self.root/'VERSION.txt').write_text('1.7.0')
        with self.assertRaisesRegex(ModError,'needs Solar Sim 1.8.0'):
            install(self.root,'interstellar',offline=True)
        self.assertFalse((self.root/'mods/interstellar.json').exists())

    def test_registered_remote_download_and_offline_fallback(self):
        calls=[]
        def remote(url,limit):calls.append((url,limit));return PACKAGE
        self.assertIn('Interstellar mod repository',install(self.root,'interstellar mod',fetch=remote))
        self.assertEqual(calls,[(REGISTRY['interstellar']['url'],LIMIT)])
        self.assertEqual(load(self.root/'mods','interstellar')['id'],'interstellar')
        fallback=install(self.root,'interstellar',fetch=lambda *_:(_ for _ in ()).throw(URLError('offline')))
        self.assertIn('bundled package',fallback)

    def test_packages_cannot_impersonate_another_registered_mod(self):
        self.activate()
        for data,expected in ((PACKAGE,'proxima-centauri'),((ROOT/'mod_catalogue/proxima-centauri.json').read_bytes(),'interstellar')):
            with self.assertRaises(ModError):validate(data,expected)
        old=(self.root/'mods/interstellar.json').read_bytes()
        with self.assertRaises(ModError):install(self.root,'interstellar',fetch=lambda *_:b'{}')
        self.assertEqual((self.root/'mods/interstellar.json').read_bytes(),old)
        self.assertFalse(list((self.root/'mods').glob('*.tmp')))

    def test_schema_rejects_injected_fields_and_unsafe_physical_values(self):
        for index,key,value in ((0,'mass',1e45),(0,'radius',-1),(0,'rotation',10),(1,'mass',float('inf')),
                                (1,'parent','Sun'),(1,'features','bad\x1b[0m'),(1,'run','exec'),(2,'period',0)):
            data=json.loads(PACKAGE);data['bodies'][index][key]=value
            with self.assertRaises(ModError,msg=key):validate(json.dumps(data).encode(),'interstellar')

    def test_system_switches_preserve_separate_catalogues_and_settings(self):
        original=dict(BODIES)
        self.activate()
        self.assertTrue(self.sim.interstellar_mode)
        self.assertFalse(self.sim.proxima_mode)
        self.assertEqual([b.name for b in self.sim.visible_bodies],['Gargantua','Miller','Mann','Edmunds'])
        self.assertEqual([b.name for b in self.sim.primary_bodies],['Miller','Mann','Edmunds'])
        self.assertIn('not modeled',self.sim.command('/compare earth miller'))
        saved=(self.sim.settings.theme,self.sim.settings.screensaver)
        install(self.root,'proxima centauri',offline=True)
        self.sim.command('/proxima centari')
        self.assertTrue(self.sim.proxima_mode)
        self.assertFalse(self.sim.interstellar_mode)
        self.assertIn('RV minimum',self.sim.command('/proxima b'))
        self.assertIn('not modeled',self.sim.command('/compare miller "proxima b"'))
        self.sim.command('/interstellar');self.sim.command('/dwarf')
        self.assertTrue(self.sim.dwarf_mode);self.assertFalse(self.sim.mod_mode)
        self.sim.command('/interstellar');self.sim.command('/interstellar exit')
        self.assertEqual(self.sim.selected.name,'Earth')
        self.assertEqual(len(self.sim.primary_bodies),8)
        self.assertEqual(saved,(self.sim.settings.theme,self.sim.settings.screensaver))
        self.assertEqual(BODIES,original)

    def test_profiles_aliases_day_moons_and_distance_disclaimers(self):
        self.activate()
        for name in ('miller','mann','edmunds','gargantua'):
            self.assertIn('FICTIONAL MODEL',self.sim.command('/'+name))
        self.assertIn('MILLER',self.sim.command('/"Miller\'s planet"'))
        self.assertIn('GARGANTUA',self.sim.command('/blackhole'))
        self.assertIn('Not specified',self.sim.command('/day miller'))
        self.assertIn('no planetary surface',self.sim.command('/day gargantua'))
        self.assertIn('not specified in the film',self.sim.command('/mooons miller'))
        self.assertIn('no spacecraft orbits included',self.sim.command('/satellites mann'))
        text=self.sim.command('/compare miller mann')
        for label in ('FICTIONAL MODEL','Center-to-center distance:','ignores curved spacetime','invented placeholder'):
            self.assertIn(label,text)
        self.assertIn('0.0 km',self.sim.command('/distance miller miller'))
        self.assertIn('placeholders',self.sim.command('/weight 70 miller'))
        self.assertIn('fictional',self.sim.command('/sync').lower())
        self.assertIn('paramount.com',self.sim.command('/sources'))

    def test_motion_orbit_focus_and_all_cameras(self):
        self.activate();self.sim.command('/time 2026/10/18 13:45')
        start=self.sim.position(self.sim.body('mann'))
        self.sim.command('/step 1.5')
        self.assertAlmostEqual(math.dist(start,self.sim.position(self.sim.body('mann'))),9e8,places=4)
        self.assertTrue(self.sim.paused)
        self.assertIn('Fictional',self.sim.command('/orbit'))
        for index,name in enumerate(('miller','mann','edmunds'),1):
            self.sim.command('/'+name)
            center,children=self.sim.map_system()
            self.assertEqual(center.name,'Gargantua')
            self.assertEqual([b.name.lower() for b in children],[name])
            grid='\n'.join(''.join(c[0] for c in row) for row in self.sim.map_cells(88,25))
            self.assertIn(f'[{index}]',grid)
        for name in ('miller','mann','edmunds','gargantua'):
            self.sim.command('/'+name)
            for level in ('close','body','high','wide','system'):
                self.sim.command('/camera '+level)
                self.assertEqual(len(self.sim.map_cells(64,22)),22)
        self.sim.command('/camera system')
        self.assertIn('not specified',self.sim.command('/mooons miller'))
        self.assertEqual(self.sim.map_system()[1],[])

    def test_navigation_completions_and_mission_reset(self):
        self.activate()
        self.assertIn('/interstellar',completions('/inter'))
        self.assertIn('/interstellar exit',completions('/interstellar e',self.sim))
        self.assertIn('/miller',completions('/mi',self.sim))
        nav=Navigation();nav.section=nav.sections.index('Mods')
        self.assertIn('Interstellar',[i.label for i in nav.items(self.sim)])
        item=body_item(self.sim.body('mann')).children[1]
        self.sim.command('/interstellar exit')
        self.assertNotIn('Could not run',nav.execute(item,self.sim))
        self.assertTrue(self.sim.interstellar_mode)
        self.assertEqual(self.sim.screen,'orbit')
        self.sim.command('/compare miller mann');self.assertEqual(self.sim.screen,'dashboard')
        self.sim.command('/mission Apollo 11 30 seconds')
        self.assertFalse(self.sim.mod_mode);self.assertIsNotNone(self.sim.mission)
        self.sim.command('/interstellar');self.assertIsNone(self.sim.mission)
        self.sim.command('/reset');self.assertFalse(self.sim.mod_mode)

    def test_failed_activation_keeps_current_system_and_replay(self):
        self.activate()
        self.assertIn('not installed',self.sim.command('/proxima centauri'))
        self.assertTrue(self.sim.interstellar_mode)
        self.sim.command('/mission Apollo 11 30 seconds')
        self.assertIn('not installed',self.sim.command('/proxima centauri'))
        self.assertIsNotNone(self.sim.mission)

    def test_export_labels_fiction_and_uses_own_coordinate_frame(self):
        self.activate()
        with patch('proxima.ROOT',self.root):self.sim.command('/export')
        data=json.loads(next((self.root/'exports').glob('interstellar-*.json')).read_text())
        self.assertTrue(data['fictional'])
        self.assertIn('Fictional Gargantua',data['frame'])
        self.assertEqual(len(data['bodies']),4)
        for body in data['bodies']:
            self.assertTrue(body['values_are_fictional'])
            self.assertFalse(body['mass_is_rv_minimum'])
            self.assertIn('local_position_km',body)
            self.assertNotIn('heliocentric_position_km',body)

    def test_extracted_download_cli_install_restart_and_switch(self):
        archive,_=build(self.root/'dist')
        with zipfile.ZipFile(archive) as package:package.extractall(self.root/'download')
        app=self.root/'download/solar-sim'
        def run(*args):
            result=subprocess.run([sys.executable,str(app/'solar_sim.py'),*args],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            self.assertNotIn('Could not run command',result.stdout)
            return result.stdout
        self.assertIn('Installed Interstellar',run('--offline','-minterstellar'))
        run('--offline','-mproxima centauri')
        text=run('--offline','-c','/interstellar','-c','/orbit','-c','/mann','-c','/camera wide','-c','/map',
                 '-c','/compare miller mann','-c','/proxima centari','-c','/proxima b',
                 '-c','/interstellar','-c','/interstellar exit','-c','/planet')
        for expected in ('Gargantua','Mann','FICTIONAL MODEL','PROXIMA CENTAURI B','/neptune'):
            self.assertIn(expected,text)


if __name__=='__main__':unittest.main()
