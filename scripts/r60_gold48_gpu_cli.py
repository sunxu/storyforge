"""Owner Mac Gold48 GPU argv and CLI dry-run ONLY; no submit action.

Reuses Base336 GPU job specification and Common2 HF CLI compatibility.
This does not attest the staged code or private inputs and cannot authorize GPU.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

import hf_job_guard
import r60_base336_gpu_cli as gpu
import r60_common2_wrapped_hf_cli as shared

from storyforge_dataset.generation_eval.gold48_contract_bridge import ROLES
from storyforge_dataset.generation_eval.gold48_owner_receipt import RUN_ID
from storyforge_dataset.generation_eval.gold48_runtime_gate import FROZEN_RUNTIME_IMAGE

SCHEMA = "storyforge_r60_gold48_gpu_cli_shape_safe_v1"
BUCKET = "hf://buckets/adradar/storyforge-training/"
IMAGE = FROZEN_RUNTIME_IMAGE
ROLE_ADAPTERS = ("r46_v02", "r54_v03a", "r60_base336")
INPUT_PREFIX = "preflight/r60/gold48/gpu/runs"
RESULT_PREFIX = "experiments/r60-gold48/outputs"
CODE_PREFIX = "preflight/r60/gold48/runtime-code"


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
) -> list[str]:
    """Five exact RO volumes plus distinct RW; existing argv builder only."""
    inputs, output = _volumes(run_id, role, code, adapters)
    missing = shared.missing_job_cli_flags(help_text)
    default_one = shared.use_documented_default_attempts(help_text)
    _check(not missing or default_one, "GOLD48_HF_CLI_FLAGS_HOLD")
    command = [
        "bash", "/input/code/scripts/r60_gold48_gpu_worker.sh",
        "check", run_id, role,
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
    parser.add_argument("action", choices=("shape", "dry-run"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--role", choices=ROLES, required=True)
    parser.add_argument("--code-prefix", required=True)
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
    except (OSError, ValueError, subprocess.TimeoutExpired):
        result = safe("HOLD", "GOLD48_GPU_CLI_SHAPE_OR_DRY_RUN_HOLD")
        code = 42
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
