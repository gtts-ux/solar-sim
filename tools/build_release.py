#!/usr/bin/env python3
"""Build a clean portable source ZIP using only Python's standard library."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Explicit manifests prevent cache, credentials, exports or unrelated files leaking into releases.
FILES = (
    'START_HERE.txt', 'GETTING_STARTED.txt', 'MODDING.txt', 'solar-mod.json', 'README.md', 'README.txt', 'GITHUB_SETUP.md', 'SOURCES.txt', 'VERSION.txt',
    'Start Solar Sim.command', 'Start Solar Sim.sh', 'Start Solar Sim.bat', 'Install Solar Sim Commands.bat', 'install_commands.py',
    'solar_sim.py', 'windows_console.py', 'updater.py', 'engine.py', 'proxima.py', 'interstellar.py', 'mod_manager.py', 'community_mods.py', 'community_runtime.py', 'mod_builder.py', 'builder_ui.py', 'mod_catalogue/proxima-centauri.json', 'mod_catalogue/interstellar.json', 'navigation.py', 'catalog.py', 'ephemeris.py', 'missions.py',
    'day_lengths.py', 'flight_replay.py', 'screensaver.py', 'screensaver_scenes.py', 'themes.py', 'camera.py', 'live_launches.py',
    'test_solar_sim.py', 'test_screensaver.py', 'test_distribution.py', 'test_controls.py', 'test_commands.py', 'test_windows_console.py', 'test_navigation.py', 'test_updater.py', 'test_mods.py', 'test_interstellar.py', 'test_community_mods.py', 'test_mod_controls.py', 'test_mod_builder.py',
    '.gitignore', '.gitattributes', 'tools/build_release.py', 'tools/smoke_update.py',
    '.github/workflows/checks.yml', '.github/workflows/release.yml',
)


def build(output_dir):
    files=list(FILES)
    if (ROOT/'LICENSE').is_file():
        files.append('LICENSE')
    for name in files:
        if not (ROOT/name).is_file():
            raise FileNotFoundError(f'Required release file missing: {name}')
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    archive=output_dir/'solar-sim.zip'
    manifest={'format':1,'version':(ROOT/'VERSION.txt').read_text().strip(),
              'python_min':[3,10],'files':[*files,'RELEASE_MANIFEST.json']}
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as package:
        for name in manifest['files']:
            info=zipfile.ZipInfo('solar-sim/'+name, date_time=(2026,1,1,0,0,0))
            info.create_system=3
            mode=0o755 if name.endswith(('.command','.sh')) else 0o644
            info.external_attr=(stat.S_IFREG|mode)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            data=(json.dumps(manifest,indent=2)+'\n').encode() if name=='RELEASE_MANIFEST.json' else (ROOT/name).read_bytes()
            package.writestr(info,data)
    checksum=archive.with_suffix('.zip.sha256')
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f'{digest}  {archive.name}\n',encoding='utf-8')
    return archive,checksum


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'dist')
    args=parser.parse_args()
    for path in build(args.output_dir):
        print(path)


if __name__=='__main__':
    main()
