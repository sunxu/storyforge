#!/usr/bin/env python3
"""R58 G2: local-only triage of three frozen target dates against Git release-note dates.

WARNING: This tool verifies and parses the existing PRIVATE source JSONL
(which contains story, user and Assistant text) into memory. It only projects
target_created_at for date buckets; no private field/date/ID/content is printed
or sent anywhere. Use ONLY after Owner explicitly runs this scoped command.

No database, internet, git mutation, HF job, source recapture or file writes.
This is NOT historical deployment proof, request-ID correlation or byte replay.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from capture_priority3 import read_time

SCHEMA = "r58_g2_frozen_target_release_doc_date_triage_safe_v1"
FROZEN_NAME = "priority3_source_20261030_first_capture"
CATEGORIES = (
    "before_2026_10_09_utc",
    "2026_10_09_through_17_utc",
    "2026_10_18_through_27_utc",
    "2026_10_28_through_29_utc",
    "on_or_after_2026_10_30_utc",
)
CUTOFFS = (
    datetime(2026, 10, 9, tzinfo=timezone.utc),
    datetime(2026, 10, 18, tzinfo=timezone.utc),
    datetime(2026, 10, 28, tzinfo=timezone.utc),
    datetime(2026, 10, 30, tzinfo=timezone.utc),
)
EXPECTED_COHORTS = frozenset(("AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"))


class ScopeHold(Exception):
    pass


def bucket(value: str) -> str:
    try:
        moment = read_time(value, "frozen-target").astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError, AttributeError):
        raise ScopeHold("invalid target time") from None
    for i, bound in enumerate(CUTOFFS):
        if moment < bound:
            return CATEGORIES[i]
    return CATEGORIES[-1]


def aggregate_frozen_dates(targets: list[dict]) -> dict:
    if not isinstance(targets, list) or len(targets) != 3:
        raise ScopeHold("not exactly three frozen targets")
    cohorts = [row.get("cohort") if isinstance(row, dict) else None for row in targets]
    if set(cohorts) != EXPECTED_COHORTS or len(set(cohorts)) != 3:
        raise ScopeHold("unrecognized or duplicate frozen cohort")
    summary = Counter({key: 0 for key in CATEGORIES})
    for row in targets:
        summary[bucket(row.get("target_time"))] += 1
    if sum(summary.values()) != 3:
        raise ScopeHold("date accounting drift")
    return {
        "schema": SCHEMA,
        "status": "FROZEN_THREE_TARGET_RELEASE_DOC_DATE_SCOPE_TRIAGED__HISTORICAL_DEPLOYMENT_HOLD",
        "source": "ORIGINAL_OWNER_LOCAL_FROZEN_PRIORITY3_CAPTURE_VERIFIED_IN_MEMORY",
        "private_frozen_source_rows_verified": 3,
        "private_per_case_fingerprints_verified": 12,
        "release_document_date_bucket_counts": dict(summary),
        "reported_release_candidate_catalog_commits": 13,
        "historical_release_candidate_catalog": (
            "docs/evidence/R58_G2_ROLEPLAY_OCT_RELEASE_CODE_BLOB_PARITY_SAFE_20261101.json"
        ),
        "source_data_file_contains_private_narrative_read_locally": True,
        "private_source_content_or_ids_exported": False,
        "raw_target_timestamps_exported": False,
        "per_case_date_or_cohort_binding_exported": False,
        "no_source_files_written": True,
        "production_database_queried": False,
        "hf_job_started": False,
        "git_release_report_proves_target_served_sha": False,
        "release_date_bucket_proves_actual_cutover_interval": False,
        "historical_deployed_sha_proven": False,
        "target_message_to_request_id_link_proven": False,
        "original_provider_request_bytes_verified": False,
        "g1_clearance": "HOLD", "g2_clearance": "HOLD",
        "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def audit(private_dir: Path) -> dict:
    if not isinstance(private_dir, Path):
        raise ScopeHold("private input path required")
    required = Path.home() / ".storyforge-r58-private" / FROZEN_NAME
    # Do not .resolve() a symlinked input. Existing verifier rejects symlinks.
    if ".." in private_dir.parts or private_dir.expanduser().absolute() != required.absolute():
        raise ScopeHold("private input must be the original frozen capture folder")
    # Imported only during explicit Owner CLI execution. This validates all
    # three case fingerprints, file permissions and 0600/0700 boundaries.
    from audit_priority3_request_timeline import fixed_targets
    return aggregate_frozen_dates(fixed_targets(private_dir))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(audit(args.private_dir), sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "FROZEN_TARGET_OR_RELEASE_DATE_METADATA_UNAVAILABLE__G2_HOLD",
            "private_source_content_or_ids_exported": False,
            "raw_target_timestamps_exported": False,
            "no_source_files_written": True,
            "production_database_queried": False,
            "hf_job_started": False,
            "g1_clearance": "HOLD", "g2_clearance": "HOLD",
            "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
            "expansion_allowed": False,
        }, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
