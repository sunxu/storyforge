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
from importlib.metadata import PackageNotFoundError, version
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


def use_documented_default_attempts(help_text: str) -> bool:
    """Accept one old CLI omission only with known pinned local HF SDK.

    HF Jobs defaults to exactly one attempt when --attempts is absent.
    Never accept missing flags other than this one; keep the explicit
    --attempts=1 path when supported.
    """
    if missing_job_cli_flags(help_text) != ["--attempts"]:
        return False
    try:
        return version("huggingface_hub") == "1.33.0"
    except PackageNotFoundError:
        return False


def missing_job_cli_flags(help_text: str) -> list[str]:
    """Return only known public option names; never emit complete CLI help."""
    missing = hf_job_guard.missing_hf_cli_options(help_text)
    # Existing verified CPU2 supports HF's exact short -v alias.
    if re.search(r"(?<![A-Za-z0-9_-])-v(?![A-Za-z0-9_-])", help_text):
        missing = [flag for flag in missing if flag != "--volume"]
    # The runner uses --env and --dry-run; both must be documented.
    for option in ("--env", "--dry-run"):
        if re.search(
            r"(?<![A-Za-z0-9_-])" + re.escape(option) + r"(?![A-Za-z0-9_-])",
            help_text,
        ) is None:
            missing.append(option)
    return sorted(set(missing))


def inspect_job_cli_flags() -> dict:
    """Read-only local HF CLI inspection, no token, remote access or submission."""
    result = safe("WRAPPED_CPU_CLI_FLAGS_HOLD__NO_JOB", "CLI_HELP_UNAVAILABLE")
    result["missing_cli_flags"] = []
    try:
        probe = subprocess.run(
            ["hf", "jobs", "run", "--help"],
            capture_output=True, text=True, timeout=20, check=False,
        )
        if probe.returncode:
            return result
        missing = missing_job_cli_flags(probe.stdout)
        default_attempts = use_documented_default_attempts(probe.stdout)
        result["missing_cli_flags"] = [] if default_attempts else missing
        result["attempts_mode"] = (
            "PINNED_CLI_DEFAULT_ONE" if default_attempts
            else "EXPLICIT_ONE" if not missing else "UNVERIFIED"
        )
        result["status"] = (
            "WRAPPED_CPU_CLI_FLAGS_PASS__NO_JOB" if not missing or default_attempts
            else "WRAPPED_CPU_CLI_FLAGS_HOLD__NO_JOB"
        )
        result["reason_code"] = (
            "DOCUMENTED_DEFAULT_ONE" if default_attempts
            else "REQUIRED_OPTIONS_PRESENT" if not missing
            else "MISSING_REQUIRED_OPTIONS"
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def job_command(key: str, help_text: str) -> list[str]:
    missing = missing_job_cli_flags(help_text)
    default_attempts = use_documented_default_attempts(help_text)
    if missing and not default_attempts:
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
    if default_attempts:
        # Shared builder remains unchanged for all other pipelines.
        # HF documented default is 1; the pinned CLI does not expose flag.
        index = argv.index("--attempts")
        if argv[index + 1] != "1":
            raise ValueError("HF_CLI_FLAGS_HOLD")
        del argv[index:index + 2]
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


def diagnose(stage: Path, key: str) -> dict:
    """Read-only remote state. Never uploads, creates a job or emits remote paths."""
    out = safe("WRAPPED_CPU_REMOTE_DIAGNOSTIC_HOLD", "NOT_CHECKED")
    out.update(phase="STAGE_VERIFY", remote_input="UNKNOWN",
               remote_output="UNKNOWN", submit_marker="UNKNOWN")
    try:
        if not stage_tool.RUN_RE.fullmatch(key) or stage.name != key:
            raise ValueError("RUN_KEY_HOLD")
        # This is read-only. A previously verified stage that now fails is
        # never silently repaired, restaged, overwritten or uploaded.
        expected_files = expected(stage, key)
        out["phase"] = "SDK_IMPORT"
        from huggingface_hub import HfApi
        api = HfApi()
        out["phase"] = "REMOTE_INPUT_LIST"
        found = remote_set(api, f"{PREFIX}/runs/{key}/")
        out["remote_input"] = (
            "EMPTY" if not found else
            "READY_FILESET" if found == expected_files else "PARTIAL_OR_MISMATCH"
        )
        out["phase"] = "REMOTE_OUTPUT_LIST"
        outputs = remote_set(api, f"{PREFIX}/results/{key}/")
        out["remote_output"] = "EMPTY" if not outputs else "NONEMPTY"
        out["phase"] = "MARKER_CHECK"
        marker = stage.parent / (key + ".wrapped-cpu-attempted")
        out["submit_marker"] = "PRESENT" if marker.exists() or marker.is_symlink() else "ABSENT"
        out.update(status="WRAPPED_CPU_REMOTE_DIAGNOSTIC_PASS__NO_JOB",
                   reason_code="READ_ONLY_INSPECTION", phase="COMPLETE")
    except Exception as exc:  # noqa: BLE001 - never expose remote/private exception text
        if out["phase"] == "STAGE_VERIFY":
            # Before SDK_IMPORT this is a local failure. Never report a
            # fabricated remote SDK/service cause for arbitrary local errors.
            reason = classify_safe_failure(exc)
            stage_codes = {
                "RUN_KEY_HOLD", "STAGE_DIR_HOLD", "STAGE_MANIFEST_HOLD",
                "STAGE_FILES_HOLD", "STAGE_HASH_SCHEMA_HOLD",
                "STAGE_PATH_HOLD", "STAGE_CONTRACT_HOLD",
                "INPUT_SYMLINK_REJECTED", "INPUT_OPEN_FAILED",
                "INPUT_NOT_REGULAR_FILE", "INPUT_SIZE_LIMIT_EXCEEDED",
                "INPUT_DESCRIPTOR_CHANGED", "INPUT_SHA256_MISMATCH",
                "INPUT_READ_FAILED", "INPUT_JSON_INVALID",
            }
            out["reason_code"] = (
                reason if reason in stage_codes else "STAGE_INPUT_OR_RUNTIME_HOLD"
            )
        else:
            out["reason_code"] = classify_safe_failure(exc)
    return out


def classify_safe_failure(exc: Exception) -> str:
    """Use the existing HF CPU2 classifier without leaking exception messages."""
    allowed = {
        "RUN_KEY_HOLD", "REMOTE_PATH_HOLD", "REMOTE_LIST_HOLD",
        "REMOTE_STAGE_FILESET_HOLD", "REMOTE_STAGE_ALREADY_EXISTS_HOLD",
        "REMOTE_RESULT_ALREADY_EXISTS_HOLD", "REMOTE_UPLOAD_INCOMPLETE_HOLD",
        "REMOTE_MANIFEST_UPLOAD_HOLD", "JOB_ATTEMPT_ALREADY_RECORDED_HOLD",
        "EXISTING_JOB_HOLD", "HF_CLI_HELP_HOLD", "HF_CLI_FLAGS_HOLD",
        "HF_CLI_DRY_RUN_HOLD", "HF_AUTH_HOLD", "EXPLICIT_EXECUTE_REQUIRED",
    }
    # Stage and shared InputManager failures must be distinguishable from
    # remote SDK faults. These labels are fixed public codes, never file text.
    allowed.update({
        "STAGE_DIR_HOLD", "STAGE_MANIFEST_HOLD", "STAGE_FILES_HOLD",
        "STAGE_HASH_SCHEMA_HOLD", "STAGE_PATH_HOLD", "STAGE_CONTRACT_HOLD",
        "INPUT_SYMLINK_REJECTED", "INPUT_OPEN_FAILED", "INPUT_NOT_REGULAR_FILE",
        "INPUT_SIZE_LIMIT_EXCEEDED", "INPUT_DESCRIPTOR_CHANGED",
        "INPUT_SHA256_MISMATCH", "INPUT_READ_FAILED", "INPUT_JSON_INVALID",
    })
    if type(exc) is ValueError and str(exc) in allowed:
        return str(exc)
    from r60_common2_hf_cpu_bucket_guard import classify_failure
    code = classify_failure(exc)
    if code in {
        "SDK_MODULE_MISSING", "SDK_API_UNAVAILABLE", "SDK_API_INCOMPATIBLE",
        "REMOTE_AUTHORIZATION_HOLD", "REMOTE_BUCKET_OR_PATH_NOT_FOUND_HOLD",
        "REMOTE_RATE_LIMIT_HOLD", "REMOTE_SERVICE_5XX_HOLD",
        "REMOTE_TIMEOUT_HOLD", "REMOTE_CONNECTION_HOLD",
        "REMOTE_SDK_OR_SERVICE_HOLD",
    }:
        return code
    return "SDK_OR_RUNTIME_HOLD"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "action", choices=["preflight", "sync", "ready", "submit", "diagnose", "cli-flags"],
    )
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--run-key", required=True)
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    try:
        out = (inspect_job_cli_flags() if a.action == "cli-flags"
               else diagnose(a.stage, a.run_key) if a.action == "diagnose"
               else execute(a.action, a.stage, a.run_key, a.execute))
    except Exception as exc:  # noqa: BLE001 - fail closed, never leak private errors
        out = safe("WRAPPED_CPU_ORCHESTRATION_HOLD", classify_safe_failure(exc))
    print(json.dumps(out, sort_keys=True))
    return 0 if out["status"] in {
        "WRAPPED_CPU_LOCAL_STAGE_PASS__NO_JOB",
        "WRAPPED_CPU_REMOTE_STAGE_READY__NO_JOB",
        "WRAPPED_CPU_REMOTE_AND_CLI_READY__NO_JOB",
        "WRAPPED_CPU_JOB_SUBMITTED__TRAIN_HOLD",
        "WRAPPED_CPU_REMOTE_DIAGNOSTIC_PASS__NO_JOB",
        "WRAPPED_CPU_CLI_FLAGS_PASS__NO_JOB",
    } else 42


if __name__ == "__main__":
    raise SystemExit(main())
