"""R60 CPU2 v2 final read-only gates: no submit, no private values.

Reuses frozen stage hash guard and remote Bucket guard. A bounded Job list is
diagnostic only, NOT proof of global absence. No automatic admission.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts import r60_common2_hf_cpu_bucket_guard as bucket
    from scripts import r60_common2_hf_cpu_image_probe as probe
    from scripts import r60_common2_hf_cpu_image_retry as retry
    from scripts import r60_common2_hf_cpu_stage as stage_contract
except ModuleNotFoundError:
    import r60_common2_hf_cpu_bucket_guard as bucket
    import r60_common2_hf_cpu_image_probe as probe
    import r60_common2_hf_cpu_image_retry as retry
    import r60_common2_hf_cpu_stage as stage_contract

RESULTS = "preflight/r60/common2/cpu2/results"


def check(api, stage: Path, key: str) -> dict:
    report = {
        "schema": "storyforge_r60_common2_cpu2_final_read_only_safe_v1",
        "status": "CPU2_FINAL_READ_ONLY_HOLD",
        "reason_code": "NOT_CHECKED",
        "local_stage": "NOT_CHECKED",
        "remote_input": "NOT_CHECKED",
        "remote_output": "NOT_CHECKED",
        "submit_marker": "NOT_CHECKED",
        "visible_jobs": 0,
        "matching_jobs": 0,
        "history_exhaustive": False,
        "job_submission_calls": 0, "train_admitted": 0,
        "gpu_started": False, "private_values_emitted": False,
    }
    if not stage_contract.RUN_KEY.fullmatch(key) or key == retry.RUN_KEY or stage.name != key:
        report["reason_code"] = "RUN_KEY_HOLD"
        return report
    if stage.is_symlink() or not stage.is_dir():
        report["reason_code"] = "STAGE_HOLD"
        return report
    marker = stage.parent / (key + ".cpu-submit-v2-attempted")
    report["submit_marker"] = "PRESENT" if marker.exists() else "ABSENT"
    if marker.exists():
        report["reason_code"] = "SUBMISSION_ALREADY_ATTEMPTED"
        return report
    try:
        probe.check_local(stage, key)
        report["local_stage"] = "PASS"
        bucket.check("ready", key, stage, api)
        report["remote_input"] = "READY_PASS"
        prefix = f"{RESULTS}/{key}/"
        entries = api.list_bucket_tree(bucket.BUCKET, prefix=prefix, recursive=True)
        files = [x for x in entries if getattr(x, "type", "") != "directory"]
        if files:
            report["remote_output"] = "NONEMPTY"
            report["reason_code"] = "OUTPUT_ALREADY_PRESENT"
            return report
        report["remote_output"] = "EMPTY_PASS"
        jobs = api.list_jobs(namespace="adradar")
        report["visible_jobs"] = len(jobs)
        matches = [
            j for j in jobs
            if key in str(getattr(j, "name", ""))
            or key in str(getattr(j, "labels", ""))
        ]
        report["matching_jobs"] = len(matches)
        if matches:
            report["reason_code"] = "VISIBLE_JOB_MATCH_HOLD"
        elif len(jobs) >= 100:
            report["reason_code"] = "JOB_HISTORY_INCOMPLETE_HOLD"
        else:
            # The endpoint has no documented exhaustion guarantee.
            report["reason_code"] = "JOB_HISTORY_NOT_PROVEN_EXHAUSTIVE"
        return report
    except Exception as exc:
        report["reason_code"] = bucket.classify_failure(exc)
        return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    try:
        from huggingface_hub import HfApi
        report = check(HfApi(), args.stage, args.run_key)
    except Exception:
        report = {
            "schema": "storyforge_r60_common2_cpu2_final_read_only_safe_v1",
            "status": "CPU2_FINAL_READ_ONLY_HOLD",
            "reason_code": "SDK_RUNTIME_HOLD",
            "job_submission_calls": 0,
            "train_admitted": 0,
            "gpu_started": False,
            "private_values_emitted": False,
        }
    print(json.dumps(report, sort_keys=True))
    return 42


if __name__ == "__main__":
    raise SystemExit(main())
