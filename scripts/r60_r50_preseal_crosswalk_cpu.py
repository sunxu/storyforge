"""Read-only R50 PRESEAL 46/46 structural crosswalk; never train/admit/seal.

Only emits bounded aggregate counts/booleans and fixed status values.
Does NOT prove final R50 50-case protection, R45 isolation, or overlap with Common2.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

SCHEMA = "storyforge_r60_r50_preseal_crosswalk_safe_v1"
MAX_BYTES = 12_000_000
MAX_LINES = 100


def read(path: Path, *, jsonl: bool):
    if path.is_symlink():
        raise ValueError("FILE_SYMLINK_HOLD")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or not 0 < st.st_size <= MAX_BYTES:
        raise ValueError("FILE_SIZE_HOLD")
    if st.st_mode & 0o077:
        raise ValueError("FILE_PERMISSION_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as f:
        before = os.fstat(f.fileno())
        raw = f.read(MAX_BYTES + 1)
        after = os.fstat(f.fileno())
    if (len(raw) != st.st_size or st.st_ino != before.st_ino
            or st.st_dev != before.st_dev
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns):
        raise ValueError("FILE_CHANGED_HOLD")
    if jsonl:
        lines = raw.splitlines()
        if len(lines) != 46 or any(not x for x in lines):
            raise ValueError("CASE_COUNT_HOLD")
        return [json.loads(x) for x in lines]
    return json.loads(raw)


def bounded_unique(values):
    if not all(isinstance(x, (str, int)) and type(x) is not bool and str(x) for x in values):
        raise ValueError("SOURCE_ID_SCHEMA_HOLD")
    if len({(type(x).__name__, str(x)) for x in values}) != len(values):
        raise ValueError("DUPLICATE_CASE_ID_HOLD")


def check(paths: list[Path]) -> dict:
    result = {
        "schema": SCHEMA,
        "status": "R50_PRESEAL_CROSSWALK_HOLD",
        "reason_code": "UNVERIFIED",
        "preseal_cases_checked": 0,
        "case_id_order_exact": False,
        "provenance_story_fields_present": False,
        "history_reference_fields_present": False,
        "frozen_protection_50_verified": False,
        "r45_full_source_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    try:
        if len(paths) != 6 or len({str(p.resolve(strict=False)) for p in paths}) != 6:
            raise ValueError("DUPLICATE_PATH_HOLD")
        cases, prov = (read(p, jsonl=True) for p in paths[:2])
        selection, admission, worlds, gate = (read(p, jsonl=False) for p in paths[2:])
        if not all(isinstance(x, dict) for x in cases + prov):
            raise ValueError("ROW_SCHEMA_HOLD")
        if not all(isinstance(x, dict) for x in (selection, admission, worlds, gate)):
            raise ValueError("REPORT_SCHEMA_HOLD")
        case_ids = [r.get("case_id") for r in cases]
        prov_ids = [r.get("case_id") for r in prov]
        bounded_unique(case_ids)
        bounded_unique(prov_ids)
        result["preseal_cases_checked"] = 46
        result["case_id_order_exact"] = case_ids == prov_ids
        if not result["case_id_order_exact"]:
            raise ValueError("CASE_ID_ORDER_HOLD")
        result["provenance_story_fields_present"] = all(
            isinstance(row.get("source_story_id"), (str, int))
            and not isinstance(row.get("source_story_id"), bool)
            and bool(str(row.get("source_story_id")))
            and isinstance(row.get("source_session_id"), (str, int))
            and not isinstance(row.get("source_session_id"), bool)
            and bool(str(row.get("source_session_id")))
            for row in prov
        )
        result["history_reference_fields_present"] = all(
            isinstance(row.get("history_message_ids"), list)
            and len(row["history_message_ids"]) > 0
            and all(isinstance(v, (str, int)) and not isinstance(v, bool)
                    and bool(str(v)) for v in row["history_message_ids"])
            for row in prov
        )
        if not (result["provenance_story_fields_present"]
                and result["history_reference_fields_present"]):
            raise ValueError("SOURCE_PROVENANCE_HOLD")
        # Only allowlisted metadata structure; never assume status semantics or final seal.
        for name, report, fields in [
            ("selection", selection, ("original_case_count", "selected_case_count", "excluded_cases", "final_heldout_seal")),
            ("admission", admission, ("candidate_case_count", "excluded_case_count", "final_heldout_seal", "promotion")),
            ("worlds", worlds, ("same_story_id_pair_count", "heldout_final_seal", "semantic_hidden_alias_and_world_component_closure")),
            ("r45_gate", gate, ("frozen_r45_hashes_verified", "heldout_cases_sealed", "incomplete_or_hidden_world_aliases")),
        ]:
            result[name + "_expected_fields_present"] = all(field in report for field in fields)
        if not all(result[k] for k in result if k.endswith("_expected_fields_present")):
            raise ValueError("REPORT_FIELDS_HOLD")
        # A count-only audit cannot attest to final R50 coverage or R45 exclusion.
        result.update(status="R50_PRESEAL_46_CROSSWALK_PASS__FINAL_COVERAGE_HOLD",
                      reason_code="PRESEAL_STRUCTURE_ONLY")
    except Exception as exc:
        safe = {"DUPLICATE_PATH_HOLD", "FILE_SYMLINK_HOLD", "FILE_SIZE_HOLD",
                "FILE_PERMISSION_HOLD", "FILE_CHANGED_HOLD", "CASE_COUNT_HOLD",
                "SOURCE_ID_SCHEMA_HOLD", "DUPLICATE_CASE_ID_HOLD",
                "ROW_SCHEMA_HOLD", "REPORT_SCHEMA_HOLD", "CASE_ID_ORDER_HOLD",
                "SOURCE_PROVENANCE_HOLD", "REPORT_FIELDS_HOLD"}
        result["reason_code"] = str(exc) if isinstance(exc, ValueError) and str(exc) in safe else "FILE_FORMAT_OR_RUNTIME_HOLD"
    return result


def main():
    ap = argparse.ArgumentParser()
    for arg in ("cases", "provenance", "selection", "admission", "worlds", "r45-gate"):
        ap.add_argument("--" + arg, type=Path, required=True)
    args = ap.parse_args()
    paths = [getattr(args, k) for k in ("cases", "provenance", "selection", "admission", "worlds", "r45_gate")]
    result = check(paths)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"].startswith("R50_PRESEAL_46_CROSSWALK_PASS") else 42


if __name__ == "__main__":
    raise SystemExit(main())
