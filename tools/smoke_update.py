"""Release-job check: download the just-published assets and upgrade a disposable app."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from updater import LATEST, REPO, fetch_bytes, run_update


def main():
    version=(Path(__file__).resolve().parents[1]/'VERSION.txt').read_text().strip()
    # gh uses the workflow token for metadata, avoiding shared-runner API quotas.
    # ZIP/checksum downloads use the production updater's HTTPS transport.
    metadata=subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/v{version}'])
    def published(url,limit):
        return metadata if url==LATEST else fetch_bytes(url,limit)
    with tempfile.TemporaryDirectory(prefix='solar self-update ') as temp:
        root=Path(temp)/'app with spaces';root.mkdir()
        (root/'VERSION.txt').write_text('0.0.0\n')
        (root/'settings.json').write_text('{"theme":"amber","screensaver":"jupiter"}')
        original=(root/'settings.json').read_bytes()
        backup=run_update(root,fetch=published)
        assert backup is not None
        assert (root/'VERSION.txt').read_text().strip()==version
        assert (root/'settings.json').read_bytes()==original
        result=subprocess.run([sys.executable,str(root/'solar_sim.py'),'--offline','-c','/planet'],capture_output=True,text=True,timeout=20)
        assert result.returncode==0,result.stderr
        assert '/neptune' in result.stdout
        install=subprocess.run([sys.executable,str(root/'solar_sim.py'),'--offline','-mproxima centauri'],capture_output=True,text=True,timeout=20)
        assert install.returncode==0,install.stderr+install.stdout
        result=subprocess.run([sys.executable,str(root/'solar_sim.py'),'--offline','-c','/proxima centari','-c','/orbit','-c','/compare "proxima b" "proxima d"','-c','/proxima exit'],capture_output=True,text=True,timeout=20)
        assert result.returncode==0,result.stderr
        assert 'Could not run command' not in result.stdout,result.stdout
        assert 'Proxima Centauri d' in result.stdout
        installed=(root/'mods/proxima-centauri.json').read_bytes()
        assert run_update(root,fetch=published) is None
        assert (root/'mods/proxima-centauri.json').read_bytes()==installed
    print('Published ZIP/checksum downloaded successfully; upgrade, saved settings, Proxima installation/orbits/comparison and repeat check passed.')


if __name__=='__main__':main()
