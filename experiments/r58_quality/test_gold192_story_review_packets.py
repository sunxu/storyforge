"""Synthetic tests for per-world Gold192 review packet assembly."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from gold192_story_review_packets import build_packets, write_private
from legacy_gold_target_reuse import canonical


def make_inputs(root, conflict=False, cross_cohort=False):
    tasks_path = root / "tasks.jsonl"
    queue_path = root / "queue.jsonl"
    scope_path = root / "scope.jsonl"
    with (
        tasks_path.open("w", encoding="utf-8") as tasks,
        queue_path.open("w", encoding="utf-8") as queue,
        scope_path.open("w", encoding="utf-8") as scope,
    ):
        for i in range(195):
            excluded = i < 3
            reason = (
                "WORLD_OR_TARGET_IDENTITY_HOLD" if excluded
                else "CONTEXT_EQUIVALENCE_UNVERIFIED" if i < 108
                else "HISTORICAL_EVIDENCE_NOT_FULLY_BOUND"
            )
            status = "EXCLUDED_WORLD_ID_UNRESOLVED" if excluded else "CANDIDATE_ONLY_QUALITY_HOLD"
            world = (
                f"synthetic-gold108-world-{i % 7}" if i < 108
                else "synthetic-gold108-world-0" if cross_cohort
                else f"synthetic-gold87-world-{i % 6}"
            )
            card = {"world": world, "rules": ["synthetic"]}
            if conflict and i == 27:
                card = {"world": world, "rules": ["conflicting"]}
            card_text = json.dumps(card, ensure_ascii=False, sort_keys=True, indent=2)
            card_hash = hashlib.sha256(card_text.encode()).hexdigest()
            assistant_first = 3 <= i < 135
            history = (
                [{"role": "assistant", "content": "synthetic orphan assistant"}]
                if assistant_first else [
                    {"role": "user", "content": "synthetic previous user"},
                    {"role": "assistant", "content": "synthetic previous assistant"},
                ]
            )
            messages = [
                {"role": "system", "content": card_text},
                *history,
                {"role": "user", "content": "synthetic current user"},
            ]
            target = f"synthetic target {i}"
            row = {
                "schema": "r58_gold195_six_dimension_review_task_private_v1",
                "case_id": f"synthetic-case-{i}",
                "story_uuid": world,
                "card_snapshot_sha256": card_hash,
                "card_source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
                "input_design_status": "PROPOSED_OFFLINE_CARD_NOT_APPROVED",
                "messages": messages,
                "source_history_starts_with_assistant": assistant_first,
                "target_text": target,
                "input_messages_sha256": hashlib.sha256(canonical(messages)).hexdigest(),
                "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
                "review_instructions": {
                    "dimensions": {
                        "chinese_prose": "test",
                        "character_consistency": "test",
                        "npc_initiative": "test",
                        "player_agency": "test",
                        "rule_fidelity": "test",
                        "narrative_continuity": "test",
                    },
                    "dimension_floors": {
                        "chinese_prose": 4,
                        "character_consistency": 4,
                        "npc_initiative": 3,
                        "player_agency": 4,
                        "rule_fidelity": 4,
                        "narrative_continuity": 4,
                    },
                    "score_range": [1, 5],
                    "two_independent_blinded_reviews_required": True,
                    "source_world_card_is_unapproved": True,
                    "check_card_gold_contradictions": True,
                    "do_not_infer_missing_world_facts": True,
                },
                "review_status": "UNREVIEWED",
                "review_results": [],
                "world_component_id": None,
                "split": None,
                "quality_v1_admitted": False,
                "training_authorized": False,
            }
            tasks.write(json.dumps(row) + "\n")
            queue.write(json.dumps({
                "case_id": row["case_id"], "reason_code": reason,
            }) + "\n")
            scope.write(json.dumps({
                "case_id": row["case_id"], "scope_status": status,
                "quality_v1_admitted": False, "training_authorized": False,
            }) + "\n")
    return tasks_path, queue_path, scope_path


class Gold192StoryPacketTests(unittest.TestCase):
    def test_192_cases_group_into_13_story_packets(self):
        with tempfile.TemporaryDirectory() as td:
            receipt, packets = build_packets(*make_inputs(Path(td)))
            self.assertEqual(receipt["candidate_cases"], 192)
            self.assertEqual(receipt["story_packets"], 13)
            self.assertEqual(receipt["story_uuids_present_in_both_cohorts"], 0)
            self.assertEqual(receipt["assistant_first_cases"], 132)
            self.assertEqual(receipt["user_first_cases"], 60)
            self.assertEqual(sum(p["case_count"] for p in packets), 192)
            self.assertTrue(all(not p["world_card_approved_for_system"] for p in packets))
            self.assertNotIn("synthetic target", json.dumps(receipt))


    def test_private_packet_write_is_exclusive_and_outside_repo(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            repo = base / "repo"
            repo.mkdir()
            private = base / "private"
            private.mkdir(mode=0o700)
            output = private / "packets.jsonl"
            receipt, packets = build_packets(*make_inputs(base))
            write_private(output, repo, packets)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                write_private(output, repo, packets)
            with self.assertRaises(ValueError):
                write_private(repo / "inside.jsonl", repo, packets)

    def test_cross_cohort_world_overlap_holds(self):
        with (
            tempfile.TemporaryDirectory() as td,
            self.assertRaisesRegex(ValueError, "PACKET_CROSS_COHORT_WORLD_OVERLAP"),
        ):
            build_packets(*make_inputs(Path(td), cross_cohort=True))

    def test_conflicting_card_snapshot_within_story_holds(self):
        with (
            tempfile.TemporaryDirectory() as td,
            self.assertRaisesRegex(ValueError, "PACKET_WORLD_CARD_CONFLICT"),
        ):
            build_packets(*make_inputs(Path(td), conflict=True))


if __name__ == "__main__":
    unittest.main()
