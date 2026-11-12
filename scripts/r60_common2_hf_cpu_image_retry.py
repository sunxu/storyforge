"""Retry R60 Common2 once via typed HF SDK after *verified* old image-spec ERROR.

No CLI argument parsing, no restage, no model training, no GPU, no auto retry.
All public output is SAFE, never print private data, token or traceback.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts import r60_common2_hf_cpu_bucket_guard as guard
except ModuleNotFoundError:
    import r60_common2_hf_cpu_bucket_guard as guard

RUN_KEY = "r60-common2-cpu2-20261112T032815Z-71c840b37254"
OLD_JOB = "6af53990ab34849891aecb44"
IMAGE = "pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime"


def validate_old_error(info) -> None:
    status = getattr(info, "status", None)
    stage = getattr(status, "stage", None)
    message = getattr(status, "message", None)
    # The *same* failed job must have a terminal Docker-image argument error.
    if (getattr(info, "id", None) != OLD_JOB
            or str(stage).upper() != "ERROR"
            or not isinstance(message, str)
            or "Job image specification error" not in message
            or "docker.io/--name" not in message):
        raise ValueError("OLD_IMAGE_ERROR_NOT_VERIFIED")


def submit_one(api, volume_class, key: str, stage: Path, old_job: str):
    """Legacy API intentionally disabled until guarded RO/RW mounting is supported.

    The original 1.6.0 run_job signature does not accept volumes/name.  The
    frozen worker expects a whole-bucket writable /workspace mount, violating
    AGENTS.md and the shared hf_job_guard.validate_spec contract.  Do not
    create an attempt marker or call run_job from this legacy entrypoint.
    """
    if key != RUN_KEY or old_job != OLD_JOB or stage.name != key:
        raise ValueError("FROZEN_RUN_BINDING_HOLD")
    raise ValueError("LEGACY_SUBMISSION_MOUNT_POLICY_HOLD")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-key", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--old-job", required=True)
    args = p.parse_args()
    try:
        from huggingface_hub import HfApi
        new_id = submit_one(HfApi(), None, args.run_key, args.stage, args.old_job)
        print(json.dumps({
            "status": "R60_COMMON2_CPU2_IMAGE_FIX_JOB_SUBMITTED",
            "job_id": new_id, "gpu_started": False,
            "train_admitted": 0, "private_values_emitted": False,
        }, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never leak private or token details
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) in {
            "OLD_IMAGE_ERROR_NOT_VERIFIED", "FROZEN_RUN_BINDING_HOLD",
            "PRIVATE_STAGE_MODE_HOLD", "STAGE_MANIFEST_UNSAFE",
            "STAGE_SOURCE_SHA_HOLD", "NEW_JOB_ID_MISSING",
            "LEGACY_SUBMISSION_MOUNT_POLICY_HOLD",
        } else "SAFE_REMOTE_OR_RUNTIME_HOLD"
        if isinstance(exc, FileExistsError):
            reason = "RETRY_ALREADY_ATTEMPTED"
        print(json.dumps({"status": "R60_COMMON2_CPU2_IMAGE_FIX_HOLD",
                          "reason_code": reason, "train_admitted": 0,
                          "private_values_emitted": False}, sort_keys=True),
              file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
