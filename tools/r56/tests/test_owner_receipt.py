import importlib.util, pathlib, unittest, tempfile, json, hashlib, csv
SRC=pathlib.Path(__file__).resolve().parents[1]/'scripts/r56_verify_owner_receipt.py'
spec=importlib.util.spec_from_file_location('r56validator',SRC);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
valid={'schema':m.REPORT_SCHEMA,'result':m.REPORT_STATUS,'repo_head':'a'*40,'old_unit_tests':11,
 'safe_summary_sha256':m.deterministic_safe_hash(m.FROZEN_SUMMARY),
 'deep_count_only_sha256':m.deterministic_safe_hash(m.FROZEN_DEEP),
 'official_test_admitted':0,'r50_read':False,'gpu_job_started':False,'training_performed':False,'model_promoted':False}
class Verify(unittest.TestCase):
 def test_receipt_accepts_structural_holds(self):
  self.assertIn('NOT_YET_RECHECKED',m.verify_receipt(valid)['status'])
 def test_suspicious_admission(self):
  x=dict(valid,official_test_admitted=1)
  with self.assertRaises(m.GateError):m.verify_receipt(x)
 def test_gpu_false_required(self):
  x=dict(valid,gpu_job_started=0)
  with self.assertRaises(m.GateError):m.verify_receipt(x)
 def test_bad_commit(self):
  x=dict(valid,repo_head='x'*40)
  with self.assertRaises(m.GateError):m.verify_receipt(x)
 def test_bad_hash(self):
  x=dict(valid,safe_summary_sha256='xyz')
  with self.assertRaises(m.GateError):m.verify_receipt(x)
 def test_deterministic_frozen_sha_matches_owner_receipt(self):
  self.assertEqual(valid['safe_summary_sha256'],'2e5bc00efce421d94ac551e5d243d2d1a22c528d75adcc03ad3bd7df0fd59b32')
  self.assertEqual(valid['deep_count_only_sha256'],'d6a95bddfc6f917cc55a345e64b4243aa3fc1f3f0cf1702f7921b6f01b4cda61')
 def test_bad_schema(self):
  x=dict(valid,schema='bad')
  with self.assertRaises(m.GateError):m.verify_receipt(x)
 def test_validate_summaries(self):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td); s=dict(m.FROZEN_SUMMARY)
   d=dict(m.FROZEN_DEEP)
   one=td/'original_prescreen/R56_GOLD195_ELIGIBILITY_AUDIT.json';two=td/'deep_preflight/safe/R56_DEEP_PREFLIGHT_COUNTS_ONLY.json'
   for path,data in [(one,s),(two,d)]:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
   receipt=dict(valid,safe_summary_sha256=m.digest(one),deep_count_only_sha256=m.digest(two))
   result=m.verify_receipt(receipt);m.validate_origin(td,receipt,result)
   self.assertTrue(result['deep_output_sha256_verified'])
   s['gold_total']=194;one.write_text(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
   with self.assertRaises(m.GateError):m.validate_origin(td,receipt,result)
 def test_unit_logs(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)
   (p/'ORIGINAL_11_TESTS.log').write_text('Ran 11 tests in 0.1s\n\nOK\n')
   (p/'NEW_TESTS.log').write_text('Ran 7 tests in 0.1s\n\nOK\n')
   r={};m.validate_logs(p,r);self.assertTrue(r['both_unittest_logs_verified'])
   (p/'NEW_TESTS.log').write_text('Ran 7 tests in 0.1s\n\nFAILED (failures=1)\n')
   with self.assertRaises(m.GateError):m.validate_logs(p,r)
 def test_private_case_sheets(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'deep_preflight/private';p.mkdir(parents=True)
   for name,total in [('R56_GOLD32_CASE_GATE_REVIEW_PRIVATE.csv',32),('R56_GOLD24_PROVISIONAL_GATE_REVIEW_PRIVATE.csv',24)]:
    with (p/name).open('w',newline='') as f:
     w=csv.DictWriter(f,fieldnames=['candidate_id_PRIVATE','story_code','selected24_provisional','status','gold_independent_review']);w.writeheader()
     for i in range(total):
      code='03' if i<(14 if total==32 else 12) else '05'
      sel='NO' if (total==32 and i in (0,1,14,15,16,17,18,19)) else 'YES'
      w.writerow({'candidate_id_PRIVATE':str(i),'story_code':code,'selected24_provisional':sel,'status':'HOLD_NOT_TEST_ADMITTED','gold_independent_review':'NOT_RUN'})
   r={};m.validate_private_sheets(pathlib.Path(td),r);self.assertTrue(r['private_case_sheet_structural_check'])
if __name__=='__main__':unittest.main()
