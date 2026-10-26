"""Synthetic-only third audit; exercises prior validators, source hashes and privacy."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import v03_r55_gold5_third_evidence_audit as third
import v03_r55_gold5_second_evidence_audit as second
import v03_r55_gold5_review_freeze as fr
import test_v03_r55_gold5_second_evidence_audit as synth

class ThirdAuditSynthetic(unittest.TestCase):
    def setUp(self):
        self.fx=synth.SyntheticFrozen76('test_first_input_76_items_152_category_counts')
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.second_pack,self.second_prep=self.fx.make_pack()
        self.second_decisions=self.fx.scored(self.second_pack,mode='REJECTED')
        self.second_val=self.fx.root/'validated-second'
        self.second_safe=second.validate_second(self.second_pack,self.second_decisions,self.second_val)
        attrnames=('PINNED_SECOND_BLIND','PINNED_SECOND_DECISIONS','EXPECTED_SECOND_ITEMS',
                   'EXPECTED_SECOND_CATEGORIES','EXPECTED_TERTIARY_CATEGORY_COUNT')
        old=tuple(getattr(third,k) for k in attrnames)
        self.addCleanup(lambda: [setattr(third,k,v) for k,v in zip(attrnames,old)])
        third.PINNED_SECOND_BLIND=third.digest((self.second_pack/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json').read_bytes())
        third.PINNED_SECOND_DECISIONS=third.digest(self.second_decisions.read_bytes())
        third.EXPECTED_SECOND_ITEMS=self.second_safe['selected_candidate_count']
        third.EXPECTED_SECOND_CATEGORIES=self.second_safe['second_category_decisions_validated']
        third.EXPECTED_TERTIARY_CATEGORY_COUNT=self.second_safe['first_HOLD_or_disagreement_needs_tertiary_count']
        self.root=self.fx.root

    def state(self):
        return third.checked_twice(self.fx.pack,self.fx.first,self.fx.safe,
                                   self.second_pack,self.second_decisions,self.second_val)

    def pack(self):
        st=self.state();target=self.root/'third-pack';rc=third.prepare(st,target)
        return target,rc

    def filled(self,pack,mode='REJECTED'):
        data=json.loads((pack/'reviewers/R55_GOLD5_THIRD_AUDIT_DECISIONS_BLANK_PRIVATE.json').read_text())
        for ans in data['items']:
            for cat in third.CATS:
                ans[cat]={'verdict':mode,
                          'candidate_quote':'synthetic reply' if mode=='CONFIRMED' else '',
                          'context_quote':'player chooses' if mode=='CONFIRMED' else '',
                          'rationale':'Independently checked original synthetic visible rules.'}
        out=self.root/'third-done.json';synth.write(out,data);return out

    def test_prev_validation_and_count(self):
        st=self.state()
        self.assertEqual(sum(st['focus'].values()),third.EXPECTED_TERTIARY_CATEGORY_COUNT)
        self.assertLessEqual(len(st['chosen']),third.EXPECTED_SECOND_ITEMS)

    def test_pinned_real_constants_nonempty(self):
        self.assertEqual(len(third.PINNED_SECOND_BLIND),64)
        self.assertEqual(len(third.PINNED_SECOND_DECISIONS),64)

    def test_output_count_union_and_both_categories(self):
        pack,rec=self.pack()
        self.assertEqual(rec['required_third_category_judgments'],rec['selected_unique_candidates']*2)
        self.assertEqual(rec['category_disagreements_or_first_hold_selected'],third.EXPECTED_TERTIARY_CATEGORY_COUNT)
        self.assertFalse(rec['r50_accessed'])
        self.assertFalse(rec['automatic_final_adjudication'])

    def test_no_prior_verdicts_leaked(self):
        pack,rec=self.pack()
        source=(pack/'reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json').read_text()
        for word in ('source_arm_private','first_verdict_private','second_verdict_private',
                     'original_first_candidate_token_private','unresolved_categories_private',
                     'first_HOLD_or_disagreement','REJECTED__TO__CONFIRMED'):
            self.assertNotIn(word,source)
        private=(pack/'coordinator/R55_GOLD5_THIRD_AUDIT_INDEX_PRIVATE.json').read_text()
        self.assertIn('first_verdict_private',private)
        self.assertEqual((pack/'reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json').stat().st_mode & 0o777,0o600)

    def test_no_overwrite(self):
        st=self.state();self.pack()
        with self.assertRaisesRegex(fr.Hold,'OUTPUT_ALREADY_EXISTS'):
            third.prepare(st,self.root/'third-pack')

    def test_outside_git(self):
        st=self.state();p=self.root/'repo';p.mkdir();(p/'.git').mkdir()
        with self.assertRaisesRegex(fr.Hold,'PRIVATE_OUTPUT_INSIDE_GIT'):
            third.prepare(st,p/'second-level'/'third')

    def test_second_blind_modification_holds(self):
        f=self.second_pack/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json'
        f.write_bytes(f.read_bytes()+b' ')
        with self.assertRaisesRegex(fr.Hold,'PINNED_SECOND_BLIND_SHA_MISMATCH'):
            self.state()

    def test_second_decisions_modification_holds(self):
        self.second_decisions.write_bytes(self.second_decisions.read_bytes()+b' ')
        with self.assertRaisesRegex(fr.Hold,'PINNED_SECOND_DECISIONS_SHA_MISMATCH'):
            self.state()

    def test_safe_receipt_mismatch_holds(self):
        p=self.second_val/'R55_GOLD5_SECOND_AUDIT_SAFE_COUNT_ONLY.json'
        obj=json.loads(p.read_text());obj['same_verdict_count']=999
        synth.write(p,obj)
        with self.assertRaisesRegex(fr.Hold,'SECOND_SAFE_REPLAY_MISMATCH'):
            self.state()

    def test_private_comparison_mismatch_holds(self):
        p=self.second_val/'R55_GOLD5_SECOND_AUDIT_COMPARISON_PRIVATE.json'
        obj=json.loads(p.read_text());obj['warning']='tampered'
        synth.write(p,obj)
        with self.assertRaisesRegex(fr.Hold,'SECOND_COMPARISON_REPLAY_MISMATCH'):
            self.state()

    def test_original_first_modified_holds(self):
        self.fx.first.write_bytes(self.fx.first.read_bytes()+b' ')
        with self.assertRaisesRegex(fr.Hold,'PINNED_FIRST_DECISIONS_SHA_MISMATCH'):
            self.state()

    def test_validate_complete_rejected(self):
        pack,rec=self.pack()
        result=third.validate(pack,self.filled(pack),self.root/'third-validated')
        self.assertEqual(result['third_category_decisions'],rec['required_third_category_judgments'])
        self.assertEqual(result['third_verdict_counts']['REJECTED'],rec['required_third_category_judgments'])
        self.assertEqual(result['original_unresolved_category_count'],third.EXPECTED_TERTIARY_CATEGORY_COUNT)
        self.assertTrue(result['verdict_semantics_not_automatically_certified'])

    def test_validate_complete_confirmed(self):
        pack,rec=self.pack()
        result=third.validate(pack,self.filled(pack,'CONFIRMED'),self.root/'third-validated')
        self.assertEqual(result['third_verdict_counts']['CONFIRMED'],rec['required_third_category_judgments'])

    def test_empty_decisions_holds(self):
        pack,rec=self.pack()
        with self.assertRaisesRegex(fr.Hold,'THIRD_UNFILLED_VERDICT'):
            third.validate(pack,pack/'reviewers/R55_GOLD5_THIRD_AUDIT_DECISIONS_BLANK_PRIVATE.json',self.root/'bad-validated')

    def test_wrong_quote_holds(self):
        pack,rc=self.pack();done=self.filled(pack,'CONFIRMED')
        obj=json.loads(done.read_text());obj['items'][0]['agency']['candidate_quote']='falsified impossible quote'
        synth.write(done,obj)
        with self.assertRaisesRegex(fr.Hold,'THIRD_QUOTE_NOT_EXACT'):
            third.validate(pack,done,self.root/'bad-validated')

    def test_duplicate_token_holds(self):
        pack,rc=self.pack();done=self.filled(pack)
        obj=json.loads(done.read_text());obj['items'][1]['candidate_token']=obj['items'][0]['candidate_token']
        synth.write(done,obj)
        with self.assertRaisesRegex(fr.Hold,'THIRD_DECISIONS_DUPLICATE_TOKEN'):
            third.validate(pack,done,self.root/'bad-validated')

    def test_blind_source_tampering_holds(self):
        pack,rc=self.pack();done=self.filled(pack)
        p=pack/'reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json'
        p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(fr.Hold,'blind_packet_sha256_MISMATCH'):
            third.validate(pack,done,self.root/'bad-validated')

    def test_privatemap_tamper_holds(self):
        pack,rc=self.pack();done=self.filled(pack)
        p=pack/'coordinator/R55_GOLD5_THIRD_AUDIT_INDEX_PRIVATE.json'
        p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(fr.Hold,'private_mapping_sha256_MISMATCH'):
            third.validate(pack,done,self.root/'bad-validated')

    def test_validation_no_overwrite(self):
        pack,rc=self.pack();done=self.filled(pack)
        third.validate(pack,done,self.root/'third-validated')
        with self.assertRaisesRegex(fr.Hold,'OUTPUT_ALREADY_EXISTS'):
            third.validate(pack,done,self.root/'third-validated')

    def test_unresolved_selection_integrity(self):
        pack,rc=self.pack();done=self.filled(pack)
        p=pack/'coordinator/R55_GOLD5_THIRD_AUDIT_INDEX_PRIVATE.json'
        obj=json.loads(p.read_text());obj['records'][0]['unresolved_categories_private']=[]
        # Simulate a malicious actor with write access to the private mapping/receipt.
        synth.write(p,obj)
        safe=pack/'safe/R55_GOLD5_THIRD_AUDIT_PREP_SAFE_COUNT_ONLY.json'
        entry=json.loads(safe.read_text());entry['private_mapping_sha256']=third.digest(p.read_bytes());synth.write(safe,entry)
        with self.assertRaisesRegex(fr.Hold,'THIRD_UNRESOLVED_SELECTION_INVALID|THIRD_UNRESOLVED_CATEGORY_TOTAL_MISMATCH'):
            third.validate(pack,done,self.root/'bad-validated')

if __name__=='__main__':unittest.main()
