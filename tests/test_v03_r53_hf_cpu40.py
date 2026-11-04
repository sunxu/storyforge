"""No-network, no paid CPU tests for R53 HF 40-row audit and launcher."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = pathlib.Path(os.environ.get('R53_TEST_PRIVATE_STAGE', '/mnt/data/R53_HF_CPU40_20261021/input/private_stage'))
sys.path.insert(0, str(SCRIPTS))
import v03_r53_hf_cpu40_audit as a

class R53Workflow(unittest.TestCase):
    @unittest.skipUnless(DATA.is_dir(), "R53 frozen private stage unavailable; set R53_TEST_PRIVATE_STAGE for owner-local integrity tests")
    def test_true_frozen_stage(self):
        rows, b = a.preflight(DATA)
        self.assertEqual({k:len(x) for k,x in rows.items()},a.COUNTS)
        self.assertEqual({k:a.sha(x) for k,x in b.items()},a.COMPILED_SHA)

    @unittest.skipUnless(DATA.is_dir(), "R53 frozen private stage unavailable; set R53_TEST_PRIVATE_STAGE for owner-local integrity tests")
    def test_mutated_input_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t)
            for src in DATA.glob('*'): shutil.copy2(src,p/src.name)
            f=p/'STAGED_TRAIN_NOT_ADMITTED.jsonl'
            f.write_bytes(f.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'SHA mismatch'):
                a.preflight(p)

    @unittest.skipUnless(DATA.is_dir(), "R53 frozen private stage unavailable; set R53_TEST_PRIVATE_STAGE for owner-local integrity tests")
    def test_mutated_manifest_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t)
            for src in DATA.glob('*'): shutil.copy2(src,p/src.name)
            f=p/'STAGED_31_9_SOURCE_HASH_MANIFEST_PRIVATE.json'
            f.write_bytes(f.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'manifest SHA mismatch'):
                a.preflight(p)

    @unittest.skipUnless(DATA.is_dir(), "R53 frozen private stage unavailable; set R53_TEST_PRIVATE_STAGE for owner-local integrity tests")
    def test_final_target_marker_baked_into_compiled_sha(self):
        rows,_=a.preflight(DATA)
        sample=rows['train'][0]
        self.assertEqual(sample['messages'][-1]['loss'],True)
        self.assertEqual(sample['messages'][-2]['loss'],False)
        changed=json.loads(json.dumps(sample))
        changed['messages'][-1]['content']+='modification'
        self.assertNotEqual(a.canonical_compiled(changed),a.canonical_compiled(sample))

    def test_collator_good(self):
        self.assertEqual(a.check_collator({'input_ids':[1,2,3], 'labels':[-100,2,3]},
                                          {'input_ids':[[1,2,3,0]],'labels':[[-100,2,3,-100]]})['padding_tokens'],1)

    def test_collator_left_pad_good(self):
        self.assertEqual(a.check_collator({'input_ids':[1,2], 'labels':[-100,2]},
                                          {'input_ids':[[0,0,1,2]],'labels':[[-100,-100,-100,2]]})['padding_tokens'],2)

    def test_collator_leaked_pad_bad(self):
        with self.assertRaises(ValueError):
            a.check_collator({'input_ids':[1,2], 'labels':[-100,2]},
                             {'input_ids':[[1,2,0]],'labels':[[-100,2,0]]})

    def test_collator_leaked_history_bad(self):
        with self.assertRaises(ValueError):
            a.check_collator({'input_ids':[1,2], 'labels':[-100,2]},
                             {'input_ids':[[1,2]],'labels':[[1,2]]})

    def test_list_handling(self):
        self.assertEqual(a.one_int_list({'input_ids':[[12,13]]}),[12,13])
        with self.assertRaises(ValueError):a.one_int_list([[1,2],[3,4]])

    def test_unavailable_swift_blocks_no_fake_pass(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t)/'report'
            cmd=[sys.executable,str(SCRIPTS/'v03_r53_hf_cpu40_audit.py'),'audit',
                 '--stage',str(DATA),'--output-dir',str(p)]
            r=subprocess.run(cmd,capture_output=True,text=True)
            # Whether swift is installed or not, no actual runtime should PASS in offline test env.
            self.assertNotEqual(r.returncode,0)
            report=p/'R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json'
            if report.exists():self.assertEqual(json.loads(report.read_text())['status'],'BLOCKED')

    def test_submit_refuses_unapproved_cpu_before_charge(self):
        # Use fake hf CLI that records requests but never submits.
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);stub=p/'hf'; record=p/'calls'
            stub.write_text('#!/bin/sh\necho "$@" >> "$R53_TEST_CALL_LOG"\nexit 0\n')
            stub.chmod(0o755)
            env={**os.environ,'PATH':str(p)+os.pathsep+os.environ['PATH'],
                 'R53_TEST_CALL_LOG':str(record)}
            env.pop('STORYFORGE_ALLOW_PAID_CPU',None)
            env.pop('STORYFORGE_R53_CPU40_NO_TRAIN_ONLY',None)
            r=subprocess.run(['bash',str(SCRIPTS/'v03_r53_hf_cpu40_submit.sh'),'submit',
                              'r53-cpu40-20261021T150000Z-123456'],env=env,capture_output=True)
            self.assertEqual(r.returncode,3)
            self.assertFalse(record.exists())

    @unittest.skipUnless(DATA.is_dir(), "R53 frozen private stage unavailable; set R53_TEST_PRIVATE_STAGE for owner-local integrity tests")
    def test_verifier_rejects_fake_pass_missing_log(self):
        import v03_r53_hf_cpu40_verify as v
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);d=p/'fake.json';d.write_text('{}')
            with self.assertRaises((KeyError,ValueError)):
                v.verify(DATA,d,p/'missing.log',p/'out.json')
            self.assertFalse((p/'out.json').exists())

if __name__=='__main__':unittest.main()
