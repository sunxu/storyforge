import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from r59_sft_context_window import _is_inside_repository, rebuild_preview_rows

SYSTEM = "approved system prompt"


def validate_fixture(row):
    messages = row["messages"]
    if messages[0]["content"] != SYSTEM:
        raise ValueError("system pin")
    target_sha = hashlib.sha256(messages[-1]["content"].encode()).hexdigest()
    if target_sha != row["metadata"]["source_target_sha256"]:
        raise ValueError("target hash")


def make_row(history_roles, target="fixed target"):
    messages = [{"role": "system", "content": SYSTEM, "loss": False}]
    for index, role in enumerate(history_roles):
        messages.append({"role": role, "content": f"history-{index}", "loss": False})
    messages.append({"role": "user", "content": "current user", "loss": False})
    messages.append({"role": "assistant", "content": target, "loss": True})
    original = [
        {"role": item["role"], "content": item["content"]}
        for item in messages[:-1]
    ]
    return {
        "messages": messages,
        "metadata": {
            "status": "ENGINEERING_PREVIEW_NOT_ADMITTED",
            "source_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
            "input_messages_sha256": hashlib.sha256(json.dumps(
                original, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest(),
        },
    }


class ContextWindowTests(unittest.TestCase):
    def test_keeps_full_history_when_it_fits(self):
        row = make_row(["assistant", "user", "assistant"])
        rebuilt, safe = rebuild_preview_rows(
            [row], lambda candidate: len(candidate["messages"]),
            validate_row=validate_fixture,
        )
        self.assertEqual(rebuilt[0]["messages"], row["messages"])
        self.assertEqual(safe["rows_rebuilt"], 1)
        self.assertEqual(safe["messages_dropped"], 0)

    def test_drops_only_prefix_and_starts_on_user_boundary(self):
        row = make_row(["assistant", "user", "assistant", "user", "assistant"])
        original = copy.deepcopy(row)

        def measure(candidate):
            history = candidate["messages"][1:-2]
            return 20 if len(history) > 3 else 10

        rebuilt, safe = rebuild_preview_rows(
            [row], measure, max_length=10, validate_row=validate_fixture
        )
        messages = rebuilt[0]["messages"]
        self.assertEqual(messages[0], original["messages"][0])
        self.assertEqual(messages[-2:], original["messages"][-2:])
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1:-1], original["messages"][4:-1])
        self.assertEqual(messages[-1]["content"], original["messages"][-1]["content"])
        self.assertTrue(all(item["loss"] is False for item in messages[:-1]))
        self.assertTrue(messages[-1]["loss"])
        self.assertEqual(safe["messages_dropped"], 3)

    def test_target_tampering_is_rejected(self):
        row = make_row(["user", "assistant"])
        row["messages"][-1]["content"] = "changed"
        with self.assertRaises(ValueError):
            rebuild_preview_rows(
                [row], lambda candidate: 1, validate_row=validate_fixture
            )

    def test_holds_when_current_user_and_target_do_not_fit(self):
        row = make_row(["assistant", "user", "assistant"])
        rebuilt, safe = rebuild_preview_rows(
            [row], lambda candidate: 99, max_length=10,
            validate_row=validate_fixture,
        )
        self.assertEqual(rebuilt, [])
        self.assertEqual(safe["status"], "R59_CONTEXT_WINDOW_HOLD")
        self.assertEqual(safe["rows_unfit"], 1)

    def test_source_hash_is_preserved_and_new_hash_recomputed(self):
        row = make_row(["assistant", "user", "assistant", "user", "assistant"])
        original_hash = row["metadata"]["input_messages_sha256"]

        def measure(candidate):
            return 20 if len(candidate["messages"][1:-2]) > 3 else 10

        rebuilt, _ = rebuild_preview_rows(
            [row], measure, max_length=10, validate_row=validate_fixture
        )
        metadata = rebuilt[0]["metadata"]
        self.assertEqual(metadata["source_input_messages_sha256"], original_hash)
        self.assertNotEqual(metadata["input_messages_sha256"], original_hash)

    def test_input_rows_are_not_mutated(self):
        row = make_row(["assistant", "user", "assistant"])
        original = copy.deepcopy(row)

        def measure(candidate):
            return 20 if len(candidate["messages"][1:-2]) > 3 else 10

        rebuild_preview_rows(
            [row], measure, max_length=10, validate_row=validate_fixture
        )
        self.assertEqual(row, original)

    def test_system_prompt_tampering_is_rejected(self):
        row = make_row(["user", "assistant"])
        row["messages"][0]["content"] = "changed"
        with self.assertRaises(ValueError):
            rebuild_preview_rows(
                [row], lambda candidate: 1, validate_row=validate_fixture
            )

    def test_output_path_is_checked_against_repository_not_process_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            root.mkdir()
            private = root / "private"
            private.mkdir()
            external = Path(directory) / "outside"
            external.mkdir()
            self.assertTrue(_is_inside_repository(private, root))
            self.assertFalse(_is_inside_repository(external, root))


if __name__ == "__main__":
    unittest.main()
