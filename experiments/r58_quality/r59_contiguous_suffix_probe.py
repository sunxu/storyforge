"""Read-only aggregate probe for the longest untouched R59 history suffix.

This reports structural possibilities only, never rewrites source files or
approves training. It cannot establish temporal fidelity or sample quality.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from gold_source_context_stage import _private_file, _read_rows

SCHEMA = "storyforge-r59-contiguous-suffix-probe-safe-v1"
ROLES = {"user", "assistant"}


def _valid(message: object) -> bool:
    return (
        isinstance(message, dict)
        and message.get("role") in ROLES
        and isinstance(message.get("content"), str)
        and bool(message["content"].strip())
        and message.get("status") == "completed"
    )


def _bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n < 4:
        return "2-3"
    if n < 8:
        return "4-7"
    if n < 16:
        return "8-15"
    if n < 32:
        return "16-31"
    return "32+"


def probe(rows: list[dict]) -> dict:
    if not isinstance(rows, list) or not rows:
        raise ValueError("SOURCE_ROWS_INVALID")
    counts = Counter()
    distribution = Counter()
    for row in rows:
        history = row.get("history") if isinstance(row, dict) else None
        if not isinstance(history, list) or not history:
            counts["history_missing_or_empty"] += 1
            distribution["0"] += 1
            continue
        # Do not skip a bad final user or stitch through an invalid message.
        if not _valid(history[-1]) or history[-1]["role"] != "user":
            counts["last_message_invalid_or_not_user"] += 1
            distribution["0"] += 1
            continue
        n = 1
        expected = "assistant"
        for msg in reversed(history[:-1]):
            if not _valid(msg) or msg["role"] != expected:
                break
            n += 1
            expected = "user" if expected == "assistant" else "assistant"
        distribution[_bucket(n)] += 1
        if n == len(history):
            counts["fully_valid_unchanged_history"] += 1
        else:
            counts["proper_suffix_only"] += 1
        if n == 1:
            counts["last_user_only_no_assistant_context"] += 1
        else:
            counts["at_least_one_prior_assistant_turn"] += 1
        if n >= 4:
            counts["at_least_four_contiguous_messages"] += 1
        if n >= 8:
            counts["at_least_eight_contiguous_messages"] += 1
        if n >= 16:
            counts["at_least_sixteen_contiguous_messages"] += 1
    return {
        "schema": SCHEMA,
        "status": "CONTIGUOUS_SUFFIX_DIAGNOSTIC_ONLY__NO_ADMISSION",
        "source_rows": len(rows),
        "case_category_counts": dict(sorted(counts.items())),
        "longest_valid_suffix_messages_distribution": dict(sorted(distribution.items())),
        "source_mutated": False,
        "projected_histories_persisted": False,
        "temporal_or_semantic_validity_proven": False,
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
        print(json.dumps(probe(rows), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - private paths, data, errors may not be logged
        print(json.dumps({
            "schema": SCHEMA,
            "status": "CONTIGUOUS_SUFFIX_DIAGNOSTIC_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
