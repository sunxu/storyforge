"""Synthetic-only tests for private W17 seven-gap review workpaper validator."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(FOLDER))
spec = importlib.util.spec_from_file_location(
    "sevenvalidator", FOLDER / "v03_r50_verify_seven_gap_workpaper.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixtures():
    sha = "b" * 64
    packets = [{
        "private_candidate_contexts": [
            {"source_rank": 2, "original_source_message_index": i}
            for i in (15, 17)
        ] + [{"source_rank": 17, "original_source_message_index": 5}]
    } for _ in range(7)]
    decisions = {
        "schema": "storyforge-r50-w17-seven-gap-independent-ai-workpaper-v1",
        "reviewed_packet_manifest_sha256": sha,
        "source_kit_sha256": module.coverage.PINNED_KIT_SHA256,
        "prior_private_decision_sha256": module.coverage.PINNED_DECISION_SHA256,
        "semantic_world_graph_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "model_promotion": False,
        "gap_reviews": [{
            "gap_index": i,
            "assessment": "INSUFFICIENT_CONTEXT",
            "source_refs": [{
                "source_rank": 2,
                "source_message_index": 15,
                "full_untruncated_message_reviewed": False,
            }],
            "private_reasoning": "Synthetic record lacks distinctive and validated identity details in source excerpts.",
            "historical_card_timing": "NOT_CHECKED",
            "remaining_evidence_requirements": ["Check the original full narrative"],
        } for i in range(7)],
    }
    return sha, packets, decisions


def validate(d):
    sha, packets, _ = fixtures()
    return module.summarize({}, packets, sha, d, "c" * 64)


class W17SevenGapWorkpaperTests(unittest.TestCase):
    def test_valid_private_workpaper_remains_hold(self):
        _, _, decision = fixtures()
        result = validate(decision)
        self.assertEqual(len(result["assessments"]), 7)
        self.assertEqual(result["assessment_counts"]["INSUFFICIENT_CONTEXT"], 7)
        self.assertEqual(result["semantic_world_graph_gate"], "HOLD")
        self.assertEqual(result["heldout_final_seal"], "NOT_PERFORMED")
        self.assertNotIn("Synthetic record", str(result))

    def test_unsupported_or_fabricated_message_index_rejected(self):
        _, _, decision = fixtures()
        decision["gap_reviews"][0]["source_refs"][0]["source_message_index"] = 99
        with self.assertRaisesRegex(
            ValueError, "WORKPAPER_REFERENCE_NOT_IN_PINNED_PACKET"
        ):
            validate(decision)

    def test_missing_gap_rejected(self):
        _, _, decision = fixtures()
        decision["gap_reviews"].pop()
        with self.assertRaisesRegex(ValueError,
                                    "EXACT_SEVEN_WORKPAPER_REVIEWS_REQUIRED"):
            validate(decision)

    def test_supported_evidence_requires_actual_citation(self):
        _, _, decision = fixtures()
        decision["gap_reviews"][0]["assessment"] = "SUPPORTED_IN_SCOPED_CONTEXT"
        decision["gap_reviews"][0]["source_refs"] = []
        with self.assertRaisesRegex(ValueError,
                                    "SUPPORTED_GAP_NEEDS_EXISTING_SOURCE_REF"):
            validate(decision)

    def test_unknown_card_status_rejected(self):
        _, _, decision = fixtures()
        decision["gap_reviews"][0]["historical_card_timing"] = "TRUST_EXPORT"
        with self.assertRaisesRegex(
            ValueError, "WORKPAPER_HISTORICAL_CARD_STATUS_INVALID"
        ):
            validate(decision)

    def test_unresolved_missing_evidence_must_be_named(self):
        _, _, decision = fixtures()
        decision["gap_reviews"][1]["remaining_evidence_requirements"] = []
        with self.assertRaisesRegex(
            ValueError, "OPEN_GAP_MUST_DECLARE_MISSING_EVIDENCE"
        ):
            validate(decision)

    def test_private_manifest_loaded_with_real_manifest_sha_not_last_packet_sha(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "private"
            folder.mkdir(mode=0o700)
            entries = []
            for i in range(7):
                filename = f"gap_{i:02d}.json"
                packet = {
                    "schema": "storyforge-r50-w17-seven-gap-private-context-packet-v1",
                    "gap_index": i,
                    "status": "CONTEXT_EXPANDED__NOT_AI_REVIEWED",
                    "source_world_graph_gate": "HOLD",
                    "final_heldout_seal": "NOT_PERFORMED",
                    "original_private_index_sha256":
                        module.coverage.PINNED_INDEX_SHA256,
                    "private_candidate_contexts": [],
                }
                data = (json.dumps(packet) + "\n").encode()
                f = folder / filename
                f.write_bytes(data)
                os.chmod(f, 0o600)
                entries.append({
                    "gap_index": i, "file": filename,
                    "sha256": module.digest(data),
                    "private_candidate_count": 0,
                })
            manifest = {
                "schema": "storyforge-r50-w17-seven-gap-private-context-manifest-v1",
                "private_index_sha256": module.coverage.PINNED_INDEX_SHA256,
                "packet_count": 7, "packets": entries,
                "semantic_graph_gate": "HOLD",
                "final_heldout_seal": "NOT_PERFORMED",
                "ai_review_executed": False,
            }
            raw = (json.dumps(manifest) + "\n").encode()
            mp = folder / "manifest.json"
            mp.write_bytes(raw)
            os.chmod(mp, 0o600)
            expected = module.digest(raw)
            with patch.object(module, "PINNED_MANIFEST_SHA256", expected):
                loaded, packets, sha = module.load_manifest(folder)
            self.assertEqual(loaded["packet_count"], 7)
            self.assertEqual(len(packets), 7)
            self.assertEqual(sha, expected)
            self.assertNotEqual(sha, entries[-1]["sha256"])

    def test_manifest_sha_pin_rejects_tampering(self):
        module.verify_manifest_sha(b"synthetic", expected=module.digest(b"synthetic"))
        with self.assertRaisesRegex(ValueError, "PRIVATE_MANIFEST_SHA256_MISMATCH"):
            module.verify_manifest_sha(b"mutated", expected=module.digest(b"original"))

    def test_full_message_claim_requires_untruncated_authenticated_packet(self):
        sha, packets, decision = fixtures()
        decision["gap_reviews"][0]["source_refs"][0]["full_untruncated_message_reviewed"] = True
        with self.assertRaisesRegex(ValueError,
                                    "FULL_MESSAGE_CLAIM_NOT_SUPPORTED_BY_PACKET"):
            module.summarize({}, packets, sha, decision, "c" * 64)

    def test_full_message_claim_accepted_only_if_packet_contains_entire_sha_text(self):
        sha, packets, decision = fixtures()
        source = next(row for row in packets[0]["private_candidate_contexts"]
                      if row["source_rank"] == 2 and
                      row["original_source_message_index"] == 15)
        source["focus_excerpt"] = "Synthetic complete message"
        source["focus_start_character"] = 0
        source["focus_is_truncated"] = False
        source["original_message_codepoints"] = len(source["focus_excerpt"])
        source["original_message_sha256"] = module.digest(
            source["focus_excerpt"].encode("utf8")
        )
        decision["gap_reviews"][0]["source_refs"][0]["full_untruncated_message_reviewed"] = True
        report = module.summarize({}, packets, sha, decision, "c" * 64)
        self.assertEqual(report["assessments"][0]["reported_full_message_review_count"], 1)

    def test_semantic_pass_is_never_authorized(self):
        _, _, decision = fixtures()
        decision["semantic_world_graph_gate"] = "PASS"
        with self.assertRaisesRegex(
            ValueError, "PREMATURE_SEMANTIC_PASS_OR_MODEL_PROMOTION"
        ):
            validate(decision)


if __name__ == "__main__":
    unittest.main()
