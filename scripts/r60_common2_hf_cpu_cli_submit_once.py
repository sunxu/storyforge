"""R60 Common2 CPU2 one-attempt Mac HF CLI submission, guarded and fail-closed.

Run ONLY on Owner Mac. No dataset admission, training, or GPU. The marker is
create-only and persists even when the submission fails or the result is unclear.
Never replay the same run key after creating the marker.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from scripts import r60_common2_hf_cpu_cli_dry_run as dry
    from scripts import r60_common2_hf_cpu_final_read_only as gate
except ModuleNotFoundError:
    import r60_common2_hf_cpu_cli_dry_run as dry
    import r60_common2_hf_cpu_final_read_only as gate

SAFE_SCHEMA = "storyforge_r60_common2_cpu2_cli_submit_once_safe_v1"


def result(status: str, *, reason: str, job_id: str | None = None) -> dict:
    out = {
        "schema": SAFE_SCHEMA,
        "status": status,
        "reason_code": reason,
        "job_submission_calls_max": 1,
        "gpu_started": False,
        "train_admitted": 0,
        "private_values_emitted": False,
    }
    if job_id is not None:
        out["job_id"] = job_id
        out["job_url"] = f"https://huggingface.co/jobs/adradar/{job_id}"
    return out


def submit(stage: Path, key: str, *, execute: bool = False) -> dict:
    marker = stage.parent / f"{key}.cpu-submit-v2-attempted"
    if not execute:
        return result("CPU2_SUBMIT_HOLD", reason="EXPLICIT_EXECUTE_REQUIRED")
    if marker.exists():
        return result("CPU2_SUBMIT_HOLD", reason="ATTEMPT_MARKER_PRESENT")
    phase = "SDK_IMPORT"
    marker_created = False
    try:
        from huggingface_hub import HfApi
        phase = "FINAL_GATE"
        report = gate.check(HfApi(), stage, key)
        if (report["status"] != "CPU2_HISTORY_PAGINATED_PASS__NO_JOB"
                or report["history_exhaustive"] is not True
                or report["matching_jobs"] != 0
                or report["submit_marker"] != "ABSENT"
                or report["remote_output"] != "EMPTY_PASS"):
            return result("CPU2_SUBMIT_HOLD", reason="FINAL_GATE_FAILED")
        phase = "HF_HELP"
        help_result = subprocess.run(
            ["hf", "jobs", "run", "--help"], capture_output=True,
            text=True, timeout=20, check=False,
        )
        if help_result.returncode != 0:
            return result("CPU2_SUBMIT_HOLD", reason="HF_HELP_HOLD")
        phase = "CLI_PREPARE"
        argv = dry.prepare(stage, key, help_result.stdout)
        if "--dry-run" not in argv:
            return result("CPU2_SUBMIT_HOLD", reason="DRY_RUN_ARG_HOLD")
        phase = "CLI_DRY_RUN"
        preflight = subprocess.run(
            argv, capture_output=True, text=True, timeout=60, check=False,
        )
        if (preflight.returncode != 0
                or ("dry-run" not in (preflight.stdout + preflight.stderr).lower()
                    and "dry run" not in (preflight.stdout + preflight.stderr).lower())):
            return result("CPU2_SUBMIT_HOLD", reason="CLI_DRY_RUN_HOLD")
        phase = "HF_AUTH"
        auth = subprocess.run(
            ["hf", "auth", "whoami"], capture_output=True,
            text=True, timeout=20, check=False,
        )
        if auth.returncode != 0:
            return result("CPU2_SUBMIT_HOLD", reason="HF_AUTH_HOLD")
        phase = "SUBMISSION_POLICY"
        argv.remove("--dry-run")
        if argv.count("--attempts") != 1 or argv[argv.index("--attempts")+1] != "1":
            return result("CPU2_SUBMIT_HOLD", reason="ATTEMPT_POLICY_HOLD")
        if "--detach" not in argv or "--name" not in argv or dry.IMAGE not in argv:
            return result("CPU2_SUBMIT_HOLD", reason="SUBMISSION_POLICY_HOLD")
        # Create-only, durable marker BEFORE invoking the potentially billable API.
        phase = "MARKER_CREATE"
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        marker_created = True
        with os.fdopen(fd, "w") as file:
            file.write(json.dumps({
                "schema": SAFE_SCHEMA, "run_key": key,
                "status": "SUBMISSION_ATTEMPTED_DO_NOT_RETRY",
            }, sort_keys=True) + "\n")
            file.flush()
            os.fsync(file.fileno())
        phase = "SUBMISSION_CALL"
        try:
            process = subprocess.run(
                argv, capture_output=True, text=True,
                timeout=120, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return result("CPU2_SUBMISSION_UNCONFIRMED_HOLD", reason="CLI_TIMEOUT_OR_IO")
        if process.returncode != 0:
            return result("CPU2_SUBMISSION_UNCONFIRMED_HOLD", reason="CLI_NONZERO_CHECK_JOBS")
        output = process.stdout + "\n" + process.stderr
        ids = set(re.findall(r"(?<![a-f0-9])[a-f0-9]{24}(?![a-f0-9])", output))
        if len(ids) != 1:
            return result("CPU2_SUBMISSION_UNCONFIRMED_HOLD", reason="JOB_ID_NOT_UNIQUE")
        return result("CPU2_JOB_SUBMITTED__TRAIN_HOLD", reason="ONE_CPU_JOB", job_id=ids.pop())
    except FileExistsError:
        return result("CPU2_SUBMIT_HOLD", reason="ATTEMPT_MARKER_PRESENT")
    except Exception:
        if marker_created or marker.exists():
            return result("CPU2_SUBMISSION_UNCONFIRMED_HOLD", reason="POST_MARKER_" + phase + "_HOLD")
        return result("CPU2_SUBMIT_HOLD", reason="PRE_MARKER_" + phase + "_HOLD")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-key", required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    report = submit(a.stage, a.run_key, execute=a.execute)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "CPU2_JOB_SUBMITTED__TRAIN_HOLD" else 42


if __name__ == "__main__":
    sys.exit(main())
