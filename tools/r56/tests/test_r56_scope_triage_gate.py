import importlib.util
import csv
import json
from pathlib import Path
import tempfile
import unittest

p=Path(__file__).resolve().parents[1]/'scripts'/'r56_scope_triage_gate.py'
spec=importlib.util.spec_from_file_location('r56_stage7',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ID='12345678-1234-4234-8234-123456789012'
SHA='a'*64
FIELDS=['story_uuid_PRIVATE','original_story_sha256_PRIVATE','original_source_path_PRIVATE','uuid_triage','formal_world_admitted']

def case(path, **change):
    row=dict(zip(FIELDS,[ID,SHA,'/safe/evaluations/v0.2/source-archives/jsonl/01-foo.jsonl',m.GOLD,'NO']))
    row.update(change)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerow(row)

class Stage7ScopeTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.d=Path(self.t.name);self.csv=self.d/'in.csv';self.out=self.d/'out'
    def test_genuine_gold_only(self):
        case(self.csv); s,p=m.triage(self.csv);self.assertEqual(s['potential_new_uuid_only'],0);self.assertTrue(s['old_gold_source_root_observed']);self.assertEqual(s['official_test_admitted'],0)
    def test_gold_only_block_repeat(self):
        case(self.csv);s,_=m.triage(self.csv);self.assertIn('STOP_REPEAT',s['status'])
    def test_potential_holds(self):
        case(self.csv,uuid_triage=m.POTENTIAL);s,_=m.triage(self.csv);self.assertEqual(s['potential_new_uuid_only'],1);self.assertEqual(s['official_test_admitted'],0)
    def test_historical_overlap(self):
        case(self.csv,uuid_triage=m.HISTORY);s,_=m.triage(self.csv);self.assertEqual(s['historical_uuid_overlap'],1)
    def test_missing_fields(self):
        self.csv.write_text('hello\nworld\n');self.assertRaises(m.Blocked,m.triage,self.csv)
    def test_invalid_sha(self):
        case(self.csv,original_story_sha256_PRIVATE='a');self.assertRaises(m.Blocked,m.triage,self.csv)
    def test_invalid_uuid(self):
        case(self.csv,story_uuid_PRIVATE='incorrect');self.assertRaises(m.Blocked,m.triage,self.csv)
    def test_unknown_class(self):
        case(self.csv,uuid_triage='PASS');self.assertRaises(m.Blocked,m.triage,self.csv)
    def test_false_approval(self):
        case(self.csv,formal_world_admitted='YES');self.assertRaises(m.Blocked,m.triage,self.csv)
    def test_empty_csv(self):
        with self.csv.open('w',newline='') as f: csv.DictWriter(f,fieldnames=FIELDS).writeheader()
        self.assertRaises(m.Blocked,m.triage,self.csv)
    def test_no_overwrite(self):
        case(self.csv);s,p=m.triage(self.csv);m.write(s,p,self.out);self.assertRaises(m.Blocked,m.write,s,p,self.out)
    def test_sanitized_safe_no_ids(self):
        case(self.csv);s,p=m.triage(self.csv);m.write(s,p,self.out);b=(self.out/'safe'/'R56_STAGE7_SCOPE_COUNTS_ONLY.json').read_text();self.assertNotIn(ID,b);self.assertNotIn('/safe/',b)
    def test_main_real(self):
        case(self.csv);self.assertEqual(m.main(['--triage-csv',str(self.csv),'--out-dir',str(self.out)]),0)

if __name__=='__main__':unittest.main()
