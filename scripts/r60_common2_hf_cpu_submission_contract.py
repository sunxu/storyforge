"""Read-only CPU2 submission contract preflight; no Hub submission or bucket writes.

Reuse the shared HF job guard for mount and resource policy.  This preflight
does not permit bypassing the frozen old worker's /workspace RW mount.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

try:
    from scripts import hf_job_guard
    from scripts import r60_common2_hf_cpu_image_retry as retry
    from scripts import r60_common2_hf_cpu_stage as stage_contract
    from scripts import r60_common2_hf_cpu_image_probe as probe
except ModuleNotFoundError:
    import hf_job_guard
    import r60_common2_hf_cpu_image_retry as retry
    import r60_common2_hf_cpu_stage as stage_contract
    import r60_common2_hf_cpu_image_probe as probe

ROOT = "hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2"


def check_contract(api, stage: Path, key: str, worker_source: str) -> dict:
    report = {
        "schema": "storyforge_r60_cpu2_submit_contract_safe_v1",
        "status": "CPU2_SUBMIT_CONTRACT_HOLD",
        "reason_code": "UNVERIFIED_CONTRACT",
        "job_submission_calls": 0,
        "gpu_started": False,
        "train_admitted": 0,
        "private_values_emitted": False,
    }
    if (not stage_contract.RUN_KEY.fullmatch(key)
            or key == retry.RUN_KEY or stage.name != key):
        report["reason_code"] = "FROZEN_BINDING_HOLD"
        return report

    # Source and destination prefixes are disjoint; never whole-bucket RW.
    inputs = [f"{ROOT}/runs/{key}:/input/common2:ro"]
    output = f"{ROOT}/results/{key}-fixed:/output:rw"
    try:
        hf_job_guard.validate_spec(
            namespace="adradar", flavor="cpu-upgrade",
            timeout_minutes=120, input_volumes=inputs,
            output_volume=output, command=["bash", "/input/common2/code/scripts/r60_common2_hf_cpu_worker_v2.sh"],
        )
    except hf_job_guard.PolicyError:
        report["reason_code"] = "SHARED_GUARD_HOLD"
        return report

    # The SDK must actually support mounting RO inputs and RW outputs.
    try:
        signature = inspect.signature(api.run_job)
        params = signature.parameters
        accepts_mounts = "volumes" in params or "mounts" in params
    except (AttributeError, TypeError, ValueError):
        accepts_mounts = False
    report["sdk_mount_api_supported"] = accepts_mounts
    if not accepts_mounts:
        report["reason_code"] = "SDK_MOUNT_API_UNAVAILABLE"
        return report

    # A legacy worker that still reads/writes /workspace must be
    # published as a new SHA-verified artifact before any compliant job.
    if ("/workspace" in worker_source or 'ROOT="/input/common2"' not in worker_source
            or 'OUT="/output"' not in worker_source
            or "os.O_EXCL" not in worker_source):
        report["reason_code"] = "FROZEN_WORKER_MOUNT_CONTRACT_HOLD"
        return report
    report["status"] = "CPU2_SUBMIT_CONTRACT_PREFLIGHT_PASS__NO_JOB"
    report["reason_code"] = "NO_SUBMISSION"
    return report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    try:
        from huggingface_hub import HfApi
        probe.check_local(args.stage, args.run_key)
        worker = args.stage / "code/scripts/r60_common2_hf_cpu_worker_v2.sh"
        if not worker.is_file() or worker.is_symlink():
            raise ValueError("FROZEN_WORKER_MISSING")
        result = check_contract(HfApi(), args.stage, args.run_key, worker.read_text())
    except Exception:
        result = {
            "schema": "storyforge_r60_cpu2_submit_contract_safe_v1",
            "status": "CPU2_SUBMIT_CONTRACT_HOLD",
            "reason_code": "SAFE_LOCAL_RUNTIME_HOLD",
            "job_submission_calls": 0,
            "gpu_started": False,
            "train_admitted": 0,
            "private_values_emitted": False,
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"].startswith("CPU2_SUBMIT_CONTRACT_PREFLIGHT_PASS") else 42


if __name__ == "__main__":
    raise SystemExit(main())
