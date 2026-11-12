"""Read-only, allowlisted status projection of R50 reports from Owner 0600 copies.

Does not make any R50 exclusion/admission claims. No raw strings, IDs, hashes,
paths, source text, schema values, or unknown report fields may be printed.
"""
from __future__ import annotations
import argparse
import json
import os
import stat
from pathlib import Path

SCHEMA = "storyforge_r60_r50_freeze_status_projection_safe_v1"
MAX_BYTES = 12_000_000

FIELDS = {
    "selection": ("original_case_count", "selected_case_count", "excluded_cases",
                  "final_heldout_seal", "owner_exclusion_authorized"),
    "admission": ("candidate_case_count", "excluded_case_count", "exclude_ids",
                  "final_heldout_seal", "promotion"),
    "worlds": ("same_story_id_pair_count", "heldout_final_seal",
               "semantic_hidden_alias_and_world_component_closure"),
    "r45_gate": ("frozen_r45_hashes_verified", "heldout_cases_sealed",
                 "incomplete_or_hidden_world_aliases", "exact_world_id_conflicts"),
}


def read_private_json(path: Path):
    if path.is_symlink():
        raise ValueError("SOURCE_LINK_HOLD")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or not 0 < st.st_size <= MAX_BYTES:
        raise ValueError("SOURCE_SIZE_HOLD")
    if st.st_mode & 0o077:
        raise ValueError("SOURCE_MODE_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        pre = os.fstat(f.fileno())
        data = f.read(MAX_BYTES + 1)
        post = os.fstat(f.fileno())
    if (len(data) != st.st_size or (pre.st_dev, pre.st_ino) != (st.st_dev, st.st_ino)
            or (pre.st_size, pre.st_mtime_ns) != (post.st_size, post.st_mtime_ns)):
        raise ValueError("SOURCE_CHANGED_HOLD")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("REPORT_OBJECT_HOLD")
    return value


def project(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if type(value) is int:
        # Bound numeric fields to avoid accidental private ID leaking.
        return {"type": "integer", "value": value} if 0 <= value <= 5000 else {"type": "integer_out_of_safe_range"}
    if isinstance(value, list):
        return {"type": "array", "count": len(value)} if len(value) <= 5000 else {"type": "array_too_large"}
    if isinstance(value, dict):
        return {"type": "object", "key_count": len(value)} if len(value) <= 5000 else {"type": "object_too_large"}
    return {"type": "string_or_unsupported"}  # NEVER emit raw string/enum.


def check(paths: dict[str, Path]):
    result = {
        "schema": SCHEMA,
        "status": "R50_FREEZE_PROJECTION_HOLD",
        "reason_code": "UNVERIFIED",
        "r50_complete_exclusion_verified": False,
        "r45_full_source_isolation_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    try:
        if set(paths) != set(FIELDS) or len({str(p.resolve(strict=False)) for p in paths.values()}) != 4:
            raise ValueError("INPUT_CONTRACT_HOLD")
        reports = {name: read_private_json(paths[name]) for name in FIELDS}
        result["reports"] = {
            name: {field: project(reports[name][field]) if field in reports[name]
                   else {"type": "missing"} for field in fields}
            for name, fields in FIELDS.items()
        }
        result.update(status="R50_FREEZE_STATUS_TYPES_READ__EXCLUSION_HOLD",
                      reason_code="STRUCTURE_AND_SAFE_TYPES_ONLY")
    except Exception as exc:
        safe = {"INPUT_CONTRACT_HOLD", "SOURCE_LINK_HOLD", "SOURCE_SIZE_HOLD",
                "SOURCE_MODE_HOLD", "SOURCE_CHANGED_HOLD", "REPORT_OBJECT_HOLD"}
        result["reason_code"] = str(exc) if isinstance(exc, ValueError) and str(exc) in safe else "REPORT_READ_OR_FORMAT_HOLD"
    return result


def main():
    ap = argparse.ArgumentParser()
    for x in FIELDS:
        ap.add_argument("--" + x.replace("_", "-"), type=Path, required=True)
    args = ap.parse_args()
    reports = {x: getattr(args, x) for x in FIELDS}
    output = check(reports)
    print(json.dumps(output, sort_keys=True))
    return 0 if output["status"] == "R50_FREEZE_STATUS_TYPES_READ__EXCLUSION_HOLD" else 42


if __name__ == "__main__":
    raise SystemExit(main())
