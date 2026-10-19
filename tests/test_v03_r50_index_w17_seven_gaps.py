"""Synthetic checks only: private W17 seven-gap lexical locator."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "r50seven", SCRIPTS / "v03_r50_index_w17_seven_gaps.py"
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def synthetic_sources():
    return {i: {"messages": [
        {"role": "assistant", "content":
         "Synthetic galaxy-specific character alias and timeline " * 8},
        {"role": "user", "content": "ordinary background message" * 6},
    ]} for i in m.SCOPED_RANKS}


class SevenGapIndexTests(unittest.TestCase):
    def test_seven_gaps_remain_semantic_hold(self):
        gaps = ["galaxy-specific timeline"] * 7
        report = m.build_inventory(gaps, synthetic_sources())
        self.assertEqual(report["gap_count"], 7)
        self.assertEqual(set(report["gaps"][0]["candidate_source_excerpts"]),
                         {"2", "4", "7", "10", "17"})
        self.assertEqual(report["world_graph_admission"], "HOLD")
        self.assertEqual(report["heldout_final_seal"], "NOT_PERFORMED")
        self.assertTrue(report["no_ai_model_inference"])
        self.assertTrue(report["no_git_write"])

    def test_synthetic_lexical_match_is_not_semantic_pass(self):
        records = m.candidate_messages("galaxy-specific alias",
                                       synthetic_sources()[2])
        self.assertGreater(len(records), 0)
        self.assertIn("Synthetic galaxy-specific", records[0]["excerpt"])
        self.assertLessEqual(len(records[0]["excerpt"]), m.MAX_EXCERPT)

    def test_no_lexical_match_is_not_forged(self):
        records = m.candidate_messages("鳳鸚麒麟鹹酥雞",
                                       synthetic_sources()[4])
        self.assertEqual(records, [])

    def test_wrong_number_of_gaps_fails(self):
        with self.assertRaisesRegex(ValueError,
                                    "SEVEN_EXACT_PRIVATE_GAPS_REQUIRED"):
            m.build_inventory(["only one"], synthetic_sources())

    def test_wrong_source_set_fails(self):
        broken = synthetic_sources()
        del broken[7]
        with self.assertRaisesRegex(ValueError,
                                    "W17_SCOPED_SOURCE_RANKS_MISMATCH"):
            m.build_inventory(["need missing transcript"] * 7, broken)


if __name__ == "__main__":
    unittest.main()
