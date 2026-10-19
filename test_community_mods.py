"""Public authoring/install workflow and scoped planet/moon simulation."""
import base64
from contextlib import nullcontext
from copy import deepcopy
from datetime import timedelta
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError
import zipfile

import community_mods as model
from catalog import BODIES
from engine import Simulation
from mod_manager import LIMIT, ModError, download_community, install, installed, load, parse_package
from navigation import Navigation, body_item
from solar_sim import completions
from tools.build_release import build
from updater import fetch_bytes

ROOT=Path(__file__).resolve().parent
PACKAGE=(ROOT/'solar-mod.json').read_bytes()
DATA=json.loads(PACKAGE)


class CommunityModTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'app with spaces';self.root.mkdir()
        (self.root/'VERSION.txt').write_text((ROOT/'VERSION.txt').read_text())
        (self.root/'solar-mod.json').write_bytes(PACKAGE)
        (self.root/'mod_catalogue').mkdir()
        for name in ('proxima-centauri','interstellar'):
            (self.root/'mod_catalogue'/f'{name}.json').write_bytes((ROOT/'mod_catalogue'/f'{name}.json').read_bytes())
        self.sim=Simulation(mods_path=self.root/'mods',settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')

    def activate(self):
        install(self.root,str(self.root/'solar-mod.json'),offline=True)
        response=self.sim.command('/mod aurora-system')
        self.assertNotIn('Could not run',response)
        return response

    def test_template_install_is_data_only_and_lists_its_actual_id(self):
        text=self.activate()
        self.assertIn('FICTIONAL',text)
        self.assertTrue(self.sim.community_mode)
        self.assertFalse(self.sim.proxima_mode)
        self.assertFalse(self.sim.interstellar_mode)
        self.assertEqual(self.sim.mod_id,'aurora-system')
        self.assertEqual((self.root/'mods/aurora-system.json').read_bytes(),PACKAGE)
        self.assertIn('/mod aurora-system',self.sim.command('/mods'))
        self.assertEqual(len(self.sim.mod_bodies),4)

    def test_github_repository_reads_root_file_on_default_branch(self):
        metadata=json.dumps({'type':'file','encoding':'base64','size':len(PACKAGE),
                             'content':base64.encodebytes(PACKAGE).decode()}).encode()
        for source in ('new-user/my-system','https://github.com/new-user/my-system','https://github.com/new-user/my-system.git'):
            calls=[]
            def fetch(url,limit):calls.append((url,limit));return metadata
            result=install(self.root,source,fetch=fetch)
            self.assertIn('public GitHub package',result)
            self.assertEqual(calls,[('https://api.github.com/repos/new-user/my-system/contents/solar-mod.json',LIMIT*2)])

    def test_github_blob_and_raw_links_fetch_only_the_json(self):
        raw='https://raw.githubusercontent.com/new-user/my-system/main/data/system.json'
        for source in (raw,'https://github.com/new-user/my-system/blob/main/data/system.json'):
            calls=[]
            def fetch(url,limit):calls.append((url,limit));return PACKAGE
            install(self.root,source,fetch=fetch)
            self.assertEqual(calls,[(raw,LIMIT)])

    def test_repository_transport_requests_github_json_metadata(self):
        url='https://api.github.com/repos/new-user/my-system/contents/solar-mod.json'
        metadata=json.dumps({'type':'file','encoding':'base64','size':len(PACKAGE),
                             'content':base64.encodebytes(PACKAGE).decode()}).encode()
        response=Mock();response.geturl.return_value=url
        response.headers={'Content-Length':str(len(metadata))};response.read.return_value=metadata
        opener=Mock();opener.open.return_value=nullcontext(response)
        with patch('updater.build_opener',return_value=opener):
            self.assertEqual(download_community('new-user/my-system',fetch_bytes),PACKAGE)
        request=opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Accept'),'application/vnd.github+json')

    def test_non_github_urls_credentials_queries_and_non_json_are_rejected(self):
        for source in ('http://github.com/u/r','https://example.com/mod.json',
                       'https://user:pass@github.com/u/r','https://github.com/u/r?token=secret',
                       'https://raw.githubusercontent.com/u/r/main/evil.py',
                       'https://127.0.0.1/mod.json','https://github.com:444/u/r'):
            with self.subTest(source=source),self.assertRaises(ModError):
                install(self.root,source,fetch=lambda *_:self.fail('Must not fetch unaccepted URL'))

    def test_offline_repository_does_not_silently_install_a_different_mod(self):
        with self.assertRaisesRegex(ModError,'needs internet'):
            install(self.root,'new-user/my-system',offline=True,fetch=lambda *_:self.fail('offline'))
        with self.assertRaisesRegex(ModError,'Cannot download'):
            install(self.root,'new-user/my-system',fetch=lambda *_:(_ for _ in ()).throw(URLError('offline')))
        self.assertFalse((self.root/'mods').exists())

    def test_repository_metadata_and_package_downloads_are_bounded(self):
        for metadata in ({'type':'dir'}, {'type':'file','encoding':'base64','size':LIMIT+1,'content':'AA=='},
                         {'type':'file','encoding':'base64','size':1,'content':'invalid!'},
                         {'type':'file','encoding':'base64','size':100,'content':'AA=='}):
            with self.assertRaises(ModError):download_community('new-user/my-system',lambda *_:json.dumps(metadata).encode())
        with self.assertRaises(ModError):parse_package(b'x'*(LIMIT+1))

    def test_unsafe_ids_aliases_controls_and_unknown_code_fields_are_rejected(self):
        for identifier in ('../outside','/absolute','bad/name','UPPER','bad..id','interstellar','proxima-centauri','con','com1','two--hyphens'):
            data=deepcopy(DATA);data['id']=identifier
            with self.assertRaises(ModError,msg=identifier):parse_package(json.dumps(data).encode())
        for key,value in (('features','bad\x1b[2J'),('aliases',['../bad']),('aliases',['Azure']),('run','script.py'),('mass',float('nan')),('radius',0),('color',True)):
            data=deepcopy(DATA);data['bodies'][1][key]=value
            with self.assertRaises(ModError,msg=key):parse_package(json.dumps(data).encode())
        self.assertFalse((self.root/'outside.json').exists())

    def test_parent_graph_names_ranges_sources_and_versions_are_validated(self):
        cases=[]
        for index,key,value in ((0,'parent','Azure'),(1,'name','Aurora'),(2,'parent','Unknown'),
                                (2,'parent','azure'),(2,'parent','Lumen'),(2,'parent','Aurora'),
                                (1,'period',0),(1,'eccentricity',.95),(1,'inclination',181),(1,'phase',360),
                                (1,'rotation',1000001),(1,'mass',1e50)):
            data=deepcopy(DATA);data['bodies'][index][key]=value;cases.append(data)
        for key,value in (('fictional','yes'),('app_min','1.9.0'),('version','next'),('format',True),('sources',['http://example.com'])):
            data=deepcopy(DATA);data[key]=value;cases.append(data)
        data=deepcopy(DATA);data['fictional']=False;cases.append(data)
        for data in cases:
            with self.assertRaises(ModError):parse_package(json.dumps(data).encode())
        data=deepcopy(DATA);data['fictional']=False;data['sources']=['https://science.nasa.gov/']
        self.assertFalse(parse_package(json.dumps(data).encode())['fictional'])

    def test_bad_update_size_mismatch_and_failed_replace_keep_previous_file(self):
        self.activate();target=self.root/'mods/aurora-system.json'
        for content in (b'{}',b'bad',b'x'*(LIMIT+1)):
            with self.assertRaises(ModError):install(self.root,'https://raw.githubusercontent.com/u/r/main/mod.json',fetch=lambda *_,v=content:v)
            self.assertEqual(target.read_bytes(),PACKAGE)
        with patch('mod_manager.os.replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):install(self.root,str(self.root/'solar-mod.json'),offline=True)
        self.assertEqual(target.read_bytes(),PACKAGE)
        self.assertFalse(list((self.root/'mods').glob('*.tmp')))

    def test_community_versions_update_without_downgrades_and_require_compatible_app(self):
        self.activate()
        data=deepcopy(DATA);data['version']='1.1.0'
        (self.root/'solar-mod.json').write_text(json.dumps(data))
        install(self.root,str(self.root/'solar-mod.json'),offline=True)
        (self.root/'solar-mod.json').write_bytes(PACKAGE)
        self.assertIn('Kept installed',install(self.root,str(self.root/'solar-mod.json'),offline=True))
        self.assertEqual(load(self.root/'mods','aurora-system')['version'],'1.1.0')
        data['app_min']='99.0.0';(self.root/'solar-mod.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(ModError,'needs Solar Sim'):install(self.root,str(self.root/'solar-mod.json'),offline=True)

    @unittest.skipIf(sys.platform=='win32','Symlink permissions differ on Windows')
    def test_symlink_mod_destination_does_not_write_outside_the_app(self):
        outside=self.root/'outside';outside.mkdir()
        (self.root/'mods').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ModError,'symbolic links'):install(self.root,str(self.root/'solar-mod.json'),offline=True)
        self.assertEqual(list(outside.iterdir()),[])

    def test_planets_moons_comparisons_and_unknown_data_have_community_labels(self):
        self.activate()
        self.assertEqual([b.name for b in self.sim.primary_bodies],['Azure','Ember'])
        self.assertIn('estimate/model value',self.sim.command('/body Azure'))
        self.assertIn('Lumen',self.sim.command('/moons'))
        self.assertIn('Lumen',self.sim.command('/moons Azure'))
        self.assertIn('0 included moons',self.sim.command('/moons Ember'))
        self.assertIn('LUMEN',self.sim.command('/moon Lumen'))
        self.assertIn('AZURE',self.sim.command('/blue world'))
        self.assertIn('24 hours',self.sim.command('/day Azure'))
        self.assertIn('Center-to-center distance:',self.sim.command('/compare Azure Ember'))
        self.assertIn('not an observed',self.sim.command('/distance Azure Lumen'))
        self.assertIn('0.000 km',self.sim.command('/distance Azure Azure'))
        self.assertIn('not modeled',self.sim.command('/distance Earth Azure'))
        self.assertIn('Spherical model force',self.sim.command('/weight 70 Azure'))
        self.assertIn('no planetary solid surface',self.sim.command('/weight 70 Aurora'))
        self.assertIn('Fictional original',self.sim.command('/sources'))
        self.assertIn('/azure',self.sim.command('/search ocean'))
        self.assertIn('community',self.sim.command('/sync').lower())

    def test_parent_relative_ellipses_have_real_period_and_orbit_path_alignment(self):
        self.activate();self.sim.command('/time 2000/01/01 12:00')
        for name in ('Azure','Lumen','Ember'):
            body=self.sim.body(name);parent=self.sim.body(body.parent)
            start=tuple(a-b for a,b in zip(self.sim.position(body),self.sim.position(parent)))
            self.assertTrue(body.orbit*(1-body.eccentricity)-.001<=math.dist(start,(0,0,0))<=body.orbit*(1+body.eccentricity)+.001)
            entry=self.sim.entry(body)
            mean=math.radians(entry['phase']);ecc=mean
            for _ in range(20):ecc-=(ecc-body.eccentricity*math.sin(ecc)-mean)/(1-body.eccentricity*math.cos(ecc))
            self.assertLess(math.dist(start,self.sim.orbit_path(body)(ecc)),.001)
            date=self.sim.date;self.sim.date+=timedelta(days=body.period)
            end=tuple(a-b for a,b in zip(self.sim.position(body),self.sim.position(parent)))
            self.assertLess(math.dist(start,end),.01)
            self.sim.date=date

    def test_high_eccentricities_converge_and_moons_support_parent_chains(self):
        data=deepcopy(DATA)
        data['bodies'][1]['eccentricity']=.94
        body=model.bodies(data)[1]
        for angle in (0,.001,.1,1,3,5,6.28):
            entry={**data['bodies'][1],'phase':math.degrees(angle)}
            point=model.offset(body,entry,model.EPOCH)
            self.assertTrue(all(math.isfinite(v) for v in point))
            self.assertTrue(body.orbit*.06-.01<=math.dist(point,(0,0,0))<=body.orbit*1.94+.01)
        moon=deepcopy(data['bodies'][2]);moon.update(name='Little Lumen',parent='Lumen',aliases=['little moon'],orbit=4000,period=2)
        data['bodies'].append(moon)
        self.assertEqual(len(parse_package(json.dumps(data).encode())['bodies']),5)

    def test_focus_and_all_moon_orbits_keep_consistent_numbers_at_every_zoom(self):
        data=deepcopy(DATA);moon=deepcopy(data['bodies'][2]);moon.update(name='Second Moon',aliases=['second'],orbit=600000,period=50)
        data['bodies'].append(moon);(self.root/'solar-mod.json').write_text(json.dumps(data))
        install(self.root,str(self.root/'solar-mod.json'),offline=True);self.sim.command('/mod aurora-system')
        self.sim.command('/orbit');self.sim.command('/mooons Azure')
        self.assertEqual([b.name for b in self.sim.map_system()[1]],['Lumen','Second Moon'])
        self.sim.command('/body Second Moon')
        self.assertEqual(self.sim.map_system()[0].name,'Azure')
        grid='\n'.join(''.join(c[0] for c in row) for row in self.sim.map_cells(88,25))
        self.assertIn('[2]',grid)
        self.assertIn('[2] Second Moon',self.sim.text_map())
        for name in ('Aurora','Azure','Lumen','Ember'):
            self.sim.command('/body '+name)
            for level in ('close','body','high','wide','system'):
                self.sim.command('/camera '+level)
                self.assertEqual(len(self.sim.map_cells(64,22)),22)

    def test_catalogue_switches_do_not_pollute_global_bodies_or_other_instances(self):
        before=dict(BODIES);self.activate()
        other=Simulation(mods_path=self.root/'mods')
        self.assertFalse(other.community_mode);self.assertEqual(len(other.primary_bodies),8)
        for name,command in (('proxima centauri','/proxima centari'),('interstellar','/interstellar')):
            install(self.root,name,offline=True)
            self.assertNotIn('Could not run',self.sim.command(command))
            self.assertFalse(self.sim.community_mode)
            self.sim.command('/mod aurora-system')
        self.sim.command('/dwarf');self.assertTrue(self.sim.dwarf_mode)
        self.sim.command('/mod aurora-system');self.sim.command('/mod exit')
        self.assertEqual(self.sim.selected.name,'Earth')
        self.assertEqual(BODIES,before)

    def test_command_name_collisions_cannot_take_over_controls(self):
        data=deepcopy(DATA);data['bodies'][3].update(name='Reset',aliases=['time'])
        (self.root/'solar-mod.json').write_text(json.dumps(data))
        install(self.root,str(self.root/'solar-mod.json'),offline=True);self.sim.command('/mod aurora-system')
        self.assertIn('RESET / Planet',self.sim.command('/body Reset'))
        self.assertIn('SIMULATION CLOCK',self.sim.command('/time'))
        self.sim.command('/reset');self.assertFalse(self.sim.mod_mode)

    def test_installed_list_reports_invalid_files_and_validates_filename_id(self):
        self.activate();(self.root/'mods/broken.json').write_text('{}')
        (self.root/'mods/wrong-name.json').write_bytes(PACKAGE)
        valid,errors=installed(self.root/'mods')
        self.assertEqual([p['id'] for p in valid],['aurora-system'])
        self.assertEqual({name for name,_ in errors},{'broken.json','wrong-name.json'})
        self.assertIn('INVALID PACKAGES',self.sim.command('/mods'))
        self.assertIn('not installed',self.sim.command('/mod missing-id'))
        self.assertTrue(self.sim.community_mode)

    def test_explicit_reinstall_repairs_an_invalid_installed_package(self):
        self.activate()
        (self.root/'mods/aurora-system.json').write_text('{}')
        self.assertIn('INVALID PACKAGES',self.sim.command('/mods'))
        install(self.root,str(self.root/'solar-mod.json'),offline=True)
        self.assertEqual(load(self.root/'mods','aurora-system')['id'],'aurora-system')

    def test_arrow_menu_installed_entries_stale_body_actions_and_completion(self):
        self.activate();nav=Navigation();nav.section=nav.sections.index('Mods')
        self.assertIn('Aurora System',[i.label for i in nav.items(self.sim)])
        nav.section=nav.sections.index('Planets')
        self.assertEqual([i.label for i in nav.items(self.sim)],['Aurora','Azure','Ember'])
        self.assertIn('Moons',[i.label for i in nav.items(self.sim)[1].children])
        item=nav.items(self.sim)[1].children[0]
        nav.section=nav.sections.index('Moons')
        self.assertEqual([i.label for i in nav.items(self.sim)],['Lumen'])
        self.sim.command('/mod exit')
        self.assertNotIn('Could not run',nav.execute(item,self.sim))
        self.assertTrue(self.sim.community_mode)
        self.assertIn('/mod aurora-system',completions('/mod au',self.sim))
        self.assertIn('/body Azure',completions('/body Az',self.sim))
        self.assertIn('/mod tutorial',completions('/mod tu',self.sim))

    def test_export_contains_only_this_local_system_and_marks_estimates(self):
        self.activate()
        with patch('community_runtime.ROOT',self.root):self.sim.command('/export')
        data=json.loads(next((self.root/'exports').glob('*.json')).read_text())
        self.assertEqual(data['mod_id'],'aurora-system');self.assertTrue(data['fictional'])
        self.assertEqual(len(data['bodies']),4)
        for body in data['bodies']:
            self.assertIn('local_position_km',body);self.assertNotIn('heliocentric_position_km',body)
            self.assertTrue(body['mass_is_estimate'])

    def test_full_screen_overview_handles_custom_rotation_and_central_stars(self):
        from solar_sim import tui
        self.activate();self.sim.paused=True
        install(self.root,'proxima centauri',offline=True)
        curses=SimpleNamespace(error=type('CursesError',(Exception,),{}),A_BOLD=1,A_DIM=2,A_REVERSE=4,
                               KEY_ENTER=343,KEY_BACKSPACE=263,KEY_DC=330,KEY_F2=266,
                               KEY_LEFT=260,KEY_RIGHT=261,KEY_UP=259,KEY_DOWN=258,
                               KEY_HOME=262,KEY_END=360,KEY_PPAGE=339,KEY_NPAGE=338,
                               set_escdelay=Mock(),curs_set=Mock(),doupdate=Mock())
        screen=Mock();screen.getmaxyx.return_value=(36,110)
        screen.get_wch.side_effect=[*'/body Lumen\r',*'/body Aurora\r',*'/mod proxima-centauri\r',*'/star\r',*'/mod exit\r','\x04']
        with patch.dict('sys.modules',{'curses':curses}):tui(screen,self.sim,no_color=True)
        self.assertTrue(any('COMMUNITY DATA' in str(call) for call in screen.addnstr.call_args_list))

    def test_full_extracted_author_workflow_template_check_install_and_restart(self):
        archive,_=build(self.root/'dist')
        with zipfile.ZipFile(archive) as package:package.extractall(self.root/'download')
        app=self.root/'download/solar-sim';destination=self.root/'my new mod.json'
        def run(*args,code=0):
            result=subprocess.run([sys.executable,str(app/'solar_sim.py'),*args],cwd=self.temp.name,capture_output=True,text=True,timeout=25)
            self.assertEqual(result.returncode,code,result.stdout+result.stderr)
            return result.stdout
        self.assertIn('MAKE AND SHARE',run('--mod-tutorial'))
        self.assertIn('Created mod template',run('--mod-template',str(destination)))
        original=destination.read_bytes();run('--mod-template',str(destination),code=1)
        self.assertEqual(destination.read_bytes(),original)
        self.assertIn('Nothing was installed',run('--check-mod',str(destination)))
        self.assertFalse((app/'mods').exists())
        self.assertIn('Installed Aurora System',run('--offline','-m'+str(destination)))
        text=run('--offline','-c','/mods','-c','/mod aurora-system','-c','/orbit','-c','/moons Azure',
                 '-c','/body Lumen','-c','/compare Azure Ember','-c','/mod exit','-c','/planet','-c','/mod tutorial')
        self.assertNotIn('Could not run command',text)
        for expected in ('Lumen','COMMUNITY SYSTEM','Center-to-center distance:','/neptune','MAKE AND SHARE'):
            self.assertIn(expected,text)
        destination.write_text('{}');run('--check-mod',str(destination),code=1)
        self.assertEqual((app/'mods/aurora-system.json').read_bytes(),PACKAGE)

    @unittest.skipIf(os.name=='nt','The short-command wrappers target POSIX shells.')
    def test_short_commands_preserve_project_folder_for_relative_mod_paths(self):
        from install_commands import install as install_commands
        archive,_=build(self.root/'dist')
        with zipfile.ZipFile(archive) as package:package.extractall(self.root/'download')
        app=self.root/'download/solar-sim';bin_dir=self.root/'commands'
        install_commands(app,bin_dir)
        for name in ('sol-sim','solar-sim'):
            project=self.root/('project '+name);project.mkdir()
            for args in (['--mod-template','solar-mod.json'],['--check-mod','solar-mod.json'],['--offline','-m','./solar-mod.json']):
                result=subprocess.run([str(bin_dir/name),*args],cwd=project,capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual((project/'solar-mod.json').read_bytes(),PACKAGE)
        self.assertEqual((app/'solar-mod.json').read_bytes(),PACKAGE)


if __name__=='__main__':unittest.main()
