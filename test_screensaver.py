"""Galaxy rendering and safe return from full-screen animation."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from screensaver import Galaxy, PALETTE, show_screensaver


class GalaxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.galaxy=Galaxy()

    def test_frames_fit_resizes_and_include_cool_arms_and_warm_core(self):
        for width,height in ((1,1),(20,8),(64,22),(120,40),(200,60)):
            frame=self.galaxy.frame(width,height,12)
            self.assertEqual(len(frame),height)
            self.assertTrue(all(len(row)==width for row in frame))
            self.assertTrue(all(0<=color<len(PALETTE) for row in frame for _,color,_ in row))
        self.assertEqual(self.galaxy.frame(0,20,1),[])
        self.assertEqual(self.galaxy.frame(20,0,1),[])
        frame=self.galaxy.frame(120,40,12)
        families={color//8 for row in frame for char,color,_ in row if char!=' '}
        self.assertEqual(families,{0,1,2,3})
        text=''.join(char for row in frame for char,_,_ in row)
        self.assertTrue(any(0x2800<ord(char)<=0x28ff for char in text))
        self.assertNotIn('SOLAR',text)
        self.assertNotIn('Enter',text)

    def test_rotation_is_time_based_and_does_not_randomize_between_frames(self):
        first=self.galaxy.frame(100,32,8)
        neighbor=self.galaxy.frame(100,32,8+1/30)
        later=self.galaxy.frame(100,32,15)
        self.galaxy.frame(64,22,9)
        self.assertEqual(first,self.galaxy.frame(100,32,8))
        self.assertEqual(first,Galaxy().frame(100,32,8))
        changes=lambda frame:sum(a!=b for row,other in zip(first,frame) for a,b in zip(row,other))
        self.assertGreater(changes(neighbor),0)
        self.assertLess(changes(neighbor),changes(later))

    def test_grouped_draw_runs_reconstruct_the_exact_frame(self):
        expected=self.galaxy.frame(80,24,3)
        reconstructed=[[(' ',24,False) for _ in range(80)] for _ in range(24)]
        for y,x,text,color,bold in self.galaxy.runs(80,24,3):
            self.assertLessEqual(x+len(text),80)
            for offset,char in enumerate(text):
                reconstructed[y][x+offset]=(char,color,bold)
        self.assertEqual(reconstructed,expected)


class ScreensaverStateTests(unittest.TestCase):
    def run_saver(self,keys,paused=False,colors=False,color_count=256,draw_error=None):
        error=type('CursesError',(Exception,),{})
        curses=SimpleNamespace(error=error,COLORS=color_count,COLOR_PAIRS=256,
                               COLOR_BLACK=0,KEY_ENTER=343,A_BOLD=1,A_DIM=2,
                               init_pair=Mock(),color_pair=lambda color:color<<8,
                               curs_set=Mock(),doupdate=Mock())
        screen=Mock()
        screen.getmaxyx.return_value=(24,80)
        screen.getbkgd.return_value=987
        if draw_error:
            screen.addstr.side_effect=draw_error
        sim=SimpleNamespace(paused=paused,running=True,last_tick=0,tick=Mock(),
                            screen='mission',mission=object(),selected=object())
        key_iterator=iter(keys)
        def next_key():
            self.assertTrue(sim.paused)
            return next(key_iterator)
        screen.get_wch.side_effect=next_key
        original=(sim.screen,sim.mission,sim.selected)
        self.addCleanup(lambda:self.assertEqual((sim.screen,sim.mission,sim.selected),original))
        with patch.dict('sys.modules',{'curses':curses}),patch('screensaver.time.monotonic',return_value=100),patch('screensaver.Galaxy') as galaxy:
            galaxy.return_value.runs.return_value=[(2,4,'⣿⣤',18,False)]
            if draw_error:
                with self.assertRaises(RuntimeError):
                    show_screensaver(screen,sim,colors)
            else:
                show_screensaver(screen,sim,colors)
        self.assertEqual(sim.paused,paused)
        self.assertEqual(sim.last_tick,100)
        sim.tick.assert_called_once()
        screen.timeout.assert_called_with(60)
        screen.leaveok.assert_called_with(False)
        screen.bkgd.assert_called_with(987)
        return sim,screen,curses

    def test_enter_and_escape_return_without_changing_view_or_pause(self):
        for key in ('\r','\n',343,'\x1b'):
            for paused in (True,False):
                with self.subTest(key=key,paused=paused):
                    sim,_,_=self.run_saver(['x',key],paused)
                    self.assertTrue(sim.running)

    def test_control_c_and_d_exit_without_leaking_terminal_settings(self):
        for key in ('\x03','\x04'):
            sim,_,_=self.run_saver([key])
            self.assertFalse(sim.running)

    def test_extended_eight_color_and_monochrome_modes(self):
        for colors,count,expected in ((True,256,32),(True,8,0),(False,256,0)):
            _,screen,curses=self.run_saver(['\r'],colors=colors,color_count=count)
            self.assertEqual(curses.init_pair.call_count,expected)
            screen.addstr.assert_called_once()

    def test_unexpected_draw_failure_restores_clock_and_terminal(self):
        self.run_saver(['\r'],draw_error=RuntimeError('draw failed'))


if __name__=='__main__':
    unittest.main()
