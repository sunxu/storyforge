"""Synthetic-only G1 review queue privacy, quota and fail-closed tests."""
import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from pilot_round1_shortlist import CATEGORIES, Hold
from prepare_round1_g1_review_queue import OUTPUT_FIELDS, QUEUE_STATUS, SCHEMA, prepare_queue, run

STORY={
    'story_id':'synthetic-A','source_type':'original','not_deleted':'t',
    'moderation_status':'approved','story_type':'v2_sandbox',
    'assistant_completed':'201','session_count':'8',
    'has_world':'t','has_character':'t','has_characters':'f',
    'has_opening':'t',
}
GUARDS=[
    'owner_world_graph_reviewed','r50_protected_clear',
    'prior_sft_clear','r55_r57_dev_clear','other_protected_clear'
]

class TestG1Queue(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.folder=self.root/'owner_private'
        self.folder.mkdir(mode=0o700)
        os.chmod(self.folder,0o700)

    def tearDown(self):
        self.tmp.cleanup()

    def private_input(self, rows):
        p=self.folder/'stories.csv'
        with p.open('w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        os.chmod(p,0o600)
        return p

    def test_no_guard_is_ever_approved_by_preparation(self):
        queue=prepare_queue([STORY])
        self.assertEqual(len(queue),1)
        self.assertTrue(all(x in queue[0] for x in GUARDS))
        self.assertTrue(all(queue[0][x]=='false' for x in GUARDS))
        self.assertEqual(queue[0]['world_component'],'')
        self.assertEqual(queue[0]['evidence_reference'],'')
        self.assertEqual(queue[0]['review_state'],'G1_HOLD')

    def test_quota_five_and_source_strata(self):
        types=['original']*8+['dice_cocreate']*4+['ai_assisted']*4
        entries=[]
        for i,typ in enumerate(types):
            entries.append({**STORY,'story_id':f'syn-{i}','source_type':typ,
                            'session_count':str(20-i),'assistant_completed':'300'})
        queue=prepare_queue(entries)
        self.assertEqual(len(queue),5)
        for typ,cap in CATEGORIES.items():
            self.assertEqual(sum(x['source_type']==typ for x in queue),cap)

    def test_private_queue_write_and_safe_result(self):
        inp=self.private_input([STORY])
        out=self.folder/'queue.csv'
        data=run(inp,out)
        self.assertEqual(data['schema'],SCHEMA)
        self.assertEqual(data['status'],QUEUE_STATUS)
        self.assertNotIn('synthetic-A',json.dumps(data))
        self.assertFalse(data['expansion_allowed'])
        self.assertFalse(data['private_reply_text_read'])
        self.assertEqual(out.stat().st_mode & 0o777,0o600)
        with out.open(newline='',encoding='utf-8') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),1)
        self.assertEqual(set(rows[0]),set(OUTPUT_FIELDS))
        self.assertEqual(rows[0]['story_id'],'synthetic-A')

    def test_existing_destination_rejected_immutable(self):
        inp=self.private_input([STORY])
        out=self.folder/'queue.csv'
        before=b'existing private file'
        out.write_bytes(before)
        os.chmod(out,0o600)
        with self.assertRaises(Hold):
            run(inp,out)
        self.assertEqual(out.read_bytes(),before)

    def test_world_protection_not_auto_certified(self):
        data=run(self.private_input([STORY]),self.folder/'queue.csv')
        self.assertEqual(data['actual_world_components_verified'],0)
        self.assertFalse(data['protected_worlds_checked'])
        self.assertFalse(data['existing_training_exposure_checked'])
        self.assertEqual(data['train_admitted'],0)

    def test_invalid_and_duplicate_metadata_rejected(self):
        with self.assertRaises(Hold):
            prepare_queue([STORY,STORY])

    def test_private_world_queue_is_not_training_shortlist(self):
        queue=prepare_queue([STORY])
        self.assertNotIn('content',queue[0])
        self.assertNotIn('messages',queue[0])
        self.assertNotIn('prompt',queue[0])
        self.assertIn('G1_HOLD',queue[0]['review_state'])

if __name__=='__main__':
    unittest.main()
