#!/usr/bin/env python3
"""R58 G1: five additional Bucket roots, 7 completed GPU Jobs only.

Read-only: HF Bucket file/directory names + previously frozen PRIVATE metadata.
No logs, commands, file bytes, stories, Job creation, or training. Findings are
path-name references, NOT evidence of actual training or historical input use.
Job IDs and matching paths remain exclusively in a fresh 0600 PRIVATE receipt.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from r58_g1_other_three_jobs_private_ledger_crosscheck_safe import (
    BUCKET, DEFAULT_ROOT, RE_JOB, read_private,
)
from r58_g1_gpu18_bucket_metadata_coverage_readonly_20261101 import verify_ledger
from triage_hf_job_exposure import write_private

SCHEMA = "r58_g1_gpu7_completed_other_bucket_roots_metadata_safe_v1"
PRIVATE_SCHEMA = "r58_g1_gpu7_completed_other_bucket_roots_metadata_private_v1"
BRANCH = "r58/roleplay-sft-skill-v01"
ROOTS = (
    "experiments",
    "baseline-runs/baseline",
    "evaluation",
    "evaluation-runs",
    "preflight",
)
MAX_LISTINGS = 1000
MAX_ENTRIES = 5000
MAX_DEPTH = 10
RE_TOKEN = re.compile(r"(?<![a-f0-9])[a-f0-9]{24}(?![a-f0-9])")


class Hold(Exception):
    pass


def completed_missing(coverage: dict, gpu: list[dict], focus: str) -> set[str]:
    if (coverage.get("schema") != "r58_g1_gpu18_bucket_directory_coverage_private_v1"
            or coverage.get("status") != "GPU18_BUCKET_PREFIX_METADATA_PRIVATE__ALL_PENDING"
            or coverage.get("namespace") != "adradar"
            or coverage.get("g1_clearance") != "HOLD"
            or coverage.get("expansion_allowed") is not False
            or coverage.get("bucket_roots") != ["runs", "baseline-runs/capacity"]):
        raise Hold("frozen GPU18 prefix coverage receipt mismatch")
    rows = coverage.get("gpu18_entries_PRIVATE")
    if not isinstance(rows, list) or len(rows) != 18:
        raise Hold("expected 18 frozen rows")
    by_id = {r["id"]: r["stage"] for r in gpu}
    seen, missing = set(), set()
    matched, no_dir = Counter(), Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise Hold("invalid frozen GPU18 row")
        uid = row.get("hf_job_id_PRIVATE")
        stage = row.get("stage")
        dirs = row.get("bucket_job_id_directory_roots_PRIVATE")
        if (not isinstance(uid, str) or RE_JOB.fullmatch(uid) is None
                or uid in seen or uid not in by_id or stage != by_id[uid]
                or row.get("hardware_class") != "GPU"
                or row.get("parameter_update_classification") != "PENDING_SOURCE_REVIEW"
                or row.get("train_validation_consumption_status") != "NOT_VERIFIED"
                or not isinstance(dirs, list)
                or len(dirs) != len(set(dirs))
                or any(d not in ["runs", "baseline-runs/capacity"] for d in dirs)
                or row.get("job_id_directory_in_scanned_roots") is not bool(dirs)):
            raise Hold("frozen GPU18 metadata drift")
        seen.add(uid)
        (matched if dirs else no_dir)[stage] += 1
        if stage == "COMPLETED" and not dirs:
            missing.add(uid)
        if uid == focus and not dirs:
            raise Hold("original priority Job directory unexpectedly absent")
    if (seen != set(by_id) or len(missing) != 7
            or matched != {"CANCELED": 2, "ERROR": 2}
            or no_dir != {"COMPLETED": 7, "ERROR": 7}):
        raise Hold("original GPU18 4/14 findings changed")
    return missing


def scan_names(fs, root: str, targets: set[str]) -> tuple[dict[str, int], dict[str, set[str]]]:
    """Bounded metadata-only directory walk; refuse incomplete walks."""
    if root not in ROOTS or len(targets) != 7:
        raise Hold("invalid scoped root or target cohort")
    base = BUCKET + "/" + root
    base_canonical = base.removeprefix("hf://").rstrip("/")
    stack = [(base, 0)]
    listings = entries = 0
    stats = {"metadata_list_calls": 0, "metadata_entries": 0}
    match_map: dict[str, set[str]] = defaultdict(set)
    while stack:
        directory, depth = stack.pop()
        if listings >= MAX_LISTINGS or depth > MAX_DEPTH:
            raise Hold("metadata walk bound reached")
        listings += 1
        children = fs.ls(directory, detail=True)
        if not isinstance(children, list):
            raise Hold("invalid Bucket listing")
        for obj in children:
            if not isinstance(obj, dict):
                raise Hold("invalid Bucket entry")
            raw = obj.get("name", obj.get("path"))
            kind = obj.get("type")
            if not isinstance(raw, str) or not isinstance(kind, str):
                raise Hold("invalid Bucket entry metadata")
            canonical = raw.removeprefix("hf://").lstrip("/").rstrip("/")
            if not canonical.startswith(base_canonical + "/"):
                raise Hold("path outside authorized Bucket prefix")
            entries += 1
            if entries > MAX_ENTRIES:
                raise Hold("metadata entries bound reached")
            for token in set(RE_TOKEN.findall(canonical)):
                if token in targets:
                    match_map[token].add(root)
            if kind in ("directory", "dir"):
                if depth + 1 > MAX_DEPTH:
                    raise Hold("path depth limit reached")
                stack.append((raw if raw.startswith("hf://") else "hf://" + canonical, depth + 1))
            elif kind not in ("file", "link"):
                raise Hold("unsupported Bucket node type")
    stats["metadata_list_calls"] = listings
    stats["metadata_entries"] = entries
    return stats, dict(match_map)


def run(args: argparse.Namespace) -> dict:
    repo = args.repo_root.resolve(strict=True)
    branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        capture_output=True, text=True, timeout=8, check=True,
    )
    if branch.stdout.strip() != BRANCH:
        raise Hold("not on R58 branch")
    if args.private_output.exists() or args.private_output.is_symlink():
        raise Hold("private output exists; do not overwrite")
    if args.private_output in (args.private_unknown_ledger, args.private_priority_ledger,
                               args.private_gpu18_coverage):
        raise Hold("private output/input alias")
    unknown = read_private(args.private_unknown_ledger)
    priority = read_private(args.private_priority_ledger)
    coverage = read_private(args.private_gpu18_coverage)
    gpu, focus = verify_ledger(unknown, priority)
    targets = completed_missing(coverage, gpu, focus)

    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    per_root = {}
    matched: dict[str, set[str]] = defaultdict(set)
    for root in ROOTS:
        stat, hints = scan_names(fs, root, targets)
        per_root[root] = {**stat, "completed_gpu7_path_ref_matches": len(hints)}
        for jid, roots in hints.items():
            matched[jid].update(roots)
    private = {
        "schema": PRIVATE_SCHEMA,
        "status": "SEVEN_COMPLETED_GPU_OTHER_ROOT_NAME_MATCHES_PRIVATE__ALL_PENDING",
        "namespace": "adradar",
        "scanned_roots": list(ROOTS),
        "matches_PRIVATE": [
            {"hf_job_id_PRIVATE": jid,
             "root_path_name_reference_matches_PRIVATE": sorted(matched.get(jid, [])),
             "historical_training_classification": "PENDING_SOURCE_REVIEW"}
            for jid in sorted(targets)
        ],
        "g1_clearance": "HOLD",
        "expansion_allowed": False,
    }
    write_private(args.private_output, private)
    return {
        "schema": SCHEMA,
        "status": "GPU7_COMPLETED_OTHER_BUCKET_ROOT_METADATA_NAMES_CHECKED__ALL_PENDING",
        "namespace": "adradar",
        "frozen_original_unknown_gpu": 18,
        "frozen_completed_gpu_without_prior_root_directory": 7,
        "other_roots_scanned": list(ROOTS),
        "per_root_metadata_counts": per_root,
        "completed_gpu7_with_any_additional_path_name_reference": len(matched),
        "completed_gpu7_without_name_reference_in_five_roots": 7 - len(matched),
        "zero_path_references_proves_nontraining": False,
        "path_reference_proves_training": False,
        "historical_input_consumption_proven": False,
        "optimizer_update_independently_proven": False,
        "all_historical_job_roots_exhausted": False,
        "source_registry_complete": False,
        "all_original_gpu18_remain_pending": True,
        "private_receipt_written_exclusive_0600": True,
        "job_commands_logs_environment_or_dataset_bytes_read": False,
        "job_ids_or_paths_exported": False,
        "hf_job_started": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--private-unknown-ledger", type=Path,
                   default=DEFAULT_ROOT / "g1_hf_unknown_jobs_private.json")
    p.add_argument("--private-priority-ledger", type=Path,
                   default=DEFAULT_ROOT / "g1_hf_gpu_signal_priority_one_private.json")
    p.add_argument("--private-gpu18-coverage", type=Path,
                   default=DEFAULT_ROOT / "g1_gpu18_bucket_prefix_metadata_PRIVATE_20261101.json")
    p.add_argument("--private-output", type=Path,
                   default=DEFAULT_ROOT / "g1_gpu7_completed_other_roots_PRIVATE_20261101.json")
    args = p.parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "OTHER_BUCKET_ROOT_METADATA_INCOMPLETE__G1_HOLD",
            "job_ids_or_paths_exported": False,
            "hf_job_started": False,
            "g1_clearance": "HOLD",
            "g2_clearance": "HOLD",
            "train_admitted": 0,
            "validation_admitted": 0,
            "teacher_admitted": 0,
            "expansion_allowed": False,
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
