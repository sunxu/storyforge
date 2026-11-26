"""Synthetic-only tests for R52 seven-story/21-pair world review kit."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_world_semantic_review_kit as kit


def source_fixture():
    packets, shortlist, world_queue = [], [], []
    ranks = (6, 8, 9, 10, 12, 14, 15)
    possible = (7, 7, 7, 7, 6, 6, 6)
    for group, rank in enumerate(ranks):
        sid = "synthetic-story-%02d" % rank
        n = 16 if group < 3 else 15
        world_queue.append({
            "schema": "storyforge-r52-private-world-component-review-v1",
            "private_do_not_commit": True,
            "source_story_id": sid,
            "story_rank": rank,
            "first_pass_possible": possible[group],
            "exact_v01_story_uuid_overlap": False,
            "owner_component_isolation_signed": False,
            "train_val_split": None,
            "training_admission": kit.HOLD,
        })
        for i in range(n):
            cid = "synthetic-%s-%03d" % (rank, i)
            target = "Synthetic target content %s" % cid
            visible = "Synthetic user message %s" % cid
            row = {
                "schema": kit.PACKET_SCHEMA,
                "private_do_not_commit": True,
                "candidate_id": cid, "source_story_id": sid,
                "story_rank": rank,
                "target_content_for_review_only": target,
                "target_sha256": kit.sha_text(target),
                "target_original_array_index": i * 10 + 5,
                "frozen_visible_history": [{
                    "role": "user",
                    "content": visible,
                    "original_source_array_index": i * 10 + 4,
                    "source_body_sha256": kit.sha_text(visible),
                }],
                "training_admission": kit.HOLD,
                "split": None,
                "historical_card_version_verified": False,
            }
            packets.append(row)
            if i < possible[group]:
                shortlist.append({
                    "candidate_id": cid,
                    "source_story_id": sid,
                    "target_sha256": row["target_sha256"],
                    "eligibility_stage": "QUALITY_POSSIBLE__NEEDS_GATES",
                    "training_admission": kit.HOLD,
                    "split": None,
                })
    receipt = {
        "schema": "storyforge-r52-world-isolation-exact-screen-v1",
        "status": "R52_V01_EXACT_UUID_SCREEN_PASS__WORLD_GRAPH_AND_SEALED_TEST_HOLD",
        "first_pass_candidates": 46,
        "source_story_groups": 7,
        "exact_overlap_with_v01_splits_by_story_count": {
            "train": 0, "validation": 0, "test": 0},
        "linked_component_graph_reviewed": 0,
        "r50_sealed_heldout_opened": False,
        "world_split_assigned": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
    }
    return packets, shortlist, world_queue, receipt


def fake_decisions(pairs):
    results = []
    for pair in pairs:
        left = pair["left_bounded_witnesses"][0][
            "bounded_original_message_witnesses"][0]
        right = pair["right_bounded_witnesses"][0][
            "bounded_original_message_witnesses"][0]
        cites = [{
            "scope": x["scope"],
            "story_rank": x["story_rank"],
            "original_source_array_index": x["original_source_array_index"],
            "source_body_sha256": x["source_body_sha256"],
        } for x in (left, right)]
        results.append({
            "schema": kit.DECISION_SCHEMA,
            "left_rank": pair["left_rank"],
            "right_rank": pair["right_rank"],
            "left_source_targets_digest": pair["left_source_targets_digest"],
            "right_source_targets_digest": pair["right_source_targets_digest"],
            "decision": "NO_LINK_OBSERVED_IN_BOUNDED_EVIDENCE__HOLD",
            "rationale": "Synthetic pair only: this does not certify semantic independence.",
            "source_citations": cites,
            "reviewer_a_b_analysis_seen": False,
            "training_admission": kit.HOLD,
        })
    return results


class TestSemanticWorldKit(unittest.TestCase):
    def test_build_seven_and_twentyone_and_hold(self):
        data = source_fixture()
        self.assertEqual(len(data[0]), 108)
        a, b, safe = kit.build(*data)
        self.assertEqual(len(a), 7)
        self.assertEqual(len(b), 21)
        self.assertEqual(safe["quality_shortlist_bound"], 46)
        self.assertEqual(safe["linked_worlds_certified"], 0)
        self.assertTrue(all(x["training_admission"] == kit.HOLD for x in b))

    def test_validate_pair_citations_then_refuse_tamper(self):
        _, pairs, _ = kit.build(*source_fixture())
        decisions = fake_decisions(pairs)
        report = kit.check_decisions(pairs, decisions)
        self.assertEqual(report["pairs_validated"], 21)
        self.assertEqual(report["evidence_citations_validated"], 42)
        self.assertFalse(report["semantic_world_isolation_verified"])
        decisions[0]["source_citations"][0]["source_body_sha256"] = "f" * 64
        with self.assertRaisesRegex(kit.prior.GateHold, "PAIR_CITATION_SHA_OR_SOURCE_INVALID"):
            kit.check_decisions(pairs, decisions)

    def test_wrong_world_queue_is_rejected(self):
        packets, shortlist, worlds, receipt = source_fixture()
        worlds[0]["first_pass_possible"] += 1
        with self.assertRaisesRegex(kit.prior.GateHold, "WORLD_SHORTLIST_COUNT_MISMATCH"):
            kit.build(packets, shortlist, worlds, receipt)


if __name__ == "__main__":
    unittest.main()
