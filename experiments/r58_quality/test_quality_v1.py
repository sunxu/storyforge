#!/usr/bin/env python3
"""Synthetic-only checks for Quality-v1. No private files, network or HF."""
from __future__ import annotations

import copy
import json
import unittest

from quality_v1 import (
    CORPORA, EVIDENCE, FLOORS, MAX_R58_ROWS, OUT_SCHEMA, SCHEMA, SCORES,
    SEVERE, Hold, canonical, decide, sha, summarize,
)


def make_case(case_id="synthetic_01", world="world_1", split="train",
              corpus="gold195"):
    messages = [
        {"role": "system", "content": "虚构故事世界，仅用于单测。"},
        {"role": "user", "content": "你在门外看到了什么？"},
        {"role": "assistant", "content": "门口有一盏旧灯，NPC 等着回应。"},
        {"role": "user", "content": f"请由 NPC 继续行动，保留我的决定。{case_id}"},
    ]
    target = f"NPC 推开自己的手提箱，轻声提出下一步的建议。{case_id}"
    reviews = []
    for reviewer in ("synthetic_model_A", "synthetic_model_B"):
        reviews.append({
            "reviewer_key": reviewer, "decision": "PASS",
            "private_evidence_ref": f"{reviewer}_evidence",
            "severe_flags": {k: False for k in SEVERE},
            "scores": {k: max(4, FLOORS[k]) for k in SCORES},
        })
    evidence = {k: True for k in EVIDENCE}
    evidence.update({
        "known_protected_overlap": False,
        "final_heldout_overlap": False,
        "protected_test_body_accessed": False,
    })
    return {
        "schema": SCHEMA, "case_id": case_id, "corpus": corpus,
        "source_kind": "original_gold", "source_version_sha256": "a" * 64,
        "world_graph_sha256": "b" * 64, "world_component_id": world,
        "split": split, "messages": messages, "target_text": target,
        "input_messages_sha256": sha(canonical(messages)),
        "assistant_target_sha256": sha(target.encode("utf-8")),
        "evidence": evidence, "reviews": reviews,
    }


class QualityV1SyntheticTest(unittest.TestCase):
    def test_all_good_is_candidate_only_not_training_admission(self):
        a, b = make_case(), make_case("synthetic_02", "world_2", "validation")
        r = summarize([a, b])
        self.assertEqual(r["schema"], OUT_SCHEMA)
        self.assertEqual(r["decision_counts"]["PASS"], 2)
        self.assertEqual(r["quality_dataset_admitted"], 0)
        self.assertFalse(r["training_authorized"])
        self.assertFalse(r["original_provider_request_replay_required"])
        self.assertFalse(r["literary_quality_independently_judged_by_this_script"])

    def test_production_replay_fields_are_not_required(self):
        a = make_case()
        self.assertNotIn("history_replay_verified", a["evidence"])
        self.assertNotIn("target_time_canon_verified", a["evidence"])
        self.assertEqual(decide(a)[0], "PASS")

    def test_same_world_train_validation_collision_holds_both(self):
        a = make_case()
        b = make_case("synthetic_02", "world_1", "validation")
        r = summarize([a, b])
        self.assertTrue(r["world_train_validation_collision_found"])
        self.assertEqual(r["decision_counts"]["HOLD"], 2)
        self.assertEqual(r["hold_reject_reasons"]["TRAIN_VALIDATION_WORLD_COLLISION"], 2)

    def test_same_world_train_train_is_allowed(self):
        a = make_case()
        b = make_case("synthetic_02", "world_1", "train")
        self.assertEqual(summarize([a, b])["decision_counts"]["PASS"], 2)

    def test_duplicate_input_target_and_id_holds(self):
        a = make_case()
        b = copy.deepcopy(a)
        b["world_component_id"] = "other_world"
        result = summarize([a, b])
        self.assertEqual(result["decision_counts"]["HOLD"], 2)
        self.assertEqual(result["hold_reject_reasons"]["DUPLICATE_SOURCE_OR_TARGET"], 2)

    def test_target_hash_tamper_holds(self):
        a = make_case()
        a["target_text"] += "偷偷改变"
        self.assertEqual(decide(a), ("HOLD", "INPUT_TARGET_STRUCTURE_OR_HASH_MISMATCH"))

    def test_history_role_wrong_order_holds(self):
        a = make_case()
        a["messages"][2]["role"] = "user"
        a["input_messages_sha256"] = sha(canonical(a["messages"]))
        self.assertEqual(decide(a)[0], "HOLD")

    def test_severe_agency_or_hard_rule_rejects(self):
        for k in ("serious_player_agency", "hard_fact_or_ban"):
            a = make_case()
            a["reviews"][0]["severe_flags"][k] = True
            with self.subTest(flag=k):
                self.assertEqual(decide(a), ("REJECT", "REVIEW_SEVERE_OR_REJECT"))

    def test_disagreeing_reviewers_hold(self):
        a = make_case()
        a["reviews"][1]["decision"] = "HOLD"
        self.assertEqual(decide(a)[0], "HOLD")

    def test_duplicate_reviewer_id_holds(self):
        a = make_case()
        a["reviews"][1]["reviewer_key"] = a["reviews"][0]["reviewer_key"]
        self.assertEqual(decide(a)[0], "HOLD")

    def test_quality_floor_holds(self):
        a = make_case()
        a["reviews"][0]["scores"]["chinese_prose"] = 3
        self.assertEqual(decide(a), ("HOLD", "QUALITY_BELOW_V1_FLOOR"))

    def test_bool_is_not_integer_score(self):
        a = make_case()
        a["reviews"][0]["scores"]["player_agency"] = True
        self.assertEqual(decide(a)[0], "HOLD")

    def test_protected_overlap_and_unknown_coverage_hold(self):
        a = make_case()
        a["evidence"]["known_protected_overlap"] = True
        self.assertEqual(decide(a)[0], "HOLD")
        a["evidence"]["known_protected_overlap"] = False
        a["evidence"]["known_protected_metadata_checked"] = False
        self.assertEqual(decide(a)[0], "HOLD")

    def test_no_r50_body_allowed(self):
        a = make_case()
        a["evidence"]["protected_test_body_accessed"] = True
        self.assertEqual(decide(a)[0], "HOLD")

    def test_teacher_or_unrecognized_corpus_not_admitted(self):
        a = make_case()
        a["source_kind"] = "teacher_generated"
        self.assertEqual(decide(a)[0], "HOLD")
        a["source_kind"] = "original_gold"
        a["corpus"] = "protected_r50"
        self.assertNotIn(a["corpus"], CORPORA)
        self.assertEqual(decide(a)[0], "HOLD")

    def test_r58_pilot_20_cap_fail_closed(self):
        rows = [make_case(f"synthetic_{i}", f"world_{i}", corpus="r58_round1")
                for i in range(MAX_R58_ROWS + 1)]
        with self.assertRaises(Hold):
            summarize(rows)

    def test_private_strings_never_exported(self):
        private_marker = "SYNTHETIC_PRIVATE_CANARY_123"
        a = make_case(case_id=private_marker)
        r = summarize([a])
        encoded = json.dumps(r, ensure_ascii=False)
        self.assertNotIn(private_marker, encoded)
        self.assertNotIn(a["target_text"], encoded)
        self.assertNotIn(a["source_version_sha256"], encoded)
        self.assertFalse(r["private_ids_text_or_hashes_exported"])

    def test_missing_evidence_prevents_pass(self):
        a = make_case()
        del a["evidence"]["owner_quality_approved"]
        self.assertEqual(decide(a)[0], "HOLD")

    def test_empty_or_oversized_batch_holds(self):
        with self.assertRaises(Hold):
            summarize([])
        with self.assertRaises(Hold):
            summarize([make_case(f"synthetic_{i}", f"world_{i}")
                       for i in range(196)])


if __name__ == "__main__":
    unittest.main()
