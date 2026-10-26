"""Synthetic R55 Gold5 event review tests. No source story or R50 accessed."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import v03_r55_gold5_event_arbitration as a
import v03_r55_gold5_owner_unblind as ub
import v03_r55_gold5_review_freeze as fr
from test_v03_r55_gold5_owner_unblind import FakeV2


class TestEventPipeline(unittest.TestCase):
    def setUp(self):
        self.fix=FakeV2('test_complete_verify')
        self.fix.setUp()
        self.state=self.fix.verify()
        self.mappings,_=ub.validate_key(self.state,pins=self.fix.pins)
        self.root=self.fix.root

    def tearDown(self):
        self.fix.tearDown()

    def flag(self,mode='pair',case=0,reviewer=0,agency='LEFT',hard=None):
        cols=fr.MODES[mode]
        row=self.state['rows'][mode][reviewer][case]
        if agency is not None:
            row[cols[3]]=agency
        if hard is not None:
            row[cols[4]]=hard
        row['逐事件严重问题证据']='synthetic evidence string'
        return row

    def test_empty_flagged_scope_holds(self):
        with self.assertRaisesRegex(fr.Hold,'NO_FLAGGED_GROUPS_TO_REVIEW'):
            a.groups_from_frozen(self.state,self.mappings)

    def test_all_scope_produces_all_100(self):
        items,ix,safe=a.groups_from_frozen(self.state,self.mappings,scope='all')
        self.assertEqual(len(items),100)
        self.assertEqual(len(ix),100)
        self.assertEqual(safe['flagged_case_arm_groups'],0)
        self.assertTrue(safe['original_gold_is_not_a_model'])

    def test_pair_one_flag_yields_one_group(self):
        self.flag()
        items,ix,safe=a.groups_from_frozen(self.state,self.mappings)
        self.assertEqual(len(items),1)
        self.assertEqual(ix[0]['source_arm_private'],'v02')
        self.assertEqual(safe['flagged_reviewer_case_arm_category_marks'],1)

    def test_same_candidate_cross_round_coalesces_group_not_event(self):
        self.flag('pair',0,0,'LEFT')
        self.flag('four',0,1,'C')
        self.flag('five',0,2,'NONE','D')
        items,ix,safe=a.groups_from_frozen(self.state,self.mappings)
        self.assertEqual(len(items),1)
        self.assertEqual(safe['flagged_reviewer_case_arm_category_marks'],3)
        self.assertEqual(len(ix[0]['flag_observations_UNADJUDICATED']),3)

    def test_both_pair_two_groups(self):
        self.flag('pair',1,0,'BOTH')
        items,ix,_=a.groups_from_frozen(self.state,self.mappings)
        self.assertEqual(len(items),2)
        self.assertEqual({r['source_arm_private'] for r in ix},{'v02','v03'})

    def test_gold_will_be_considered_but_never_model_named_to_arbiter(self):
        self.flag('five',0,0,'A')
        items,ix,safe=a.groups_from_frozen(self.state,self.mappings)
        self.assertEqual(ix[0]['source_arm_private'],'gold')
        self.assertNotIn('source_arm_private',items[0])
        self.assertEqual(items[0]['must_evaluate_both_categories'],list(a.CATEGORIES))

    def test_context_cross_round_mismatch_holds(self):
        self.flag()
        self.state['clean']['four'][2][0]['历史对话']='tampered context'
        with self.assertRaisesRegex(fr.Hold,'CROSS_ROUND_SOURCE_CONTEXT_MISMATCH'):
            a.groups_from_frozen(self.state,self.mappings)

    def test_source_reply_hash_mismatch_holds(self):
        self.flag()
        self.state['clean']['five'][0][0]['回复D']='tampered response'
        with self.assertRaisesRegex(fr.Hold,'REPLY_SHA_NOT_MATCH_FROZEN_KEY'):
            a.groups_from_frozen(self.state,self.mappings)

    def test_prepare_generates_separate_coordinator_and_blind(self):
        self.flag()
        out=self.root/'event-pack'
        s=a.prepare(self.state,out,pins=self.fix.pins)
        self.assertEqual(s['arbitration_items'],1)
        blind=json.loads((out/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json').read_text())
        index=json.loads((out/'coordinator/R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json').read_text())
        self.assertNotIn('source_arm_private',blind['items'][0])
        self.assertIn('source_arm_private',index['records'][0])
        self.assertNotIn('fake bg',(out/'safe/R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json').read_text())
        self.assertEqual((out/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json').stat().st_mode & 0o777,0o600)

    def test_prepare_no_overwrite(self):
        self.flag()
        out=self.root/'event-pack'
        a.prepare(self.state,out,pins=self.fix.pins)
        with self.assertRaisesRegex(fr.Hold,'OUTPUT_DIR_ALREADY_EXISTS'):
            a.prepare(self.state,out,pins=self.fix.pins)

    def test_validate_rejected_without_evidence_quote(self):
        self.flag()
        out=self.root/'event-pack'
        a.prepare(self.state,out,pins=self.fix.pins)
        decision=json.loads((out/'reviewers/R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json').read_text())
        for row in decision['items']:
            for cat in a.CATEGORIES:
                row[cat]['verdict']='REJECTED'
                row[cat]['rationale']='No grounded violation in the frozen synthetic sample.'
        file=self.root/'completed.json'
        file.write_text(json.dumps(decision,ensure_ascii=False),encoding='utf-8')
        safe=a.verify_decisions(out,file,self.root/'verified-out')
        self.assertEqual(safe['adjudication_items_checked'],1)
        self.assertEqual(safe['verdict_counts_by_category_and_arm']['agency']['v02']['REJECTED'],1)
        self.assertTrue(safe['r50_accessed'] is False)

    def test_validate_confirmed_exact_quotes(self):
        self.flag()
        out=self.root/'event-pack';a.prepare(self.state,out,pins=self.fix.pins)
        src=json.loads((out/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json').read_text())
        dec=json.loads((out/'reviewers/R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json').read_text())
        d=dec['items'][0]
        for cat in a.CATEGORIES:
            d[cat]={'verdict':'CONFIRMED','candidate_quote':src['items'][0]['匿名候选回复'],
                    'context_quote':'fake bg', 'rationale':'The example proves a synthetic source-grounded issue.'}
        f=self.root/'decisions.json';f.write_text(json.dumps(dec,ensure_ascii=False))
        safe=a.verify_decisions(out,f,self.root/'validated')
        self.assertEqual(safe['verdict_counts_by_category_and_arm']['agency']['v02']['CONFIRMED'],1)

    def test_validate_ungrounded_quote_holds(self):
        self.flag();out=self.root/'event-pack';a.prepare(self.state,out,pins=self.fix.pins)
        dec=json.loads((out/'reviewers/R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json').read_text())
        for cat in a.CATEGORIES:
            dec['items'][0][cat]={'verdict':'CONFIRMED','candidate_quote':'not an actual exact quote',
                                  'context_quote':'fake bg','rationale':'Synthetic rationale with sufficient length.'}
        f=self.root/'decisions.json';f.write_text(json.dumps(dec))
        with self.assertRaisesRegex(fr.Hold,'CONFIRMED_CANDIDATE_QUOTE_NOT_SOURCE_EXACT'):
            a.verify_decisions(out,f,self.root/'validated')

    def test_validate_unfilled_verdict_holds(self):
        self.flag();out=self.root/'event-pack';a.prepare(self.state,out,pins=self.fix.pins)
        f=out/'reviewers/R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json'
        with self.assertRaisesRegex(fr.Hold,'UNFILLED_OR_INVALID_VERDICT'):
            a.verify_decisions(out,f,self.root/'validated')

    def test_validate_source_packet_mutation_holds(self):
        self.flag();out=self.root/'event-pack';a.prepare(self.state,out,pins=self.fix.pins)
        p=out/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json'
        p.write_bytes(p.read_bytes()+b'changed')
        f=out/'reviewers/R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json'
        with self.assertRaisesRegex(fr.Hold,'ARBITER_PACKET_HASH_MISMATCH'):
            a.verify_decisions(out,f,self.root/'validated')

    def test_validate_duplicate_token_holds(self):
        self.flag('pair',0,0,'BOTH');out=self.root/'event-pack';a.prepare(self.state,out,pins=self.fix.pins)
        dec=json.loads((out/'reviewers/R55_GOLD5_ARBITER_DECISIONS_BLANK_PRIVATE.json').read_text())
        dec['items'][1]['candidate_token']=dec['items'][0]['candidate_token']
        f=self.root/'decisions.json';f.write_text(json.dumps(dec))
        with self.assertRaisesRegex(fr.Hold,'DECISION_TOKEN_SET_MISMATCH'):
            a.verify_decisions(out,f,self.root/'validated')

    def test_key_pin_mismatch_holds(self):
        self.flag();bad={**self.fix.pins,'key':'0'*64}
        with self.assertRaisesRegex(fr.Hold,'COORDINATOR_KEY_OWNER_SHA_MISMATCH'):
            a.prepare(self.state,self.root/'bad',pins=bad)

    def test_not_git(self):
        self.flag()
        d=self.root/'git-root';d.mkdir();(d/'.git').mkdir()
        with self.assertRaisesRegex(fr.Hold,'PRIVATE_OUTPUT_INSIDE_GIT'):
            a.prepare(self.state,d/'private-dir',pins=self.fix.pins)


if __name__=='__main__':
    unittest.main()
