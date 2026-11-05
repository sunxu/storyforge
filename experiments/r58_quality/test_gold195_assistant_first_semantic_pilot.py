import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_assistant_first_semantic_pilot import (
    prepare, read_comparisons, write_private,
)
from gold195_source_review_packet import canon


def example(i):
    history = [
        {"role": "assistant", "content": "PRIVATE_LEADING_" + str(i)},
        {"role": "user", "content": "PRIVATE_USER_" + str(i)},
        {"role": "assistant", "content": "PRIVATE_REPLY_" + str(i)},
    ]
    proposed = history[1:]
    target = "PRIVATE_TARGET_" + str(i)
    return {
        "schema": "r58_gold195_assistant_first_context_diagnostic_private_v1",
        "case_id": "private-case-" + str(i),
        "story_uuid": "world-" + str(i % 13),
        "source_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
        "original_history_sha256": hashlib.sha256(canon(history)).hexdigest(),
        "proposed_history_sha256": hashlib.sha256(canon(proposed)).hexdigest(),
        "leading_assistant_sha256": hashlib.sha256(history[0]["content"].encode()).hexdigest(),
        "original_history": history,
        "proposed_history_if_first_assistant_removed": proposed,
        "current_user_text": "PRIVATE_CURRENT_USER",
        "frozen_target_text": target,
        "source_card_snapshot": {"world": "PRIVATE_CARD_" + str(i)},
        "approved_history_transform": False,
        "quality_v1_admitted": False,
        "training_candidate_messages": None,
        "training_authorized": False,
    }


class SemanticPilotTests(unittest.TestCase):
    def test_cross_world_selection_all_hold(self):
        rows = [example(i) for i in range(132)]
        receipt, selected = prepare(rows)
        self.assertEqual(receipt["source_comparisons_verified"], 132)
        self.assertEqual(receipt["distinct_worlds_in_pilot"], 10)
        self.assertEqual([r["pilot_label"] for r in selected],
                         ["pilot%02d" % i for i in range(1, 11)])
        self.assertEqual(len({r["story_uuid"] for r in selected}), 10)
        self.assertTrue(all(r["review_status"] == "UNREVIEWED" for r in selected))
        self.assertTrue(all(r["training_candidate_messages"] is None for r in selected))
        self.assertEqual(receipt["quality_v1_admitted"], 0)
        self.assertNotIn("PRIVATE_TARGET", json.dumps(receipt))

    def test_private_source_hash_and_write_guards(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            path = private / "comparisons.jsonl"
            path.write_bytes(b"".join(canon(example(i)) + b"\n" for i in range(132)))
            path.chmod(0o600)
            rows = read_comparisons(path)
            _, tasks = prepare(rows)
            output = private / "pilot.jsonl"
            write_private(output, repo, tasks)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(output.read_text().splitlines()), 10)
            with self.assertRaises(ValueError):
                write_private(output, repo, tasks)
            with self.assertRaises(ValueError):
                write_private(repo / "bad.jsonl", repo, tasks)
            tampered = [example(i) for i in range(132)]
            tampered[50]["original_history"][0]["content"] = "TAMPERED"
            path.write_bytes(b"".join(canon(x) + b"\n" for x in tampered))
            with self.assertRaises(ValueError):
                read_comparisons(path)

    def test_single_world_still_selects_ten(self):
        rows = [example(i) for i in range(132)]
        for row in rows:
            row["story_uuid"] = "one-world"
        receipt, selected = prepare(rows)
        self.assertEqual(len(selected), 10)
        self.assertEqual(receipt["distinct_worlds_in_pilot"], 1)


if __name__ == "__main__":
    unittest.main()
