"""Synthetic ONLY R50 job preflight tests; never load R50 protected prompts."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

THIS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('r50_cpu', THIS / 'scripts/v03_r50_hf_cpu46_audit.py')
r50 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r50)

class SafeStage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.candidates = self.root / 'candidates.jsonl'
        self.candidates.write_text(''.join(json.dumps({'history':[],'user_input':f'synthetic-{i}'})+'\n' for i in range(46)),encoding='utf8')
        self.system = self.root / 'system.txt'
        self.system.write_text('synthetic, not private\n',encoding='utf8')
        self.preflight = self.root / 'original.py'
        self.preflight.write_text('print("FAKE PREFLIGHT")\n', encoding='utf8')
        self.worker = THIS/'scripts/v03_r50_hf_cpu46_worker.sh'
        self.audit = THIS/'scripts/v03_r50_hf_cpu46_audit.py'
        self.cpatch = patch.object(r50, 'CASE_SHA', r50.sha(self.candidates))
        self.spatch = patch.object(r50, 'SYSTEM_SHA', r50.sha(self.system))
        self.cpatch.start(); self.addCleanup(self.cpatch.stop)
        self.spatch.start(); self.addCleanup(self.spatch.stop)
        self.stagepath = self.root / 'stage'

    def do_stage(self):
        r50.stage(types.SimpleNamespace(candidates=str(self.candidates),system_file=str(self.system),preflight=str(self.preflight),audit_source=str(self.audit),worker_source=str(self.worker),stage=str(self.stagepath)))
        return self.stagepath

    def test_01_good_stage(self):
        root=self.do_stage()
        self.assertTrue(r50.check_stage(root))
        self.assertEqual(len(list(root.rglob('*'))),8) # code/private directories and 6 files plus root excluded

    def test_02_modified_private_input_fails(self):
        root=self.do_stage()
        (root/r50.CASES).write_text('tampered\n')
        with self.assertRaises(r50.GateError):r50.check_stage(root)

    def test_03_extra_unexpected_stage_file_fails(self):
        root=self.do_stage()
        (root/'private/secret.txt').write_text('not accepted')
        with self.assertRaises(r50.GateError):r50.check_stage(root)

    def test_04_corrupt_manifest_fails(self):
        root=self.do_stage()
        (root/'SHA256SUMS.txt').write_text('0\n')
        with self.assertRaises(r50.GateError):r50.check_stage(root)

    def test_05_stage_never_overwrite(self):
        self.do_stage()
        with self.assertRaises(r50.GateError):self.do_stage()

    def test_06_bad_candidate_count_fails_before_stage(self):
        self.candidates.write_text('{"user_input":"synthetic"}\n')
        r50.CASE_SHA=r50.sha(self.candidates)
        with self.assertRaises(r50.GateError):self.do_stage()

    def test_07_symlink_in_stage_fails(self):
        root=self.do_stage()
        target=root/r50.ORIGINAL_PREFLIGHT
        tmp=root/'private/hold'
        target.rename(tmp)
        target.symlink_to(tmp)
        with self.assertRaises(r50.GateError):r50.check_stage(root)

    def test_08_worker_syntax_and_submit_syntax(self):
        for name in ('v03_r50_hf_cpu46_worker.sh','v03_r50_hf_cpu46_submit.sh'):
            proc=subprocess.run(['bash','-n',str(THIS/'scripts'/name)],capture_output=True)
            self.assertEqual(proc.returncode,0)

    def test_09_good_worker_run_and_verify_with_mocked_tokenizer(self):
        root=self.do_stage()
        tok=self.root/'tok';tok.mkdir()
        (tok/'tokenizer.json').write_text('{}')
        (tok/'tokenizer_config.json').write_text('{}')
        fake_hub=types.SimpleNamespace(snapshot_download=lambda **kwargs:str(tok))
        fake_trans=types.SimpleNamespace(__version__='5.16.1')
        key='r50-cpu46-20261022T220000Z-123456'
        dest=self.root/'results'
        def fake_run(command, **kwargs):
            out=Path(command[command.index('--output')+1]);out.write_text('{"cases":46,"synthetic":true}')
            return types.SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch.dict(sys.modules,{'huggingface_hub':fake_hub,'transformers':fake_trans}),patch.object(r50.subprocess,'run',fake_run),patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'','JOB_ID':'TEST123'},clear=False):
            r50.cpu_run(types.SimpleNamespace(stage=str(root),run_key=key,output_dir=str(dest)))
        receipt=json.loads((dest/r50.RECEIPT).read_text())
        self.assertFalse(receipt['full_46_token_length_and_role_checks_independently_verified'])
        self.assertEqual(receipt['official_heldout_admitted'],0)
        out=self.root/'intake.json'
        r50.verify(types.SimpleNamespace(stage=str(root),receipt=str(dest/r50.RECEIPT),report=str(dest/r50.REPORT),private_log=str(dest/r50.PRIVATE_LOG),run_key=key,output=str(out)))
        self.assertTrue(out.is_file())
        self.assertEqual(json.loads(out.read_text())['status'],'R50_CPU46_OWNER_INTAKE_REPORT_HASHES_PASS__DRAFT_ONLY__NOT_FINAL_SEAL')
        with self.assertRaises(r50.GateError):
            r50.verify(types.SimpleNamespace(stage=str(root),receipt=str(dest/r50.RECEIPT),report=str(dest/r50.REPORT),private_log=str(dest/r50.PRIVATE_LOG),run_key=key,output=str(out)))
        (dest/r50.REPORT).write_text('{"tampered":true}')
        with self.assertRaises(r50.GateError):
            r50.verify(types.SimpleNamespace(stage=str(root),receipt=str(dest/r50.RECEIPT),report=str(dest/r50.REPORT),private_log=str(dest/r50.PRIVATE_LOG),run_key=key,output=str(self.root/'another.json')))

    def test_10_worker_forbids_gpu_env(self):
        self.do_stage()
        with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'0'},clear=False):
            with self.assertRaises(r50.GateError):
                r50.cpu_run(types.SimpleNamespace(stage=str(self.stagepath),run_key='r50-cpu46-20261022T220000Z-123456',output_dir=str(self.root/'out')))

    def test_11_invalid_run_key(self):
        self.do_stage()
        with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':''},clear=False):
            with self.assertRaises(r50.GateError):
                r50.cpu_run(types.SimpleNamespace(stage=str(self.stagepath),run_key='r50-r53-evil',output_dir=str(self.root/'out')))

    def test_13_submit_without_explicit_billing_consent_is_blocked(self):
        fake_bin=self.root/'bin';fake_bin.mkdir()
        fake_hf=fake_bin/'hf'
        fake_hf.write_text('#!/bin/sh\nif [ "$1" = auth ]; then exit 0; fi\nif [ "$1" = buckets ] && [ "$2" = info ]; then echo \'{"id":"greenkeedle/storyforge-r50-audit","private":true}\'; exit 0; fi\nexit 4\n')
        fake_hf.chmod(0o755)
        env={**os.environ,'PATH':str(fake_bin)+':'+os.environ['PATH']}
        env.pop('STORYFORGE_ALLOW_PAID_CPU',None)
        env.pop('STORYFORGE_R50_CPU46_DRAFT_ONLY',None)
        proc=subprocess.run(['bash',str(THIS/'scripts/v03_r50_hf_cpu46_submit.sh'),'submit','r50-cpu46-20261022T220000Z-123456'],env=env,capture_output=True,text=True)
        self.assertEqual(proc.returncode,3,proc.stdout+' '+proc.stderr)
        self.assertIn('R50_PAID_CPU_SCOPE_NOT_AUTHORIZED',proc.stderr)

    def test_14_private_bucket_requirement_blocks_sync(self):
        fake_bin=self.root/'bin';fake_bin.mkdir()
        fake_hf=fake_bin/'hf'
        fake_hf.write_text('#!/bin/sh\nif [ "$1" = auth ]; then exit 0; fi\nif [ "$1" = buckets ] && [ "$2" = info ]; then echo \'{"id":"greenkeedle/storyforge-r50-audit","private":false}\'; exit 0; fi\nexit 4\n')
        fake_hf.chmod(0o755)
        env={**os.environ,'PATH':str(fake_bin)+':'+os.environ['PATH']}
        proc=subprocess.run(['bash',str(THIS/'scripts/v03_r50_hf_cpu46_submit.sh'),'sync'],env=env,capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn('R50_BUCKET_NOT_CONFIRMED_PRIVATE__HOLD',proc.stderr)

    def test_12_verify_never_opens_private_text_in_stdout(self):
        self.assertNotIn('print(report)',self.audit.read_text())
        self.assertNotIn('print(run.stdout)',self.audit.read_text())

if __name__=='__main__': unittest.main()
