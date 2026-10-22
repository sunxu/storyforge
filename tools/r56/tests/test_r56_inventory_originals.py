import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid
S=Path(__file__).resolve().parents[1]/'scripts'/'r56_inventory_originals.py'
spec=importlib.util.spec_from_file_location('r56_inventory_originals',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SourceInventoryTests(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
    def write(self,filename='a.jsonl',uid=None,rank=21,msg='ok'):
        p=self.root/filename;obj={'rank':rank,'story':{'id':uid or str(uuid.uuid4()),'created_at':'2026-01-01'},'messages':[{'id':str(uuid.uuid4()),'role':'assistant','content':msg}]};p.write_text(json.dumps(obj));return p,obj
    def test_success(self):
        p,o=self.write();rows,c=m.inventory([self.root]);self.assertEqual(c['unique_world_uuids'],1);self.assertEqual(rows[0]['story_uuid_PRIVATE'],o['story']['id'])
    def test_exact_sha(self):
        import hashlib
        p,_=self.write();self.assertEqual(m.parse_export(p)['original_story_sha256_PRIVATE'],hashlib.sha256(p.read_bytes()).hexdigest())
    def test_no_gold_proposal(self):self.assertIn('NO_ADMISSION',m.parse_export(self.write()[0])['candidate_status_PRIVATE'])
    def test_sealed_path(self):self.assertTrue(m.is_sealed('/private/R50/sources.jsonl'))
    def test_rank_rejected(self):
        p,_=self.write(rank=19)
        with self.assertRaises(m.Blocked):m.parse_export(p)
    def test_non_story_skipped(self):
        p=self.root/'sample.jsonl';p.write_text('{"id":"example"}')
        self.assertIsNone(m.parse_export(p))
    def test_duplicate_versions_hold(self):
        u=str(uuid.uuid4());self.write('a.jsonl',u,msg='one');self.write('b.jsonl',u,msg='two');rows,c=m.inventory([self.root]);self.assertEqual(c['world_uuids_with_version_conflict'],1);self.assertTrue(all(r['candidate_status_PRIVATE'].startswith('SOURCE_VERSION') for r in rows))
    def test_no_overwrite(self):self.assertEqual(m.main(['--root',str(self.root),'--out-dir',str(self.root)]),2)
    def test_symlink_skipped(self):
        p,_=self.write();(self.root/'alias.jsonl').symlink_to(p);self.assertEqual(len(m.inventory([self.root])[0]),1)
    def test_archive_no_auto_open(self):
        p=self.root/'stories.zip';p.write_bytes(b'zip');self.assertEqual(m.inventory([self.root])[1]['archives_skipped_extract_first'],1)
if __name__=='__main__':unittest.main()
