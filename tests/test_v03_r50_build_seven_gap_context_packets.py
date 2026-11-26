"""Purely synthetic tests for immutable seven-gap private contextual packets."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "gapcontext", SCRIPTS / "v03_r50_build_seven_gap_context_packets.py"
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def source(rank):
    return {"messages": [
        {"role": "user", "content": "context-before"},
        {"role": "assistant", "content": ("Unique synthetic history for world " +
                                          str(rank) + " ")*40},
        {"role": "user", "content": "context-after"},
    ]}


def synthetic_index():
    gaps = []
    for i in range(7):
        by_rank = {}
        for rank in m.SCOPED:
            text = source(rank)["messages"][1]["content"]
            by_rank[str(rank)] = {
                "source_rank": rank,
                "ranked_candidates": [{
                    "source_message_index": 1,
                    "source_role": "assistant",
                    "excerpt_start_character": 0,
                    "excerpt": text[:1000],
                    "lexical_ranking_score": 12,
                    "matched_trigram_count": 3,
                }],
            }
        gaps.append({
            "gap_index": i,
            "requirement_from_original_private_ai_decision":
                "synthetic evidence need " + str(i),
            "evidence_status": "UNREVIEWED",
            "candidate_source_excerpts": by_rank,
        })
    return {
        "schema": m.coverage.EXPECTED_SCHEMA,
        "status": "SEVEN_GAP_LEXICAL_LOCATOR_ONLY__AI_REVIEW_NOT_EXECUTED",
        "source_ranks": list(m.SCOPED),
        "gap_count": 7,
        "kit_sha256": m.coverage.PINNED_KIT_SHA256,
        "decision_sha256": m.coverage.PINNED_DECISION_SHA256,
        "world_graph_admission": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "no_ai_model_inference": True,
        "no_git_write": True,
        "gaps": gaps,
    }


class ContextPacketsTests(unittest.TestCase):
    def test_exact_seven_packets_non_semantic(self):
        packets = m.build_packets(synthetic_index(),
                                  {rank: source(rank) for rank in m.SCOPED})
        self.assertEqual(len(packets), 7)
        self.assertEqual(packets[0]["private_candidate_count"], 5)
        self.assertEqual(packets[0]["source_world_graph_gate"], "HOLD")
        self.assertEqual(packets[0]["final_heldout_seal"], "NOT_PERFORMED")
        self.assertTrue(packets[0]["lexical_retrieval_is_not_semantic_support"])

    def test_verbatim_candidate_provenance(self):
        report = m.build_packets(synthetic_index(),
                                 {rank: source(rank) for rank in m.SCOPED})
        self.assertTrue(all(row["index_excerpt_verbatim_checked"]
                            for row in report[0]["private_candidate_contexts"]))
        self.assertEqual(report[0]["private_candidate_contexts"][0]
                         ["original_source_message_index"], 1)

    def test_tampered_index_excerpt_is_rejected(self):
        index = synthetic_index()
        index["gaps"][0]["candidate_source_excerpts"]["2"][
            "ranked_candidates"][0]["excerpt"] = "Not in original"
        with self.assertRaisesRegex(
            ValueError, "INDEX_EXCERPT_NOT_VERBATIM_FROM_ORIGINAL"
        ):
            m.build_packets(index, {rank: source(rank) for rank in m.SCOPED})

    def test_tampered_original_source_role_is_rejected(self):
        index = synthetic_index()
        index["gaps"][0]["candidate_source_excerpts"]["2"][
            "ranked_candidates"][0]["source_role"] = "user"
        with self.assertRaisesRegex(ValueError, "INDEX_SOURCE_MESSAGE_ROLE_MISMATCH"):
            m.build_packets(index, {rank: source(rank) for rank in m.SCOPED})

    def test_missing_old_world_07_is_hard_failure(self):
        s = {rank: source(rank) for rank in m.SCOPED if rank != 7}
        with self.assertRaisesRegex(ValueError,
                                    "EXPECTED_FIVE_IMMUTABLE_SOURCE_WORLDS"):
            m.build_packets(synthetic_index(), s)

    def test_neighbor_and_focus_are_bounded(self):
        report = m.build_packets(synthetic_index(),
                                 {rank: source(rank) for rank in m.SCOPED})
        item = report[0]["private_candidate_contexts"][0]
        self.assertLessEqual(len(item["focus_excerpt"]), m.CENTER_CHARS)
        self.assertTrue(all(len(n["excerpt"]) <= m.NEIGHBOR_CHARS
                            for n in item["source_neighbors"]))


if __name__ == "__main__":
    unittest.main()
