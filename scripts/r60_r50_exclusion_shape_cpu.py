"""Read-only structural diagnosis of the two R50 four-item exclusion arrays.

Output only type counts and known, hard-coded field names. Never print source
values, source-defined field names, individual IDs, raw strings, or hashes.
The probe cannot validate exclusion equivalence, R50 seal, or training admission.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

try:
    from scripts.r60_r50_freeze_status_projection_cpu import read_private_json
except ModuleNotFoundError:
    from r60_r50_freeze_status_projection_cpu import read_private_json

SCHEMA = "storyforge_r60_r50_exclusion_shape_safe_v1"
# Known source *schema vocabulary*, not values or discovered dynamic keys.
KNOWN_FIELDS = frozenset({
    "case_id", "id", "source_case_id", "excluded_case_id", "case_number",
    "position", "line_number", "source_line", "source_line_number",
    "original_line", "original_line_number", "parent_line",
    "reason", "reason_code", "status", "decision", "world_id",
    "source_story_id", "story_number", "source_session_id",
    "history_message_ids", "cutoff_message_id",
})


def kind(x):
    if x is None:
        return "null"
    if type(x) is bool:
        return "boolean"
    if type(x) is int:
        return "integer"
    if type(x) is float:
        return "number"
    if type(x) is str:
        return "string"
    if type(x) is dict:
        return "object"
    if type(x) is list:
        return "array"
    return "unknown"


def signature(items):
    if not isinstance(items, list) or len(items) != 4:
        raise ValueError("FOUR_ENTRIES_HOLD")
    types = Counter(kind(x) for x in items)
    fields = sorted({k for row in items if type(row) is dict
                     for k in row if type(k) is str and k in KNOWN_FIELDS})
    unknown_field_count = sum(
        1 for row in items if type(row) is dict
        for k in row if not (type(k) is str and k in KNOWN_FIELDS)
    )
    nested = sum(1 for row in items if type(row) is dict
                 for value in row.values() if type(value) in (dict, list))
    return {
        "count": 4,
        "element_type_counts": dict(sorted(types.items())),
        "recognized_schema_fields": fields,
        "unrecognized_field_occurrences": unknown_field_count,
        "nested_container_occurrences": nested,
    }


def check(selection: Path, admission: Path) -> dict:
    out = {
        "schema": SCHEMA,
        "status": "R50_EXCLUSION_SHAPE_HOLD",
        "reason_code": "UNVERIFIED",
        "exclusion_id_sets_equal_verified": False,
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
        a = read_private_json(selection)
        b = read_private_json(admission)
        out["selection"] = signature(a.get("excluded_cases"))
        out["admission"] = signature(b.get("exclude_ids"))
        out.update(status="R50_EXCLUSION_SHAPES_IDENTIFIED__MAPPING_HOLD",
                   reason_code="ELEMENT_SHAPES_ONLY")
    except Exception as exc:
        known = {"DUPLICATE_INPUT_HOLD", "FOUR_ENTRIES_HOLD"}
        out["reason_code"] = (str(exc) if isinstance(exc, ValueError)
                              and str(exc) in known else "SOURCE_OR_FORMAT_HOLD")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    out = check(args.selection, args.admission)
    print(json.dumps(out, sort_keys=True))
    return 0 if out["status"] == "R50_EXCLUSION_SHAPES_IDENTIFIED__MAPPING_HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())
