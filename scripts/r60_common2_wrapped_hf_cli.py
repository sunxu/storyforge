"""Mac HF CLI orchestration for R60 Common2 wrapped CPU quality gate.

Subcommands: preflight, sync, ready, submit. Only 'submit --execute' can
create a CPU job. No fallback/retry and no GPU. Reuses shared hf_job_guard.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import hf_job_guard
import r60_common2_wrapped_hf_stage as stage_tool

BUCKET = "adradar/storyforge-training"
PREFIX = "preflight/r60/common2/wrapped-cpu"
IMAGE = "pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"
WORKER = "/input/common2/scripts/r60_common2_wrapped_hf_worker.sh"
SCHEMA = "storyforge_r60_common2_wrapped_hf_cli_safe_v1"


def safe(status: str, reason: str) -> dict:
    return {"schema": SCHEMA, "status": status, "reason_code": reason,
            "train_admitted": 0, "gpu_started": False,
            "private_values_emitted": False, "job_submission_calls": 0}


def remote_set(api, prefix: str) -> set[str]:
    values = set()
    for entry in api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True):
        path = getattr(entry, "path", "")
        if not isinstance(path, str) or not path.startswith(prefix):
            raise ValueError("REMOTE_PATH_HOLD")
        if getattr(entry, "type", "") == "directory":
            continue
        item = path[len(prefix):]
        if not item or item in values or ".." in Path(item).parts:
            raise ValueError("REMOTE_LIST_HOLD")
        values.add(item)
    return values


def expected(stage: Path, key: str) -> set[str]:
    stage_tool.verify(stage, key)
    # Verified stage includes the private manifest and every imported code file.
    return {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}


def remote_check(stage: Path, key: str, *, ready: bool, api) -> None:
    prefix = f"{PREFIX}/runs/{key}/"
    found = remote_set(api, prefix)
    if ready:
        if found != expected(stage, key):
            raise ValueError("REMOTE_STAGE_FILESET_HOLD")
    elif found:
        raise ValueError("REMOTE_STAGE_ALREADY_EXISTS_HOLD")


def output_is_empty(api, key: str) -> None:
    if remote_set(api, f"{PREFIX}/results/{key}/"):
        raise ValueError("REMOTE_RESULT_ALREADY_EXISTS_HOLD")


def job_command(key: str, help_text: str) -> list[str]:
    missing = hf_job_guard.missing_hf_cli_options(help_text)
    if re.search(r"(?<![A-Za-z0-9_-])-v(?![A-Za-z0-9_-])", help_text):
        missing = [x for x in missing if x != "--volume"]
    if missing or "--dry-run" not in help_text:
        raise ValueError("HF_CLI_FLAGS_HOLD")
    base = "hf://buckets/" + BUCKET
    inputs = [f"{base}/{PREFIX}/runs/{key}:/input/common2:ro"]
    output = f"{base}/{PREFIX}/results/{key}:/output:rw"
    command = ["bash", WORKER]
    hf_job_guard.validate_spec(
        namespace="adradar", flavor="cpu-upgrade", timeout_minutes=120,
        input_volumes=inputs, output_volume=output, command=command
    )
    argv = hf_job_guard.build_hf_argv(
        namespace="adradar", name=f"r60-wrapcpu-{key}",
        flavor="cpu-upgrade", timeout_minutes=120,
        input_volumes=inputs, output_volume=output,
        image=IMAGE, command=command
    )
    pos = argv.index(IMAGE)
    argv[pos:pos] = ["--env", f"STORYFORGE_R60_WRAPCPU_KEY={key}"]
    pos = argv.index(IMAGE)
    if argv[pos + 1:pos + 2] == ["--"]:
        argv.pop(pos + 1)  # HF CLI 2.4.0 IMAGE COMMAND ... syntax
    return argv


def execute(action: str, stage: Path, key: str, allow_submit: bool) -> dict:
    if not stage_tool.RUN_RE.fullmatch(key) or stage.name != key:
        raise ValueError("RUN_KEY_HOLD")
    expected(stage, key)
    if action == "preflight":
        return safe("WRAPPED_CPU_LOCAL_STAGE_PASS__NO_JOB", "LOCAL_SHA_VERIFIED")
    from huggingface_hub import HfApi
    api = HfApi()
    marker = stage.parent / (key + ".wrapped-cpu-attempted")
    if action == "sync":
        remote_check(stage, key, ready=False, api=api)
        output_is_empty(api, key)
        base = "hf://buckets/" + BUCKET + "/" + PREFIX + "/runs/" + key
        # One shot per key. No automatic retries on an incomplete stage.
        for name in sorted(expected(stage, key) - {"SHA256_MANIFEST_PRIVATE.json"}):
            result = subprocess.run(
                ["hf", "buckets", "cp", str(stage / name), base + "/" + name],
                capture_output=True, text=True, timeout=90, check=False
            )
            if result.returncode:
                raise ValueError("REMOTE_UPLOAD_INCOMPLETE_HOLD")
        manifest = "SHA256_MANIFEST_PRIVATE.json"
        result = subprocess.run(
            ["hf", "buckets", "cp", str(stage / manifest), base + "/" + manifest],
            capture_output=True, text=True, timeout=90, check=False
        )
        if result.returncode:
            raise ValueError("REMOTE_MANIFEST_UPLOAD_HOLD")
        remote_check(stage, key, ready=True, api=api)
        return safe("WRAPPED_CPU_REMOTE_STAGE_READY__NO_JOB", "REMOTE_FILESET_MATCH")
    remote_check(stage, key, ready=True, api=api)
    output_is_empty(api, key)
    if marker.exists() or marker.is_symlink():
        raise ValueError("JOB_ATTEMPT_ALREADY_RECORDED_HOLD")
    # The only no-existing-job check reuses the exhaustive pagination helper
    # from the already-tested Common2 CPU2 pipeline.
    from r60_common2_hf_cpu_final_read_only import walk_job_history
    _, matching = walk_job_history(api, key)
    if matching:
        raise ValueError("EXISTING_JOB_HOLD")
    helper = subprocess.run(["hf", "jobs", "run", "--help"],
                            capture_output=True, text=True, timeout=20, check=False)
    if helper.returncode:
        raise ValueError("HF_CLI_HELP_HOLD")
    argv = job_command(key, helper.stdout)
    if action == "ready":
        argv.insert(argv.index(IMAGE), "--dry-run")
        result = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
        if (result.returncode != 0 or
            not any(s in (result.stdout + result.stderr).lower()
                    for s in ("dry-run", "dry run"))):
            raise ValueError("HF_CLI_DRY_RUN_HOLD")
        return safe("WRAPPED_CPU_REMOTE_AND_CLI_READY__NO_JOB", "PAGINATED_NO_JOB")
    if action != "submit" or not allow_submit:
        raise ValueError("EXPLICIT_EXECUTE_REQUIRED")
    argv.insert(argv.index(IMAGE), "--dry-run")
    trial = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
    if (trial.returncode or
        not any(s in (trial.stdout + trial.stderr).lower()
                for s in ("dry-run", "dry run"))):
        raise ValueError("HF_CLI_DRY_RUN_HOLD")
    auth = subprocess.run(["hf", "auth", "whoami"], capture_output=True, text=True, timeout=20, check=False)
    if auth.returncode:
        raise ValueError("HF_AUTH_HOLD")
    argv.remove("--dry-run")
    # O_EXCL marker BEFORE the single potentially billable submission.
    fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps({"run_key": key, "status": "ATTEMPTED_DO_NOT_RETRY"}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return safe("WRAPPED_CPU_JOB_SUBMISSION_UNCONFIRMED", "CHECK_ORG_HISTORY_NO_RETRY")
    if result.returncode:
        return safe("WRAPPED_CPU_JOB_SUBMISSION_UNCONFIRMED", "CHECK_ORG_HISTORY_NO_RETRY")
    ids = set(re.findall(r"(?<![a-f0-9])[a-f0-9]{24}(?![a-f0-9])",
                         result.stdout + result.stderr))
    if len(ids) != 1:
        return safe("WRAPPED_CPU_JOB_SUBMISSION_UNCONFIRMED", "JOB_ID_UNCONFIRMED_NO_RETRY")
    report = safe("WRAPPED_CPU_JOB_SUBMITTED__TRAIN_HOLD", "ONE_CPU_JOB")
    report["job_id"] = ids.pop()
    report["job_submission_calls"] = 1
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["preflight", "sync", "ready", "submit"])
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--run-key", required=True)
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    try:
        out = execute(a.action, a.stage, a.run_key, a.execute)
    except Exception as exc:  # noqa: BLE001 - fail closed, never leak private errors
        codes = {
            "RUN_KEY_HOLD", "REMOTE_STAGE_FILESET_HOLD", "REMOTE_STAGE_ALREADY_EXISTS_HOLD",
            "REMOTE_RESULT_ALREADY_EXISTS_HOLD", "REMOTE_UPLOAD_INCOMPLETE_HOLD",
            "REMOTE_MANIFEST_UPLOAD_HOLD", "JOB_ATTEMPT_ALREADY_RECORDED_HOLD",
            "EXISTING_JOB_HOLD", "HF_CLI_HELP_HOLD", "HF_CLI_FLAGS_HOLD",
            "HF_CLI_DRY_RUN_HOLD", "HF_AUTH_HOLD", "EXPLICIT_EXECUTE_REQUIRED",
        }
        out = safe("WRAPPED_CPU_ORCHESTRATION_HOLD",
                   str(exc) if type(exc) is ValueError and str(exc) in codes
                   else "SDK_OR_RUNTIME_HOLD")
    print(json.dumps(out, sort_keys=True))
    return 0 if out["status"] in {
        "WRAPPED_CPU_LOCAL_STAGE_PASS__NO_JOB",
        "WRAPPED_CPU_REMOTE_STAGE_READY__NO_JOB",
        "WRAPPED_CPU_REMOTE_AND_CLI_READY__NO_JOB",
        "WRAPPED_CPU_JOB_SUBMITTED__TRAIN_HOLD",
    } else 42


if __name__ == "__main__":
    raise SystemExit(main())
