"""R58 G1 bounded GPU log scan: synthetic only, never contacts Hugging Face."""
from __future__ import annotations
from collections import Counter
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
import probe_hf_gpu_job_logs as m


def fake_input():
    rows=[]
    for i in range(60):
        stage=('COMPLETED' if i < 7 else 'ERROR' if i < 16 else 'CANCELED') if i < 18 else ('ERROR' if i%2 else 'COMPLETED')
        rows.append({'hf_job_id_PRIVATE':f'{i+1000:024x}',
        'stage':stage,'hardware_class':'GPU' if i<18 else 'CPU',
        'historical_parameter_update_classification':'PENDING_SOURCE_REVIEW',
        'primary_train_input_provenance':'NOT_VERIFIED'})
    return {'schema':m.INPUT_SCHEMA,'namespace':'adradar',
            'status':'PRIVATE_UNKNOWN_JOB_INVENTORY_ONLY__ALL_PENDING',
            'entries':rows,'g1_clearance':'HOLD','expansion_allowed':False}


def write_in(home, data=None):
    root=home/m.ROOT_NAME;root.mkdir(mode=0o700)
    sub=root/'round1';sub.mkdir(mode=0o700)
    path=sub/'unknown.json'
    with path.open('w',encoding='utf-8') as f:json.dump(data or fake_input(),f)
    path.chmod(0o600)
    return path,sub/'out.json'

class FakeApi:
    def __init__(self, value=None, fail_ids=None):
        self.calls=[];self.value=value if value is not None else ['done\n']
        self.fail_ids=set(fail_ids or [])
    def fetch_job_logs(self,*,job_id,namespace,follow):
        self.calls.append((job_id,namespace,follow))
        if job_id in self.fail_ids:raise RuntimeError('API_TOKEN_SHOULD_NEVER_ECHO')
        return iter(self.value)

class TestGpuLogProbe(unittest.TestCase):
    def test_01_input_frozen_60_18_42_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            p,_=write_in(home)
            with mock.patch.object(Path,'home',return_value=home):
                v,sha=m.read_input(p)
                self.assertEqual(len(v['gpu']),18)
                self.assertEqual(len(sha),64)
    def test_02_bad_schema_holds(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);o=fake_input();o['schema']='bad';p,_=write_in(home,o)
            with mock.patch.object(Path,'home',return_value=home):
                with self.assertRaises(m.Hold):m.read_input(p)
    def test_03_extra_or_missing_unknown_holds(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);o=fake_input();o['entries'].pop();p,_=write_in(home,o)
            with mock.patch.object(Path,'home',return_value=home):
                with self.assertRaises(m.Hold):m.read_input(p)
    def test_04_duplicate_job_holds(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);o=fake_input();o['entries'][1]['hf_job_id_PRIVATE']=o['entries'][0]['hf_job_id_PRIVATE'];p,_=write_in(home,o)
            with mock.patch.object(Path,'home',return_value=home):
                with self.assertRaises(m.Hold):m.read_input(p)
    def test_05_source_not_0600_holds(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,_=write_in(home);p.chmod(0o644)
            with mock.patch.object(Path,'home',return_value=home):
                with self.assertRaises(m.Hold):m.read_input(p)
    def test_06_source_symlink_holds(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,_=write_in(home);s=p.with_name('link.json');s.symlink_to(p)
            with mock.patch.object(Path,'home',return_value=home):
                with self.assertRaises(m.Hold):m.read_input(s)
    def test_07_gpu_stage_count_change_holds(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);o=fake_input();o['entries'][0]['stage']='ERROR';p,_=write_in(home,o)
            with mock.patch.object(Path,'home',return_value=home):
                with self.assertRaises(m.Hold):m.read_input(p)
    def test_08_output_no_overwrite_and_0600(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,out=write_in(home)
            with mock.patch.object(Path,'home',return_value=home):
                m.write_private(out,{'schema':m.OUTPUT_SCHEMA})
                self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o600)
                before=out.read_bytes()
                with self.assertRaises(m.Hold):m.write_private(out,{'schema':'changed'})
                self.assertEqual(before,out.read_bytes())
    def test_09_output_alias_path_holds(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,out=write_in(home);alias=p.parent.parent/'alias';alias.symlink_to(p.parent,target_is_directory=True)
            with mock.patch.object(Path,'home',return_value=home):
                with self.assertRaises(m.Hold):m.write_private(alias/'out.json',{})
    def test_10_scan_telemetry_positive_not_proven(self):
        r=m.scan_logs(["{'loss': 1.3, 'grad_norm': 0.2, 'learning_rate': 0.00001}\n"])
        self.assertEqual(r['scan_state'],'POTENTIAL_OPTIMIZER_LOG_INDICATOR')
        self.assertIn('TRAINING_LOSS_GRAD_TELEMETRY',r['indicator_classes'])
    def test_11_no_signal_does_not_clear(self):
        r=m.scan_logs(['Complete, hello\n'])
        self.assertEqual(r['scan_state'],'NO_INDICATOR_OBSERVED__NOT_EXCLUDED')
    def test_12_limit_ends_as_pending(self):
        with mock.patch.object(m,'MAX_LOG_BYTES',10):
            r=m.scan_logs(['b'*11]);self.assertEqual(r['scan_state'],'BOUNDED_LIMIT_PENDING')
            self.assertIsNone(r['log_sha256_PRIVATE'])
    def test_13_wrong_line_type_rejected(self):
        with self.assertRaises(m.Hold):m.scan_logs([{'text':'secret'}])
    def test_14_all_gpu_requested_no_new_jobs(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,_=write_in(home)
            with mock.patch.object(Path,'home',return_value=home):
                ledger,sha=m.read_input(p)
            api=FakeApi(["train_loss: 1.7 train_runtime: 12\n"])
            safe,private=m.examine(api,ledger,sha)
            self.assertEqual(len(api.calls),18)
            self.assertTrue(all(x[2] is False for x in api.calls))
            self.assertEqual(safe['gpu_log_scan_state_counts']['POTENTIAL_OPTIMIZER_LOG_INDICATOR'],18)
            self.assertEqual(safe['gpu_jobs_with_parameter_updates_independently_proven'],0)
            self.assertEqual(safe['gpu_jobs_cleared_as_non_training'],0)
            self.assertFalse(safe['expansion_allowed'])
            self.assertEqual(len(private['entries']),18)
            self.assertNotIn(api.calls[0][0],json.dumps(safe))
    def test_15_log_unavailable_keeps_pending(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,_=write_in(home)
            with mock.patch.object(Path,'home',return_value=home):ledger,sha=m.read_input(p)
            one=ledger['gpu'][0]['hf_job_id_PRIVATE'];api=FakeApi(fail_ids={one})
            safe,private=m.examine(api,ledger,sha)
            self.assertEqual(safe['gpu_log_scan_state_counts']['LOG_UNAVAILABLE_PENDING'],1)
            self.assertTrue(all(x['confirmed_no_parameter_update'] is False for x in private['entries']))
    def test_16_no_raw_logs_in_safe_or_private(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,_=write_in(home)
            with mock.patch.object(Path,'home',return_value=home):ledger,sha=m.read_input(p)
            token='SECRET='+'1234DONTLEAK'
            api=FakeApi([token+'\n'])
            safe,private=m.examine(api,ledger,sha)
            self.assertNotIn(token,json.dumps(safe))
            self.assertNotIn(token,json.dumps(private))
            self.assertEqual(safe['gpu_log_scan_state_counts']['NO_INDICATOR_OBSERVED__NOT_EXCLUDED'],18)
    def test_17_main_invalid_namespace_fails_closed(self):
        err=io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(m.main(['--namespace','someoneelse','--private-unknown-ledger','/bad','--private-output','/bad2']),42)
        self.assertNotIn('someoneelse',err.getvalue())
    def test_18_main_api_read_output_synthetic(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);inp,out=write_in(home)
            fake=FakeApi(['Done\n'])
            module=type('fake',(),{'HfApi':lambda:fake})
            import sys
            text=io.StringIO()
            with (mock.patch.object(Path,'home',return_value=home),
                  mock.patch.dict(sys.modules,{'huggingface_hub':module}),
                  redirect_stdout(text)):
                self.assertEqual(m.main(['--allow-private-historical-job-logs','--private-unknown-ledger',str(inp),'--private-output',str(out)]),0)
            safe=json.loads(text.getvalue())
            self.assertTrue(safe['private_gpu_log_signal_ledger_written'])
            self.assertEqual(safe['gpu_logs_requested'],18)
            self.assertEqual(len(json.loads(out.read_text())['entries']),18)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o600)
    def test_19_missing_owner_opt_in_fails_closed_without_private_access(self):
        err=io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(m.main(['--private-unknown-ledger','/bad','--private-output','/bad2']),42)
        self.assertIn('HOLD',err.getvalue())

    def test_20_training_steps_not_estimated(self):
        api=FakeApi(["optimizer.step()\n"])
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);p,_=write_in(home)
            with mock.patch.object(Path,'home',return_value=home):ledger,sha=m.read_input(p)
        safe,private=m.examine(api,ledger,sha)
        self.assertFalse(safe['all_actual_sft_runs_and_input_sources_proven_complete'])
        self.assertTrue(all(x['parameter_update_proven'] is False for x in private['entries']))

if __name__=='__main__':unittest.main()
