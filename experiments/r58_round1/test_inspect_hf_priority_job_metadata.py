"""Synthetic tests only: no HF calls, no private user data."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
import io,json,stat,tempfile,unittest,sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from contextlib import redirect_stderr,redirect_stdout
import inspect_hf_priority_job_metadata as m

def source():
    return {'schema':m.PRIORITY_SCHEMA,'status':'ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED',
      'namespace':'adradar','hf_job_id_PRIVATE':'a'*24,'stage':'CANCELED',
      'indicator_classes':['TRAINING_LOSS_GRAD_TELEMETRY'],
      'prior_gpu_log_sha256_PRIVATE':'e'*64,'update_proof_status':'PENDING_PRIMARY_RUN_ARTIFACT',
      'training_input_sha256_status':'NOT_VERIFIED','train_validation_usage_status':'NOT_VERIFIED',
      'g1_clearance':'HOLD','expansion_allowed':False}

def job(command=None,arguments=None):
    now=datetime(2026,10,31,tzinfo=timezone.utc)
    return SimpleNamespace(id='a'*24,status=SimpleNamespace(stage='CANCELED'),flavor='a100-large',
      started_at=now,finished_at=now+timedelta(seconds=60),command=command,arguments=arguments)

def private(d):
    home=Path(d);root=home/'.storyforge-r58-private';root.mkdir(mode=0o700)
    folder=root/'round1';folder.mkdir(mode=0o700);p=folder/'priority.json'
    p.write_text(json.dumps(source())+'\n');p.chmod(0o600)
    return p,folder/'result.json'

class TestPriorityMetadata(unittest.TestCase):
    def test_01_metadata_only_without_command_read(self):
        class Trap:
            id='a'*24;status=SimpleNamespace(stage='CANCELED');flavor='a100-large'
            started_at=datetime(2026,10,31,tzinfo=timezone.utc)
            finished_at=datetime(2026,10,31,tzinfo=timezone.utc)
            @property
            def command(self):raise AssertionError('COMMAND READ')
            @property
            def arguments(self):raise AssertionError('ARGUMENTS READ')
            @property
            def environment(self):raise AssertionError('ENV READ')
        s,p=m.evaluate(Trap(),source(),allow_command=False)
        self.assertEqual(s['command_intent_class'],'NOT_ACCESSED_NO_OWNER_OPT_IN')
        self.assertFalse(s['parameter_update_proven']);self.assertFalse(s['nontraining_proven'])
    def test_02_training_intent_not_update_proof(self):
        s,p=m.evaluate(job(['python','scripts/train_sft.py']),source(),allow_command=True)
        self.assertEqual(s['command_intent_class'],'POTENTIAL_TRAINING_COMMAND_INTENT')
        self.assertFalse(s['parameter_update_proven'])
        self.assertNotIn('scripts/train_sft.py',json.dumps(s)+json.dumps(p))
    def test_03_unrelated_command_not_nontrain(self):
        s,_=m.evaluate(job(['python','-c','print(4)']),source(),allow_command=True)
        self.assertEqual(s['command_intent_class'],'NO_TRAINING_COMMAND_MARKER__NOT_EXCLUDED')
        self.assertFalse(s['nontraining_proven'])
    def test_04_no_command_available(self):
        s,_=m.evaluate(job(),source(),allow_command=True)
        self.assertEqual(s['command_intent_class'],'COMMAND_UNAVAILABLE_PENDING')
    def test_05_bounded_command(self):
        s,_=m.evaluate(job(['z'*17000]),source(),allow_command=True)
        self.assertEqual(s['command_intent_class'],'BOUNDED_COMMAND_PENDING')
    def test_06_invalid_command_type(self):
        s,_=m.evaluate(job('secret'),source(),allow_command=True)
        self.assertEqual(s['command_intent_class'],'UNINSPECTABLE_PENDING')
    def test_07_wrong_provider_id_holds(self):
        a=job();a.id='b'*24
        with self.assertRaises(m.Hold):m.evaluate(a,source(),allow_command=False)
    def test_08_non_canceled_stage_holds(self):
        a=job();a.status.stage='COMPLETED'
        with self.assertRaises(m.Hold):m.evaluate(a,source(),allow_command=False)
    def test_09_no_gpu_flavor_holds(self):
        a=job();a.flavor='cpu-basic'
        with self.assertRaises(m.Hold):m.evaluate(a,source(),allow_command=False)
    def test_10_clock_inverted_holds(self):
        a=job();a.finished_at=a.started_at-timedelta(seconds=1)
        with self.assertRaises(m.Hold):m.evaluate(a,source(),allow_command=False)
    def test_11_safe_private_mode_and_exclusive(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(Path,'home',return_value=Path(d)):
            a,b=private(d);m.write_private(b,{'x':1})
            self.assertEqual(stat.S_IMODE(b.stat().st_mode),0o600)
            with self.assertRaises(Exception):m.write_private(b,{'x':2})
            self.assertEqual(json.loads(b.read_text()),{'x':1})
    def test_12_input_0600(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(Path,'home',return_value=Path(d)):
            a,b=private(d);self.assertEqual(m.read_priority(a)['stage'],'CANCELED')
            a.chmod(0o644)
            with self.assertRaises(Exception):m.read_priority(a)
    def test_13_ledger_source_drift_holds(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(Path,'home',return_value=Path(d)):
            a,b=private(d);x=source();x['update_proof_status']='PASS';a.write_text(json.dumps(x));a.chmod(0o600)
            with self.assertRaises(m.Hold):m.read_priority(a)
    def test_14_full_main_no_command_without_optin(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(Path,'home',return_value=Path(d)):
            a,b=private(d);j=job(['python','train.py'])
            fake=SimpleNamespace(HfApi=lambda:SimpleNamespace(inspect_job=lambda **kw:j))
            val=io.StringIO()
            with mock.patch.dict(sys.modules,{'huggingface_hub':fake}),redirect_stdout(val):
                self.assertEqual(m.main(['--private-priority-ledger',str(a),'--private-output',str(b)]),0)
            v=json.loads(val.getvalue());self.assertFalse(v['command_intent_mode_enabled'])
            self.assertFalse(v['environment_secrets_labels_logs_read'])
            self.assertEqual(v['g1_clearance'],'HOLD')
    def test_15_no_secret_in_error(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(Path,'home',return_value=Path(d)):
            a,b=private(d)
            fake=SimpleNamespace(HfApi=lambda:SimpleNamespace(inspect_job=lambda **kw:(_ for _ in ()).throw(RuntimeError('MY_SECRET'))))
            err=io.StringIO()
            with mock.patch.dict(sys.modules,{'huggingface_hub':fake}),redirect_stderr(err):
                self.assertEqual(m.main(['--private-priority-ledger',str(a),'--private-output',str(b)]),42)
            self.assertNotIn('MY_SECRET',err.getvalue())
    def test_16_reject_symlinked_input(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(Path,'home',return_value=Path(d)):
            a,b=private(d);link=a.with_name('alias.json');link.symlink_to(a)
            with self.assertRaises(Exception):m.read_priority(link)
    def test_17_no_input_or_output_same_file(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(Path,'home',return_value=Path(d)):
            a,b=private(d);err=io.StringIO()
            with redirect_stderr(err):self.assertEqual(m.main(['--private-priority-ledger',str(a),'--private-output',str(a)]),42)
    def test_18_status_pure_stage_enum(self):
        a=job();a.status.stage=SimpleNamespace(value='CANCELED')
        self.assertEqual(m.evaluate(a,source(),allow_command=False)[0]['priority_stage_verified'],'CANCELED')
    def test_19_timestamps_none_allowed_still_pending(self):
        a=job();a.started_at=None;a.finished_at=None
        s,_=m.evaluate(a,source(),allow_command=False)
        self.assertFalse(s['provider_started_at_present']);self.assertFalse(s['nontraining_proven'])

if __name__=='__main__':unittest.main()
