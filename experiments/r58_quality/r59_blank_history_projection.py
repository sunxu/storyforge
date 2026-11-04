"""SAFE read-only projection of R59 histories after excluding all blank entries.

A counterfactual diagnostic only: not authority to delete completed blank
messages, to merge consecutive turns, or to admit any training candidate.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import pairwise
from pathlib import Path

from gold_source_context_stage import _private_file, _read_rows

SCHEMA = "storyforge-r59-blank-history-projection-safe-v1"
ROLES = {"user", "assistant"}


def project(rows: list[dict]) -> dict:
    if not isinstance(rows, list) or not rows:
        raise ValueError("SOURCE_ROWS_INVALID")
    cases = Counter()
    messages = Counter()
    for row in rows:
        history = row.get("history") if isinstance(row, dict) else None
        if not isinstance(history, list) or not history:
            cases["unusable_history_shape"] += 1
            continue
        kept = []
        original_repeats = False
        malformed = False
        previous_original_role = None
        for item in history:
            if not isinstance(item, dict):
                messages["non_object"] += 1
                malformed = True
                previous_original_role = None
                continue
            role = item.get("role")
            content = item.get("content")
            status = item.get("status")
            nonblank = isinstance(content, str) and bool(content.strip())
            complete = status == "completed"
            if role not in ROLES:
                malformed = True
                messages["invalid_role"] += 1
            if role in ROLES and role == previous_original_role:
                original_repeats = True
            previous_original_role = role if role in ROLES else None
            if not nonblank:
                if complete:
                    messages["excluded_completed_blank"] += 1
                else:
                    messages["excluded_unfinished_blank"] += 1
                continue
            if not complete:
                messages["retained_unfinished_nonblank"] += 1
            else:
                messages["retained_completed_nonblank"] += 1
            kept.append(item)

        if original_repeats:
            cases["original_repeated_roles"] += 1
        if not kept:
            cases["after_blank_filter_empty"] += 1
            continue
        projected_repeats = any(
            a.get("role") == b.get("role")
            for a, b in pairwise(kept)
        )
        if projected_repeats:
            cases["after_blank_filter_repeated_roles"] += 1
            if not original_repeats:
                cases["repeated_roles_created_by_filter"] += 1
        elif original_repeats:
            cases["original_repeats_resolved_by_filter"] += 1
        if kept[-1].get("role") != "user":
            cases["after_blank_filter_last_not_user"] += 1
        if malformed:
            cases["malformed_source_message_or_role"] += 1
        if (not projected_repeats and kept[-1].get("role") == "user"
                and not malformed and all(x.get("status") == "completed" for x in kept)):
            cases["structurally_valid_after_all_blank_projection"] += 1
        else:
            cases["still_invalid_after_all_blank_projection"] += 1
    return {
        "schema": SCHEMA,
        "status": "ALL_BLANK_COUNTERFACTUAL_ONLY__NO_ADMISSION",
        "source_rows": len(rows),
        "case_counts": dict(sorted(cases.items())),
        "message_counts": dict(sorted(messages.items())),
        "case_categories_overlap": True,
        "source_mutated": False,
        "records_removed": False,
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
        print(json.dumps(project(rows), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - do not expose private data
        print(json.dumps({
            "schema": SCHEMA,
            "status": "ALL_BLANK_COUNTERFACTUAL_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
