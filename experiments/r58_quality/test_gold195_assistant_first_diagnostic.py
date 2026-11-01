import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_assistant_first_diagnostic import analyze, verified_rows, write_private


def row(i):
    leading = i >= 63
    history = ([{"role": "assistant", "content": "PRIVATE_ORPHAN"},
                {"role": "user", "content": "PRIVATE_PREVIOUS_USER"},
                {"role": "assistant", "content": "PRIVATE_PREVIOUS_REPLY"}]
               if leading else
               [{"role": "user", "content": "PRIVATE_PREVIOUS_USER"},
                {"role": "assistant", "content": "PRIVATE_PREVIOUS_REPLY"}])
    target = "PRIVATE_FROZEN_TARGET_" + str(i)
    return {
        "schema": "r58_gold195_card_gold_semantic_review_private_v1",
        "case_id": "secret-" + str(i),
        "source_history_starts_with_assistant": leading,
        "candidate_status": "PRIVATE_REVIEW_ONLY_NOT_TRAIN_READY",
        "quality_v1_admitted": False,
        "original_history": history,
        "current_user_text": "PRIVATE_CURRENT_USER",
        "target_assistant_text": target,
        "source_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
        "card_snapshot": {"world": "PRIVATE_WORLD"},
        "card_snapshot_sha256": "a" * 64,
        "story_uuid": "private-story",
        "corpus": "synthetic",
    }


class AssistantFirstDiagnosticTests(unittest.TestCase):
    def test_132_private_comparisons_and_no_training(self):
        rows = [row(i) for i in range(195)]
        frozen = copy.deepcopy(rows)
        receipt, cases = analyze(rows, collect=True)
        self.assertEqual(receipt["counts"]["assistant_first_hold"], 132)
        self.assertEqual(receipt["counts"]["user_first_unchanged"], 63)
        self.assertEqual(receipt["counts"]["drop_first_assistant_shape_valid_only"], 132)
        self.assertEqual(len(cases), 132)
        self.assertEqual(cases[0]["original_history"][0]["role"], "assistant")
        self.assertEqual(cases[0]["proposed_history_if_first_assistant_removed"][0]["role"], "user")
        self.assertIsNone(cases[0]["training_candidate_messages"])
        self.assertFalse(cases[0]["approved_history_transform"])
        self.assertEqual(receipt["new_user_turns_invented"], 0)
        self.assertEqual(receipt["quality_v1_admitted"], 0)
        self.assertEqual(rows, frozen)
        summary = json.dumps(receipt)
        self.assertNotIn("PRIVATE_", summary)
        self.assertNotIn("secret-", summary)

    def test_tampered_target_and_history_rejected(self):
        rows = [row(i) for i in range(195)]
        rows[120]["target_assistant_text"] = "MUTATED"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "private.jsonl"
            p.write_text("".join(json.dumps(x) + "\n" for x in rows))
            p.chmod(0o600)
            with self.assertRaises(ValueError):
                verified_rows(p)
        rows = [row(i) for i in range(195)]
        rows[80]["original_history"][1]["role"] = "assistant"
        with self.assertRaises(ValueError):
            analyze(rows)

    def test_permission_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            inp = private / "in.jsonl"
            inp.write_text("".join(json.dumps(row(i)) + "\n" for i in range(195)))
            inp.chmod(0o600)
            rows = verified_rows(inp)
            _, review = analyze(rows, collect=True)
            dest = private / "new.jsonl"
            write_private(dest, repo, review)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(dest.read_text().splitlines()), 132)
            with self.assertRaises(ValueError):
                write_private(dest, repo, review)
            with self.assertRaises(ValueError):
                write_private(repo / "bad.jsonl", repo, review)


if __name__ == "__main__":
    unittest.main()
