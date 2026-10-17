"""Verify the actual downloadable package works after extraction."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.build_release import FILES, build


class DistributionTests(unittest.TestCase):
    def test_archive_checksum_contents_and_launch_after_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder)
            archive,checksum=build(temp/'download')
            self.assertEqual(checksum.read_text().split()[0],hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as package:
                self.assertIsNone(package.testzip())
                self.assertTrue({'solar-sim/'+f for f in FILES}<=set(package.namelist()))
                self.assertTrue(all(n.startswith('solar-sim/') and '..' not in Path(n).parts for n in package.namelist()))
                for name in package.namelist():
                    self.assertFalse(any(part in ('.git','__pycache__','exports','.DS_Store','ephemeris_cache.json') for part in Path(name).parts))
                self.assertTrue(package.getinfo('solar-sim/Start Solar Sim.command').external_attr>>16 & 0o111)
                package.extractall(temp/'folder with spaces')
            extracted=temp/'folder with spaces'/'solar-sim'
            args=['--offline','-c','/day earth','-c','/mission Apollo 11 30 seconds','-c','/mission seek 47','-c','/sources']
            result=subprocess.run([sys.executable,'-B',str(extracted/'solar_sim.py'),*args],cwd=temp,
                                  text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            for text in ('DAY LENGTH','24.00 hours','APOLLO 11','Moon landing','NASA'):
                self.assertIn(text,result.stdout)
            self.assertNotIn('Could not run command',result.stdout)
            if shutil.which('sh') and sys.platform!='win32':
                for name in ('Start Solar Sim.sh','Start Solar Sim.command'):
                    result=subprocess.run(['sh',str(extracted/name),'--offline','-c','/planet'],cwd=temp,
                                          text=True,capture_output=True,timeout=30)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('/neptune',result.stdout)
                commands=temp/'user commands'
                result=subprocess.run([sys.executable,str(extracted/'install_commands.py'),
                                       '--bin-dir',str(commands),'--no-path'],cwd=temp,
                                      text=True,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                for name in ('solar-sim','sol-sim'):
                    result=subprocess.run([str(commands/name),'--offline','-c','/planet'],cwd=temp,
                                          text=True,capture_output=True,timeout=30)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('/neptune',result.stdout)
            if sys.platform=='win32':
                result=subprocess.run(['cmd','/c',str(extracted/'Start Solar Sim.bat'),'--offline','-c','/planet'],
                                      cwd=temp,text=True,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('/neptune',result.stdout)


if __name__=='__main__':
    unittest.main()
