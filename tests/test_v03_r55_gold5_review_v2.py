"""R55 v2 no-original, synthetic-only tests for three distinct blind tasks."""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import patch

# V1 transitive imports stubbed for synthetic only; production imports Git source.
for name, attributes in {
    'v02_r47_eval_validate': {
        'validate_prompts': lambda *_: None,
        'validate_responses': lambda *_: None,
    },
    'v02_r48_four_arm_build': {
        'check_r47': lambda *_: None,
        'read_gold': lambda *_: None,
        'sha': lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(),
        'CANONICAL_TEST_SHA256': 'synthetic',
    },
}.items():
    sys.modules.setdefault(name, types.SimpleNamespace(**attributes))
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('r55goldv2synthetic', SCRIPTS/'v03_r55_gold5_review_v2.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
legacy=mod.legacy


def fake_data(n=20):
    prompts = [{'messages': [{'role': 'system', 'content': 'test background'},
                            {'role': 'user', 'content': f'question {i}'}]} for i in range(n)]
    entries = [{'sample_id': f'case-{i:03d}', 'prompt_sha256': 'f' * 64} for i in range(n)]
    answers = {arm: [f'synthetic {arm} answer {i}' for i in range(n)] for arm in mod.ALL_ARMS}
    return prompts, entries, answers


class TestBlindPackV2(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dest = self.root / 'owner-pack-v2'

    def make(self):
        prompts, entries, answers = fake_data()
        return mod.make_review_v2(prompts, entries, answers, {}, self.dest)

    def key(self):
        return json.loads((self.dest/'coordinator/private/R55_GOLD5_COORDINATOR_KEY_V2_PRIVATE.json').read_text())

    def rows(self, label, n=1):
        p = self.dest/'reviewers'/f'R55_GOLD5_{label}_V2_Reviewer_{n:02d}_PRIVATE.csv'
        with p.open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))

    def test_nine_csv_sheets(self):
        self.make();self.assertEqual(len(list((self.dest/'reviewers').glob('*.csv'))), 9)

    def test_three_report_tasks(self):
        receipt=self.make()
        self.assertEqual([receipt[x] for x in ('pairwise_task_count','four_model_task_count','five_way_task_count')],[20,20,20])

    def test_no_model_only_column_in_five_sheet(self):
        self.make(); row=self.rows('FIVE')[0]
        self.assertNotIn('四模型最佳(请填写对应匿名字母或TIE)',row)
        self.assertEqual(set(x for x in row if x.startswith('回复')),set('回复'+x for x in 'ABCDE'))

    def test_four_sheet_excludes_gold(self):
        self.make()
        for m in self.key()['identity_maps']:
            self.assertEqual(set(m['four_model_mapping'].values()),set(mod.MODEL_ARMS))
            self.assertNotIn('gold',m['four_model_mapping'].values())

    def test_pair_sheet_only_v02_v03(self):
        self.make()
        for m in self.key()['identity_maps']:
            self.assertEqual(set(m['pairwise_mapping'].values()),{'v02','v03'})

    def test_five_includes_gold_anon(self):
        self.make()
        for m in self.key()['identity_maps']:
            self.assertEqual(set(m['five_way_mapping'].values()),set(mod.ALL_ARMS))

    def test_pair_and_four_and_five_each_within_one_key(self):
        self.make()
        self.assertEqual(len(self.key()['identity_maps']),20)
        self.assertEqual(set(self.key()['identity_maps'][0]),{'sample_id','prompt_sha256','source_reply_sha256','pairwise_mapping','four_model_mapping','five_way_mapping'})

    def test_four_column_naming(self):
        self.make(); r=self.rows('FOUR')[0]
        self.assertIn('整体最佳(A/B/C/D/TIE)',r)
        self.assertNotIn('回复E',r)

    def test_five_preference_blank(self):
        self.make();r=self.rows('FIVE')[0]
        self.assertEqual(r['整体最佳(A/B/C/D/E/TIE)'],'')

    def test_pair_preference_blank(self):
        self.make();r=self.rows('PAIR')[0]
        self.assertEqual(r['偏好(LEFT/RIGHT/TIE)'],'')

    def test_six_dimensional_scores(self):
        self.make();r=self.rows('FIVE')[0]
        self.assertEqual(sum(x.startswith(tuple(mod.DIMS)) for x in r),30)
        self.assertTrue(all(r[f'{dim}·A']=='' for dim in mod.DIMS))

    def test_20_case_rows(self):
        self.make()
        for typ in ('PAIR','FOUR','FIVE'): self.assertEqual(len(self.rows(typ)),20)

    def test_three_identical_pristine_per_task(self):
        self.make(); a=self.dest/'reviewers'
        for t in ('PAIR','FOUR','FIVE'):
            p=a/f'R55_GOLD5_{t}_V2_Reviewer_01_PRIVATE.csv'
            q=a/f'R55_GOLD5_{t}_V2_Reviewer_03_PRIVATE.csv'
            self.assertEqual(p.read_bytes(),q.read_bytes())

    def test_safe_receipt_no_text(self):
        self.make(); text=(self.dest/'R55_GOLD5_V2_PREP_SAFE_COUNT_ONLY.json').read_text()
        self.assertNotIn('synthetic ',text);self.assertNotIn('question 0',text);self.assertNotIn('case-000',text)

    def test_private_key_only_in_coordinator(self):
        self.make(); self.assertFalse(list((self.dest/'reviewers').glob('*KEY*')))

    def test_permissions(self):
        self.make()
        if os.name=='posix':
            self.assertEqual((self.dest/'coordinator/private/R55_GOLD5_COORDINATOR_KEY_V2_PRIVATE.json').stat().st_mode&0o777,0o600)
            self.assertEqual(self.dest.stat().st_mode&0o777,0o700)

    def test_no_overwrite(self):
        self.make(); a,b,c=fake_data()
        with self.assertRaisesRegex(legacy.Hold,'PRIVATE_OUTPUT_ALREADY_EXISTS'):
            mod.make_review_v2(a,b,c,{},self.dest)

    def test_reject_git_path(self):
        (self.root/'.git').mkdir();a,b,c=fake_data()
        with self.assertRaisesRegex(legacy.Hold,'PRIVATE_OUTPUT_WITHIN_GIT_REPO'):
            mod.make_review_v2(a,b,c,{},self.dest)

    def test_reject_missing_gold(self):
        a,b,c=fake_data();del c['gold']
        with self.assertRaisesRegex(legacy.Hold,'WRONG_FIVE_ARM_SET'):
            mod.make_review_v2(a,b,c,{},self.dest)

    def test_reject_wrong_case_count(self):
        a,b,c=fake_data(19)
        with self.assertRaisesRegex(legacy.Hold,'WRONG_SOURCE_LENGTH'):
            mod.make_review_v2(a,b,c,{},self.dest)

    def test_reject_blank_reply(self):
        a,b,c=fake_data();c['gold'][2]=''
        with self.assertRaisesRegex(legacy.Hold,'EMPTY_RESPONSE'):
            mod.make_review_v2(a,b,c,{},self.dest)

    def test_consistent_response_between_key_and_csv(self):
        self.make();identity=self.key()['identity_maps'][0]
        for t,mkey in [('PAIR','pairwise_mapping'),('FOUR','four_model_mapping'),('FIVE','five_way_mapping')]:
            row=self.rows(t)[0]
            for letter,arm in identity[mkey].items():
                self.assertEqual(hashlib.sha256(row[f'回复{letter}'].encode()).hexdigest(), identity['source_reply_sha256'][arm])

    def test_receipt_private_csv_hashes(self):
        receipt=self.make()
        self.assertEqual(len(receipt['reviewer_private_csv_sha256']),9)
        for filename,digest in receipt['reviewer_private_csv_sha256'].items():
            self.assertEqual(hashlib.sha256((self.dest/'reviewers'/filename).read_bytes()).hexdigest(),digest)

    def test_preserves_prompt_context(self):
        self.make();r=self.rows('FOUR')[0]
        self.assertEqual(r['当前用户输入'],'question 0')
        self.assertEqual(r['故事背景与系统规则'],'【system】\ntest background')

    def test_no_gpu_and_no_final_seal(self):
        r=self.make()
        for key in ('gpu_inference','training','model_promoted','new_heldout','r50_accessed','final_seal'):
            self.assertFalse(r[key])

if __name__=='__main__':unittest.main()
