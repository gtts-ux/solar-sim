"""Windows transport buffering and key semantics without changing shared app code."""
import unittest
import windows_console as console


class FakeConsole:
    def __init__(self):self.shape=(25,80);self.writes=[]
    def size(self):return self.shape
    def write(self,text):self.writes.append(text)
    def read(self,timeout):self.timeout=timeout;return console.KEY_RIGHT


class WindowsConsoleTests(unittest.TestCase):
    def test_physical_keys_and_control_commands_keep_shared_ui_semantics(self):
        for vk,expected in ((0x25,console.KEY_LEFT),(0x27,console.KEY_RIGHT),
                            (0x26,console.KEY_UP),(0x28,console.KEY_DOWN),(0x71,console.KEY_F2)):
            self.assertEqual(console.decode_key(vk,'\0'),expected)
        self.assertEqual(console.decode_key(0x44,'\x04',8),'\x04')
        self.assertEqual(console.decode_key(0x50,'\0',8),'\x10')
        self.assertEqual(console.decode_key(0x41,'a'),'a')
        self.assertEqual(console.decode_key(0x0d,'\r'),'\r')
        self.assertIsNone(console.decode_key(0x10,'\0'))

    def test_unicode_frames_use_changed_runs_in_one_write_and_resize_clears_old_cells(self):
        io=FakeConsole();screen=console.Screen(io)
        screen.addstr(2,3,'Earth ⊕ ⣿',console.color_pair(4)|console.A_BOLD)
        screen.flush();first=io.writes[-1]
        self.assertIn('Earth ⊕ ⣿',first)
        self.assertIn('\x1b[3;4H',first)
        screen.erase();screen.addstr(2,3,'Earth ⊕ ⣿',console.color_pair(4)|console.A_BOLD)
        screen.flush()
        self.assertNotIn('Earth',io.writes[-1])
        screen.addstr(2,11,'⠿',console.color_pair(4)|console.A_BOLD);screen.flush()
        self.assertIn('⠿',io.writes[-1]);self.assertNotIn('Earth',io.writes[-1])
        io.shape=(22,64);screen.erase();screen.flush()
        self.assertEqual(screen.getmaxyx(),(22,64));self.assertIn('\x1b[2J',io.writes[-1])
        self.assertEqual(len(io.writes),4)

    def test_screensaver_background_and_cursor_are_restored_by_the_shared_api(self):
        io=FakeConsole();screen=console.Screen(io)
        original=screen.getbkgd();screen.bkgd(' ',console.color_pair(9))
        screen.erase();self.assertEqual(screen.rows[0][0],(' ',9))
        screen.leaveok(True);screen.visibility=0;screen.flush()
        self.assertTrue(io.writes[-1].endswith('\x1b[?25l'))
        screen.bkgd(original);screen.leaveok(False);screen.move(4,10);screen.flush()
        self.assertIn('\x1b[5;11H',io.writes[-1])
        screen.timeout(33);self.assertEqual(screen.get_wch(),console.KEY_RIGHT)
        self.assertEqual(io.timeout,33)

    def test_colors_use_the_same_256_color_palette_and_highlight_flags(self):
        console.init_pair(4,141,0)
        style=console.style_codes(console.color_pair(4)|console.A_BOLD|console.A_REVERSE)
        self.assertIn(';38;5;141;',style);self.assertIn(';48;5;0m',style)
        self.assertIn(';1;',style);self.assertIn(';7;',style)


if __name__=='__main__':unittest.main()
