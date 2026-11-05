#!/usr/bin/env python3
"""Pure-stdlib contract tests for Transformers v5 BatchEncoding handling."""
from __future__ import annotations
import importlib.util
from collections import UserDict
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'v03_r50_cpu_tokenizer_preflight_46.py'
spec = importlib.util.spec_from_file_location('r50_cpu_preflight', MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FakeTokenizer:
    def __init__(self, ids=None):
        self.ids = [100, 200, 300] if ids is None else ids
        self.last_kwargs = None
    def apply_chat_template(self, messages, **kwargs):
        self.last_kwargs = kwargs
        return UserDict({'input_ids': self.ids, 'attention_mask': [1] * len(self.ids)})

class EncodingContractTests(unittest.TestCase):
    def test_transformers_v5_mapping(self):
        self.assertEqual(mod.strict_input_ids(UserDict({'input_ids': [1, 2, 3]}), 'T'), [1, 2, 3])

    def test_real_template_call_options_are_explicit(self):
        fake = FakeTokenizer()
        result = mod.tokenize_case_messages(fake, [{'role':'user','content':'synthetic'}], False, 'T')
        self.assertEqual(result, [100, 200, 300])
        self.assertEqual(fake.last_kwargs, {
            'tokenize': True,
            'return_dict': True,
            'add_generation_prompt': True,
            'enable_thinking': False,
            'truncation': False,
            'padding': False,
        })

    def test_raw_list_is_rejected(self):
        with self.assertRaises(TypeError):
            mod.strict_input_ids([1, 2], 'T')

    def test_missing_key_rejected(self):
        with self.assertRaises(TypeError):
            mod.strict_input_ids({'attention_mask': [1]}, 'T')

    def test_invalid_shapes_rejected(self):
        for ids in ([], [[1, 2]], ['1'], [True], [1.5], [-1], [2**32]):
            with self.subTest(ids=ids), self.assertRaises(TypeError):
                mod.strict_input_ids({'input_ids': ids}, 'T')

    def test_thinking_enabled_passed(self):
        fake = FakeTokenizer()
        self.assertEqual(mod.tokenize_case_messages(fake, [], True, 'T'), [100, 200, 300])
        self.assertIs(fake.last_kwargs['enable_thinking'], True)

if __name__ == '__main__':
    unittest.main()
