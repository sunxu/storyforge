"""Synthetic read-only CPU2 contract checks; no HF calls."""
from __future__ import annotations

from types import SimpleNamespace

from scripts import r60_common2_hf_cpu_submission_contract as contract
from scripts import r60_common2_hf_cpu_image_retry as retry


def test_sdk_160_without_mount_contract_holds(tmp_path):
    class Hub160:
        def run_job(self, *, image, command, env=None, flavor=None,
                    timeout=None, labels=None, namespace=None, token=None):
            raise AssertionError("must never run")
    result = contract.check_contract(
        Hub160(), tmp_path / retry.RUN_KEY, retry.RUN_KEY,
        "BASE=/workspace/preflight/r60/common2/cpu2",
    )
    assert result["status"] == "CPU2_SUBMIT_CONTRACT_HOLD"
    assert result["reason_code"] == "SDK_MOUNT_API_UNAVAILABLE"
    assert result["sdk_mount_api_supported"] is False
    assert result["job_submission_calls"] == 0


def test_frozen_worker_requires_new_verified_artifact(tmp_path):
    class MountCapable:
        def run_job(self, *, image, command, volumes):
            raise AssertionError("must never run")
    result = contract.check_contract(
        MountCapable(), tmp_path / retry.RUN_KEY, retry.RUN_KEY,
        "BASE=/workspace/preflight/r60/common2/cpu2",
    )
    assert result["reason_code"] == "FROZEN_WORKER_MOUNT_CONTRACT_HOLD"
    assert result["job_submission_calls"] == 0


def test_policy_rejects_incorrect_binding_without_sdk_calls(tmp_path):
    class NoCalls:
        pass
    result = contract.check_contract(NoCalls(), tmp_path / "wrong", "wrong", "")
    assert result["reason_code"] == "FROZEN_BINDING_HOLD"
    assert result["job_submission_calls"] == 0


def test_shared_guard_keeps_input_ro_output_rw_disjoint():
    from scripts import hf_job_guard
    key = retry.RUN_KEY
    root = contract.ROOT
    inputs, output = hf_job_guard.validate_spec(
        namespace="adradar", flavor="cpu-upgrade", timeout_minutes=120,
        input_volumes=[f"{root}/runs/{key}:/input/common2:ro"],
        output_volume=f"{root}/results/{key}-fixed:/output:rw",
        command=["bash", "/input/common2/code/scripts/r60_common2_hf_cpu_worker.sh"],
    )
    assert all(i.mode == "ro" for i in inputs)
    assert output.mode == "rw"
    assert output.destination == "/output"
