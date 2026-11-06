"""Synthetic-only tests for the Gold72 Reviewer B2 package builder."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.r58_quality import r60_reviewer_b2_package as m


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def jsonl(rows):
    return b"".join(canonical(row) + b"\n" for row in rows)


def fixture():
    source_packets = []
    staged_rows = []
    source_index = []
    for story_index in range(13):
        cases = []
        start = story_index * 15
        end = min(192, start + 15)
        card = {"cardType": "story", "name": f"Synthetic {story_index}"}
        card_sha = hashlib.sha256(
            json.dumps(card, ensure_ascii=False, sort_keys=True, indent=2).encode()
        ).hexdigest()
        for i in range(start, end):
            target = f"Synthetic target text {i}"
            digest = hashlib.sha256(target.encode()).hexdigest()
            case = {
                "case_id": f"private-case-{i:03d}",
                "cohort": "gold87" if i % 2 else "gold108",
                "legacy_evidence_state": "PRIVATE_LEGACY_LABEL",
                "priority": "P1_ASSISTANT_FIRST_CONTEXT" if i % 2 else "P2_USER_FIRST_CONTEXT",
                "history_starts_with_assistant": True,
                "history": [
                    {"role": "assistant", "content": f"Prior assistant {i}"},
                    {"role": "user", "content": f"Prior user {i}"},
                    {"role": "assistant", "content": f"Prior assistant continuation {i}"},
                ],
                "current_user_text": f"Current user {i}",
                "target_assistant_text": target,
                "target_sha256": digest,
                "review_status": "UNREVIEWED",
                "review_focus": ["Check player agency", "Check continuity"],
            }
            cases.append(case)
            source_index.append((case, f"story-{story_index:02d}"))
            if i < 72:
                staged_rows.append({
                    "schema": m.STAGE_SCHEMA,
                    "status": m.STAGE_STATUS,
                    "case_id": case["case_id"],
                    "target_sha256": digest,
                })
        source_packets.append({
            "schema": m.SOURCE_PACKET_SCHEMA,
            "status": m.SOURCE_PACKET_STATUS,
            "story_uuid": f"story-{story_index:02d}",
            "world_card": card,
            "world_card_sha256": card_sha,
            "world_card_source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
            "review_protocol": {"dimensions": ["six"]},
            "review_protocol_addendum": {"preserve_history": True},
            "cases": cases,
        })
    instructions = "# Reviewer B2\n" + ("Independent blind review instructions. " * 8)
    return source_packets, staged_rows, instructions


def deterministic_tokens():
    counter = iter(range(1, 100))
    return lambda: f"fixed-{next(counter):04d}"


class ReviewerB2PackageTests(unittest.TestCase):
    def test_builds_72_new_blind_ids_without_owner_fields(self):
        source, staged, instructions = fixture()
        packets, mapping, counts = m.build(
            source, staged, instructions,
            token_factory=deterministic_tokens(),
            shuffle=lambda values: values.reverse(),
        )
        self.assertEqual(counts["candidate_count"], 72)
        self.assertEqual(counts["story_packet_count"], 5)
        self.assertEqual(sum(p["case_count"] for p in packets), 72)
        self.assertEqual(len({c["blind_case_id"] for p in packets for c in p["cases"]}), 72)
        self.assertEqual(len(mapping), 72)
        self.assertTrue(all(row["blind_case_id"].startswith("B2-") for row in mapping))
        self.assertEqual(
            {row["target_sha256"] for row in mapping},
            {row["target_sha256"] for row in staged},
        )
        self.assertFalse(counts["reviewer_a_materials_read"])
        self.assertFalse(counts["reviewer_b1_materials_read"])
        for packet in packets:
            self.assertEqual(packet["reviewer"], "B2")
            self.assertIn("independent_recheck_only", packet["review_protocol_addendum"])
            for case in packet["cases"]:
                self.assertNotIn("case_id", case)
                self.assertNotIn("cohort", case)
                self.assertNotIn("review_status", case)
                self.assertTrue(case["blind_case_id"].startswith("B2-"))

    def test_rejects_stage_case_id_target_sha_crosswire(self):
        source, staged, instructions = fixture()
        staged[0]["target_sha256"] = "f" * 64
        with self.assertRaisesRegex(m.PackageHold, "GOLD72_STAGE_SOURCE_BINDING_MISMATCH"):
            m.build(source, staged, instructions)

    def test_rejects_duplicate_stage_identity(self):
        source, staged, instructions = fixture()
        staged[1]["case_id"] = staged[0]["case_id"]
        with self.assertRaisesRegex(m.PackageHold, "GOLD72_STAGE_IDENTITY_DUPLICATE"):
            m.build(source, staged, instructions)

    def test_rejects_source_target_text_tampering(self):
        source, staged, instructions = fixture()
        source[0]["cases"][0]["target_assistant_text"] = "tampered"
        with self.assertRaisesRegex(m.PackageHold, "GOLD192_CASE_SOURCE_INVALID"):
            m.build(source, staged, instructions)

    def test_rejects_random_id_collision(self):
        source, staged, instructions = fixture()
        with self.assertRaisesRegex(m.PackageHold, "B2_RANDOM_ID_COLLISION"):
            m.build(source, staged, instructions, token_factory=lambda: "same")

    def test_run_writes_private_package_and_safe_receipt(self):
        source, staged, instructions = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir(mode=0o700)
            private_parent = Path(tmp) / "private"
            private_parent.mkdir(mode=0o700)
            source_path = private_parent / "source.jsonl"
            stage_path = private_parent / "stage.jsonl"
            stage_safe_path = private_parent / "stage-safe.json"
            instructions_path = private_parent / "instructions.md"
            source_raw = jsonl(source)
            stage_raw = jsonl(staged)
            instructions_raw = instructions.encode()
            source_path.write_bytes(source_raw)
            stage_path.write_bytes(stage_raw)
            stage_safe = {
                "schema": m.STAGING_RECEIPT_SCHEMA,
                "status": m.STAGING_RECEIPT_STATUS,
                "staged_file_sha256": hashlib.sha256(stage_raw).hexdigest(),
                "source_context_file_sha256": "a" * 64,
                "source_rows": 72,
                "context_staged": 72,
                "context_structure_hold": 0,
                "source_histories_mutated": False,
                "original_staging_mutated": False,
                "quality_v1_admitted": 0,
                "training_authorized": False,
                "gpu_started": False,
                "r50_accessed": False,
            }
            stage_safe_path.write_text(json.dumps(stage_safe))
            instructions_path.write_bytes(instructions_raw)
            for path in (source_path, stage_path, stage_safe_path, instructions_path):
                path.chmod(0o600)
            output = private_parent / "b2-package"
            with (
                patch.object(m, "GOLD192_SOURCE_SHA256", hashlib.sha256(source_raw).hexdigest()),
                patch.object(m, "GOLD72_STAGE_SHA256", hashlib.sha256(stage_raw).hexdigest()),
            ):
                safe = m.run(
                    source_path, stage_path, stage_safe_path,
                    instructions_path, output, root,
                )
            self.assertEqual(safe["status"], "REVIEWER_B2_PACKAGE_BUILT__AWAITING_INDEPENDENT_EXECUTION")
            self.assertEqual(safe["candidate_count"], 72)
            self.assertFalse(safe["reviewer_a_or_b1_results_included"])
            self.assertTrue((output / "R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl").is_file())
            self.assertTrue((output / "R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json").is_file())
            self.assertTrue((output / "R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json").is_file())
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o700)
            self.assertTrue(all((path.stat().st_mode & 0o777) == 0o600 for path in output.iterdir()))

    def test_run_rejects_staging_receipt_pin_mismatch(self):
        source, staged, instructions = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir(mode=0o700)
            parent = Path(tmp) / "private"
            parent.mkdir(mode=0o700)
            paths = [parent / name for name in ("source", "stage", "safe", "instructions")]
            paths[0].write_bytes(jsonl(source))
            paths[1].write_bytes(jsonl(staged))
            paths[2].write_text(json.dumps({
                "schema": m.STAGING_RECEIPT_SCHEMA,
                "status": m.STAGING_RECEIPT_STATUS,
                "staged_file_sha256": "0" * 64,
            }))
            paths[3].write_text(instructions)
            for path in paths:
                path.chmod(0o600)
            with (
                patch.object(m, "GOLD192_SOURCE_SHA256", hashlib.sha256(paths[0].read_bytes()).hexdigest()),
                patch.object(m, "GOLD72_STAGE_SHA256", hashlib.sha256(paths[1].read_bytes()).hexdigest()),
            ):
                with self.assertRaisesRegex(m.PackageHold, "GOLD72_STAGING_RECEIPT_INVALID"):
                    m.run(*paths[:1], paths[1], paths[2], paths[3], parent / "out", root)


if __name__ == "__main__":
    unittest.main()
