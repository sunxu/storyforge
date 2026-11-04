"""Synthetic-only tests for R59 HF CPU review token audit."""
import json
import tempfile
import unittest
from pathlib import Path

from r59_semantic_prompt_token_cpu import audit, load_prompts, sha, write_safe


class FakeTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        assert kwargs["tokenize"] is True
        assert kwargs["add_generation_prompt"] is True
        assert kwargs["enable_thinking"] is False
        return list(range(120))


def fixture():
    fingerprint = "b" * 64
    rows = [
        {"schema": "storyforge-r59-semantic-review-prompt-private-v1",
         "pilot_index": i, "prompt_fingerprint": fingerprint,
         "review_decision": None, "gpu_started": False,
         "quality_v1_admitted": False,
         "history_coverage": {"scope": "FULL_STAGED_SUFFIX_ONLY"},
         "messages": [{"role": "system", "content": "synthetic system"},
                      {"role": "user", "content": "synthetic user prompt"}]}
        for i in range(8)
    ]
    raw = b"".join(json.dumps(r, ensure_ascii=False).encode() + b"\n" for r in rows)
    return raw, fingerprint


class Tests(unittest.TestCase):
    def test_frozen_prompts_token_pass(self):
        raw, fingerprint = fixture()
        result = audit(raw, expected_sha=sha(raw), expected_fingerprint=fingerprint,
                       model="synthetic/Qwen", revision="a" * 40,
                       max_model_len=4096, reserved_output_tokens=2400,
                       tokenizer=FakeTokenizer(), transformers_version="test")
        self.assertEqual(result["cases_checked"], 8)
        self.assertEqual(result["prompt_tokens_max"], 120)
        self.assertEqual(result["over_budget_count"], 0)
        self.assertFalse(result["gpu_started"])

    def test_budget_hold(self):
        raw, fingerprint = fixture()
        result = audit(raw, expected_sha=sha(raw), expected_fingerprint=fingerprint,
                       model="synthetic/Qwen", revision="a" * 40,
                       max_model_len=4096, reserved_output_tokens=4096,
                       tokenizer=FakeTokenizer(), transformers_version="test")
        self.assertEqual(result["over_budget_count"], 8)

    def test_sha_and_fingerprint_fail_closed(self):
        raw, fingerprint = fixture()
        with self.assertRaises(ValueError):
            load_prompts(raw, "c" * 64, fingerprint)
        with self.assertRaises(ValueError):
            load_prompts(raw, sha(raw), "d" * 64)

    def test_case_count_and_order_fail_closed(self):
        raw, fp = fixture()
        with self.assertRaises(ValueError):
            load_prompts(b"\n".join(raw.splitlines()[:-1]) + b"\n", sha(raw), fp)
        rows = [json.loads(x) for x in raw.splitlines()]
        rows[1]["pilot_index"] = 0
        bad = b"".join(json.dumps(r).encode() + b"\n" for r in rows)
        with self.assertRaises(ValueError):
            load_prompts(bad, sha(bad), fp)

    def test_private_safe_create_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            folder.chmod(0o700)
            path = folder / "safe.json"
            write_safe(path, {"status": "synthetic"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_safe(path, {"status": "other"})


if __name__ == "__main__":
    unittest.main()