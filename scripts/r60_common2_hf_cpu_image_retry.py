"""Retry R60 Common2 once via typed HF SDK after *verified* old image-spec ERROR.

No CLI argument parsing, no restage, no model training, no GPU, no auto retry.
All public output is SAFE, never print private data, token or traceback.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
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
    if key != RUN_KEY or old_job != OLD_JOB or stage.name != key:
        raise ValueError("FROZEN_RUN_BINDING_HOLD")
    if (stage.is_symlink() or not stage.is_dir()
            or stat.S_IMODE(stage.stat().st_mode) & 0o077):
        raise ValueError("PRIVATE_STAGE_MODE_HOLD")
    guard.check("ready", key, stage, api)
    from hashlib import sha256
    # Verify every original staged byte before submitting.
    for line in (stage / "SHA256SUMS.txt").read_text().splitlines():
        digest, sep, rel = line.partition("  ")
        if (not sep or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or not rel.startswith(("code/", "private_stage/"))
                or ".." in Path(rel).parts):
            raise ValueError("STAGE_MANIFEST_UNSAFE")
        file = stage / rel
        if file.is_symlink() or not file.is_file() or sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError("STAGE_SOURCE_SHA_HOLD")
    validate_old_error(api.inspect_job(old_job, namespace="adradar"))
    # Atomic persistent attempt marker; do not delete even after a network error.
    attempt = stage.parent / (key + ".cpu-submit-image-fix-attempted")
    attempt.mkdir(mode=0o700)
    job = api.run_job(
        image=IMAGE,
        command=["bash", f"/workspace/preflight/r60/common2/cpu2/runs/{key}/code/scripts/r60_common2_hf_cpu_worker.sh"],
        namespace="adradar",
        name="storyforge-r60-common2-cpu2-image-fixed-no-train",
        flavor="cpu-upgrade",
        timeout="120m",
        env={"STORYFORGE_R60_COMMON2_RUN_KEY": key},
        volumes=[volume_class(type="bucket", source="adradar/storyforge-training", mount_path="/workspace", read_only=False)],
    )
    job_id = getattr(job, "id", None)
    if not isinstance(job_id, str) or not re.fullmatch(r"[a-f0-9]{24}", job_id):
        raise ValueError("NEW_JOB_ID_MISSING")
    return job_id


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-key", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--old-job", required=True)
    args = p.parse_args()
    try:
        from huggingface_hub import HfApi, Volume
        new_id = submit_one(HfApi(), Volume, args.run_key, args.stage, args.old_job)
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
