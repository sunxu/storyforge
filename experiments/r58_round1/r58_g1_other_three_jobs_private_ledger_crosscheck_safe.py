#!/usr/bin/env python3
"""StoryForge R58 G1: read-only, single-cohort SAFE membership crosscheck.

Reads ONLY existing PRIVATE metadata ledgers and HF Bucket *directory names*.
Matches the three already-observed additional GPU Job directories to the
original 60-item PRIVATE unknown-Job ledger. No logs, commands, training
bytes, secret data, Job execution, private identifiers, or hashes exported.
Always HOLD. Never writes or overwrites a private file.

Run from the repo's R58 branch (or --repo-root PATH). Requires the existing
Hugging Face auth and huggingface_hub with bucket filesystem support.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

PRIVATE_ROOT = Path.home() / ".storyforge-r58-private"
DEFAULT_ROOT = PRIVATE_ROOT / "round1_pilot_20261030"
BUCKET = "hf://buckets/adradar/storyforge-training"
RE_JOB = re.compile(r"[a-f0-9]{24}\Z")
MAX_FILE = 150_000
SAFE_SCHEMA = "r58_g1_other_three_gpu_jobs_private_ledger_membership_safe_v1"


class Hold(Exception):
    pass


def read_private(path: Path) -> dict:
    if not path.is_absolute() or not path.is_relative_to(PRIVATE_ROOT):
        raise Hold("private input path outside intended root")
    ancestor = path.parent
    while ancestor != Path.home():
        if ancestor.is_symlink():
            raise Hold("symlinked private ancestor")
        if ancestor == ancestor.parent:
            raise Hold("invalid private path")
        ancestor = ancestor.parent
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or not 0 < st.st_size <= MAX_FILE:
            raise Hold("private ledger unsafe permissions or size")
        raw = f.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise Hold("private ledger too large")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise Hold("private ledger must be JSON object")
    return value


def basename_ids(fs, url: str) -> set[str]:
    result = fs.ls(url, detail=False)
    if not isinstance(result, list) or len(result) > 100:
        raise Hold("unexpected remote listing")
    names = []
    for v in result:
        if not isinstance(v, str):
            raise Hold("unexpected directory listing item")
        v = v.rstrip("/").rsplit("/", 1)[-1]
        if not RE_JOB.fullmatch(v):
            raise Hold("non-Job directory encountered")
        names.append(v)
    if len(set(names)) != len(names):
        raise Hold("duplicate directory in listing")
    return set(names)


def verify(unknown: dict, priority: dict, known_ids: set[str], bucket_ids: set[str]) -> dict:
    if (unknown.get("schema") != "r58_round1_g1_hf_job_exposure_triage_private_v1"
            or unknown.get("namespace") != "adradar"
            or unknown.get("status") != "PRIVATE_UNKNOWN_JOB_INVENTORY_ONLY__ALL_PENDING"
            or unknown.get("g1_clearance") != "HOLD"
            or unknown.get("expansion_allowed") is not False):
        raise Hold("unrecognized original 60-job private ledger")
    entries = unknown.get("entries")
    if not isinstance(entries, list) or len(entries) != 60:
        raise Hold("original unknown Job cohort not 60")
    lookup = {}
    for row in entries:
        if not isinstance(row, dict):
            raise Hold("invalid original Job row")
        jobid = row.get("hf_job_id_PRIVATE")
        if not isinstance(jobid, str) or not RE_JOB.fullmatch(jobid) or jobid in lookup:
            raise Hold("invalid or duplicate original Job ID")
        if (row.get("historical_parameter_update_classification") != "PENDING_SOURCE_REVIEW"
                or row.get("primary_train_input_provenance") != "NOT_VERIFIED"
                or row.get("stage") not in {"COMPLETED", "ERROR", "CANCELED"}
                or row.get("hardware_class") not in {"GPU", "CPU", "UNRECOGNIZED"}):
            raise Hold("unexpected original Job classification")
        lookup[jobid] = row
    hardware = Counter(row["hardware_class"] for row in entries)
    if hardware != {"GPU": 18, "CPU": 42}:
        raise Hold("original GPU18/CPU42 cohort drift")
    if (priority.get("schema") != "r58_round1_g1_gpu_signal_priority_case_private_v1"
            or priority.get("namespace") != "adradar"
            or priority.get("status") != "ONE_POTENTIAL_LOG_INDICATOR__PROOF_NOT_ESTABLISHED"
            or priority.get("stage") != "CANCELED"
            or priority.get("indicator_classes") != ["TRAINING_LOSS_GRAD_TELEMETRY"]
            or priority.get("g1_clearance") != "HOLD"):
        raise Hold("priority Job ledger mismatch")
    focus = priority.get("hf_job_id_PRIVATE")
    if not isinstance(focus, str) or not RE_JOB.fullmatch(focus) or focus not in lookup:
        raise Hold("priority Job not in original unknown cohort")
    if len(known_ids) != 9 or len(bucket_ids) != 6 or not known_ids.isdisjoint(set(lookup)):
        raise Hold("known job or bucket cohort drift")
    if focus not in bucket_ids or focus in known_ids:
        raise Hold("prior priority Job missing or misclassified")
    remaining = bucket_ids - known_ids - {focus}
    if len(remaining) != 3 or not remaining.issubset(lookup):
        raise Hold("three other Bucket jobs not exactly matched to private 60")
    by_status = Counter(lookup[j]["stage"] for j in remaining)
    if by_status != {"ERROR": 2, "CANCELED": 1}:
        raise Hold("private provider stage did not match 3-job direct evidence")
    if any(lookup[j]["hardware_class"] != "GPU" for j in remaining):
        raise Hold("private cohort has non-GPU for one of three jobs")
    return {
        "schema": SAFE_SCHEMA,
        "status": "THREE_OTHER_GPU_BUCKET_JOBS_MATCH_FROZEN_60_UNKNOWN_LEDGER__ALL_STILL_PENDING",
        "namespace": "adradar",
        "original_unknown_jobs": 60,
        "original_unknown_gpu": 18,
        "original_unknown_cpu": 42,
        "observed_run_and_capacity_job_directories": len(bucket_ids),
        "priority_job_also_matches_original_60": True,
        "additional_bucket_job_directories": 3,
        "additional_job_private_ledger_exact_matches": 3,
        "additional_job_stages": dict(sorted(by_status.items())),
        "additional_job_hardware_all_gpu": True,
        "additional_jobs_removed_from_pending": 0,
        "logs_commands_environment_training_bytes_read": False,
        "job_ids_or_private_sha256_exported": False,
        "private_ledgers_modified": False,
        "hf_job_started": False,
        "historical_universe_complete": False,
        "optimizer_step_proven_for_additional_jobs": False,
        "historical_input_consumption_proven_for_additional_jobs": False,
        "source_registry_complete": False,
        "g1_clearance": "HOLD", "g2_clearance": "HOLD",
        "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--private-unknown-ledger", type=Path,
                   default=DEFAULT_ROOT / "g1_hf_unknown_jobs_private.json")
    p.add_argument("--private-priority-ledger", type=Path,
                   default=DEFAULT_ROOT / "g1_hf_gpu_signal_priority_one_private.json")
    args = p.parse_args()
    try:
        # Reuse the repository's existing frozen 5+4 identity registry.
        repo = args.repo_root.resolve(strict=True)
        branch = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                                capture_output=True, text=True, timeout=8, check=True)
        if branch.stdout.strip() != "r58/roleplay-sft-skill-v01":
            raise Hold("incorrect repository branch")
        sys.path.insert(0, str(repo / "experiments" / "r58_round1"))
        from check_hf_training_job_inventory import KNOWN_SFT_JOBS
        from triage_hf_job_exposure import DOCUMENTED_NO_OPTIMIZER
        known_ids = set(KNOWN_SFT_JOBS.values()) | set(DOCUMENTED_NO_OPTIMIZER.values())
        unknown = read_private(args.private_unknown_ledger)
        priority = read_private(args.private_priority_ledger)
        from huggingface_hub import HfFileSystem
        fs = HfFileSystem()
        bucket_ids = (basename_ids(fs, BUCKET + "/runs")
                      | basename_ids(fs, BUCKET + "/baseline-runs/capacity"))
        safe = verify(unknown, priority, known_ids, bucket_ids)
        print(json.dumps(safe, sort_keys=True, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        print(json.dumps({"schema": SAFE_SCHEMA,
                          "status": "PRIVATE_OR_BUCKET_COHORT_UNAVAILABLE__HOLD",
                          "private_job_ids_exported": False,
                          "hf_job_started": False, "g1_clearance": "HOLD",
                          "g2_clearance": "HOLD", "train_admitted": 0,
                          "validation_admitted": 0, "teacher_admitted": 0,
                          "expansion_allowed": False}, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
