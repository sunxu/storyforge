"""Synthetic, never uses StoryForge protected inputs or real case IDs."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

S = Path(__file__).resolve().parents[1] / 'scripts/v03_r50_role12_owner_audit.py'
spec = importlib.util.spec_from_file_location('r50_role12', S)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SyntheticRoleAudit(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.files = {n: self.root/n for n in ['cases.jsonl', 'system.txt', 'report.json', 'intake.json']}
        self.cases = []
        self.rows = []
        for i in range(46):
            n = 8 if i < 42 else 7
            hist = [{'role': 'user' if j % 2 == 0 else 'assistant', 'content': f'synthetic-{i}-{j}'} for j in range(n)]
            hist[-1]['role'] = 'user' if i < 12 else 'assistant'
            case = {'case_id':f'SYNTH-{i:03}', 'history':hist, 'world_card': f'world-{i}',
                    'long_term_rules':['synthetic rule'], 'user_input':f'new-{i}'}
            self.cases.append(case)
            count = 700+i
            self.rows.append({'case_id':case['case_id'], 'history_count':n,
                              'consecutive_user':hist[-1]['role']=='user', 'input_tokens':count,
                              'input_plus_output_budget':count+1536, 'within_budget':True,
                              'input_id_sha256':'a'*64})
        self.report = {
            'schema':mod.REPORT_SCHEMA,'status':'PREFLIGHT_ONLY_NO_FINAL_SEAL',
            'pinned_model_revision':mod.REV,'candidate_original_sha256':'',
            'system_sha256':'','thinking_mode':'disabled', 'max_context':16384,
            'reserved_output_tokens':1536, 'no_model_generation':True,'no_gpu':True,
            'no_final_heldout_seal':True,
            'strategy':'PRESERVE_CONSECUTIVE_USER_AND_INJECT_WORLD_RULES_TO_SHARED_SYSTEM__DRAFT_ONLY',
            'cases':self.rows, 'case_count':46, 'overflow_count':0,
            'tokenizer_file_sha256':{'tokenizer.json':mod.TOKENIZER_JSON_SHA,'tokenizer_config.json':mod.TOKENIZER_CONFIG_SHA},
            'chat_template_sha256':mod.CHAT_TEMPLATE_SHA,
        }
        self.intake = {
            'schema':'storyforge-r50-hf-cpu46-local-intake-v2',
            'status':'R50_CPU46_OWNER_INTAKE_REPORT_HASHES_PASS__DRAFT_ONLY__NOT_FINAL_SEAL',
            'job_id_reported':mod.JOB_ID,'run_key':mod.RUN_KEY,
            'remote_private_report_sha256':'','source_count':46,
            'original_script_exit_0_and_json_generated':True,
            'official_heldout_admitted':0,'final_seal':False,
        }
        self.persist()

    def persist(self):
        self.files['cases.jsonl'].write_text(''.join(json.dumps(c, ensure_ascii=False)+'\n' for c in self.cases),encoding='utf8')
        self.files['system.txt'].write_text('SYSTEM SYNTHETIC',encoding='utf8')
        pins = {'cases':mod.sha(self.files['cases.jsonl'].read_bytes()),
                'system':mod.sha(self.files['system.txt'].read_bytes())}
        self.report['candidate_original_sha256'] = pins['cases']
        self.report['system_sha256'] = pins['system']
        self.files['report.json'].write_text(json.dumps(self.report,ensure_ascii=False),encoding='utf8')
        pins['report'] = mod.sha(self.files['report.json'].read_bytes())
        self.intake['remote_private_report_sha256'] = pins['report']
        self.files['intake.json'].write_text(json.dumps(self.intake),encoding='utf8')
        pins['intake'] = mod.sha(self.files['intake.json'].read_bytes())
        self.pins = pins

    def run_audit(self):
        return mod.audit(self.files['cases.jsonl'],self.files['system.txt'],
                         self.files['report.json'],self.files['intake.json'], pins=self.pins)

    def fail(self, code):
        self.persist()
        with self.assertRaisesRegex(mod.GateError,code):self.run_audit()

    def test_01_actual_draft_preserves_all_46_364_12(self):
        result=self.run_audit()
        self.assertEqual(result['frozen_candidate_count'],46)
        self.assertEqual(result['historical_message_count'],364)
        self.assertEqual(result['trailing_user_history_count'],12)
        self.assertEqual(result['trailing_user_real_tokenizer_encoded_count'],12)
        self.assertFalse(result['actual_four_arm_runtime_role_parity_verified'])
        self.assertEqual(result['official_heldout_admitted'],0)
        self.assertNotIn('SYNTH-',str(result))

    def test_02_exact_draft_builder(self):
        messages=mod.build_messages(self.cases[0],'SYSTEM SYNTHETIC')
        self.assertEqual(messages[1:-1],self.cases[0]['history'])
        self.assertEqual(messages[-2]['role'],'user')
        self.assertEqual(messages[-1]['role'],'user')
        self.assertEqual(messages[0]['role'],'system')
        self.assertIn('[STORY_WORLD_CARD]', messages[0]['content'])

    def test_03_frozen_candidates_mismatch(self):
        self.files['cases.jsonl'].write_text('tampered',encoding='utf8')
        with self.assertRaisesRegex(mod.GateError,'FROZEN_CASES_SHA_MISMATCH'):self.run_audit()

    def test_04_wrong_real_report_hash(self):
        self.files['report.json'].write_text('{}',encoding='utf8')
        with self.assertRaisesRegex(mod.GateError,'FROZEN_REPORT_SHA_MISMATCH'):self.run_audit()

    def test_05_disagree_trailing_user(self):
        self.rows[0]['consecutive_user']=False
        self.fail('TOKEN_REPORT_CONSECUTIVE_USER_DIFFERS')

    def test_06_too_few_trailing_user(self):
        self.cases[0]['history'][-1]['role']='assistant'
        self.rows[0]['consecutive_user']=False
        self.fail('FROZEN_TRAILING_USER_TOTAL_DIFFERS')

    def test_07_missing_token_id_proof(self):
        self.rows[0]['input_id_sha256']='bad'
        self.fail('TOKEN_REPORT_ENCODING_PROOF_MISSING')

    def test_08_wrong_history_count(self):
        self.rows[1]['history_count']+=1
        self.fail('TOKEN_REPORT_HISTORY_COUNT_DIFFERS')

    def test_09_invalid_history_role(self):
        self.cases[2]['history'][-1]['role']='tool'
        self.fail('INVALID_HISTORY_ROLES')

    def test_10_truncation_or_budget_overflow(self):
        self.rows[12]['input_tokens']=16000
        self.rows[12]['input_plus_output_budget']=17536
        self.rows[12]['within_budget']=False
        self.fail('DRAFT_TOKEN_BUDGET_OVERFLOW')

    def test_11_duplicate_private_report_id(self):
        self.rows[0]['case_id']=self.rows[1]['case_id']
        self.fail('REPORT_DUPLICATE_OR_INVALID_ID')

    def test_12_wrong_intake_model_job_id(self):
        self.intake['job_id_reported']='WRONG'
        self.fail('OWNER_INTAKE_IDENTITY_MISMATCH')

    def test_13_invalid_report_strategy(self):
        self.report['strategy']='MERGE_USER'
        self.fail('PRIVATE_REPORT_STRATEGY_MISMATCH')

    def test_14_missing_report_row(self):
        self.rows.pop()
        self.fail('PRIVATE_REPORT_ROW_COUNT_MISMATCH')

    def test_15_different_row_set(self):
        self.rows[0]['case_id']='OTHER'
        self.fail('REPORT_CASE_SET_DIFFERS_FROM_FROZEN_SOURCE')

    def test_16_no_arbitrary_text_leak_in_code(self):
        txt=S.read_text()
        self.assertNotIn('print(case)',txt)
        self.assertNotIn('print(messages)',txt)
        self.assertNotIn('print(report)',txt)
        self.assertNotIn('print(history)',txt)

    def test_17_refuse_git_output(self):
        git=self.root/'repo';git.mkdir();(git/'.git').mkdir()
        self.assertTrue(mod.in_git(git/'out.json'))

    def test_19_tokenizer_template_sha_drift(self):
        self.report['chat_template_sha256']='0'*64
        self.fail('QWEN_FROZEN_TOKENIZER_OR_TEMPLATE_HASH_DRIFT')

    def test_20_tokenizer_json_sha_drift(self):
        self.report['tokenizer_file_sha256']['tokenizer.json']='0'*64
        self.fail('QWEN_FROZEN_TOKENIZER_OR_TEMPLATE_HASH_DRIFT')

    def test_18_wrong_history_total(self):
        self.cases[17]['history'].append({'role':'assistant','content':'synthetic addition'})
        self.rows[17]['history_count']+=1
        self.rows[17]['consecutive_user']=False
        self.fail('FROZEN_HISTORY_TOTAL_DIFFERS')

if __name__=='__main__': unittest.main()
