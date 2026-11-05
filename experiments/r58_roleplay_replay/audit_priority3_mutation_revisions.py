#!/usr/bin/env python3
"""SAFE R58 offline mutation-revision risk diagnosis from sealed local source.

Read only; no DB, network, model or write. Counts only. Positive revision may
reflect status/partial-content finalization and is NOT necessarily text editing.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from capture_priority3 import Hold, MAX_INPUT_BYTES
from verify_priority3_private import read_private_file, verify
from preflight_priority3_history import derive_case

EXPECTED = {"AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"}


def revision_analysis(row: dict) -> dict:
    history = row["history24"]
    diag = derive_case(row)
    # Only reconstruct the indices needed for the same *conditional*
    # summary-window count. This is not proof of historical runtime inputs.
    if len(history) != 24 or diag["eleven_message_structure"] != "PASS":
        raise Hold("conditional 11-message source window not established")
    if diag["conditional_window_count"] != 11:
        raise Hold("not an 11-message window")
    window = history[-11:]
    # In a suffix-aligned 11-message window the selected window must be the
    # last 11 entries, beginning with user and ending with user.
    if window[0].get("role") != "user" or window[-1].get("role") != "user":
        raise Hold("conditional suffix window alignment mismatch")
    by_role = {role: {"total": 0, "revision_positive": 0} for role in ("user", "assistant")}
    for msg in window:
        role = msg.get("role")
        rev = msg.get("mutation_revision")
        if role not in by_role or type(rev) is not int or rev < 0:
            raise Hold("source role/revision type invalid")
        by_role[role]["total"] += 1
        if rev > 0:
            by_role[role]["revision_positive"] += 1
    pos = sum(x["revision_positive"] for x in by_role.values())
    if pos != diag["mutated_rows_in_conditional_window"]:
        raise Hold("revision count mismatch with preflight")
    ledger_count = row["structural_checks"].get("post_target_ledger_events")
    if type(ledger_count) is not int or ledger_count != 0:
        raise Hold("recorded post-target ledger guard is not zero")
    return {
        "cohort": diag["cohort"],
        "conditional_window_count": 11,
        "revision_positive_rows": pos,
        "role_counts": by_role,
        "recorded_post_target_ledger_events": ledger_count,
        "revision_reason": "UNKNOWN_FROM_CAPTURE",
        "status_only_or_stream_finalization": "POSSIBLE_NOT_VERIFIED",
        "historical_content_unchanged": "HOLD",
        "as_of_target_text_parity": "HOLD",
    }


def audit(folder: Path) -> dict:
    if verify(folder)["case_fingerprints_verified"] != 12:
        raise Hold("private source integrity guard failed")
    raw = read_private_file(folder / "source.private.jsonl", MAX_INPUT_BYTES)
    try:
        rows = [json.loads(x) for x in raw.splitlines() if x.strip()]
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Hold("invalid private source JSONL") from exc
    if len(rows) != 3:
        raise Hold("expected exactly three cases")
    result = [revision_analysis(x) for x in rows]
    if {r["cohort"] for r in result} != EXPECTED:
        raise Hold("unexpected source cohorts")
    return {
        "status": "R58_MUTATION_REVISION_ROLE_AUDIT_PASS__HISTORICAL_TEXT_PARITY_HOLD",
        "source_bundle_integrity": "PASS",
        "cases": sorted(result, key=lambda r: r["cohort"]),
        "runtime_prompt_byte_exact": "HOLD",
        "training_admission": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="SAFE 11-window mutation revision role audit")
    ap.add_argument("--private-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        print(json.dumps(audit(args.private_dir), sort_keys=True))
        return 0
    except (Hold, ValueError, KeyError, OSError, TypeError):
        print("R58_MUTATION_REVISION_ROLE_AUDIT: HOLD", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
