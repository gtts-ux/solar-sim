"""User-level commands, shell startup integration and safe repeat installation."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from install_commands import ROOT, MARKER, NAMES, install, path_block


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


if __name__=='__main__':unittest.main()
