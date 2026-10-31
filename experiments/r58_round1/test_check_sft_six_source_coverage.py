#!/usr/bin/env python3
"""Synthetic-only tests; never open real source blobs or protected files."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from check_sft_six_source_coverage import (
    Hold, HISTORY_KEYS, SOURCE_PINS, SOURCES, private_json,
    parse_historical, pinned_split_counts, reconcile, main,
)


def uid(n):
    return f'{n:08x}-aaaa-4aaa-8aaa-aaaaaaaaaaaa'


def test_data():
    keys=list(SOURCE_PINS)+list(HISTORY_KEYS.values())
    counts={key:{} for key in keys}
    lines={key:[] for key in SOURCE_PINS}
    historical={'schema':'storyforge-r56-source-world-exposure-v1','r50_read':False,'splits':{}}
    groups={
        'V01_TRAIN':([*range(1,16)],65),
        'V01_VALIDATION':([*range(16,18)],15),
        'R46_TRAIN':([*range(18,23)],49),
        'R46_VALIDATION':([*range(22,25)],15),
        'R54_TRAIN':([*range(24,27)],31),
        'R54_VALIDATION':([*range(26,28)],9),
    }
    for key,(worlds,n) in groups.items():
        for i in range(n):
            world=uid(worlds[i%len(worlds)])
            counts[key][world]=counts[key].get(world,0)+1
            if key in SOURCE_PINS:
                lines[key].append(json.dumps({'id':f'sample-{i:06d}',
                   'metadata':{'story_id':world},'messages':[{'role':'user','content':'fiction'}]}))
        for old,new in HISTORY_KEYS.items():
            if new==key:
                historical['splits'][old]={u:[hashlib.sha256(f'{key}:{u}:{j}'.encode()).hexdigest()
                                              for j in range(k)] for u,k in counts[key].items()}
    gold=set([uid(n) for n in range(1,12)]+[uid(28),uid(29)])
    worlds=[]
    for i in range(1,30):
        u=uid(i)
        row={k:counts[k].get(u,0) for k in keys}
        row['GOLD87']=1 if u in list(sorted(gold))[:5] else 0
        row['GOLD108']=1 if u in gold and row['GOLD87']==0 else 0
        worlds.append({'source_story_uuid_PRIVATE':u,'source_row_counts':row,
          'same_exact_uuid_seen_in_previous_sft':i<=27})
    roster={'schema':'storyforge-r57-g2-owner-private-world-alias-review-roster-v1',
            'worlds':worlds}
    blobs={key:('\n'.join(lines[key])+'\n').encode() for key in SOURCE_PINS}
    return roster,historical,blobs


class SixSourceTests(unittest.TestCase):
    def setUp(self):
        self.roster,self.hist,self.blobs=test_data()

    def test_01_positive_frozen_counts(self):
        safe=reconcile(self.roster,self.hist,self.blobs)
        self.assertTrue(safe['known_six_source_per_world_counts_equal'])
        self.assertEqual(safe['known_six_source_total_rows'],184)
        self.assertEqual(safe['known_six_source_unique_world_uuids'],27)
        self.assertEqual(safe['g1_clearance'],'HOLD')
        self.assertFalse(safe['remote_trainer_primary_inputs_verified'])
        self.assertFalse(safe['source_registry_complete'])
        self.assertNotIn(uid(1),json.dumps(safe))

    def test_02_pinned_train_row_count_fail_closed(self):
        with self.assertRaises(Hold):pinned_split_counts(self.blobs['V01_TRAIN'],64)

    def test_03_ambiguous_story_metadata_fail_closed(self):
        corrupt=self.blobs['V01_TRAIN'].replace(b'"story_id"',b'"story_id"',1)
        corrupt=corrupt.replace(b'"metadata": {',b'"metadata": {"story_id": "'+uid(1).encode()+b'", ',1)
        with self.assertRaises(Hold):pinned_split_counts(corrupt,65)

    def test_04_wrong_v01_world_row_count(self):
        self.roster['worlds'][0]['source_row_counts']['V01_TRAIN']+=1
        with self.assertRaises(Hold):reconcile(self.roster,self.hist,self.blobs)

    def test_05_missing_r56_split(self):
        del self.hist['splits']['r46_val']
        with self.assertRaises(Hold):parse_historical(self.hist)

    def test_06_r56_split_count_change(self):
        one=next(iter(self.hist['splits']['r54_train'].values()))
        one.pop()
        with self.assertRaises(Hold):parse_historical(self.hist)

    def test_07_r56_target_digest_invalid(self):
        one=next(iter(self.hist['splits']['r46_train'].values()))
        one[0]='incorrect'
        with self.assertRaises(Hold):parse_historical(self.hist)

    def test_08_roster_false_sft_flag(self):
        self.roster['worlds'][0]['same_exact_uuid_seen_in_previous_sft']=False
        with self.assertRaises(Hold):reconcile(self.roster,self.hist,self.blobs)

    def test_09_roster_duplicate_uuid(self):
        self.roster['worlds'][1]['source_story_uuid_PRIVATE']=uid(1)
        with self.assertRaises(Hold):reconcile(self.roster,self.hist,self.blobs)

    def test_10_r56_uuid_rename(self):
        r=self.hist['splits']['r46_val']
        k=next(iter(r))
        r[uid(90)]=r.pop(k)
        with self.assertRaises(Hold):reconcile(self.roster,self.hist,self.blobs)

    def test_11_private_0600_input_and_bad_0644_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'private.json'
            p.write_text(json.dumps(self.hist));p.chmod(0o600)
            self.assertEqual(private_json(p,400000)['schema'],self.hist['schema'])
            p.chmod(0o644)
            with self.assertRaises(Hold):private_json(p,400000)

    def test_12_r50_flag_true_fails(self):
        self.hist['r50_read']=True
        with self.assertRaises(Hold):parse_historical(self.hist)

    def test_13_g1_sft_flags_never_admit(self):
        r=reconcile(self.roster,self.hist,self.blobs)
        self.assertEqual((r['train_admitted'],r['validation_admitted'],r['teacher_admitted']), (0,0,0))
        self.assertFalse(r['expansion_allowed'])

    def test_14_duplicate_history_target_within_split(self):
        one=next(iter(self.hist['splits']['r54_train'].values()))
        one[1]=one[0]
        with self.assertRaises(Hold):parse_historical(self.hist)

    def test_15_negative_duplicate_sample_id(self):
        raw=self.blobs['V01_TRAIN'].splitlines()
        obj=json.loads(raw[1]);obj['id']='sample-000000';raw[1]=json.dumps(obj).encode()
        with self.assertRaises(Hold):pinned_split_counts(b'\n'.join(raw)+b'\n',65)

    def test_16_cli_no_output_on_invalid_file(self):
        with tempfile.TemporaryDirectory() as td:
            fake=Path(td)/'R57_G2_WORLD_ALIAS_REVIEW_20261031_112233_PRIVATE.json'
            fake.write_text('{}');fake.chmod(0o600)
            r=main(['--repo-root',td,'--r57-private-root',td,
                 '--r56-historical-exposure',str(Path(td)/'missing'/'R56_HISTORICAL_EXPOSURE_WORLD_IDS_PRIVATE.json')])
            self.assertEqual(r,42)

if __name__=='__main__':unittest.main()
