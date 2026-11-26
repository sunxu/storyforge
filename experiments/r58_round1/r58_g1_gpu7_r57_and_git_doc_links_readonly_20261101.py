#!/usr/bin/env python3
"""R58 G1: check seven completed GPU Job name refs in R57 and pinned Git docs.

Only reads three existing PRIVATE metadata receipts, names of files/directories
under a single HF Bucket evaluation-runs/v03-r57 root, and tracked Git HEAD
SAFE .md/.json documents. No raw training, logs, Job commands or HF compute.
Does not create, change or disclose any PRIVATE receipt. All jobs remain PENDING.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess

from r58_g1_other_three_jobs_private_ledger_crosscheck_safe import (
    BUCKET, DEFAULT_ROOT, RE_JOB, read_private,
)
from r58_g1_gpu18_bucket_metadata_coverage_readonly_20261101 import verify_ledger
from r58_g1_gpu7_completed_other_bucket_roots_metadata_safe_20261101 import (
    ROOTS, RE_TOKEN, completed_missing,
)
from check_hf_job_documentation_coverage import frozen_job_mentions

SCHEMA = "r58_g1_gpu7_r57_and_git_document_refs_safe_v1"
R57_ROOT = "evaluation-runs/v03-r57"
MAX_NODES = 1500
MAX_LIST_CALLS = 100
MAX_DEPTH = 10
BRANCH = "r58/roleplay-sft-skill-v01"


class Hold(Exception):
    pass


def verify_other_roots(ledger: dict, targets: set[str]) -> tuple[set[str], set[str]]:
    if (not isinstance(ledger, dict)
            or ledger.get("schema") != "r58_g1_gpu7_completed_other_bucket_roots_metadata_private_v1"
            or ledger.get("namespace") != "adradar"
            or ledger.get("status") != "SEVEN_COMPLETED_GPU_OTHER_ROOT_NAME_MATCHES_PRIVATE__ALL_PENDING"
            or ledger.get("scanned_roots") != list(ROOTS)
            or ledger.get("g1_clearance") != "HOLD"
            or ledger.get("expansion_allowed") is not False):
        raise Hold("original seven GPU name-reference receipt invalid")
    rows = ledger.get("matches_PRIVATE")
    if not isinstance(rows, list) or len(rows) != 7:
        raise Hold("expected seven exact ledger rows")
    seen, in_eval, nowhere = set(), set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise Hold("invalid private row")
        uid = row.get("hf_job_id_PRIVATE")
        roots = row.get("root_path_name_reference_matches_PRIVATE")
        if (not isinstance(uid, str) or RE_JOB.fullmatch(uid) is None
                or uid not in targets or uid in seen
                or row.get("historical_training_classification") != "PENDING_SOURCE_REVIEW"
                or roots not in ([], ["evaluation-runs"])):
            raise Hold("Job metadata receipt mismatch")
        seen.add(uid)
        (in_eval if roots else nowhere).add(uid)
    if seen != targets or len(in_eval) != 4 or len(nowhere) != 3:
        raise Hold("original seven Job 4/3 split drift")
    return in_eval, nowhere


def r57_metadata_job_ids(fs, targets: set[str]) -> tuple[set[str], dict]:
    if len(targets) != 7:
        raise Hold("wrong target count")
    base = BUCKET + "/" + R57_ROOT
    canonical_base = base.removeprefix("hf://").rstrip("/")
    stack = [(base, 0)]
    matches = set()
    seen = set()
    nodes = calls = 0
    categories = Counter()
    while stack:
        directory, depth = stack.pop()
        if depth > MAX_DEPTH or calls >= MAX_LIST_CALLS or directory in seen:
            raise Hold("unbounded or repeated metadata directory")
        seen.add(directory)
        calls += 1
        children = fs.ls(directory, detail=True)
        if not isinstance(children, list):
            raise Hold("unexpected HF metadata listing")
        for entry in children:
            if not isinstance(entry, dict):
                raise Hold("unrecognized metadata entry")
            name = entry.get("name", entry.get("path"))
            typ = entry.get("type")
            if not isinstance(name, str) or typ not in ("dir", "directory", "file", "link"):
                raise Hold("unsupported Bucket object metadata")
            canonical = name.removeprefix("hf://").lstrip("/").rstrip("/")
            if not canonical.startswith(canonical_base + "/"):
                raise Hold("out-of-scope Bucket path")
            nodes += 1
            if nodes > MAX_NODES:
                raise Hold("metadata limit")
            matches.update(set(RE_TOKEN.findall(canonical)) & targets)
            basename = canonical.rsplit("/", 1)[-1]
            if typ in ("dir", "directory"):
                if depth >= MAX_DEPTH:
                    raise Hold("metadata depth limit")
                stack.append((name if name.startswith("hf://") else "hf://" + canonical, depth + 1))
            else:
                categories["files"] += 1
                if basename == "trainer_state.json":
                    categories["trainer_state_named"] += 1
                if basename == "optimizer.pt":
                    categories["optimizer_pt_named"] += 1
                if basename.endswith(".safetensors"):
                    categories["model_safetensors_named"] += 1
                if basename in ("train.jsonl", "validation.jsonl"):
                    categories["training_split_jsonl_named"] += 1
    return matches, {"metadata_list_calls": calls, "metadata_objects": nodes, **dict(sorted(categories.items()))}


def summarize(targets: set[str], eval_ids: set[str], missing_ids: set[str],
              r57_ids: set[str], docs: set[str], doc_count: int,
              stats: dict) -> dict:
    if (not isinstance(docs, set) or doc_count <= 0
            or targets != eval_ids | missing_ids
            or eval_ids & missing_ids
            or r57_ids != eval_ids):
        raise Hold("historical R57 Job exact-link mismatch")
    return {
        "schema": SCHEMA,
        "status": "GPU7_R57_PATH_AND_FROZEN_DOC_REFERENCE_METADATA_CHECKED__ALL_PENDING",
        "namespace": "adradar",
        "original_completed_gpu7_checked": 7,
        "original_eval_runs_linked": len(eval_ids),
        "original_no_five_root_name_link": len(missing_ids),
        "r57_specific_root": R57_ROOT,
        "eval_linked_four_all_found_in_r57_specific_root": True,
        "r57_root_metadata": stats,
        "frozen_git_head_document_blobs_scanned": doc_count,
        "eval_linked_four_with_git_doc_reference": len(eval_ids & docs),
        "eval_linked_four_without_git_doc_reference": len(eval_ids - docs),
        "other_three_with_git_doc_reference": len(missing_ids & docs),
        "other_three_without_git_doc_reference": len(missing_ids - docs),
        "git_doc_reference_proves_training_or_nontraining": False,
        "r57_path_reference_proves_evaluation_only": False,
        "named_checkpoint_absence_proves_no_update": False,
        "historical_input_consumption_proven": False,
        "weight_update_proven": False,
        "all_seven_remain_pending": True,
        "other_hf_namespaces_or_deleted_jobs_checked": False,
        "source_registry_complete": False,
        "private_ledgers_modified": False,
        "raw_job_ids_or_private_paths_exported": False,
        "training_data_logs_commands_environment_read": False,
        "hf_job_started": False,
        "g1_clearance": "HOLD", "g2_clearance": "HOLD",
        "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def run(args: argparse.Namespace) -> dict:
    repo = args.repo_root.resolve(strict=True)
    branch = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                            capture_output=True, text=True, timeout=8, check=True)
    if branch.stdout.strip() != BRANCH:
        raise Hold("wrong Git branch")
    unknown = read_private(args.private_unknown_ledger)
    priority = read_private(args.private_priority_ledger)
    coverage = read_private(args.private_gpu18_coverage)
    rootlinks = read_private(args.private_gpu7_roots)
    gpu, focus = verify_ledger(unknown, priority)
    targets = completed_missing(coverage, gpu, focus)
    eval_ids, no_refs = verify_other_roots(rootlinks, targets)
    from huggingface_hub import HfFileSystem
    remote_ids, stats = r57_metadata_job_ids(HfFileSystem(), targets)
    docs, doc_count = frozen_job_mentions(repo)
    return summarize(targets, eval_ids, no_refs, remote_ids, docs, doc_count, stats)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--private-unknown-ledger", type=Path,
                   default=DEFAULT_ROOT / "g1_hf_unknown_jobs_private.json")
    p.add_argument("--private-priority-ledger", type=Path,
                   default=DEFAULT_ROOT / "g1_hf_gpu_signal_priority_one_private.json")
    p.add_argument("--private-gpu18-coverage", type=Path,
                   default=DEFAULT_ROOT / "g1_gpu18_bucket_prefix_metadata_PRIVATE_20261101.json")
    p.add_argument("--private-gpu7-roots", type=Path,
                   default=DEFAULT_ROOT / "g1_gpu7_completed_other_roots_PRIVATE_20261101.json")
    args = p.parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "GPU7_R57_OR_FROZEN_DOC_METADATA_UNAVAILABLE__G1_HOLD",
            "raw_job_ids_or_private_paths_exported": False,
            "hf_job_started": False,
            "g1_clearance": "HOLD", "g2_clearance": "HOLD",
            "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
            "expansion_allowed": False,
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
