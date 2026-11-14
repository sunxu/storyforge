"""Create-only private R50 known-five source quarantine for 339 V123 candidates.

This is a PARTIAL exclusion only. The 336 remaining candidates stay HOLD.
No remote model, DB, GPU, training admission, or private values in SAFE stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_exclusion_cpu as known
import r60_real1000_v123_crosswalk as crosswalk
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_real1000_r50_known5_quarantine_private_v1"
SAFE = "storyforge_r60_real1000_r50_known5_quarantine_safe_v1"
FILENAME = "R60_REAL1000_R50_KNOWN5_QUARANTINE_PRIVATE.json"
MAX_PRIVATE_REPORT = 200_000


class Hold(ValueError):
    pass


def construct(cases: list[dict], report: dict, report_sha256: str) -> dict:
    identity_safe = identity.audit(cases, report)
    entries = report["entries"]
    if len(entries) != 339:
        raise Hold("CANDIDATE_SCOPE_HOLD")
    flagged, pending = [], []
    for entry in entries:
        case = cases[entry["position"] - 1]
        source = case["source"]
        item = {
            "position": entry["position"],
            "case_key": entry["case_key"],
            "v1_receipt_sha256": entry["v1_receipt_sha256"],
        }
        if source["story_id"] in known.KNOWN_R50_STORIES:
            flagged.append({
                **item,
                "reason_code": "R50_KNOWN5_SOURCE_STORY_OVERLAP",
                # No story UUIDs or original text needed in the manifest.
            })
        else:
            pending.append({
                **item,
                "status": "PARTIAL_KNOWN5_CLEAR__FULL_R50_HOLD",
            })
    if (len(flagged) !=
            identity_safe["r50_known5_candidate_overlap_count"]
            or len(flagged) + len(pending) != 339):
        raise Hold("KNOWN5_SOURCE_SET_DRIFT_HOLD")
    return {
        "schema": SCHEMA,
        "status": "R50_KNOWN5_QUARANTINE__FULL_R50_HOLD",
        "source_crosswalk_sha256": report_sha256,
        "source_reference": known.REFERENCE_DOC,
        "known_story_reference_count": len(known.KNOWN_R50_STORIES),
        "original_candidate_count": 339,
        "excluded_known5": flagged,
        "remaining_full_r50_hold": pending,
        "r50_complete_exclusion_verified": False,
        "historical_system_snapshot_verified": False,
        "world_isolation_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "gold_promoted": False,
    }


def run(old_dir: Path, plan_dir: Path, v2_dir: Path, v3_dir: Path,
        audit_dir: Path, output_dir: Path, *, write: bool) -> dict:
    if (output_dir.parent != private.BASE
            or not output_dir.name.startswith(
                "r60-real1000-r50-known5-quarantine-")
            or output_dir.is_symlink()
            or output_dir in (old_dir, plan_dir, v2_dir, v3_dir, audit_dir)
            or output_dir.exists() and write):
        raise Hold("QUARANTINE_OUTPUT_PATH_HOLD")
    cases, report = identity.verified_cases_report(
        old_dir, plan_dir, v2_dir, v3_dir, audit_dir)
    report_raw = private.read_private(
        audit_dir / crosswalk.FILENAME, crosswalk.MAX_REPORT)
    manifest = construct(
        cases, report, hashlib.sha256(report_raw).hexdigest())
    excluded = len(manifest["excluded_known5"])
    remaining = len(manifest["remaining_full_r50_hold"])
    safe = {
        "schema": SAFE,
        "status": ("R50_KNOWN5_QUARANTINE_SAVED__FULL_R50_HOLD"
                   if write else "R50_KNOWN5_QUARANTINE_PREFLIGHT__NO_FILES"),
        "original_candidate_count": 339,
        "known5_excluded_count": excluded,
        "known5_overlapping_story_count":
            len({cases[item["position"] - 1]["source"]["story_id"]
                 for item in manifest["excluded_known5"]}),
        "remaining_full_r50_hold": remaining,
        "r50_complete_exclusion_verified": False,
        "historical_system_snapshot_verified": False,
        "world_isolation_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0, "gold_promoted": False,
        "model_requests": 0, "gpu_started": False,
        "database_modified": False, "private_values_emitted": False,
    }
    if write:
        blob = (json.dumps(
            manifest, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")) + "\n").encode()
        if len(blob) > min(MAX_PRIVATE_REPORT, private.MAX_CAPTURE_BYTES):
            raise Hold("QUARANTINE_REPORT_SIZE_HOLD")
        private.private_dir(output_dir, create=True)
        private.write_new(output_dir / FILENAME, blob)
    return safe


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--old-dir", type=Path, required=True)
    p.add_argument("--plan-dir", type=Path, required=True)
    p.add_argument("--v2-dir", type=Path, required=True)
    p.add_argument("--v3-dir", type=Path, required=True)
    p.add_argument("--audit-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--write-private-report", action="store_true")
    args = p.parse_args()
    try:
        result = run(
            args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir,
            args.audit_dir, args.output_dir, write=args.write_private_report)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        code = str(exc)
        if (type(exc) not in {
            Hold, identity.Hold, crosswalk.Hold, private.Hold
        } or not re.fullmatch(r"[A-Z][A-Z0-9_]{3,79}", code)):
            code = "QUARANTINE_LOCAL_RUNTIME_HOLD"
        print(json.dumps({
            "schema": SAFE, "status": "R50_KNOWN5_QUARANTINE_HOLD",
            "reason_code": code,
            "train_admitted": 0, "private_values_emitted": False,
            "model_requests": 0, "gpu_started": False,
            "database_modified": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
