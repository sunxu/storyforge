#!/usr/bin/env python3
"""Safe, read-only keyset diagnostic for private R60 P2-A semantic checks.

Only emits line numbers, field names, counts, and the source file SHA-256.
Never emits calibration IDs, reviewer references, reasoning, or field values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

EXPECTED_CHECK_KEYS = frozenset({
    "schema", "rubric_version", "reviewer_role", "reviewer_ref",
    "conclusion", "reviewed_evidence_indexes", "reasoning_summary",
})


def diagnose(raw: bytes) -> dict:
    digest = hashlib.sha256(raw).hexdigest()
    rows = []
    keysets = []
    errors = []
    lines = raw.splitlines()
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            errors.append({"line": line_number, "reason": "EMPTY_LINE"})
            continue
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append({"line": line_number, "reason": "INVALID_JSON"})
            continue
        if not isinstance(row, dict):
            errors.append({"line": line_number, "reason": "ROW_NOT_OBJECT"})
            continue
        check = row.get("check")
        if not isinstance(check, dict):
            errors.append({"line": line_number, "reason": "CHECK_NOT_OBJECT"})
            continue
        keys = frozenset(check)
        keysets.append(keys)
        missing = sorted(EXPECTED_CHECK_KEYS - keys)
        extra = sorted(keys - EXPECTED_CHECK_KEYS)
        rows.append({
            "line": line_number,
            "missing_keys": missing,
            "extra_keys": extra,
            "keyset_match": not missing and not extra,
        })

    distributions = Counter(tuple(sorted(keys)) for keys in keysets)
    return {
        "schema": "storyforge_r60_p2a_semantic_check_keyset_diagnostic_safe_v1",
        "status": "DIAGNOSTIC_COMPLETE" if not errors else "DIAGNOSTIC_INPUT_HOLD",
        "source_sha256": digest,
        "expected_check_keys": sorted(EXPECTED_CHECK_KEYS),
        "total_rows": len(lines),
        "valid_check_rows": len(rows),
        "keyset_match_count": sum(row["keyset_match"] for row in rows),
        "keyset_mismatch_count": sum(not row["keyset_match"] for row in rows),
        "keyset_distributions": [
            {"keys": list(keys), "count": count}
            for keys, count in sorted(distributions.items())
        ],
        "row_diagnostics": [row for row in rows if not row["keyset_match"]],
        "input_errors": errors,
        "private_values_emitted": False,
        "files_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(diagnose(args.input.read_bytes()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
