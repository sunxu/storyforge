"""Synthetic-only world UUID guard; no real StoryForge text or identities."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r52_world_exact_isolation as world


def write(path, rows):
    if isinstance(rows, list):
        body = "".join(json.dumps(row) + "\n" for row in rows)
    else:
        body = json.dumps(rows)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)


def prepare(root):
    root.mkdir(exist_ok=True, mode=0o700)
    roots, held, pre = [], [], []
    ranks = (6, 8, 9, 10, 12, 14, 15)
    for idx, rank in enumerate(ranks):
        sid = "synthetic-world-%02d" % idx
        positive = 7 if idx < 4 else 6
        # 7+7+7+7+6+6+6 = 46
        negative = 3 if idx < 2 else 2
        # 3+3+2+2+2+2+2 = 16
        for i in range(positive + negative):
            good = i < positive
            case = {
                "schema": world.QUALITY_SCHEMA, "private_do_not_commit": True,
                "candidate_id": "fake-%d-%d" % (idx, i),
                "source_story_id": sid, "story_rank": rank,
                "target_sha256": "b" * 64,
                "split": None, "training_admission": world.HOLD,
                "owner_rights": "OWNER_ATTESTED_FULL_OWNERSHIP",
                "final_quality_and_safety_signoff": "PENDING",
                "linked_world_component_verified": False,
                "quality_review_route": (
                    "NO_CARD_CONTEXT_AND_TARGET_POSSIBLE__HOLD"
                    if good else "TARGET_PLAYER_AGENCY_DEFECT__HOLD"),
                "eligibility_stage": (
                    "QUALITY_POSSIBLE__NEEDS_GATES"
                    if good else "QUALITY_DEFECT_HOLD"),
            }
            (roots if good else held).append(case)
        pre.append({
            "schema": world.WORLD_SCHEMA,
            "private_do_not_commit": True,
            "source_story_id": sid, "source_story_rank": rank,
            "first_pass_possible": positive, "quality_holds": negative,
            "linked_or_alias_world_component": "UNRESOLVED",
            "component_isolation_pass": False, "world_split": None,
        })
    write(root / "R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl", roots)
    write(root / "R52_PRIVATE_QUALITY_16_HOLD_REGISTER.jsonl", held)
    write(root / "R52_PRIVATE_WORLD_COMPONENT_PREFLIGHT.jsonl", pre)
    write(root / "R52_POST_QUALITY_SAFE_AGGREGATE.json", {
        "schema": world.AGGREGATE_SCHEMA,
        "status": "R52_ALL_62_QUALITY_REVIEWS_REVERIFIED__NO_ADMISSION",
        "cases_revalidated": 62, "quality_possible_first_pass": 46,
        "quality_holds": 16, "source_citations_revalidated": 205,
        "train_admitted": 0, "validation_admitted": 0,
    })


def hist():
    return (
        {"train": {"old-train"}, "validation": {"old-val"}, "test": {"old-test"}},
        {"v01_frozen_sha256_verified": True},
    )


class TestR52WorldExactIsolation(unittest.TestCase):
    def test_disjoint_preserves_all_manual_holds(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            prepare(d)
            with patch.object(world, "historical_registry", return_value=hist()):
                queue, safe = world.screen(d, d)
            self.assertEqual(len(queue), 7)
            self.assertEqual(safe["first_pass_candidates"], 46)
            self.assertEqual(safe["quality_holds"], 16)
            self.assertEqual(safe["world_split_assigned"], 0)
            self.assertFalse(safe["semantic_world_independence_verified"])
            self.assertTrue(all(row["train_val_split"] is None and
                                not row["owner_component_isolation_signed"]
                                for row in queue))

    def test_historical_exact_overlap_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            prepare(d)
            overlap = hist()[0]
            overlap["train"].add("synthetic-world-00")
            with patch.object(world, "historical_registry",
                              return_value=(overlap, {})):
                with self.assertRaisesRegex(world.GateHold, "EXACT_HISTORICAL_UUID_OVERLAP"):
                    world.screen(d, d)

    def test_tampered_world_preflight_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            prepare(d)
            p = d / "R52_PRIVATE_WORLD_COMPONENT_PREFLIGHT.jsonl"
            rows = [json.loads(x) for x in p.read_text().splitlines()]
            rows[0]["world_split"] = "train"
            write(p, rows)
            with self.assertRaisesRegex(world.GateHold, "WORLD_PREFLIGHT_PROVENANCE_CHANGED"):
                world.cases_and_worlds(d)


if __name__ == "__main__":
    unittest.main()
