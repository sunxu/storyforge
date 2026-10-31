#!/usr/bin/env python3
"""Synthetic-only R04/Gold108 and G1 PRIVATE ledger tests (no story content)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_r04_non_gold_uuid import (
    Hold, OWNER_POLICY, evaluate, frozen_five_from_dev20,
    r04_non_gold_worlds, structural_world_rows, source_shape_diagnostic, write_private,
)


def uid(n):
    return f'{n:08x}-1111-4111-8111-{n:012x}'


def snapshots():
    # 150 R04 over ten worlds; exactly 108 Gold108 over the first eight.
    # Synthetic row structure intentionally has no actual roleplay content.
    lines = []
    for i in range(150):
        rank = i % 10
        lines.append(json.dumps({'id':f'example-{i:03d}',
            'metadata':{'story_id':uid(rank)},
            'messages':[{'role':'user','content':'synthetic-only'}]},
            sort_keys=True,separators=(',',':')).encode())
    r04 = b'\n'.join(lines) + b'\n'
    gold_rows = [line for line in lines if json.loads(line)['metadata']['story_id'] in
                 {uid(n) for n in range(8)}]
    # 15 each across 8 -> 120, retain only 108, but all eight remain present.
    gold = b'\n'.join(gold_rows[:108]) + b'\n'
    return r04, gold


def hashes(r04,gold):
    return hashlib.sha256(r04).hexdigest(),hashlib.sha256(gold).hexdigest()


def private_dev():
    ids=[uid(n) for n in [20,21,22,23,24]]
    return {'schema':'r58_round1_g1_legacy_dev20_uuid_private_v1',
            'owner_uuid_world_policy':OWNER_POLICY, 'expansion_allowed':False,
            'entries':[{'story_id_PRIVATE':u,
                'historical_sft_uuid_exposed':i==0,
                'r50_protected_uuid_match':False,
                'r57_gold195_source_uuid_match':False,
                'legacy_dev20_uuid_match':False,
                'train_admitted':False,'expansion_allowed':False}
                for i,u in enumerate(ids)]}


class TestR04NonGold(unittest.TestCase):
    def test_01_two_world_difference(self):
        r,g=snapshots()
        self.assertEqual(r04_non_gold_worlds(r,g,*hashes(r,g)),{uid(8),uid(9)})
    def test_02_full_pin_mismatch_holds(self):
        r,g=snapshots()
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g)
    def test_03_r04_row_count_holds(self):
        r,g=snapshots();r=r.split(b'\n',1)[1]
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g,*hashes(r,g))
    def test_04_gold_row_count_holds(self):
        r,g=snapshots();g=g.split(b'\n',1)[1]
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g,*hashes(r,g))
    def test_05_gold_not_exact_row_subset_holds(self):
        r,g=snapshots();g=g.replace(b'synthetic-only',b'synthetic-change',1)
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g,*hashes(r,g))
    def test_06_bad_metadata_token_holds(self):
        r,g=snapshots();r=r.replace(b'"story_id"',b'"world"',1)
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g,*hashes(r,g))
    def test_07_bad_r04_world_count_holds(self):
        r,g=snapshots();r=r.replace(uid(9).encode(),uid(8).encode())
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g,*hashes(r,g))
    def test_08_gold_world_count_holds(self):
        r,g=snapshots();g=g.replace(uid(7).encode(),uid(6).encode())
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g,*hashes(r,g))
    def test_09_repeated_frozen_row_holds(self):
        r,g=snapshots();lines=r.splitlines();lines[1]=lines[0];r=b'\n'.join(lines)+b'\n'
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g,*hashes(r,g))
    def test_10_private_dev_hold_shape(self):
        rows=frozen_five_from_dev20(private_dev())
        self.assertEqual(len(rows),5)
        self.assertEqual(sum(x['historical_sft_uuid_exposed'] for x in rows),1)
    def test_11_private_dev_expansion_refused(self):
        obj=private_dev();obj['entries'][2]['train_admitted']=True
        with self.assertRaises(Hold):frozen_five_from_dev20(obj)
    def test_12_private_dev_collision_refused(self):
        obj=private_dev();obj['entries'][2]['legacy_dev20_uuid_match']=True
        with self.assertRaises(Hold):frozen_five_from_dev20(obj)
    def test_13_evaluate_zero_match_still_hold(self):
        safe,rows=evaluate(frozen_five_from_dev20(private_dev()),{uid(8),uid(9)})
        self.assertEqual(safe['remaining_without_known_sft_r50_gold_dev20_and_r04_non_gold_uuid_match'],4)
        self.assertFalse(safe['other_protected_uuids_covered'])
        self.assertFalse(safe['r56_rank_07_11_to_uuid_provenance_replayed'])
        self.assertEqual(safe['train_admitted'],0)
        self.assertNotIn(uid(20),json.dumps(safe))
        self.assertEqual(len(rows),5)
    def test_14_evaluate_two_matches_hold(self):
        safe,_=evaluate(frozen_five_from_dev20(private_dev()),{uid(21),uid(22)})
        self.assertEqual(safe['r04_non_gold_exact_uuid_matches_among_remaining_four'],2)
        self.assertEqual(safe['remaining_without_known_sft_r50_gold_dev20_and_r04_non_gold_uuid_match'],2)
    def test_15_output_0600_no_overwrite(self):
        _,rows=evaluate(frozen_five_from_dev20(private_dev()),{uid(8),uid(9)})
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/'private';folder.mkdir(mode=0o700)
            dst=folder/'ledger.json'
            write_private(dst,rows)
            self.assertEqual(dst.stat().st_mode & 0o777,0o600)
            with self.assertRaises(Hold):write_private(dst,rows)
            self.assertEqual(json.loads(dst.read_text())['train_admitted'],0)
    def test_16_reject_symlinked_parent(self):
        _,rows=evaluate(frozen_five_from_dev20(private_dev()),{uid(8),uid(9)})
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/'private';folder.mkdir(mode=0o700)
            alias=Path(td)/'alias';alias.symlink_to(folder, target_is_directory=True)
            with self.assertRaises(Hold):write_private(alias/'ledger.json',rows)
            self.assertFalse((folder/'ledger.json').exists())
    def test_17_reject_symlinked_ancestor(self):
        _,rows=evaluate(frozen_five_from_dev20(private_dev()),{uid(8),uid(9)})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);actual=root/'actual';actual.mkdir(mode=0o700)
            nested=actual/'nested';nested.mkdir(mode=0o700)
            alias=root/'alias';alias.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(Hold):write_private(alias/'nested'/'ledger.json',rows)
            self.assertFalse((nested/'ledger.json').exists())
    def test_19_legacy_source_story_id_schema_accepted(self):
        r,g=snapshots()
        r=r.replace(b'"story_id"',b'"source_story_id"')
        g=g.replace(b'"story_id"',b'"source_story_id"')
        self.assertEqual(r04_non_gold_worlds(r,g,*hashes(r,g)),{uid(8),uid(9)})

    def test_20_mixed_legacy_and_modern_schema_accepted(self):
        r,g=snapshots()
        # Both frozen sources may contain either historical key, line by line.
        r=r.replace(b'"story_id"',b'"source_story_id"')
        g=g.replace(b'"story_id"',b'"source_story_id"')
        # Change one row in the common exact-byte subset back to story_id.
        common=r.splitlines()[0]
        fixed=common.replace(b'"source_story_id"',b'"story_id"')
        r=r.replace(common,fixed,1)
        g=g.replace(common,fixed,1)
        self.assertEqual(r04_non_gold_worlds(r,g,*hashes(r,g)),{uid(8),uid(9)})

    def test_21_two_simultaneous_world_tokens_must_hold(self):
        r,g=snapshots()
        r=r.replace(b'"story_id":',b'"source_story_id":"'+uid(8).encode()+b'","story_id":',1)
        with self.assertRaises(Hold): r04_non_gold_worlds(r,g,*hashes(r,g))

    def test_22_unpinned_world_token_value_must_hold(self):
        r,g=snapshots()
        r=r.replace(b'"story_id"',b'"source_story_id"',1)
        with self.assertRaises(Hold):r04_non_gold_worlds(r,g)

    def test_23_safe_shape_diagnostic_accepts_source_story_id(self):
        r,g=snapshots()
        r=r.replace(b'"story_id"',b'"source_story_id"')
        result=source_shape_diagnostic(r,hashlib.sha256(r).hexdigest(),150,10)
        self.assertTrue(result['sha256_pin_verified'])
        self.assertEqual(result['source_story_id_only_rows'],150)
        self.assertTrue(result['distinct_worlds_expected_verified'])
        self.assertNotIn(uid(0),json.dumps(result))

    def test_24_safe_diagnostic_on_pin_mismatch_cannot_claim_worlds(self):
        r,g=snapshots()
        result=source_shape_diagnostic(r,'a'*64,150,10)
        self.assertFalse(result['sha256_pin_verified'])
        self.assertFalse(result['distinct_worlds_expected_verified'])
        self.assertEqual(result['valid_single_uuid_rows'],0)

    def test_18_unique_uuids_in_private(self):
        obj=private_dev();obj['entries'][2]['story_id_PRIVATE']=obj['entries'][1]['story_id_PRIVATE']
        with self.assertRaises(Hold):frozen_five_from_dev20(obj)

if __name__=='__main__':unittest.main()
