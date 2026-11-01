import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_six_dimension_review_tasks import (
    build, check_history, prepare_row, write_private,
)


def example(i=0, leading=False):
    card = {"characters": [{"name": "PRIVATE_NPC"}], "world": "PRIVATE_CANON"}
    content = json.dumps(card, ensure_ascii=False, sort_keys=True, indent=2).encode()
    target = f"PRIVATE_TARGET_{i}"
    return {
        "schema": "r58_gold195_card_gold_semantic_review_private_v1",
        "case_id": f"private-{i}",
        "candidate_status": "PRIVATE_REVIEW_ONLY_NOT_TRAIN_READY",
        "quality_v1_admitted": False,
        "card_snapshot": card,
        "card_snapshot_sha256": hashlib.sha256(content).hexdigest(),
        "story_uuid": "private_world",
        "card_source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
        "original_history": ([{"role":"assistant","content":"old"}]
                             if leading else [{"role":"user","content":"old user"},
                                               {"role":"assistant","content":"old assistant"}]),
        "source_history_starts_with_assistant": leading,
        "current_user_text": "PRIVATE_USER",
        "target_assistant_text": target,
        "source_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
    }


class ReviewTasksTests(unittest.TestCase):
    def test_63_review_tasks_preserve_history_without_passing_quality(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "private.jsonl"
            with path.open("w") as f:
                for i in range(195):
                    f.write(json.dumps(example(i, leading=i >= 63)) + "\n")
            receipt, tasks = build(path, collect=True)
            self.assertEqual(receipt["counts"]["user_first_review_tasks_prepared"], 63)
            self.assertEqual(receipt["counts"]["LEADING_ASSISTANT_CONTEXT_HOLD"], 132)
            self.assertEqual(receipt["quality_v1_admitted"], 0)
            self.assertEqual(len(tasks), 63)
            self.assertEqual(tasks[0]["messages"][-1]["role"], "user")
            self.assertEqual(tasks[0]["messages"][1]["role"], "user")
            self.assertEqual(tasks[0]["target_text"], "PRIVATE_TARGET_0")
            self.assertEqual(tasks[0]["review_results"], [])
            self.assertNotIn("PRIVATE_NPC", json.dumps(receipt))
            self.assertNotIn("PRIVATE_TARGET", json.dumps(receipt))

    def test_digest_mutation_is_rejected(self):
        row = example()
        row["card_snapshot"]["world"] = "mutated"
        with self.assertRaises(ValueError):
            prepare_row(row)

    def test_leading_assistant_never_silently_truncated(self):
        draft, reason = prepare_row(example(1, leading=True))
        self.assertIsNone(draft)
        self.assertEqual(reason, "LEADING_ASSISTANT_CONTEXT_HOLD")

    def test_bad_history_is_hold(self):
        row = example()
        row["original_history"][0]["role"] = "assistant"
        task, reason = prepare_row(row)
        self.assertIsNone(task)
        self.assertEqual(reason, "HISTORY_INPUT_SHAPE_HOLD")

    def test_history_roles(self):
        self.assertTrue(check_history([]))
        self.assertTrue(check_history([{"role":"user","content":"ok"}]))
        self.assertFalse(check_history([{"role":"assistant","content":"bad"}]))

    def test_private_output_not_in_checkout(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            dest = private / "new.jsonl"
            write_private(dest, repo, [prepare_row(example())[0]])
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                write_private(dest, repo, [])
            with self.assertRaises(ValueError):
                write_private(repo / "new.jsonl", repo, [])


if __name__ == "__main__":
    unittest.main()
