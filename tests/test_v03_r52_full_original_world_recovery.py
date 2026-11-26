"""Synthetic-only full original source reconstruction and pair intake checks."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_full_original_world_recovery as full


def digest(text):
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def source_case(rank):
    story_id = "synthetic-story-" + str(rank)
    user, previous, target = (
        "Synthetic user for " + str(rank),
        "Synthetic assistant history for " + str(rank),
        "Synthetic target for " + str(rank),
    )
    messages = [
        {"id": "u" + str(rank), "role": "user", "content": user},
        {"id": "h" + str(rank), "role": "assistant", "content": previous},
        {"id": "t" + str(rank), "role": "assistant", "content": target},
    ]
    original = {"story": {"id": story_id}, "messages": messages}
    encoded = (json.dumps(original, ensure_ascii=False) + "\n").encode()
    packet = {
        "candidate_id": "fake-" + str(rank),
        "source_story_id": story_id,
        "story_rank": rank,
        "target_message_id": "t" + str(rank),
        "target_sha256": digest(target),
        "target_original_array_index": 2,
        "source_original_raw_zip_sha256": "zip-sha-" + str(rank),
        "source_original_raw_jsonl_sha256": hashlib.sha256(encoded).hexdigest(),
        "frozen_visible_history": [
            {"role": "user", "source_body_sha256": digest(user),
             "original_source_array_index": 0},
            {"role": "assistant", "source_body_sha256": digest(previous),
             "original_source_array_index": 1},
        ],
    }
    return packet, encoded


class TestFullSourceRecovery(unittest.TestCase):
    def setUp(self):
        self.ranks = (6, 8, 9, 10, 12, 14, 15)
        rows = [source_case(rank) for rank in self.ranks]
        self.packets = [p for p, _ in rows]
        self.payloads = {rank: raw for rank, (_, raw)
                         in zip(self.ranks, rows, strict=True)}
        self.dossiers = [
            {"source_story_id": p["source_story_id"],
             "story_rank": p["story_rank"]}
            for p in self.packets
        ]
        self.pins = {rank: "zip-sha-" + str(rank) for rank in self.ranks}

    def recover(self):
        with (
            patch.object(full.replay, "pinned_archive",
                         return_value=(b"synthetic-asset", self.pins)),
            patch.object(full.replay, "discover_raw_zips",
                         return_value={r: b"raw-zip" for r in self.ranks}),
            patch.object(full.replay, "choose_source_jsonl",
                         side_effect=[
                             self.payloads[r] for r in self.ranks]),
        ):
            return full.extract_full_sources(
                Path("/synthetic"), self.packets, self.dossiers)

    def test_seven_full_originals_and_target_pins(self):
        worlds = self.recover()
        self.assertEqual(len(worlds), 7)
        self.assertEqual(sum(len(w["original_root_messages"]) for w in worlds), 21)
        self.assertTrue(all(w["training_admission"] == full.HOLD and
                            not w["semantic_independence_certified"] and
                            not w["original_generated_system_prompt_reconstructed"]
                            for w in worlds))

    def test_source_tampering_fails_closed(self):
        self.packets[0]["target_sha256"] = "0" * 64
        with self.assertRaisesRegex(full.identity.GateHold,
                                    "ORIGINAL_TARGET_ID_ROLE_SHA_CHANGED"):
            self.recover()

    def test_priority_three_is_not_full_graph_approval(self):
        worlds = self.recover()
        tasks = []
        decisions = []
        for i, (a, b) in enumerate(__import__("itertools").combinations(self.ranks, 2)):
            tasks.append({"left_rank": a, "right_rank": b})
            decisions.append({
                "left_rank": a, "right_rank": b,
                "decision": (full.ROUTE_PRIORITY if i < 3 else full.ROUTE_BOUNDED),
                "rationale": "Synthetic decision from bounded sources.",
                "source_citations": [],
            })
        files, safe = full.create_artifacts(
            worlds, tasks, decisions, {"synthetic_hash": "test"})
        self.assertEqual(safe["priority_insufficient_bounded_pairs"], 3)
        self.assertEqual(safe["complete_pair_review_queue"], 21)
        self.assertEqual(safe["train_admitted"], 0)
        self.assertEqual(safe["world_components_certified"], 0)
        self.assertEqual(len([
            x for x in files if x.startswith("R52_PRIVATE_FULL_ORIGINAL_STORY_")]), 7)


if __name__ == "__main__":
    unittest.main()
