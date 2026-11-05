"""Synthetic Gold192 scope tests. No private story content."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from gold192_scope_exclusion import inspect_scope
from legacy_gold_target_reuse import canonical


class TestGold192Scope(unittest.TestCase):
    def make_inputs(self, root, bad=False):
        tasks = root / "tasks.jsonl"
        queue = root / "queue.jsonl"
        with tasks.open("w", encoding="utf-8") as t, queue.open("w", encoding="utf-8") as q:
            for i in range(195):
                target = "synthetic"
                messages = [{"role": "user", "content": "canary"}]
                row = {
                    "schema": "r58_gold195_six_dimension_review_task_private_v1",
                    "case_id": f"synthetic-{i}",
                    "story_uuid": "synthetic-world",
                    "target_text": target,
                    "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
                    "messages": messages,
                    "input_messages_sha256": hashlib.sha256(canonical(messages)).hexdigest(),
                    "quality_v1_admitted": False,
                    "training_authorized": False,
                }
                t.write(json.dumps(row) + "\n")
                reason = (
                    "WORLD_OR_TARGET_IDENTITY_HOLD" if i < (2 if bad else 3)
                    else "CONTEXT_EQUIVALENCE_UNVERIFIED" if i < 108
                    else "HISTORICAL_EVIDENCE_NOT_FULLY_BOUND"
                )
                q.write(json.dumps({"case_id": f"synthetic-{i}", "reason_code": reason}) + "\n")
        return tasks, queue

    def test_192_scope(self):
        with tempfile.TemporaryDirectory() as td:
            tasks, queue = self.make_inputs(Path(td))
            receipt = inspect_scope(tasks, queue)
            self.assertEqual(receipt["scoped_candidate_count"], 192)
            self.assertEqual(receipt["excluded_world_identity_unresolved"], 3)
            self.assertEqual(receipt["quality_v1_admitted"], 0)
            self.assertNotIn("synthetic-", json.dumps(receipt))

    def test_wrong_exclusion_count_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            tasks, queue = self.make_inputs(Path(td), bad=True)
            with self.assertRaisesRegex(ValueError, "SCOPE_EXPECTED_COUNTS_MISMATCH"):
                inspect_scope(tasks, queue)


if __name__ == "__main__":
    unittest.main()
