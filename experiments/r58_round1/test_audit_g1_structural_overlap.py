"""R58 G1 overlap diagnostics: synthetic-only tests, no live DB or story data."""
import csv
import os
from pathlib import Path
import tempfile
import unittest

from audit_g1_structural_overlap import (
    SCHEMA, Hold, build_sql, load_queue, project, run,
    EXPECTED_CSV,
)

def row(story_id="synthetic-one"):
    return {
        'story_id':story_id,'source_type':'original','review_state':'G1_HOLD',
        'world_component':'','owner_world_graph_reviewed':'false',
        'r50_protected_clear':'false','prior_sft_clear':'false',
        'r55_r57_dev_clear':'false','other_protected_clear':'false',
        'evidence_reference':'',
    }

def result(size):
    return {
        'reader_role_correct':True,'transaction_read_only':'on',
        'selected_count':size,'matched_count':size,
        'compared_pairs':size*(size-1)//2,
        'same_author_pairs':1 if size>1 else 0,
        'same_title_pairs':0,'same_world_setting_pairs':0,
        'same_v2_world_exact_pairs':0,
    }

class TestG1StructuralOverlap(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.dir=Path(self.temp.name)
        os.chmod(self.dir,0o700)
    def tearDown(self):
        self.temp.cleanup()
    def save(self,rows):
        path=self.dir/'g1_queue.csv'
        with path.open('w',newline='',encoding='utf-8') as f:
            wr=csv.DictWriter(f,fieldnames=sorted(EXPECTED_CSV))
            wr.writeheader();wr.writerows(rows)
        os.chmod(path,0o600)
        return path
    def test_plan_only_never_db(self):
        ans=run(self.save([row()]),True)
        self.assertEqual(ans['status'],'PLAN_ONLY__NO_DB_ACCESS')
    def test_private_queue_can_load_five_unique_ids(self):
        p=self.save([row(f'synthet-{i}') for i in range(5)])
        self.assertEqual(len(load_queue(p)),5)
    def test_requires_all_guard_flags_false(self):
        q=row();q['r50_protected_clear']='true'
        with self.assertRaises(Hold):load_queue(self.save([q]))
    def test_requires_world_unassigned(self):
        q=row();q['world_component']='unknown-world'
        with self.assertRaises(Hold):load_queue(self.save([q]))
    def test_rejects_sql_injection_in_identifier(self):
        with self.assertRaises(Hold):
            build_sql(["id'; DROP TABLE"])
    def test_db_query_is_read_only_and_aggregate(self):
        q=build_sql(['synthetic-one','synthetic-two'])
        self.assertIn('BEGIN READ ONLY',q)
        self.assertIn('jsonb_build_object',q)
        self.assertIn('user_stories',q)
        self.assertNotIn('v2_chat_messages',q)
        self.assertNotIn('COPY ',q)
    def test_projection_safe_no_raw_ids(self):
        ans=project(result(2),2)
        self.assertEqual(ans['schema'],SCHEMA)
        self.assertEqual(ans['same_author_pairs'],1)
        self.assertEqual(ans['world_components_certified'],0)
        self.assertFalse(ans['r50_protection_checked'])
        self.assertFalse(ans['expansion_allowed'])
        self.assertNotIn('story_id',ans)
    def test_no_identity_or_read_only_failure(self):
        x=result(3);x['reader_role_correct']=False
        with self.assertRaises(Hold):project(x,3)
        x=result(3);x['transaction_read_only']='off'
        with self.assertRaises(Hold):project(x,3)
    def test_count_mismatch_holds(self):
        x=result(5);x['matched_count']=4
        with self.assertRaises(Hold):project(x,5)
    def test_pair_bounds_holds(self):
        x=result(2);x['same_author_pairs']=2
        with self.assertRaises(Hold):project(x,2)
    def test_missing_queue_holds(self):
        with self.assertRaises(Hold):load_queue(self.dir/'absent.csv')

if __name__=='__main__':
    unittest.main()
