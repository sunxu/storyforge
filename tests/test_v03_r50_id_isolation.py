"""Synthetic fail-closed tests for the R50 exact-ID screen."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_id_isolation import HISTORIC, ROOT, check


def fixture(repo: Path, *, collide: bool = False) -> None:
    for rank in range(16, 21):
        folder = repo / ROOT / f"{rank}-test"
        folder.mkdir(parents=True)
        (folder / "age-review.json").write_text(json.dumps({
            "story_id": f"story-{rank}", "rank": rank,
            "has_explicit_under_18": False, "requires_sample_level_review": True,
        }), encoding="utf-8")
        (folder / "runtime-context.json").write_text(json.dumps({
            "story_id": f"story-{rank}", "rank": rank,
            "session_id": f"session-{rank}",
        }), encoding="utf-8")
    for rel, count in HISTORIC:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            for index in range(count):
                identifier = "story-16" if collide and index == 0 else f"old-{index}"
                stream.write(json.dumps({"metadata": {
                    "story_id": identifier,
                    "session_id": f"old-session-{index}",
                }}) + "\n")


class R50ExactIdTests(unittest.TestCase):
    def test_no_id_overlap_does_not_grant_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            fixture(repo)
            report = check(repo)
            self.assertEqual(report["world_count"], 5)
            self.assertEqual(sum(report["history_row_counts"].values()), 215)
            self.assertEqual(report["heldout_cases_sealed"], 0)
            self.assertEqual(report["semantic_alias_review"], "PENDING")

    def test_collision_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            fixture(repo, collide=True)
            with self.assertRaisesRegex(ValueError, "collision"):
                check(repo)

    def test_missing_historical_reference_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            fixture(repo)
            (repo / HISTORIC[0][0]).unlink()
            with self.assertRaises(FileNotFoundError):
                check(repo)


if __name__ == "__main__":
    unittest.main()
