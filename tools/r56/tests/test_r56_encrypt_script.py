import pathlib
import subprocess
import tempfile
import unittest

SCRIPT=pathlib.Path(__file__).resolve().parents[1]/'scripts/r56_encrypt_private_audit.sh'

class EncryptFailClosed(unittest.TestCase):
    def call(self,*args):
        return subprocess.run(['bash',str(SCRIPT),*args],capture_output=True,text=True)
    def test_missing_args(self):
        self.assertEqual(self.call().returncode,2)
    def test_bad_recipient(self):
        self.assertEqual(self.call('--repo','/tmp','--source','/tmp/dummy.zip','--recipient','not_age_key','--name','audit').returncode,2)
    def test_unsafe_archive_name(self):
        self.assertEqual(self.call('--repo','/tmp','--source','/tmp/dummy.zip','--recipient','age1'+'q'*40,'--name','../outside').returncode,2)
    def test_r50_forbidden(self):
        self.assertEqual(self.call('--repo','/tmp','--source','/tmp/R50_PRIVATE.zip','--recipient','age1'+'q'*40,'--name','audit').returncode,2)
    def test_missing_source_forbidden(self):
        self.assertEqual(self.call('--repo','/tmp','--source','/tmp/not-existing-r56.zip','--recipient','age1'+'q'*40,'--name','audit').returncode,2)

if __name__=='__main__':unittest.main()
