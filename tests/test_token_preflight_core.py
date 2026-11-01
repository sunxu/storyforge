"""Pure-standard-library tests; no tokenizers, HF, API, GPU or private data."""
import unittest

from storyforge_dataset.token_preflight import (
    extract_input_ids, encode_chat, describe_token_lengths, digest_serialized_items,
)


class FakeTokenizer:
    def __init__(self):
        self.kwargs = None

    def apply_chat_template(self, messages, **kwargs):
        self.kwargs = kwargs
        return {"input_ids": [list(range(64))], "attention_mask": [[1] * 64]}


class SharedTokenPreflightTests(unittest.TestCase):
    def test_batchencoding_counts_real_input_ids(self):
        encoded = {"input_ids": [list(range(64))], "attention_mask": [[1] * 64]}
        self.assertEqual(len(encoded), 2)
        self.assertEqual(len(extract_input_ids(encoded, prompt_chars=500)), 64)
        self.assertEqual(extract_input_ids(list(range(64))), list(range(64)))
        for bad in (
            {"input_ids": [[1, 2]], "attention_mask": [[1, 1]]},
            {"attention_mask": [[1, 1]]},
            {"input_ids": []},
            {"input_ids": [[1, -1] * 20]},
            {"input_ids": [[True] * 64]},
            {"input_ids": [[1] * 64, [2] * 64]},
        ):
            with self.assertRaises(ValueError):
                extract_input_ids(bad, prompt_chars=500)

    def test_real_chat_template_flags_and_output(self):
        tok = FakeTokenizer()
        messages = [{"role": "user", "content": "hello " * 25}]
        self.assertEqual(len(encode_chat(tok, messages, disable_thinking=True)), 64)
        self.assertIs(tok.kwargs["enable_thinking"], False)
        self.assertIs(tok.kwargs["add_generation_prompt"], True)
        self.assertEqual(len(encode_chat(tok, messages, disable_thinking=False)), 64)
        self.assertNotIn("enable_thinking", tok.kwargs)

    def test_fallback_only_for_unsupported_thinking_flag(self):
        class LegacyTokenizer:
            def apply_chat_template(self, messages, tokenize, add_generation_prompt):
                return list(range(64))
        self.assertEqual(len(encode_chat(LegacyTokenizer(),
                                         [{"role": "user", "content": "x" * 200}],
                                         disable_thinking=True)), 64)
        class BrokenTokenizer:
            def apply_chat_template(self, messages, **kwargs):
                raise TypeError("unrelated template failure")
        with self.assertRaises(TypeError):
            encode_chat(BrokenTokenizer(), [{"role": "user", "content": "x" * 200}],
                        disable_thinking=True)

    def test_budget_stats_pilot_and_hold(self):
        lengths = list(range(100, 113))
        s = describe_token_lengths(lengths, max_model_len=130,
                                   reserved_output_tokens=20, pilot_count=2)
        self.assertEqual(s["cases_checked"], 13)
        self.assertEqual(s["prompt_tokens_p95"], 112)
        self.assertEqual(s["prompt_tokens_median"], 106)
        self.assertEqual(s["pilot_prompt_tokens_max"], 101)
        self.assertEqual(s["remaining_prompt_tokens_max"], 112)
        self.assertEqual(s["over_budget_count"], 2)
        self.assertEqual(s["max_total_tokens"], 132)
        with self.assertRaises(ValueError):
            describe_token_lengths([True, 64], max_model_len=300,
                                   reserved_output_tokens=10)

    def test_prompt_identity_is_order_and_content_sensitive(self):
        a = digest_serialized_items([{"role": "user", "content": "one"},
                                     {"role": "user", "content": "two"}])
        b = digest_serialized_items([{"role": "user", "content": "two"},
                                     {"role": "user", "content": "one"}])
        c = digest_serialized_items([{"role": "user", "content": "ONE"},
                                     {"role": "user", "content": "two"}])
        self.assertEqual(a, digest_serialized_items([{"content": "one", "role": "user"},
                                                       {"content": "two", "role": "user"}]))
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)


if __name__ == "__main__":
    unittest.main()
