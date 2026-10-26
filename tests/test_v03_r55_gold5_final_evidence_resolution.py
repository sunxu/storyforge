"""Synthetic-only private Owner docket tests. No real private R55 text or R50 access."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import v03_r55_gold5_final_evidence_resolution as final
import v03_r55_gold5_third_evidence_audit as third
import v03_r55_gold5_review_freeze as fr
import test_v03_r55_gold5_third_evidence_audit as fixtures
import test_v03_r55_gold5_second_evidence_audit as synth


class FinalResolutionSynthetic(unittest.TestCase):
    def setUp(self):
        self.fx=fixtures.ThirdAuditSynthetic('test_prev_validation_and_count')
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.third_pack,_=self.fx.pack()
        self.third_done=self.fx.filled(self.third_pack)
        self.third_out=self.fx.root/'third-validated'
        self.third_safe=third.validate(self.third_pack,self.third_done,self.third_out)
        attrs=('PINNED_THIRD_BLIND','PINNED_THIRD_DECISIONS','PINNED_THIRD_COMPARISON',
               'EXPECTED_THIRD_CANDIDATES','EXPECTED_THIRD_CATEGORY_SLOTS',
               'EXPECTED_ORIGINAL_DISPUTES','EXPECTED_ADDITIONAL_CONTRADICTIONS','EXPECTED_PRIORITY')
        old=[getattr(final,x) for x in attrs]
        self.addCleanup(lambda:[setattr(final,x,v) for x,v in zip(attrs,old)])
        final.PINNED_THIRD_BLIND=third.digest((self.third_pack/'reviewers/R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json').read_bytes())
        final.PINNED_THIRD_DECISIONS=third.digest(self.third_done.read_bytes())
        final.PINNED_THIRD_COMPARISON=third.digest((self.third_out/'R55_GOLD5_THIRD_AUDIT_TRIAGE_COMPARISON_PRIVATE.json').read_bytes())
        final.EXPECTED_THIRD_CANDIDATES=self.third_safe['third_candidate_count']
        final.EXPECTED_THIRD_CATEGORY_SLOTS=self.third_safe['third_category_decisions']
        final.EXPECTED_ORIGINAL_DISPUTES=self.third_safe['original_unresolved_category_count']
        # synthetic 3rd votes REJECTED; first+second agree CONFIRMED only if
        # both had been CONFIRMED, which cannot arise with all-REJECTED 2nd
        final.EXPECTED_ADDITIONAL_CONTRADICTIONS=0
        final.EXPECTED_PRIORITY=final.EXPECTED_ORIGINAL_DISPUTES
        self.root=self.fx.root

    def checked(self):
        return final.checked_all(self.fx.fx.pack,self.fx.fx.first,self.fx.fx.safe,
                                 self.fx.second_pack,self.fx.second_decisions,self.fx.second_val,
                                 self.third_pack,self.third_done,self.third_out)

    def prepared(self):
        state=self.checked()
        pack=self.root/'final-pack'
        return pack,final.prepare(state,pack)

    def filled(self,pack,kind='all',value='REJECTED'):
        source=json.loads((pack/'owner/R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json').read_text())
        tiers={item['candidate_token']:item['categories'] for item in source['items']}
        obj=json.loads((pack/'owner/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_BLANK_PRIVATE.json').read_text())
        for item in obj['items']:
            for cat in final.CATS:
                if kind=='priority' and not tiers[item['candidate_token']][cat]['priority_reason'].startswith('P0_'):
                    continue
                item[cat]={'final_verdict':value,'issue_subtype':('not_applicable' if value=='REJECTED' else 'undetermined' if value=='HOLD_INSUFFICIENT_EVIDENCE' else 'hard_fact_mismatch' if cat=='hard_fact_or_ban' else 'not_applicable'),
                           'candidate_quote':'synthetic reply' if value=='CONFIRMED' else '',
                           'context_quote':'player chooses' if value=='CONFIRMED' else '',
                           'rationale':'I independently re-read the synthetic source, rules and response.',
                           'evidence_gap':'The hypothetical timepoint evidence is unavailable.' if value=='HOLD_INSUFFICIENT_EVIDENCE' else '',
                           'final_decider_id':'owner-001'}
        f=self.root/('completed-'+kind+'-'+value+'.json')
        synth.write(f,obj)
        return f

    def test_real_pins_are_64(self):
        for k in ('PINNED_THIRD_BLIND','PINNED_THIRD_DECISIONS','PINNED_THIRD_COMPARISON'):
            self.assertEqual(len(getattr(final,k)),64)

    def test_full_replay_and_build(self):
        p,safe=self.prepared()
        self.assertEqual(safe['source_category_slots'],152)
        self.assertEqual(safe['priority_category_slots'],final.EXPECTED_PRIORITY)
        self.assertFalse(safe['r50_accessed'])
        self.assertEqual((p/'owner/R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json').stat().st_mode&0o777,0o600)

    def test_priority_validation(self):
        pack,_=self.prepared()
        result=final.validate(pack,self.filled(pack,'priority'),self.root/'verified',priority_only=True)
        self.assertEqual(result['verified_category_judgments'],final.EXPECTED_PRIORITY)
        self.assertEqual(result['not_reviewed_in_this_validation'],152-final.EXPECTED_PRIORITY)
        self.assertIn('NOT_FINAL',result['status'])

    def test_all_validation(self):
        pack,_=self.prepared()
        result=final.validate(pack,self.filled(pack),self.root/'verified',priority_only=False)
        self.assertEqual(result['verified_category_judgments'],152)
        self.assertEqual(result['verdict_counts'],{'REJECTED':152})
        self.assertTrue(result['semantic_correctness_not_automatically_certified'])

    def test_confirmed_quote_and_subtype(self):
        pack,_=self.prepared()
        result=final.validate(pack,self.filled(pack,value='CONFIRMED'),self.root/'verified',priority_only=False)
        self.assertEqual(result['verdict_counts']['CONFIRMED'],152)

    def test_hold_requires_gap(self):
        pack,_=self.prepared()
        result=final.validate(pack,self.filled(pack,value='HOLD_INSUFFICIENT_EVIDENCE'),self.root/'verified',priority_only=False)
        self.assertEqual(result['HOLD_categories_still_unresolved'],152)

    def test_blank_fails(self):
        pack,_=self.prepared()
        with self.assertRaisesRegex(fr.Hold,'FINAL_VERDICT_NOT_FILLED'):
            final.validate(pack,pack/'owner/R55_GOLD5_FINAL_EVIDENCE_DECISIONS_BLANK_PRIVATE.json',self.root/'bad',priority_only=True)

    def test_modified_third_decisions_fail(self):
        self.third_done.write_bytes(self.third_done.read_bytes()+b'\n')
        with self.assertRaisesRegex(fr.Hold,'THIRD_DECISIONS_PIN_MISMATCH'):
            self.checked()

    def test_modified_third_comparison_fail(self):
        p=self.third_out/'R55_GOLD5_THIRD_AUDIT_TRIAGE_COMPARISON_PRIVATE.json'
        p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(fr.Hold,'THIRD_COMPARE_PIN_MISMATCH'):
            self.checked()

    def test_source_modified_fail(self):
        pack,_=self.prepared()
        p=pack/'owner/R55_GOLD5_FINAL_EVIDENCE_OWNER_DOCKET_PRIVATE.json'
        p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(fr.Hold,'FINAL_DOCKET_HASH_MISMATCH'):
            final.validate(pack,self.filled(pack),self.root/'bad',priority_only=False)

    def test_fake_quote_fails(self):
        pack,_=self.prepared()
        path=self.filled(pack,value='CONFIRMED')
        obj=json.loads(path.read_text());obj['items'][0]['agency']['candidate_quote']='fabricated'
        synth.write(path,obj)
        with self.assertRaisesRegex(fr.Hold,'FINAL_CANDIDATE_QUOTE_NOT_EXACT'):
            final.validate(pack,path,self.root/'bad',priority_only=False)

    def test_hard_fact_requires_subtype(self):
        pack,_=self.prepared()
        path=self.filled(pack,value='CONFIRMED');obj=json.loads(path.read_text())
        obj['items'][0]['hard_fact_or_ban']['issue_subtype']='not_applicable'
        synth.write(path,obj)
        with self.assertRaisesRegex(fr.Hold,'FINAL_HARD_FACT_MISSING_SUBTYPE'):
            final.validate(pack,path,self.root/'bad',priority_only=False)

    def test_duplicate_token_fails(self):
        pack,_=self.prepared();path=self.filled(pack)
        obj=json.loads(path.read_text());obj['items'][1]['candidate_token']=obj['items'][0]['candidate_token']
        synth.write(path,obj)
        with self.assertRaisesRegex(fr.Hold,'FINAL_COMPLETED_DUPLICATE_TOKEN'):
            final.validate(pack,path,self.root/'bad',priority_only=False)

    def test_no_overwrite(self):
        pack,safe=self.prepared()
        with self.assertRaisesRegex(fr.Hold,'OUTPUT_ALREADY_EXISTS'):
            final.prepare(self.checked(),pack)
        path=self.filled(pack)
        final.validate(pack,path,self.root/'verified',priority_only=False)
        with self.assertRaisesRegex(fr.Hold,'OUTPUT_ALREADY_EXISTS'):
            final.validate(pack,path,self.root/'verified',priority_only=False)

    def test_git_private_output_rejected(self):
        root=self.root/'repo';root.mkdir();(root/'.git').mkdir()
        with self.assertRaisesRegex(fr.Hold,'PRIVATE_OUTPUT_INSIDE_GIT'):
            final.prepare(self.checked(),root/'out')


if __name__=='__main__':unittest.main()
