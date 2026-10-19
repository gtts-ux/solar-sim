#!/usr/bin/env python3
"""Install solar-sim and sol-sim for the current user on Windows, macOS or Linux."""
import argparse
import os
from pathlib import Path
import shlex
import sys

ROOT=Path(__file__).resolve().parent
NAMES=('solar-sim','sol-sim')
MARKER='# Installed by Solar Sim terminal command installer.'
WINDOWS=sys.platform=='win32'
WINDOWS_MARKER='rem Installed by Solar Sim Windows command installer.'


def prepare_windows_runtime(root,allow_download=True):
    """Validate the bundled Windows console backend; no pip or wheel required."""
    if not (Path(root)/'windows_console.py').is_file():
        raise RuntimeError('The Windows interface file is missing. Extract the entire current Solar Sim ZIP and reinstall commands from that folder.')
    return Path(sys.executable)


def windows_launch(root,arguments):
    """Maintenance uses the ordinary CLI; interactive launch uses native Windows UI."""
    import subprocess
    root=Path(root);arguments=list(arguments)
    actions=('--plain','--help','-h','--version','--tutorial','--mod-tutorial','--update','-u',
             '--mod','-m','--mod-template','--check-mod','--command','-c')
    maintenance=any(arg in actions or arg.startswith(('--command=','--mod=','--mod-template=','--check-mod='))
                    or (arg.startswith(('-c','-m')) and not arg.startswith('--')) for arg in arguments)
    environment=os.environ.copy()
    environment['TERM']='xterm-256color'
    environment['PYTHONUTF8']='1';environment['PYTHONIOENCODING']='utf-8'
    if maintenance:
        command=[sys.executable,'-B',str(root/'solar_sim.py'),*arguments]
    else:
        try:prepare_windows_runtime(root)
        except RuntimeError as failure:
            print(str(failure),file=sys.stderr)
            return 1
        command=[sys.executable,'-B',str(root/'install_commands.py'),'--run-windows-ui',*arguments]
    return subprocess.call(command,env=environment)


def windows_wrapper(root):
    # %% is a literal percent in a batch file; delayed expansion must stay off.
    launcher=str(Path(root)/'Start Solar Sim.bat').replace('%','%%')
    return ('@echo off\nsetlocal DisableDelayedExpansion\n'+WINDOWS_MARKER+'\n'
            'chcp 65001 >nul\n'
            f'if not exist "{launcher}" (\n'
            '    echo Solar Sim folder moved. Run the command installer from its new folder. 1>&2\n'
            '    exit /b 1\n)\n'
            # Tail-call without CALL: a second expansion would corrupt quoted arguments.
            f'"{launcher}" %*\n')


def windows_add_path(bin_dir):
    """Append only to the current user's PATH, preserving its type and contents."""
    import winreg
    import ntpath
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,'Environment',0,winreg.KEY_QUERY_VALUE|winreg.KEY_SET_VALUE) as key:
        try:previous,kind=winreg.QueryValueEx(key,'Path')
        except FileNotFoundError:previous,kind='',winreg.REG_EXPAND_SZ
        normalize=lambda value:ntpath.normcase(ntpath.normpath(ntpath.expandvars(value.strip().strip('"'))))
        if normalize(str(bin_dir)) not in [normalize(p) for p in previous.split(';') if p.strip()]:
            separator='' if not previous or previous.endswith(';') else ';'
            winreg.SetValueEx(key,'Path',0,kind,previous+separator+str(bin_dir))
    # Let Explorer/new terminals inherit the change; existing shells retain their PATH.
    try:
        import ctypes
        from ctypes import wintypes
        send=ctypes.windll.user32.SendMessageTimeoutW
        send.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,ctypes.c_wchar_p,
                       wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t)]
        send.restype=ctypes.c_ssize_t
        send(0xffff,0x1a,0,'Environment',2,2000,None)
    except (AttributeError,OSError):pass


def install_windows(root,bin_dir,*,add_path=True,setup_runtime=True):
    root=Path(root).expanduser().resolve();bin_dir=Path(bin_dir).expanduser().resolve()
    if not (root/'solar_sim.py').is_file() or not (root/'Start Solar Sim.bat').is_file():
        raise FileNotFoundError('Keep the installer with solar_sim.py and Start Solar Sim.bat. Extract the whole ZIP first.')
    destinations=[bin_dir/(name+'.cmd') for name in NAMES]
    for path in destinations:
        if path.is_symlink() or (path.exists() and (not path.is_file() or WINDOWS_MARKER not in path.read_text(encoding='utf-8'))):
            raise FileExistsError(f'Another file already uses {path}; it was left unchanged.')
    bin_dir.mkdir(parents=True,exist_ok=True)
    for path in destinations:
        temporary=path.with_name(path.name+f'.{os.getpid()}.tmp')
        try:
            with temporary.open('w',encoding='utf-8',newline='\r\n') as stream:stream.write(windows_wrapper(root))
            temporary.replace(path)
        finally:temporary.unlink(missing_ok=True)
    if add_path:windows_add_path(bin_dir)
    if setup_runtime:prepare_windows_runtime(root)
    return destinations


def windows_main(argv):
    import subprocess
    parser=argparse.ArgumentParser(description='Install Windows commands and the bundled full-screen interface; no administrator needed.')
    default=Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData'/'Local')/'SolarSim'/'bin'
    parser.add_argument('--bin-dir',type=Path,default=default,help='Folder for solar-sim.cmd and sol-sim.cmd.')
    parser.add_argument('--no-path',action='store_true',help='Leave the Windows user PATH unchanged.')
    parser.add_argument('--no-runtime',action='store_true',help='Install commands only; skip checking bundled Windows interface files.')
    args=parser.parse_args(argv)
    try:paths=install_windows(ROOT,args.bin_dir,add_path=not args.no_path,setup_runtime=not args.no_runtime)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print('Could not finish Windows setup: '+str(error),file=sys.stderr)
        print('Extract the entire latest ZIP and retry. Start Solar Sim.bat --plain remains available.',file=sys.stderr)
        return 1
    print('Installed: '+', '.join(NAMES))
    print('Windows full-screen interface: bundled / no extra download required')
    print('App folder: '+str(ROOT))
    print('Command folder: '+str(paths[0].parent))
    print('Add the command folder to PATH yourself.' if args.no_path else 'Close all terminal windows and open a new terminal, then type sol-sim or solar-sim.')
    print('Getting started: sol-sim --tutorial   |   Update: sol-sim -u   |   Text fallback: sol-sim --plain')
    return 0


def profile_paths(shell):
    home=Path.home()
    if shell=='zsh':
        directory=Path(os.environ.get('ZDOTDIR') or home).expanduser()
        return [directory/'.zprofile',directory/'.zshrc']
    if shell=='bash':
        # Creating .bash_profile would hide an existing .profile, so use the
        # login file Bash already chooses, plus its interactive startup file.
        login=next((home/n for n in ('.bash_profile','.bash_login') if (home/n).exists()),home/'.profile')
        return [login,home/'.bashrc']
    if shell=='sh':return [home/'.profile']
    raise ValueError('Automatic PATH setup supports zsh, bash and sh. Use --no-path for another shell.')


def path_block(bin_dir):
    quoted=shlex.quote(str(bin_dir))
    return (f'{MARKER}\ncase ":$PATH:" in\n'
            f'    *:{quoted}:*) ;;\n'
            f'    *) export PATH={quoted}:"$PATH" ;;\nesac\n')


def wrapper(root):
    launcher=shlex.quote(str(root/'Start Solar Sim.sh'))
    return (f'#!/bin/sh\n{MARKER}\n'
            f'if [ ! -f {launcher} ]; then\n'
            '    printf \'%s\\n\' "Solar Sim folder moved. Run python3 install_commands.py from its new folder." >&2\n'
            '    exit 1\nfi\n'
            f'exec sh {launcher} "$@"\n')


def install(root,bin_dir,profiles=()):
    root=Path(root).expanduser().resolve()
    bin_dir=Path(bin_dir).expanduser().resolve()
    if not (root/'solar_sim.py').is_file() or not (root/'Start Solar Sim.sh').is_file():
        raise FileNotFoundError('Keep install_commands.py with solar_sim.py and Start Solar Sim.sh.')
    destinations=[bin_dir/name for name in NAMES]
    # Check both names before changing either one. Only replace our own wrappers.
    for path in destinations:
        if path.is_symlink() or (path.exists() and (not path.is_file() or MARKER not in path.read_text(encoding='utf-8'))):
            raise FileExistsError(f'Another file already uses {path}; it was left unchanged.')
    block=path_block(bin_dir)
    updates=[]
    for profile in dict.fromkeys(map(Path,profiles)):
        previous=profile.read_text(encoding='utf-8') if profile.exists() else ''
        if block not in previous:
            updates.append((profile,('' if not previous or previous.endswith('\n') else '\n')+'\n'+block))
    bin_dir.mkdir(parents=True,exist_ok=True)
    content=wrapper(root)
    for path in destinations:
        temporary=path.with_name(path.name+f'.{os.getpid()}.tmp')
        try:
            temporary.write_text(content,encoding='utf-8')
            temporary.chmod(0o755)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    for profile,addition in updates:
        profile.parent.mkdir(parents=True,exist_ok=True)
        # Append through symlinks too, preserving the rest of the shell config.
        with profile.open('a',encoding='utf-8') as stream:stream.write(addition)
    return destinations


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if WINDOWS:
        if argv[:1]==['--launch-windows']:return windows_launch(ROOT,argv[1:])
        if argv[:1]==['--run-windows-ui']:
            from windows_console import run
            return run(ROOT,argv[1:])
        return windows_main(argv)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir',type=Path,default=Path.home()/'.local/bin',help='Command folder (default: ~/.local/bin).')
    parser.add_argument('--shell',default=Path(os.environ.get('SHELL') or ('/bin/zsh' if sys.platform=='darwin' else '/bin/bash')).name,
                        help='Shell for PATH setup: zsh, bash or sh.')
    parser.add_argument('--no-path',action='store_true',help='Install wrappers without editing shell startup files.')
    args=parser.parse_args(argv)
    try:
        profiles=[] if args.no_path else profile_paths(args.shell)
        paths=install(ROOT,args.bin_dir,profiles)
    except (OSError,ValueError) as error:
        print('Could not install terminal commands: '+str(error),file=sys.stderr)
        return 1
    print('Installed: '+', '.join(NAMES))
    print('App folder: '+str(ROOT))
    print('Command folder: '+str(paths[0].parent))
    print('Add the command folder to PATH to use the short names.' if args.no_path else
          'Open a new terminal window, then type solar-sim or sol-sim.')
    print('Getting started: sol-sim --tutorial   |   Update later: sol-sim -u')
    return 0


if __name__=='__main__':raise SystemExit(main())
