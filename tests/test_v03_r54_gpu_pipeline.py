"""Network-free R54 V2 sync/submit/verify anti-bypass tests; no GPU activity."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]

def load(name, filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/filename)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

guard=load("r54_remote_guard","v03_r54_gpu_remote_guard.py")
runner=load("r54_gpu_runner","v03_r54_gpu_runner.py")
verifier=load("r54_gpu_verify","v03_r54_gpu_verify.py")
KEY="r54-v2-20261021T113539Z-523139"

class API:
    def __init__(self,entries=(),error=None):
        self.entries=list(entries);self.error=error
    def list_bucket_tree(self,bucket,*,prefix,recursive):
        if self.error: raise self.error
        return [SimpleNamespace(path=x,type="file") for x in self.entries if x.startswith(prefix)]

class GuardTests(unittest.TestCase):
    def test_empty_stage_and_results_prefix(self):
        self.assertIn("AVAILABLE",guard.check("empty",KEY,API()))
    def test_ready_requires_every_file(self):
        stage=f"{guard.PREFIX}/{KEY}/"
        self.assertIn("COMPLETE",guard.check("ready",KEY,API([stage+x for x in guard.FILES])))
    def test_empty_prefix_does_not_misread_listing_exit_code(self):
        stage=f"{guard.PREFIX}/{KEY}/"
        with self.assertRaisesRegex(ValueError,"ALREADY_EXISTS"):
            guard.check("empty",KEY,API([stage+"code/foo.py"]))
    def test_partial_stage_rejected(self):
        stage=f"{guard.PREFIX}/{KEY}/"
        with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
            guard.check("ready",KEY,API([stage+"SHA256SUMS.txt"]))
    def test_extra_stage_rejected(self):
        stage=f"{guard.PREFIX}/{KEY}/"
        with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
            guard.check("ready",KEY,API([stage+x for x in guard.FILES]+[stage+"extra"]))
    def test_old_results_key_never_reused(self):
        with self.assertRaisesRegex(ValueError,"EXPERIMENT_ALREADY_EXISTS"):
            guard.check("empty",KEY,API([f"{guard.EXPERIMENTS}/{KEY}/output/log"]))
    def test_remote_submission_marker_blocks_reuse(self):
        path=f"{guard.SUBMISSIONS}/{KEY}/submit-attempt.txt"
        with self.assertRaisesRegex(ValueError,"NO_AUTOMATIC_RETRY"):
            guard.check("ready",KEY,API([path]))
    def test_auth_failure_never_treated_as_empty(self):
        with self.assertRaises(PermissionError):
            guard.check("empty",KEY,API(error=PermissionError("denied")))
    def test_key_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError,"INVALID_RUN_KEY"):
            guard.check("empty","../any",API())

class RunnerStageTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.stage=Path(t.name);self.expected=[
            "config/r54.yaml",
            "private/release/train.jsonl","private/release/validation.jsonl",
            "private/release/R53_RELEASE_RECEIPT.json",
            "private/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json",
            "private/R53_CPU40_OWNER_INTAKE_VERIFIED.json",
            "code/v03_r54_gpu_runner.py","code/v03_r54_gpu_worker.sh",
            "code/v03_r54_gpu_readiness_v2.py",
            "code/v03_r54_last_step_checkpoint_gate.py",
            "code/hf_label_mask_audit.py","code/hf_smoke_guard.py",
            "code/hf_job_runner.py"]
        for name in self.expected:
            p=self.stage/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("from pathlib import Path\n"
                         "def check(*args): return {'training_config':{'optimizer_steps_estimate':16}}\n"
                         if name=="code/v03_r54_gpu_readiness_v2.py" else "synthetic-test-file")
        self.update_manifest()
    def update_manifest(self):
        (self.stage/"SHA256SUMS.txt").write_text("".join(
            runner.digest(self.stage/name)+"  "+name+"\n" for name in sorted(self.expected)))
    def test_synthetic_stage_manifest_ok(self):
        self.assertEqual(runner.stage_gate(self.stage)["config_sha256"],
                         runner.digest(self.stage/"config/r54.yaml"))
    def test_mutated_stage_blocked(self):
        (self.stage/"private/release/train.jsonl").write_text("tampered")
        with self.assertRaisesRegex(RuntimeError,"sha mismatch"):
            runner.stage_gate(self.stage)
    def test_additional_manifest_object_blocked(self):
        other=self.stage/"code/extra.py";other.write_text("extra")
        with (self.stage/"SHA256SUMS.txt").open("a") as stream:
            stream.write(runner.digest(other)+"  code/extra.py\n")
        with self.assertRaisesRegex(RuntimeError,"unexpected or missing"):
            runner.stage_gate(self.stage)
    def test_relative_path_escape_blocked(self):
        with (self.stage/"SHA256SUMS.txt").open("a") as stream:
            stream.write("a"*64+"  ../outside.json\n")
        with self.assertRaisesRegex(RuntimeError,"unsafe/duplicate"):
            runner.stage_gate(self.stage)

class NoPaidSubmitTests(unittest.TestCase):
    def test_shell_syntax(self):
        for name in ("v03_r54_gpu_submit.sh","v03_r54_gpu_worker.sh"):
            r=subprocess.run(["bash","-n",str(ROOT/"scripts"/name)],capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr.decode())
    def test_sync_does_not_authorize_submit(self):
        code=(ROOT/"scripts/v03_r54_gpu_submit.sh").read_text()
        self.assertLess(code.index("if [[ \"$MODE\" == sync ]]"),code.index("STORYFORGE_ALLOW_PAID_GPU:-"))
        self.assertIn('STORYFORGE_R54_OWNER_GPU_SCOPE:-',code)
        self.assertEqual(code.count("hf jobs run"),1)
        self.assertIn("R54_PAID_GPU_SUBMIT_NOT_EXECUTED",code)
    def test_worker_fails_without_exact_scope(self):
        code=(ROOT/"scripts/v03_r54_gpu_worker.sh").read_text()
        self.assertIn('R54_31_9_V2_16STEP_ONE_EPOCH',code)
        self.assertIn('sha256sum --check --status',code)
        self.assertIn('v03_r54_gpu_readiness_v2.py',code)
    def test_submit_local_and_remote_attempt_guard(self):
        code=(ROOT/"scripts/v03_r54_gpu_submit.sh").read_text()
        self.assertIn('mkdir "$LOCAL_LOCK"',code)
        self.assertIn('/submissions/$RUN_KEY/submit-attempt.txt',code)
        self.assertLess(code.index('mkdir "$LOCAL_LOCK"'),code.index('hf jobs run --namespace'))
    def test_runner_requires_terminal_checkpoint_and_actual_infer(self):
        code=(ROOT/"scripts/v03_r54_gpu_runner.py").read_text()
        self.assertIn('checkpoint_check(output,reload_file)',code)
        self.assertIn('check_inference_result(inference_output)',code)
        self.assertIn('R54_GPU_16STEP_ENGINEERING_PASS__NOT_PROMOTED',code)
        self.assertNotIn('"swift","sft","--max_steps"',code)
    def test_verify_no_remote_or_gpu_execution(self):
        code=(ROOT/"scripts/v03_r54_gpu_verify.py").read_text()
        for forbidden in ("hf jobs run","swift sft","snapshot_download(","subprocess.run("):
            self.assertNotIn(forbidden,code)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.release=self.root/"release";self.release.mkdir()
        self.cfg=self.root/"r54.yaml";self.cfg.write_text("synthetic")
        for name in ("train.jsonl","validation.jsonl","R53_RELEASE_RECEIPT.json"):
            (self.release/name).write_text("synthetic")
        self.log=self.root/"runtime.log"
        self.log.write_text("R54_STATUS=R54_GPU_16STEP_ENGINEERING_PASS__NOT_PROMOTED\\n")
        self.reload=self.root/"reload.json"
        self.reload_record={"status":"R54_ADAPTER_RELOAD_INFERENCE_PASS",
            "final_global_step":16,"adapter_sha256":"a"*64,
            "model_revision":verifier.REVISION}
        self.reload.write_text(json.dumps(self.reload_record))
        self.report=self.root/"report.json"
        self.data={"schema":"storyforge-r54-v2-gpu-one-epoch-v1",
            "run_key":KEY,"status":"R54_GPU_16STEP_ENGINEERING_PASS__NOT_PROMOTED",
            "training_started":True,"training_finished":True,"adapter_reload_pass":True,
            "model":verifier.MODEL,"revision":verifier.REVISION,
            "formal_train_rows":31,"formal_validation_rows":9,
            "r50_read":False,"model_promoted":False,"gpu_used":True,
            "stage":{"config_sha256":verifier.CONFIG_SHA,"train_sha256":verifier.TRAIN_SHA,
                     "validation_sha256":verifier.VAL_SHA,
                     "formal_release_receipt_sha256":verifier.RELEASE_SHA},
            "dependencies":{"ms-swift":"4.5.3","transformers":"5.16.1",
                            "bitsandbytes":"0.50.2"},
            "actual_ms_swift_full_label_audit":"PASS_40",
            "gpu":{"name":"synthetic-A100"},
            "checkpoint_and_reload":{
                "status":"R54_FINAL_STEP_16_CHECKPOINT_AND_RELOAD_EVIDENCE_ACCEPTED__NOT_PROMOTED",
                "global_step":16,"final_checkpoint":"checkpoint-16",
                "intermediate_checkpoint":"checkpoint-8",
                "eval_steps_verified":[4,8,12,16],
                "final_adapter_sha256":"a"*64}}
        import hashlib
        self.data["checkpoint_and_reload"]["reload_report_sha256"]=hashlib.sha256(self.reload.read_bytes()).hexdigest()
        self.rewrite()
    def rewrite(self):
        self.report.write_text(json.dumps(self.data))
    def evaluate(self):
        import hashlib
        trusted={"r54.yaml":verifier.CONFIG_SHA,"train.jsonl":verifier.TRAIN_SHA,
                 "validation.jsonl":verifier.VAL_SHA,
                 "R53_RELEASE_RECEIPT.json":verifier.RELEASE_SHA}
        def fake_hash(p):
            return trusted.get(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
        with mock.patch.object(verifier,"hashfile",side_effect=fake_hash):
            return verifier.verify(self.report,self.log,self.reload,self.release,self.cfg)
    def test_valid_synthetic_report(self):
        r=self.evaluate()
        self.assertEqual(r["global_step"],16)
        self.assertFalse(r["independent_remote_weight_sha256_verification"])
    def test_fake_success_state_blocked(self):
        self.data["status"]="FAILED_OR_INCOMPLETE__NO_PROMOTION";self.rewrite()
        with self.assertRaisesRegex(ValueError,"not fully PASS"):self.evaluate()
    def test_missing_terminal_eval_blocked(self):
        self.data["checkpoint_and_reload"]["eval_steps_verified"]=[4,8,12];self.rewrite()
        with self.assertRaisesRegex(ValueError,"checkpoint proof incomplete"):self.evaluate()
    def test_forged_reload_digest_blocked(self):
        self.reload_record["adapter_sha256"]="f"*64
        self.reload.write_text(json.dumps(self.reload_record))
        with self.assertRaisesRegex(ValueError,"reload evidence inconsistent"):self.evaluate()
    def test_false_log_status_blocked(self):
        self.log.write_text("R54_STATUS=FAILED_OR_INCOMPLETE__NO_PROMOTION\\n")
        with self.assertRaisesRegex(ValueError,"console PASS"):self.evaluate()
    def test_r50_access_blocked(self):
        self.data["r50_read"]=True;self.rewrite()
        with self.assertRaisesRegex(ValueError,"scope mismatch"):self.evaluate()

if __name__=="__main__":unittest.main()
