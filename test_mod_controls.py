"""Installed mod switches, removal and keyboard management with isolated app data."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine import Simulation
from mod_manager import ModError, disabled_mods, install, installed, set_enabled, uninstall
from navigation import Navigation
from solar_sim import completions

ROOT=Path(__file__).resolve().parent


class ModControlsTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.folder=self.root/'mods';self.folder.mkdir()
        (self.root/'VERSION.txt').write_text((ROOT/'VERSION.txt').read_text())
        for mod_id in ('proxima-centauri','interstellar'):
            (self.folder/(mod_id+'.json')).write_bytes((ROOT/'mod_catalogue'/(mod_id+'.json')).read_bytes())
        (self.folder/'aurora-system.json').write_bytes((ROOT/'solar-mod.json').read_bytes())
        self.sim=self.simulation()

    def simulation(self):
        return Simulation(mods_path=self.folder,settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')

    def command(self,raw):
        response=self.sim.command(raw)
        self.assertFalse(response.startswith(('Could not run command:','File operation failed:')),response)
        return response

    def test_switches_persist_and_gate_all_activation_spellings(self):
        for mod_id,commands in (('proxima-centauri',('/mod proxima-centauri','/proxima centauri','/proxima centari')),
                                ('interstellar',('/mod interstellar','/interstellar')),
                                ('aurora-system',('/mod aurora-system',))):
            self.command('/mods disable '+mod_id)
            self.sim=self.simulation()
            for command in commands:
                self.assertIn('turned off',self.sim.command(command))
                self.assertFalse(self.sim.mod_mode)
            self.command('/mods enable '+mod_id)
            self.command(commands[0]);self.assertEqual(self.sim.mod_id,mod_id)
            self.command('/mod exit')
        self.assertEqual(disabled_mods(self.folder),set())
        self.assertEqual(len(installed(self.folder)[0]),3)
        self.assertFalse(installed(self.folder)[1])

    def test_disable_and_uninstall_active_system_return_safely(self):
        for action in ('disable','uninstall'):
            self.command('/mods enable aurora-system')
            self.command('/mod aurora-system');self.command('/orbit Azure')
            self.sim.paused=True;date=self.sim.date
            self.command('/mods '+action+' aurora-system')
            self.assertFalse(self.sim.mod_mode);self.assertEqual(self.sim.selected.name,'Earth')
            self.assertIsNone(self.sim.orbit_focus);self.assertEqual(self.sim.date,date)
            self.assertNotIn('Azure',self.command('/orbit'))

    def test_other_mod_switch_does_not_leave_viewed_catalogue(self):
        self.command('/mod aurora-system')
        self.command('/mods disable interstellar')
        self.assertTrue(self.sim.community_mode)
        self.command('/mods uninstall interstellar')
        self.assertTrue(self.sim.community_mode)

    def test_uninstall_removes_only_package_and_its_preference(self):
        self.command('/mods disable aurora-system')
        self.command('/mods disable interstellar')
        (self.folder/'notes.txt').write_text('keep')
        before=(self.folder/'proxima-centauri.json').read_bytes()
        self.command('/mods uninstall aurora-system')
        self.assertFalse((self.folder/'aurora-system.json').exists())
        self.assertEqual(disabled_mods(self.folder),{'interstellar'})
        self.assertEqual((self.folder/'notes.txt').read_text(),'keep')
        self.assertEqual((self.folder/'proxima-centauri.json').read_bytes(),before)

    def test_updates_preserve_off_and_reinstall_after_removal_defaults_on(self):
        source=self.root/'solar-mod.json';source.write_bytes((ROOT/'solar-mod.json').read_bytes())
        self.command('/mods disable aurora-system')
        install(self.root,str(source),offline=True)
        self.assertIn('turned off',self.sim.command('/mod aurora-system'))
        self.command('/mods uninstall aurora-system')
        install(self.root,str(source),offline=True)
        self.command('/mod aurora-system');self.assertTrue(self.sim.community_mode)

    def test_invalid_package_can_be_removed_but_not_enabled(self):
        (self.folder/'broken-system.json').write_text('{}')
        self.assertIn('Could not run command:',self.sim.command('/mods enable broken-system'))
        nav=Navigation();nav.open_mods(self.sim)
        nav.index=next(i for i,item in enumerate(nav.items(self.sim)) if item.mod_id=='broken-system')
        self.assertIsNone(nav.activate(self.sim))
        self.assertEqual([i.label for i in nav.items(self.sim)],['Uninstall'])
        nav.execute(nav.current(self.sim),self.sim)
        self.assertFalse((self.folder/'broken-system.json').exists());self.assertFalse(nav.pages)

    def test_arrow_menu_refreshes_switch_and_keeps_selection_away_from_uninstall(self):
        nav=Navigation();nav.open_mods(self.sim)
        nav.index=next(i for i,item in enumerate(nav.items(self.sim)) if item.mod_id=='aurora-system')
        nav.activate(self.sim);nav.index=1
        self.assertEqual(nav.current(self.sim).label,'Turn off')
        nav.execute(nav.current(self.sim),self.sim)
        self.assertTrue(nav.opened);self.assertEqual(nav.current(self.sim).label,'Turn on')
        self.assertNotIn('Open system',[i.label for i in nav.items(self.sim)])
        nav.execute(nav.current(self.sim),self.sim)
        self.assertEqual(nav.current(self.sim).label,'Turn off')
        nav.index=2;nav.execute(nav.current(self.sim),self.sim)
        self.assertEqual(nav.title,'Mods');self.assertTrue(nav.opened)
        self.assertNotIn('aurora-system',[i.mod_id for i in nav.items(self.sim)])

    def test_failed_preference_write_preserves_file_state_and_active_view(self):
        self.command('/mod aurora-system')
        with patch('mod_manager.os.replace',side_effect=OSError('disk full')):
            self.assertIn('File operation failed:',self.sim.command('/mods disable aurora-system'))
        self.assertTrue(self.sim.community_mode)
        self.assertEqual(disabled_mods(self.folder),set())
        self.assertFalse(list(self.folder.glob('*.tmp')))

    def test_failed_uninstall_restores_preference(self):
        set_enabled(self.folder,'aurora-system',False)
        original=Path.unlink
        def fail_target(path,*args,**kwargs):
            if path==self.folder/'aurora-system.json':raise OSError('permission denied')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',fail_target):
            self.assertIn('File operation failed:',self.sim.command('/mods uninstall aurora-system'))
        self.assertTrue((self.folder/'aurora-system.json').is_file())
        self.assertIn('aurora-system',disabled_mods(self.folder))

    def test_paths_and_symlinks_cannot_delete_outside_package(self):
        for name in ('../outside','/tmp/outside','', 'BAD ID'):
            with self.assertRaises((ModError,TypeError)):uninstall(self.folder,name)
        outside=self.root/'outside.json';outside.write_text('keep')
        (self.folder/'linked-mod.json').symlink_to(outside)
        with self.assertRaises(ModError):uninstall(self.folder,'linked-mod')
        (self.folder/'.state.json').symlink_to(outside)
        with self.assertRaises(ModError):set_enabled(self.folder,'aurora-system',False)
        self.assertEqual(outside.read_text(),'keep')

    def test_damaged_preferences_are_reported_without_crashing_menu(self):
        (self.folder/'.state.json').write_text('{')
        self.assertIn('Cannot read mod preferences',self.sim.command('/mod aurora-system'))
        nav=Navigation();nav.open_mods(self.sim)
        self.assertEqual(nav.current(self.sim).label,'Mod preferences need repair')

    def test_commands_help_completion_and_default_on_listing(self):
        text=self.command('/mods')
        self.assertIn('[ON] Aurora System',text)
        self.assertIn('/mods uninstall ID',text)
        self.command('/mods disable aurora-system')
        self.assertIn('[OFF] Aurora System',self.command('/mods list'))
        self.assertIn('/mods enable aurora-system',completions('/mods enable au',self.sim))
        self.assertIn('/mods disable ID',self.command('/help'))
        self.assertIn('Usage:',self.sim.command('/mods nonsense'))


if __name__=='__main__':unittest.main()
