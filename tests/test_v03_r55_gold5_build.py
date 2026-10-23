"""Synthetic only; zero private R55/R50 data read, no model calls."""
from __future__ import annotations
import csv
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import types
import unittest
from unittest.mock import patch

# In isolation, inject placeholders for imported canonical validators; production
# invokes the real Git-versioned modules, and tests patch the module's names.
for name, attributes in {
    'v02_r47_eval_validate': {'validate_prompts':lambda *a:None,'validate_responses':lambda *a:None},
    'v02_r48_four_arm_build': {'check_r47':lambda *a:None,'read_gold':lambda *a:None,
                              'sha':lambda x:__import__('hashlib').sha256(Path(x).read_bytes()).hexdigest(),
                              'CANONICAL_TEST_SHA256':'synthetic'},
}.items():
    sys.modules.setdefault(name,types.SimpleNamespace(**attributes))
SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'v03_r55_gold5_build.py'
spec=importlib.util.spec_from_file_location('r55gold5synthetic',SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fake_data(n=20):
    p=[{'messages':[{'role':'system','content':'demo'},
                    {'role':'user','content':f'question {i}'}]} for i in range(n)]
    meta=[{'sample_id':f'synthetic-{i:03d}','prompt_sha256':mod.hash_text(f'prompt {i}')} for i in range(n)]
    arms={name:[f'non-private {name} answer {i}' for i in range(n)] for name in mod.ALL_ARMS}
    return p,meta,arms

class TestSafePackage(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def build(self):
        p,e,txt=fake_data()
        return mod.make_package(p,e,txt,{},self.root/'private-frozen')
    def test_five_way_counts(self):
        o=self.build();self.assertEqual((o['case_count'],o['five_way_response_count']),(20,100))
    def test_gold_non_model_reference(self):
        o=self.build();self.assertTrue(o['original_gold_is_non_model_reference'])
    def test_zero_inference(self):
        o=self.build();self.assertFalse(o['gpu_inference']);self.assertFalse(o['training'])
    def test_zero_r50(self):
        o=self.build();self.assertFalse(o['r50_accessed']);self.assertFalse(o['new_heldout'])
    def test_six_csv_files(self):
        self.build();self.assertEqual(len(list((self.root/'private-frozen/reviewers').glob('*.csv'))),6)
    def test_blind_gold_randomized_label(self):
        self.build();d=json.loads((self.root/'private-frozen/coordinator/private/R55_GOLD5_COORDINATOR_KEY_PRIVATE.json').read_text())
        self.assertEqual(len(d['identity_maps']),20)
        for row in d['identity_maps']:
            self.assertEqual(set(row['five_way_mapping'].values()),set(mod.ALL_ARMS))
    def test_pairwise_only_two_models(self):
        self.build();d=json.loads((self.root/'private-frozen/coordinator/private/R55_GOLD5_COORDINATOR_KEY_PRIVATE.json').read_text())
        for row in d['identity_maps']:
            self.assertEqual(set(row['pairwise_mapping'].values()),{'v02','v03'})
    def test_safe_receipt_no_source_text(self):
        self.build();t=(self.root/'private-frozen/R55_GOLD5_PREP_SAFE_COUNT_ONLY.json').read_text()
        self.assertNotIn('non-private',t);self.assertNotIn('question',t);self.assertNotIn('synthetic-000',t)
    def test_reviewer_answers_identical(self):
        self.build();p=self.root/'private-frozen/reviewers'
        self.assertEqual((p/'R55_GOLD5_FIVE_Reviewer_01_PRIVATE.csv').read_bytes(),
                         (p/'R55_GOLD5_FIVE_Reviewer_03_PRIVATE.csv').read_bytes())
    def test_ratings_not_prepopulated(self):
        self.build()
        with (self.root/'private-frozen/reviewers/R55_GOLD5_FIVE_Reviewer_01_PRIVATE.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),20)
        self.assertEqual(rows[0]['剧情连续性·A'],'')
        self.assertTrue(rows[0]['回复A'])
    def test_repeated_output_disallowed(self):
        self.build()
        p,e,txt=fake_data()
        with self.assertRaisesRegex(mod.Hold,'PRIVATE_OUTPUT_ALREADY_EXISTS'):
            mod.make_package(p,e,txt,{},self.root/'private-frozen')
    def test_reject_git_tree(self):
        (self.root/'.git').mkdir()
        p,e,txt=fake_data()
        with self.assertRaisesRegex(mod.Hold,'PRIVATE_OUTPUT_WITHIN_GIT_REPO'):
            mod.make_package(p,e,txt,{},self.root/'somewhere'/'out')
    def test_wrong_20_cases(self):
        p,e,txt=fake_data(19)
        with self.assertRaisesRegex(mod.Hold,'WRONG_SOURCE_LENGTH'):
            mod.make_package(p,e,txt,{},self.root/'out')
    def test_missing_gold_arm(self):
        p,e,txt=fake_data();txt.pop('gold')
        with self.assertRaisesRegex(mod.Hold,'WRONG_FIVE_ARM_SET'):
            mod.make_package(p,e,txt,{},self.root/'out')
    def test_safe_hash_in_generated_receipt(self):
        o=self.build();self.assertEqual(len(o['private_five_key_sha256']),64)
    def test_preflight_sha_pins_fail_closed(self):
        import argparse
        args=argparse.Namespace(**{k:self.root/f'{k}.json' for k in (
            'compiled_test','prompts','manifest','r47_report','base','v01','v02','v03','r55_report')})
        for x in vars(args).values(): x.write_text('synthetic',encoding='utf-8')
        with self.assertRaisesRegex(mod.Hold,'CANONICAL_GOLD_TEST_SHA_MISMATCH'):
            mod.load_exact_sources(args)
    def test_preflight_source_and_model_alignment(self):
        import argparse
        args=argparse.Namespace(**{k:self.root/f'{k}.json' for k in (
            'compiled_test','prompts','manifest','r47_report','base','v01','v02','v03','r55_report')})
        for x in vars(args).values(): x.write_text('synthetic',encoding='utf-8')
        p,e,txt=fake_data()
        from contextlib import ExitStack
        with ExitStack() as st:
            st.enter_context(patch.object(mod,'CANONICAL_TEST_SHA256',mod.sha(args.compiled_test)))
            st.enter_context(patch.object(mod,'EXPECTED_PROMPTS_BLOB',mod.git_blob_sha(args.prompts.read_bytes())))
            st.enter_context(patch.object(mod,'EXPECTED_MANIFEST_BLOB',mod.git_blob_sha(args.manifest.read_bytes())))
            st.enter_context(patch.object(mod,'R55_OUTPUT_SHA256',mod.sha(args.v03)))
            st.enter_context(patch.object(mod,'R55_REPORT_SHA256',mod.sha(args.r55_report)))
            st.enter_context(patch.object(mod,'validate_prompts',return_value=(p,e)))
            st.enter_context(patch.object(mod,'read_gold',return_value=txt['gold']))
            st.enter_context(patch.object(mod,'check_r47',return_value={k:txt[k] for k in ('base','v01','v02')}))
            st.enter_context(patch.object(mod,'validate_responses',return_value=txt['v03']))
            rp, re, rt, input_paths=mod.load_exact_sources(args)
            self.assertEqual(len(rp),20);self.assertEqual(set(rt),set(mod.ALL_ARMS))
            args.v03.write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(mod.Hold,'FROZEN_R55_V03_RESPONSES_SHA_MISMATCH'):
                mod.load_exact_sources(args)
    def test_refuse_symlinks(self):
        p=self.root/'real';p.write_text('text')
        sym=self.root/'alias';sym.symlink_to(p)
        with self.assertRaisesRegex(mod.Hold,'MISSING_OR_SYMLINK'):
            mod.ensure_regular(sym,'TEST')
    def test_five_way_exact_source_in_csv(self):
        self.build();p=self.root/'private-frozen/reviewers/R55_GOLD5_FIVE_Reviewer_02_PRIVATE.csv'
        with p.open(encoding='utf-8-sig',newline='') as f: row=next(csv.DictReader(f))
        self.assertEqual(row['当前用户输入'],'question 0')
        self.assertEqual(row['故事背景与系统规则'],'【system】\ndemo')
    def test_pairwise_rating_columns(self):
        self.build();p=self.root/'private-frozen/reviewers/R55_GOLD5_PAIR_Reviewer_01_PRIVATE.csv'
        with p.open(encoding='utf-8-sig',newline='') as f: row=next(csv.DictReader(f))
        self.assertIn('剧情连续性·LEFT',row);self.assertIn('玩家自主权·RIGHT',row)
        self.assertEqual(row['偏好(LEFT/RIGHT/TIE)'],'')

if __name__=='__main__':unittest.main()
