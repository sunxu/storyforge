"""Synthetic tests for private W17 semantic-review kit construction."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "privatekit", SCRIPTS / "v03_r50_build_w17_semantic_kit.py"
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def source(rank, shared):
    msgs = [{"role": "user", "content": "unique synthetic " + str(rank)}]
    if shared:
        msgs.append({"role": "assistant", "content": shared})
    msgs.append({"role": "user", "content": "later synthetic context"})
    return {"story": {"id": "synthetic-" + str(rank)}, "messages": msgs}


class W17PrivateKitTests(unittest.TestCase):
    def setUp(self):
        self.shared = "SYNTHETIC SHARED ASSISTANT MESSAGE " * 20
        self.old = {k: source(k, self.shared if k != 7 else None)
                    for k in (2, 4, 7, 10)}
        self.new = source(17, self.shared)
        self.card = {"export_time_card":
                     {"id": "synthetic", "v2_data":
                      {"characters": [{"name": "synthetic-character"}]}}}

    def test_private_kit_contains_evidence_not_verdict(self):
        result = m.kit_from_sources(self.old, self.new, self.card,
                                    m.overlap.normalize(self.shared))
        self.assertEqual(result["status"],
                         "PRIVATE_EVIDENCE_BUILT__AI_REVIEW_PENDING")
        self.assertIn("synthetic-character",
                      str(result["w17_export_card_review_hints"]))
        self.assertEqual(result["semantic_world_alias_gate"], "HOLD")
        self.assertEqual(result["old_world_contexts"]["7"]
                         ["matched_message_occurrences"], 0)

    def test_reject_missing_old_source_match(self):
        self.old[4] = source(4, None)
        with self.assertRaisesRegex(ValueError,
                                    "OLD_MATCHED_SOURCE_LITERAL_MISSING"):
            m.kit_from_sources(self.old, self.new, self.card,
                               m.overlap.normalize(self.shared))

    def test_reject_missing_new_source_match(self):
        with self.assertRaisesRegex(ValueError,
                                    "W17_MATCHED_SOURCE_LITERAL_MISSING"):
            m.kit_from_sources(self.old, source(17, None), self.card,
                               m.overlap.normalize(self.shared))

    def test_neighbors_have_bounded_excerpts(self):
        old = source(2, "X" * 2000)
        data = m.excerpts(old, "x" * 2000)
        self.assertEqual(data["matched_message_occurrences"], 1)
        self.assertTrue(all(len(x["text_excerpt"]) <= 750
                            for x in data["context_examples"][0]["neighbors"]))
        self.assertTrue(any(x["excerpt_truncated"]
                            for x in data["context_examples"][0]["neighbors"]))

    def test_no_automatic_final_seal(self):
        result = m.kit_from_sources(self.old, self.new, self.card,
                                    m.overlap.normalize(self.shared))
        self.assertEqual(result["heldout_final_seal"], "NOT_PERFORMED")


if __name__ == "__main__":
    unittest.main()
