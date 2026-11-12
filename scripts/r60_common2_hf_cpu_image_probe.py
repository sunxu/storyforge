"""Read-only, SAFE phase probe for a failed R60 Common2 HF CPU image retry.

No Job submission, stage mutation, deletion, network writes or private text output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from scripts import r60_common2_hf_cpu_bucket_guard as guard
from scripts import r60_common2_hf_cpu_image_retry as retry


def check_local(stage: Path, key: str) -> None:
    if stage.name != key or not stage.is_dir() or stage.is_symlink():
        raise ValueError("LOCAL_STAGE_PATH_HOLD")
    expected = guard.expected(stage)
    lines = (stage / "SHA256SUMS.txt").read_text().splitlines()
    if len(lines) + 1 != len(expected):
        raise ValueError("LOCAL_FILESET_HOLD")
    for line in lines:
        digest, sep, name = line.partition("  ")
        if not sep or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("LOCAL_MANIFEST_HOLD")
        f = stage / name
        if not f.is_file() or f.is_symlink():
            raise ValueError("LOCAL_FILE_HOLD")
        if hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            raise ValueError("LOCAL_HASH_HOLD")


def probe(api, stage: Path, key: str, old_job: str) -> dict:
    result = {"schema": "storyforge_r60_cpu2_retry_probe_safe_v1",
              "status": "R60_CPU2_RETRY_READ_ONLY_PROBE_HOLD",
              "local_stage": "NOT_CHECKED", "remote_ready": "NOT_CHECKED",
              "old_job": "NOT_CHECKED", "retry_marker": "NOT_CHECKED",
              "job_submission_calls": 0, "train_admitted": 0,
              "private_values_emitted": False}
    if key != retry.RUN_KEY or old_job != retry.OLD_JOB:
        result["reason_code"] = "FROZEN_BINDING_HOLD"
        return result
    try:
        check_local(stage, key)
        result["local_stage"] = "PASS"
    except Exception:  # noqa: BLE001 - do not expose private file details
        result["reason_code"] = "LOCAL_STAGE_HOLD"
        return result
    try:
        guard.check("ready", key, stage, api)
        result["remote_ready"] = "PASS"
    except Exception as exc:  # noqa: BLE001 - categorized, no exception string
        result["reason_code"] = guard.classify_failure(exc)
        return result
    try:
        retry.validate_old_error(api.inspect_job(old_job, namespace="adradar"))
        result["old_job"] = "VERIFIED_IMAGE_ERROR"
    except Exception as exc:  # noqa: BLE001 - categorized without source text
        result["reason_code"] = (
            "OLD_IMAGE_ERROR_NOT_VERIFIED"
            if isinstance(exc, ValueError)
            else guard.classify_failure(exc))
        return result
    marker = stage.parent / (key + ".cpu-submit-image-fix-attempted")
    result["retry_marker"] = "PRESENT" if marker.exists() else "ABSENT"
    result["status"] = "R60_CPU2_RETRY_READ_ONLY_PROBE_PASS"
    if marker.exists():
        result["reason_code"] = "RETRY_ATTEMPTED__CHECK_JOBS_BEFORE_ANY_ACTION"
    else:
        result["reason_code"] = "PRE_SUBMISSION_FAILURE_POSSIBLE"
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-key", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--old-job", required=True)
    a = p.parse_args()
    try:
        from huggingface_hub import HfApi
        result = probe(HfApi(), a.stage, a.run_key, a.old_job)
    except Exception as exc:  # noqa: BLE001
        result = {"schema": "storyforge_r60_cpu2_retry_probe_safe_v1",
                  "status": "R60_CPU2_RETRY_READ_ONLY_PROBE_HOLD",
                  "reason_code": guard.classify_failure(exc),
                  "job_submission_calls": 0, "train_admitted": 0,
                  "private_values_emitted": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"].endswith("_PASS") else 42


if __name__ == "__main__":
    raise SystemExit(main())
