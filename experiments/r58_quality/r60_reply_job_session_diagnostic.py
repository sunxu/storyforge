"""R60 S3B: distinguish absent Reply Job sessions from absent exact turns.

Private, eight-target, index-guarded read-only pilot. No model payloads or
identifiers leave SQL, and no training evidence status is promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

try:
    from .r60_model_input_coverage_catalog import REQUIRED_ROLE, SQL, TABLES, classify
    from .r60_model_input_evidence_seed import _read_private
    from .r60_reply_job_locator_pilot import MAX_PILOT, summarize
except ImportError:
    from r60_model_input_coverage_catalog import REQUIRED_ROLE, SQL, TABLES, classify
    from r60_model_input_evidence_seed import _read_private
    from r60_reply_job_locator_pilot import MAX_PILOT, summarize

SCHEMA = "r60_reply_job_session_diagnostic_safe_v1"
EXPECTED_SOURCE_SHA = "eb2b186b03ffc31585c224ac75cbfd7dd20c8d762887a6463c85bc5090ae9739"
SOURCE_SCHEMA = "r60_gold192_supabase_extract_v3_safe_v1"
SOURCE_STATUS = "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED"


def select_diverse(raw: bytes, safe_raw: bytes, limit: int = MAX_PILOT) -> tuple[list[tuple[str, int]], int]:
    if limit != MAX_PILOT:
        raise ValueError("EXACT_PILOT_SIZE_REQUIRED")
    try:
        receipt = json.loads(safe_raw)
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise ValueError("SOURCE_PARSE_INVALID") from None
    digest = hashlib.sha256(raw).hexdigest()
    pinned = receipt.get("artifacts", {}).get("R60_SOURCE_LOCATORS_192.jsonl", {})
    if (receipt.get("schema") != SOURCE_SCHEMA
        or receipt.get("status") != SOURCE_STATUS
        or receipt.get("gold192") != 192
        or receipt.get("quality_v1_admitted") != 0
        or receipt.get("training_authorized") is not False
        or receipt.get("gpu_started") is not False
        or receipt.get("database_modified") is not False
        or receipt.get("private_values_emitted") is not False
        or pinned.get("sha256") != digest
        or pinned.get("records") != 192
        or digest != EXPECTED_SOURCE_SHA
        or len(rows) != 192):
        raise ValueError("SOURCE_PIN_INVALID")
    seen_ids = set()
    per_story = {}
    for row in rows:
        case_id, story, session, turn = (
            row.get("case_id"), row.get("story_id"), row.get("session_id"),
            row.get("turn_index"),
        )
        if (not isinstance(case_id, str) or not case_id or case_id in seen_ids
            or not isinstance(story, str) or not story
            or not isinstance(session, str) or not session
            or type(turn) is not int or turn < 1
            or row.get("source_status") != "EXACT_MATCH"):
            raise ValueError("SOURCE_LOCATOR_INVALID")
        seen_ids.add(case_id)
        per_story.setdefault(story, []).append((case_id, session, turn))
    for items in per_story.values():
        items.sort()
    # One frozen case per distinct story first; deterministic without reading
    # target prose or using random selection that could change on rerun.
    queue = [per_story[k] for k in sorted(per_story)]
    selected = []
    while len(selected) < limit and any(queue):
        for items in queue:
            if items and len(selected) < limit:
                selected.append(items.pop(0))
    return [(session, turn) for _, session, turn in selected], len(
        {row["story_id"] for row in rows}
    )


def summarize_diagnostic(results: list[tuple[bool, int, int]], total_stories: int) -> dict:
    if len(results) != MAX_PILOT or total_stories < 1 or any(
        type(exists) is not bool or type(count) is not int or type(attempts) is not int
        or count not in (0, 1) or attempts < 0 or (count == 0 and attempts != 0)
        or (count == 1 and not exists)
        for exists, count, attempts in results
    ):
        raise ValueError("INVALID_DATABASE_RESULT")
    base = summarize([(count, attempts) for _, count, attempts in results], len(results))
    by_reason = Counter(
        "EXACT_TURN_FOUND" if count else
        "SESSION_FOUND_EXACT_TURN_MISSING" if exists else
        "SESSION_NOT_FOUND"
        for exists, count, _ in results
    )
    return {
        **base,
        "schema": SCHEMA,
        "status": "REPLY_JOB_SESSION_DIAGNOSTIC_METADATA_ONLY",
        "pilot_selection": "ONE_PER_STORY_THEN_ROUND_ROBIN",
        "distinct_gold192_stories": total_stories,
        "session_found_exact_turn_missing": by_reason["SESSION_FOUND_EXACT_TURN_MISSING"],
        "session_not_found": by_reason["SESSION_NOT_FOUND"],
        "exact_turn_found": by_reason["EXACT_TURN_FOUND"],
    }


def run(dsn: str, targets: list[tuple[str, int]], stories: int) -> dict:
    import psycopg

    with (
        psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        try:
            cur.execute("SET LOCAL row_security = on")
            cur.execute("SET LOCAL statement_timeout = '3000ms'")
            cur.execute("SET LOCAL lock_timeout = '1000ms'")
            cur.execute(
                "SELECT current_user, current_setting('transaction_read_only'), "
                "current_setting('row_security')"
            )
            if cur.fetchone() != (REQUIRED_ROLE, "on", "on"):
                raise ValueError("DATABASE_GUARD_FAILED")
            cur.execute(SQL, (list(TABLES),))
            catalog = classify(cur.fetchall())
            if any(x["status"] != "CATALOG_POLICY_MATCHED_COUNTS_NOT_RUN"
                   for x in catalog.values()):
                raise ValueError("CATALOG_POLICY_HOLD")
            indexes = set(catalog["v2_chat_reply_jobs"]["index_names"])
            if not {"uq_v2_reply_job_assistant_turn", "uq_v2_reply_job_client_msg"} <= indexes:
                raise ValueError("LOCATOR_INDEX_MISSING")
            results = []
            for session, turn in targets:
                cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM public.v2_chat_reply_jobs "
                    "WHERE session_id = %s LIMIT 1)",
                    (session,),
                )
                session_found = cur.fetchone()[0]
                cur.execute(
                    "SELECT count(*)::integer, COALESCE(sum(attempt_count),0)::bigint "
                    "FROM public.v2_chat_reply_jobs "
                    "WHERE session_id=%s AND assistant_turn=%s",
                    (session, turn),
                )
                count, attempts = cur.fetchone()
                results.append((session_found, count, attempts))
        finally:
            conn.rollback()
    return summarize_diagnostic(results, stories)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-locators", type=Path, required=True)
    parser.add_argument("--source-safe", type=Path, required=True)
    args = parser.parse_args()
    dsn = os.environ.get("STORYFORGE_SUPABASE_DSN")
    if not dsn:
        print(json.dumps({"schema": SCHEMA, "status": "HOLD", "reason_code": "DSN_UNAVAILABLE"}))
        return 2
    try:
        if args.source_locators.parent != args.source_safe.parent:
            raise ValueError("SOURCE_RUN_DIR_MISMATCH")
        targets, stories = select_diverse(
            _read_private(args.source_locators),
            _read_private(args.source_safe),
        )
        receipt = run(dsn, targets, stories)
    except ValueError as exc:
        known = {"EXACT_PILOT_SIZE_REQUIRED", "SOURCE_PARSE_INVALID", "SOURCE_PIN_INVALID",
                 "SOURCE_LOCATOR_INVALID", "SOURCE_RUN_DIR_MISMATCH",
                 "DATABASE_GUARD_FAILED", "CATALOG_POLICY_HOLD", "LOCATOR_INDEX_MISSING",
                 "INVALID_DATABASE_RESULT", "PRIVATE_INPUT_PATH_INVALID",
                 "PRIVATE_INPUT_PARENT_MODE_INVALID", "PRIVATE_INPUT_FILE_MODE_INVALID"}
        code = str(exc) if str(exc) in known else "VALIDATION_HOLD"
        receipt = {"schema": SCHEMA, "status": "REPLY_JOB_SESSION_DIAGNOSTIC_HOLD",
                   "reason_code": code, "database_modified": False,
                   "private_values_emitted": False}
    except Exception as exc:  # noqa: BLE001 - DB errors can include private bind values
        receipt = {"schema": SCHEMA, "status": "REPLY_JOB_SESSION_DIAGNOSTIC_HOLD",
                   "reason_code": type(exc).__name__, "database_modified": False,
                   "private_values_emitted": False}
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "REPLY_JOB_SESSION_DIAGNOSTIC_METADATA_ONLY" else 2


if __name__ == "__main__":
    sys.exit(main())
