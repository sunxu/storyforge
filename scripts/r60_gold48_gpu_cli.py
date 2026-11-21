"""Owner Mac Gold48 GPU preflight / explicit once-only submit; no auto retry.

Reuses Base336 GPU job specification and Common2 HF CLI compatibility.
This does not attest the staged code or private inputs and cannot authorize GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

import hf_job_guard
import r60_base336_gpu_cli as gpu
import r60_common2_wrapped_hf_cli as shared

from storyforge_dataset.generation_eval.gold48_contract_bridge import ROLES
from storyforge_dataset.generation_eval.gold48_owner_receipt import (
    APPROVAL_MODE,
    APPROVAL_SCHEMA,
    PRODUCTION_SCOPE,
    RUN_ID,
)
from storyforge_dataset.generation_eval.gold48_runtime_gate import FROZEN_RUNTIME_IMAGE
from storyforge_dataset.hf_runtime.inputs import InputManager
from storyforge_dataset.hf_runtime.outputs import OutputManager

SCHEMA = "storyforge_r60_gold48_gpu_cli_shape_safe_v1"
BUCKET = "hf://buckets/adradar/storyforge-training/"
IMAGE = FROZEN_RUNTIME_IMAGE
ROLE_ADAPTERS = ("r46_v02", "r54_v03a", "r60_base336")
INPUT_PREFIX = "preflight/r60/gold48/gpu/runs"
RESULT_PREFIX = "experiments/r60-gold48/outputs"
CODE_PREFIX = "preflight/r60/gold48/runtime-code"
# Compare the minimal live worker/loader files against the trusted Mac checkout.
# No new code bundle format, no new general-purpose staging framework.
CORE_CODE_FILES = (
    "scripts/r60_gold48_gpu_worker.sh",
    "scripts/r60_gold48_gpu_worker_entry.py",
    "src/storyforge_dataset/generation_eval/gold48_contract_bridge.py",
    "src/storyforge_dataset/generation_eval/gold48_runtime_gate.py",
    "src/storyforge_dataset/generation_eval/gold48_owner_receipt.py",
    "src/storyforge_dataset/generation_eval/gold48_qwen35_loader.py",
    "src/storyforge_dataset/generation_eval/backend.py",
    "src/storyforge_dataset/generation_eval/worker.py",
    "src/storyforge_dataset/hf_runtime/inputs.py",
    "src/storyforge_dataset/hf_runtime/outputs.py",
)


def _check(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def _source(source: str) -> str:
    """One precise private bucket prefix, never a bucket root or overlap."""
    _check(isinstance(source, str) and source.startswith(BUCKET),
           "GOLD48_SOURCE_BUCKET_HOLD")
    relative = source[len(BUCKET):]
    _check(
        bool(relative) and not relative.endswith("/")
        and all(part and part not in {".", ".."} for part in relative.split("/"))
        and not re.search(r"[\s:]", relative),
        "GOLD48_SOURCE_PREFIX_HOLD",
    )
    return source


def _volumes(run_id: str, role: str, code: str, adapters: dict) -> tuple[list[str], str]:
    _check(bool(RUN_ID.fullmatch(run_id)) and role in ROLES,
           "GOLD48_RUN_ROLE_HOLD")
    _check(set(adapters) == set(ROLE_ADAPTERS),
           "GOLD48_ADAPTER_SOURCE_SET_HOLD")
    _check(
        code.startswith(BUCKET + CODE_PREFIX + "/")
        and re.fullmatch(r"[0-9a-f]{40}", code.rsplit("/", 1)[-1]) is not None,
        "GOLD48_IMMUTABLE_CODE_PREFIX_HOLD",
    )
    sources = [
        BUCKET + INPUT_PREFIX + "/" + run_id,
        _source(code),
        *(_source(adapters[r]) for r in ROLE_ADAPTERS),
    ]
    output = BUCKET + RESULT_PREFIX + "/" + run_id
    _check(len(set(sources)) == len(sources), "GOLD48_DUPLICATE_VOLUME_HOLD")
    for item in sources:
        _check(item != output and not item.startswith(output + "/")
               and not output.startswith(item + "/"),
               "GOLD48_INPUT_OUTPUT_OVERLAP_HOLD")
        _check(not any(
            item != other and (
                item.startswith(other + "/") or other.startswith(item + "/")
            )
            for other in sources
        ), "GOLD48_INPUT_VOLUME_OVERLAP_HOLD")
    names = (
        "/input/gold48", "/input/code",
        *(f"/ro_adapters/{r}" for r in ROLE_ADAPTERS),
    )
    inputs = [f"{source}:{dest}:ro" for source, dest in zip(sources, names)]
    output_volume = f"{output}:/output:rw"
    for value in (*inputs, output_volume):
        hf_job_guard.parse_volume(value)
    return inputs, output_volume


def job_dry_run_argv(
    *, run_id: str, role: str, code: str, adapters: dict, help_text: str,
    execute: bool = False,
) -> list[str]:
    """Five exact RO volumes plus distinct RW; existing argv builder only."""
    inputs, output = _volumes(run_id, role, code, adapters)
    missing = shared.missing_job_cli_flags(help_text)
    default_one = shared.use_documented_default_attempts(help_text)
    _check(not missing or default_one, "GOLD48_HF_CLI_FLAGS_HOLD")
    command = [
        "bash", "/input/code/scripts/r60_gold48_gpu_worker.sh",
        "execute" if execute else "check", run_id, role,
    ]
    argv = hf_job_guard.build_hf_argv(
        namespace="adradar", name=run_id, flavor=gpu.contract.HF_FLAVOR,
        timeout_minutes=gpu.contract.HF_TIMEOUT_MINUTES,
        input_volumes=inputs, output_volume=output,
        image=IMAGE, command=command,
    )
    if default_one:
        pos = argv.index("--attempts")
        _check(argv[pos + 1] == "1", "GOLD48_CLI_ATTEMPTS_HOLD")
        del argv[pos:pos + 2]
    pos = argv.index(IMAGE)
    if argv[pos + 1:pos + 2] == ["--"]:
        argv.pop(pos + 1)
    argv.insert(argv.index(IMAGE), "--dry-run")
    return argv



def _local_stage_sha(stage: Path, run_id: str, role: str) -> dict[str, str]:
    """Read Owner-private pre-existing stage; NEVER create or sign it here."""
    import r60_gold48_gpu_worker_entry as worker

    _check(stage.is_absolute() and stage.name == run_id
           and stage.is_dir() and not stage.is_symlink()
           and stat.S_IMODE(stage.stat().st_mode) == 0o700,
           "GOLD48_LOCAL_STAGE_0700_HOLD")
    _check(stat.S_IMODE(stage.parent.stat().st_mode) == 0o700,
           "GOLD48_MARKER_PARENT_0700_HOLD")
    _check({p.name for p in stage.iterdir()} == set(worker.STAGED),
           "GOLD48_LOCAL_STAGE_EXACT_FILESET_HOLD")
    hashes = {}
    for name, maximum in worker.STAGED.items():
        path = stage / name
        info = path.lstat()
        _check(stat.S_ISREG(info.st_mode)
               and stat.S_IMODE(info.st_mode) == 0o600
               and not path.is_symlink()
               and 0 < info.st_size <= maximum,
               "GOLD48_LOCAL_PRIVATE_FILE_MODE_OR_SIZE_HOLD")
        hashes[name] = InputManager.open_verified(
            path, max_bytes=maximum,
        ).sha256
    owner = InputManager.validate_json(
        InputManager.open_verified(
            stage / "owner_authorization.private.json", max_bytes=65536,
        ).read_bytes()
    )
    _check(isinstance(owner, dict)
           and set(owner) == {"schema", "approval_mode", "payload"}
           and owner.get("schema") == APPROVAL_SCHEMA
           and owner.get("approval_mode") == APPROVAL_MODE
           and isinstance(owner.get("payload"), dict),
           "GOLD48_OWNER_MAC_APPROVAL_REQUIRED_HOLD")
    scope = owner["payload"]
    _check(scope.get("run_id") == run_id
           and scope.get("model_role") == role
           and scope.get("execution_environment") == PRODUCTION_SCOPE
           and scope.get("record_count") == 48
           and scope.get("max_model_calls") == 48
           and scope.get("gpu_authorized") is True
           and scope.get("inference_authorized") is True
           and scope.get("training_authorized") is False
           and scope.get("runtime_image_digest") ==
               IMAGE.removeprefix("pytorch/pytorch@")
           and scope.get("output_directory") ==
               "/tmp/storyforge-gold48-private/outputs/" + run_id
           and scope.get("output_filename") == role + ".private.json",
           "GOLD48_OWNER_GPU_SCOPE_HOLD")
    try:
        issued = datetime.fromisoformat(scope["issued_at_utc"])
        expires = datetime.fromisoformat(scope["expires_at_utc"])
        from datetime import timedelta
        _check(issued.tzinfo is not None and expires.tzinfo is not None
               and issued <= datetime.now(UTC) <= expires
               and timedelta(0) < expires - issued <= timedelta(hours=48),
               "GOLD48_OWNER_GPU_APPROVAL_EXPIRED_HOLD")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("GOLD48_OWNER_GPU_APPROVAL_TIME_HOLD") from exc
    # The Job independently verifies all 48 frozen-case bindings before
    # loading GPU weights; Mac checks the complete staged byte set here.
    return hashes


def _remote_file_sha(api, prefix: str, names: dict[str, str]) -> None:
    """Read-only remote SHA compare; reuse existing hf buckets cp, no upload."""
    _check(shared.BUCKET == "adradar/storyforge-training",
           "GOLD48_SHARED_BUCKET_HOLD")
    _check(shared.remote_set(api, prefix) == set(names),
           "GOLD48_REMOTE_STAGE_EXACT_FILESET_HOLD")
    with TemporaryDirectory(prefix="gold48-remote-audit-") as directory:
        for name, expected in sorted(names.items()):
            target = Path(directory) / (name.replace("/", "__"))
            uri = BUCKET + prefix + name
            result = subprocess.run(
                ["hf", "buckets", "cp", uri, str(target)],
                capture_output=True, text=True, timeout=300, check=False,
            )
            _check(result.returncode == 0 and target.is_file()
                   and not target.is_symlink(),
                   "GOLD48_REMOTE_SHA_DOWNLOAD_HOLD")
            sha = hashlib.sha256(target.read_bytes()).hexdigest()
            _check(sha == expected, "GOLD48_REMOTE_STAGE_SHA_MISMATCH_HOLD")


def _ready_or_submit(
    *, action: str, run_id: str, role: str, code: str, adapters: dict,
    stage: Path, allow_execute: bool,
) -> dict:
    """Single trusted Mac: exact bytes -> history -> dry-run -> create-only submit."""
    from huggingface_hub import HfApi
    from r60_common2_hf_cpu_final_read_only import walk_job_history

    _check(action != "submit" or allow_execute,
           "GOLD48_EXPLICIT_OWNER_GPU_EXECUTE_REQUIRED_HOLD")
    _check(bool(RUN_ID.fullmatch(run_id)) and stage.name == run_id,
           "GOLD48_RUN_STAGE_MISMATCH_HOLD")
    _volumes(run_id, role, code, adapters)
    local_sha = _local_stage_sha(stage, run_id, role)
    marker = stage.parent / (run_id + ".gold48-gpu-submit.private.json")
    _check(not marker.exists() and not marker.is_symlink(),
           "GOLD48_GPU_ALREADY_ATTEMPTED_NO_RETRY_HOLD")
    api = HfApi()
    _check(not shared.remote_set(api, RESULT_PREFIX + "/" + run_id + "/"),
           "GOLD48_REMOTE_RESULT_NOT_EMPTY_HOLD")
    _remote_file_sha(api, INPUT_PREFIX + "/" + run_id + "/", local_sha)

    local_commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    _check(local_commit.returncode == 0
           and local_commit.stdout.strip() == code.rsplit("/", 1)[-1],
           "GOLD48_LOCAL_CODE_COMMIT_MISMATCH_HOLD")
    remote_code = shared.remote_set(
        api, CODE_PREFIX + "/" + local_commit.stdout.strip() + "/",
    )
    _check(set(CORE_CODE_FILES).issubset(remote_code),
           "GOLD48_REMOTE_CODE_BUNDLE_MISSING_HOLD")
    with TemporaryDirectory(prefix="gold48-code-audit-") as directory:
        for name in CORE_CODE_FILES:
            local_bytes = (ROOT / name).read_bytes()
            target = Path(directory) / name.replace("/", "__")
            result = subprocess.run(
                ["hf", "buckets", "cp", code + "/" + name, str(target)],
                capture_output=True, text=True, timeout=300, check=False,
            )
            _check(result.returncode == 0 and target.is_file()
                   and hashlib.sha256(local_bytes).hexdigest() ==
                       hashlib.sha256(target.read_bytes()).hexdigest(),
                   "GOLD48_CODE_BUNDLE_SHA_HOLD")
    _, matching = walk_job_history(api, run_id)
    _check(matching == 0, "GOLD48_PREEXISTING_HF_JOB_NO_RETRY_HOLD")
    help_result = subprocess.run(
        ["hf", "jobs", "run", "--help"], capture_output=True,
        text=True, timeout=20, check=False,
    )
    _check(help_result.returncode == 0, "GOLD48_HF_CLI_HELP_HOLD")
    argv = job_dry_run_argv(
        run_id=run_id, role=role, code=code, adapters=adapters,
        help_text=help_result.stdout, execute=True,
    )
    probe = subprocess.run(
        argv, capture_output=True, text=True, timeout=60, check=False,
    )
    _check(probe.returncode == 0
           and any(s in (probe.stdout + probe.stderr).lower()
                   for s in ("dry-run", "dry run")),
           "GOLD48_HF_CLI_DRY_RUN_HOLD")
    if action == "ready":
        report = safe("GOLD48_GPU_MAC_STAGE_CODE_AND_CLI_READY__NO_JOB",
                      "REMOTE_SHA_EXACT_AND_NO_PREEXISTING_JOB")
        report.update(
            private_stage_bytes_verified=True, code_bundle_sha_verified=True,
            owner_gpu_authorized=True,
        )
        return report
    auth = subprocess.run(
        ["hf", "auth", "whoami"], capture_output=True,
        text=True, timeout=20, check=False,
    )
    _check(auth.returncode == 0, "GOLD48_HF_AUTH_HOLD")
    # The one-and-only billable call is below this durable create-only marker.
    # A timeout or error means UNKNOWN, never an automatic retry.
    try:
        OutputManager.write_safe(
            marker,
            {"schema": "storyforge_gold48_gpu_submit_attempt_private_v1",
             "status": "ATTEMPTED__NO_AUTO_RETRY",
             "run_id": run_id, "model_role": role,
             "code_commit": local_commit.stdout.strip()},
            mode=0o600,
        )
    except (OSError, ValueError) as exc:
        raise ValueError("GOLD48_LOCAL_SUBMIT_MARKER_CREATE_ONLY_HOLD") from exc
    argv.remove("--dry-run")
    try:
        sent = subprocess.run(
            argv, capture_output=True, text=True, timeout=120, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return {
            **safe("GOLD48_GPU_SUBMISSION_UNCONFIRMED_NO_RETRY",
                   "CHECK_HF_ORG_JOB_HISTORY_BEFORE_ANY_ACTION"),
            "hf_jobs_submitted": None, "gpu_started": None, "model_calls": None,
        }
    if sent.returncode:
        return {
            **safe("GOLD48_GPU_SUBMISSION_UNCONFIRMED_NO_RETRY",
                   "CHECK_HF_ORG_JOB_HISTORY_BEFORE_ANY_ACTION"),
            "hf_jobs_submitted": None, "gpu_started": None, "model_calls": None,
        }
    ids = set(re.findall(
        r"(?<![0-9a-f])[0-9a-f]{24}(?![0-9a-f])",
        sent.stdout + sent.stderr,
    ))
    if len(ids) != 1:
        return {
        **safe("GOLD48_GPU_SUBMISSION_UNCONFIRMED_NO_RETRY",
               "HF_JOB_ID_UNKNOWN_CHECK_HISTORY"),
        "hf_jobs_submitted": None, "gpu_started": None, "model_calls": None,
    }
    report = safe("GOLD48_GPU_SUBMITTED__OWNER_DOWNLOAD_AUDIT_PENDING",
                  "ONE_JOB__NO_AUTO_RETRY")
    report.update(hf_jobs_submitted=1, owner_gpu_authorized=True,
                  private_stage_bytes_verified=True,
                  code_bundle_sha_verified=True, job_id=next(iter(ids)),
                  gpu_started=None, model_calls=None)
    return report


def safe(status: str, reason: str) -> dict:
    return {
        "schema": SCHEMA, "status": status, "reason_code": reason,
        "hf_jobs_submitted": 0, "gpu_started": False, "model_calls": 0,
        "private_values_emitted": False, "quality_v1_admitted": 0,
        "owner_gpu_authorized": False,
        "private_stage_bytes_verified": False,
        "code_bundle_sha_verified": False,
        "provider_handoff_live_mount_verified": False,
        "adapter_sources_privately_reviewed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("shape", "dry-run", "ready", "submit"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--role", choices=ROLES, required=True)
    parser.add_argument("--code-prefix", required=True)
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--execute", action="store_true")
    for role in ROLE_ADAPTERS:
        parser.add_argument("--adapter-" + role.replace("_", "-"), required=True)
    args = parser.parse_args(argv)
    try:
        adapters = {
            role: getattr(args, "adapter_" + role) for role in ROLE_ADAPTERS
        }
        if args.action == "shape":
            inputs, output = _volumes(args.run_id, args.role,
                                      args.code_prefix, adapters)
            _check(len(inputs) == 5 and output.endswith(":/output:rw"),
                   "GOLD48_VOLUMES_HOLD")
            result = safe("GOLD48_GPU_COMMAND_SHAPE_PASS__NO_JOB",
                          "EXACT_SIX_RO_ONE_RW_SCOPE__REMOTE_NOT_VERIFIED")
        elif args.action in ("ready", "submit"):
            _check(args.stage is not None, "GOLD48_LOCAL_STAGE_REQUIRED_HOLD")
            result = _ready_or_submit(
                action=args.action, run_id=args.run_id, role=args.role,
                code=args.code_prefix, adapters=adapters, stage=args.stage,
                allow_execute=args.execute,
            )
        else:
            helper = subprocess.run(
                ["hf", "jobs", "run", "--help"],
                capture_output=True, text=True, timeout=20, check=False,
            )
            _check(helper.returncode == 0, "GOLD48_HF_CLI_HELP_HOLD")
            dry_argv = job_dry_run_argv(
                run_id=args.run_id, role=args.role, code=args.code_prefix,
                adapters=adapters, help_text=helper.stdout,
            )
            probe = subprocess.run(
                dry_argv, capture_output=True, text=True,
                timeout=60, check=False,
            )
            _check(probe.returncode == 0 and
                   any(t in (probe.stdout + probe.stderr).lower()
                       for t in ("dry-run", "dry run")),
                   "GOLD48_HF_CLI_DRY_RUN_HOLD")
            result = safe("GOLD48_GPU_CLI_DRY_RUN_PASS__NO_JOB",
                          "NO_SUBMISSION__STAGE_AND_AUTHORIZATION_STILL_HOLD")
        code = 0
    except Exception:  # noqa: BLE001 - fail closed; never print private errors
        result = safe("HOLD", "GOLD48_GPU_CLI_SHAPE_OR_DRY_RUN_HOLD")
        code = 42
    print(json.dumps(result, sort_keys=True))
    if result["status"] not in {
        "GOLD48_GPU_COMMAND_SHAPE_PASS__NO_JOB",
        "GOLD48_GPU_CLI_DRY_RUN_PASS__NO_JOB",
        "GOLD48_GPU_MAC_STAGE_CODE_AND_CLI_READY__NO_JOB",
        "GOLD48_GPU_SUBMITTED__OWNER_DOWNLOAD_AUDIT_PENDING",
    }:
        code = 42
    return code


if __name__ == "__main__":
    raise SystemExit(main())
