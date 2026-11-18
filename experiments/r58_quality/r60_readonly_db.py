"""Shared read-only PostgreSQL boundary helpers for R60 quality/evaluation jobs.

The helpers normalize PostgreSQL-native values at the database boundary so
quality scripts do not accidentally reject valid UUID/timestamptz values or
silently treat naive timestamps as local time.  They are read-only by design:
the transaction is REPEATABLE READ + READ ONLY with row security enabled.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

DEFAULT_READER_ROLE = "r58_export_reader"


class ReadOnlyDBHold(ValueError):
    """Fail-closed database boundary error."""


def normalize_identifier(value: object, *, field: str = "identifier") -> str:
    """Return a canonical text identifier from psycopg UUID or text output."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str) and value:
        return value
    raise ReadOnlyDBHold(f"DB_IDENTIFIER_HOLD:{field}")


def normalize_timestamp(value: object, *, field: str = "timestamp") -> datetime:
    """Return a timezone-aware datetime; naive timestamps are rejected."""
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ReadOnlyDBHold(f"DB_TIMESTAMP_HOLD:{field}") from exc
    else:
        raise ReadOnlyDBHold(f"DB_TIMESTAMP_HOLD:{field}")
    if result.tzinfo is None or result.utcoffset() is None:
        raise ReadOnlyDBHold(f"DB_TIMESTAMP_HOLD:{field}")
    return result


def normalize_identifier_fields(
    row: dict[str, Any],
    fields: Sequence[str],
) -> dict[str, Any]:
    """Normalize required identifier fields in-place and return the row."""
    for field in fields:
        row[field] = normalize_identifier(row.get(field), field=field)
    return row


def assert_readonly_guard(
    row: tuple[Any, ...] | None,
    *,
    expected_role: str = DEFAULT_READER_ROLE,
) -> None:
    """Require the exact restricted reader transaction contract."""
    expected = (expected_role, "on", "on", False, False)
    if row != expected:
        raise ReadOnlyDBHold("DATABASE_GUARD_HOLD")


def fetch_dict_rows(
    dsn: str,
    sql: str,
    params: Sequence[Any] = (),
    *,
    expected_role: str = DEFAULT_READER_ROLE,
    connect_timeout: int = 10,
    statement_timeout_ms: int = 30_000,
    lock_timeout_ms: int = 1_000,
) -> list[dict[str, Any]]:
    """Execute one read-only query and return rows keyed by column name.

    psycopg's native UUID/datetime objects are deliberately preserved here;
    callers must normalize fields through the shared helpers before applying
    business validation.  Database exceptions are intentionally propagated so
    callers can emit their own redacted diagnostic receipt.
    """
    if not isinstance(dsn, str) or not dsn:
        raise ReadOnlyDBHold("DB_DSN_NOT_SET_HOLD")
    if not isinstance(sql, str) or not sql.strip():
        raise ReadOnlyDBHold("DB_SQL_HOLD")

    import psycopg

    with psycopg.connect(
        dsn,
        connect_timeout=connect_timeout,
        autocommit=False,
    ) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                )
                cur.execute("SET LOCAL row_security=on")
                cur.execute(
                    f"SET LOCAL statement_timeout='{int(statement_timeout_ms)}ms'"
                )
                cur.execute(
                    f"SET LOCAL lock_timeout='{int(lock_timeout_ms)}ms'"
                )
                cur.execute(
                    """
                    SELECT current_user,current_setting('transaction_read_only'),
                           current_setting('row_security'),r.rolbypassrls,r.rolsuper
                    FROM pg_catalog.pg_roles r
                    WHERE r.rolname=current_user
                    """
                )
                assert_readonly_guard(cur.fetchone(), expected_role=expected_role)
                cur.execute(sql, params)
                columns = [desc[0] for desc in cur.description]
                return [
                    dict(zip(columns, row, strict=True))
                    for row in cur.fetchall()
                ]
        finally:
            conn.rollback()
