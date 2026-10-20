"""Menu actions against the real simulation, without a platform curses dependency."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, PropertyMock, patch

from catalog import lookup
from engine import Simulation
from flight_replay import find_flight
from live_launches import parse_launch
from navigation import Navigation
from solar_sim import completions, tui
from themes import Settings


def launch(identifier, name):
    return parse_launch({'id':identifier, 'name':name, 'net':'2026-10-20T12:00:00Z',
                         'status':{'id':1,'name':'Go for launch'},
                         'launch_service_provider':{'name':'SpaceX'}})


class NavigationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.sim=Simulation(settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')
        self.clock=patch('engine.time.monotonic',return_value=100.)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        request=patch.object(self.sim.launches,'request')
        request.start()
        self.addCleanup(request.stop)
        self.nav=Navigation()
        self.nav.toggle()

    def choose(self, section, *labels):
        self.nav.opened=True
        self.nav.change_section(self.nav.sections.index(section)-self.nav.section)
        item=None
        for label in labels:
            self.nav.index=next(i for i,item in enumerate(self.nav.items(self.sim)) if item.label==label)
            item=self.nav.activate(self.sim)
        return item

    def run_item(self, section, *labels):
        item=self.choose(section,*labels)
        self.assertIsNotNone(item)
        result=self.nav.execute(item,self.sim)
        self.assertNotIn('Could not run command',result)
        return result

    def test_browsing_and_cancel_preserve_replay_overlay_clock_and_camera(self):
        self.sim.command('/mission Apollo 11 1 minute')
        self.sim.command('/camera wide')
        self.sim.command('/setting')
        replay=self.sim.mission
        date=self.sim.date
        for section in self.nav.sections:
            self.nav.change_section(1)
            entries=self.nav.items(self.sim)
            for index in range(len(entries)):
                self.nav.index=index
                if entries[index].children:
                    self.nav.activate(self.sim)
                    self.nav.move(10000,self.sim)
                    self.nav.back()
        self.nav.toggle()
        self.assertFalse(self.nav.opened)
        self.assertIs(self.sim.mission,replay)
        self.assertEqual(self.sim.date,date)
        self.assertFalse(self.sim.paused)
        self.assertEqual(self.sim.overlay,'settings')
        self.assertEqual(self.sim.camera.name,'wide')
        self.assertIn('ARROW NAVIGATION',self.sim.command('/menu'))
        self.assertIs(self.sim.mission,replay)
        self.assertIn('/menu',completions('/men'))

    def test_body_orbits_profiles_and_moons_work_from_existing_orbit_mode(self):
        self.run_item('Planets','Jupiter','Orbit view')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.view,'jupiter')
        self.run_item('Planets','Jupiter','Moons')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.system_filter,'moons')
        self.sim.command('/setting')
        result=self.run_item('Moons','Europa','Profile')
        self.assertIn('PHYSICAL PROFILE',result)
        self.assertEqual(self.sim.screen,'dashboard')
        self.assertEqual(self.sim.selected,lookup('europa'))
        self.run_item('Spacecraft','ISS','Orbit view')
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.orbit_focus.name,'ISS')

    def test_dwarfs_remain_separate_and_catalogue_switches_only_on_action(self):
        item=self.choose('Dwarfs','Pluto','Orbit view')
        self.assertFalse(self.sim.dwarf_mode)
        self.nav.execute(item,self.sim)
        self.assertTrue(self.sim.dwarf_mode)
        self.assertEqual(self.sim.view,'pluto')
        self.choose('Moons')
        self.assertEqual([i.label for i in self.nav.items(self.sim)],['Charon'])
        self.run_item('Planets','Earth','Orbit view')
        self.assertFalse(self.sim.dwarf_mode)
        self.assertEqual(self.sim.view,'earth')
        self.choose('Planets')
        self.assertNotIn('Pluto',[i.label for i in self.nav.items(self.sim)])
        # A reopened submenu uses the current catalogue, even after external commands.
        stale_item=self.choose('Planets','Earth','Profile')
        self.sim.command('/dwarf')
        self.nav.execute(stale_item,self.sim)
        self.assertFalse(self.sim.dwarf_mode)
        self.assertEqual(self.sim.selected,lookup('earth'))

    def test_settings_save_without_interrupting_replay(self):
        self.sim.command('/mission Apollo 11 1 minute')
        replay=self.sim.mission
        self.run_item('Settings','Themes','Amber')
        self.assertTrue(self.nav.opened)
        self.assertEqual(Settings(self.root/'settings.json').theme,'amber')
        self.run_item('Settings','Screensavers','Saturn')
        self.assertTrue(self.nav.opened)
        self.assertEqual(Settings(self.root/'settings.json').screensaver,'saturn')
        self.run_item('Settings','Camera zoom','Wide')
        self.assertFalse(self.nav.opened)
        self.assertEqual(self.sim.camera.name,'wide')
        self.assertIs(self.sim.mission,replay)
        self.assertFalse(self.sim.paused)

    def test_mission_durations_controls_and_rejected_speed_changes(self):
        self.run_item('Missions','Apollo 11','Replay in 30 seconds')
        self.assertEqual(self.sim.mission.flight,find_flight('Apollo 11'))
        self.assertEqual(self.sim.mission.duration,30)
        replay=self.sim.mission
        item=self.choose('Clock','10 days per second')
        self.assertIn('Could not run command',self.nav.execute(item,self.sim))
        self.assertTrue(self.nav.opened)
        self.assertIs(self.sim.mission,replay)
        self.run_item('Missions','Resume replay')
        self.assertFalse(self.sim.paused)
        self.run_item('Missions','Stop replay')
        self.assertIsNone(self.sim.mission)
        self.assertTrue(self.sim.paused)

    def test_live_selection_tracks_id_after_feed_changes(self):
        first,second=launch('one','First launch'),launch('two','Second launch')
        with patch.object(self.sim.launches,'snapshot',return_value=((first,second),None,None,None)):
            item=self.choose('Live','Second launch')
        with patch.object(self.sim.launches,'snapshot',return_value=((second,first),None,None,None)):
            self.nav.execute(item,self.sim)
        self.assertEqual(self.sim.live_selection,'two')
        self.assertEqual(self.sim.overlay,'live')
        self.nav.opened=True
        with patch.object(self.sim.launches,'snapshot',return_value=((),None,None,None)):
            self.assertIn('no longer',self.nav.execute(item,self.sim))
        self.assertTrue(self.nav.opened)
        self.assertEqual(self.sim.live_selection,'two')

    def test_empty_catalogue_and_clock_prompt_are_safe(self):
        with patch.object(Simulation,'visible_bodies',new_callable=PropertyMock,return_value=[]):
            self.choose('Moons')
            self.nav.move(100,self.sim)
            self.assertIsNone(self.nav.activate(self.sim))
        item=self.choose('Clock','Set exact date/time...')
        before=self.sim.date
        self.assertEqual(item.prompt,'/time ')
        self.assertEqual(self.sim.date,before)


class TUIArrowTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.sim=Simulation(settings_path=self.root/'settings.json',launch_cache_path=self.root/'launch.json')
        self.sim.paused=True
        clock=patch('engine.time.monotonic',return_value=100.)
        clock.start();self.addCleanup(clock.stop)

    def run_keys(self,keys):
        curses=SimpleNamespace(error=type('CursesError',(Exception,),{}),A_BOLD=1,A_DIM=2,A_REVERSE=4,
                               KEY_ENTER=343,KEY_BACKSPACE=263,KEY_DC=330,KEY_F2=266,
                               KEY_LEFT=260,KEY_RIGHT=261,KEY_UP=259,KEY_DOWN=258,
                               KEY_HOME=262,KEY_END=360,KEY_PPAGE=339,KEY_NPAGE=338,
                               set_escdelay=Mock(),curs_set=Mock(),doupdate=Mock())
        screen=Mock();screen.getmaxyx.return_value=(36,110)
        screen.get_wch.side_effect=[*keys,'\x04']
        previews=[]
        with patch.dict('sys.modules',{'curses':curses}),patch('solar_sim.show_screensaver',side_effect=lambda *args:previews.append(self.sim.settings.screensaver)):
            tui(screen,self.sim,no_color=True)
        return previews,screen

    def test_mods_command_immediately_focuses_management_arrows(self):
        import shutil
        self.sim.mods_path=self.root/'mods';self.sim.mods_path.mkdir()
        source=Path(__file__).resolve().parent/'mod_catalogue/interstellar.json'
        shutil.copyfile(source,self.sim.mods_path/'interstellar.json')
        self.run_keys([*'/mods\r','\r',258,'\r','\r',258,'\r'])
        # Enter mod -> down to Turn off -> Enter -> Enter turns on -> down -> uninstall.
        self.assertFalse((self.sim.mods_path/'interstellar.json').exists())
        self.assertFalse(self.sim.mod_mode)

    def test_builder_forms_use_arrows_for_editing_and_keep_invalid_values_open(self):
        self.sim.mods_path=self.root/'mods'
        self.sim.command('/builder new "Form system"')
        self.sim.command('/builder add star Sol')
        self.sim.command('/builder add planet Terra')
        # Home: details, notes, Sol, Terra. Radius is field 4 in a planet form.
        self.run_keys([*'/builder\r',258,258,258,'\r',258,258,258,258,'\r',
                       *'7000',260,261,'\r','\x1b'])
        self.assertEqual(self.sim.builder.body(2)['radius'],7000)
        self.assertEqual(self.sim.camera.name,'system')
        self.sim.running=True
        self.run_keys([*'/builder\r',258,258,258,'\r',258,258,258,258,'\r',
                       *'-5','\r','\x1b'])
        self.assertEqual(self.sim.builder.body(2)['radius'],7000)

    def test_settings_arrows_select_and_preview_saver_then_apply_theme_without_zoom(self):
        self.sim.command('/orbit jupiter')
        previews,_=self.run_keys([*'/setting\r',258,'\r',258,258,'\r',
                                 '\x1b',259,'\r',258,'\r',260,261])
        self.assertEqual(previews,['saturn'])
        self.assertEqual(self.sim.settings.screensaver,'saturn')
        self.assertEqual(Settings(self.root/'settings.json').theme,'amber')
        self.assertEqual(self.sim.camera.index,0)
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.view,'jupiter')

    def test_up_down_browse_instead_of_recalling_history(self):
        self.run_keys([*'/help\r',258,'\r'])
        self.assertEqual(self.sim.screen,'orbit')
        self.assertEqual(self.sim.camera.index,0)

    def test_orbit_arrows_zoom_but_editing_a_command_does_not(self):
        self.sim.command('/orbit jupiter')
        self.run_keys([261,*'/time 1969/12/03',260,261,'\r'])
        self.assertEqual(self.sim.camera.name,'close')
        self.assertEqual(self.sim.date.strftime('%Y-%m-%d'),'1969-12-03')

    def test_mission_arrows_open_navigation_and_cancel_without_changing_camera_or_replay(self):
        self.sim.command('/mission Apollo 11 1 minute')
        replay=self.sim.mission
        self.run_keys([260,261,'\x1b'])
        self.assertIs(self.sim.mission,replay)
        self.assertFalse(self.sim.paused)
        self.assertEqual(self.sim.camera.index,0)

    def test_direct_saver_command_opens_focused_picker_and_ctrl_p_recalls_history(self):
        self.sim.command('/mission Apollo 11 1 minute')
        replay=self.sim.mission
        previews,_=self.run_keys([*'/setting screensaver black-hole\r','\r','\x10','\r'])
        self.assertEqual(previews,['black-hole'])
        self.assertIs(self.sim.mission,replay)
        self.assertFalse(self.sim.paused)
        self.assertEqual(self.sim.camera.index,0)

    def test_numeric_settings_shortcuts_and_a_bare_slash_still_work(self):
        previews,_=self.run_keys([*'/setting\r',*'13\r','\r','\x1b','\x1b',*'/\r'])
        self.assertEqual(previews,['jupiter'])
        self.assertEqual(Settings(self.root/'settings.json').screensaver,'jupiter')


if __name__=='__main__':
    unittest.main()
