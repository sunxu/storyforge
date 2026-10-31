"""Pure synthetic metadata-only tests, no network and no private user files."""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from contextlib import redirect_stdout, redirect_stderr

import triage_hf_job_exposure as m


def job(n, stage="COMPLETED", flavor="cpu-basic"):
    return SimpleNamespace(id=f"{n:024x}", status=SimpleNamespace(stage=stage), flavor=flavor)

def records():
    known=[SimpleNamespace(id=i,status=SimpleNamespace(stage="COMPLETED"),flavor="a100-large")
           for i in m.KNOWN_SFT_JOBS.values()]
    documented=[SimpleNamespace(id=i,status=SimpleNamespace(stage="COMPLETED"),flavor="cpu-upgrade")
                for i in m.DOCUMENTED_NO_OPTIMIZER.values()]
    return known + documented + [job(1,"ERROR","a100-large"),job(2,"CANCELED","cpu-basic"),job(3,"COMPLETED","mystery-hw")]

class TestHfTriage(unittest.TestCase):
    def test_01_known_and_documented_counts(self):
        s,p=m.summarize_and_private(records(),"adradar")
        self.assertEqual(s["known_parameter_update_job_ids_found"],5)
        self.assertEqual(s["known_documented_non_optimizer_job_ids_found"],4)
        self.assertEqual(s["unclassified_job_count"],3)
        self.assertEqual(s["hf_jobs_returned"],12)
    def test_02_unknown_gpu_remains_pending(self):
        s,p=m.summarize_and_private(records(),"adradar")
        self.assertEqual(s["unclassified_job_hardware_counts"]["GPU"],1)
        self.assertFalse(s["unclassified_gpu_jobs_excluded_as_non_training"])
        self.assertIn("PENDING_SOURCE_REVIEW",[x["historical_parameter_update_classification"] for x in p["entries"]])
    def test_03_unknown_cpu_remains_pending(self):
        s,_=m.summarize_and_private(records(),"adradar")
        self.assertFalse(s["unclassified_cpu_jobs_excluded_as_non_training"])
        self.assertEqual(s["unclassified_job_hardware_counts"]["CPU"],1)
    def test_04_unknown_flavor_remains_pending(self):
        s,_=m.summarize_and_private(records(),"adradar")
        self.assertEqual(s["unclassified_job_hardware_counts"]["UNRECOGNIZED"],1)
    def test_05_error_cancel_dont_clear(self):
        s,_=m.summarize_and_private(records(),"adradar")
        self.assertFalse(s["failed_or_canceled_jobs_proven_no_updates"])
        self.assertEqual(s["unclassified_job_stage_counts"]["CANCELED"],1)
        self.assertEqual(s["unclassified_job_stage_counts"]["ERROR"],1)
    def test_06_no_known_nontrain_bypasses_full_completeness(self):
        s,_=m.summarize_and_private(records()[:9],"adradar")
        self.assertFalse(s["source_registry_complete"])
        self.assertEqual(s["g1_clearance"],"HOLD")
    def test_07_malformed_uuid_id_blocked(self):
        with self.assertRaises(m.Hold):m.summarize_and_private([SimpleNamespace(id="bad",status=SimpleNamespace(stage="ERROR"),flavor="cpu-basic")],"adradar")
    def test_08_duplicate_id_blocked(self):
        with self.assertRaises(m.Hold):m.summarize_and_private([job(4),job(4)],"adradar")
    def test_09_bad_stage_blocked(self):
        with self.assertRaises(m.Hold):m.summarize_and_private([job(4,stage="POTATO")],"adradar")
    def test_10_bad_namespace_blocked(self):
        with self.assertRaises(m.Hold):m.summarize_and_private(records(),"adradar/sub")
    def test_11_no_command_access(self):
        class ProtectedJob:
            id=f"{99:024x}"
            status=SimpleNamespace(stage="ERROR")
            flavor="a100-large"
            @property
            def command(self): raise AssertionError("COMMAND ACCESSED")
            @property
            def secrets(self): raise AssertionError("SECRETS ACCESSED")
            @property
            def labels(self): raise AssertionError("LABEL ACCESSED")
        s,_=m.summarize_and_private([ProtectedJob()],"adradar")
        self.assertFalse(s["job_commands_arguments_env_secrets_logs_labels_read"])
    def test_12_no_id_in_public_safe(self):
        s,p=m.summarize_and_private(records(),"adradar")
        raw=json.dumps(s)
        for x in p["entries"]: self.assertNotIn(x["hf_job_id_PRIVATE"],raw)
    def test_13_private_entries_bounded_metadata(self):
        _,p=m.summarize_and_private(records(),"adradar")
        self.assertEqual(set(p["entries"][0]),{"hf_job_id_PRIVATE","stage","hardware_class","historical_parameter_update_classification","primary_train_input_provenance"})
    def test_14_reject_nonstring_flavor(self):
        with self.assertRaises(m.Hold):m.summarize_and_private([job(6,flavor=123)],"adradar")
    def test_15_missing_flavor_remains_unrecognized(self):
        s,_=m.summarize_and_private([job(6,flavor=None)],"adradar")
        self.assertEqual(s["unclassified_job_hardware_counts"],{"UNRECOGNIZED":1})
    def test_16_reject_invalid_source_count_limit(self):
        with mock.patch.object(m,"MAX_JOBS",2):
            with self.assertRaises(m.Hold):m.summarize_and_private([job(1),job(2),job(3)],"adradar")
    def test_17_private_output_mode_and_no_overwrite(self):
        _,p=m.summarize_and_private(records(),"adradar")
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);root=home/".storyforge-r58-private";root.mkdir(mode=0o700)
            folder=root/"round1";folder.mkdir(mode=0o700)
            dst=folder/"hf_unknown.json"
            with mock.patch.object(Path,"home",return_value=home):
                m.write_private(dst,p)
                self.assertEqual(dst.stat().st_mode & 0o777,0o600)
                self.assertEqual(len(json.loads(dst.read_text())["entries"]),3)
                before=dst.read_bytes()
                with self.assertRaises(m.Hold):m.write_private(dst,p)
                self.assertEqual(dst.read_bytes(),before)
    def test_18_no_private_output_beyond_root(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);dst=home/"unsafe.json"
            with mock.patch.object(Path,"home",return_value=home):
                with self.assertRaises(m.Hold):m.write_private(dst,{})
    def test_19_symlink_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);root=home/".storyforge-r58-private";root.mkdir(mode=0o700)
            target=root/"real";target.mkdir(mode=0o700)
            symlink=root/"link";symlink.symlink_to(target,target_is_directory=True)
            with mock.patch.object(Path,"home",return_value=home):
                with self.assertRaises(m.Hold):m.write_private(symlink/"unknown.json",{})
    def test_20_main_no_new_job(self):
        fake_api=SimpleNamespace(list_jobs=lambda namespace: records())
        fake_module=SimpleNamespace(HfApi=lambda:fake_api)
        output=io.StringIO()
        with mock.patch.dict(sys.modules,{"huggingface_hub":fake_module}),redirect_stdout(output):
            self.assertEqual(m.main(["--namespace","adradar"]),0)
        x=json.loads(output.getvalue())
        self.assertFalse(x["new_job_started"])
        self.assertEqual(x["unclassified_job_count"],3)
    def test_21_missing_credential_or_api_fails_closed(self):
        fake_api=SimpleNamespace(list_jobs=lambda namespace: (_ for _ in ()).throw(RuntimeError("secret: never echo")))
        err=io.StringIO()
        with mock.patch.dict(sys.modules,{"huggingface_hub":SimpleNamespace(HfApi=lambda:fake_api)}),redirect_stderr(err):
            self.assertEqual(m.main(["--namespace","adradar"]),42)
        self.assertNotIn("secret",err.getvalue())

if __name__=="__main__":unittest.main()
