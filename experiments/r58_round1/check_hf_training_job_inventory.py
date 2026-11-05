#!/usr/bin/env python3
"""R58 G1: enumerate existing HF Jobs, read-only, aggregate-only, fail closed.

Uses HfApi.list_jobs(namespace=...). Does not create Jobs, read secrets,
commands/arguments/logs, fetch Buckets, inspect samples, or update private
G1 ledgers. A Jobs listing alone CANNOT establish complete model exposure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter

SCHEMA = "r58_round1_g1_hf_job_inventory_safe_v1"
# These IDs are already in frozen GitHub public audit docs, not secret values.
KNOWN_SFT_JOBS = {
    "v01_rank32_smoke": "6ac73cabe7a0dae8a278117a",
    "v01_rank64_capacity": "6ac74ce3df2184ac91ac8f43",
    "v01_rank64_baseline": "6ac75bafdf2184ac91acb293",
    "r46_exploratory_sft": "6acf29e4c66288145223871b",
    "r54_v2_sft": "6ad8e60f5275124786e27d21",
}
ALLOWED_STAGES = frozenset({
    "COMPLETED", "ERROR", "CANCELED", "DELETED", "RUNNING", "SCHEDULING"
})
JOB_ID = re.compile(r"^[0-9a-f]{24}$")
MAX_JOBS = 100_000

class Hold(Exception):
    pass


def stage_only(job) -> str:
    """The only field besides job.id accessed from JobInfo."""
    status = getattr(job, "status", None)
    stage = getattr(status, "stage", None)
    if stage is None:
        raise Hold("job status absent")
    value = getattr(stage, "value", stage)
    if not isinstance(value, str) or value not in ALLOWED_STAGES:
        raise Hold("job stage unexpected")
    return value


def summarize(jobs, namespace: str) -> dict:
    if not isinstance(namespace, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", namespace):
        raise Hold("namespace invalid")
    seen = set()
    stages = Counter()
    known_stages = {}
    unknown = 0
    expected_by_id = {value: key for key, value in KNOWN_SFT_JOBS.items()}
    if len(expected_by_id) != len(KNOWN_SFT_JOBS):
        raise Hold("known job roster duplicates")
    for job in jobs:
        raw = getattr(job, "id", None)
        if not isinstance(raw, str) or JOB_ID.fullmatch(raw) is None or raw in seen:
            raise Hold("malformed/duplicate returned HF Job identity")
        if len(seen) >= MAX_JOBS:
            raise Hold("HF Job listing exceeds safe limit")
        seen.add(raw)
        stage = stage_only(job)
        stages[stage] += 1
        if raw in expected_by_id:
            known_stages[expected_by_id[raw]] = stage
        else:
            unknown += 1
    matched = len(known_stages)
    missing = len(KNOWN_SFT_JOBS) - matched
    return {
        "schema": SCHEMA,
        "status": (
            "R58_G1_HF_JOBS_ENUMERATED__ALL_KNOWN_IDS_PRESENT__PRIMARY_INPUT_AND_COMPLETENESS_HOLD"
            if not missing else
            "R58_G1_HF_JOBS_ENUMERATED__KNOWN_IDS_MISSING__PRIMARY_INPUT_AND_COMPLETENESS_HOLD"
        ),
        "queried_namespace": namespace,
        "hf_jobs_returned": len(seen),
        "hf_jobs_by_stage": dict(sorted(stages.items())),
        "known_sft_or_training_smoke_job_ids_expected": len(KNOWN_SFT_JOBS),
        "known_sft_or_training_smoke_job_ids_found": matched,
        "known_sft_or_training_smoke_job_ids_missing": missing,
        "known_job_stage_by_role": dict(sorted(known_stages.items())),
        "other_job_ids_unclassified": unknown,
        "all_jobs_across_other_namespaces_verified": False,
        "hf_listing_retention_or_historical_completeness_proven": False,
        "unknown_jobs_proven_non_training": False,
        "remote_trainer_primary_input_bytes_verified": False,
        "all_actual_sft_runs_and_input_sources_proven_complete": False,
        "other_protected_uuids_covered": False,
        "source_registry_complete": False,
        "r50_protected_content_accessed": False,
        "job_commands_arguments_environment_or_secrets_read_or_exported": False,
        "training_started": False,
        "g1_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--namespace", default="adradar",
                   help="Explicit HF namespace; requires locally stored HF authentication")
    args = p.parse_args(argv)
    try:
        # Lazy import: unit tests require only Python stdlib and never network.
        from huggingface_hub import HfApi
        result = summarize(HfApi().list_jobs(namespace=args.namespace), args.namespace)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception:
        # Never print HTTP error bodies, tokens, commands, private HF Job metadata.
        print("R58_G1_HF_JOB_INVENTORY: HOLD (authenticated listing unavailable or invalid)",
              file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
