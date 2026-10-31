#!/usr/bin/env python3
"""R58 G1: stage-only SAFE diagnostic for an earlier GPU7 R57/Git-doc HOLD.

Read-only; one frozen GPU7 cohort; one R57 Bucket prefix; tracked Git HEAD
SAFE documentation. No log/command/weights/train-bytes access or HF Jobs.
No private receipt written or overwritten, no raw errors/paths/IDs printed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from r58_g1_other_three_jobs_private_ledger_crosscheck_safe import DEFAULT_ROOT, read_private
from r58_g1_gpu18_bucket_metadata_coverage_readonly_20261101 import verify_ledger
from r58_g1_gpu7_completed_other_bucket_roots_metadata_safe_20261101 import completed_missing
from r58_g1_gpu7_r57_and_git_doc_links_readonly_20261101 import (
    BRANCH,
    r57_metadata_job_ids,
    verify_other_roots,
    summarize,
)
from check_hf_job_documentation_coverage import frozen_job_mentions

SCHEMA = "r58_g1_gpu7_r57_git_doc_stage_diagnostic_safe_v1"

# Fixed stages are safe to disclose. Never serialize source exceptions.
STAGES = frozenset({
    "REPOSITORY_BRANCH",
    "PRIVATE_UNKNOWN_LEDGER",
    "PRIVATE_PRIORITY_LEDGER",
    "PRIVATE_GPU18_COVERAGE_LEDGER",
    "PRIVATE_GPU7_ROOTS_LEDGER",
    "FROZEN_GPU18_COHORT",
    "FROZEN_GPU7_ROOT_COHORT",
    "FROZEN_GIT_HEAD_DOCUMENTS",
    "R57_BUCKET_DIRECTORY_NAMES",
    "R57_EXACT_JOB_SET_BINDING",
    "FINAL_AGGREGATION",
})


class ScopeHold(Exception):
    pass


def diagnose(args: argparse.Namespace) -> dict:
    stage = "REPOSITORY_BRANCH"
    evidence = {}
    try:
        repo = args.repo_root.resolve(strict=True)
        result = subprocess.run(
            ["git", "-C", str(repo), "branch", "--show-current"],
            capture_output=True, text=True, timeout=8, check=True,
        )
        if result.stdout.strip() != BRANCH:
            raise ScopeHold("wrong branch")

        stage = "PRIVATE_UNKNOWN_LEDGER"
        unknown = read_private(args.private_unknown_ledger)

        stage = "PRIVATE_PRIORITY_LEDGER"
        priority = read_private(args.private_priority_ledger)

        stage = "PRIVATE_GPU18_COVERAGE_LEDGER"
        coverage = read_private(args.private_gpu18_coverage)

        stage = "PRIVATE_GPU7_ROOTS_LEDGER"
        rootlinks = read_private(args.private_gpu7_roots)

        stage = "FROZEN_GPU18_COHORT"
        gpu, focus = verify_ledger(unknown, priority)
        targets = completed_missing(coverage, gpu, focus)

        stage = "FROZEN_GPU7_ROOT_COHORT"
        expected_eval, no_refs = verify_other_roots(rootlinks, targets)
        if len(targets) != 7 or len(expected_eval) != 4 or len(no_refs) != 3:
            raise ScopeHold("unexpected frozen cohort size")

        # Check Git documents BEFORE remote listing to avoid duplicate HF
        # metadata scans if the failure is actually in local Git.
        stage = "FROZEN_GIT_HEAD_DOCUMENTS"
        docs, doc_count = frozen_job_mentions(repo)
        if not isinstance(docs, set) or doc_count <= 0:
            raise ScopeHold("no frozen docs")

        stage = "R57_BUCKET_DIRECTORY_NAMES"
        from huggingface_hub import HfFileSystem
        observed, stats = r57_metadata_job_ids(HfFileSystem(), targets)

        stage = "R57_EXACT_JOB_SET_BINDING"
        evidence = {
            "expected_r57_eval_job_count": len(expected_eval),
            "observed_r57_gpu7_job_name_matches": len(observed),
            "observed_r57_expected_set_overlap_count": len(observed & expected_eval),
            "expected_eval_jobs_not_in_r57_names": len(expected_eval - observed),
            "observed_other_gpu7_jobs_in_r57_names": len(observed - expected_eval),
            "frozen_git_docs_scanned": doc_count,
            "r57_metadata_list_calls": stats["metadata_list_calls"],
            "r57_metadata_objects": stats["metadata_objects"],
        }
        if observed != expected_eval:
            raise ScopeHold("name set mismatch")

        stage = "FINAL_AGGREGATION"
        summary = summarize(targets, expected_eval, no_refs, observed,
                            docs, doc_count, stats)
        summary["schema"] = SCHEMA
        summary["diagnostic_status"] = "ALL_SCOPED_STAGES_PASSED"
        summary.update(evidence)
        return summary
    except Exception:
        # Fixed stage and aggregate counts only. Do NOT expose Python exception,
        # HF URI, Git document snippet, raw path or PRIVATE job identity.
        if stage not in STAGES:
            stage = "FINAL_AGGREGATION"
        return {
            "schema": SCHEMA,
            "status": "GPU7_R57_STAGE_DIAGNOSTIC_HOLD",
            "failed_stage": stage,
            **evidence,
            "raw_error_or_private_data_exported": False,
            "private_ledgers_modified": False,
            "job_commands_logs_environment_or_training_bytes_read": False,
            "hf_job_started": False,
            "all_original_gpu18_remain_pending": True,
            "source_registry_complete": False,
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
    p.add_argument("--private-gpu7-roots", type=Path,
                   default=DEFAULT_ROOT / "g1_gpu7_completed_other_roots_PRIVATE_20261101.json")
    result = diagnose(p.parse_args())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.get("diagnostic_status") == "ALL_SCOPED_STAGES_PASSED" else 42


if __name__ == "__main__":
    raise SystemExit(main())
