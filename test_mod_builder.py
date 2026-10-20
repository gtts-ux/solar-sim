"""Saved form edits, valid public mod exports and authoring data preservation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine import Simulation
from mod_builder import ModBuilder
from mod_manager import install, load
from navigation import Navigation
from solar_sim import completions

ROOT=Path(__file__).resolve().parent


class ModBuilderTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);(self.root/'VERSION.txt').write_text((ROOT/'VERSION.txt').read_text())
        self.builder=ModBuilder(self.root)

    def system(self):
        self.builder.new('Test system');self.builder.add('Star','Helios')
        self.builder.add('Planet','Nova');self.builder.add('Moon','Pebble','Nova')

    def simulation(self):
        return Simulation(online=False,mods_path=self.root/'mods',settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')

    def test_export_installs_as_standard_mod_with_orbits_moons_and_notes(self):
        self.system();self.builder.set('body','notes','An ocean world.',2)
        self.builder.set('project','notes','Author notes\\nSecond paragraph')
        destination=self.builder.export()
        self.assertEqual(set(p.name for p in destination.iterdir()),{'solar-mod.json','builder-draft.json','README.md','README.txt','PUBLISH.txt'})
        self.assertIn('Author notes\nSecond paragraph',(destination/'README.md').read_text())
        self.assertIn('solar-mod.json must be at the repository root',(destination/'PUBLISH.txt').read_text())
        install(self.root,str(destination/'solar-mod.json'),offline=True)
        sim=self.simulation()
        for command,expected in (('/mod test-system','COMMUNITY SYSTEM'),('/body Nova','An ocean world.'),
                                 ('/orbit','Nova'),('/moons Nova','Pebble')):
            self.assertIn(expected,sim.command(command))
        self.assertEqual(load(self.root/'mods','test-system')['format'],2)

    def test_draft_persists_and_renaming_updates_planet_and_moon_parents(self):
        self.system();self.builder.set('body','name','New Nova',2)
        self.builder.set('body','name','New Helios',1)
        reloaded=ModBuilder(self.root)
        self.assertEqual(reloaded.body(2)['parent'],'New Helios')
        self.assertEqual(reloaded.body(3)['parent'],'New Nova')
        self.assertIn('Ready to export',reloaded.validate())

    def test_invalid_edits_are_transactional_in_memory_and_on_disk(self):
        self.system();before=self.builder.path.read_bytes();state=self.builder.state
        for scope,field,value,index in (('body','mass','nan',2),('body','radius','-1',2),
                                        ('body','name','Helios',2),('body','parent','Pebble',3),
                                        ('body','color','9',2),('mod','id','../outside',None)):
            with self.subTest(field=field),self.assertRaises(ValueError):self.builder.set(scope,field,value,index)
            self.assertEqual(self.builder.path.read_bytes(),before);self.assertEqual(self.builder.state,state)
        for index in (0,-1,100,'not a number'):
            with self.assertRaises(ValueError):self.builder.remove(index)

    def test_incomplete_drafts_save_but_cannot_be_exported(self):
        self.builder.new('Empty system')
        with self.assertRaises(ValueError):self.builder.export()
        self.builder.add('Star','Alone')
        with self.assertRaises(ValueError):self.builder.export()
        self.assertEqual(ModBuilder(self.root).body(1)['name'],'Alone')
        self.assertFalse(any(p.is_dir() for p in self.builder.folder.iterdir()))

    def test_real_mod_requires_sources_at_export_and_keeps_estimate_flags(self):
        self.system();self.builder.set('mod','fictional','false')
        with self.assertRaises(ValueError):self.builder.export()
        with self.assertRaises(ValueError):self.builder.set('mod','sources','http://example.com')
        self.builder.set('mod','sources','https://example.com/source')
        data=json.loads((self.builder.export()/'solar-mod.json').read_text())
        self.assertFalse(data['fictional']);self.assertTrue(data['bodies'][1]['estimated_mass'])

    def test_repeated_exports_never_overwrite_published_snapshots_or_existing_folders(self):
        self.system();existing=self.builder.folder/'test-system';existing.mkdir()
        (existing/'keep.txt').write_text('keep')
        first=self.builder.export();before=(first/'solar-mod.json').read_bytes()
        self.builder.set('body','notes','Changed later',2);second=self.builder.export()
        self.assertNotEqual(first,second);self.assertEqual((first/'solar-mod.json').read_bytes(),before)
        self.assertEqual((existing/'keep.txt').read_text(),'keep')

    def test_new_and_load_preserve_previous_drafts_and_project_notes(self):
        self.system();self.builder.set('project','notes','Remember this');export=self.builder.export()
        self.builder.new('Other project')
        backups=[p for p in self.builder.projects() if p.startswith('saved-draft-')]
        self.assertEqual(len(backups),1)
        self.builder.load(export.name)
        self.assertEqual(self.builder.state['notes'],'Remember this')
        self.assertEqual(len([p for p in self.builder.projects() if p.startswith('saved-draft-')]),2)
        with self.assertRaises(ValueError):self.builder.load('../draft.json')

    def test_removing_planet_removes_descendants_but_keeps_other_bodies_and_exports(self):
        self.system();self.builder.add('Moon','Dust','Pebble');self.builder.add('Planet','Elsewhere')
        export=self.builder.export();self.builder.remove(2)
        self.assertEqual([b['name'] for b in self.builder.package['bodies']],['Helios','Elsewhere'])
        self.assertEqual(len(json.loads((export/'solar-mod.json').read_text())['bodies']),5)

    def test_failed_save_preserves_draft_and_cleans_temporary_file(self):
        self.system();before=self.builder.path.read_bytes();state=self.builder.state
        with patch('mod_builder.os.replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.builder.set('body','radius','7000',2)
        self.assertEqual(self.builder.path.read_bytes(),before);self.assertEqual(self.builder.state,state)
        self.assertFalse(list(self.builder.folder.glob('*.tmp')))

    def test_corrupt_draft_does_not_crash_menu_and_is_backed_up_before_recovery(self):
        self.builder.folder.mkdir();self.builder.path.write_text('{bad draft')
        sim=self.simulation();nav=Navigation();nav.open_builder(sim)
        self.assertEqual(nav.items(sim)[0].label,'Start a fresh draft')
        self.builder.new('Recovered')
        saved=next(self.builder.folder.glob('saved-draft-*'))
        self.assertEqual(saved.read_text(),'{bad draft')
        self.assertEqual(self.builder.package['name'],'Recovered')

    def test_symlink_draft_and_project_folder_are_rejected(self):
        outside=self.root/'outside';outside.mkdir()
        self.builder.folder.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):self.builder.new('Linked')
        self.builder.folder.unlink();self.builder.folder.mkdir()
        target=outside/'keep.json';target.write_text('keep')
        self.builder.path.symlink_to(target)
        with self.assertRaises(ValueError):self.builder.new('Linked')
        self.assertEqual(target.read_text(),'keep')

    def test_arrow_forms_add_star_planet_and_moon_without_json_or_slash_commands(self):
        sim=self.simulation();nav=Navigation();nav.open_mods(sim)
        nav.index=next(i for i,item in enumerate(nav.items(sim)) if item.label=='Create a mod')
        nav.activate(sim)
        def form(label,value):
            nav.index=next(i for i,item in enumerate(nav.items(sim)) if item.label==label)
            self.assertIsNone(nav.activate(sim));self.assertIsNotNone(nav.editor)
            self.assertTrue(nav.submit_editor(value,sim),nav.feedback)
        form('New mod...','Menu system');form('Add star','Sunlet');nav.back()
        form('Add planet','Blue');form('Add moon','Dot');nav.back();nav.back()
        self.assertEqual(sim.builder.body(3)['parent'],'Blue')
        nav.index=next(i for i,item in enumerate(nav.items(sim)) if item.label=='Export project folder')
        response=nav.execute(nav.activate(sim),sim)
        self.assertIn('Mod project exported:',response)
        self.assertTrue((self.root/'mod-projects/menu-system/solar-mod.json').is_file())
        self.assertTrue(nav.opened)

    def test_commands_and_original_manual_workflow_remain_available(self):
        sim=self.simulation()
        self.assertIn('MOD MAKER',sim.command('/builder'))
        self.assertIn('Created draft',sim.command('/builder new "CLI project"'))
        self.assertIn('Added Sol',sim.command('/builder add star Sol'))
        self.assertIn('Added Terra',sim.command('/builder add planet Terra'))
        self.assertIn('Ready to export',sim.command('/builder validate'))
        self.assertIn('MAKE AND SHARE',sim.command('/mod tutorial'))
        self.assertIn('/builder',completions('/bu',sim))

    def test_existing_mod_ids_are_not_taken_over_by_the_new_maker(self):
        self.system();self.builder.set('mod','id','maker')
        install(self.root,str(self.builder.export()/'solar-mod.json'),offline=True)
        sim=self.simulation()
        self.assertIn('COMMUNITY SYSTEM',sim.command('/mod maker'))


if __name__=='__main__':unittest.main()
