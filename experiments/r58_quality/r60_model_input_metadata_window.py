"""R60 P0 S2: bounded metadata-only coverage for two indexed evidence tables.

No request body, JSONB, message, user ID, story ID or session ID leaves SQL.
Reply-job counts remain HOLD until a safe selective index/path is established.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

try:
    from .r60_model_input_coverage_catalog import (
        METADATA_SELECT_COLUMNS,
        REQUIRED_ROLE,
        SQL,
        TABLES,
        classify,
    )
except ImportError:
    from r60_model_input_coverage_catalog import (
        METADATA_SELECT_COLUMNS,
        REQUIRED_ROLE,
        SQL,
        TABLES,
        classify,
    )

SCHEMA = "r60_model_input_metadata_window_safe_v1"
MAX_WINDOW = dt.timedelta(days=1)
QUERIES = {
    "chat_abnormal_snapshot": """
      SELECT count(*)::bigint,
             count(request_id)::bigint,
             count(relay_request_id)::bigint
      FROM public.chat_abnormal_snapshot
      WHERE created_at >= %s AND created_at < %s
    """,
    "chat_latency_metrics": """
      SELECT count(*)::bigint,
             count(request_id)::bigint,
             count(relay_request_id)::bigint
      FROM public.chat_latency_metrics
      WHERE created_at >= %s AND created_at < %s
    """,
}
EXPECTED_DATE_INDEXES = {
    "chat_abnormal_snapshot": "idx_chat_abnormal_snapshot_created",
    "chat_latency_metrics": "idx_chat_latency_metrics_created",
}
REQUIRED_COUNT_COLUMNS = {"created_at", "request_id", "relay_request_id"}


def validate_window(start: str, end: str) -> tuple[dt.datetime, dt.datetime]:
    try:
        a = dt.datetime.fromisoformat(start)
        b = dt.datetime.fromisoformat(end)
    except ValueError as exc:
        raise ValueError("WINDOW_PARSE_INVALID") from exc
    if a.tzinfo is None or b.tzinfo is None:
        raise ValueError("WINDOW_TZ_REQUIRED")
    if not dt.timedelta(0) < b - a <= MAX_WINDOW:
        raise ValueError("WINDOW_NOT_BOUNDED")
    return a.astimezone(dt.UTC), b.astimezone(dt.UTC)


def check_catalog(tables: dict) -> None:
    if set(tables) != set(TABLES):
        raise ValueError("CATALOG_INCOMPLETE")
    for name, values in tables.items():
        if values["status"] != "CATALOG_POLICY_MATCHED_COUNTS_NOT_RUN":
            raise ValueError("CATALOG_POLICY_HOLD")
        if name in QUERIES and EXPECTED_DATE_INDEXES[name] not in values["index_names"]:
            raise ValueError("DATE_INDEX_MISSING")
        if name in QUERIES and not REQUIRED_COUNT_COLUMNS.issubset(
            set(METADATA_SELECT_COLUMNS[name]) | set(values["columns_present"])
        ):
            raise ValueError("COUNT_COLUMNS_MISSING")


def run(dsn: str, start: str, end: str) -> dict:
    import psycopg

    a, b = validate_window(start, end)
    with (
        psycopg.connect(dsn, autocommit=True, connect_timeout=10) as conn,
        conn.cursor() as cur,
    ):
        cur.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        try:
            cur.execute("SET LOCAL statement_timeout = '8000ms'")
            cur.execute("SET LOCAL lock_timeout = '1000ms'")
            cur.execute("SET LOCAL row_security = on")
            cur.execute(
                "SELECT current_user, current_setting('transaction_read_only'),"
                "current_setting('row_security'),"
                "current_setting('statement_timeout'),"
                "current_setting('lock_timeout')"
            )
            role, read_only, row_security, stmt_timeout, lock_timeout = cur.fetchone()
            if (
                role != REQUIRED_ROLE or read_only != "on" or row_security != "on"
                or stmt_timeout not in ("8s", "8000ms")
                or lock_timeout not in ("1s", "1000ms")
            ):
                raise ValueError("DATABASE_GUARD_FAILED")
            cur.execute(SQL, (list(TABLES),))
            catalog = classify(cur.fetchall())
            check_catalog(catalog)
            outcomes = {}
            for table_name, query in QUERIES.items():
                cur.execute(query, (a, b))
                total, request, relay = cur.fetchone()
                if not 0 <= request <= total or not 0 <= relay <= total:
                    raise ValueError("INCONSISTENT_AGGREGATE")
                outcomes[table_name] = {
                    "rows_in_window": total,
                    "request_id_present": request,
                    "relay_request_id_present": relay,
                }
        finally:
            conn.rollback()

    return {
        "schema": SCHEMA,
        "status": "METADATA_WINDOW_AGGREGATES_ONLY_NOT_CASE_LINKED",
        "window_start_utc": a.isoformat(),
        "window_end_utc": b.isoformat(),
        "database_role_verified": REQUIRED_ROLE,
        "tables": outcomes,
        "v2_chat_reply_jobs": {
            "status": "HOLD_NO_VERIFIED_CREATED_AT_LEADING_INDEX",
            "rows_in_window": None,
        },
        "aggregate_counts_executed": True,
        "business_rows_returned": 0,
        "raw_identifier_values_emitted": False,
        "actual_sent_payload_verified_count": 0,
        "request_attempt_linkage_verified_count": 0,
        "input_evidence_class_counts": {
            "A": None, "B": None, "C": None, "D": None,
            "UNKNOWN_NOT_REVIEWED": 192,
        },
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True, help="ISO-8601 with timezone")
    p.add_argument("--end", required=True, help="ISO-8601 with timezone; <= 24h")
    args = p.parse_args()
    dsn = os.environ.get("STORYFORGE_SUPABASE_DSN")
    if not dsn:
        print(json.dumps({"schema": SCHEMA, "status": "HOLD", "reason_code": "DSN_UNAVAILABLE"}))
        return 2
    try:
        result = run(dsn, args.start, args.end)
    except (ValueError, OSError) as exc:
        result = {"schema": SCHEMA, "status": "METADATA_WINDOW_HOLD",
                  "reason_code": str(exc) if isinstance(exc, ValueError) else "IO_HOLD",
                  "database_modified": False, "private_values_emitted": False}
        print(json.dumps(result, sort_keys=True))
        return 2
    except Exception as exc:  # noqa: BLE001 - DB exception text may reveal credentials
        print(json.dumps({"schema": SCHEMA, "status": "METADATA_WINDOW_HOLD",
                          "reason_code": type(exc).__name__,
                          "database_modified": False, "private_values_emitted": False}))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
