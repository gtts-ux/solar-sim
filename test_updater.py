"""Real packaged upgrades, local-data preservation, rejected downloads and rollback."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request
import zipfile

import updater
import solar_sim
from tools.build_release import build


class UpdaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as temp:
            archive,_=build(temp)
            cls.package=archive.read_bytes()
        cls.latest=(Path(__file__).parent/'VERSION.txt').read_text().strip()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"user's solar sim"
        self.root.mkdir()
        self.original={'VERSION.txt':b'0.1.0\n','solar_sim.py':b'# my previous app source\n',
                       'settings.json':b'{"theme":"amber","screensaver":"saturn"}',
                       'launch_cache.json':b'launch cache','ephemeris_cache.json':b'astronomy cache',
                       'exports/keep.json':b'export data','mods/proxima-centauri.json':b'installed mod data',
                       '.git/config':b'git metadata','notes.txt':b'personal notes'}
        for name,data in self.original.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        self.messages=[]

    def fetcher(self,content=None,change=None):
        content=self.package if content is None else content
        digest=hashlib.sha256(content).hexdigest();tag='v'+self.latest
        release={'tag_name':tag,'draft':False,'prerelease':False,'assets':[
            {'name':name,'state':'uploaded','browser_download_url':f'https://github.com/{updater.REPO}/releases/download/{tag}/{name}',
             **({'digest':'sha256:'+digest} if name=='solar-sim.zip' else {})}
            for name in ('solar-sim.zip','solar-sim.zip.sha256')]}
        if change:change(release)
        calls=[]
        def fetch(url,limit):
            calls.append(url)
            if url==updater.LATEST:return json.dumps(release).encode()
            if url.endswith('.sha256'):return f'{digest}  solar-sim.zip\n'.encode()
            if url.endswith('.zip'):return content
            raise AssertionError(url)
        return fetch,calls

    def unchanged(self):
        for name,data in self.original.items():self.assertEqual((self.root/name).read_bytes(),data,name)
        self.assertFalse((self.root/'.solar-sim-update.lock').exists())

    def modified_zip(self,name,data,mode=None):
        output=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.package)) as source,zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as target:
            for member in source.infolist():
                if member.filename!='solar-sim/'+name:target.writestr(member,source.read(member))
            entry=zipfile.ZipInfo('solar-sim/'+name)
            entry.external_attr=(mode or stat.S_IFREG|0o644)<<16
            target.writestr(entry,data)
        return output.getvalue()

    def test_full_upgrade_preserves_local_data_and_backups_and_runs_then_is_idempotent(self):
        fetch,calls=self.fetcher()
        backup=updater.run_update(self.root,fetch,self.messages.append)
        self.assertEqual((self.root/'VERSION.txt').read_text().strip(),self.latest)
        for name,data in self.original.items():
            if name in ('VERSION.txt','solar_sim.py'):
                self.assertEqual((backup/name).read_bytes(),data)
            else:self.assertEqual((self.root/name).read_bytes(),data)
        result=subprocess.run([sys.executable,'-B',str(self.root/'solar_sim.py'),'--offline','-c','/planet','-c','/tutorial'],
                              cwd=self.temp.name,text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('/neptune',result.stdout)
        self.assertIn('sol-sim -u',result.stdout)
        self.assertIsNone(updater.run_update(self.root,fetch,self.messages.append))
        self.assertEqual(len(calls),4)  # Second check downloads metadata only.
        self.assertEqual(len(list((self.root/'update-backups').iterdir())),1)
        self.assertFalse((self.root/'.solar-sim-update.lock').exists())

    def test_bad_checksum_and_disagreeing_metadata_leave_the_app_unchanged(self):
        fetch,_=self.fetcher()
        def corrupt(url,limit):
            data=fetch(url,limit)
            return data+b'corruption' if url.endswith('.zip') else data
        with self.assertRaisesRegex(updater.UpdateError,'checksum failed'):
            updater.run_update(self.root,corrupt,self.messages.append)
        self.unchanged()
        fetch,_=self.fetcher(change=lambda r:r['assets'][0].update(digest='sha256:'+'0'*64))
        with self.assertRaisesRegex(updater.UpdateError,'disagree'):
            updater.run_update(self.root,fetch,self.messages.append)
        self.unchanged()
        self.assertFalse((self.root/'update-backups').exists())

    def test_malicious_paths_symlinks_missing_files_and_invalid_code_are_rejected_before_install(self):
        cases=(('../outside.txt',b'bad',None),('settings.json',b'bad',None),('mods/proxima-centauri.json',b'bad',None),
               ('Engine.py',b'case collision',None),('link',b'../outside',stat.S_IFLNK|0o777),
               ('VERSION.txt',b'9.9.9',None),('engine.py',b'def invalid(:',None),
               ('RELEASE_MANIFEST.json',b'{}',None))
        for name,data,mode in cases:
            with self.subTest(name=name):
                fetch,_=self.fetcher(self.modified_zip(name,data,mode))
                with self.assertRaises((updater.UpdateError,SyntaxError)):
                    updater.run_update(self.root,fetch,self.messages.append)
                self.unchanged()
                self.assertFalse((self.root/'update-backups').exists())

    def test_partial_install_failure_restores_old_source_version_and_new_files(self):
        fetch,_=self.fetcher();replace=updater.os.replace
        def fail_version(source,target):
            if Path(target).name=='VERSION.txt' and '.solar-sim-stage-' in str(source):
                raise PermissionError('simulated write failure')
            return replace(source,target)
        with patch('updater.os.replace',side_effect=fail_version):
            with self.assertRaises(PermissionError):updater.run_update(self.root,fetch,self.messages.append)
        self.unchanged()
        self.assertFalse((self.root/'engine.py').exists())
        self.assertFalse((self.root/'RELEASE_MANIFEST.json').exists())

    def test_symlink_destination_and_concurrent_update_are_not_overwritten(self):
        fetch,_=self.fetcher()
        lock=self.root/'.solar-sim-update.lock';lock.write_text('another updater')
        with self.assertRaisesRegex(updater.UpdateError,'Another update'):
            updater.run_update(self.root,fetch,self.messages.append)
        self.assertEqual(lock.read_text(),'another updater');lock.unlink()
        try:(self.root/'engine.py').symlink_to(self.root/'notes.txt')
        except OSError:self.skipTest('Symlinks unavailable for this account.')
        with self.assertRaisesRegex(updater.UpdateError,'symbolic link'):
            updater.run_update(self.root,fetch,self.messages.append)
        self.unchanged()

    def test_unpublished_or_foreign_assets_and_redirects_are_rejected(self):
        for change in (lambda r:r.update(draft=True),lambda r:r.update(prerelease=True),
                       lambda r:r.update(assets=[]),
                       lambda r:r['assets'][0].update(browser_download_url='https://example.org/solar-sim.zip')):
            fetch,_=self.fetcher(change=change)
            with self.assertRaises(updater.UpdateError):updater.run_update(self.root,fetch,self.messages.append)
            self.unchanged()
        for url in ('http://github.com/file','https://example.org/file','https://github.com@evil.org/file'):
            with self.assertRaises(updater.UpdateError):
                updater.GitHubRedirects().redirect_request(Request(updater.LATEST),None,302,'',{},url)

    def test_update_cli_reports_network_error_without_traceback(self):
        stderr=io.StringIO()
        with patch('updater.run_update',side_effect=HTTPError(updater.LATEST,429,'rate limited',{},None)),redirect_stderr(stderr):
            self.assertEqual(updater.update_cli(self.root),1)
        self.assertIn('rate limit',stderr.getvalue())
        self.assertNotIn('Traceback',stderr.getvalue())


class TutorialCLITests(unittest.TestCase):
    def test_update_flag_routes_before_simulation_or_terminal_initialization(self):
        for flag in ('-u','--update'):
            with patch.object(sys,'argv',['sol-sim',flag]),patch('solar_sim.Simulation',side_effect=AssertionError('Must not start simulation')),patch('updater.update_cli',return_value=0) as update:
                self.assertEqual(solar_sim.main(),0)
                update.assert_called_once_with(Path(solar_sim.__file__).resolve().parent)

    def test_tutorial_and_version_run_from_any_directory_without_starting_simulation(self):
        script=Path(solar_sim.__file__).resolve()
        for flag,text in (('--tutorial','GET STARTED WITH SOL-SIM'),('--version','Solar Sim ')):
            with tempfile.TemporaryDirectory() as temp:
                result=subprocess.run([sys.executable,str(script),flag],cwd=temp,text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(text,result.stdout)


if __name__=='__main__':unittest.main()
