#!/usr/bin/env python3
"""R58 G1 private index readiness preflight.

Reads ONLY the five-row Owner-private provenance inventory. It STATs explicitly
declared source paths; it NEVER opens/reads source index files or R50 contents.
Reports fixed labels and aggregate booleans/counts; no paths, hashes, IDs or raw
inventory values appear in stdout or stderr. NEVER upgrades G1 clearance.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import stat
import sys

SCOPES = (
    "semantic_world_graph",
    "r50_protected_worlds",
    "prior_sft_exposure",
    "r55_r57_dev_worlds",
    "other_protected_or_holdout",
)
COLUMNS = {
    "scope", "private_source_reference", "source_revision", "coverage_status",
    "world_identity_namespace", "independent_review_status",
}
SCHEMA = "r58_round1_g1_index_readiness_safe_v1"
EMPTY = {"", "unknown", "pending", "n/a", "none", "null", "not available", "tbd"}


class Hold(Exception):
    pass


def input_inventory(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 131072:
        raise Hold("private inventory inaccessible")
    if path.stat().st_mode & 0o077:
        raise Hold("private inventory permissions too broad")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rd = csv.DictReader(handle)
        if not rd.fieldnames or set(rd.fieldnames) != COLUMNS:
            raise Hold("invalid evidence inventory columns")
        rows = list(rd)
    if len(rows) != len(SCOPES):
        raise Hold("must have exactly five scope rows")
    out = {}
    for row in rows:
        if None in row or any(v is None for v in row.values()):
            raise Hold("ragged CSV")
        scope = row["scope"].strip()
        if scope not in SCOPES or scope in out:
            raise Hold("duplicate or invalid scope")
        out[scope] = row
    return out


def nonempty(s: str) -> bool:
    return isinstance(s, str) and s.strip().lower() not in EMPTY


def path_present_without_reading(raw: str) -> bool:
    if not nonempty(raw):
        return False
    p = Path(raw.strip()).expanduser()
    if not p.is_absolute():
        return False
    try:
        info = p.lstat()
    except OSError:
        return False
    # symlinks, directories, devices and zero-byte paths are not usable files
    return stat.S_ISREG(info.st_mode) and info.st_size > 0


def readiness(rows: dict) -> dict:
    per_scope = {}
    for scope in SCOPES:
        item = rows[scope]
        ref = item["private_source_reference"]
        file_present = path_present_without_reading(ref)
        revision_recorded = nonempty(item["source_revision"])
        namespace_recorded = nonempty(item["world_identity_namespace"])
        coverage_claim = item["coverage_status"].strip().upper()
        review_claim = item["independent_review_status"].strip().upper()
        if not nonempty(ref):
            status = "MISSING_SOURCE_REFERENCE"
        elif not file_present:
            status = "SOURCE_REFERENCE_NOT_VERIFIED"
        elif not revision_recorded:
            status = "SOURCE_FOUND_REVISION_MISSING"
        elif not namespace_recorded:
            status = "SOURCE_FOUND_WORLD_NAMESPACE_MISSING"
        elif coverage_claim != "OWNER_COVERAGE_ATTESTED":
            status = "SOURCE_FOUND_COVERAGE_UNVERIFIED"
        else:
            status = "OWNER_COVERAGE_CLAIM_ONLY__INDEPENDENT_CHECK_PENDING"
        # Even 'INDEPENDENT_VERIFIED' written into a CSV is a self-claim.
        per_scope[scope] = {
            "status": status,
            "source_file_exists_unopened": file_present,
            "revision_recorded": revision_recorded,
            "world_namespace_recorded": namespace_recorded,
            "owner_coverage_attestation_present": (
                file_present and coverage_claim == "OWNER_COVERAGE_ATTESTED"
            ),
            "independent_review_claim_in_inventory": review_claim == "INDEPENDENT_VERIFIED",
            "independent_review_proven_by_this_tool": False,
            "actual_index_coverage_verified": False,
            "world_isolation_pass": False,
        }
    return {
        "schema": SCHEMA,
        "status": "R58_G1_SOURCE_EXISTENCE_PREFLIGHT_ONLY__WORLD_AND_PROTECTION_HOLD",
        "scope_count": len(per_scope),
        "source_files_present_unopened": sum(
            x["source_file_exists_unopened"] for x in per_scope.values()
        ),
        "owner_coverage_claims_present": sum(
            x["owner_coverage_attestation_present"] for x in per_scope.values()
        ),
        "independently_verified_complete_scopes": 0,
        "scope_readiness": per_scope,
        "source_index_bytes_read": False,
        "protected_test_content_read": False,
        "candidate_story_content_read": False,
        "private_paths_or_identifiers_returned": False,
        "candidate_world_components_certified": 0,
        "g1_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
        "owner_expansion_approval": "REQUIRED",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-inventory", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = readiness(input_inventory(args.private_inventory))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (Hold, OSError, UnicodeError, ValueError, KeyError, TypeError):
        print("R58_G1_INDEX_READINESS: HOLD (private source or schema)", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
