#!/usr/bin/env python3
"""Owner-only R58 G2: triage 3 frozen timestamps vs five Owner-reported events.

Requires explicit Owner local execution. Existing PRIVATE source JSONL
(including story/narrative bytes) is fully read and its 12 fingerprints
verified IN MEMORY, only to extract three target timestamps. No timestamp,
case identifier, cohort, text or per-case result is exported.

All event cutovers are historical Git document CLAIMS, NOT authenticated
production routing, deployment SHA, model configuration or provider bytes.
No new database query, source capture, file writing, HF or network access.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path

from capture_priority3 import Hold as PrivateHold, read_time

SCHEMA = "r58_g2_frozen_target_reported_cutover_window_safe_v1"
FIXED_FOLDER = "priority3_source_20261030_first_capture"
EXPECTED_COHORTS = frozenset(("AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"))
# UTC times transcribed from pinned OWNER release/runtime reports; NOT
# independently authenticated cutover/active-backend evidence.
REPORTED_EVENTS = (
    ("2026-10-28T01:36:59Z", "OWNER_REPORTED_APP_CUTOVER_6DC474B9"),
    ("2026-10-28T07:28:16Z", "OWNER_REPORTED_APP_CUTOVER_9D45083F"),
    ("2026-10-28T08:57:00Z", "OWNER_REPORTED_MODEL_CATALOG_REV_9_TO_10"),
    ("2026-10-29T01:02:47Z", "OWNER_REPORTED_APP_CUTOVER_8F9E5626"),
    ("2026-10-29T04:07:06Z", "OWNER_REPORTED_APP_CUTOVER_A11D55F3"),
    ("2026-10-30T00:00:00Z", "UTC_DATE_BOUNDARY_NOT_A_DEPLOYMENT_EVENT"),
)
WINDOW_IDS = tuple(f"window_{i}" for i in range(len(REPORTED_EVENTS) + 1))


class ScopeHold(Exception):
    pass


def parse_time(s: str) -> datetime:
    try:
        v = read_time(s, "frozen-target")
        return v.astimezone(UTC)
    except (PrivateHold, ValueError, TypeError, OverflowError, AttributeError):
        raise ScopeHold("invalid date/time") from None


def event_boundaries() -> tuple[datetime, ...]:
    values = tuple(parse_time(x[0]) for x in REPORTED_EVENTS)
    if tuple(sorted(values)) != values or len(set(values)) != len(values):
        raise ScopeHold("reported event ordering invalid")
    return values


def summarize(targets: list[dict]) -> dict:
    if not isinstance(targets, list) or len(targets) != 3:
        raise ScopeHold("expected three frozen targets")
    cohorts = [r.get("cohort") if isinstance(r, dict) else None for r in targets]
    if len(set(cohorts)) != 3 or set(cohorts) != EXPECTED_COHORTS:
        raise ScopeHold("incorrect cohort set")
    boundaries = event_boundaries()
    histogram = Counter({k: 0 for k in WINDOW_IDS})
    for case in targets:
        ts = parse_time(case.get("target_time"))
        idx = bisect_right(boundaries, ts)
        histogram[WINDOW_IDS[idx]] += 1
    if sum(histogram.values()) != 3:
        raise ScopeHold("count mismatch")
    return {
        "schema": SCHEMA,
        "status": "THREE_FROZEN_TARGETS_SORTED_VS_REPORTED_LATE_OCT_EVENTS__DEPLOYMENT_HOLD",
        "source_record_count": 3,
        "existing_local_fingerprints_reverified": 12,
        "total_comparison_boundary_count": len(REPORTED_EVENTS),
        "owner_reported_event_count": len(REPORTED_EVENTS) - 1,
        "owner_reported_cutover_window_counts": dict(histogram),
        "window_labels_in_pinned_git_source_only": True,
        "all_cutover_dates_and_runtime_changes_are_owner_reported": True,
        "time_window_proves_active_deployment_or_backend": False,
        "private_full_source_jsonl_read_in_memory": True,
        "private_raw_timestamp_or_identity_exported": False,
        "case_to_cohort_or_window_mapping_exported": False,
        "source_files_written": False,
        "production_database_queried": False,
        "hf_job_started": False,
        "actual_historical_deployment_sha_proven": False,
        "historical_runtime_model_version_proven": False,
        "target_to_api_request_id_proven": False,
        "original_provider_request_bytes_verified": False,
        "g1_clearance": "HOLD", "g2_clearance": "HOLD",
        "g3_status": "NOT_STARTED",
        "train_admitted": 0, "validation_admitted": 0,
        "teacher_admitted": 0, "expansion_allowed": False,
    }


def audit(private_dir: Path) -> dict:
    expected = Path.home() / ".storyforge-r58-private" / FIXED_FOLDER
    if (".." in private_dir.parts
            or private_dir.expanduser().absolute() != expected.absolute()):
        raise ScopeHold("not the original frozen source location")
    # This existing verifier rejects symlinks, wrong permissions and
    # fingerprint mismatches, and parses full PRIVATE story content locally.
    from audit_priority3_request_timeline import fixed_targets
    return summarize(fixed_targets(private_dir))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(audit(args.private_dir), sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "PRIVATE_FROZEN_INPUT_OR_REPORTED_EVENT_CHECK_UNAVAILABLE__G2_HOLD",
            "raw_private_values_exported": False,
            "source_files_written": False,
            "hf_job_started": False,
            "g1_clearance": "HOLD", "g2_clearance": "HOLD",
            "train_admitted": 0, "validation_admitted": 0,
            "teacher_admitted": 0, "expansion_allowed": False,
        }, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
