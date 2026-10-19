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
        (self.root/'windows_console.py').write_text('# bundled interface\n')

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

    def test_windows_launch_never_bootstraps_for_maintenance_or_explicit_plain_input(self):
        for arguments in (['--plain'],['-u'],['--update'],['-mproxima centauri'],['-m','user/repo'],
                          ['--command=/mods'],['-c/planet'],['--mod-template','solar-mod.json'],['--version'],['--tutorial']):
            with self.subTest(arguments=arguments),patch('install_commands.sys.stdin') as stdin,patch('install_commands.sys.stdout') as stdout,patch.object(installer,'prepare_windows_runtime') as runtime,patch('subprocess.call',return_value=7) as call:
                stdin.isatty.return_value=True;stdout.isatty.return_value=True
                self.assertEqual(installer.windows_launch(self.root,arguments),7)
                runtime.assert_not_called()
                self.assertEqual(call.call_args.args[0][-len(arguments):],arguments)
    def test_interactive_launch_uses_native_ui_even_with_piped_stdio_and_dumb_term(self):
        args=['--offline','--no-color']
        with patch('install_commands.sys.stdin') as stdin,patch('install_commands.sys.stdout') as stdout,patch.dict(os.environ,{'TERM':'dumb'}),patch.object(installer,'prepare_windows_runtime') as runtime,patch('subprocess.call',return_value=0) as call:
            stdin.isatty.return_value=False;stdout.isatty.return_value=False
            installer.windows_launch(self.root,args)
            runtime.assert_called_once_with(self.root)
            self.assertEqual(call.call_args.args[0],[sys.executable,'-B',str(self.root/'install_commands.py'),'--run-windows-ui',*args])
            self.assertEqual(call.call_args.kwargs['env']['TERM'],'xterm-256color')
            self.assertEqual(call.call_args.kwargs['env']['PYTHONUTF8'],'1')
            self.assertEqual(call.call_args.kwargs['env']['PYTHONIOENCODING'],'utf-8')

    def test_missing_interface_reports_error_instead_of_silently_opening_old_text_mode(self):
        with patch('install_commands.sys.stderr'),patch.object(installer,'prepare_windows_runtime',side_effect=RuntimeError('missing interface')),patch('subprocess.call') as call:
            self.assertEqual(installer.windows_launch(self.root,['--offline']),1)
            call.assert_not_called()

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

    def test_windows_interface_is_bundled_and_never_downloads_a_python_wheel(self):
        with patch('subprocess.run') as download:
            self.assertEqual(installer.prepare_windows_runtime(self.root,allow_download=False),Path(sys.executable))
            download.assert_not_called()
        (self.root/'windows_console.py').unlink()
        with self.assertRaises(RuntimeError):installer.prepare_windows_runtime(self.root)


@unittest.skipUnless(os.name=='nt','Real Windows .bat, .cmd and native console checks run on the Windows CI runner.')
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
        self.assertEqual(python,Path(sys.executable))
        self.assertEqual(installer.prepare_windows_runtime(self.root,allow_download=False),python)
        result_path=self.root.parent/'console-result.json'
        worker=self.root.parent/'console_probe.py'
        worker.write_text(WINDOWS_CONSOLE_PROBE,encoding='utf-8')
        process=subprocess.Popen([str(python),str(worker),str(self.root),str(result_path)],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
        try:code=process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            process.kill();process.wait();self.fail('Windows full-screen console did not exit.')
        self.assertTrue(result_path.exists(),'The Windows console probe did not write its result.')
        result=json.loads(result_path.read_text(encoding='utf-8'))
        self.assertEqual(code,0,result)
        self.assertEqual(result,{'ok':True})


WINDOWS_CONSOLE_PROBE=r'''
import ctypes as ct,json,os,subprocess,sys,time,traceback
from ctypes import wintypes as wt
from pathlib import Path
root=Path(sys.argv[1]);result=Path(sys.argv[2]);process=None
try:
    api=ct.WinDLL('kernel32',use_last_error=True)
    class Coord(ct.Structure):_fields_=[('X',ct.c_short),('Y',ct.c_short)]
    class Rect(ct.Structure):_fields_=[('Left',ct.c_short),('Top',ct.c_short),('Right',ct.c_short),('Bottom',ct.c_short)]
    class Info(ct.Structure):
        _fields_=[('size',Coord),('cursor',Coord),('attributes',wt.WORD),('window',Rect),('maximum',Coord)]
    class Character(ct.Union):_fields_=[('wide',wt.WCHAR),('ascii',ct.c_char)]
    class Key(ct.Structure):
        _fields_=[('down',wt.BOOL),('repeat',wt.WORD),('virtual',wt.WORD),('scan',wt.WORD),('character',Character),('control',wt.DWORD)]
    class Event(ct.Union):_fields_=[('key',Key),('padding',ct.c_byte*16)]
    class Input(ct.Structure):_fields_=[('type',wt.WORD),('event',Event)]
    api.CreateFileW.argtypes=[wt.LPCWSTR,wt.DWORD,wt.DWORD,ct.c_void_p,wt.DWORD,wt.DWORD,wt.HANDLE]
    api.CreateFileW.restype=wt.HANDLE
    api.CloseHandle.argtypes=[wt.HANDLE]
    api.GetConsoleScreenBufferInfo.argtypes=[wt.HANDLE,ct.POINTER(Info)]
    api.ReadConsoleOutputCharacterW.argtypes=[wt.HANDLE,wt.LPWSTR,wt.DWORD,Coord,ct.POINTER(wt.DWORD)]
    api.WriteConsoleInputW.argtypes=[wt.HANDLE,ct.POINTER(Input),wt.DWORD,ct.POINTER(wt.DWORD)]
    input_handle=api.CreateFileW('CONIN$',0xc0000000,3,None,3,0,None)
    def snapshot():
        handle=api.CreateFileW('CONOUT$',0xc0000000,3,None,3,0,None)
        try:
            info=Info()
            if not api.GetConsoleScreenBufferInfo(handle,ct.byref(info)):return ''
            width=info.size.X;height=info.window.Bottom-info.window.Top+1
            buffer=ct.create_unicode_buffer(width*height+1);read=wt.DWORD()
            if not api.ReadConsoleOutputCharacterW(handle,buffer,width*height,Coord(0,info.window.Top),ct.byref(read)):return ''
            return '\n'.join(buffer.value[y*width+info.window.Left:y*width+info.window.Right+1] for y in range(height))
        finally:api.CloseHandle(handle)
    def send(text='',virtual=0):
        chars=list(text) if text else ['\0']
        records=(Input*(len(chars)*2))()
        for index,character in enumerate(chars):
            code=virtual or (0x0d if character=='\r' else ord(character.upper()) if character.isascii() and character.isalpha() else 0)
            for up,down in enumerate((True,False)):
                item=records[index*2+up];item.type=1
                item.event.key=Key(down,1,code,0,Character(character),0x100 if virtual else 0)
        count=wt.DWORD()
        assert api.WriteConsoleInputW(input_handle,records,len(records),ct.byref(count)),ct.get_last_error()
    def expect(text,timeout=12):
        end=time.monotonic()+timeout;last=''
        while time.monotonic()<end:
            last=snapshot()
            if text in last:return last
            if process.poll() is not None:break
            time.sleep(.06)
        raise AssertionError('Expected '+repr(text)+'; screen:\n'+last)
    def saver():
        end=time.monotonic()+12;last=''
        while time.monotonic()<end:
            last=snapshot()
            if sum(0x2800<ord(c)<=0x28ff for c in last)>25 and 'SOLAR' not in last:return last
            time.sleep(.06)
        raise AssertionError('Screensaver did not draw a full-screen frame:\n'+last)
    mods=root/'mods';mods.mkdir()
    (mods/'aurora-system.json').write_bytes((root/'solar-mod.json').read_bytes())
    # Actual .bat -> installer -> app main -> native console -> shared macOS UI.
    # Pipes and inherited TERM=dumb reproduce paths previously dropping to text mode.
    env=os.environ.copy();env['TERM']='dumb'
    command='"'+os.environ.get('COMSPEC','cmd.exe')+'" /d /s /c "'+subprocess.list2cmdline([str(root/'Start Solar Sim.bat'),'--offline'])+'"'
    process=subprocess.Popen(command,cwd=root.parent,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    expect('WELCOME TO YOUR OBSERVATORY');expect('TERMINAL OBSERVATORY')
    send('/setting\r');expect('ARROW NAVIGATION')
    send(virtual=0x28);send('\r');expect('SCREENSAVERS')
    send(virtual=0x28);send('\r');first=saver()
    time.sleep(.6);second=saver();assert first!=second,'Earth screensaver did not animate'
    assert json.loads((root/'settings.json').read_text())['screensaver']=='earth'
    send('\r');expect('ARROW NAVIGATION');send(virtual=0x71)
    send('/orbit jupiter\r');expect('ORBIT / JUPITER')
    send(virtual=0x27);expect('Close / 10 km')
    send(virtual=0x28);expect('ARROW NAVIGATION');send(virtual=0x71)
    send('/back\r');expect('OVERVIEW')
    send('/setting screensaver moon-view\r');saver();send('\r');expect('ARROW NAVIGATION')
    send(virtual=0x71)
    send('/mission Apollo 11 30 seconds\r');expect('MISSION / APOLLO 11')
    send('/mission pause\r');expect('PAUSED')
    send('/mods\r');expect('ARROW NAVIGATION');send('\r');expect('Open system')
    send('\r');expect('AURORA SYSTEM / COMMUNITY SYSTEM')
    send('/orbit Azure\r');expect('ORBIT / AZURE')
    send('/mods\r');expect('ARROW NAVIGATION');send('\r');expect('Turn off')
    send(virtual=0x28);send('\r');expect('Applied: Turn off')
    send('\r');expect('Applied: Turn on')
    send(virtual=0x28);send('\r');expect('Applied: Uninstall')
    assert not (mods/'aurora-system.json').exists()
    assert json.loads((root/'settings.json').read_text())['screensaver']=='moon-view'
    send(virtual=0x71);send('\x04')
    out,err=process.communicate(timeout=15)
    assert process.returncode==0,(out.decode('utf-8','replace'),err.decode('utf-8','replace'))
    api.CloseHandle(input_handle)
    result.write_text(json.dumps({'ok':True}),encoding='utf-8')
except BaseException:
    failure=traceback.format_exc()
    if process is not None:
        process.kill()
        try:
            out,err=process.communicate(timeout=5)
            failure+='\nChild output:\n'+out.decode('utf-8','replace')+'\n'+err.decode('utf-8','replace')
        except BaseException:pass
    result.write_text(json.dumps({'error':failure}),encoding='utf-8')
    sys.exit(1)
'''


if __name__=='__main__':unittest.main()
