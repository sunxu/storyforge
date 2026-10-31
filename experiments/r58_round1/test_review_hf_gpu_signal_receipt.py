"""Synthetic-only R58 GPU single-positive priority audit tests; never network."""
from __future__ import annotations

import hashlib
import io
import json
import stat
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import review_hf_gpu_signal_receipt as m


def fixture(home: Path, *, positive_stage='ERROR'):
    root=home/'.storyforge-r58-private';root.mkdir(mode=0o700)
    folder=root/'round1';folder.mkdir(mode=0o700)
    unknown=folder/'60.json'; gpu=folder/'18.json'; target=folder/'1.json'
    entries=[]
    for i in range(60):
        if i<18:
            stage='COMPLETED' if i<7 else 'ERROR' if i<16 else 'CANCELED'
            hw='GPU'
        else:
            stage='ERROR'
            hw='CPU'
        entries.append({'hf_job_id_PRIVATE':f'{i+100:024x}',
                       'stage':stage,'hardware_class':hw,
                       'historical_parameter_update_classification':'PENDING_SOURCE_REVIEW',
                       'primary_train_input_provenance':'NOT_VERIFIED'})
    src={'schema':'r58_round1_g1_hf_job_exposure_triage_private_v1',
         'namespace':'adradar',
         'status':'PRIVATE_UNKNOWN_JOB_INVENTORY_ONLY__ALL_PENDING',
         'entries':entries,'g1_clearance':'HOLD','expansion_allowed':False}
    unknown.write_text(json.dumps(src)+'\n',encoding='utf-8');unknown.chmod(0o600)
    items=[]
    for i in range(18):
        state='POTENTIAL_OPTIMIZER_LOG_INDICATOR' if i==9 else 'NO_INDICATOR_OBSERVED__NOT_EXCLUDED'
        items.append({'hf_job_id_PRIVATE':entries[i]['hf_job_id_PRIVATE'],
                      'stage':entries[i]['stage'],'scan_state':state,
                      'log_sha256_PRIVATE':hashlib.sha256(str(i).encode()).hexdigest(),
                      'log_bytes_scanned':100,'lines_scanned':3,
                      'indicator_classes':['TRAINING_LOSS_GRAD_TELEMETRY'] if i==9 else [],
                      'parameter_update_proven':False,
                      'confirmed_no_parameter_update':False,
                      'primary_input_bytes_verified':False})
    log={'schema':m.OUTPUT_SCHEMA,
         'status':'GPU_LOG_SIGNAL_REVIEW_ONLY__ALL_PENDING',
         'namespace':'adradar',
         'input_private_ledger_sha256_PRIVATE':hashlib.sha256(unknown.read_bytes()).hexdigest(),
         'entries':items,'g1_clearance':'HOLD','expansion_allowed':False}
    gpu.write_text(json.dumps(log)+'\n',encoding='utf-8');gpu.chmod(0o600)
    return unknown,gpu,target


def check(unknown, gpu):
    src,digest=m.read_input(unknown)
    return m.read_gpu_receipt(gpu,src,digest)

class TestGpuPriority(unittest.TestCase):
    def test_01_one_flagged_case_no_ids_in_safe(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            unknown,gpu,_=fixture(Path(d));s,p=check(unknown,gpu)
            self.assertEqual(s['potential_indicator_jobs'],1)
            self.assertEqual(s['no_indicator_jobs_not_excluded'],17)
            self.assertEqual(s['priority_job_stage'],'ERROR')
            self.assertEqual(s['priority_job_indicator_classes'],['TRAINING_LOSS_GRAD_TELEMETRY'])
            self.assertEqual(p['hf_job_id_PRIVATE'],f'{109:024x}')
            self.assertNotIn(p['hf_job_id_PRIVATE'],json.dumps(s))
    def test_02_hasher_links_to_60_source(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            unknown,gpu,_=fixture(Path(d));src,digest=m.read_input(unknown)
            self.assertTrue(m.read_gpu_receipt(gpu,src,digest)[0]['gpu_signal_ledger_crosslinked_to_unknown_ledger'])
            obj=json.loads(gpu.read_text());obj['input_private_ledger_sha256_PRIVATE']='0'*64
            gpu.write_text(json.dumps(obj));gpu.chmod(0o600)
            with self.assertRaises(m.Hold):m.read_gpu_receipt(gpu,src,digest)
    def test_03_missing_ledger_0600_holds(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            unknown,gpu,_=fixture(Path(d));gpu.chmod(0o644)
            with self.assertRaises(Exception):check(unknown,gpu)
    def test_04_duplicate_ids_hold(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());obj['entries'][1]['hf_job_id_PRIVATE']=obj['entries'][0]['hf_job_id_PRIVATE'];g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_05_stage_mismatch_holds(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());obj['entries'][0]['stage']='CANCELED';g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_06_two_positives_hold(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());x=obj['entries'][0];x['scan_state']='POTENTIAL_OPTIMIZER_LOG_INDICATOR';x['indicator_classes']=['OPTIMIZER_STEP_LITERAL'];g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_07_no_positive_holds(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());x=obj['entries'][9];x['scan_state']='NO_INDICATOR_OBSERVED__NOT_EXCLUDED';x['indicator_classes']=[];g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_08_malicious_signal_class_holds(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());obj['entries'][9]['indicator_classes']=['USER_CONTENT'];g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_09_duplicate_signal_class_holds(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());obj['entries'][9]['indicator_classes']=['OPTIMIZER_STEP_LITERAL']*2;g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_10_falsely_claimed_training_approval_holds(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());obj['entries'][9]['parameter_update_proven']=True;g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_11_writes_private_0600_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,out=fixture(Path(d));s,p=check(u,g);m.write_private(out,p)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o600)
            val=out.read_bytes()
            with self.assertRaises(Exception):m.write_private(out,p)
            self.assertEqual(val,out.read_bytes())
            self.assertEqual(json.loads(val)['update_proof_status'],'PENDING_PRIMARY_RUN_ARTIFACT')
    def test_12_reject_symlinked_output(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,out=fixture(Path(d));out.symlink_to(u)
            with self.assertRaises(Exception):m.write_private(out,{})
            self.assertTrue(out.is_symlink())
    def test_13_main_end_to_end_no_hf_or_logs(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,out=fixture(Path(d));v=io.StringIO()
            with redirect_stdout(v):self.assertEqual(m.main(['--private-unknown-ledger',str(u),'--private-gpu-signal-ledger',str(g),'--private-priority-output',str(out)]),0)
            s=json.loads(v.getvalue());self.assertFalse(s['hf_api_called_this_step'])
            self.assertFalse(s['historical_job_logs_read_this_step'])
            self.assertEqual(s['g1_clearance'],'HOLD');self.assertEqual(s['train_admitted'],0)
            self.assertFalse(s['expansion_allowed'])
            self.assertTrue(out.exists())
    def test_14_main_collision_fails_and_no_stdout_data(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,out=fixture(Path(d));v=io.StringIO();err=io.StringIO()
            with redirect_stdout(v),redirect_stderr(err): self.assertEqual(m.main(['--private-unknown-ledger',str(u),'--private-gpu-signal-ledger',str(g),'--private-priority-output',str(u)]),42)
            self.assertEqual(v.getvalue(),'');self.assertIn('HOLD',err.getvalue())
    def test_15_mismatched_source_count_fails(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(u.read_text());obj['entries'].pop();u.write_text(json.dumps(obj));u.chmod(0o600)
            with self.assertRaises(Exception):check(u,g)
    def test_16_reject_log_sha_absent(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());obj['entries'][0]['log_sha256_PRIVATE']=None;g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)
    def test_17_reject_unknown_signal_stage(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(Path,'home',return_value=Path(d)):
            u,g,_=fixture(Path(d));obj=json.loads(g.read_text());obj['entries'][0]['scan_state']='BOUNDED_LIMIT_PENDING';g.write_text(json.dumps(obj));g.chmod(0o600)
            with self.assertRaises(m.Hold):check(u,g)

if __name__=='__main__':unittest.main()
