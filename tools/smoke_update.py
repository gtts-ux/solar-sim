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
        install=subprocess.run([sys.executable,str(root/'solar_sim.py'),'--offline','-minterstellar'],capture_output=True,text=True,timeout=20)
        assert install.returncode==0,install.stderr+install.stdout
        result=subprocess.run([sys.executable,str(root/'solar_sim.py'),'--offline','-c','/interstellar','-c','/orbit','-c','/mann','-c','/compare miller mann','-c','/proxima centari','-c','/interstellar','-c','/interstellar exit'],capture_output=True,text=True,timeout=20)
        assert result.returncode==0,result.stderr
        assert 'Could not run command' not in result.stdout,result.stdout
        assert 'FICTIONAL MODEL' in result.stdout
        film=(root/'mods/interstellar.json').read_bytes()
        def app_command(*args):
            result=subprocess.run([sys.executable,str(root/'solar_sim.py'),*args],capture_output=True,text=True,timeout=45)
            assert result.returncode==0,result.stdout+result.stderr
            assert 'Could not run command' not in result.stdout,result.stdout
            return result.stdout
        project=Path(temp)/'new mod project';project.mkdir()
        template=project/'solar-mod.json'
        assert 'Created mod template' in app_command('--mod-template',str(template))
        assert 'Valid mod:' in app_command('--check-mod',str(template))
        assert 'Installed Aurora System' in app_command('--offline','-m'+str(template))
        text=app_command('--offline','-c','/mod aurora-system','-c','/orbit','-c','/moons Azure',
                         '-c','/body Lumen','-c','/compare Azure Ember','-c','/mod exit')
        assert 'Lumen' in text and 'COMMUNITY SYSTEM' in text
        assert 'public GitHub package' in app_command('-m','gtts-ux/solar-sim')
        community=(root/'mods/aurora-system.json').read_bytes()
        assert json.loads(community)['format']==2
        assert run_update(root,fetch=published) is None
        assert (root/'mods/proxima-centauri.json').read_bytes()==installed
        assert (root/'mods/interstellar.json').read_bytes()==film
        assert (root/'mods/aurora-system.json').read_bytes()==community
    print('Published ZIP/checksum downloaded successfully; upgrade, saved settings, curated mods, community creation/validation/local and public GitHub installation, moon orbits/comparison and repeat check passed.')


if __name__=='__main__':main()
