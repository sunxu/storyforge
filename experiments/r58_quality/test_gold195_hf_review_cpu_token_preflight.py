import json
import unittest
from gold195_hf_review_cpu_token_preflight import (
    DEFAULT_MODEL, DEFAULT_REVISION, count_lengths, validate_input,
)
from gold195_hf_review_batch import input_record
from gold195_assistant_first_full132 import build
from test_gold195_assistant_first_semantic_pilot import example


class DummyTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        # Synthetic only: NEVER makes tokenizer/model/network calls.
        return [7] * (100 + len(messages[0]["content"]) // 50)


class CPUPreflightTests(unittest.TestCase):
    def setUp(self):
        self.source = [input_record(x) for x in
                       build([example(i) for i in range(132)])[1]]

    def test_exact_132_contract_and_safe_counts(self):
        rows = validate_input(self.source)
        result = count_lengths(rows, DummyTokenizer(), 8192, 1200)
        self.assertEqual(result["cases_total"], 132)
        self.assertEqual(result["fits_context"] + result["token_hold"], 132)
        self.assertTrue(result["prompt_tokens_max"] >= result["prompt_tokens_min"])
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertEqual(len(DEFAULT_REVISION), 40)
        self.assertEqual(DEFAULT_MODEL, "Qwen/Qwen3-32B")

    def test_overlong_is_explicit_hold(self):
        result = count_lengths(self.source, DummyTokenizer(), 1024, 900)
        self.assertEqual(result["token_hold"], 132)

    def test_no_omitted_or_reordered_private_rows(self):
        with self.assertRaises(ValueError):
            validate_input(self.source[:-1])
        rows = list(self.source)
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaises(ValueError):
            validate_input(rows)


if __name__ == "__main__":
    unittest.main()
