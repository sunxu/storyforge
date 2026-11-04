"""Read-only, aggregate-only diagnosis of R59 Gold source history structure.

Never changes source, emits case IDs, message text, hashes or paths, or
promotes candidates to review/admission. Classifies all violations rather
than only the first exception raised by the source staging validator.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from gold_source_context_stage import _private_file, _read_rows

SCHEMA = "storyforge-r59-history-structure-diagnostic-safe-v1"
ALLOWED_ROLES = {"user", "assistant"}


def diagnose(rows: list[dict]) -> dict:
    if not isinstance(rows, list) or not rows:
        raise ValueError("SOURCE_ROWS_INVALID")
    violations = Counter()
    status_values = Counter()
    cases_with_violations = 0
    cases_without_violations = 0
    messages_total = 0
    for row in rows:
        history = row.get("history") if isinstance(row, dict) else None
        issues = set()
        if not isinstance(history, list):
            issues.add("HISTORY_NOT_LIST")
        elif not history:
            issues.add("HISTORY_EMPTY")
        else:
            previous = None
            for message in history:
                messages_total += 1
                if not isinstance(message, dict):
                    issues.add("MESSAGE_NOT_OBJECT")
                    previous = None
                    continue
                role = message.get("role")
                if role not in ALLOWED_ROLES:
                    issues.add("ROLE_INVALID")
                if role in ALLOWED_ROLES and role == previous:
                    issues.add("REPEATED_ROLE")
                previous = role if role in ALLOWED_ROLES else None
                content = message.get("content")
                if not isinstance(content, str) or not content.strip():
                    issues.add("CONTENT_EMPTY_OR_INVALID")
                status = message.get("status")
                if status == "completed":
                    status_values["completed"] += 1
                elif status is None:
                    status_values["null_or_missing"] += 1
                    issues.add("STATUS_NOT_COMPLETED")
                elif isinstance(status, str):
                    status_values["other_string"] += 1
                    issues.add("STATUS_NOT_COMPLETED")
                else:
                    status_values["other_type"] += 1
                    issues.add("STATUS_NOT_COMPLETED")
            if not isinstance(history[-1], dict) or history[-1].get("role") != "user":
                issues.add("HISTORY_LAST_ROLE_NOT_USER")
        if issues:
            cases_with_violations += 1
            for issue in issues:
                violations[issue] += 1
        else:
            cases_without_violations += 1

    return {
        "schema": SCHEMA,
        "status": "HISTORY_STRUCTURE_DIAGNOSTIC_ONLY__NO_ADMISSION",
        "source_rows": len(rows),
        "cases_with_violations": cases_with_violations,
        "cases_without_violations": cases_without_violations,
        "messages_inspected": messages_total,
        "case_violation_counts": dict(sorted(violations.items())),
        "message_status_category_counts": dict(sorted(status_values.items())),
        "violation_categories_overlap": True,
        "source_mutated": False,
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
        raw = _private_file(args.source_context_jsonl, 160 * 1024 * 1024)
        result = diagnose(_read_rows(raw))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no source/errors echoed to stdout
        print(json.dumps({
            "schema": SCHEMA,
            "status": "HISTORY_STRUCTURE_DIAGNOSTIC_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
