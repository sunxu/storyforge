"""Synthetic-only checks for R59 review prompt preparation."""
import json
import stat
import tempfile
import unittest
from pathlib import Path

from r59_semantic_review_prompt import (
    INPUT_SCHEMA,
    canon,
    make_prompts,
    run,
    sha,
)


def example():
    result = []
    for i in range(8):
        target = f"Synthetic target {i}"
        result.append({"schema": INPUT_SCHEMA, "pilot_index": i,
                       "generic_system_prompt": "Generic instructions, not a world card.",
                       "visible_history": [{"role": "user", "content": f"Synthetic user {i}"}],
                       "target_text": target, "target_sha256": sha(target.encode()),
                       "history_coverage": {"scope": "FULL_STAGED_SUFFIX_ONLY",
                                            "retained_history_messages": 1,
                                            "removed_upstream_prefix_messages": i,
                                            "context_semantically_verified": False,
                                            "historical_world_card_approved": False},
                       "review_decision": None,
                       "quality_v1_admitted": False, "training_authorized": False})
    return result


class Tests(unittest.TestCase):
    def test_exact_full_history_and_prompt_fingerprint(self):
        original = example()
        prompts, safe = make_prompts(original)
        self.assertEqual(len(prompts), 8)
        self.assertEqual(safe["review_decisions"], 0)
        payload = json.loads(prompts[1]["messages"][1]["content"].split("待审材料：\n", 1)[1])
        self.assertEqual(payload["visible_history"], original[1]["visible_history"])
        self.assertNotIn("unapproved_card", payload)
        self.assertEqual(payload["history_coverage"]["removed_upstream_prefix_messages"], 1)
        self.assertEqual(prompts[0]["prompt_fingerprint"], prompts[7]["prompt_fingerprint"])

    def test_reject_changed_target(self):
        rows = example()
        rows[0]["target_text"] = "tampered"
        with self.assertRaises(ValueError):
            make_prompts(rows)

    def test_reject_unverified_or_misdeclared_coverage(self):
        rows = example()
        rows[0]["history_coverage"]["context_semantically_verified"] = True
        with self.assertRaises(ValueError):
            make_prompts(rows)
        rows = example()
        rows[0]["history_coverage"]["retained_history_messages"] = 2
        with self.assertRaises(ValueError):
            make_prompts(rows)

    def test_invalid_8_indices(self):
        rows = example()
        rows[1]["pilot_index"] = 0
        with self.assertRaises(ValueError):
            make_prompts(rows)

    def test_create_only_and_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.chmod(0o700)
            path = root / "input.jsonl"
            raw = b"".join(canon(r) + b"\n" for r in example())
            path.write_bytes(raw)
            path.chmod(0o600)
            output = root / "out"
            safe = run(path, sha(raw), output)
            self.assertEqual(safe["prompt_rows"], 8)
            for f in output.iterdir():
                self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
            with self.assertRaises(ValueError):
                run(path, sha(raw), output)

    def test_input_pin_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.chmod(0o700)
            path = root / "input.jsonl"
            path.write_bytes(b"".join(canon(r) + b"\n" for r in example()))
            path.chmod(0o600)
            with self.assertRaises(ValueError):
                run(path, "0" * 64, root / "out")


if __name__ == "__main__":
    unittest.main()