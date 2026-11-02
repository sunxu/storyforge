"""Synthetic-only tests for Gold87/108 target-level reuse. No private data."""
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from legacy_gold_target_reuse import canonical, index_rows, inspect


class ReuseTests(unittest.TestCase):
    def test_target_match_is_not_context_or_quality_pass(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = "synthetic target"
            digest = hashlib.sha256(target.encode()).hexdigest()
            messages = [{"role": "user", "content": "synthetic prompt"}]
            for filename, cols, data, count in (
                ("87.csv", ["story_id", "sample_target_sha256", "review_A", "review_B", "sample_id"],
                 ["story-1", digest, "ACCEPT", "ACCEPT", "a"], 87),
                ("108.csv", ["story_id", "target_sha256", "reviewer1_decision",
                             "reviewer2_decision", "candidate_id"],
                 ["story-2", hashlib.sha256(b"another").hexdigest(), "ACCEPT", "ACCEPT", "b"], 108),
            ):
                with (base / filename).open("w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(cols)
                    for i in range(count):
                        w.writerow([data[0] if i == 0 else f"{data[0]}-{i}"] + data[1:-1] + [f"{data[-1]}-{i}"])
            with (base / "tasks.jsonl").open("w", encoding="utf-8") as f:
                for i in range(7):
                    row = {
                        "schema": "r58_gold195_six_dimension_review_task_private_v1",
                        "case_id": f"canary-{i}",
                        "story_uuid": "story-1",
                        "target_sha256": digest,
                        "target_text": target,
                        "messages": messages,
                        "input_messages_sha256": hashlib.sha256(canonical(messages)).hexdigest(),
                        "quality_v1_admitted": False,
                        "training_authorized": False,
                    }
                    f.write(json.dumps(row) + "\n")
            result, queue = inspect(base / "87.csv", base / "108.csv", base / "tasks.jsonl")
            self.assertEqual(result["counts"]["current_tasks_checked"], 7)
            self.assertEqual(result["counts"]["target_identity_matched"], 7)
            self.assertEqual(result["quality_v1_admitted"], 0)
            self.assertFalse(result["context_changes_verified"])
            self.assertEqual(len(queue), 7)
            self.assertEqual(queue[0]["reason_code"], "HISTORICAL_EVIDENCE_NOT_FULLY_BOUND")

            self.assertNotIn("canary-", json.dumps(result))
            taskfile = base / "tasks.jsonl"
            lines = taskfile.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(lines[0])
            tampered["target_text"] = "tampered synthetic target"
            lines[0] = json.dumps(tampered)
            taskfile.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "TASK_CONTENT_INVALID"):
                inspect(base / "87.csv", base / "108.csv", taskfile)

    def test_duplicate_legacy_candidate_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "87.csv"
            digest = hashlib.sha256(b"synthetic").hexdigest()
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["story_id", "sample_target_sha256", "review_A",
                                 "review_B", "sample_id"])
                for i in range(87):
                    writer.writerow([f"world-{i}", digest, "ACCEPT", "ACCEPT", "same"])
            with self.assertRaisesRegex(ValueError, "LEGACY_DUPLICATE_ID"):
                index_rows(path, 87)


if __name__ == "__main__":
    unittest.main()
