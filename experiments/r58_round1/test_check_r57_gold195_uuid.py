"""Synthetic-only R58 R57 Gold195 source UUID guarded comparison tests."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_r57_gold195_uuid import (
    Hold, r57_gold_ids, evaluate, read_r50_private, run,
    EXPECTED_SOURCES,
)
from check_prior_sft_exact_world_ids import OWNER_IDENTITY_POLICY

def uid(n):
    return f"00000000-0000-0000-0000-{n:012d}"

def roster():
    rows=[]
    for n in range(1,30):
        count={k:0 for k in EXPECTED_SOURCES}
        if n<=11 or n in (28,29):
            count["GOLD87"]=1
        if n<=27:
            count["V01_TRAIN"]=1
        rows.append({
            "source_story_uuid_PRIVATE":uid(n),
            "source_row_counts":count,
            "gold_final_targets_without_previous_exact_match":0,
            "same_exact_uuid_seen_in_previous_sft":n<=27,
            "owner_declared_component_token_PRIVATE":None,
            "owner_alias_evidence_references_PRIVATE":[],
            "owner_alias_semantic_review_status":"PENDING_NOT_VERIFIED",
            "owner_signoff_status":"NOT_SIGNED",
            "dataset_v04_decision":"HOLD_NOT_REVIEWED",
        })
    return {
        "schema":"storyforge-r57-g2-owner-private-world-alias-review-roster-v1",
        "purpose":"OWNER_MANUAL_SEMANTIC_ALIAS_AND_WORLD_COMPONENT_EVIDENCE_REVIEW_ONLY",
        "sources_frozen_byte_identity_checked_by_cli":False,
        "independent_semantic_world_link_certified":False,
        "training_authorized":False,
        "v04_admitted_rows":0,"worlds":rows,
    }

def sft():
    rows=[]
    for n in (1,28,30,31,32):
        old=n==1
        rows.append({
            "story_id_PRIVATE":uid(n),
            "historical_sft_exact_uuid_overlap":old,
            "status":"EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE"
                     if old else "HOLD_R50_DEV_OTHER_PROTECTED_UUID_CHECK_PENDING",
        })
    return {
        "schema":"r58_round1_g1_prior_sft_exact_id_holds_private_v2",
        "owner_world_identity_policy":OWNER_IDENTITY_POLICY,
        "namespace_equivalence_owner_confirmed":True,
        "expansion_allowed":False,"entries":rows,
    }

def r50():
    return {
        "schema":"r58_round1_g1_r50_protection_private_v1",
        "owner_world_identity_policy":OWNER_IDENTITY_POLICY,
        "status":"NO_GLOBAL_G1_CLEARANCE","expansion_allowed":False,
        "entries":[{
            "story_id_PRIVATE":r["story_id_PRIVATE"],
            "historically_sft_exposed":r["historical_sft_exact_uuid_overlap"],
            "r50_exact_story_uuid_match":False,
        } for r in sft()["entries"]],
    }

class TestGold195UUID(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.private=self.base/"private"
        self.private.mkdir(mode=0o700)
        os.chmod(self.private,0o700)
        self.r57=self.base/"r57"/"private"
        self.r57.mkdir(parents=True,mode=0o700)
    def tearDown(self):
        self.temp.cleanup()
    def file(self,p,obj):
        p.write_text(json.dumps(obj),encoding="utf-8")
        os.chmod(p,0o600)
        return p
    def inputs(self):
        sr=self.file(self.private/"sft.json",sft())
        rc=self.file(self.private/"r50.json",r50())
        rost=self.file(self.r57/"R57_G2_WORLD_ALIAS_REVIEW_20261030_213000_PRIVATE.json",roster())
        discovery=self.file(self.private/"discovery.json",{
            "schema":"r58_g1_filename_candidates_private_v1",
            "candidate_paths_by_scope":{
                "semantic_world_graph":[str(rost)],
                "r55_r57_dev_worlds":[],
            },
        })
        return sr,rc,discovery
    def test_gold13_from_29_metadata_roster(self):
        gold=r57_gold_ids(roster())
        self.assertEqual(len(gold),13)
        self.assertIn(uid(28),gold)
        self.assertNotIn(uid(30),gold)
    def test_wrong_roster_gold_count_holds(self):
        a=roster()
        a["worlds"][-1]["source_row_counts"]["GOLD87"]=0
        with self.assertRaises(Hold):r57_gold_ids(a)
    def test_missing_source_count_holds(self):
        a=roster()
        del a["worlds"][0]["source_row_counts"]["R46_TRAIN"]
        with self.assertRaises(Hold):r57_gold_ids(a)
    def test_source_count_is_nonnegative_int(self):
        a=roster()
        a["worlds"][0]["source_row_counts"]["GOLD87"]=-1
        with self.assertRaises(Hold):r57_gold_ids(a)
    def test_r50_sft_ledger_case_level_membership(self):
        p=self.file(self.private/"r50.json",r50())
        rows=read_r50_private(p,sft())
        self.assertEqual(len(rows),5)
    def test_r50_duplicate_or_unexpected_exposure_holds(self):
        bad=r50()
        bad["entries"][1]["r50_exact_story_uuid_match"]=True
        p=self.file(self.private/"r50.json",bad)
        with self.assertRaises(Hold):read_r50_private(p,sft())
    def test_one_r57_gold_only_overlap_is_hold(self):
        safe,private=evaluate(sft(),r50()["entries"],r57_gold_ids(roster()))
        self.assertEqual(safe["r57_gold195_exact_uuid_matches_among_remaining_four"],1)
        self.assertEqual(safe["remaining_without_sft_r50_or_r57_gold_source_uuid_match"],3)
        self.assertFalse(safe["legacy_r47_r48_r55_r57_dev20_uuid_index_covered"])
        self.assertEqual(safe["g1_clearance"],"HOLD")
        self.assertEqual(sum("HOLD_R57_GOLD" in x["status"] for x in private),1)
        self.assertNotIn(uid(28),json.dumps(safe))
    def test_zero_gold_match_is_only_partial(self):
        safe,_=evaluate(sft(),r50()["entries"],{uid(i) for i in range(40,53)})
        self.assertEqual(safe["remaining_without_sft_r50_or_r57_gold_source_uuid_match"],4)
        self.assertFalse(safe["other_protected_uuids_covered"])
        self.assertEqual(safe["train_admitted"],0)
    def test_private_output_safeguarded_and_no_overwrite(self):
        sr,rc,discovery=self.inputs()
        output=self.private/"r57_gold_private.json"
        safe=run(sr,rc,discovery,self.r57,output)
        self.assertTrue(safe["private_case_hold_ledger_written"])
        self.assertEqual(output.stat().st_mode & 0o777,0o600)
        self.assertNotIn(uid(28),json.dumps(safe))
        body=output.read_bytes()
        with self.assertRaises(Hold):run(sr,rc,discovery,self.r57,output)
        self.assertEqual(body,output.read_bytes())

if __name__=="__main__":
    unittest.main()
