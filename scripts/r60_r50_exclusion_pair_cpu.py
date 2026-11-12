"""Offline, no-leak R50 PRESEAL exclusion-list membership check.

This is NOT R50 final seal/complete exclusion. Uses Owner private 0600 copies.
Never emits the excluded IDs or free-form statuses and never mutates sources.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

try:
    from scripts.r60_r50_freeze_status_projection_cpu import read_private_json
except ModuleNotFoundError:
    from r60_r50_freeze_status_projection_cpu import read_private_json

SCHEMA = "storyforge_r60_r50_exclusion_pair_safe_v1"


def safe_ids(items):
    # Only compare scalar IDs; dicts/compound references require an explicit
    # reviewed mapping policy, never accidental stringification.
    if not isinstance(items, list) or len(items) != 4:
        raise ValueError("FOUR_IDS_SHAPE_HOLD")
    if any(type(v) not in (str, int) or not str(v) or
           (type(v) is str and len(v) > 256) for v in items):
        raise ValueError("EXCLUSION_ID_TYPE_HOLD")
    keys = [(type(v).__name__, str(v)) for v in items]
    if len(set(keys)) != 4:
        raise ValueError("EXCLUSION_ID_DUPLICATE_HOLD")
    return set(keys)


def check(selection: Path, admission: Path):
    result = {
        "schema": SCHEMA,
        "status": "R50_EXCLUSION_PAIR_HOLD",
        "reason_code": "UNVERIFIED",
        "selection_excluded_count": 0,
        "admission_excluded_count": 0,
        "exclusion_id_sets_equal": False,
        "final_heldout_seal_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    try:
        if selection.resolve(strict=False) == admission.resolve(strict=False):
            raise ValueError("DUPLICATE_INPUT_HOLD")
        a, b = read_private_json(selection), read_private_json(admission)
        if (type(a.get("original_case_count")) is not int
            or a["original_case_count"] != 50
            or type(a.get("selected_case_count")) is not int
            or a["selected_case_count"] != 46
            or type(b.get("candidate_case_count")) is not int
            or b["candidate_case_count"] != 46
            or type(b.get("excluded_case_count")) is not int
            or b["excluded_case_count"] != 4
            or a.get("owner_exclusion_authorized") is not True):
            raise ValueError("COUNT_OR_AUTH_HOLD")
        x, y = a.get("excluded_cases"), b.get("exclude_ids")
        result["selection_excluded_count"] = len(x) if isinstance(x, list) else 0
        result["admission_excluded_count"] = len(y) if isinstance(y, list) else 0
        xids, yids = safe_ids(x), safe_ids(y)
        result["exclusion_id_sets_equal"] = (xids == yids)
        if not result["exclusion_id_sets_equal"]:
            raise ValueError("EXCLUSION_ID_SET_MISMATCH_HOLD")
        result.update(status="R50_PRESEAL_FOUR_EXCLUSIONS_MATCH__SEAL_HOLD",
                      reason_code="FOUR_EXCLUSION_IDS_MATCH")
    except Exception as exc:
        known = {"DUPLICATE_INPUT_HOLD", "COUNT_OR_AUTH_HOLD",
                 "FOUR_IDS_SHAPE_HOLD", "EXCLUSION_ID_TYPE_HOLD",
                 "EXCLUSION_ID_DUPLICATE_HOLD",
                 "EXCLUSION_ID_SET_MISMATCH_HOLD"}
        result["reason_code"] = str(exc) if isinstance(exc, ValueError) and str(exc) in known else "SOURCE_FORMAT_OR_RUNTIME_HOLD"
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--admission", type=Path, required=True)
    a = ap.parse_args()
    result = check(a.selection, a.admission)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "R50_PRESEAL_FOUR_EXCLUSIONS_MATCH__SEAL_HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())
