"""Mac-side R60 Base336 HF GPU sync/READY/dry-run. There is deliberately no submit action."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import hf_job_guard
import r60_base336_gpu_contract as contract
import r60_base336_gpu_stage as stage_tool
import r60_common2_wrapped_hf_cli as shared_cli

BUCKET = contract.HF_BUCKET
STAGE_PREFIX = contract.HF_STAGE_PREFIX
RESULT_PREFIX = contract.HF_RESULT_PREFIX
SUBMISSION_PREFIX = contract.HF_SUBMISSION_PREFIX
IMAGE = contract.HF_IMAGE
WORKER = "/input/r60-base336/scripts/r60_base336_gpu_worker.sh"
GPU_SCOPE = contract.GPU_SCOPE
SCHEMA = "storyforge_r60_base336_gpu_cli_safe_v1"


def safe(status: str, reason: str) -> dict:
    return {
        "schema": SCHEMA,
        "status": status,
        "reason_code": reason,
        "run_key_validated": False,
        "remote_file_sha_verified": False,
        "job_history_exhaustive": False,
        "job_submission_calls": 0,
        "hf_jobs_submitted": 0,
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def _remote_set(api, prefix: str) -> set[str]:
    return shared_cli.remote_set(api, prefix)


def _local_files(stage: Path, key: str) -> dict[str, str]:
    stage_tool.verify(stage, key)
    manifest = contract.read_json(stage / "SHA256_MANIFEST_PRIVATE.json")
    if manifest.get("git_commit") != stage_tool._git_commit():
        raise ValueError("STAGE_GIT_HEAD_DRIFT_HOLD")
    files = dict(manifest["files"])
    files["SHA256_MANIFEST_PRIVATE.json"] = hashlib.sha256(
        (stage / "SHA256_MANIFEST_PRIVATE.json").read_bytes()
    ).hexdigest()
    return files


def _remote_prefix(key: str) -> str:
    return f"{STAGE_PREFIX}/{key}/"


def _remote_uri(prefix: str, relative: str) -> str:
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("REMOTE_PATH_HOLD")
    return f"hf://buckets/{BUCKET}/{prefix}{relative}"


def _check_remote_set(api, stage: Path, key: str, *, ready: bool) -> dict[str, str]:
    expected = _local_files(stage, key)
    found = _remote_set(api, _remote_prefix(key))
    if not ready:
        if found:
            raise ValueError("REMOTE_STAGE_ALREADY_EXISTS_HOLD")
        return expected
    if found != set(expected):
        raise ValueError("REMOTE_STAGE_FILESET_HOLD")
    return expected


def _verify_remote_sha(stage: Path, key: str, expected: dict[str, str]) -> None:
    base = _remote_prefix(key)
    with tempfile.TemporaryDirectory(
        prefix=f".{key}-remote-check-", dir=stage.parent
    ) as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        for relative, expected_sha in sorted(expected.items()):
            target = root / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            result = subprocess.run(
                ["hf", "buckets", "cp", _remote_uri(base, relative), str(target)],
                capture_output=True, text=True, timeout=180, check=False,
            )
            if result.returncode or target.is_symlink() or not target.is_file():
                raise ValueError("REMOTE_OBJECT_DOWNLOAD_HOLD")
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha:
                raise ValueError("REMOTE_OBJECT_SHA_HOLD")


def _prefix_empty(api, prefix: str, reason: str) -> None:
    if _remote_set(api, prefix):
        raise ValueError(reason)


def _check_job_history(api, key: str) -> dict:
    from r60_common2_hf_cpu_final_read_only import walk_job_history

    total, matching = walk_job_history(api, key)
    if matching:
        raise ValueError("EXISTING_JOB_HOLD")
    return {"visible_jobs": total, "matching_jobs": matching, "exhaustive": True}


def job_command(key: str, help_text: str) -> list[str]:
    if not contract.RUN_RE.fullmatch(key):
        raise ValueError("RUN_KEY_HOLD")
    missing = shared_cli.missing_job_cli_flags(help_text)
    default_attempts = shared_cli.use_documented_default_attempts(help_text)
    if missing and not default_attempts:
        raise ValueError("HF_CLI_FLAGS_HOLD")
    input_volumes = [
        f"hf://buckets/{BUCKET}/{_remote_prefix(key)}:/input/r60-base336:ro"
    ]
    output_volume = (
        f"hf://buckets/{BUCKET}/{RESULT_PREFIX}/{key}:/output:rw"
    )
    command = ["bash", WORKER]
    # Reuse the generic argv builder only. Do not call the CPU-only policy
    # validator or relax its CPU flavor allowlist.
    argv = hf_job_guard.build_hf_argv(
        namespace=contract.HF_NAMESPACE,
        name=key,
        flavor=contract.HF_FLAVOR,
        timeout_minutes=contract.HF_TIMEOUT_MINUTES,
        input_volumes=input_volumes,
        output_volume=output_volume,
        image=IMAGE,
        command=command,
    )
    if default_attempts:
        index = argv.index("--attempts")
        if argv[index + 1] != "1":
            raise ValueError("HF_CLI_FLAGS_HOLD")
        del argv[index:index + 2]
    image_index = argv.index(IMAGE)
    argv[image_index:image_index] = [
        "--env", f"STORYFORGE_R60_BASE336_GPU_RUN_KEY={key}",
        "--env", "STORYFORGE_R60_BASE336_GPU_SCOPE=DRY_RUN_NOT_AUTHORIZED",
    ]
    image_index = argv.index(IMAGE)
    if argv[image_index + 1:image_index + 2] == ["--"]:
        argv.pop(image_index + 1)
    argv.insert(argv.index(IMAGE), "--dry-run")
    return argv


def sync(stage: Path, key: str, api) -> dict:
    expected = _check_remote_set(api, stage, key, ready=False)
    _prefix_empty(api, f"{RESULT_PREFIX}/{key}/", "REMOTE_RESULT_ALREADY_EXISTS_HOLD")
    _prefix_empty(api, f"{SUBMISSION_PREFIX}/{key}/", "REMOTE_SUBMISSION_MARKER_EXISTS_HOLD")
    _check_job_history(api, key)
    base = _remote_prefix(key)
    for relative in sorted(set(expected) - {"SHA256_MANIFEST_PRIVATE.json"}):
        result = subprocess.run(
            ["hf", "buckets", "cp", str(stage / relative), _remote_uri(base, relative)],
            capture_output=True, text=True, timeout=180, check=False,
        )
        if result.returncode:
            raise ValueError("REMOTE_UPLOAD_INCOMPLETE_HOLD")
    manifest = "SHA256_MANIFEST_PRIVATE.json"
    result = subprocess.run(
        ["hf", "buckets", "cp", str(stage / manifest), _remote_uri(base, manifest)],
        capture_output=True, text=True, timeout=90, check=False,
    )
    if result.returncode:
        raise ValueError("REMOTE_MANIFEST_UPLOAD_HOLD")
    expected = _check_remote_set(api, stage, key, ready=True)
    _verify_remote_sha(stage, key, expected)
    return {
        **safe("BASE336_GPU_REMOTE_STAGE_READY__NO_JOB", "REMOTE_FILESET_AND_SHA_PASS"),
        "run_key_validated": True,
        "remote_file_sha_verified": True,
        "stage_files": len(expected),
    }


def ready(stage: Path, key: str, api) -> dict:
    expected = _check_remote_set(api, stage, key, ready=True)
    _verify_remote_sha(stage, key, expected)
    _prefix_empty(api, f"{RESULT_PREFIX}/{key}/", "REMOTE_RESULT_ALREADY_EXISTS_HOLD")
    _prefix_empty(api, f"{SUBMISSION_PREFIX}/{key}/", "REMOTE_SUBMISSION_MARKER_EXISTS_HOLD")
    history = _check_job_history(api, key)
    helper = subprocess.run(
        ["hf", "jobs", "run", "--help"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    if helper.returncode:
        raise ValueError("HF_CLI_HELP_HOLD")
    argv = job_command(key, helper.stdout)
    result = subprocess.run(
        argv, capture_output=True, text=True, timeout=60, check=False,
    )
    combined = (result.stdout + result.stderr).lower()
    if result.returncode or not any(value in combined for value in ("dry-run", "dry run")):
        raise ValueError("HF_CLI_DRY_RUN_HOLD")
    return {
        **safe("BASE336_GPU_REMOTE_AND_CLI_READY__NO_JOB", "REMOTE_SHA_HISTORY_AND_DRY_RUN_PASS"),
        "run_key_validated": True,
        "remote_file_sha_verified": True,
        "job_history_exhaustive": history["exhaustive"],
        "visible_jobs": history["visible_jobs"],
        "matching_jobs": history["matching_jobs"],
        "stage_files": len(expected),
        "gpu_flavor_preflighted": contract.HF_FLAVOR,
        "image_digest_pinned": True,
    }


def diagnose(stage: Path, key: str) -> dict:
    report = safe("BASE336_GPU_REMOTE_DIAGNOSTIC_HOLD", "NOT_CHECKED")
    report.update(remote_input="UNKNOWN", remote_output="UNKNOWN", submission_marker="UNKNOWN")
    try:
        if not contract.RUN_RE.fullmatch(key) or stage.name != key:
            raise ValueError("RUN_KEY_HOLD")
        expected = _local_files(stage, key)
        from huggingface_hub import HfApi

        api = HfApi()
        found = _remote_set(api, _remote_prefix(key))
        report["remote_input"] = (
            "EMPTY" if not found else
            "READY_FILESET" if found == set(expected) else "PARTIAL_OR_MISMATCH"
        )
        report["remote_output"] = (
            "EMPTY" if not _remote_set(api, f"{RESULT_PREFIX}/{key}/") else "NONEMPTY"
        )
        report["submission_marker"] = (
            "ABSENT" if not _remote_set(api, f"{SUBMISSION_PREFIX}/{key}/") else "PRESENT"
        )
        report.update(
            status="BASE336_GPU_REMOTE_DIAGNOSTIC_PASS__NO_JOB",
            reason_code="READ_ONLY_REMOTE_INSPECTION",
            run_key_validated=True,
        )
    except Exception:  # noqa: BLE001 - SAFE only
        report["reason_code"] = "REMOTE_DIAGNOSTIC_HOLD"
    return report


def execute(action: str, stage: Path, key: str) -> dict:
    if not contract.RUN_RE.fullmatch(key) or stage.name != key:
        raise ValueError("RUN_KEY_HOLD")
    _local_files(stage, key)
    if action == "preflight":
        return {
            **safe("BASE336_GPU_LOCAL_STAGE_PASS__NO_JOB", "LOCAL_SHA_AND_PROOF_PASS"),
            "run_key_validated": True,
            "stage_files": len(_local_files(stage, key)),
        }
    from huggingface_hub import HfApi

    api = HfApi()
    if action == "sync":
        return sync(stage, key, api)
    if action == "ready":
        return ready(stage, key, api)
    raise ValueError("ACTION_NOT_SUPPORTED_NO_SUBMIT")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "sync", "ready", "diagnose", "cli-flags"))
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--run-key", required=True)
    args = parser.parse_args()
    try:
        if args.action == "cli-flags":
            result = shared_cli.inspect_job_cli_flags()
            report = safe(
                "BASE336_GPU_CLI_FLAGS_PASS__NO_JOB"
                if result["status"] == "WRAPPED_CPU_CLI_FLAGS_PASS__NO_JOB"
                else "BASE336_GPU_CLI_FLAGS_HOLD__NO_JOB",
                result["reason_code"],
            )
        elif args.action == "diagnose":
            report = diagnose(args.stage, args.run_key)
        else:
            report = execute(args.action, args.stage, args.run_key)
    except Exception:  # noqa: BLE001 - never leak remote paths or SDK exception text
        report = safe("BASE336_GPU_ORCHESTRATION_HOLD__NO_JOB", "STAGE_REMOTE_OR_CLI_HOLD")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] in {
        "BASE336_GPU_LOCAL_STAGE_PASS__NO_JOB",
        "BASE336_GPU_REMOTE_STAGE_READY__NO_JOB",
        "BASE336_GPU_REMOTE_AND_CLI_READY__NO_JOB",
        "BASE336_GPU_REMOTE_DIAGNOSTIC_PASS__NO_JOB",
        "BASE336_GPU_CLI_FLAGS_PASS__NO_JOB",
    } else 42


if __name__ == "__main__":
    raise SystemExit(main())
