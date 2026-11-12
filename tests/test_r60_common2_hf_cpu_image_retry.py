"""Pure-synthetic test for typed SDK CPU retry after exact image error."""
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
        self.stage_value = "ERROR"
        self.message = "Job image specification error: Invalid image name: docker.io/--name"

    def list_bucket_tree(self, bucket, prefix, recursive):
        assert bucket == "adradar/storyforge-training"
        return [SimpleNamespace(path=prefix + p, type="file")
                for p in sorted(retry.guard.expected(self.stage))]

    def inspect_job(self, job_id, namespace):
        assert namespace == "adradar"
        return SimpleNamespace(id=job_id, status=SimpleNamespace(
            stage=self.stage_value, message=self.message))

    def run_job(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(id="0123456789abcdef01234567")


def fake_volume(**kw):
    return kw


def test_typed_submission_fixes_image_and_stays_cpu_only(tmp_path):
    inp = fixture(tmp_path)
    stage = tmp_path / retry.RUN_KEY
    staging.stage(inp, stage, retry.RUN_KEY)
    api = FakeApi(stage)
    job_id = retry.submit_one(api, fake_volume, retry.RUN_KEY, stage, retry.OLD_JOB)
    assert job_id == "0123456789abcdef01234567"
    assert len(api.calls) == 1
    call = api.calls[0]
    assert call["image"] == retry.IMAGE
    assert call["flavor"] == "cpu-upgrade"
    assert call["command"][0] == "bash"
    assert call["volumes"][0]["source"] == "adradar/storyforge-training"
    assert call["volumes"][0]["read_only"] is False
    assert call["env"]["STORYFORGE_R60_COMMON2_RUN_KEY"] == retry.RUN_KEY
    assert (tmp_path / (retry.RUN_KEY + ".cpu-submit-image-fix-attempted")).is_dir()
    with pytest.raises(FileExistsError):
        retry.submit_one(api, fake_volume, retry.RUN_KEY, stage, retry.OLD_JOB)
    assert len(api.calls) == 1


@pytest.mark.parametrize("status,message", [
    ("RUNNING", "Job image specification error: docker.io/--name"),
    ("ERROR", "Different failure"),
    ("COMPLETED", "Docker image failed"),
])
def test_cannot_retry_unverified_failure(tmp_path, status, message):
    inp = fixture(tmp_path)
    stage = tmp_path / retry.RUN_KEY
    staging.stage(inp, stage, retry.RUN_KEY)
    api = FakeApi(stage)
    api.stage_value = status
    api.message = message
    with pytest.raises(ValueError, match="OLD_IMAGE_ERROR_NOT_VERIFIED"):
        retry.submit_one(api, fake_volume, retry.RUN_KEY, stage, retry.OLD_JOB)
    assert not api.calls
