"""Synthetic-only R58 pilot shortlist tests. No protected-world IDs or story content."""
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from argparse import Namespace
from pilot_round1_shortlist import discover, select, audit, Hold, CATEGORIES

STORY={'story_id':'id1','source_type':'original','not_deleted':'true',
       'moderation_status':'approved','story_type':'v2_sandbox',
       'assistant_completed':'250','session_count':'6',
       'has_world':'true','has_character':'true',
       'has_characters':'true','has_opening':'true'}
GUARD={'story_id':'id1','world_component':'world-1',
       'owner_world_graph_reviewed':'true','r50_protected_clear':'true',
       'prior_sft_clear':'true','r55_r57_dev_clear':'true',
       'other_protected_clear':'true','evidence_reference':'LOCAL_EVIDENCE'}

class Cases(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.base=Path(self.t.name)
        self.sec=self.base/'secure';self.sec.mkdir(mode=0o700)
        os.chmod(self.sec,0o700)
    def tearDown(self):self.t.cleanup()
    def csvfile(self,name,rows):
        p=self.sec/name
        with p.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        return p
    def args(self,inv,guards=None,out=None):
        return Namespace(inventory=str(inv),guards=str(guards) if guards else None,
                         private_output=str(out) if out else None,safe_output=None)
    def test_discover_empty_genre_not_required(self):
        self.assertEqual(len(discover([STORY])),1)
    def test_psql_csv_t_true_for_discovery(self):
        """PostgreSQL --csv emits t/f, not Python's true/false."""
        row={**STORY,'not_deleted':'t','has_world':'t',
             'has_character':'t','has_characters':'f','has_opening':'t'}
        self.assertEqual(len(discover([row])),1)

    def test_psql_csv_f_false_for_discovery(self):
        row={**STORY,'not_deleted':'f','has_world':'t',
             'has_character':'t','has_opening':'t'}
        self.assertEqual(discover([row]),[])

    def test_psql_csv_roundtrip_t_f_metadata_only(self):
        row={**STORY,'not_deleted':'t','has_world':'t',
             'has_character':'t','has_characters':'f','has_opening':'t'}
        inv=self.csvfile('psql.csv',[row])
        result=audit(self.args(inv))
        self.assertEqual(result['metadata_eligible'],1)
        self.assertEqual(result['metadata_eligible_by_source']['original'],1)
        self.assertFalse(result['expansion_allowed'])

    def test_psql_csv_f_for_protection_guard(self):
        row={**STORY,'not_deleted':'t','has_world':'t','has_character':'t','has_opening':'t'}
        good={**GUARD,'r50_protected_clear':'t','prior_sft_clear':'t',
              'r55_r57_dev_clear':'t','other_protected_clear':'t',
              'owner_world_graph_reviewed':'t'}
        blocked={**good,'r50_protected_clear':'f'}
        self.assertEqual(len(select(discover([row]),[good])[0]),1)
        self.assertEqual(select(discover([row]),[blocked])[0],[])

    def test_unknown_boolean_token_holds(self):
        row={**STORY,'not_deleted':'maybe'}
        with self.assertRaises(Hold):
            discover([row])

    def test_discover_rejects_low_activity(self):
        x={**STORY,'assistant_completed':'49'};self.assertEqual(discover([x]),[])
    def test_discover_rejects_missing_card(self):
        x={**STORY,'has_world':'false'};self.assertEqual(discover([x]),[])
    def test_duplicate_inventory_holds(self):
        with self.assertRaises(Hold):discover([STORY,STORY])
    def test_no_guard_discovery_only(self):
        inv=self.csvfile('inventory.csv',[STORY]);x=audit(self.args(inv))
        self.assertIn('DISCOVERY_ONLY',x['status']);self.assertFalse(x['expansion_allowed'])
    def test_guards_false_blocked(self):
        entries=discover([STORY]); bad={**GUARD,'r50_protected_clear':'false'}
        picked,pool=select(entries,[bad]);self.assertEqual(picked,[])
    def test_no_world_component_blocked(self):
        picked,pool=select(discover([STORY]),[{**GUARD,'world_component':''}]);self.assertFalse(picked)
    def test_selection_private_only_safe_stdout(self):
        inv=self.csvfile('a.csv',[STORY]); g=self.csvfile('b.csv',[GUARD]); out=self.sec/'selected.json'
        safe=audit(self.args(inv,g,out));self.assertEqual(safe['picked_story_count'],1)
        self.assertNotIn('id1',json.dumps(safe));self.assertTrue(out.exists())
        self.assertEqual(out.stat().st_mode&0o777,0o600)
        self.assertTrue(json.loads(out.read_text())['requires_owner_confirmation_before_expansion'])
    def test_world_component_unique(self):
        x=[{**STORY,'story_id':'id1'}, {**STORY,'story_id':'id2'}]
        g=[GUARD,{**GUARD,'story_id':'id2'}]
        picked,_=select(discover(x),g);self.assertEqual(len(picked),1)
    def test_quota(self):
        x=[];g=[]
        cats=['original']*7+['dice_cocreate']*3+['ai_assisted']*2
        for i,c in enumerate(cats):
            sid=f'id{i}';x.append({**STORY,'story_id':sid,'source_type':c})
            g.append({**GUARD,'story_id':sid,'world_component':f'w{i}'})
        picked,_=select(discover(x),g)
        self.assertEqual(len(picked),5)
        self.assertEqual({c:sum(p['source_type']==c for p in picked) for c in CATEGORIES},CATEGORIES)
    def test_requires_private_output_guarded(self):
        inv=self.csvfile('inv.csv',[STORY]);g=self.csvfile('guard.csv',[GUARD])
        with self.assertRaises(Hold):audit(self.args(inv,g))
    def test_rejects_overwrite(self):
        inv=self.csvfile('inv2.csv',[STORY]);g=self.csvfile('guard2.csv',[GUARD]);o=self.sec/'chosen.json'
        audit(self.args(inv,g,o))
        with self.assertRaises(Hold):audit(self.args(inv,g,o))
if __name__=='__main__':unittest.main()
