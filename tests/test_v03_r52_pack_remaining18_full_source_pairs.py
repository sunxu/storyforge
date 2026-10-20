"""Synthetic private package tests, no actual story material."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v03_r52_pack_priority_full_source_pairs import fixtures, file
import v03_r52_pack_remaining18_full_source_pairs as pack


def run(src, out, repo):
    all21 = pack.private_file(
        src / "R52_PRIVATE_ALL_21_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl")
    priority = pack.private_file(
        src / "R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl")
    with patch.object(pack, "EXPECTED_ALL21_SHA", pack.sha(all21)), \
         patch.object(pack, "EXPECTED_PRIORITY3_SHA", pack.sha(priority)):
        return pack.package(src, out, repo)


class TestRemaining18SourcePack(unittest.TestCase):
    def test_success_and_exclusion_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            src, out, repo = fixtures(Path(root))
            result = run(src, out, repo)
            self.assertEqual(result["complete_original_worlds_packaged"], 7)
            self.assertEqual(result["remaining_pair_tasks_prepared"], 18)
            self.assertEqual(result["prior_priority_pairs_excluded"], 3)
            self.assertEqual(result["pair_count_each_batch"], [6, 6, 6])
            self.assertEqual(result["all_original_source_messages_verified"], 20577)
            self.assertEqual(result["r51_original_target_pins_verified"], 104)
            self.assertEqual(result["train_admitted"], 0)
            zips = list(out.glob("*.zip"))
            self.assertEqual(len(zips), 1)
            with zipfile.ZipFile(zips[0]) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertEqual(len([n for n in names if n.startswith(
                    "R52_PRIVATE_FULL_ORIGINAL_STORY_")]), 7)
                queues = []
                for batch in (1, 2, 3):
                    fname = f"R52_PRIVATE_REMAINING_18_BATCH_{batch:02d}_PAIR_TASKS.jsonl"
                    subset = [json.loads(x) for x in archive.read(fname).splitlines()]
                    self.assertEqual(len(subset), 6)
                    queues.extend(subset)
                self.assertEqual(len({(p["left_rank"], p["right_rank"])
                                      for p in queues}), 18)
            with self.assertRaisesRegex(pack.PackHold, "OUTPUT_ALREADY_EXISTS"):
                run(src, out, repo)

    def test_altered_source_body_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            src, out, repo = fixtures(Path(root))
            path = src / "R52_PRIVATE_FULL_ORIGINAL_STORY_06.json"
            obj = json.loads(path.read_text())
            obj["original_root_messages"][25]["content"] = "FAKE-TAMPER"
            file(path, json.dumps(obj))
            with self.assertRaisesRegex(
                pack.PackHold, "FULL_ORIGINAL_MESSAGE_SHA_OR_INDEX_CHANGED"):
                run(src, out, repo)

    def test_queue_hash_drift_blocks_packaging(self):
        with tempfile.TemporaryDirectory() as root:
            src, out, repo = fixtures(Path(root))
            with self.assertRaisesRegex(pack.PackHold,
                                        "FROZEN_PAIR_QUEUE_SHA_CHANGED"):
                pack.package(src, out, repo)

    def test_changed_pair_reference_rejected_even_when_hash_recomputed(self):
        with tempfile.TemporaryDirectory() as root:
            src, out, repo = fixtures(Path(root))
            path = src / "R52_PRIVATE_ALL_21_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            rows[4]["right_original_jsonl_sha256"] = "f" * 64
            file(path, "".join(json.dumps(x) + "\n" for x in rows))
            with self.assertRaisesRegex(pack.PackHold,
                                        "PAIR_ORIGINAL_SOURCE_REFERENCE_CHANGED"):
                run(src, out, repo)


if __name__ == "__main__":
    unittest.main()
