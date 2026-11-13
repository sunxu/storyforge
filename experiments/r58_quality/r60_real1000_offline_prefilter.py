"""Offline full-1000 structural/context prefilter; no model or database access.

The sealed R60 source is read through the existing frozen_pool gate, never
from unverified JSONL. Only deterministic evidence is automatically excluded.
A missing world/card/System history is a separate downstream gate, not proof
of a defective source record.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_real1000_prefilter_private_v1"
SAFE = "storyforge_r60_real1000_prefilter_safe_v1"
OUTPUT = "R60_REAL1000_PREFILTER_PRIVATE.json"
PAGE_SIZE = 100
EXPECTED = 1000
HISTORY_ROLES = ("user", "assistant", "user")
SOURCE_FIELDS = (
    "story_id", "session_id", "assistant_message_id",
    "prior_user_message_id", "previous_assistant_message_id",
    "previous_user_message_id",
)
EXCLUDE_CODES = frozenset({
    "STRUCTURE_INVALID", "SOURCE_FIELDS_INVALID",
    "EXACT_TARGET_DUPLICATE", "EXACT_RECORD_DUPLICATE",
})
REVIEW_CODES = frozenset({"IDENTICAL_HISTORY_DIFFERENT_TARGET"})


class Hold(ValueError):
    pass


def classify_cases(cases: list[dict]) -> list[dict]:
    """Pure, deterministic screening; returned rows contain no original prose."""
    if not isinstance(cases, list) or len(cases) != EXPECTED:
        raise Hold("EXACT_1000_REQUIRED")
    seen_targets: dict[str, int] = {}
    seen_records: set[tuple[str, str]] = set()
    seen_history: dict[str, str] = {}
    seen_source_ids: set[str] = set()
    result = []
    for position, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            raise Hold("CASE_FORMAT_HOLD")
        src = case.get("source")
        history = case.get("history_messages")
        target = case.get("target_text")
        if (not isinstance(src, dict)
                or not isinstance(history, list)
                or not isinstance(target, str)):
            raise Hold("FROZEN_SOURCE_STRUCTURE_HOLD")
        # Integrity failures must fail the entire batch rather than silently
        # treating a tampered/corrupt frozen case as an exclusion.
        if (case.get("history_messages_sha256") != private.digest(history)
                or case.get("assistant_target_sha256") !=
                private.digest(target)):
            raise Hold("SOURCE_DIGEST_HOLD")
        if (not isinstance(case.get("case_key"), str)
                or not case["case_key"]):
            raise Hold("CASE_IDENTITY_HOLD")
        code = None
        if (any(not isinstance(src.get(k), str) or not src[k].strip()
                for k in SOURCE_FIELDS)
                or type(src.get("assistant_turn_index")) is not int
                or src["assistant_turn_index"] < 4):
            code = "SOURCE_FIELDS_INVALID"
        elif (len(history) != 3 or any(
                not isinstance(row, dict)
                or row.get("role") != expected
                or not isinstance(row.get("content"), str)
                or not row["content"].strip()
                for row, expected in zip(history, HISTORY_ROLES))
                or not target.strip()):
            code = "STRUCTURE_INVALID"
        # These duplicate checks are content-based, not heuristics.
        target_digest = case["assistant_target_sha256"]
        history_digest = case["history_messages_sha256"]
        record_key = (history_digest, target_digest)
        source_id = src.get("assistant_message_id")
        if isinstance(source_id, str) and source_id:
            if source_id in seen_source_ids:
                raise Hold("FROZEN_SOURCE_DUPLICATE_ID_HOLD")
            seen_source_ids.add(source_id)
        if code is None:
            if record_key in seen_records:
                code = "EXACT_RECORD_DUPLICATE"
            elif target_digest in seen_targets:
                code = "EXACT_TARGET_DUPLICATE"
            elif (history_digest in seen_history
                  and seen_history[history_digest] != target_digest):
                code = "IDENTICAL_HISTORY_DIFFERENT_TARGET"
        # Track all syntactically valid data, including review-holds, to
        # prevent duplicate examples from silently reentering later.
        if code not in ("STRUCTURE_INVALID", "SOURCE_FIELDS_INVALID"):
            seen_records.add(record_key)
            seen_targets.setdefault(target_digest, position)
            seen_history.setdefault(history_digest, target_digest)
        state = ("EXCLUDE" if code in EXCLUDE_CODES
                 else "CONTEXT_HOLD" if code in REVIEW_CODES
                 else "STRUCTURE_PASS")
        result.append({
            "position": position,
            "case_key": case["case_key"],
            "history_messages_sha256": history_digest,
            "assistant_target_sha256": target_digest,
            "state": state,
            "reason_code": code or "STRUCTURE_AND_CONTEXT_BOUNDARY_PASS",
            "quality_evaluated": False,
            "train_admitted": 0,
        })
    return result


def summarize(rows: list[dict]) -> dict:
    if len(rows) != EXPECTED:
        raise Hold("EXACT_1000_REQUIRED")
    states = Counter(r["state"] for r in rows)
    reasons = Counter(r["reason_code"] for r in rows)
    if set(states) - {"EXCLUDE", "CONTEXT_HOLD", "STRUCTURE_PASS"}:
        raise Hold("UNKNOWN_STATE_HOLD")
    return {
        "schema": SAFE,
        "status": "REAL1000_PREFILTER_COMPLETE__QUALITY_NOT_EVALUATED",
        "cases_total": EXPECTED,
        "structure_pass": states["STRUCTURE_PASS"],
        "excluded": states["EXCLUDE"],
        "context_hold": states["CONTEXT_HOLD"],
        "reason_counts": {s: reasons[s] for s in sorted(
            EXCLUDE_CODES | REVIEW_CODES) if reasons[s]},
        "quality_reviewed": 0,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "r50_complete_exclusion_verified": False,
        "historical_system_snapshot_verified": False,
        "world_isolation_verified": False,
        "model_requests": 0,
        "gpu_started": False,
        "database_modified": False,
        "private_values_emitted": False,
    }


def run(expand_dir: Path, output_dir: Path) -> dict:
    safe = {
        "schema": SAFE, "status": "REAL1000_PREFILTER_HOLD",
        "model_requests": 0, "gpu_started": False,
        "database_modified": False, "train_admitted": 0,
        "private_values_emitted": False,
    }
    try:
        if (output_dir.parent != private.BASE
                or not output_dir.name.startswith("r60-real1000-prefilter-")
                or output_dir.exists() or output_dir.is_symlink()):
            raise Hold("PRIVATE_OUTPUT_PATH_HOLD")
        cases, pool_sha = quality.frozen_pool(expand_dir)
        rows = classify_cases(cases)
        status = summarize(rows)
        private.private_dir(output_dir, create=True)
        pages = []
        for index, offset in enumerate(range(0, EXPECTED, PAGE_SIZE), 1):
            name = f"R60_REAL1000_PREFILTER_PAGE_{index:04d}_PRIVATE.json"
            page = {
                "schema": SCHEMA, "pool_sha256": pool_sha,
                "page_index": index, "rows": rows[offset:offset + PAGE_SIZE],
            }
            raw = (json.dumps(page, ensure_ascii=False, sort_keys=True)
                   + "\n").encode("utf-8")
            private.write_new(output_dir / name, raw)
            pages.append({"name": name, "sha256": private.digest(page)})
        # Only a complete create-only page set receives its final marker.
        payload = {
            "schema": SCHEMA, "pool_sha256": pool_sha,
            "cases_total": EXPECTED, "pages": pages,
            "safe": status, "quality_evaluated": False, "train_admitted": 0,
        }
        private.write_new(
            output_dir / OUTPUT,
            (json.dumps(payload, ensure_ascii=False, sort_keys=True)
             + "\n").encode("utf-8"),
        )
        return status
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expand-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    status = run(args.expand_dir, args.output_dir)
    print(json.dumps(status, sort_keys=True))
    return 0 if status["status"].startswith("REAL1000_PREFILTER_COMPLETE") else 42


if __name__ == "__main__":
    raise SystemExit(main())
