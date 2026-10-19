"""Synthetic tests for seven-gap private index coverage checker; no source text."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location(
    "w17coverage", ROOT / "v03_r50_verify_seven_gap_coverage.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_index() -> dict:
    return {
        "schema": mod.EXPECTED_SCHEMA,
        "status": "SEVEN_GAP_LEXICAL_LOCATOR_ONLY__AI_REVIEW_NOT_EXECUTED",
        "source_ranks": list(mod.RANKS),
        "gap_count": 7,
        "kit_sha256": mod.PINNED_KIT_SHA256,
        "decision_sha256": mod.PINNED_DECISION_SHA256,
        "world_graph_admission": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "no_ai_model_inference": True,
        "no_git_write": True,
        "gaps": [{
            "gap_index": i,
            "requirement_from_original_private_ai_decision":
                "Synthetic private requirement " + str(i),
            "evidence_status": "UNREVIEWED",
            "candidate_source_excerpts": {
                str(rank): {
                    "source_rank": rank,
                    "ranked_candidates": (
                        [{"source_message_index": i,
                          "lexical_ranking_score": 3,
                          "excerpt": "SYNTHETIC source extract"}]
                        if rank in (2, 17) else []
                    ),
                } for rank in mod.RANKS
            },
        } for i in range(7)],
    }


class SevenGapCoverageTests(unittest.TestCase):
    def test_exact_index_returns_only_safe_aggregate(self):
        report = mod.summarize(synthetic_index())
        self.assertEqual(report["gap_count"], 7)
        self.assertEqual(report["total_bounded_lexical_candidates"], 14)
        self.assertEqual(report["per_gap"][0]["candidate_count"], 2)
        self.assertEqual(report["semantic_world_graph_gate"], "HOLD")
        self.assertEqual(report["heldout_final_seal"], "NOT_PERFORMED")
        self.assertNotIn("SYNTHETIC source extract", str(report))
        self.assertNotIn("Synthetic private requirement", str(report))

    def test_wrong_source_rank_rejected(self):
        record = synthetic_index()
        record["gaps"][0]["candidate_source_excerpts"]["2"]["source_rank"] = 4
        with self.assertRaisesRegex(ValueError, "SOURCE_RANK_MISMATCH"):
            mod.summarize(record)

    def test_missing_real_gap_rejected(self):
        record = synthetic_index()
        record["gaps"].pop()
        with self.assertRaisesRegex(ValueError, "SEVEN_ACTUAL_REVIEW_GAPS_REQUIRED"):
            mod.summarize(record)

    def test_no_lexical_match_is_not_semantic_pass(self):
        record = synthetic_index()
        for rank in mod.RANKS:
            record["gaps"][1]["candidate_source_excerpts"][str(rank)]["ranked_candidates"] = []
        report = mod.summarize(record)
        self.assertEqual(report["per_gap"][1]["candidate_count"], 0)
        self.assertEqual(report["per_gap"][1]["review_status"], "UNREVIEWED")
        self.assertTrue(report["per_gap"][1]
                        ["no_lexical_candidate_is_not_evidence_of_absence"])

    def test_oversized_extract_rejected(self):
        record = synthetic_index()
        record["gaps"][0]["candidate_source_excerpts"]["2"]["ranked_candidates"][0]["excerpt"] = "Z" * 1001
        with self.assertRaisesRegex(ValueError, "INVALID_OR_OVERSIZED_PRIVATE_EXCERPT"):
            mod.summarize(record)

    def test_unsafe_self_certification_fails(self):
        record = synthetic_index()
        record["world_graph_admission"] = "PASS"
        with self.assertRaisesRegex(ValueError, "INDEX_ADMISSION_STATUS_UNSAFE"):
            mod.summarize(record)


if __name__ == "__main__":
    unittest.main()
