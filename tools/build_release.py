#!/usr/bin/env python3
"""Build a clean portable source ZIP using only Python's standard library."""
import argparse
import hashlib
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Explicit manifests prevent cache, credentials, exports or unrelated files leaking into releases.
FILES = (
    'START_HERE.txt', 'README.md', 'README.txt', 'GITHUB_SETUP.md', 'SOURCES.txt', 'VERSION.txt',
    'Start Solar Sim.command', 'Start Solar Sim.sh', 'Start Solar Sim.bat',
    'solar_sim.py', 'engine.py', 'catalog.py', 'ephemeris.py', 'missions.py',
    'day_lengths.py', 'flight_replay.py', 'screensaver.py',
    'test_solar_sim.py', 'test_screensaver.py', 'test_distribution.py',
    '.gitignore', '.gitattributes', 'tools/build_release.py',
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
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as package:
        for name in files:
            info=zipfile.ZipInfo('solar-sim/'+name, date_time=(2026,1,1,0,0,0))
            info.create_system=3
            mode=0o755 if name.endswith(('.command','.sh')) else 0o644
            info.external_attr=(stat.S_IFREG|mode)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            package.writestr(info,(ROOT/name).read_bytes())
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
