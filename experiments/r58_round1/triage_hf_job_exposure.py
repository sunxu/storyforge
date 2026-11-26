#!/usr/bin/env python3
"""R58 G1: metadata-only Hugging Face Job exposure triage.

Accesses only JobInfo.id, status.stage, and flavor; NEVER accesses job
commands, arguments, environment, secrets, labels, logs, metrics or volumes.
All unknown jobs remain PENDING.  Known evaluation/CPU receipts document
intent, not independently established absence of optimizer operations.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from check_hf_training_job_inventory import (
    JOB_ID,
    KNOWN_SFT_JOBS,
    MAX_JOBS,
    Hold,
    stage_only,
)

SCHEMA = "r58_round1_g1_hf_job_exposure_triage_safe_v1"
PRIVATE_SCHEMA = "r58_round1_g1_hf_job_exposure_triage_private_v1"
# IDs and claimed purposes appear in frozen GitHub SAFE evidence; no private runs.
DOCUMENTED_NO_OPTIMIZER = {
    "v01_validation_evaluation": "6ac794fae7a0dae8a2788ee6",
    "v01_heldout_evaluation": "6ac85c22fee2c90070172dad",
    "v01_checkpoint_sha256_cpu": "6ac8be0e095c578089304f37",
    "r53_cpu40_no_train_preflight": "6ad8a7af0a35baab53a1ced2",
}
GPU_FLAVORS = frozenset({
    "t4-small", "t4-medium", "l4x1", "l4x4", "l40sx1", "l40sx4",
    "l40sx8", "a10g-small", "a10g-large", "a10g-largex2",
    "a10g-largex4", "a100-large", "a100x4", "a100x8",
})
MAX_PRIVATE = 100_000
NAMESPACE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def flavor_class(job) -> str:
    raw = getattr(job, "flavor", None)
    if raw is None:
        return "UNRECOGNIZED"
    if not isinstance(raw, str):
        raise Hold("invalid flavor data")
    if raw.startswith("cpu-") and re.fullmatch(r"cpu-[a-z0-9-]{1,40}", raw):
        return "CPU"
    if raw in GPU_FLAVORS:
        return "GPU"
    return "UNRECOGNIZED"


def summarize_and_private(jobs, namespace: str) -> tuple[dict, dict]:
    if not isinstance(namespace, str) or NAMESPACE.fullmatch(namespace) is None:
        raise Hold("invalid HF namespace")
    all_known = {**KNOWN_SFT_JOBS, **DOCUMENTED_NO_OPTIMIZER}
    if (len(all_known) != len(KNOWN_SFT_JOBS) + len(DOCUMENTED_NO_OPTIMIZER)
            or len(set(all_known.values())) != len(all_known)):
        raise Hold("duplicate documented jobs")
    by_id = {jid: name for name, jid in all_known.items()}
    seen = set()
    stages = Counter()
    unknown_stages = Counter()
    unknown_hw = Counter()
    unknown_stage_hw = Counter()
    known_train_found = {}
    known_referenced_found = {}
    unknown_rows = []
    for job in jobs:
        uid = getattr(job, "id", None)
        if not isinstance(uid, str) or JOB_ID.fullmatch(uid) is None or uid in seen:
            raise Hold("job identity missing/duplicate")
        if len(seen) >= MAX_JOBS or len(unknown_rows) > MAX_PRIVATE:
            raise Hold("job inventory bounded limit exceeded")
        seen.add(uid)
        stage = stage_only(job)
        hardware = flavor_class(job)
        stages[stage] += 1
        role = by_id.get(uid)
        if role in KNOWN_SFT_JOBS:
            known_train_found[role] = stage
        elif role in DOCUMENTED_NO_OPTIMIZER:
            known_referenced_found[role] = {"stage": stage, "hardware_class": hardware}
        else:
            unknown_stages[stage] += 1
            unknown_hw[hardware] += 1
            unknown_stage_hw[(stage, hardware)] += 1
            unknown_rows.append({
                "hf_job_id_PRIVATE": uid,
                "stage": stage,
                "hardware_class": hardware,
                "historical_parameter_update_classification": "PENDING_SOURCE_REVIEW",
                "primary_train_input_provenance": "NOT_VERIFIED",
            })
    if len(seen) != len(known_train_found) + len(known_referenced_found) + len(unknown_rows):
        raise Hold("counts mismatch")
    result = {
        "schema": SCHEMA,
        "status": "R58_G1_HF_METADATA_PRIORITY_TRIAGE_DONE__UNKNOWN_JOB_AND_PRIMARY_SOURCE_HOLD",
        "hf_namespace": namespace,
        "hf_jobs_returned": len(seen),
        "hf_jobs_by_stage": dict(sorted(stages.items())),
        "known_parameter_update_job_ids_expected": len(KNOWN_SFT_JOBS),
        "known_parameter_update_job_ids_found": len(known_train_found),
        "known_documented_non_optimizer_job_ids_expected": len(DOCUMENTED_NO_OPTIMIZER),
        "known_documented_non_optimizer_job_ids_found": len(known_referenced_found),
        "known_documented_non_optimizer_job_roles_found": sorted(known_referenced_found),
        "non_optimizer_role_is_document_claim_only": True,
        "unclassified_job_count": len(unknown_rows),
        "unclassified_job_stage_counts": dict(sorted(unknown_stages.items())),
        "unclassified_job_hardware_counts": dict(sorted(unknown_hw.items())),
        "unclassified_job_stage_hardware_counts": {
            f"{stage}_{hardware}": count
            for (stage, hardware), count in sorted(unknown_stage_hw.items())
        },
        "unclassified_gpu_jobs_excluded_as_non_training": False,
        "unclassified_cpu_jobs_excluded_as_non_training": False,
        "failed_or_canceled_jobs_proven_no_updates": False,
        "job_commands_arguments_env_secrets_logs_labels_read": False,
        "private_job_ids_exported_to_stdout": False,
        "hf_job_listing_historical_completeness_proven": False,
        "other_hf_namespaces_audited": False,
        "remote_training_primary_inputs_rehashed": False,
        "source_registry_complete": False,
        "other_protected_worlds_covered": False,
        "r50_protected_content_accessed": False,
        "g1_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
        "new_job_started": False,
    }
    private = {
        "schema": PRIVATE_SCHEMA,
        "namespace": namespace,
        "status": "PRIVATE_UNKNOWN_JOB_INVENTORY_ONLY__ALL_PENDING",
        "entries": sorted(unknown_rows, key=lambda x: x["hf_job_id_PRIVATE"]),
        "g1_clearance": "HOLD",
        "expansion_allowed": False,
    }
    return result, private


def write_private(path: Path, data: dict) -> None:
    if path.exists() or path.is_symlink():
        raise Hold("private output already exists")
    root = Path.home()/".storyforge-r58-private"
    # Only the established R58 private area, with no user-managed symlinks.
    if (not path.is_absolute() or not path.is_relative_to(root)
            or path.parent.is_symlink() or not path.parent.is_dir()):
        raise Hold("private output outside allowed private root")
    for ancestor in (path.parent, *path.parent.parents):
        if ancestor == Path.home():
            break
        if ancestor.is_symlink():
            raise Hold("private directory symlink forbidden")
    if path.parent.stat().st_mode & 0o077:
        raise Hold("private directory permissions unsafe")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=2, sort_keys=True)
            out.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--namespace", default="adradar")
    p.add_argument("--private-unknown-output", type=Path)
    args = p.parse_args(argv)
    try:
        from huggingface_hub import HfApi
        safe, private = summarize_and_private(
            HfApi().list_jobs(namespace=args.namespace), args.namespace)
        if args.private_unknown_output is not None:
            write_private(args.private_unknown_output, private)
            safe["private_unknown_job_ledger_written"] = True
        print(json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception:
        print("R58_G1_HF_JOB_TRIAGE: HOLD (metadata unavailable/invalid or private output unsafe)",
              file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
