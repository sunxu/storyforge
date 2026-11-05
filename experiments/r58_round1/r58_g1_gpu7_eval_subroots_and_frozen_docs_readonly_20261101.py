#!/usr/bin/env python3
"""R58 G1: corrected evaluation-runs subroot match, seven completed GPU Jobs.

The old diagnostic incorrectly required four evaluation-runs-linked Jobs to
appear within v03-r57, but only two were observed there. This tool checks
the exact four against the five already-known evaluation-runs subroots and
counts frozen Git HEAD documentation references for those four and the other
three. Reads only file/directory NAMES and PRIVATE metadata ledger contents;
does not read HF file bytes, Job logs/commands, training text, R50 items.
Does not write files or launch any HF Job. Everything stays G1/G2 HOLD.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess

from r58_g1_other_three_jobs_private_ledger_crosscheck_safe import (
    BUCKET, DEFAULT_ROOT, read_private,
)
from r58_g1_gpu18_bucket_metadata_coverage_readonly_20261101 import verify_ledger
from r58_g1_gpu7_completed_other_bucket_roots_metadata_safe_20261101 import (
    RE_TOKEN, completed_missing,
)
from r58_g1_gpu7_r57_and_git_doc_links_readonly_20261101 import (
    BRANCH, verify_other_roots,
)
from check_hf_job_documentation_coverage import frozen_job_mentions

SCHEMA = "r58_g1_gpu7_eval_subroots_and_frozen_docs_safe_v1"
SUBROOTS = ("test", "v02-r47", "v03-r55", "v03-r57", "validation")
MAX_OBJECTS_TOTAL = 1200
MAX_LIST_CALLS_TOTAL = 200
MAX_DEPTH = 10


class Hold(Exception):
    pass


def canonical(uri: str) -> str:
    if not isinstance(uri, str):
        raise Hold("invalid Bucket URI")
    return uri.removeprefix("hf://").lstrip("/").rstrip("/")


def scan_eval_subroots(fs, targets: set[str]) -> tuple[dict, dict[str, set[str]]]:
    """Metadata-only traversal, all five subroots; fail closed if incomplete."""
    if len(targets) != 7 or not all(isinstance(x, str) for x in targets):
        raise Hold("incorrect target cohort size")
    parent = BUCKET + "/evaluation-runs"
    parent_c = canonical(parent)
    children = fs.ls(parent, detail=True)
    if not isinstance(children, list) or len(children) != len(SUBROOTS):
        raise Hold("subroot scope drift")
    roots = {}
    for child in children:
        if not isinstance(child, dict):
            raise Hold("malformed subroot metadata")
        raw = child.get("name", child.get("path"))
        typ = child.get("type")
        name = canonical(raw)
        if (typ not in ("directory", "dir")
                or not name.startswith(parent_c + "/")
                or name[len(parent_c) + 1:] not in SUBROOTS):
            raise Hold("unexpected evaluation-runs subroot")
        key = name[len(parent_c) + 1:]
        if key in roots:
            raise Hold("duplicate subroot")
        roots[key] = raw if raw.startswith("hf://") else "hf://" + name
    if set(roots) != set(SUBROOTS):
        raise Hold("missing subroot")

    per_root = {}
    refs: dict[str, set[str]] = defaultdict(set)
    total_calls = 1
    total_nodes = len(children)
    for key in SUBROOTS:
        base = roots[key]
        base_c = canonical(base)
        stack = [(base, 0)]
        visited = set()
        matched = set()
        artifact_counts = {
            "trainer_state_json_named": 0,
            "optimizer_pt_named": 0,
            "model_safetensors_named": 0,
            "train_validation_jsonl_named": 0,
        }
        sub_calls = 0
        sub_nodes = 0
        while stack:
            directory, depth = stack.pop()
            if (depth > MAX_DEPTH or directory in visited
                    or total_calls >= MAX_LIST_CALLS_TOTAL):
                raise Hold("metadata recursion limit")
            visited.add(directory)
            total_calls += 1
            sub_calls += 1
            parts = fs.ls(directory, detail=True)
            if not isinstance(parts, list):
                raise Hold("invalid metadata response")
            for obj in parts:
                if not isinstance(obj, dict):
                    raise Hold("malformed Bucket object")
                raw = obj.get("name", obj.get("path"))
                typ = obj.get("type")
                node = canonical(raw)
                if (not node.startswith(base_c + "/")
                        or typ not in ("directory", "dir", "file", "link")):
                    raise Hold("out-of-scope or unexpected Bucket node")
                total_nodes += 1
                sub_nodes += 1
                if total_nodes > MAX_OBJECTS_TOTAL:
                    raise Hold("metadata object limit")
                matched_here = set(RE_TOKEN.findall(node)) & targets
                for job_id in matched_here:
                    refs[job_id].add(key)
                    matched.add(job_id)
                if typ in ("directory", "dir"):
                    if depth + 1 > MAX_DEPTH:
                        raise Hold("metadata depth limit")
                    stack.append((raw if raw.startswith("hf://")
                                  else "hf://" + node, depth + 1))
                else:
                    base_name = node.rsplit("/", 1)[-1]
                    if base_name == "trainer_state.json":
                        artifact_counts["trainer_state_json_named"] += 1
                    if base_name == "optimizer.pt":
                        artifact_counts["optimizer_pt_named"] += 1
                    if base_name.endswith(".safetensors"):
                        artifact_counts["model_safetensors_named"] += 1
                    if base_name in ("train.jsonl", "validation.jsonl"):
                        artifact_counts["train_validation_jsonl_named"] += 1
        per_root[key] = {
            "metadata_list_calls": sub_calls,
            "metadata_nodes": sub_nodes,
            "gpu7_exact_path_name_matches": len(matched),
            **artifact_counts,
        }
    return {
        "per_subroot": per_root,
        "total_metadata_list_calls": total_calls,
        "total_metadata_nodes": total_nodes,
    }, dict(refs)


def summarize(eval_ids: set[str], other_three: set[str],
              path_refs: dict[str, set[str]], docs: set[str],
              n_docs: int, stats: dict) -> dict:
    if (len(eval_ids) != 4 or len(other_three) != 3
            or eval_ids & other_three or len(docs) < 1 or n_docs < 1):
        raise Hold("invalid source cohort")
    found = set(path_refs)
    if found != eval_ids:
        raise Hold("evaluation-runs root mapping disagrees with frozen 4/3 ledger")
    r57_ids = {k for k,v in path_refs.items() if "v03-r57" in v}
    if len(r57_ids) != 2:
        raise Hold("R57 diagnostic two-of-four evidence changed")
    overlaps = sum(len(v) > 1 for v in path_refs.values())
    if sum(v["gpu7_exact_path_name_matches"] for v in stats["per_subroot"].values()) < 4:
        raise Hold("subroot accounting inconsistent")
    return {
        "schema": SCHEMA,
        "status": "GPU7_EVAL_SUBROOT_DISTRIBUTION_AND_FROZEN_DOC_REFS_CHECKED__ALL_PENDING",
        "namespace": "adradar",
        "original_completed_gpu7": 7,
        "original_eval_runs_name_linked": 4,
        "original_five_root_name_unlinked": 3,
        "eval_subroots_scanned": list(SUBROOTS),
        "per_subroot_metadata": stats["per_subroot"],
        "metadata_list_calls": stats["total_metadata_list_calls"],
        "metadata_nodes": stats["total_metadata_nodes"],
        "unique_gpu7_linked_in_eval_subroots": len(found),
        "r57_specific_subroot_exact_matches": len(r57_ids),
        "linked_four_with_any_other_eval_subroot": sum(
            any(x != "v03-r57" for x in v) for v in path_refs.values()
        ),
        "linked_four_referenced_in_multiple_eval_subroots": overlaps,
        "git_head_documents_scanned": n_docs,
        "linked_four_with_git_doc_reference": len(eval_ids & docs),
        "linked_four_without_git_doc_reference": len(eval_ids - docs),
        "other_three_with_git_doc_reference": len(other_three & docs),
        "other_three_without_git_doc_reference": len(other_three - docs),
        "job_id_or_path_exported": False,
        "raw_error_exported": False,
        "git_document_reference_proves_job_role": False,
        "eval_root_path_proves_evaluation_only": False,
        "file_absence_proves_no_optimizer_update": False,
        "historical_input_consumption_proven": False,
        "optimizer_step_directly_proven": False,
        "all_original_gpu18_remain_pending": True,
        "all_historical_job_roots_exhausted": False,
        "source_registry_complete": False,
        "private_ledgers_modified": False,
        "job_commands_logs_environment_or_training_bytes_read": False,
        "hf_job_started": False,
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
    p.add_argument("--private-gpu18-coverage", type=Path,
                   default=DEFAULT_ROOT / "g1_gpu18_bucket_prefix_metadata_PRIVATE_20261101.json")
    p.add_argument("--private-gpu7-roots", type=Path,
                   default=DEFAULT_ROOT / "g1_gpu7_completed_other_roots_PRIVATE_20261101.json")
    a = p.parse_args()
    stage = "REPOSITORY_BRANCH"
    try:
        repo = a.repo_root.resolve(strict=True)
        b = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                           capture_output=True, text=True, timeout=8, check=True)
        if b.stdout.strip() != BRANCH:
            raise Hold("incorrect R58 branch")
        stage = "PRIVATE_FROZEN_LEDGER"
        unknown = read_private(a.private_unknown_ledger)
        priority = read_private(a.private_priority_ledger)
        coverage = read_private(a.private_gpu18_coverage)
        roots = read_private(a.private_gpu7_roots)
        gpu, focus = verify_ledger(unknown, priority)
        ids = completed_missing(coverage, gpu, focus)
        eval_ids, three = verify_other_roots(roots, ids)
        stage = "FROZEN_GIT_HEAD_DOCS"
        docs, doc_count = frozen_job_mentions(repo)
        stage = "EVAL_RUNS_SUBROOT_DIRECTORY_NAMES"
        from huggingface_hub import HfFileSystem
        metadata, refs = scan_eval_subroots(HfFileSystem(), ids)
        stage = "EXACT_SET_AND_DOC_AGGREGATION"
        result = summarize(eval_ids, three, refs, docs, doc_count, metadata)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "GPU7_EVAL_SUBROOT_OR_DOC_EVIDENCE_UNAVAILABLE__G1_HOLD",
            "failed_stage": stage,
            "job_id_or_path_exported": False,
            "raw_error_exported": False,
            "private_ledgers_modified": False,
            "hf_job_started": False,
            "g1_clearance": "HOLD", "g2_clearance": "HOLD",
            "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
            "expansion_allowed": False,
        }, sort_keys=True, ensure_ascii=False, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
