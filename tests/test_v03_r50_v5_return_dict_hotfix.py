import ast
import hashlib
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1]/'scripts/v03_r50_v5_return_dict_hotfix.py'
spec=importlib.util.spec_from_file_location('fix',P)
fix=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

class Tests(unittest.TestCase):
    def apply(self,s):
        b=s.encode('utf8')
        patched,rec=fix.patch_bytes(b,required_sha=hashlib.sha256(b).hexdigest())
        return patched.decode('utf8'),rec
    def test_basic_v5_change(self):
        t='''from transformers import AutoTokenizer\ndef main(t, messages):\n    ids=t.apply_chat_template(messages, tokenize=True)\n    if not isinstance(ids,list): raise TypeError('invalid encoded ids for CASE')\n'''
        p,r=self.apply(t)
        self.assertIn('tokenize=True, return_dict=False)',p)
        self.assertEqual(r['private_cases_opened'],0)
    def test_multiline_trailing_comma(self):
        t='''def f(t,m):\n  ids=t.apply_chat_template(\n      m,\n      tokenize=True,\n  )\n  if not isinstance(ids,list): raise TypeError('invalid encoded ids')\n'''
        p,_=self.apply(t)
        self.assertIn('return_dict=False',p)
        ast.parse(p)
    def test_trailing_comma_inline(self):
        t="ids=t.apply_chat_template(m, tokenize=True,)\nraise TypeError('invalid encoded ids')\n"
        p,_=self.apply(t)
        self.assertIn('tokenize=True, return_dict=False)',p)
    def test_utf8_byte_offsets(self):
        t="msg='中文🔍'; ids=t.apply_chat_template(m, tokenize=True)\nraise TypeError('invalid encoded ids')\n"
        p,_=self.apply(t)
        self.assertIn('tokenize=True, return_dict=False)',p)
    def test_sha_fail(self):
        b=b"raise TypeError('invalid encoded ids')"
        with self.assertRaisesRegex(fix.Blocked,'SOURCE_SHA256_NOT_FROZEN'):fix.patch_bytes(b)
    def test_multiple_calls_block(self):
        s="t.apply_chat_template(m);t.apply_chat_template(m)\nraise TypeError('invalid encoded ids')"
        with self.assertRaisesRegex(fix.Blocked,'NOT_EXACTLY_ONE'):self.apply(s)
    def test_already_explicit(self):
        s="t.apply_chat_template(m, return_dict=False)\nraise TypeError('invalid encoded ids')"
        with self.assertRaisesRegex(fix.Blocked,'RETURN_DICT_ALREADY'):self.apply(s)
    def test_dynamic_kwargs_block(self):
        s="t.apply_chat_template(m, **kw)\nraise TypeError('invalid encoded ids')"
        with self.assertRaisesRegex(fix.Blocked,'DYNAMIC_KWARGS'):self.apply(s)
    def test_return_tensors_block(self):
        s="t.apply_chat_template(m, return_tensors='pt')\nraise TypeError('invalid encoded ids')"
        with self.assertRaisesRegex(fix.Blocked,'RETURN_TENSORS'):self.apply(s)
    def test_no_guard_block(self):
        s="t.apply_chat_template(m, tokenize=True)"
        with self.assertRaisesRegex(fix.Blocked,'EXPECTED_ENCODED_IDS_GUARD_NOT_PRESENT'):self.apply(s)
    def test_dynamic_tokenize_block(self):
        s="t.apply_chat_template(m, tokenize=arg)\nraise TypeError('invalid encoded ids')"
        with self.assertRaisesRegex(fix.Blocked,'TOKENIZE_NOT_EXPLICIT_TRUE'):self.apply(s)

if __name__=='__main__':unittest.main()
