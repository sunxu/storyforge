"""R58 G2: offline bounded check of Owner's existing deployment interval metadata.

This is intentionally a STRUCTURAL preflight, not a historical attestation.
Never queries production, reads story text, verifies signatures, or grants G2.
Private timestamps/SHAs/host identities stay in the owner-only 0600 manifest.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

from r58_g1_scope_reconcile import Hold, read_private

SCHEMA = "r58_g2_private_deployment_interval_manifest_v1"
RESULT_SCHEMA = "r58_g2_deployment_interval_structural_check_safe_v1"
SOURCE_PIN = "e9fe29c42434caeb0bac5acc91845ab4741ecb2b"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
UTC_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
BACKENDS = frozenset(("PRIMARY", "V2_REPLICA", "FALLBACK", "MIGRATION", "UNKNOWN"))
ACTIVATION = frozenset((
    "SUCCESS_CUTOVER_RECEIPT_REPORTED", "ARCHIVED_STAGE_ONLY",
    "CURRENT_DEPLOYED_SHA_ONLY", "UNKNOWN",
))
TERMINATION = frozenset((
    "NEXT_CUTOVER_RECEIPT_REPORTED", "ROLLBACK_RECEIPT_REPORTED", "UNKNOWN",
))
MAX_INTERVALS = 96


def require_keys(value: object, keys: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise Hold("deployment metadata fields invalid")
    return value


def parse_instant(value: object) -> datetime:
    if not isinstance(value, str) or not UTC_INSTANT.fullmatch(value):
        raise Hold("UTC time must be seconds-precision Z")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        raise Hold("invalid UTC time") from None
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise Hold("noncanonical UTC time")
    return parsed


def analyze(manifest: dict) -> dict:
    require_keys(manifest, {"schema", "source_pin", "frozen_target_claims", "deployment_intervals"})
    if manifest["schema"] != SCHEMA or manifest["source_pin"] != SOURCE_PIN:
        raise Hold("source pin mismatch")

    claims = manifest["frozen_target_claims"]
    if not isinstance(claims, list) or len(claims) != 3:
        raise Hold("expected three frozen targets")
    targets = []
    for case in claims:
        require_keys(case, {"generated_at_utc", "serving_backend"})
        role = case["serving_backend"]
        if not isinstance(role, str) or role not in BACKENDS:
            raise Hold("invalid claimed target backend")
        targets.append((parse_instant(case["generated_at_utc"]), role))
    if len({t for t, _ in targets}) != 3 or targets != sorted(targets, key=lambda x: x[0]):
        raise Hold("frozen target times must be distinct and ordered")

    raw_intervals = manifest["deployment_intervals"]
    if not isinstance(raw_intervals, list) or len(raw_intervals) > MAX_INTERVALS:
        raise Hold("deployment interval roster invalid")
    intervals = []
    for entry in raw_intervals:
        require_keys(entry, {
            "serving_backend", "deploy_sha", "active_from_utc", "active_until_utc",
            "activation_receipt_type", "termination_receipt_type",
            "activation_receipt_sha256", "termination_receipt_sha256",
        })
        role, sha = entry["serving_backend"], entry["deploy_sha"]
        if (not isinstance(role, str) or role not in BACKENDS - {"UNKNOWN"}
                or not isinstance(sha, str) or not SHA40.fullmatch(sha)):
            raise Hold("invalid interval backend or SHA")
        start = parse_instant(entry["active_from_utc"])
        end = parse_instant(entry["active_until_utc"])
        if start >= end:
            raise Hold("invalid deployment time interval")
        start_type = entry["activation_receipt_type"]
        end_type = entry["termination_receipt_type"]
        if (not isinstance(start_type, str) or start_type not in ACTIVATION
                or not isinstance(end_type, str) or end_type not in TERMINATION):
            raise Hold("invalid source evidence class")
        start_pin = entry["activation_receipt_sha256"]
        end_pin = entry["termination_receipt_sha256"]
        if (not isinstance(start_pin, str) or not SHA64.fullmatch(start_pin)
                or not isinstance(end_pin, str) or not SHA64.fullmatch(end_pin)
                or start_pin == end_pin):
            raise Hold("invalid or repeated local source fingerprint")
        intervals.append((role, sha, start, end, start_type, end_type))
    if intervals != sorted(intervals, key=lambda x: (x[0], x[2])):
        raise Hold("intervals must be sorted by backend and activation")
    for prior, current in pairwise(intervals):
        if prior[0] == current[0] and prior[3] > current[2]:
            raise Hold("overlapping deployment claims for the same backend")

    structurally_covered = 0
    pinned_source_covered = 0
    reportedly_bracketed = 0
    unknown_backend = 0
    for instant, role in targets:
        if role == "UNKNOWN":
            unknown_backend += 1
            continue
        matches = [iv for iv in intervals if iv[0] == role and iv[2] <= instant < iv[3]]
        if len(matches) > 1:
            raise Hold("ambiguous target coverage")
        if not matches:
            continue
        structurally_covered += 1
        _role, sha, _start, _end, from_type, until_type = matches[0]
        if sha == SOURCE_PIN:
            pinned_source_covered += 1
        if (from_type == "SUCCESS_CUTOVER_RECEIPT_REPORTED"
                and until_type in ("NEXT_CUTOVER_RECEIPT_REPORTED", "ROLLBACK_RECEIPT_REPORTED")):
            reportedly_bracketed += 1

    return {
        "schema": RESULT_SCHEMA,
        "status": "PRIVATE_DEPLOYMENT_INTERVALS_STRUCTURALLY_CHECKED__HISTORICAL_SOURCE_UNAUTHENTICATED_HOLD",
        "owner_supplied_target_time_claims": 3,
        "owner_supplied_interval_count": len(intervals),
        "target_backend_unknown_count": unknown_backend,
        "structurally_covered_target_count": structurally_covered,
        "claimed_source_pin_target_count": pinned_source_covered,
        "reported_start_end_receipts_target_count": reportedly_bracketed,
        "historical_deployment_receipt_authenticity_independently_verified": False,
        "frozen_target_identity_and_time_independently_bound": False,
        "historical_production_routing_independently_verified": False,
        "target_time_deployed_sha_proven": False,
        "request_to_target_direct_link_proven": False,
        "provider_original_request_bytes_verified": False,
        "input_timestamps_shas_receipt_digests_or_host_ids_exported": False,
        "production_accessed": False,
        "private_evidence_written": False,
        "g1_clearance": "HOLD",
        "g2_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = Path.home() / ".storyforge-r58-private"
        private = read_private(args.private_manifest, root)
        result = analyze(private)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError, OverflowError):
        print("R58_G2_DEPLOY_INTERVAL: HOLD (private evidence missing/inconsistent)", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
