import importlib.util,io,json,pathlib,tempfile,unittest,copy,csv
source=pathlib.Path(__file__).resolve().parents[1]/'scripts/r56_prepare_content_review.py'
spec=importlib.util.spec_from_file_location('r56_stage2',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Stage2Tests(unittest.TestCase):
 def setUp(self):
  self.report={'schema':'storyforge-r56-owner-receipt-verification-v1',
   'status':mod.VERIFIED_STATUS,'receipt_sha256':mod.RECEIPT_SHA,
   'five_pinned_blobs_reverified_locally':True,'original_output_sha256_verified':True,
   'deep_output_sha256_verified':True,'both_unittest_logs_verified':True,
   'private_case_sheet_structural_check':True,
   'reconstructed_expected_deep_summary_sha256_matches':True,
   'reconstructed_expected_safe_summary_sha256_matches':True,
   'r50_read':False,'gpu_job_started':False,'training_performed':False,'model_promoted':False,
   'official_test_admitted':0,'additional_independent_worlds_missing':2,
   'independent_case_content_gate':'HOLD_NOT_REVIEWED',
   'source_exposure_semantic_gate':'HOLD_NOT_REVIEWED','cross_world_independence':'HOLD_NOT_PROVEN'}
  msgs=[{'role':'user','content':'Alpha'}, {'role':'assistant','content':'Beta'}]
  digest=mod.sha(msgs[-1]['content'].encode('utf-8'))
  self.row={'candidate_id_PRIVATE':'synthetic-1','story_code':'03','target_turn':'2','context_message_count':'1',
            'gold_target_sha256_PRIVATE':digest,'source_snapshot_sha256_PRIVATE':'a'*64,
            'selected24_provisional':'NO','status':'HOLD_NOT_TEST_ADMITTED','gold_independent_review':'NOT_RUN','target_time_card_recorded':'ABSENT'}
  self.gold={'synthetic-1':{'id':'synthetic-1','messages':msgs,'metadata':{
      'story_id':'synthetic-world','target_turn_index':2,'context_message_count':1,
      'source_message_ids':['m1','m2'],'source_turn_indices':[1,2],
      'source_sha256':'a'*64,'target_sha256_utf8':digest,'story_card_version_id':None}}}
 def test_valid_report(self):mod.verify_report(self.report)
 def test_bad_status(self):
  x=copy.deepcopy(self.report);x['status']='PASS'
  with self.assertRaises(mod.Block):mod.verify_report(x)
 def test_nonzero_admission_blocked(self):
  x=copy.deepcopy(self.report);x['official_test_admitted']=1
  with self.assertRaises(mod.Block):mod.verify_report(x)
 def test_bad_original_blob_flag(self):
  x=copy.deepcopy(self.report);x['five_pinned_blobs_reverified_locally']=False
  with self.assertRaises(mod.Block):mod.verify_report(x)
 def test_bad_receipt_hash(self):
  x=copy.deepcopy(self.report);x['receipt_sha256']='0'*64
  with self.assertRaises(mod.Block):mod.verify_report(x)
 def test_r50_flag_fail_closed(self):
  x=copy.deepcopy(self.report);x['r50_read']=True
  with self.assertRaises(mod.Block):mod.verify_report(x)
 def test_valid_fake_record(self):
  x=mod.content_packet(self.row,self.gold)
  self.assertEqual(x['final_test_admission'],'HOLD_NOT_TEST_ADMITTED')
  self.assertFalse(x['model_prompt_is_certified_complete'])
  self.assertEqual(x['gold_target_for_content_review_only_PRIVATE']['content'],'Beta')
 def test_target_hash_mismatch(self):
  r=copy.deepcopy(self.row);r['gold_target_sha256_PRIVATE']='f'*64
  with self.assertRaises(mod.Block):mod.verified_record(r,self.gold)
 def test_mismatch_source_hash(self):
  r=copy.deepcopy(self.row);r['source_snapshot_sha256_PRIVATE']='f'*64
  with self.assertRaises(mod.Block):mod.verified_record(r,self.gold)
 def test_missing_card_flags(self):
  x=mod.content_packet(self.row,self.gold)
  self.assertIn('TARGET_TIME_CARD_VERSION_NOT_VERIFIED',x['evidence_insufficiency_flags'])
 def test_leaked_prompt_flag(self):
  x=mod.content_packet(self.row,self.gold)
  self.assertNotIn(x['gold_target_for_content_review_only_PRIVATE'],x['visible_history_as_frozen_in_gold87_PRIVATE'])
 def test_wrong_source_ids(self):
  g=copy.deepcopy(self.gold);g['synthetic-1']['metadata']['source_message_ids']=['a','a']
  with self.assertRaises(mod.Block):mod.verified_record(self.row,g)
 def test_wrong_turn_order(self):
  g=copy.deepcopy(self.gold);g['synthetic-1']['metadata']['source_turn_indices']=[2,1]
  with self.assertRaises(mod.Block):mod.verified_record(self.row,g)
 def test_no_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)
   with self.assertRaises(mod.Block):mod.run(p,p/'missing',p/'missing',p)
 def test_sha_calculation(self):
  self.assertEqual(mod.sha(b'abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

if __name__=='__main__':unittest.main()
