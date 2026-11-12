"""CPU2 legacy submission must fail closed; all inputs are synthetic."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import r60_common2_hf_cpu_image_retry as retry
from scripts import r60_common2_hf_cpu_stage as staging
from tests.test_r60_common2_hf_cpu_stage import fixture


class FakeApi:
    def __init__(self, stage):
        self.stage = stage
        self.calls = []

    def run_job(self, **kwargs):
        self.calls.append(kwargs)
        raise AssertionError("legacy must never submit")

    def inspect_job(self, *, job_id, namespace):
        self.calls.append(("inspect_job", job_id, namespace))
        return SimpleNamespace(id=job_id, status=SimpleNamespace(
            stage="ERROR", message="Job image specification error: docker.io/--name"))


def test_legacy_retry_refuses_unapproved_mount_policy_without_attempt_marker(tmp_path):
    inp = fixture(tmp_path)
    out = tmp_path / retry.RUN_KEY
    staging.stage(inp, out, retry.RUN_KEY)
    api = FakeApi(out)
    with pytest.raises(ValueError, match="LEGACY_SUBMISSION_MOUNT_POLICY_HOLD"):
        retry.submit_one(api, None, retry.RUN_KEY, out, retry.OLD_JOB)
    assert api.calls == []
    assert not (tmp_path / (retry.RUN_KEY + ".cpu-submit-image-fix-attempted")).exists()


def test_legacy_retry_still_rejects_wrong_frozen_key(tmp_path):
    api = FakeApi(tmp_path)
    with pytest.raises(ValueError, match="FROZEN_RUN_BINDING_HOLD"):
        retry.submit_one(api, None, "wrong", tmp_path / "wrong", retry.OLD_JOB)
    assert api.calls == []


@pytest.mark.parametrize("status,message", [
    ("RUNNING", "Job image specification error: docker.io/--name"),
    ("ERROR", "Different failure"),
    ("COMPLETED", "Docker image failed"),
])
def test_cannot_accept_unverified_old_failure(status, message):
    info = SimpleNamespace(id=retry.OLD_JOB,
        status=SimpleNamespace(stage=status, message=message))
    with pytest.raises(ValueError, match="OLD_IMAGE_ERROR_NOT_VERIFIED"):
        retry.validate_old_error(info)


def test_old_image_error_matching_status():
    info = SimpleNamespace(id=retry.OLD_JOB,
        status=SimpleNamespace(stage="ERROR",
                               message="Job image specification error: docker.io/--name"))
    retry.validate_old_error(info)
