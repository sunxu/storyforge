"""R58 Git historical-source verification: synthetic data tests, no HF."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE=Path(__file__).with_name("verify_github_historical_training_sources.py")
spec=importlib.util.spec_from_file_location("verify_github_historical_training_sources",MODULE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def make_sample(n=1):
    lines=[]
    for i in range(n):
        uid=f"{i+1:08x}-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        lines.append(json.dumps({"id":f"sample-{i:06d}",
          "metadata":{"story_id":uid},"messages":[{"role":"user","content":"synthetic"}]}))
    return ("\n".join(lines)+"\n").encode()

class GitSourcesTests(unittest.TestCase):
    def test_01_projection_two_rows(self):
        data=make_sample(2)
        x=m.v01_worlds(data,2,hashlib.sha256(data).hexdigest())
        self.assertEqual(sum(x.values()),2)
    def test_02_projection_hash_drift(self):
        with self.assertRaises(m.Hold):
            m.v01_worlds(make_sample(),1,"0"*64)
    def test_03_projection_count_drift(self):
        x=make_sample()
        with self.assertRaises(m.Hold):
            m.v01_worlds(x,2,hashlib.sha256(x).hexdigest())
    def test_04_duplicate_sample_rejected(self):
        data=make_sample(2).replace(b"sample-000001",b"sample-000000")
        with self.assertRaises(m.Hold):
            m.v01_worlds(data,2,hashlib.sha256(data).hexdigest())
    def test_05_ambiguous_story_id_rejected(self):
        x=make_sample().replace(b'"metadata": {',b'"metadata": {"story_id":"00000002-aaaa-4aaa-8aaa-aaaaaaaaaaaa", ',1)
        with self.assertRaises(m.Hold):
            m.v01_worlds(x,1,hashlib.sha256(x).hexdigest())
    def test_06_runner_literal(self):
        self.assertEqual(m.r54_expected('EXPECTED={"train":("sha",31)}')["train"],("sha",31))
    def test_07_runner_does_not_execute(self):
        with self.assertRaises(m.Hold):
            m.r54_expected('EXPECTED=__import__("os").system("echo unsafe")')
    def test_08_runner_duplicate_holds(self):
        with self.assertRaises(m.Hold):
            m.r54_expected("EXPECTED={}\nEXPECTED={}\n")
    def test_09_untrusted_git_ref_holds(self):
        with self.assertRaises(m.Hold):
            m.read_blob(Path("/tmp"),"main")
    def test_10_invalid_ledger_holds(self):
        with self.assertRaises(m.Hold):
            m.validate_ledger({"schema":m.SCHEMA,"g1_clearance":"PASS"})
    def test_11_manifest_size_contract(self):
        self.assertEqual(sum(x[0] for x in m.SPLITS.values()),184)
        self.assertEqual(len(m.JOBS),5)
        self.assertEqual(len(m.PINS),11)
    def test_12_missing_repo_fails_closed(self):
        with tempfile.TemporaryDirectory() as p:
            self.assertEqual(m.main(["--repo-root",p]),42)

if __name__=="__main__":
    unittest.main()
