"""Synthetic-only audit tests. No real StoryForge stories, model replies, R50 or GPU."""
from __future__ import annotations
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import v03_r55_gold5_second_evidence_audit as second
import v03_r55_gold5_event_arbitration as first
import v03_r55_gold5_review_freeze as fr


def write(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return second.digest(path.read_bytes())


class SyntheticFrozen76(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='r55-second-synth-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.pack=self.root/'first-pack'
        self.first=self.root/'first-done.json'
        self.safe=self.root/'first-safe.json'
        self.original=(second.PINNED_BLIND,second.PINNED_INDEX,second.PINNED_FIRST_DECISIONS)
        self.addCleanup(self.restore)
        tasks=[]; index=[]; decisions=[]
        verdicts=(['CONFIRMED']*57+['HOLD_INSUFFICIENT_EVIDENCE']*22+['REJECTED']*73)
        # Deterministic interleaving of the 152 category verdicts.
        mixed=[verdicts[(i*47)%152] for i in range(152)]
        for i in range(76):
            tok=f'K{i:03d}'
            arm=('base','v01','v02','v03','gold')[i%5]
            response=f'This is a synthetic reply for token index {i}.'
            tasks.append({'candidate_token':tok,'case_token':f'W{i%20:02d}',
                          '故事背景与系统规则':'RULE: player chooses important decisions.',
                          '历史对话':'Earlier synthetic context.',
                          '当前用户输入':'The user makes a synthetic choice.',
                          '匿名候选回复':response,'must_evaluate_both_categories':list(second.CATS),
                          'instructions':'Do not guess model identity.'})
            index.append({'candidate_token':tok,'case_token':f'W{i%20:02d}',
                          'source_arm_private':arm,
                          'response_sha256':second.digest(response.encode())})
            entry={'candidate_token':tok}
            for j,c in enumerate(second.CATS):
                v=mixed[i*2+j]
                entry[c]={'verdict':v,'candidate_quote':'synthetic reply' if v=='CONFIRMED' else '',
                          'context_quote':'player chooses' if v=='CONFIRMED' else '',
                          'rationale':'Synthetic reason citing visible source only.'}
            decisions.append(entry)
        self.tasks=tasks; self.index=index; self.decisions=decisions
        blind=write(self.pack/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json',
                    {'schema':first.SCHEMA+'-blind-items-v1','items':tasks})
        coord=write(self.pack/'coordinator/R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json',
                    {'schema':first.SCHEMA+'-coordinator-index-v1','records':index})
        write(self.pack/'safe/R55_GOLD5_ARBITRATION_PREP_SAFE_COUNT_ONLY.json',
              {'schema':first.SCHEMA+'-safe-prep-v1','scope':'flagged','arbitration_items':76,
               'blind_items_sha256':blind,'coordinator_index_sha256':coord,'r50_accessed':False})
        first_hash=write(self.first,{'schema':first.SCHEMA+'-adjudicator-decisions-v1','items':decisions})
        second.PINNED_BLIND=blind
        second.PINNED_INDEX=coord
        second.PINNED_FIRST_DECISIONS=first_hash
        self.expected=Counter(d[c]['verdict'] for d in decisions for c in second.CATS)
        self.old_expected=second.EXPECTED_FIRST_VERDICTS
        second.EXPECTED_FIRST_VERDICTS=dict(self.expected)
        self.addCleanup(self.restore_expected)
        table=defaultdict(Counter)
        for meta,d in zip(index,decisions):
            for c in second.CATS:
                table[(c,meta['source_arm_private'])][d[c]['verdict']]+=1
        safe_table={c:{arm:dict(table[(c,arm)]) for arm in ('base','v01','v02','v03','gold')}
                    for c in second.CATS}
        write(self.safe,{'schema':first.SCHEMA+'-safe-decision-count-v1',
                         'status':'R55_GOLD5_ARBITRATION_DECISIONS_SYNTAX_AND_EXACT_QUOTES_VALIDATED__DEV_ONLY__NO_R50',
                         'scope':'flagged','adjudication_items_checked':76,
                         'blind_items_sha256':blind,'decisions_sha256':first_hash,
                         'r50_accessed':False,'model_promoted':False,
                         'verdict_counts_by_category_and_arm':safe_table})

    def restore(self):
        second.PINNED_BLIND,second.PINNED_INDEX,second.PINNED_FIRST_DECISIONS=self.original

    def restore_expected(self):
        second.EXPECTED_FIRST_VERDICTS=self.old_expected

    def state(self):
        return second.checked_first(self.pack,self.first,self.safe)

    def make_pack(self):
        st=self.state()
        out=self.root/'second-pack'
        rc=second.prepare(st,out)
        return out,rc

    def scored(self,pack,mode='REJECTED'):
        blank=json.loads((pack/'reviewers/R55_GOLD5_SECOND_AUDIT_DECISIONS_BLANK_PRIVATE.json').read_text())
        items=json.loads((pack/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json').read_text())['items']
        by_token={x['candidate_token']:x for x in items}
        for entry in blank['items']:
            task=by_token[entry['candidate_token']]
            for c in second.CATS:
                entry[c]={'verdict':mode,
                          'candidate_quote':'synthetic reply' if mode=='CONFIRMED' else '',
                          'context_quote':'player chooses' if mode=='CONFIRMED' else '',
                          'rationale':'Second reviewer independent source-grounded synthetic reason.'}
        path=self.root/'second-done.json';write(path,blank)
        return path

    def test_first_input_76_items_152_category_counts(self):
        st=self.state()
        self.assertEqual(len(st['task_by']),76)
        self.assertEqual(sum(self.expected.values()),152)
        self.assertEqual(self.expected['CONFIRMED'],57)
        self.assertEqual(self.expected['REJECTED'],73)
        self.assertEqual(self.expected['HOLD_INSUFFICIENT_EVIDENCE'],22)

    def test_sampling_is_stratified_and_deterministic(self):
        st=self.state()
        sample1=second.rejected_samples(st)
        sample2=second.rejected_samples(st)
        self.assertEqual(sample1,sample2)
        strata=Counter((st['meta_by'][tok]['source_arm_private'],cat)
                       for tok,e in st['dec_by'].items() for cat in second.CATS if e[cat]['verdict']=='REJECTED')
        selected=Counter((st['meta_by'][tok]['source_arm_private'],cat) for tok,cat in sample1)
        self.assertEqual(selected,{k:(v+4)//5 for k,v in strata.items()})
        self.assertGreater(len(sample1),0)

    def test_selection_contains_every_positive_and_hold(self):
        st=self.state();out,receipt=self.make_pack()
        meta=json.loads((out/'coordinator/R55_GOLD5_SECOND_AUDIT_INDEX_PRIVATE.json').read_text())['records']
        chosen={x['original_candidate_token_private'] for x in meta}
        for tok,row in st['dec_by'].items():
            if any(row[c]['verdict']!='REJECTED' for c in second.CATS):
                self.assertIn(tok,chosen)
        self.assertEqual(receipt['selected_category_judgments_required'],2*len(chosen))
        self.assertTrue(receipt['all_first_confirmed_and_hold_categories_included'])

    def test_second_packet_is_blind_and_fresh_tokens(self):
        out,rc=self.make_pack()
        src=(out/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json').read_text()
        orig=(self.pack/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json').read_text()
        self.assertNotEqual(src,orig)
        for key in ('source_arm_private','first_verdict_private','original_candidate_token_private',
                    'flag_observations_UNADJUDICATED','reviewer_preference_votes'):
            self.assertNotIn(key,src)
        self.assertIn('private_coordinator_index_sha256',rc)
        self.assertEqual((out/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json').stat().st_mode & 0o777,0o600)

    def test_packet_output_is_non_overwriting(self):
        st=self.state();self.make_pack()
        with self.assertRaisesRegex(fr.Hold,'SECOND_OUTPUT_ALREADY_EXISTS'):
            second.prepare(st,self.root/'second-pack')

    def test_packet_refuses_git(self):
        st=self.state();dir=self.root/'repository';dir.mkdir();(dir/'.git').mkdir()
        with self.assertRaisesRegex(fr.Hold,'PRIVATE_OUTPUT_INSIDE_GIT'):
            second.prepare(st,dir/'private-output')

    def test_first_blind_modified_holds(self):
        p=self.pack/'reviewers/R55_GOLD5_ARBITER_BLIND_ITEMS_PRIVATE.json'
        p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(fr.Hold,'PINNED_BLIND_PACKET_SHA_MISMATCH'):
            self.state()

    def test_first_decisions_modified_holds(self):
        self.first.write_bytes(self.first.read_bytes()+b'\n')
        with self.assertRaisesRegex(fr.Hold,'PINNED_FIRST_DECISIONS_SHA_MISMATCH'):
            self.state()

    def test_index_modified_holds(self):
        p=self.pack/'coordinator/R55_GOLD5_ARBITRATION_SOURCE_INDEX_PRIVATE.json'
        p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(fr.Hold,'PINNED_INDEX_SHA_MISMATCH'):
            self.state()

    def test_safe_count_table_tamper_holds(self):
        safe=json.loads(self.safe.read_text())
        safe['verdict_counts_by_category_and_arm']['agency']['v02']={'CONFIRMED':500}
        write(self.safe,safe)
        with self.assertRaisesRegex(fr.Hold,'FIRST_COUNT_TABLE_DOES_NOT_MATCH_DECISIONS'):
            self.state()

    def test_validate_second_all_rejected(self):
        out,rc=self.make_pack()
        done=self.scored(out)
        result=second.validate_second(out,done,self.root/'validated')
        self.assertEqual(result['second_category_decisions_validated'],rc['selected_category_judgments_required'])
        self.assertEqual(result['status'],
            'R55_GOLD5_SECOND_AUDIT_VERDICTS_VALIDATED__NO_AUTO_PROMOTION__NO_R50')
        self.assertFalse(result['r50_accessed'])
        self.assertEqual(result['second_category_verdicts']['REJECTED'],rc['selected_category_judgments_required'])
        self.assertEqual((self.root/'validated/R55_GOLD5_SECOND_AUDIT_COMPARISON_PRIVATE.json').stat().st_mode & 0o777,0o600)

    def test_validate_second_confirmed_with_exact_quotes(self):
        out,rc=self.make_pack();done=self.scored(out,'CONFIRMED')
        r=second.validate_second(out,done,self.root/'validated')
        self.assertEqual(r['second_category_verdicts']['CONFIRMED'],rc['selected_category_judgments_required'])
        self.assertGreater(r['both_arbiters_CONFIRMED_category_count'],0)

    def test_validate_missing_verdict_holds(self):
        out,_=self.make_pack()
        file=out/'reviewers/R55_GOLD5_SECOND_AUDIT_DECISIONS_BLANK_PRIVATE.json'
        with self.assertRaisesRegex(fr.Hold,'SECOND_UNFILLED_VERDICT'):
            second.validate_second(out,file,self.root/'validated')

    def test_validate_ungrounded_quote_holds(self):
        out,_=self.make_pack();done=self.scored(out,'CONFIRMED')
        data=json.loads(done.read_text())
        data['items'][0]['agency']['candidate_quote']='fake quote outside the actual text'
        write(done,data)
        with self.assertRaisesRegex(fr.Hold,'SECOND_UNGROUNDED_CANDIDATE_QUOTE'):
            second.validate_second(out,done,self.root/'validated')

    def test_validate_duplicate_candidate_token_holds(self):
        out,_=self.make_pack();done=self.scored(out)
        data=json.loads(done.read_text())
        data['items'][1]['candidate_token']=data['items'][0]['candidate_token']
        write(done,data)
        with self.assertRaisesRegex(fr.Hold,'ANSWERS_DUPLICATES'):
            second.validate_second(out,done,self.root/'validated')

    def test_validate_source_changed_holds(self):
        out,_=self.make_pack();done=self.scored(out)
        source=out/'reviewers/R55_GOLD5_SECOND_AUDIT_BLIND_ITEMS_PRIVATE.json'
        source.write_bytes(source.read_bytes()+b'\n')
        with self.assertRaisesRegex(fr.Hold,'SECOND_SOURCE_HASH_MISMATCH'):
            second.validate_second(out,done,self.root/'validated')

    def test_validate_second_does_not_overwrite(self):
        out,_=self.make_pack();done=self.scored(out)
        second.validate_second(out,done,self.root/'validated')
        with self.assertRaisesRegex(fr.Hold,'SECOND_VALIDATION_OUTPUT_EXISTS'):
            second.validate_second(out,done,self.root/'validated')

    def test_pinned_first_counts_guard(self):
        second.EXPECTED_FIRST_VERDICTS={'CONFIRMED':58,'REJECTED':73,'HOLD_INSUFFICIENT_EVIDENCE':21}
        with self.assertRaisesRegex(fr.Hold,'FIRST_DECISION_COUNTS_NOT_PINNED'):
            self.state()

    def test_pinned_first_report_claim_only_not_sufficient(self):
        safe=json.loads(self.safe.read_text());safe['decisions_sha256']='0'*64
        write(self.safe,safe)
        with self.assertRaisesRegex(fr.Hold,'FIRST_SAFE_RECEIPT_MISMATCH'):
            self.state()


if __name__=='__main__':
    unittest.main()
