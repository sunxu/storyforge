#!/usr/bin/env python3
"""R58 G1: reconcile 18 frozen unknown GPU Jobs to two HF Bucket roots.

Only directory-name metadata and existing PRIVATE Job ledgers are read.
No original job logs/commands/arguments/environment, no training bytes,
no R50 material and no new HF compute. A directory miss is NOT exclusion.
Output Job-level details to a fresh 0600 PRIVATE receipt, SAFE aggregate to stdout.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

from r58_g1_other_three_jobs_private_ledger_crosscheck_safe import (
    BUCKET,
    DEFAULT_ROOT,
    RE_JOB,
    basename_ids,
    read_private,
)
from check_hf_training_job_inventory import KNOWN_SFT_JOBS
from triage_hf_job_exposure import DOCUMENTED_NO_OPTIMIZER, write_private

SCHEMA = "r58_g1_gpu18_bucket_directory_coverage_safe_v1"
PRIVATE_SCHEMA = "r58_g1_gpu18_bucket_directory_coverage_private_v1"
BRANCH = "r58/roleplay-sft-skill-v01"
ROOTS = ("runs", "baseline-runs/capacity")


class Hold(Exception):
    pass


def verify_ledger(ledger: dict, priority: dict) -> tuple[list[dict], str]:
    if not isinstance(ledger, dict) or any([
        ledger.get("schema") != "r58_round1_g1_hf_job_exposure_triage_private_v1",
        ledger.get("status") != "PRIVATE_UNKNOWN_JOB_INVENTORY_ONLY__ALL_PENDING",
        ledger.get("namespace") != "adradar",
        ledger.get("g1_clearance") != "HOLD",
        ledger.get("expansion_allowed") is not False,
    ]):
        raise Hold("frozen unknown-Job ledger mismatch")
    rows = ledger.get("entries")
    if not isinstance(rows, list) or len(rows) != 60:
        raise Hold("frozen 60-Job cohort unavailable")
    known = set(KNOWN_SFT_JOBS.values()) | set(DOCUMENTED_NO_OPTIMIZER.values())
    if len(known) != 9:
        raise Hold("known Job registry mismatch")
    seen = set()
    gpu = []
    hardware = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise Hold("malformed ledger row")
        jid = row.get("hf_job_id_PRIVATE")
        stage = row.get("stage")
        cls = row.get("hardware_class")
        if (not isinstance(jid, str) or RE_JOB.fullmatch(jid) is None
                or jid in seen or jid in known
                or stage not in {"COMPLETED", "ERROR", "CANCELED"}
                or cls not in {"GPU", "CPU", "UNRECOGNIZED"}
                or row.get("historical_parameter_update_classification") != "PENDING_SOURCE_REVIEW"
                or row.get("primary_train_input_provenance") != "NOT_VERIFIED"):
            raise Hold("invalid private Job row")
        seen.add(jid)
        hardware[cls] += 1
        if cls == "GPU":
            gpu.append({"id": jid, "stage": stage})
    if hardware != {"GPU": 18, "CPU": 42}:
        raise Hold("original frozen hardware counts changed")
    if (not isinstance(priority, dict)
            or priority.get("schema") != "r58_round1_g1_gpu_signal_priority_case_private_v1"
            or priority.get("status") != "ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED"
            or priority.get("namespace") != "adradar"
            or priority.get("stage") != "CANCELED"
            or priority.get("g1_clearance") != "HOLD"
            or priority.get("expansion_allowed") is not False):
        raise Hold("original priority Job ledger mismatch")
    focus = priority.get("hf_job_id_PRIVATE")
    if not isinstance(focus, str) or focus not in {r["id"] for r in gpu}:
        raise Hold("priority Job not in original GPU18 cohort")
    return gpu, focus


def summarize(gpu: list[dict], focus: str, by_root: dict[str, set[str]]) -> tuple[dict, dict]:
    if set(by_root) != set(ROOTS):
        raise Hold("incomplete Bucket roots")
    if any(not isinstance(v, set) or any(RE_JOB.fullmatch(j) is None for j in v)
           for v in by_root.values()):
        raise Hold("invalid remote directory listing")
    combined = set().union(*by_root.values())
    matches = {r["id"] for r in gpu} & combined
    if focus not in matches:
        raise Hold("prior priority Job directory no longer located")
    present = Counter()
    absent = Counter()
    details = []
    for row in sorted(gpu, key=lambda x: x["id"]):
        roots = sorted(root for root, ids in by_root.items() if row["id"] in ids)
        p = bool(roots)
        (present if p else absent)[row["stage"]] += 1
        details.append({
            "hf_job_id_PRIVATE": row["id"],
            "stage": row["stage"],
            "hardware_class": "GPU",
            "bucket_job_id_directory_roots_PRIVATE": roots,
            "job_id_directory_in_scanned_roots": p,
            "parameter_update_classification": "PENDING_SOURCE_REVIEW",
            "train_validation_consumption_status": "NOT_VERIFIED",
        })
    if len(gpu) != 18 or len(details) != 18:
        raise Hold("count mismatch")
    safe = {
        "schema": SCHEMA,
        "status": "FROZEN_UNKNOWN_GPU18_BUCKET_PREFIX_METADATA_RECONCILED__ALL_PENDING",
        "namespace": "adradar",
        "original_unknown_job_count": 60,
        "original_unknown_gpu": 18,
        "original_unknown_cpu_unscanned": 42,
        "bucket_root_scopes": list(ROOTS),
        "bucket_job_directories_per_root": {k: len(v) for k, v in by_root.items()},
        "distinct_bucket_job_id_directories_seen": len(combined),
        "gpu18_with_job_id_directory_in_scanned_roots": len(matches),
        "gpu18_without_job_id_directory_in_scanned_roots": 18 - len(matches),
        "with_directory_stage_counts": dict(sorted(present.items())),
        "without_directory_stage_counts": dict(sorted(absent.items())),
        "priority_canceled_gpu_job_present_in_scanned_roots": True,
        "gpu18_jobs_removed_from_pending": 0,
        "no_directory_means_nontraining": False,
        "directory_presence_proves_optimizer_step": False,
        "directory_presence_proves_train_input_consumption": False,
        "historical_bucket_objects_immutable_proven": False,
        "all_historical_job_roots_exhausted": False,
        "other_namespaces_or_platforms_audited": False,
        "hf_job_started": False,
        "job_commands_logs_environment_training_bytes_read": False,
        "raw_job_ids_or_private_hashes_exported": False,
        "source_registry_complete": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }
    private = {
        "schema": PRIVATE_SCHEMA,
        "namespace": "adradar",
        "status": "GPU18_BUCKET_PREFIX_METADATA_PRIVATE__ALL_PENDING",
        "bucket_roots": list(ROOTS),
        "gpu18_entries_PRIVATE": details,
        "g1_clearance": "HOLD",
        "expansion_allowed": False,
    }
    return safe, private


def run(args: argparse.Namespace) -> dict:
    repo = args.repo_root.resolve(strict=True)
    branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        capture_output=True, text=True, check=True, timeout=8,
    )
    if branch.stdout.strip() != BRANCH:
        raise Hold("wrong Git branch")
    if (args.private_output.exists() or args.private_output.is_symlink()
            or args.private_output == args.private_unknown_ledger
            or args.private_output == args.private_priority_ledger):
        raise Hold("cannot overwrite private evidence")
    unknown = read_private(args.private_unknown_ledger)
    priority = read_private(args.private_priority_ledger)
    gpu, focus = verify_ledger(unknown, priority)
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    by_root = {root: basename_ids(fs, BUCKET + "/" + root) for root in ROOTS}
    safe, private = summarize(gpu, focus, by_root)
    # Fail-closed: write only after both listings and all validations pass.
    write_private(args.private_output, private)
    safe["private_receipt_written_exclusive_0600"] = True
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--private-unknown-ledger", type=Path,
                        default=DEFAULT_ROOT / "g1_hf_unknown_jobs_private.json")
    parser.add_argument("--private-priority-ledger", type=Path,
                        default=DEFAULT_ROOT / "g1_hf_gpu_signal_priority_one_private.json")
    parser.add_argument("--private-output", type=Path,
                        default=DEFAULT_ROOT / "g1_gpu18_bucket_prefix_metadata_PRIVATE_20261101.json")
    args = parser.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "GPU18_BUCKET_METADATA_OR_PRIVATE_LEDGER_UNAVAILABLE__G1_HOLD",
            "raw_job_ids_or_private_hashes_exported": False,
            "hf_job_started": False,
            "g1_clearance": "HOLD", "g2_clearance": "HOLD",
            "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
            "expansion_allowed": False,
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
