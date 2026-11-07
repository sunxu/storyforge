"""R60 P0: read-only production catalog preflight for model-input evidence sources.

No business rows are accessed. Never switches roles or disables RLS.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

TABLES = ("v2_chat_reply_jobs", "chat_abnormal_snapshot", "chat_latency_metrics")
REQUIRED_ROLE = "r58_export_reader"
SCHEMA = "r60_input_evidence_catalog_preflight_safe_v1"
COLUMNS = {
    "v2_chat_reply_jobs": ("id", "session_id", "assistant_turn", "request_envelope",
                           "attempt_count", "model_id", "created_at"),
    "chat_abnormal_snapshot": ("request_id", "relay_request_id", "conversation_context",
                               "history_preview", "expires_at"),
    "chat_latency_metrics": ("request_id", "relay_request_id", "attempt_trace"),
}


def classify(rows: list[tuple]) -> dict:
    """Classify catalog tuples only: (table, column, type, rls, select, index_columns)."""
    result = {}
    for table in TABLES:
        selected = [x for x in rows if x[0] == table]
        columns = {x[1] for x in selected if x[1] is not None}
        required = set(COLUMNS[table])
        access = bool(selected) and all(x[4] is True for x in selected)
        rls = bool(selected) and all(x[3] is True for x in selected)
        indices = sorted({x[5] for x in selected if x[5]})
        missing = sorted(required - columns)
        result[table] = {
            "present": bool(selected),
            "columns_present": sorted(required & columns),
            "missing_expected_columns": missing,
            "select_privilege": access,
            "rls_enabled": rls,
            "index_names": indices,
            "status": ("CATALOG_ABSENT" if not selected else
                       "SCHEMA_OR_PERMISSION_HOLD" if missing or not access or not rls else
                       "CATALOG_READY_COUNTS_NOT_RUN"),
        }
    return result


SQL = """
SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod),
       c.relrowsecurity, has_table_privilege(current_user, c.oid, 'SELECT'),
       ix.indexrelid::regclass::text
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
LEFT JOIN pg_catalog.pg_attribute AS a
  ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
LEFT JOIN pg_catalog.pg_index AS ix
  ON ix.indrelid = c.oid AND ix.indisvalid AND ix.indisready
WHERE n.nspname = 'public' AND c.relname = ANY(%s)
  AND c.relkind IN ('r', 'p')
ORDER BY c.relname, a.attnum, ix.indexrelid
"""


def run(dsn: str) -> dict:
    import psycopg

    # Per-session guard precedes catalog read, and the transaction is read-only.
    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cur.execute("SET LOCAL statement_timeout = '15000ms'")
            cur.execute("SET LOCAL lock_timeout = '1000ms'")
            cur.execute("SET LOCAL row_security = on")
            cur.execute(
                "SELECT current_user, current_setting('transaction_read_only'), "
                "current_setting('row_security'), "
                "current_setting('statement_timeout'), current_setting('lock_timeout')"
            )
            role, read_only, rls, statement_timeout, lock_timeout = cur.fetchone()
            if (role != REQUIRED_ROLE or read_only != "on" or rls != "on"
                    or statement_timeout not in ("15s", "15000ms")
                    or lock_timeout not in ("1s", "1000ms")):
                raise ValueError("DATABASE_GUARD_FAILED")
            cur.execute(SQL, (list(TABLES),))
            rows = cur.fetchall()
            conn.rollback()
    tables = classify(rows)
    return {
        "schema": SCHEMA,
        "status": ("CATALOG_PREFLIGHT_PASS_NO_BUSINESS_ROWS_READ"
                   if all(t["status"] == "CATALOG_READY_COUNTS_NOT_RUN"
                          for t in tables.values())
                   else "CATALOG_PREFLIGHT_HOLD"),
        "database_role_verified": REQUIRED_ROLE,
        "transaction_read_only": True,
        "row_security": True,
        "business_rows_read": 0,
        "aggregate_counts_executed": False,
        "tables": tables,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    dsn = os.environ.get("STORYFORGE_SUPABASE_DSN")
    if not dsn:
        print(json.dumps({"status": "HOLD", "reason": "DSN_UNAVAILABLE"}))
        return 2
    try:
        result = run(dsn)
    except (Exception,) as exc:
        # Intentionally never print exception text (may include DSN or SQL values).
        print(json.dumps({"status": "CATALOG_PREFLIGHT_HOLD",
                          "reason_code": type(exc).__name__,
                          "database_modified": False,
                          "private_values_emitted": False}))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "CATALOG_PREFLIGHT_PASS_NO_BUSINESS_ROWS_READ" else 2


if __name__ == "__main__":
    sys.exit(main())
