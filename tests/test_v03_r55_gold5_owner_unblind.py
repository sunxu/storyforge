"""Synthetic-only end-to-end Gold5 v2 post-freeze test, no private story data."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SRC))
import v03_r55_gold5_review_freeze as fr
import v03_r55_gold5_owner_unblind as ub


def encode_csv(path, headers, rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def jdump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')


class FakeV2(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='storyforge-r55-gold5-unblind-test-')
        self.root=Path(self.temp.name)
        self.pack=self.root/'owner-pack-v2'
        (self.pack/'reviewers').mkdir(parents=True)
        (self.pack/'coordinator'/'private').mkdir(parents=True)
        self.frozens={n:self.root/'frozen'/n for n in ub.ROUND_NAMES}
        self.completed={}
        self.originals={}
        self.responses=[]
        self.mapping=[]
        all_labels={'pair':('LEFT','RIGHT'),'four':tuple('ABCD'),'five':tuple('ABCDE')}
        arm_maps={
            'pair':{'LEFT':'v02','RIGHT':'v03'},
            'four':{'A':'base','B':'v01','C':'v02','D':'v03'},
            'five':{'A':'gold','B':'base','C':'v01','D':'v02','E':'v03'},
        }
        for i in range(20):
            source={arm:f'synthetic-{arm}-{i}' for arm in ub.ALL_ARMS}
            self.responses.append(source)
            self.mapping.append({
                'sample_id':f'example-{i:02d}',
                'prompt_sha256':hashlib.sha256(f'prompt-{i}'.encode()).hexdigest(),
                'source_reply_sha256':{arm:ub.h(s.encode()) for arm,s in source.items()},
                'pairwise_mapping':arm_maps['pair'],
                'four_model_mapping':arm_maps['four'],
                'five_way_mapping':arm_maps['five'],
            })
        pristine_hashes={}
        for mode in ub.ROUND_NAMES:
            specs=fr.MODES[mode]
            labels=specs[1]
            score_cols=tuple(f'{dim}·{label}' for dim in fr.DIMS for label in labels)
            cols=(*fr.COMMON,*(f'回复{label}' for label in labels),specs[2],*fr.NOTES,specs[3],specs[4],*score_cols)
            pdir=self.root/'completed'/mode
            pdir.mkdir(parents=True)
            self.completed[mode]=[]
            self.originals[mode]=[]
            for rid in range(1,4):
                pristine=[]; scored=[]
                for i in range(20):
                    context={'样本编号':f'example-{i:02d}','故事背景与系统规则':'fake bg',
                             '历史对话':'fake history','当前用户输入':'fake user'}
                    source={**context,**{f'回复{label}':self.responses[i][arm_maps[mode][label]] for label in labels}}
                    blank={c:source.get(c,'') for c in cols}
                    filled=blank.copy()
                    filled[specs[2]]=labels[(i+rid)%len(labels)]
                    filled['偏好理由与可见原文证据']=f'Synthetic review reason reviewer {rid}'
                    filled[specs[3]]='NONE'
                    filled[specs[4]]='NONE'
                    filled['逐事件严重问题证据']=''
                    for col in score_cols:
                        filled[col]=str(1+(rid+i)%5)
                    pristine.append(blank);scored.append(filled)
                p=self.pack/'reviewers'/ub.pristine_filename(mode,rid)
                d=pdir/f'reviewer-{rid:02d}.csv'
                encode_csv(p,cols,pristine)
                encode_csv(d,cols,scored)
                self.completed[mode].append(d)
                self.originals[mode].append(p)
                pristine_hashes[p.name]=ub.h(p.read_bytes())
        keyp=self.pack/'coordinator'/'private'/ub.KEY_NAME
        jdump(keyp,{'schema':'storyforge-r55-gold5-v2-coordinator-v1',
                   'scope':'EXPOSED_R47_R48_R55_SAME_20_TWO_WORLDS_DEV_ONLY',
                   'source_cases':20,'identity_maps':self.mapping,
                   'model_generation':False,'r50_accessed':False})
        jdump(self.pack/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json',{
            'schema':'storyforge-r55-gold5-v2-safe-prep-v1',
            'status':fr.EXPECTED_STATUS,'case_count':20,'reviewer_count':3,'reviewer_csv_count':9,
            'reviewers_completed':0,'new_heldout':False,'r50_accessed':False,
            'gpu_inference':False,'training':False,'model_promoted':False,
            'three_distinct_blind_tasks':True,'coordinator_private_key_sha256':ub.h(keyp.read_bytes()),
            'reviewer_private_csv_sha256':pristine_hashes,
        })
        prior=None
        for mode in ub.ROUND_NAMES:
            r=fr.freeze_round(self.pack,mode,tuple(self.completed[mode]),self.frozens[mode],
                              self.frozens['pair']/'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json' if mode!='pair' else None,
                              self.frozens['four']/'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json' if mode=='five' else None)
            self.assertEqual(r['ratings_verified'],{'pair':720,'four':1440,'five':1800}[mode])
        self.pins={
            'prep':ub.h((self.pack/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json').read_bytes()),
            'key':ub.h(keyp.read_bytes()),
            **{mode:tuple(ub.h((self.frozens[mode]/ub.review_filename(mode,r)).read_bytes()) for r in range(1,4))
               for mode in ub.ROUND_NAMES},
            'flag_presence':{'pair':0,'four':0,'five':0},
        }

    def tearDown(self):
        self.temp.cleanup()

    def verify(self):
        return ub.verify(self.pack,self.frozens,pins=self.pins)

    def test_complete_verify(self):
        state=self.verify()
        self.assertEqual(len(state['rows']['five']),3)
        self.assertEqual(state['case_ids'][0],'example-00')

    def test_unblind_aggregates(self):
        s=self.verify()
        report=ub.unblind(s,self.root/'owner-private-unblind',pins=self.pins)
        self.assertEqual(report['total_verified_rating_cells'],3960)
        self.assertEqual(sum(report['results']['pair']['reviewer_preference_votes_including_ties'].values()),60)
        self.assertEqual(sum(report['results']['five']['twenty_case_majority_or_split'].values()),20)
        self.assertEqual(report['results']['five']['overall_mean_six_1_to_5']['gold'],3.0)
        self.assertEqual(report['results']['pair']['UNADJUDICATED_cases_with_any_reviewer_flag_by_arm']['agency'],{})
        self.assertEqual(report['status_constraints']['adjudication_complete'],False)
        self.assertTrue((self.root/'owner-private-unblind'/'R55_GOLD5_V2_OWNER_UNBLIND_CASE_PRIVATE.json').exists())

    def test_no_fifth_model_confusion(self):
        s=self.verify(); maps,_=ub.validate_key(s,pins=self.pins)
        result,_=ub.tally(s,maps)
        self.assertNotIn('gold',result['four']['overall_mean_six_1_to_5'])
        self.assertIn('gold',result['five']['overall_mean_six_1_to_5'])
        self.assertNotIn('gold',result['pair']['overall_mean_six_1_to_5'])

    def test_identity_key_not_accessed_by_verify(self):
        self.pack.joinpath('coordinator/private',ub.KEY_NAME).unlink()
        self.verify()  # verify must not touch coordinator/private
        with self.assertRaises(fr.Hold):
            ub.validate_key(self.verify(),pins=self.pins)

    def test_malformed_key_held(self):
        p=self.pack/'coordinator'/'private'/ub.KEY_NAME
        p.write_text('{}',encoding='utf8')
        s=self.verify()
        with self.assertRaisesRegex(fr.Hold,'KEY_PREP_SHA_MISMATCH'):
            ub.validate_key(s,pins=self.pins)

    def test_key_source_alignment_held(self):
        p=self.pack/'coordinator'/'private'/ub.KEY_NAME
        obj=json.loads(p.read_text())
        obj['identity_maps'][3]['source_reply_sha256']['v03']='0'*64
        jdump(p,obj)
        # Synthetic re-pin to test explicit per-message validation beyond file digests.
        self.pins['key']=ub.h(p.read_bytes())
        pr=self.pack/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json'
        prep=json.loads(pr.read_text());prep['coordinator_private_key_sha256']=self.pins['key'];jdump(pr,prep)
        self.pins['prep']=ub.h(pr.read_bytes())
        for mode in ub.ROUND_NAMES:
            rp=self.frozens[mode]/'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
            rec=json.loads(rp.read_text());rec['source_prep_receipt_sha256']=self.pins['prep'];jdump(rp,rec)
        s=self.verify()
        with self.assertRaisesRegex(fr.Hold,'KEY_PAIR_SOURCE_REPLY_SHA_MISMATCH'):
            ub.validate_key(s,pins=self.pins)

    def test_bad_ratings_sha_held(self):
        target=self.frozens['five']/ub.review_filename('five',2)
        target.chmod(0o600)
        with target.open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(fr.Hold,'FREEZE_CSV_SHA_MISMATCH'):
            self.verify()

    def test_bad_owner_pin_held(self):
        self.pins['pair']=('f'*64,*self.pins['pair'][1:])
        with self.assertRaisesRegex(fr.Hold,'OWNER_SCORED_SHA_MISMATCH'):
            self.verify()

    def test_bad_receipt_status_held(self):
        p=self.frozens['pair']/'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
        data=json.loads(p.read_text());data['status']='FAKE';jdump(p,data)
        with self.assertRaisesRegex(fr.Hold,'FREEZE_METADATA_MISMATCH'):
            self.verify()

    def test_bad_receipt_flag_count_held(self):
        p=self.frozens['four']/'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
        data=json.loads(p.read_text());data['reviewer_case_flag_presence_count']=1;jdump(p,data)
        with self.assertRaisesRegex(fr.Hold,'FLAG_PRESENCE_COUNT_MISMATCH'):
            self.verify()

    def test_private_case_id_not_in_safe_report(self):
        s=self.verify(); report=ub.unblind(s,self.root/'own',pins=self.pins)
        safe=(self.root/'own'/'R55_GOLD5_V2_OWNER_UNBLIND_SAFE_AGGREGATE.json').read_text()
        self.assertNotIn('example-00',safe)
        self.assertNotIn('fake bg',safe)
        self.assertNotIn('synthetic-v03-0',safe)
        self.assertIn('example-00',(self.root/'own'/'R55_GOLD5_V2_OWNER_UNBLIND_CASE_PRIVATE.json').read_text())

    def test_no_overwrite(self):
        s=self.verify();ub.unblind(s,self.root/'own',pins=self.pins)
        with self.assertRaisesRegex(fr.Hold,'OUTPUT_DIR_ALREADY_EXISTS'):
            ub.unblind(s,self.root/'own',pins=self.pins)

    def test_expected_case_majority_count(self):
        state=self.verify(); maps,_=ub.validate_key(state,pins=self.pins)
        s,_=ub.tally(state,maps)
        for mode in ub.ROUND_NAMES:
            self.assertEqual(sum(s[mode]['twenty_case_majority_or_split'].values()),20)

    def test_pair_both_flag_parses_to_two(self):
        mp={'LEFT':'v02','RIGHT':'v03'}
        self.assertEqual(ub.decode_flag('BOTH',mp,'pair'),('v02','v03'))

    def test_model_multi_flag_parses_correctly(self):
        mp={'A':'gold','B':'base','C':'v01'}
        self.assertEqual(ub.decode_flag('A,C',mp,'five'),('gold','v01'))

    def test_all_none_flag_empty(self):
        self.assertEqual(ub.decode_flag('NONE',{'A':'gold'},'five'),())

    def test_nonstrings_in_key_rejected(self):
        p=self.pack/'coordinator'/'private'/ub.KEY_NAME
        val=json.loads(p.read_text());val['identity_maps'][0]['pairwise_mapping']['RIGHT']='gold'
        jdump(p,val)
        self.pins['key']=ub.h(p.read_bytes())
        rec=self.pack/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json';pre=json.loads(rec.read_text())
        pre['coordinator_private_key_sha256']=self.pins['key'];jdump(rec,pre)
        self.pins['prep']=ub.h(rec.read_bytes())
        for mode in ub.ROUND_NAMES:
            rp=self.frozens[mode]/'R55_GOLD5_V2_ROUND_FREEZE_SAFE.json'
            blob=json.loads(rp.read_text());blob['source_prep_receipt_sha256']=self.pins['prep'];jdump(rp,blob)
        with self.assertRaisesRegex(fr.Hold,'KEY_PAIR_ARM_MAP_INVALID'):
            ub.validate_key(self.verify(),pins=self.pins)


if __name__=='__main__': unittest.main()
