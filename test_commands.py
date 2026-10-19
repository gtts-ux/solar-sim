"""User-level commands, shell startup integration and safe repeat installation."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys
import json

from install_commands import ROOT, MARKER, NAMES, install, path_block
import install_commands as installer


@unittest.skipIf(os.name=='nt','The command installer targets macOS/Linux shells.')
class TerminalCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.bin=self.root/"user's command folder"
        self.profiles=[self.root/'.zprofile',self.root/'.zshrc']

    def test_both_names_launch_from_another_directory_and_profiles_are_idempotent(self):
        for profile in self.profiles:profile.write_text('# Existing shell settings\n')
        first=install(ROOT,self.bin,self.profiles)
        second=install(ROOT,self.bin,self.profiles)
        self.assertEqual(first,second)
        for profile in self.profiles:
            text=profile.read_text()
            self.assertTrue(text.startswith('# Existing shell settings\n'))
            self.assertEqual(text.count(MARKER),1)
        for name in NAMES:
            result=subprocess.run([str(self.bin/name),'--offline','-c','/planet','-c','/day earth'],
                                  cwd=self.root,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('/neptune',result.stdout)
            self.assertIn('24.00 hours',result.stdout)
            for flag,expected in (('--tutorial','GET STARTED WITH SOL-SIM'),('--version','Solar Sim ')):
                extra=subprocess.run([str(self.bin/name),flag],cwd=self.root,text=True,capture_output=True,timeout=15)
                self.assertEqual(extra.returncode,0,extra.stderr)
                self.assertIn(expected,extra.stdout)
        # Source the generated PATH block in a real POSIX shell, twice.
        result=subprocess.run(['sh','-c','. "$1"; . "$1"; command -v solar-sim; command -v sol-sim',
                               'check',str(self.profiles[0])],cwd=self.root,text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.splitlines(),[str(self.bin.resolve()/n) for n in NAMES])

    def test_spaces_and_shell_metacharacters_in_app_path_and_arguments_are_literal(self):
        app=self.root/"solar sim's $special files"
        app.mkdir();(app/'solar_sim.py').write_text('# fixture\n')
        (app/'Start Solar Sim.sh').write_text('#!/bin/sh\nprintf \'%s\\n\' "$@"\n')
        install(app,self.bin)
        args=['a b','"quoted"','$not_an_environment_variable','`literal`']
        result=subprocess.run([str(self.bin/'sol-sim'),*args],cwd=self.root,text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.splitlines(),args)
        shutil.rmtree(app)
        result=subprocess.run([str(self.bin/'solar-sim')],cwd=self.root,text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,1)
        self.assertIn('folder moved',result.stderr)

    def test_foreign_commands_are_preserved_before_any_installation(self):
        self.bin.mkdir()
        foreign=self.bin/'sol-sim';foreign.write_text('my own command\n')
        with self.assertRaises(FileExistsError):install(ROOT,self.bin,self.profiles)
        self.assertEqual(foreign.read_text(),'my own command\n')
        self.assertFalse((self.bin/'solar-sim').exists())
        self.assertTrue(all(not p.exists() for p in self.profiles))


class WindowsInstallerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/'app with spaces';self.root.mkdir()
        self.bin=self.root.parent/'command folder'
        (self.root/'solar_sim.py').write_text('# app\n')
        (self.root/'Start Solar Sim.bat').write_text('@echo off\n')

    def test_wrappers_repeat_safely_preserve_arguments_and_escape_percent_paths(self):
        app=self.root/'a %PATH% ! planet';app.mkdir()
        for name in ('solar_sim.py','Start Solar Sim.bat'):shutil.copy2(self.root/name,app/name)
        with patch.object(installer,'windows_add_path') as path,patch.object(installer,'prepare_windows_runtime') as runtime:
            first=installer.install_windows(app,self.bin)
            self.assertEqual(first,installer.install_windows(app,self.bin))
        self.assertEqual(path.call_count,2);self.assertEqual(runtime.call_count,2)
        for wrapper in first:
            data=wrapper.read_bytes();text=data.decode('utf-8')
            self.assertTrue(wrapper.name.endswith('.cmd'))
            self.assertIn(installer.WINDOWS_MARKER,text)
            self.assertIn('%%PATH%% ! planet',text)
            self.assertIn('DisableDelayedExpansion',text)
            self.assertIn('" %*',text)
            self.assertNotIn('call ',text.lower())
            self.assertNotIn(b'\n',data.replace(b'\r\n',b''))

    def test_foreign_windows_command_is_preserved_before_setup(self):
        self.bin.mkdir();foreign=self.bin/'sol-sim.cmd';foreign.write_text('keep')
        with patch.object(installer,'prepare_windows_runtime') as runtime:
            with self.assertRaises(FileExistsError):installer.install_windows(self.root,self.bin)
        self.assertEqual(foreign.read_text(),'keep')
        self.assertFalse((self.bin/'solar-sim.cmd').exists());runtime.assert_not_called()

    def test_windows_launch_never_bootstraps_for_maintenance_plain_or_piped_input(self):
        for arguments in (['--plain'],['-u'],['--update'],['-mproxima centauri'],['-m','user/repo'],
                          ['--command=/mods'],['-c/planet'],['--mod-template','solar-mod.json'],['--version'],['--tutorial']):
            with self.subTest(arguments=arguments),patch('install_commands.sys.stdin') as stdin,patch('install_commands.sys.stdout') as stdout,patch.object(installer,'prepare_windows_runtime') as runtime,patch('subprocess.call',return_value=7) as call:
                stdin.isatty.return_value=True;stdout.isatty.return_value=True
                self.assertEqual(installer.windows_launch(self.root,arguments),7)
                runtime.assert_not_called()
                self.assertEqual(call.call_args.args[0][-len(arguments):],arguments)
        with patch('install_commands.sys.stdin') as stdin,patch.object(installer,'prepare_windows_runtime') as runtime,patch('subprocess.call',return_value=0):
            stdin.isatty.return_value=False
            installer.windows_launch(self.root,[]);runtime.assert_not_called()

    def test_interactive_windows_launch_uses_runtime_and_environment_without_forcing_plain(self):
        args=['--offline','--no-color']
        with patch('install_commands.sys.stdin') as stdin,patch('install_commands.sys.stdout') as stdout,patch.object(installer,'prepare_windows_runtime',return_value=Path('runtime.exe')) as runtime,patch('subprocess.call',return_value=0) as call:
            stdin.isatty.return_value=True;stdout.isatty.return_value=True
            installer.windows_launch(self.root,args)
            runtime.assert_called_once_with(self.root,allow_download=False)
            self.assertEqual(call.call_args.args[0],['runtime.exe','-B',str(self.root/'solar_sim.py'),*args])
            self.assertEqual(call.call_args.kwargs['env']['PYTHONUTF8'],'1')
            self.assertEqual(call.call_args.kwargs['env']['PYTHONIOENCODING'],'utf-8')

    def test_failed_windows_runtime_has_usable_plain_fallback(self):
        with patch('install_commands.sys.stdin') as stdin,patch('install_commands.sys.stdout') as stdout,patch('install_commands.sys.stderr'),patch.object(installer,'prepare_windows_runtime',side_effect=RuntimeError('offline')),patch('subprocess.call',return_value=0) as call:
            stdin.isatty.return_value=True;stdout.isatty.return_value=True
            installer.windows_launch(self.root,['--no-color'])
            self.assertEqual(call.call_args.args[0][-2:],['--no-color','--plain'])

    def test_windows_path_preserves_variables_type_and_existing_entries_and_is_idempotent(self):
        key=Mock();key.__enter__=Mock(return_value=key);key.__exit__=Mock(return_value=False)
        data={'value':r'%USERPROFILE%\custom;C:\Existing','kind':2}
        registry=SimpleNamespace(HKEY_CURRENT_USER=1,KEY_QUERY_VALUE=1,KEY_SET_VALUE=2,REG_EXPAND_SZ=2,
                                 CreateKeyEx=Mock(return_value=key),QueryValueEx=lambda *_:(data['value'],data['kind']))
        def save(_,name,reserved,kind,value):data.update(value=value,kind=kind)
        registry.SetValueEx=Mock(side_effect=save)
        with patch.dict('sys.modules',{'winreg':registry}):
            installer.windows_add_path(r'C:\Solar Sim\bin')
            installer.windows_add_path('c:\\solar sim\\BIN\\')
        self.assertEqual(data['value'],r'%USERPROFILE%\custom;C:\Existing;C:\Solar Sim\bin')
        self.assertEqual(data['kind'],2);registry.SetValueEx.assert_called_once()

    def test_runtime_bootstrap_is_private_reusable_and_never_downloads_offline(self):
        python=installer.windows_runtime_path(self.root)
        def bootstrap(command,**kwargs):
            if command[1:3]==['-m','venv']:
                python.parent.mkdir(parents=True);python.write_text('runtime')
            return SimpleNamespace(returncode=0)
        def usable(candidate):return Path(candidate)==python and python.is_file()
        with patch.object(installer,'has_windows_curses',side_effect=usable),patch('subprocess.run',side_effect=bootstrap) as run,patch('builtins.print'):
            with self.assertRaises(RuntimeError):installer.prepare_windows_runtime(self.root,allow_download=False)
            run.assert_not_called()
            self.assertEqual(installer.prepare_windows_runtime(self.root),python)
            self.assertEqual(run.call_count,2)
            self.assertIn(installer.WINDOWS_CURSES,run.call_args.args[0])
            self.assertEqual(installer.prepare_windows_runtime(self.root,allow_download=False),python)
            self.assertEqual(run.call_count,2)


@unittest.skipUnless(os.name=='nt','Real Windows .bat, .cmd and PDCurses checks run on the Windows CI runner.')
class WindowsCommandIntegrationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/'app ! 100% ć with spaces';self.root.mkdir()
        self.bin=self.root.parent/'user commands'
        for path in ROOT.iterdir():
            if path.is_file() and path.suffix in ('.py','.txt','.json','.bat'):shutil.copy2(path,self.root/path.name)
        shutil.copytree(ROOT/'mod_catalogue',self.root/'mod_catalogue')

    def batch(self,path,*arguments):
        # CMD /S /C needs an outer pair of quotes around a quoted executable
        # plus quoted arguments; Python's normal C argv quoting alone is insufficient.
        command='"'+os.environ.get('COMSPEC','cmd.exe')+'" /d /s /c "'+subprocess.list2cmdline([str(path),*arguments])+'"'
        return subprocess.run(command,cwd=self.root.parent,capture_output=True,text=True,encoding='utf-8',timeout=30)

    def test_real_batch_installer_and_both_commands_forward_current_features(self):
        # Keep CI's real registry unchanged; PATH persistence has a separate isolated test.
        for _ in range(2):
            result=self.batch(self.root/'Install Solar Sim Commands.bat','--bin-dir',str(self.bin),'--no-path','--no-runtime')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for name in NAMES:
            wrapper=self.bin/(name+'.cmd')
            result=self.batch(wrapper,'--offline','-c','/mods','-c','/setting screensaver moon-view','-c','/mission Apollo 11 30 seconds')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertNotIn('Could not run command:',result.stdout)
            self.assertIn('MODS / installed catalogues',result.stdout)
            self.assertIn('Moon view',result.stdout);self.assertIn('APOLLO 11',result.stdout)
            result=self.batch(wrapper,'--offline','-mproxima centauri')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('Installed Proxima',result.stdout)
        # A relative authoring destination must use the caller's working directory.
        result=self.batch(self.bin/'sol-sim.cmd','--mod-template','my system.json')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue((self.root.parent/'my system.json').is_file())

    def test_real_windows_runtime_and_full_screen_controls(self):
        python=installer.prepare_windows_runtime(self.root)
        self.assertTrue(installer.has_windows_curses(python))
        self.assertEqual(installer.prepare_windows_runtime(self.root,allow_download=False),python)
        result_path=self.root.parent/'console-result.json'
        worker=self.root.parent/'console_probe.py'
        worker.write_text(WINDOWS_CONSOLE_PROBE,encoding='utf-8')
        process=subprocess.Popen([str(python),str(worker),str(self.root),str(result_path)],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
        try:code=process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.kill();process.wait();self.fail('Windows full-screen console did not exit.')
        self.assertTrue(result_path.exists(),'The Windows console probe did not write its result.')
        result=json.loads(result_path.read_text(encoding='utf-8'))
        self.assertEqual(code,0,result)
        self.assertEqual(result,{'ok':True})


WINDOWS_CONSOLE_PROBE=r'''
import ctypes,json,locale,msvcrt,sys,traceback
from pathlib import Path
root=Path(sys.argv[1]);result=Path(sys.argv[2])
try:
    sys.path.insert(0,str(root))
    sys.stdin=open('CONIN$','r',encoding='utf-8')
    sys.stdout=open('CONOUT$','w',encoding='utf-8')
    sys.stderr=sys.stdout
    kernel=ctypes.windll.kernel32
    kernel.SetStdHandle.argtypes=[ctypes.c_ulong,ctypes.c_void_p]
    for number,stream in ((-10,sys.stdin),(-11,sys.stdout),(-12,sys.stderr)):
        kernel.SetStdHandle(number,msvcrt.get_osfhandle(stream.fileno()))
    locale.setlocale(locale.LC_ALL,'')
    import curses
    from engine import Simulation
    from solar_sim import tui
    mods=root/'mods';mods.mkdir()
    (mods/'aurora-system.json').write_bytes((root/'solar-mod.json').read_bytes())
    sim=Simulation(online=False,mods_path=mods,settings_path=root/'settings.json',launch_cache_path=root/'launch.json')
    sim.paused=True
    keys=[*'/setting screensaver moon-view\r','\r',curses.KEY_F2,
          *'/mission Apollo 11 30 seconds\r',*'/mission pause\r',
          *'/mods\r','\r','\r',*'/orbit Azure\r',curses.KEY_RIGHT,
          *'/mods\r','\r',curses.KEY_DOWN,'\r','\r',curses.KEY_DOWN,'\r',
          curses.KEY_F2,'\x04']
    class ScriptedScreen:
        def __init__(self,screen):self.screen=screen
        def __getattr__(self,name):return getattr(self.screen,name)
        def get_wch(self):
            if not keys:raise AssertionError('Input script ran out before exit')
            return keys.pop(0)
    def probe(screen):
        from ctypes import wintypes as wt
        class Character(ctypes.Union):
            _fields_=[('UnicodeChar',wt.WCHAR),('AsciiChar',ctypes.c_char)]
        class KeyEvent(ctypes.Structure):
            _fields_=[('down',wt.BOOL),('repeat',wt.WORD),('virtual',wt.WORD),
                      ('scan',wt.WORD),('character',Character),('control',wt.DWORD)]
        class Event(ctypes.Union):
            _fields_=[('key',KeyEvent),('padding',ctypes.c_byte*16)]
        class Input(ctypes.Structure):
            _fields_=[('type',wt.WORD),('event',Event)]
        kernel.CreateFileW.argtypes=[wt.LPCWSTR,wt.DWORD,wt.DWORD,ctypes.c_void_p,wt.DWORD,wt.DWORD,wt.HANDLE]
        kernel.CreateFileW.restype=wt.HANDLE
        handle=kernel.CreateFileW('CONIN$',0xc0000000,3,None,3,0,None)
        kernel.WriteConsoleInputW.argtypes=[wt.HANDLE,ctypes.POINTER(Input),wt.DWORD,ctypes.POINTER(wt.DWORD)]
        kernel.CloseHandle.argtypes=[wt.HANDLE]
        screen.keypad(True)
        screen.timeout(1000)
        try:
            # PDCurses ungetch(int) is a Unicode pushback, so inject genuine
            # Windows console arrow events to test the actual keyboard path.
            for key,virtual in ((curses.KEY_LEFT,0x25),(curses.KEY_RIGHT,0x27),
                                (curses.KEY_UP,0x26),(curses.KEY_DOWN,0x28)):
                curses.flushinp()
                records=(Input*2)()
                for index,down in enumerate((True,False)):
                    records[index].type=1
                    records[index].event.key=KeyEvent(down,1,virtual,0,Character(),0x100)
                written=wt.DWORD()
                assert kernel.WriteConsoleInputW(handle,records,2,ctypes.byref(written)),kernel.GetLastError()
                observed=screen.get_wch()
                while observed==curses.KEY_RESIZE:observed=screen.get_wch()
                assert observed==key,repr((key,observed,type(observed).__name__))
        finally:kernel.CloseHandle(handle)
        screen.addstr(2,2,'Earth ⊕ • ⣿');screen.refresh()
        tui(ScriptedScreen(screen),sim)
    curses.wrapper(probe)
    assert not keys,repr(keys)
    assert sim.settings.screensaver=='moon-view'
    assert not (mods/'aurora-system.json').exists()
    assert not sim.mod_mode and sim.selected.name=='Earth'
    assert sim.mission is None
    result.write_text(json.dumps({'ok':True}),encoding='utf-8')
except BaseException:
    result.write_text(json.dumps({'error':traceback.format_exc()}),encoding='utf-8')
    sys.exit(1)
'''


if __name__=='__main__':unittest.main()
