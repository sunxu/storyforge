"""Synthetic-only R52 R45 historical exposure impact normalization tests."""
from __future__ import annotations
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_r45_exposure_impact as impact

RANKS=(6,9,10,12,13,14,15)


def make_fixture():
    worlds={}
    cases=[]
    owners=[]
    for n,rank in enumerate(RANKS):
        sid="FAKE-SOURCE-WORLD-"+str(rank)
        content="FAKE unique narrative, source rank "+str(rank)
        digest=impact.prior.sha_bytes(content.encode())
        worlds[rank]={
            "source_story_id":sid,
            "original_root_messages":[{
                "original_source_array_index":0,
                "source_body_sha256":digest,"content":content,
            }],
        }
        k=7 if n<4 else 6
        owners.append({
            "story_rank":rank,"source_story_id":sid,
            "training_admission":impact.HOLD,
            "world_split":None,
            "final_component_isolation":"NOT_VERIFIED",
            "full_story_alias_review_owner_signed":False,
            "quality_first_pass_possible":k,
        })
        for j in range(k):
            cases.append({
                "story_rank":rank, "source_story_id":sid,
                "candidate_id":f"fake-{rank}-{j}",
                "target_sha256":digest if j==0 else "a"*64,
                "training_admission":impact.HOLD,"split":None,
                "eligibility_stage":"QUALITY_POSSIBLE__NEEDS_GATES",
                "final_quality_and_safety_signoff":"PENDING",
            })
    def fake_record(rank, text):
        return {"metadata":{"source_story_id":worlds[rank]["source_story_id"] if rank else "OTHER-SOURCE"},
                "messages":[{"role":"assistant","content":text}]}
    tr=[fake_record(6,worlds[6]["original_root_messages"][0]["content"]),
        fake_record(9,"R45 prior text")]
    tr.extend(fake_record(6,"R45 earlier train story line") for _ in range(27))
    tr.extend(fake_record(0,"other") for _ in range(20))
    val=[fake_record(6,"R45 validation only"),
         fake_record(12,"R45 validation text")]
    val.extend(fake_record(12,"R45 earlier validation story line") for _ in range(11))
    val.extend(fake_record(0,"other") for _ in range(2))
    cohorts={"r45_train":tr,"r45_validation":val}
    text=worlds[6]["original_root_messages"][0]["content"]
    source_sha=worlds[6]["original_root_messages"][0]["source_body_sha256"]
    def witness(kind):
        return {
            "source_rank":6,"source_story_id":worlds[6]["source_story_id"],
            "original_source_array_index":0,"source_body_sha256":source_sha,
            "historical_corpus":"r45_train","historical_record_ordinal":0,
            "historical_message_index":0,
            "historical_message_sha256":impact.prior.sha_bytes(text.encode()),
            "match_kind":kind,"training_admission":impact.HOLD,
        }
    return worlds,cases,owners,cohorts,[
        witness("EXACT_LONG_MESSAGE"),
        witness("SAMPLED_120_CODEPOINT_FRAGMENT")
    ]


class R45ImpactTests(unittest.TestCase):
    def test_world_case_and_witness_deduplication(self):
        worlds,cases,owners,cohorts,witnesses=make_fixture()
        with patch.object(impact,"WITNESS_COUNT",2):
            per_world,per_case,receipt=impact.compute_impact(
                worlds,cases,owners,cohorts,witnesses)
        self.assertEqual(len(per_world),7)
        self.assertEqual(len(per_case),46)
        self.assertEqual(receipt["distinct_r52_worlds_with_r45_train_uuid_overlap"],2)
        self.assertEqual(receipt["distinct_r52_worlds_with_r45_validation_uuid_overlap"],2)
        self.assertEqual(receipt["distinct_r52_worlds_with_both_r45_splits_uuid_overlap"],1)
        self.assertEqual(receipt["distinct_r52_worlds_with_any_r45_uuid_overlap"],3)
        self.assertEqual(receipt["unique_message_pair_witnesses_ignoring_match_kind"],1)
        self.assertEqual(receipt["first_pass_target_sha_exact_matches"]["r45_train"],1)
        self.assertEqual(receipt["train_admitted"],0)
        self.assertFalse(receipt["actual_r46_model_training_exposure_verified"])
        self.assertTrue(all(x["training_admission"]==impact.HOLD for x in per_case))

    def test_tampered_message_anchor_rejected(self):
        worlds,cases,owners,cohorts,witnesses=make_fixture()
        witnesses[0]["source_body_sha256"]="0"*64
        with patch.object(impact,"WITNESS_COUNT",2):
            with self.assertRaisesRegex(
                impact.identity.GateHold, "WITNESS_ID_SHA_OR_SOURCE_CHANGED"):
                impact.compute_impact(worlds,cases,owners,cohorts,witnesses)

    def test_early_component_signoff_rejected(self):
        worlds,cases,owners,cohorts,witnesses=make_fixture()
        owners[0]["full_story_alias_review_owner_signed"]=True
        with patch.object(impact,"WITNESS_COUNT",2):
            with self.assertRaisesRegex(
                impact.identity.GateHold, "R52_WORLD_OWNER_SIGNOFF_PREMATURE"):
                impact.compute_impact(worlds,cases,owners,cohorts,witnesses)


if __name__=="__main__":
    unittest.main()
