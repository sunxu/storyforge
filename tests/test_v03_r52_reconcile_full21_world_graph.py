"""R52 full 21-pair private world-graph consolidation synthetic tests."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v03_r52_pack_priority_full_source_pairs import fixtures
from test_v03_r52_pack_remaining18_full_source_pairs import run as make_zip
import v03_r52_reconcile_full21_world_graph as graph


class GraphClosedEvidenceTests(unittest.TestCase):
    def source_worlds(self, tmp):
        src, out, repo = fixtures(tmp)
        make_zip(src, out, repo)
        zipped = out / "R52_REMAINING_18_FULL_ORIGINAL_WORLD_REVIEW_PRIVATE.zip"
        raw = graph.packaging.private_file(zipped)
        all21 = graph.packaging.private_file(
            src / "R52_PRIVATE_ALL_21_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl")
        pri3 = graph.packaging.private_file(
            src / "R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl")
        return src, zipped, raw, all21, pri3

    def test_missing_inputs_use_safe_names_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "pri"
            remain = root / "remaining"
            post = root / "post"
            for folder in (private, remain, post):
                folder.mkdir(mode=0o700)
            def issues():
                return graph.required_input_status(
                    remain / "source.zip", remain / "safe.json",
                    private / "priority.jsonl", private / "receipt.json",
                    remain, post)
            missing = issues()
            self.assertEqual(len(missing), 12)
            self.assertIn("PRIORITY03_DECISIONS", missing)
            self.assertNotIn(str(root), str(missing))
            for name in ("priority.jsonl", "receipt.json"):
                p = private / name
                p.write_text("{}", encoding="utf8")
                p.chmod(0o600)
            self.assertNotIn("PRIORITY03_DECISIONS", issues())
            self.assertNotIn("PRIORITY03_RECEIPT", issues())
            p = private / "priority.jsonl"
            p.chmod(0o644)
            self.assertEqual(issues()["PRIORITY03_DECISIONS"],
                             "PRIVATE_INPUT_FILE_MODE_UNSAFE")

    def test_recover_seven_stories_and_complete_21_edges(self):
        with tempfile.TemporaryDirectory() as p:
            src, zipped, raw, all21, pri3 = self.source_worlds(Path(p))
            with patch.object(graph, "ZIP_SHA", graph.packaging.sha(raw)), \
                 patch.object(graph.packaging, "EXPECTED_ALL21_SHA",
                              graph.packaging.sha(all21)), \
                 patch.object(graph.packaging, "EXPECTED_PRIORITY3_SHA",
                              graph.packaging.sha(pri3)):
                worlds, pairs = graph.recover_worlds(zipped)
            self.assertEqual(len(worlds), 7)
            self.assertEqual(len(pairs["remaining_keys"]), 18)
            self.assertEqual(len(pairs["priority_keys"]), 3)
            self.assertEqual(len(pairs["remaining_keys"] | pairs["priority_keys"]), 21)
            self.assertEqual(sum(len(x["original_root_messages"])
                                 for x in worlds.values()), 20577)

    def test_hash_and_two_sided_original_citations(self):
        with tempfile.TemporaryDirectory() as p:
            src, zipped, raw, all21, pri3 = self.source_worlds(Path(p))
            with patch.object(graph, "ZIP_SHA", graph.packaging.sha(raw)), \
                 patch.object(graph.packaging, "EXPECTED_ALL21_SHA",
                              graph.packaging.sha(all21)), \
                 patch.object(graph.packaging, "EXPECTED_PRIORITY3_SHA",
                              graph.packaging.sha(pri3)):
                worlds, _ = graph.recover_worlds(zipped)
            a, b = 6, 9
            body = lambda r: worlds[r]["original_root_messages"][0][
                "source_body_sha256"]
            record = {"left_rank": a, "right_rank": b,
                      "source_citations": [
                          {"scope": "FULL_ORIGINAL", "story_rank": r,
                           "original_source_array_index": 0,
                           "source_body_sha256": body(r)}
                          for r in (a, b)]}
            self.assertEqual(graph.referenced_citations(record, worlds), 2)
            record["source_citations"][1]["source_body_sha256"] = "0" * 64
            with self.assertRaisesRegex(
                graph.packaging.PackHold, "SOURCE_CITATION_SHA_OR_DUPLICATE"):
                graph.referenced_citations(record, worlds)

    def test_same_story_citations_are_not_two_sided(self):
        with tempfile.TemporaryDirectory() as p:
            src, zipped, raw, all21, pri3 = self.source_worlds(Path(p))
            with patch.object(graph, "ZIP_SHA", graph.packaging.sha(raw)), \
                 patch.object(graph.packaging, "EXPECTED_ALL21_SHA",
                              graph.packaging.sha(all21)), \
                 patch.object(graph.packaging, "EXPECTED_PRIORITY3_SHA",
                              graph.packaging.sha(pri3)):
                worlds, _ = graph.recover_worlds(zipped)
            messages = worlds[6]["original_root_messages"]
            citations = [
                {"scope": "FULL_ORIGINAL", "story_rank": 6,
                 "original_source_array_index": idx,
                 "source_body_sha256": messages[idx]["source_body_sha256"]}
                for idx in (0, 1)]
            with self.assertRaisesRegex(
                graph.packaging.PackHold, "BOTH_WORLDS_REQUIRE_SOURCE_CITATIONS"):
                graph.referenced_citations({
                    "left_rank": 6, "right_rank": 9,
                    "source_citations": citations,
                }, worlds)


if __name__ == "__main__":
    unittest.main()
