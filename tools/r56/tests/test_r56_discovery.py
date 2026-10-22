import copy,importlib.util,pathlib,unittest
source=pathlib.Path(__file__).resolve().parents[1]/'scripts/r56_discover_new_worlds.py';spec=importlib.util.spec_from_file_location('r56_discover',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.row={'story_uuid_PRIVATE':'story-new','original_story_sha256_PRIVATE':'c'*64,'original_source_path_PRIVATE':'origin/new.json'}
 def test_new_uuid_held(self):
  a=m.triage([self.row],{'known-gold'},{'known-train'});self.assertEqual(a[0]['uuid_triage'],'POTENTIAL_NON_GOLD_WORLD__SEMANTIC_EXPOSURE_HOLD');self.assertEqual(a[0]['formal_world_admitted'],'NO')
 def test_gold_rejected(self):self.assertTrue(m.triage([self.row],{'story-new'},set())[0]['uuid_triage'].startswith('ALREADY'))
 def test_training_rejected(self):self.assertTrue(m.triage([self.row],set(),{'story-new'})[0]['uuid_triage'].startswith('KNOWN'))
 def test_r50_filepath_blocked(self):
  r=copy.deepcopy(self.row);r['original_source_path_PRIVATE']='private/r50/secret.json'
  with self.assertRaises(m.Block):m.triage([r],set(),set())
 def test_r50_description_blocked(self):
  r=copy.deepcopy(self.row);r['provenance_evidence_private']='R50-hidden'
  with self.assertRaises(m.Block):m.triage([r],set(),set())
 def test_duplicate_world_blocked(self):
  with self.assertRaises(m.Block):m.triage([self.row,self.row],set(),set())
 def test_bad_sha_blocked(self):
  r=copy.deepcopy(self.row);r['original_story_sha256_PRIVATE']='invalid'
  with self.assertRaises(m.Block):m.triage([r],set(),set())
if __name__=='__main__':unittest.main()
