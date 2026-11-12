"""R60 CPU2 v2 final read-only gates: no submit, no private values.

Reuses frozen stage hash guard and remote Bucket guard. A bounded Job list is
diagnostic only, NOT proof of global absence. No automatic admission.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

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


def walk_job_history(api, key: str, *, max_pages: int = 100) -> tuple[int, int]:
    """Walk all authoritative API pages. Never emit any job body or token."""
    from huggingface_hub import get_session

    origin = api.endpoint.rstrip("/")
    base_path = "/api/jobs/adradar"
    target = origin + base_path
    parsed_base = urlparse(target)
    headers = api._build_hf_headers()
    session = get_session()
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    total = 0
    matching = 0
    for _ in range(max_pages):
        parsed = urlparse(target)
        if (parsed.scheme != "https" or parsed.netloc != parsed_base.netloc
                or parsed.path != base_path or parsed.fragment
                or target in seen_urls):
            raise ValueError("PAGINATION_URL_HOLD")
        seen_urls.add(target)
        response = session.get(target, headers=headers, timeout=20, allow_redirects=False)
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            raise ValueError("PAGINATION_RESPONSE_HOLD")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("PAGINATION_RESPONSE_HOLD")
            job_id = record.get("id")
            if not isinstance(job_id, str) or not job_id or job_id in seen_ids:
                raise ValueError("PAGINATION_DUPLICATE_OR_INVALID_JOB_HOLD")
            seen_ids.add(job_id)
            total += 1
            labels = record.get("labels") or {}
            name = record.get("name") or (labels.get("name") if isinstance(labels, dict) else "")
            environment = record.get("environment") or {}
            # A job can be submitted without a name containing the key.
            if (key in str(name or "")
                    or key in str(labels)
                    or (isinstance(environment, dict)
                        and environment.get("STORYFORGE_R60_COMMON2_RUN_KEY") == key)
                    or any(key in str(x) for x in (record.get("command") or []))):
                matching += 1
        next_page = response.links.get("next")
        if not next_page:
            return total, matching
        href = next_page.get("url")
        if not isinstance(href, str) or not href:
            raise ValueError("PAGINATION_URL_HOLD")
        target = urljoin(target, href)
    raise ValueError("PAGINATION_LIMIT_HOLD")



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
        total, matched = walk_job_history(api, key)
        report["visible_jobs"] = total
        report["matching_jobs"] = matched
        report["history_exhaustive"] = True
        if matched:
            report["reason_code"] = "PAGINATED_JOB_MATCH_HOLD"
        else:
            report["status"] = "CPU2_HISTORY_PAGINATED_PASS__NO_JOB"
            report["reason_code"] = "JOB_HISTORY_EXHAUSTIVE_NO_MATCH"
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
