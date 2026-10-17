#!/usr/bin/env python3
"""Install solar-sim and sol-sim for the current macOS/Linux user; no sudo needed."""
import argparse
import os
from pathlib import Path
import shlex
import sys

ROOT=Path(__file__).resolve().parent
NAMES=('solar-sim','sol-sim')
MARKER='# Installed by Solar Sim terminal command installer.'


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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir',type=Path,default=Path.home()/'.local/bin',help='Command folder (default: ~/.local/bin).')
    parser.add_argument('--shell',default=Path(os.environ.get('SHELL') or ('/bin/zsh' if sys.platform=='darwin' else '/bin/bash')).name,
                        help='Shell for PATH setup: zsh, bash or sh.')
    parser.add_argument('--no-path',action='store_true',help='Install wrappers without editing shell startup files.')
    args=parser.parse_args(argv)
    if os.name=='nt':parser.error('Use Start Solar Sim.bat on Windows. This installer is for macOS/Linux.')
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
    return 0


if __name__=='__main__':raise SystemExit(main())
