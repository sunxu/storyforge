"""R50 original-50 vs PRESEAL-46+excluded-4 exact source-ID complement audit.

Offline read-only. No original IDs, text, digests or paths ever printed.
This is a source-cohort verification, NOT final heldout seal or training admission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

try:
    from scripts.r60_r50_freeze_status_projection_cpu import read_private_json
    from scripts.r60_r50_exclusion_pair_cpu import selection_ids, safe_ids
except ModuleNotFoundError:
    from r60_r50_freeze_status_projection_cpu import read_private_json
    from r60_r50_exclusion_pair_cpu import selection_ids, safe_ids

SCHEMA = "storyforge_r60_r50_original50_complement_safe_v1"
ORIGINAL_SHA = {
    "cases": "8dbb66aeb47fd1fec34718d31b228c0378a79f43b7b847eb3e403752d8139781",
    "provenance": "9306af53c6a53fbe46a6675c50e5fac4753162a5c19d6f3c1a0072919306b280",
}
SIZE = {"cases": 422562, "provenance": 31758}
KEYS = ("source_story_id", "source_session_id", "cutoff_message_id", "history_message_ids")


def jsonl(path: Path, expected: int, source: str | None = None):
    # Reuse the existing audited 0600, no-symlink, size-bounded file read
    # contract indirectly by parsing a per-file reader with the same guards.
    import os
    import stat
    if path.is_symlink():
        raise ValueError("SYMLINK_HOLD")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or st.st_size < 1 or st.st_size > 12_000_000:
        raise ValueError("FILE_MODE_OR_SIZE_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        pre = os.fstat(stream.fileno())
        raw = stream.read(12_000_001)
        post = os.fstat(stream.fileno())
    if len(raw) != st.st_size or (pre.st_dev, pre.st_ino) != (st.st_dev, st.st_ino) or (
        pre.st_mtime_ns, pre.st_size
    ) != (post.st_mtime_ns, post.st_size):
        raise ValueError("FILE_CHANGED_HOLD")
    if source and (len(raw) != SIZE[source] or hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA[source]):
        raise ValueError("ORIGINAL_SHA_HOLD")
    lines = raw.splitlines()
    if len(lines) != expected:
        raise ValueError("ROW_COUNT_HOLD")
    records = [json.loads(line) for line in lines]
    if any(type(x) is not dict for x in records):
        raise ValueError("ROW_SCHEMA_HOLD")
    return records


def ids(records):
    result = [r.get("case_id") for r in records]
    if any(type(x) is not str or not x or len(x) > 256 for x in result):
        raise ValueError("CASE_ID_SCHEMA_HOLD")
    if len(set(result)) != len(result):
        raise ValueError("CASE_ID_DUPLICATE_HOLD")
    return result


def audit(paths: dict[str, Path]) -> dict:
    out = {
        "schema": SCHEMA,
        "status": "R50_ORIGINAL50_COMPLEMENT_HOLD",
        "reason_code": "UNVERIFIED",
        "original_hashes_verified": False,
        "original_case_provenance_order_verified": False,
        "derived_case_provenance_order_verified": False,
        "excluded_four_match_original_complement": False,
        "derived_46_match_manifest_selected_lines": False,
        "selected_source_provenance_matches_original": False,
        "original_50_complete_cohort_verified": False,
        "final_heldout_seal_verified": False,
        "r45_full_source_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    try:
        names = ("original_cases", "original_provenance", "derived_cases",
                 "derived_provenance", "selection", "admission")
        if set(paths) != set(names) or len({str(x.resolve(strict=False)) for x in paths.values()}) != 6:
            raise ValueError("INPUTS_HOLD")
        oc = jsonl(paths["original_cases"], 50, "cases")
        op = jsonl(paths["original_provenance"], 50, "provenance")
        dc = jsonl(paths["derived_cases"], 46)
        dp = jsonl(paths["derived_provenance"], 46)
        out["original_hashes_verified"] = True
        ocids, opids, dcids, dpids = (ids(x) for x in (oc, op, dc, dp))
        out["original_case_provenance_order_verified"] = ocids == opids
        out["derived_case_provenance_order_verified"] = dcids == dpids
        if not (out["original_case_provenance_order_verified"] and out["derived_case_provenance_order_verified"]):
            raise ValueError("CASE_PROVENANCE_ORDER_HOLD")
        selection = read_private_json(paths["selection"])
        admission = read_private_json(paths["admission"])
        if (type(selection.get("original_case_count")) is not int or selection["original_case_count"] != 50
            or type(selection.get("selected_case_count")) is not int or selection["selected_case_count"] != 46
            or type(admission.get("candidate_case_count")) is not int or admission["candidate_case_count"] != 46
            or type(admission.get("excluded_case_count")) is not int or admission["excluded_case_count"] != 4
            or selection.get("owner_exclusion_authorized") is not True):
            raise ValueError("MANIFEST_COUNTS_HOLD")
        excluded = selection_ids(selection.get("excluded_cases"))
        admission_ids = safe_ids(admission.get("exclude_ids"))
        # ID values are checked locally and never emitted.
        if excluded != admission_ids:
            raise ValueError("EXCLUDED_REPORT_MISMATCH_HOLD")
        original_set, derived_set = set(ocids), set(dcids)
        excluded_strings = {v for typ, v in excluded if typ == "str"}
        out["excluded_four_match_original_complement"] = (original_set - derived_set) == excluded_strings
        if not out["excluded_four_match_original_complement"] or derived_set - original_set or derived_set & excluded_strings:
            raise ValueError("ORIGINAL_COMPLEMENT_HOLD")
        positions = selection.get("selected_parent_line_numbers_1_based")
        if (type(positions) is not list or len(positions) != 46
            or any(type(x) is not int or not 1 <= x <= 50 for x in positions)
            or len(set(positions)) != 46):
            raise ValueError("PARENT_LINE_NUMBERS_HOLD")
        out["derived_46_match_manifest_selected_lines"] = (
            dcids == [ocids[pos - 1] for pos in positions]
        )
        if not out["derived_46_match_manifest_selected_lines"]:
            raise ValueError("PARENT_LINE_MAPPING_HOLD")
        original_p = dict(zip(opids, op))
        out["selected_source_provenance_matches_original"] = all(
            all(original_p[rec["case_id"]].get(k) == rec.get(k) and k in original_p[rec["case_id"]]
                and k in rec for k in KEYS)
            for rec in dp
        )
        if not out["selected_source_provenance_matches_original"]:
            raise ValueError("SOURCE_PROVENANCE_MISMATCH_HOLD")
        out.update(
            status="R50_ORIGINAL50_46_PLUS4_EXACT_COHORT_PASS__SEAL_R45_TRAIN_HOLD",
            reason_code="FROZEN_ORIGINAL_COMPLEMENT_AND_SOURCE_MAPPING_PASS",
            original_50_complete_cohort_verified=True,
        )
    except Exception as exc:
        allow = {
            "INPUTS_HOLD", "SYMLINK_HOLD", "FILE_MODE_OR_SIZE_HOLD", "FILE_CHANGED_HOLD",
            "ORIGINAL_SHA_HOLD", "ROW_COUNT_HOLD", "ROW_SCHEMA_HOLD",
            "CASE_ID_SCHEMA_HOLD", "CASE_ID_DUPLICATE_HOLD",
            "CASE_PROVENANCE_ORDER_HOLD", "MANIFEST_COUNTS_HOLD",
            "EXCLUDED_REPORT_MISMATCH_HOLD", "ORIGINAL_COMPLEMENT_HOLD",
            "PARENT_LINE_NUMBERS_HOLD", "PARENT_LINE_MAPPING_HOLD",
            "SOURCE_PROVENANCE_MISMATCH_HOLD",
            "FOUR_IDS_SHAPE_HOLD", "EXCLUSION_ID_TYPE_HOLD",
            "EXCLUSION_OBJECT_SCHEMA_HOLD", "EXCLUSION_ID_DUPLICATE_HOLD",
        }
        out["reason_code"] = str(exc) if isinstance(exc, ValueError) and str(exc) in allow else "SOURCE_FORMAT_OR_RUNTIME_HOLD"
    return out


def main():
    parser = argparse.ArgumentParser()
    for name in ("original-cases", "original-provenance", "derived-cases",
                 "derived-provenance", "selection", "admission"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    out = audit({
        k: getattr(a, k) for k in (
            "original_cases", "original_provenance", "derived_cases",
            "derived_provenance", "selection", "admission")
    })
    print(json.dumps(out, sort_keys=True))
    return 0 if out["original_50_complete_cohort_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())
