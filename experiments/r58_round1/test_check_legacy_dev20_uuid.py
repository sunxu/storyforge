#!/usr/bin/env python3
"""Synthetic-only unit tests. Does not open real Test or R50 records."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from check_legacy_dev20_uuid import (
    Hold, source_world_ids, verify_source_receipts, checked_private_rows,
    evaluate, write_private, private_json, OWNER_POLICY, SOURCE_SHA256,
)
U1="11111111-1111-4111-8111-111111111111"
U2="22222222-2222-4222-8222-222222222222"
U3="33333333-3333-4333-8333-333333333333"
U4="44444444-4444-4444-8444-444444444444"
U5="55555555-5555-4555-8555-555555555555"


def source_bytes(count=20, ids=(U1,U2)):
    lines=[]
    for i in range(count):
        lines.append(json.dumps({"id":f"sample-{i:06d}",
            "metadata":{"story_id":ids[i%len(ids)]},
            "messages":[{"content":"synthetic-only"}]}))
    return ("\n".join(lines)+"\n").encode()


def receipts():
    manifest={"schema":"storyforge-blind-v1","count":20,
              "samples":[{"sample_id":f"eval-{i:03d}","source_line":i+1,
                          "prompt_sha256":"a"*64} for i in range(20)]}
    audit={"reproducible_audit":{"checks":{
        "dataset":{"files_sha256":{"test.jsonl":SOURCE_SHA256},
                  "split_counts":{"test":20},"stories_by_split":{"test":2}},
        "heldout":{"test_alignment":"20/20",
                   "same_20_original_test_prompts_in_both_rounds":True}}}}
    budget={"sample_count":100,"split_sample_counts":{"test":20},
            "changed_samples":[{"split":"test","story_id":U1}]}
    return manifest,audit,budget


def ledgers():
    ids=[U1,U2,U3,U4,U5]
    a={"schema":"r58_round1_g1_prior_sft_exact_id_holds_private_v2",
       "owner_world_identity_policy":OWNER_POLICY,
       "namespace_equivalence_owner_confirmed":True,"expansion_allowed":False,
       "entries":[{"story_id_PRIVATE":uid,
                   "historical_sft_exact_uuid_overlap":i==0} for i,uid in enumerate(ids)]}
    b={"schema":"r58_round1_g1_r50_protection_private_v1",
       "owner_world_identity_policy":OWNER_POLICY,"status":"NO_GLOBAL_G1_CLEARANCE",
       "expansion_allowed":False,
       "entries":[{"story_id_PRIVATE":uid,"historically_sft_exposed":i==0,
                   "r50_exact_story_uuid_match":False} for i,uid in enumerate(ids)]}
    c={"schema":"r58_round1_g1_r57_gold195_uuid_private_v1",
       "owner_uuid_world_policy":OWNER_POLICY,
       "status":"PROTECTED_METADATA_ONLY__NOT_ADMITTED","expansion_allowed":False,
       "entries":[{"story_id_PRIVATE":uid,"historical_sft_uuid_exposed":i==0,
                   "r50_protected_uuid_match":False,
                   "r57_gold195_source_uuid_match":False} for i,uid in enumerate(ids)]}
    return a,b,c


class TestLegacyDev20(unittest.TestCase):
    def test_01_valid_source_metadata(self):
        blob=source_bytes()
        self.assertEqual(source_world_ids(blob,hashlib.sha256(blob).hexdigest()),{U1,U2})
    def test_02_source_hash_mismatch_hold(self):
        with self.assertRaises(Hold): source_world_ids(source_bytes())
    def test_03_source_count_not_20_hold(self):
        blob=source_bytes(19)
        with self.assertRaises(Hold): source_world_ids(blob,hashlib.sha256(blob).hexdigest())
    def test_04_source_one_world_hold(self):
        blob=source_bytes(ids=(U1,))
        with self.assertRaises(Hold): source_world_ids(blob,hashlib.sha256(blob).hexdigest())
    def test_05_invalid_uuid_hold(self):
        blob=source_bytes(ids=("not-a-uuid",U2))
        with self.assertRaises(Hold): source_world_ids(blob,hashlib.sha256(blob).hexdigest())
    def test_06_duplicate_sample_hold(self):
        blob=source_bytes().decode().splitlines()
        item=json.loads(blob[1]);item["id"]="sample-000000";blob[1]=json.dumps(item)
        data=("\n".join(blob)+"\n").encode()
        with self.assertRaises(Hold): source_world_ids(data,hashlib.sha256(data).hexdigest())
    def test_07_accepted_receipts(self):
        verify_source_receipts(*receipts(),{U1,U2})
    def test_08_bad_alignment_hold(self):
        a,b,c=receipts();b["reproducible_audit"]["checks"]["heldout"]["test_alignment"]="19/20"
        with self.assertRaises(Hold):verify_source_receipts(a,b,c,{U1,U2})
    def test_09_bad_budget_world_hold(self):
        a,b,c=receipts();c["changed_samples"][0]["story_id"]=U3
        with self.assertRaises(Hold):verify_source_receipts(a,b,c,{U1,U2})
    def test_10_private_ledgers_align(self):
        rows=checked_private_rows(*ledgers())
        self.assertEqual(len(rows),5)
        self.assertEqual(sum(r["historical_sft_uuid_exposed"] for r in rows),1)
    def test_11_private_queue_drift_hold(self):
        a,b,c=ledgers();c["entries"][2]["story_id_PRIVATE"]=U1
        with self.assertRaises(Hold):checked_private_rows(a,b,c)
    def test_12_evaluate_zero_hits_hold(self):
        rows=checked_private_rows(*ledgers())
        safe,private=evaluate(rows,{"66666666-6666-4666-8666-666666666666",
                                    "77777777-7777-4777-8777-777777777777"})
        self.assertEqual(safe["legacy_dev20_exact_uuid_matches_among_remaining_four"],0)
        self.assertEqual(safe["g1_clearance"],"HOLD")
        self.assertEqual(safe["train_admitted"],0)
        self.assertEqual(len(private),5)
    def test_13_evaluate_hit_does_not_admit(self):
        rows=checked_private_rows(*ledgers())
        safe,private=evaluate(rows,{U2,U3})
        self.assertEqual(safe["legacy_dev20_exact_uuid_matches_among_remaining_four"],2)
        self.assertEqual(safe["remaining_without_sft_r50_r57_gold_or_dev20_uuid_match"],2)
        self.assertTrue(all(r["train_admitted"] is False for r in private))
    def test_14_private_output_no_overwrite_and_0600(self):
        rows=checked_private_rows(*ledgers())
        _,private=evaluate(rows,{U2,U3})
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)/"private";home.mkdir(mode=0o700)
            target=home/"secret.json"
            write_private(target,private)
            self.assertEqual(target.stat().st_mode & 0o777,0o600)
            self.assertTrue(json.loads(target.read_text())["expansion_allowed"] is False)
            with self.assertRaises(Hold):write_private(target,private)

if __name__=="__main__":unittest.main()
