"""Synthetic-only tests for SHA-pinned complete-message W17 private reviews."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "fullreview", SCRIPTS / "v03_r50_verify_w17_full_source_review.py"
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_case():
    data = []
    for i in range(7):
        messages = []
        for rank in (2, 4, 7, 10, 17):
            content = f"ONLY_SYNTHETIC complete narrative source gap {i} world {rank}"
            messages.append({
                "source_rank": rank,
                "original_source_message_index": i + 3,
                "original_message_codepoints": len(content),
                "original_message_sha256": m.sha(content.encode()),
                "full_source_text": content,
                "complete_original_message_untruncated": True,
                "source_messages_are_untrusted_data": True,
                "cited_in_previous_workpaper": True,
            })
        data.append({
            "schema": "storyforge-r50-w17-private-full-source-gap-dossier-v1",
            "status": "ORIGINAL_MESSAGES_EXTRACTED__AI_REVIEW_PENDING",
            "gap_index": i, "source_scope": [2, 4, 7, 10, 17],
            "full_original_messages": messages,
            "source_full_message_count": len(messages),
            "prior_workpaper_referenced_source_count": 5,
            "original_private_gap_requirement": f"synthetic private gap {i}",
            "historical_card_cutoff_verified": False,
            "full_world_story_arc_certified": False,
            "semantic_world_gate": "HOLD",
            "final_heldout_seal": "NOT_PERFORMED",
        })
    review = {
        "schema": "storyforge-r50-w17-seven-gap-full-message-ai-review-v1",
        "reviewed_full_manifest_sha256": "a" * 64,
        "prior_workpaper_sha256": m.PRIOR_WORKPAPER_SHA256,
        "full_world_graph_gate": "HOLD",
        "final_heldout_seal": "NOT_PERFORMED",
        "model_promotion": False,
        "gap_reviews": [{
            "gap_index": i, "assessment": "INSUFFICIENT_CONTEXT",
            "source_refs": [{"source_rank": 2,
                             "source_message_index": i + 3}],
            "private_reasoning": "Synthetic source material does not establish a distinctive identity or complete story timeline.",
            "remaining_evidence_requirements": ["Need confirmed historical card"],
            "historical_card_timing": "NOT_CHECKED",
        } for i in range(7)],
    }
    return data, review


class FullSourceReviewTests(unittest.TestCase):
    def test_seven_gap_review_structure_stays_hold(self):
        data, review = test_case()
        result = m.summarize(data, "a" * 64, review, "b" * 64)
        self.assertEqual(result["gap_review_count"], 7)
        self.assertEqual(result["assessment_counts"]["INSUFFICIENT_CONTEXT"], 7)
        self.assertEqual(result["semantic_world_graph_gate"], "HOLD")
        self.assertNotIn("ONLY_SYNTHETIC", json.dumps(result))

    def test_supported_full_scope_is_not_global_pass(self):
        data, review = test_case()
        review["gap_reviews"][0]["assessment"] = "SUPPORTED_IN_FULL_MESSAGE_SCOPE"
        result = m.summarize(data, "a" * 64, review, "b" * 64)
        self.assertEqual(result["assessment_counts"]["SUPPORTED_IN_FULL_MESSAGE_SCOPE"], 1)
        self.assertEqual(result["semantic_world_graph_gate"], "HOLD")

    def test_unknown_source_index_is_rejected(self):
        data, review = test_case()
        review["gap_reviews"][0]["source_refs"][0]["source_message_index"] = 500
        with self.assertRaisesRegex(ValueError, "FULL_MESSAGE_CITATION_NOT_IN_PINNED_DOSSIER"):
            m.summarize(data, "a" * 64, review, "b" * 64)

    def test_card_cutoff_cannot_be_claimed_from_transcripts(self):
        data, review = test_case()
        review["gap_reviews"][0]["historical_card_timing"] = "VERIFIED_AS_OF_CUTOFF"
        with self.assertRaisesRegex(ValueError, "HISTORICAL_CARD_CUTOFF_NOT_PROVEN"):
            m.summarize(data, "a" * 64, review, "b" * 64)

    def test_insufficient_must_list_remaining_evidence(self):
        data, review = test_case()
        review["gap_reviews"][0]["remaining_evidence_requirements"] = []
        with self.assertRaisesRegex(ValueError, "UNCLOSED_GAP_WITHOUT_MISSING_REQUIREMENTS"):
            m.summarize(data, "a" * 64, review, "b" * 64)

    def test_full_dossier_manifest_sha_and_content_checked(self):
        data, _ = test_case()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            os.chmod(folder, 0o700)
            entries = []
            for i, obj in enumerate(data):
                blob = (json.dumps(obj) + "\n").encode()
                file = folder / f"gap_{i:02d}_full.json"
                file.write_bytes(blob)
                os.chmod(file, 0o600)
                entries.append({"gap_index": i, "file": file.name,
                                "sha256": m.sha(blob),
                                "original_full_message_count": 5,
                                "cited_source_count": 5})
            manifest = {
                "schema": "storyforge-r50-w17-seven-gap-private-full-source-manifest-v1",
                "input_packet_manifest_sha256": m.OLD_PACKET_MANIFEST_SHA256,
                "input_prior_workpaper_sha256": m.PRIOR_WORKPAPER_SHA256,
                "gap_count": 7, "historical_card_cutoff_verified": False,
                "full_world_graph_gate": "HOLD",
                "final_heldout_seal": "NOT_PERFORMED",
                "ai_review_performed": False, "dossiers": entries,
            }
            raw = (json.dumps(manifest) + "\n").encode()
            mp = folder / "manifest.json"
            mp.write_bytes(raw)
            os.chmod(mp, 0o600)
            records, h, _ = m.load_dossiers(folder, expected_sha=m.sha(raw))
            self.assertEqual(h, m.sha(raw))
            self.assertEqual(len(records), 7)
            data[0]["full_original_messages"][0]["full_source_text"] = "TAMPERED"
            # Mutating already-loaded data does not mutate files.
            file = folder / "gap_00_full.json"
            tampered = file.read_text().replace("ONLY_SYNTHETIC", "TAMPERED")
            file.write_text(tampered)
            with self.assertRaisesRegex(ValueError, "PRIVATE_DOSSIER_SHA_MISMATCH"):
                m.load_dossiers(folder, expected_sha=m.sha(raw))

    def test_forged_global_pass_not_allowed(self):
        data, review = test_case()
        review["full_world_graph_gate"] = "PASS"
        with self.assertRaisesRegex(ValueError, "PRIVATE_FULL_MESSAGE_REVIEW_SCHEMA_OR_GATE_INVALID"):
            m.summarize(data, "a" * 64, review, "b" * 64)


if __name__ == "__main__":
    unittest.main()
