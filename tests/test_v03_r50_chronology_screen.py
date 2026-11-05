"""Synthetic-only tests for R50 temporal source screen."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_chronology_screen import SOURCE, run


def fixture(root: Path, *, update_after_first=False, missing_time=False,
            bad_identity=False):
    for rank in range(16, 21):
        folder = root / SOURCE / f"{rank}-case"
        folder.mkdir(parents=True)
        doc = {
            "rank": rank,
            "story_id": f"story-{rank}",
            "session_id": f"session-{rank}",
            "chat_window": {
                "first_message_at": "2026-01-03T00:00:00+00:00",
                "last_message_at": "2026-01-07T00:00:00+00:00",
            },
            "export_time_card": {
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-05T00:00:00+00:00"
                if update_after_first and rank == 16
                else "2026-01-02T00:00:00+00:00",
            },
            "content_versions": [],
            "moderation_source_snapshots": [],
        }
        runtime = {"rank": rank, "story_id": f"story-{rank}",
                   "session_id": f"session-{rank}"}
        if bad_identity and rank == 17:
            runtime["story_id"] = "not-this-story"
        msgs = [
            {"role": "user", "content": "fictional example",
             "created_at": None if missing_time and rank == 16
             else "2026-01-03T00:00:00+00:00"},
            {"role": "assistant", "content": "example result",
             "created_at": "2026-01-06T00:00:00+00:00"},
        ]
        (folder / "story-cards.json").write_text(
            json.dumps(doc), encoding="utf-8")
        (folder / "runtime-context.json").write_text(
            json.dumps(runtime), encoding="utf-8")
        (folder / (folder.name + ".jsonl")).write_text(
            json.dumps({"rank": rank, "messages": msgs}) + "\n", encoding="utf-8")


class ChronologyTests(unittest.TestCase):
    def test_baseline_remains_pending(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root)
            r = run(root)
            self.assertEqual(r["total_message_records"], 10)
            self.assertEqual(r["fresh_heldout_cases"], 0)
            self.assertEqual(r["status"],
                             "CHRONOLOGY_METADATA_CHECKED__POINT_IN_TIME_MANUAL_REVIEW_PENDING")

    def test_later_card_edit_flags_prior_messages(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, update_after_first=True)
            r = run(root)
            entry = next(x for x in r["stories"] if x["story_number"] == 16)
            self.assertTrue(entry["export_card_last_edited_after_chat_start"])
            self.assertEqual(entry["messages_before_export_card_update"], 1)

    def test_missing_message_time_marked(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, missing_time=True)
            r = run(root)
            self.assertEqual(r["stories"][0]["messages_missing_timestamp"], 1)

    def test_card_identity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, bad_identity=True)
            with self.assertRaisesRegex(ValueError, "story id mismatch"):
                run(root)

    def test_version_snapshot_timestamp_buckets(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root)
            p = root / SOURCE / "16-case" / "story-cards.json"
            card = json.loads(p.read_text(encoding="utf-8"))
            card["content_versions"] = [
                {"created_at": "2026-01-02T00:00:00+00:00"},
                {"created_at": "2026-01-04T00:00:00+00:00"},
                {"created_at": "2026-01-08T00:00:00+00:00"},
                {"revision": 4},
            ]
            p.write_text(json.dumps(card), encoding="utf-8")
            result = run(root)
            one = next(w for w in result["stories"] if w["story_number"] == 16)
            self.assertEqual(one["content_version_timestamp_buckets"],
                             {"before_chat": 1, "during_chat": 1,
                              "after_chat": 1, "undated": 1})

    def test_source_edit_date_and_archive_date_kept_separate(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root)
            p = root / SOURCE / "16-case" / "story-cards.json"
            card = json.loads(p.read_text(encoding="utf-8"))
            card["content_versions"] = [{
                "source_updated_at": "2026-01-02T00:00:00+00:00",
                "archived_at": "2026-01-08T00:00:00+00:00",
            }]
            p.write_text(json.dumps(card), encoding="utf-8")
            row = next(x for x in run(root)["stories"] if x["story_number"] == 16)
            self.assertEqual(row["content_version_source_update_buckets"]["before_chat"], 1)
            self.assertEqual(row["content_version_archive_time_buckets"]["after_chat"], 1)
            self.assertEqual(row["historical_version_source_timestamp_only"],
                             "SOURCE_ASSERTION_NOT_PER_CASE_PROOF")

    def test_naive_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root)
            p = root / SOURCE / "18-case" / "story-cards.json"
            card = json.loads(p.read_text(encoding="utf-8"))
            card["export_time_card"]["updated_at"] = "2026-01-05"
            p.write_text(json.dumps(card), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "timezone-naive"):
                run(root)


if __name__ == "__main__":
    unittest.main()
