"""Synthetic-only tests: no R59 private data, HF access, or GPU."""
import copy
import stat
import tempfile
import unittest
from pathlib import Path

from r59_semantic_review_adapter import (
    SCHEMA,
    STAGE_SCHEMA,
    STAGE_STATUS,
    Hold,
    canon,
    is_inside_git_checkout,
    make_rows,
    run,
    sha,
)


def fixtures():
    priorities = (["HIGH_CONTEXT_RISK"] * 5 +
                  ["TRUNCATED_CONTEXT_REVIEW"] + ["FULL_HISTORY_REVIEW"] * 2)
    selected = []
    stage = []
    for i in range(72):
        story = f"fiction-world-{i % 6}"
        messages = [{"role": "system", "content": "Synthetic generic System."},
                    {"role": "user", "content": f"Synthetic user {i}"}]
        target = f"Synthetic assistant answer {i}"
        h = sha(target.encode())
        stage.append({
            "schema": STAGE_SCHEMA, "status": STAGE_STATUS,
            "case_id": f"case-{i}", "story_id": story, "session_id": "synthetic-session",
            "target_sha256": h, "target_text": target,
            "messages": messages, "input_messages_sha256": sha(canon(messages)),
        })
        if i < 8:
            selected.append({
                "pilot_index": i, "case_id": f"case-{i}",
                "story_id": story, "target_sha256": h,
                "pilot_status": "SELECTED_NOT_REVIEWED", "review_priority": priorities[i],
                "retained_history_messages": 1,
                "removed_prefix_messages": 0 if i >= 6 else 12,
                "assistant_first": False,
            })
    return stage, {"schema": "r59_semantic_pilot8_private_v1", "cases": selected}


class Tests(unittest.TestCase):
    def test_build_no_truncation_and_no_decisions(self):
        stage, pilot = fixtures()
        rows, safe = make_rows(stage, pilot, "a" * 64, "b" * 64)
        self.assertEqual(len(rows), 8)
        self.assertEqual(safe["full_staged_suffix_materialized"], 8)
        self.assertEqual(safe["semantic_reviews_completed"], 0)
        self.assertEqual(rows[0]["visible_history"], stage[0]["messages"][1:])
        self.assertEqual(rows[0]["generic_system_prompt"], stage[0]["messages"][0]["content"])
        self.assertNotIn("unapproved_card", rows[0])
        self.assertEqual(rows[0]["review_decision"], None)
        self.assertEqual(rows[0]["schema"], SCHEMA)

    def test_target_tamper_rejected(self):
        stage, pilot = fixtures()
        stage[0]["target_text"] += " MODIFIED"
        with self.assertRaises(Hold):
            make_rows(stage, pilot, "a" * 64, "b" * 64)

    def test_history_tamper_rejected(self):
        stage, pilot = fixtures()
        stage[0]["messages"][1]["content"] += " MODIFIED"
        with self.assertRaises(Hold):
            make_rows(stage, pilot, "a" * 64, "b" * 64)

    def test_duplicate_pilot_rejected(self):
        stage, pilot = fixtures()
        pilot["cases"][1] = copy.deepcopy(pilot["cases"][0])
        with self.assertRaises(Hold):
            make_rows(stage, pilot, "a" * 64, "b" * 64)

    def test_invalid_coverage_rejected(self):
        stage, pilot = fixtures()
        pilot["cases"][1]["review_priority"] = "FULL_HISTORY_REVIEW"
        with self.assertRaises(Hold):
            make_rows(stage, pilot, "a" * 64, "b" * 64)

    def test_checkout_block_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(is_inside_git_checkout(root / "outside"))
            checkout = root / "repo"
            checkout.mkdir()
            (checkout / ".git").write_text("gitdir: /tmp/synthetic")
            self.assertTrue(is_inside_git_checkout(checkout / "private"))
            self.assertTrue(is_inside_git_checkout(checkout / "nested" / "private"))

    def test_create_only_and_file_modes(self):
        stage, pilot = fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.chmod(0o700)
            stage_path, receipt_path, pilot_path = (root / n for n in ("stage.jsonl", "receipt.json", "pilot.json"))
            stage_raw = b"".join(canon(row) + b"\n" for row in stage)
            stage_path.write_bytes(stage_raw)
            receipt_path.write_bytes(canon({"staged_file_sha256": sha(stage_raw), "context_staged": 72}))
            pilot_path.write_bytes(canon(pilot))
            for p in (stage_path, receipt_path, pilot_path):
                p.chmod(0o600)
            out = root / "new-output"
            safe = run(stage_path, receipt_path, pilot_path, out)
            self.assertEqual(safe["pilot_cases"], 8)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
            for p in out.iterdir():
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600)
            with self.assertRaises(Hold):
                run(stage_path, receipt_path, pilot_path, out)


if __name__ == "__main__":
    unittest.main()