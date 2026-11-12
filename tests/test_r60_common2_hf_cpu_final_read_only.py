"""Synthetic final CPU2 preflight checks; no service calls."""
from __future__ import annotations

from types import SimpleNamespace

from scripts import r60_common2_hf_cpu_final_read_only as final_gate
from scripts import r60_common2_hf_cpu_image_retry as retry
from scripts import r60_common2_hf_cpu_stage as staging
from scripts import r60_common2_hf_cpu_stage_v2 as v2
from tests.test_r60_common2_hf_cpu_stage import fixture

KEY = "r60-common2-cpu2-20261112T090000Z-bbbbbbbbbbbb"


class FakeApi:
    def __init__(self, stage, jobs=(), output_files=()):
        self.stage = stage
        self.jobs = jobs
        self.output_files = output_files
        self.calls = []

    def list_bucket_tree(self, bucket, prefix, recursive):
        self.calls.append(("bucket", prefix))
        if "/runs/" in prefix:
            return [SimpleNamespace(path=prefix + p, type="file")
                    for p in sorted(final_gate.bucket.expected(self.stage))]
        return [SimpleNamespace(path=prefix + p, type="file") for p in self.output_files]

    def list_jobs(self, *, namespace):
        self.calls.append(("jobs", namespace))
        return list(self.jobs)


def create_stage(tmp_path):
    inp = fixture(tmp_path)
    old = tmp_path / retry.RUN_KEY
    staging.stage(inp, old, retry.RUN_KEY)
    new = tmp_path / KEY
    v2.build(old, new, KEY)
    return new


def test_empty_outputs_does_not_prove_exhaustive_jobs(tmp_path):
    stage = create_stage(tmp_path)
    api = FakeApi(stage, jobs=[SimpleNamespace(name="other", labels={}) for _ in range(100)])
    result = final_gate.check(api, stage, KEY)
    assert result["local_stage"] == "PASS"
    assert result["remote_input"] == "READY_PASS"
    assert result["remote_output"] == "EMPTY_PASS"
    assert result["submit_marker"] == "ABSENT"
    assert result["visible_jobs"] == 100
    assert result["reason_code"] == "JOB_HISTORY_INCOMPLETE_HOLD"
    assert result["job_submission_calls"] == 0
    assert result["history_exhaustive"] is False


def test_output_nonempty_prevents_job_list(tmp_path):
    stage = create_stage(tmp_path)
    api = FakeApi(stage, output_files=["receipt.json"])
    result = final_gate.check(api, stage, KEY)
    assert result["reason_code"] == "OUTPUT_ALREADY_PRESENT"
    assert all(call[0] != "jobs" for call in api.calls)


def test_present_marker_short_circuits_all_remote_reads(tmp_path):
    stage = create_stage(tmp_path)
    (tmp_path / (KEY + ".cpu-submit-v2-attempted")).mkdir()
    api = FakeApi(stage)
    result = final_gate.check(api, stage, KEY)
    assert result["reason_code"] == "SUBMISSION_ALREADY_ATTEMPTED"
    assert result["submit_marker"] == "PRESENT"
    assert api.calls == []


def test_named_existing_job_holds(tmp_path):
    stage = create_stage(tmp_path)
    api = FakeApi(stage, jobs=[SimpleNamespace(name=KEY, labels={})])
    result = final_gate.check(api, stage, KEY)
    assert result["reason_code"] == "VISIBLE_JOB_MATCH_HOLD"
    assert result["matching_jobs"] == 1
    assert result["job_submission_calls"] == 0
