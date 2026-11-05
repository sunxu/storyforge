"""Fake-only tests for R52 three-priority-pair full-source packaging."""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_pack_priority_full_source_pairs as kit


RANKS = (6, 8, 9, 10, 12, 14, 15)


def file(path, payload):
    path.write_text(payload, encoding="utf8")
    path.chmod(0o600)


def fixtures(folder: Path):
    root = folder / "source"
    output = folder / "out"
    repo = folder / "repo"
    for d in (root, output, repo):
        d.mkdir(mode=0o700)
    total, pins_total, identities = 0, 0, {}
    for i, rank in enumerate(RANKS):
        count = 2940 if i < 4 else 2939
        pins = 15 if i < 6 else 14
        msgs = []
        target_pins = []
        for j in range(count):
            body = f"FAKE-narrative-message-{rank}-{j}"
            md = {
                "original_source_array_index": j,
                "original_source_message_id": f"synthetic-{rank}-{j}",
                "role": "assistant" if j < pins else "user",
                "content": body,
                "source_body_sha256": kit.sha(body.encode()),
            }
            msgs.append(md)
            if j < pins:
                target_pins.append({
                    "candidate_id": f"fake-{rank}-{j}",
                    "target_original_array_index": j,
                    "target_sha256": md["source_body_sha256"],
                })
        world = {
            "schema": "storyforge-r52-private-full-original-world-v1",
            "private_do_not_commit": True,
            "story_rank": rank,
            "source_story_id": f"fictional-world-{rank}",
            "original_source_jsonl_sha256": kit.sha(str(rank).encode()),
            "source_archive_outer_sha256": kit.EXPECTED_OUTER_SHA,
            "training_admission": kit.HOLD,
            "original_generated_system_prompt_reconstructed": False,
            "semantic_independence_certified": False,
            "original_root_messages": msgs,
            "r51_frozen_target_pins_verified": target_pins,
        }
        file(root / f"R52_PRIVATE_FULL_ORIGINAL_STORY_{rank:02d}.json",
             json.dumps(world))
        identities[rank] = world
        total += count
        pins_total += pins
    assert total == 20577 and pins_total == 104
    all_pairs, priority = [], []
    for i, (a, b) in enumerate(itertools.combinations(RANKS, 2)):
        pair = {
            "schema": "storyforge-r52-private-full-source-world-pair-task-v1",
            "private_do_not_commit": True,
            "left_rank": a,
            "right_rank": b,
            "left_source_story_id": identities[a]["source_story_id"],
            "right_source_story_id": identities[b]["source_story_id"],
            "left_original_jsonl_sha256": identities[a]["original_source_jsonl_sha256"],
            "right_original_jsonl_sha256": identities[b]["original_source_jsonl_sha256"],
            "left_full_original_file": f"R52_PRIVATE_FULL_ORIGINAL_STORY_{a:02d}.json",
            "right_full_original_file": f"R52_PRIVATE_FULL_ORIGINAL_STORY_{b:02d}.json",
            "training_admission": kit.HOLD,
            "full_source_reviewer_decision": "PENDING",
            "related_world_graph_signed": False,
            "semantic_independence_verified": False,
            "bounded_decision": (kit.PRIORITY if i < 3 else
                                 "NO_LINK_OBSERVED_IN_BOUNDED_EVIDENCE__HOLD"),
        }
        all_pairs.append(pair)
        if i < 3:
            priority.append(pair)
    for name, rows in (
        ("R52_PRIVATE_ALL_21_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl", all_pairs),
        ("R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl", priority),
    ):
        file(root / name, "".join(json.dumps(x) + "\n" for x in rows))
    receipt = {
        "schema": "storyforge-r52-full-original-world-recovery-safe-aggregate-v1",
        "status": kit.SAFE_STATUS,
        "full_original_story_exports_verified": 7,
        "full_original_source_messages": total,
        "frozen_r51_target_pin_checks_in_seven_worlds": pins_total,
        "bounded_citations_revalidated": 126,
        "complete_pair_review_queue": 21,
        "priority_insufficient_bounded_pairs": 3,
        "original_source_bundle_sha256": kit.EXPECTED_OUTER_SHA,
        "r50_sealed_heldout_opened": False,
        "world_components_certified": 0,
        "world_split_assigned": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
    }
    file(root / "R52_FULL_ORIGINAL_WORLD_RECOVERY_SAFE_AGGREGATE.json",
         json.dumps(receipt))
    return root, output, repo


class TestPriorityFullSourceKit(unittest.TestCase):
    def test_private_zip_has_all_required_full_story_files(self):
        with tempfile.TemporaryDirectory() as work:
            src, out, repo = fixtures(Path(work))
            safe = kit.package(src, out, repo)
            self.assertEqual(safe["priority_pairs"], 3)
            self.assertEqual(safe["all_original_source_messages_verified"], 20577)
            self.assertEqual(safe["r51_original_target_pins_verified"], 104)
            self.assertEqual(safe["priority_complete_worlds_packaged"], 4)
            self.assertEqual(safe["world_split_assigned"], 0)
            zips = list(out.glob("*.zip"))
            self.assertEqual(len(zips), 1)
            self.assertEqual(zips[0].stat().st_mode & 0o777, 0o600)
            with zipfile.ZipFile(zips[0]) as zf:
                self.assertIsNone(zf.testzip())
                self.assertEqual(len(zf.namelist()), 7)
            with self.assertRaisesRegex(kit.PackHold, "OUTPUT_ALREADY_EXISTS"):
                kit.package(src, out, repo)

    def test_modified_original_message_sha_blocks_package(self):
        with tempfile.TemporaryDirectory() as work:
            src, out, repo = fixtures(Path(work))
            path = src / "R52_PRIVATE_FULL_ORIGINAL_STORY_06.json"
            obj = json.loads(path.read_text())
            obj["original_root_messages"][20]["content"] = "TAMPERED BODY"
            file(path, json.dumps(obj))
            with self.assertRaisesRegex(
                    kit.PackHold, "FULL_ORIGINAL_MESSAGE_SHA_OR_INDEX_CHANGED"):
                kit.package(src, out, repo)

    def test_wrong_priority_pair_blocks_package(self):
        with tempfile.TemporaryDirectory() as work:
            src, out, repo = fixtures(Path(work))
            path = src / "R52_PRIVATE_PRIORITY_03_FULL_SOURCE_PAIR_REVIEW_QUEUE.jsonl"
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            rows[0]["left_original_jsonl_sha256"] = "f" * 64
            file(path, "".join(json.dumps(r) + "\n" for r in rows))
            with self.assertRaisesRegex(kit.PackHold, "PRIORITY_PAIR_MISMATCH"):
                kit.package(src, out, repo)


if __name__ == "__main__":
    unittest.main()
