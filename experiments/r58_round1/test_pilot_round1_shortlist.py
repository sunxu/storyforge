"""Synthetic-only R58 pilot shortlist tests. No protected-world IDs or story content."""
import csv
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from pilot_round1_shortlist import (
    CATEGORIES,
    GATE_NAMES,
    PARSER_VERSION,
    Hold,
    audit,
    discover,
    safe_gate_diagnostics,
    select,
)

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
    def synthetic_exposure_ledger(self,story_ids=('id1',),exposed=()):
        path=self.sec/'test_prior_sft_holds_v2.json'
        rows=[{
            'story_id_PRIVATE':sid,
            'historical_sft_exact_uuid_overlap':sid in exposed,
            'status':('EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE' if sid in exposed
                      else 'HOLD_R50_DEV_OTHER_PROTECTED_UUID_CHECK_PENDING'),
        } for sid in story_ids]
        path.write_text(json.dumps({
            'schema':'r58_round1_g1_prior_sft_exact_id_holds_private_v2',
            'namespace_equivalence_owner_confirmed':True,
            'expansion_allowed':False,'entries':rows,
        }))
        os.chmod(path,0o600)
        return path

    def args(self,inv,guards=None,out=None):
        ledger=self.synthetic_exposure_ledger() if guards else None
        return Namespace(inventory=str(inv),guards=str(guards) if guards else None,
                         prior_sft_holds=str(ledger) if ledger else None,
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

    def test_diagnostic_aggregate_has_one_survivor(self):
        stats=safe_gate_diagnostics([STORY])
        self.assertEqual(stats['parsed_rows'],1)
        self.assertEqual(stats['individual_pass_counts']['has_opening'],1)
        self.assertEqual(stats['cumulative_survivor_counts']['recognized_source_type'],1)
        self.assertTrue(stats['parser_psql_true_supported'])
        self.assertTrue(stats['parser_psql_false_supported'])

    def test_diagnostic_reports_single_gate_failure(self):
        failed={**STORY,'has_opening':'f'}
        stats=safe_gate_diagnostics([STORY,failed])
        self.assertEqual(stats['individual_pass_counts']['has_opening'],1)
        self.assertEqual(stats['cumulative_survivor_counts']['recognized_source_type'],1)
        self.assertEqual(stats['cumulative_survivor_counts']['has_world'],2)

    def test_diagnostic_unknown_value_holds(self):
        failed={**STORY,'has_opening':'uninterpretable'}
        with self.assertRaises(Hold):
            safe_gate_diagnostics([failed])

    def test_diagnostic_does_not_echo_story_ids_or_strings(self):
        """Fixed gate labels may name v2_sandbox; CSV values must not escape."""
        row={**STORY,'story_id':'PRIVATE_SYNTHETIC_ID',
             'private_extra_field':'PRIVATE_SYNTHETIC_CANARY'}
        stats=safe_gate_diagnostics([row])
        text=json.dumps(stats)
        self.assertNotIn('PRIVATE_SYNTHETIC_ID',text)
        self.assertNotIn('PRIVATE_SYNTHETIC_CANARY',text)
        self.assertNotIn('"story_id"',text)
        self.assertNotIn('"source_type"',text)
        self.assertNotIn('"v2_sandbox"',text)
        self.assertEqual(set(stats), {
            'individual_pass_counts','cumulative_survivor_counts',
            'parser_psql_true_supported','parser_psql_false_supported',
            'parsed_rows',
        })
        for key in ('individual_pass_counts','cumulative_survivor_counts'):
            self.assertEqual(set(stats[key]),set(GATE_NAMES))
            self.assertTrue(all(type(n) is int for n in stats[key].values()))
        # Exercise the public SAFE audit projection as well, not only the helper.
        inventory=self.csvfile('privacy.csv',[row])
        safe=json.dumps(audit(self.args(inventory)))
        self.assertNotIn('PRIVATE_SYNTHETIC_ID',safe)
        self.assertNotIn('PRIVATE_SYNTHETIC_CANARY',safe)
        self.assertNotIn('"story_id"',safe)

    def test_large_unexpected_zero_is_explicit_hold(self):
        rows=[{**STORY,'story_id':f's{i}','has_opening':'f'} for i in range(101)]
        inp=self.csvfile('zero.csv',rows)
        result=audit(self.args(inp))
        self.assertEqual(result['status'],'R58_ROUND1_UNEXPECTED_ZERO__CSV_GATE_HOLD')
        self.assertEqual(result['metadata_eligible'],0)
        self.assertFalse(result['expansion_allowed'])

    def test_parser_version_marker_and_normalized_enums(self):
        x={**STORY,'story_type':' v2_sandbox ',
           'moderation_status':' approved ', 'source_type':' original '}
        inp=self.csvfile('enums.csv',[x])
        result=audit(self.args(inp))
        self.assertEqual(result['parser_version'],PARSER_VERSION)
        self.assertEqual(result['metadata_eligible'],1)
        self.assertEqual(result['metadata_eligible_by_source']['original'],1)

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
    def test_owner_world_identity_derived_from_uuid_without_manual_graph(self):
        guard={**GUARD,'world_component':'','owner_world_graph_reviewed':'false'}
        picked,pool=select(discover([STORY]),[guard])
        self.assertEqual(len(picked),1)
        self.assertEqual(picked[0]['world_component'],'id1')
    def test_selection_private_only_safe_stdout(self):
        inv=self.csvfile('a.csv',[STORY]); g=self.csvfile('b.csv',[GUARD]); out=self.sec/'selected.json'
        safe=audit(self.args(inv,g,out));self.assertEqual(safe['picked_story_count'],1)
        self.assertNotIn('id1',json.dumps(safe));self.assertTrue(out.exists())
        self.assertEqual(out.stat().st_mode&0o777,0o600)
        self.assertTrue(json.loads(out.read_text())['requires_owner_confirmation_before_expansion'])
    def test_owner_world_component_is_each_distinct_story_id(self):
        x=[{**STORY,'story_id':'id1'}, {**STORY,'story_id':'id2'}]
        g=[GUARD,{**GUARD,'story_id':'id2'}]
        picked,_=select(discover(x),g)
        self.assertEqual(len(picked),2)
        self.assertEqual({item['world_component'] for item in picked},{'id1','id2'})
    def test_owner_world_policy_does_not_waive_remaining_protected_guards(self):
        base={**GUARD,'owner_world_graph_reviewed':'false','world_component':''}
        for flag in ('r50_protected_clear','prior_sft_clear',
                     'r55_r57_dev_clear','other_protected_clear'):
            self.assertEqual(select(discover([STORY]),[{**base,flag:'false'}])[0],[])

    def test_owner_world_identity_private_shortlist_still_not_admitted(self):
        inv=self.csvfile('owner_inv.csv',[STORY])
        guard={**GUARD,'owner_world_graph_reviewed':'false','world_component':''}
        g=self.csvfile('owner_guards.csv',[guard])
        out=self.sec/'owner-shortlist.json'
        safe=audit(self.args(inv,g,out))
        self.assertEqual(safe['picked_story_count'],1)
        self.assertFalse(safe['cross_uuid_semantic_review_required'])
        private=json.loads(out.read_text())
        self.assertEqual(private['status'],'SHORTLIST_ONLY__NOT_ADMITTED')
        self.assertFalse(private['requires_world_review'])
        self.assertTrue(private['requires_protected_set_evidence_review'])
        self.assertEqual(private['selected'][0]['world_component'],'id1')

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
    def test_guarded_selection_requires_exposure_ledger_even_if_all_flags_true(self):
        inv=self.csvfile('exp_inv.csv',[STORY])
        guards=self.csvfile('exp_guard.csv',[GUARD])
        args=self.args(inv,guards,self.sec/'exp_selected.json')
        args.prior_sft_holds=None
        with self.assertRaises(Hold):
            audit(args)
        self.assertFalse((self.sec/'exp_selected.json').exists())

    def test_guarded_selection_hard_excludes_known_prior_sft_uuid(self):
        inv=self.csvfile('prior_inv.csv',[STORY])
        guards=self.csvfile('prior_guard.csv',[GUARD])
        args=self.args(inv,guards,self.sec/'prior_selected.json')
        args.prior_sft_holds=str(self.synthetic_exposure_ledger(exposed=('id1',)))
        result=audit(args)
        self.assertEqual(result['prior_sft_exposed_stories_hard_excluded'],1)
        self.assertEqual(result['picked_story_count'],0)
        self.assertEqual(result['owner_claimed_cleared_count'],0)
        self.assertFalse((self.sec/'prior_selected.json').exists())

    def test_guarded_selection_rejects_ledger_missing_guard_story(self):
        inv=self.csvfile('missing_inv.csv',[STORY])
        guards=self.csvfile('missing_guard.csv',[GUARD])
        args=self.args(inv,guards,self.sec/'missing_selected.json')
        args.prior_sft_holds=str(self.synthetic_exposure_ledger(story_ids=('unrelated',)))
        with self.assertRaises(Hold):
            audit(args)

    def test_rejects_overwrite(self):
        inv=self.csvfile('inv2.csv',[STORY]);g=self.csvfile('guard2.csv',[GUARD]);o=self.sec/'chosen.json'
        audit(self.args(inv,g,o))
        with self.assertRaises(Hold):audit(self.args(inv,g,o))
if __name__=='__main__':unittest.main()
