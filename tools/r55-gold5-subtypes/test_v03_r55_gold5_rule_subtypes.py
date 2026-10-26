import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from v03_r55_gold5_rule_subtypes import validate, SUBTYPES, SCHEMA


def fixture():
    arms = ['base','gold','v01','v02','v03']
    docket={'items':[]}
    decisions={'items':[]}
    proposal={'schema':SCHEMA,'source_sha256':{'docket':'a'*64,'decisions':'b'*64},'confirmed_subtype_records':[],'hold_evidence_records':[]}
    for i in range(76):
        token=f'K{i:025x}'
        arm=arms[i%5];case=f'W{i:014x}'
        hard='CONFIRMED' if i <62 else ('HOLD_INSUFFICIENT_EVIDENCE' if i<66 else 'REJECTED')
        agency='CONFIRMED' if i<17 else 'REJECTED'
        docket['items'].append({'candidate_token':token,'case_token':case,'source_arm_PRIVATE':arm})
        decisions['items'].append({'candidate_token':token,'agency':{'final_verdict':agency},'hard_fact_or_ban':{'final_verdict':hard,'issue_subtype':'hard_fact_mismatch','candidate_quote':'candidate','context_quote':'rule','rationale':'reason','evidence_gap':'evidence missing'}})
        if hard=='CONFIRMED':
            proposal['confirmed_subtype_records'].append({'candidate_token':token,'case_token_PRIVATE':case,'source_arm_PRIVATE':arm,'category':'hard_fact_or_ban','original_final_verdict':hard,'legacy_issue_subtype':'hard_fact_mismatch','diagnostic_subtype':SUBTYPES[i%len(SUBTYPES)],'candidate_quote':'candidate','context_quote':'rule','rationale':'reason'})
        elif hard=='HOLD_INSUFFICIENT_EVIDENCE':
            proposal['hold_evidence_records'].append({'candidate_token':token,'case_token_PRIVATE':case,'source_arm_PRIVATE':arm,'final_verdict':hard,'original_evidence_gap':'evidence missing','original_rationale':'reason','next_action':'RETAIN_HOLD_UNTIL_NEW_EVIDENCE'})
    return docket, decisions, proposal


class DiagnosticTests(unittest.TestCase):
    def test_accept_complete(self):
        d,v,p=fixture();res=validate(d,v,p,'a'*64,'b'*64)
        self.assertEqual(sum(res['subtype_counts'].values()),62)
        self.assertEqual(res['hard_fact_or_ban_hold_unchanged'],4)
        self.assertFalse(res['owner_signoff'])
    def test_refuse_docket_pin(self):
        d,v,p=fixture()
        with self.assertRaises(AssertionError):validate(d,v,p,'c'*64,'b'*64)
    def test_refuse_decision_pin(self):
        d,v,p=fixture()
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'c'*64)
    def test_refuse_source_missing(self):
        d,v,p=fixture();d['items'].pop()
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_changed_token_order(self):
        d,v,p=fixture();v['items'][0],v['items'][1]=v['items'][1],v['items'][0]
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_missing_confirmed_annotation(self):
        d,v,p=fixture();p['confirmed_subtype_records'].pop()
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_missing_hold(self):
        d,v,p=fixture();p['hold_evidence_records'].pop()
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_unrecognized_label(self):
        d,v,p=fixture();p['confirmed_subtype_records'][0]['diagnostic_subtype']='made_up'
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_modified_evidence_quote(self):
        d,v,p=fixture();p['confirmed_subtype_records'][0]['candidate_quote']='forged'
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_changed_rationale(self):
        d,v,p=fixture();p['confirmed_subtype_records'][0]['rationale']='other'
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_forced_hold(self):
        d,v,p=fixture();p['hold_evidence_records'][0]['final_verdict']='REJECTED'
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_arm_changed(self):
        d,v,p=fixture();p['confirmed_subtype_records'][0]['source_arm_PRIVATE']='gold'
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_legacy_subtype_changed(self):
        d,v,p=fixture();p['confirmed_subtype_records'][0]['legacy_issue_subtype']='explicit_banned_phrase'
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_refuse_source_final_count_changed(self):
        d,v,p=fixture();v['items'][0]['agency']['final_verdict']='REJECTED'
        with self.assertRaises(AssertionError):validate(d,v,p,'a'*64,'b'*64)
    def test_private_tokens_not_in_safe_report(self):
        d,v,p=fixture();res=validate(d,v,p,'a'*64,'b'*64)
        s=json.dumps(res);self.assertNotIn('candidate_token',s);self.assertNotIn('K000',s)

if __name__ == '__main__':unittest.main()
