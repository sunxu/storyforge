import hashlib,importlib.util,unittest
from pathlib import Path
src=Path(__file__).resolve().parents[1]/'scripts/r56_deep_preflight.py'
spec=importlib.util.spec_from_file_location('r56_deep_preflight',src)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class LocalDeepReview(unittest.TestCase):
 def row(self,code,index,context=5):
  rid=f'{code}-case-{index}';turn=(index+2)*100
  msgs=[{'role':'user' if j%2==0 else 'assistant','content':f'private history {rid} {j}'} for j in range(context)]
  msgs[-1]['role']='user'
  msgs.append({'role':'assistant','content':'response '+rid})
  target=hashlib.sha256(msgs[-1]['content'].encode()).hexdigest()
  return {'id':rid,'messages':msgs,'metadata':{'story_id':code+'-uuid','target_turn_index':turn,
      'source_message_ids':[f'{rid}-{i}' for i in range(len(msgs))],
      'source_turn_indices':list(range(turn-len(msgs)+1,turn+1)),
      'source_sha256':'a'*64,'context_message_count':context,
      'target_sha256_utf8':target,'story_card_status':'TARGET_TIME_UNVERIFIED',
      'story_card_version_id':None,'independent_gold_review':'NOT_RUN'}}
 def setUp(self):
  self.rows=[self.row('03',i,7) for i in range(14)]+[self.row('05',i,5 if i>=5 else 3) for i in range(18)]
  self.rows +=[self.row('other',i,5) for i in range(55)]
  self.select={'status':'24_PROVISIONAL_HOLD__NOT_FRESH_HELDOUT__NO_GPU',
   'ids_by_story':{'03':[f'03-case-{i}' for i in range(12)],'05':[f'05-case-{i}' for i in range(5,17)]}}
  self.audit={'official_independent_test_admitted':0,'planned_provisional_count':24,
   'source_eligible_world_counts':{'03':14,'05':18}}
 def test_valid_structure(self):
  self.assertEqual(m.check_row(self.rows[0]),self.rows[0]['metadata']['target_sha256_utf8'])
 def test_selected_all_remain_hold(self):
  rows,pool,uuids=m.make_rows(self.rows,self.select,self.audit)
  self.assertEqual(len(rows),32)
  self.assertEqual(sum(x['selected24_provisional']=='YES' for x in rows),24)
  self.assertTrue(all(x['status']==m.HOLD for x in rows))
  self.assertTrue(all(x['age_at_target_gate'].startswith('HOLD') for x in rows))
 def test_missing_card_is_never_approved(self):
  rows,_,_=m.make_rows(self.rows,self.select,self.audit)
  self.assertTrue(all(x['target_time_card_recorded']=='ABSENT' for x in rows))
 def test_wrong_hash_fails(self):
  self.rows[0]['metadata']['target_sha256_utf8']='0'*64
  with self.assertRaisesRegex(ValueError,'TARGET_SHA256'):m.make_rows(self.rows,self.select,self.audit)
 def test_short_history_selected_fails(self):
  self.select['ids_by_story']['03'][0]='05-case-0'
  with self.assertRaisesRegex(ValueError,'CROSS_WORLD_SELECTED_ID'):m.make_rows(self.rows,self.select,self.audit)
 def test_bad_source_provenance_fails(self):
  self.rows[0]['metadata']['source_message_ids'].pop()
  with self.assertRaisesRegex(ValueError,'BAD_SOURCE_PROVENANCE'):m.make_rows(self.rows,self.select,self.audit)
 def test_wrong_world_count_fails(self):
  self.rows.pop(0)
  with self.assertRaisesRegex(ValueError,'GOLD_POOL_COUNT_MISMATCH|MISSING_SELECTED_ID|GOLD87_COUNT_MISMATCH'):m.make_rows(self.rows,self.select,self.audit)
if __name__=='__main__':unittest.main(verbosity=2)
