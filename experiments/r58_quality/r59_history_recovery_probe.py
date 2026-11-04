"""Read-only aggregate counterfactual for R59 incomplete/blank history entries.

This does not rewrite, approve, or persist any candidate history. It only
checks whether dropping records that are BOTH unfinished AND blank would
produce structurally valid remaining histories. Source version and chronology
still require independent verification before any dataset materialization.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from gold_source_context_stage import _private_file, _read_rows

SCHEMA = "storyforge-r59-incomplete-blank-history-probe-safe-v1"
ROLES = {"user", "assistant"}


def probe(rows: list[dict]) -> dict:
    if not isinstance(rows, list) or not rows:
        raise ValueError("SOURCE_ROWS_INVALID")
    message_categories = Counter()
    cases = Counter()
    for row in rows:
        history = row.get("history") if isinstance(row, dict) else None
        if not isinstance(history, list) or not history:
            cases["unusable_history_shape"] += 1
            continue

        filtered = []
        removed = 0
        unsupported = False
        original_valid = True
        prev_original = None
        for message in history:
            if not isinstance(message, dict):
                unsupported = True
                original_valid = False
                message_categories["non_object"] += 1
                continue
            role = message.get("role")
            content = message.get("content")
            complete = message.get("status") == "completed"
            nonblank = isinstance(content, str) and bool(content.strip())
            if complete and nonblank:
                message_categories["completed_nonblank"] += 1
            elif not complete and not nonblank:
                message_categories["unfinished_blank"] += 1
            elif complete:
                message_categories["completed_blank"] += 1
            else:
                message_categories["unfinished_nonblank"] += 1

            if role not in ROLES or role == prev_original or not complete or not nonblank:
                original_valid = False
            prev_original = role
            if not complete and not nonblank:
                removed += 1
                continue
            if not complete or not nonblank or role not in ROLES:
                unsupported = True
            filtered.append(message)
        original_valid = original_valid and history[-1].get("role") == "user" if isinstance(history[-1], dict) else False
        if original_valid:
            cases["already_structurally_valid"] += 1
        elif not removed:
            cases["invalid_without_unfinished_blank"] += 1
        elif unsupported:
            cases["requires_other_semantic_or_structure_review"] += 1
        elif not filtered or filtered[-1].get("role") != "user":
            cases["filtered_boundary_invalid"] += 1
        elif any(a["role"] == b["role"] for a, b in zip(filtered, filtered[1:])):
            cases["filtered_repeated_roles"] += 1
        else:
            cases["potentially_recoverable_by_blank_unfinished_exclusion"] += 1
        if removed:
            cases["has_unfinished_blank"] += 1
    return {
        "schema": SCHEMA,
        "status": "COUNTERFACTUAL_ONLY__NO_SOURCE_REWRITE_OR_ADMISSION",
        "source_rows": len(rows),
        "message_category_counts": dict(sorted(message_categories.items())),
        "case_category_counts": dict(sorted(cases.items())),
        "source_mutated": False,
        "records_removed": False,
        "projected_histories_persisted": False,
        "source_eligibility_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-context-jsonl", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = _read_rows(_private_file(args.source_context_jsonl, 160 * 1024 * 1024))
        print(json.dumps(probe(rows), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - privacy: no raw exception details
        print(json.dumps({
            "schema": SCHEMA,
            "status": "COUNTERFACTUAL_PROBE_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
