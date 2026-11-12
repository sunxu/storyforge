"""R60 Common2 CPU2: use the shared HF guard for a SAFE CLI dry-run only.

The tool NEVER submits a Job, uploads a stage, or prints CLI output containing
private paths. It checks a NEW SHA-verified stage and generates one compatible
command through scripts/hf_job_guard.py (single source of CLI flags).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

try:
    from scripts import hf_job_guard
    from scripts import r60_common2_hf_cpu_image_probe as probe
    from scripts import r60_common2_hf_cpu_image_retry as retry
    from scripts import r60_common2_hf_cpu_stage as stage_contract
except ModuleNotFoundError:
    import hf_job_guard
    import r60_common2_hf_cpu_image_probe as probe
    import r60_common2_hf_cpu_image_retry as retry
    import r60_common2_hf_cpu_stage as stage_contract

PREFIX = "hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2"
WORKER = "code/scripts/r60_common2_hf_cpu_worker_v2.sh"
# Owner-verified Docker manifest digest (not config digest) for the 2.6.0 image.
IMAGE = "pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"
NEEDED_OPTIONS = (*hf_job_guard.REQUIRED_HF_RUN_FLAGS, "--dry-run")


def prepare(stage: Path, key: str, help_text: str) -> list[str]:
    if (not stage_contract.RUN_KEY.fullmatch(key) or key == retry.RUN_KEY
            or stage.name != key):
        raise ValueError("NEW_KEY_HOLD")
    probe.check_local(stage, key)
    worker = stage / WORKER
    if not worker.is_file() or worker.is_symlink():
        raise ValueError("NEW_WORKER_HOLD")
    source = worker.read_text()
    if ('ROOT="/input/common2"' not in source or 'OUT="/output"' not in source
            or "/workspace" in source or "swift sft " in source
            or "os.O_EXCL" not in source):
        raise ValueError("NEW_WORKER_CONTRACT_HOLD")
    missing = hf_job_guard.missing_hf_cli_options(help_text)
    # The v2 launch argv uses -v, so an exact documented -v switch is
    # equivalent to the long --volume spelling for this R60-only adapter.
    # Never accept -verbose or free prose containing the letters "-v".
    has_short_volume = bool(re.search(
        r"(?<![A-Za-z0-9_-])-v(?![A-Za-z0-9_-])", help_text,
    ))
    if has_short_volume:
        missing = [option for option in missing if option != "--volume"]
    if missing or "--dry-run" not in help_text:
        raise ValueError("HF_CLI_FLAGS_HOLD")
    inputs = [f"{PREFIX}/runs/{key}:/input/common2:ro"]
    output = f"{PREFIX}/results/{key}:/output:rw"
    command = ["bash", f"/input/common2/{WORKER}"]
    hf_job_guard.validate_spec(
        namespace="adradar", flavor="cpu-upgrade", timeout_minutes=120,
        input_volumes=inputs, output_volume=output, command=command,
    )
    argv = hf_job_guard.build_hf_argv(
        namespace="adradar", name=f"r60-cpu2-{key}",
        flavor="cpu-upgrade", timeout_minutes=120,
        input_volumes=inputs, output_volume=output, image=IMAGE,
        command=command,
    )
    # Add only the documented dry-run flag, before IMAGE; do not enable submit.
    # The frozen v2 worker requires this environment binding to start.
    argv[argv.index(IMAGE):argv.index(IMAGE)] = [
        "--env", f"STORYFORGE_R60_COMMON2_RUN_KEY={key}",
    ]
    argv.insert(argv.index(IMAGE), "--dry-run")
    # hf 2.4.0 documents IMAGE COMMAND..., with no extra separator in COMMAND.
    # Keep the shared builder unchanged for other projects, adapt only here.
    image_index = argv.index(IMAGE)
    if argv[image_index + 1:image_index + 2] == ["--"]:
        argv.pop(image_index + 1)
    return argv


def run(stage: Path, key: str, execute_dry_run: bool) -> dict:
    result = {
        "schema": "storyforge_r60_common2_cpu2_cli_dry_run_safe_v1",
        "status": "CLI_PREFLIGHT_HOLD",
        "reason_code": "UNVERIFIED",
        "job_submission_calls": 0, "gpu_started": False,
        "train_admitted": 0, "private_values_emitted": False,
    }
    try:
        help_process = subprocess.run(
            ["hf", "jobs", "run", "--help"], capture_output=True,
            text=True, timeout=20, check=False,
        )
        if help_process.returncode != 0:
            raise ValueError("HF_CLI_HELP_HOLD")
        argv = prepare(stage, key, help_process.stdout)
        result["status"] = "CLI_PREFLIGHT_PASS__NO_JOB"
        result["reason_code"] = "DRY_RUN_NOT_REQUESTED"
        if execute_dry_run:
            dry = subprocess.run(argv, capture_output=True,
                                 text=True, timeout=60, check=False)
            # Never expose raw CLI output: it can include source paths.
            if dry.returncode != 0:
                raise ValueError("HF_CLI_DRY_RUN_HOLD")
            # A dry-run is required to describe the resolved configuration.
            # A bare job launch receipt is not a valid preflight.
            output = dry.stdout + dry.stderr
            if "dry run" not in output.lower() and "dry-run" not in output.lower():
                raise ValueError("HF_CLI_DRY_RUN_NOT_CONFIRMED")
            result["status"] = "CLI_DRY_RUN_PASS__NO_JOB"
            result["reason_code"] = "NO_SUBMISSION"
    except (OSError, subprocess.TimeoutExpired):
        result.update(status="CLI_PREFLIGHT_HOLD", reason_code="CLI_UNAVAILABLE_OR_TIMEOUT")
    except ValueError as exc:
        result.update(status="CLI_PREFLIGHT_HOLD", reason_code=str(exc))
    except Exception:
        result.update(status="CLI_PREFLIGHT_HOLD", reason_code="SAFE_LOCAL_HOLD")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = run(args.stage, args.run_key, args.dry_run)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"].endswith("__NO_JOB") else 42


if __name__ == "__main__":
    raise SystemExit(main())
