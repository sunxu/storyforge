"""Read-only diagnostics for image retry failure, all test inputs synthetic."""
from __future__ import annotations

from types import SimpleNamespace

from scripts import r60_common2_hf_cpu_image_probe as probe
from scripts import r60_common2_hf_cpu_image_retry as retry
from scripts import r60_common2_hf_cpu_stage as stage
from tests.test_r60_common2_hf_cpu_stage import fixture


class MockApi:
    def __init__(self, files):
        self.files = files
        self.called = []

    def list_bucket_tree(self, bucket, prefix, recursive):
        self.called.append("read_bucket")
        return [SimpleNamespace(path=prefix + p, type="file")
                for p in sorted(self.files)]

    def inspect_job(self, job_id, namespace):
        self.called.append("inspect_job")
        return SimpleNamespace(id=job_id, status=SimpleNamespace(
            stage="ERROR", message="Job image specification error: docker.io/--name"))


def test_probe_checks_all_gates_without_submission(tmp_path):
    input_dir = fixture(tmp_path)
    out = tmp_path / retry.RUN_KEY
    stage.stage(input_dir, out, retry.RUN_KEY)
    api = MockApi(probe.guard.expected(out))
    result = probe.probe(api, out, retry.RUN_KEY, retry.OLD_JOB)
    assert result["status"] == "R60_CPU2_RETRY_READ_ONLY_PROBE_PASS"
    assert result["local_stage"] == "PASS"
    assert result["remote_ready"] == "PASS"
    assert result["old_job"] == "VERIFIED_IMAGE_ERROR"
    assert result["retry_marker"] == "ABSENT"
    assert result["job_submission_calls"] == 0
    assert api.called == ["read_bucket", "inspect_job"]
    (tmp_path / (retry.RUN_KEY + ".cpu-submit-image-fix-attempted")).mkdir()
    result = probe.probe(api, out, retry.RUN_KEY, retry.OLD_JOB)
    assert result["retry_marker"] == "PRESENT"
    assert result["reason_code"] == "RETRY_ATTEMPTED__CHECK_JOBS_BEFORE_ANY_ACTION"


def test_probe_rejects_unready_bucket_without_inspection(tmp_path):
    input_dir = fixture(tmp_path)
    out = tmp_path / retry.RUN_KEY
    stage.stage(input_dir, out, retry.RUN_KEY)
    api = MockApi({"SHA256SUMS.txt"})
    result = probe.probe(api, out, retry.RUN_KEY, retry.OLD_JOB)
    assert result["status"] == "R60_CPU2_RETRY_READ_ONLY_PROBE_HOLD"
    assert result["remote_ready"] == "NOT_CHECKED"
    assert result["reason_code"] == "REMOTE_RUN_FILESET_HOLD"
    assert api.called == ["read_bucket"]
