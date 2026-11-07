"""R60 P0: indexed, metadata-only Reply Job pilot for frozen Gold192 locators.

At most eight frozen targets; never return IDs, envelopes, or per-case values.
No authorization to promote input evidence classes or training candidates.
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
    from .r60_model_input_evidence_seed import _read_private
    from .r60_model_input_coverage_catalog import REQUIRED_ROLE, SQL, TABLES, classify
except ImportError:
    from r60_model_input_evidence_seed import _read_private
    from r60_model_input_coverage_catalog import REQUIRED_ROLE, SQL, TABLES, classify

SCHEMA = "r60_reply_job_locator_pilot_safe_v1"
SOURCE_SCHEMA = "r60_gold192_supabase_extract_v3_safe_v1"
SOURCE_STATUS = "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED"
MAX_PILOT = 8


def select_targets(raw: bytes, safe_raw: bytes, limit: int) -> list[tuple[str, int]]:
    if not 1 <= limit <= MAX_PILOT:
        raise ValueError("PILOT_LIMIT_INVALID")
    try:
        receipt = json.loads(safe_raw)
        rows = [json.loads(s) for s in raw.splitlines() if s.strip()]
    except (ValueError, UnicodeError):
        raise ValueError("SOURCE_INPUT_INVALID") from None
    pinned = receipt.get("artifacts", {}).get("R60_SOURCE_LOCATORS_192.jsonl", {})
    if (
        receipt.get("schema") != SOURCE_SCHEMA
        or receipt.get("status") != SOURCE_STATUS
        or receipt.get("gold192") != 192
        or receipt.get("quality_v1_admitted") != 0
        or receipt.get("training_authorized") is not False
        or receipt.get("gpu_started") is not False
        or receipt.get("database_modified") is not False
        or receipt.get("private_values_emitted") is not False
        or pinned.get("sha256") != hashlib.sha256(raw).hexdigest()
        or pinned.get("records") != 192
        or len(rows) != 192
    ):
        raise ValueError("SOURCE_PIN_INVALID")
    seen = set()
    targets = []
    for row in rows:
        cid, sess, turn = row.get("case_id"), row.get("session_id"), row.get("turn_index")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ValueError("SOURCE_IDENTITY_INVALID")
        seen.add(cid)
        if not isinstance(sess, str) or not sess or isinstance(turn, bool) or not isinstance(turn, int) or turn < 1:
            raise ValueError("SOURCE_LOCATOR_INVALID")
        targets.append((cid, sess, turn))
    return [(sess, turn) for _, sess, turn in sorted(targets)[:limit]]


def summarize(counts: list[tuple[int, int]], pilot_count: int) -> dict:
    if len(counts) != pilot_count or any(
        not isinstance(n, int) or not isinstance(attempts, int)
        or n < 0 or attempts < 0 or n > 1
        for n, attempts in counts
    ):
        raise ValueError("UNEXPECTED_REPLY_JOB_RESULT")
    hist = Counter("MATCH_ONE" if n == 1 else "NO_MATCH" for n, _ in counts)
    return {
        "schema": SCHEMA,
        "status": "REPLY_JOB_LOCATOR_PILOT_METADATA_ONLY_NOT_INPUT_VERIFIED",
        "frozen_gold192_total": 192,
        "pilot_targets_checked": pilot_count,
        "reply_job_exact_locator_matches": hist["MATCH_ONE"],
        "reply_job_not_found": hist["NO_MATCH"],
        "matched_job_attempt_count_sum": sum(attempts for n, attempts in counts if n == 1),
        "actual_sent_payload_verified_count": 0,
        "request_attempt_linkage_verified_count": 0,
        "input_evidence_class_counts": {
            "A": None, "B": None, "C": None, "D": None,
            "UNKNOWN_NOT_REVIEWED": 192,
        },
        "database_role_verified": REQUIRED_ROLE,
        "database_modified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def run(dsn: str, targets: list[tuple[str, int]]) -> dict:
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
                "SELECT current_user, current_setting('transaction_read_only'),"
                "current_setting('row_security')"
            )
            role, read_only, rls = cur.fetchone()
            if (role, read_only, rls) != (REQUIRED_ROLE, "on", "on"):
                raise ValueError("DATABASE_GUARD_FAILED")
            cur.execute(SQL, (list(TABLES),))
            catalog = classify(cur.fetchall())
            if any(t["status"] != "CATALOG_POLICY_MATCHED_COUNTS_NOT_RUN"
                   for t in catalog.values()):
                raise ValueError("CATALOG_HOLD")
            if "uq_v2_reply_job_assistant_turn" not in catalog[
                "v2_chat_reply_jobs"]["index_names"]:
                raise ValueError("LOCATOR_INDEX_MISSING")
            # Explicitly no SELECT of request_envelope or other private content.
            counts = []
            for sess, turn in targets:
                cur.execute(
                    "SELECT count(*)::integer, COALESCE(sum(attempt_count),0)::bigint "
                    "FROM public.v2_chat_reply_jobs "
                    "WHERE session_id = %s AND assistant_turn = %s",
                    (sess, turn),
                )
                counts.append(cur.fetchone())
        finally:
            conn.rollback()
    return summarize(counts, len(targets))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-locators", type=Path, required=True)
    parser.add_argument("--source-safe", type=Path, required=True)
    parser.add_argument("--pilot-count", type=int, default=8)
    args = parser.parse_args()
    dsn = os.environ.get("STORYFORGE_SUPABASE_DSN")
    if not dsn:
        print(json.dumps({"schema": SCHEMA, "status": "HOLD",
                          "reason_code": "DSN_UNAVAILABLE"}))
        return 2
    try:
        if args.source_locators.parent != args.source_safe.parent:
            raise ValueError("SOURCE_RUN_DIR_MISMATCH")
        targets = select_targets(
            _read_private(args.source_locators),
            _read_private(args.source_safe),
            args.pilot_count,
        )
        receipt = run(dsn, targets)
    except ValueError as exc:
        code = str(exc)
        if code not in {
            "PILOT_LIMIT_INVALID", "SOURCE_INPUT_INVALID", "SOURCE_PIN_INVALID",
            "SOURCE_IDENTITY_INVALID", "SOURCE_LOCATOR_INVALID",
            "SOURCE_RUN_DIR_MISMATCH", "DATABASE_GUARD_FAILED",
            "CATALOG_HOLD", "LOCATOR_INDEX_MISSING",
            "UNEXPECTED_REPLY_JOB_RESULT",
            "PRIVATE_INPUT_PATH_INVALID", "PRIVATE_INPUT_PARENT_MODE_INVALID",
            "PRIVATE_INPUT_FILE_MODE_INVALID",
        }:
            code = "VALIDATION_HOLD"
        receipt = {"schema": SCHEMA, "status": "REPLY_JOB_PILOT_HOLD",
                   "reason_code": code, "database_modified": False,
                   "private_values_emitted": False}
    except Exception as exc:  # noqa: BLE001 - SQL exceptions may contain private values
        receipt = {"schema": SCHEMA, "status": "REPLY_JOB_PILOT_HOLD",
                   "reason_code": type(exc).__name__,
                   "database_modified": False, "private_values_emitted": False}
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"].startswith("REPLY_JOB_LOCATOR_PILOT_") else 2


if __name__ == "__main__":
    sys.exit(main())
