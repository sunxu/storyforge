"""Aggregate-only JSON shape audit for exactly 172 frozen R60 story IDs.

Does not select JSON values, field names, titles, role names or raw IDs.
JSON type/empty coverage of current stories and revisions is not historical
actual-sent prompt provenance or semantic world independence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import r60_base336_story_db_locator_cpu as locator

SCHEMA = "storyforge_r60_base336_story_json_shape_safe_v1"
SQL = """
WITH scope AS (SELECT unnest(%s::text[]) AS story_id),
current_rows AS (
 SELECT s.characters, s.v2_data
 FROM scope i JOIN public.user_stories s ON s.id = i.story_id
),
version_rows AS (
 SELECT v.v2_data
 FROM scope i JOIN public.story_content_versions v ON v.story_id = i.story_id
)
SELECT
 (SELECT count(*)::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(characters) = 'array')::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(characters) = 'object')::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(characters) = 'array' AND jsonb_array_length(characters) = 0)::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(characters) = 'object' AND characters = '{}'::jsonb)::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(v2_data) = 'object')::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(v2_data) = 'array')::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE v2_data = '{}'::jsonb)::int FROM current_rows),
 (SELECT count(*) FILTER (WHERE v2_data = '[]'::jsonb)::int FROM current_rows),
 (SELECT count(*)::int FROM version_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(v2_data) = 'object')::int FROM version_rows),
 (SELECT count(*) FILTER (WHERE jsonb_typeof(v2_data) = 'array')::int FROM version_rows),
 (SELECT count(*) FILTER (WHERE v2_data = '{}'::jsonb)::int FROM version_rows),
 (SELECT count(*) FILTER (WHERE v2_data = '[]'::jsonb)::int FROM version_rows)
"""
FIELDS = (
    "current_story_rows", "characters_array_rows", "characters_object_rows",
    "characters_empty_array_rows", "characters_empty_object_rows",
    "v2_object_rows", "v2_array_rows", "v2_empty_object_rows",
    "v2_empty_array_rows", "version_rows", "version_v2_object_rows",
    "version_v2_array_rows", "version_v2_empty_object_rows",
    "version_v2_empty_array_rows",
)


class Hold(ValueError):
    pass


def validate(result: tuple) -> dict:
    if (type(result) is not tuple or len(result) != len(FIELDS)
            or any(type(x) is not int or x < 0 for x in result)):
        raise Hold("JSON_COUNTS_CONTRACT_HOLD")
    row = dict(zip(FIELDS, result, strict=True))
    if row["current_story_rows"] > 172:
        raise Hold("JSON_COUNTS_BOUNDS_HOLD")
    for name, value in row.items():
        upper = row["version_rows"] if name.startswith("version_") else row["current_story_rows"]
        if value > upper:
            raise Hold("JSON_COUNTS_BOUNDS_HOLD")
    for prefix, keys in (
        ("current_story_rows", ("characters_array_rows", "characters_object_rows")),
        ("current_story_rows", ("v2_object_rows", "v2_array_rows")),
        ("version_rows", ("version_v2_object_rows", "version_v2_array_rows")),
    ):
        if sum(row[k] for k in keys) > row[prefix]:
            raise Hold("JSON_COUNTS_BOUNDS_HOLD")
    return {
        "schema": SCHEMA,
        "status": "BASE336_STORY_JSON_SHAPE_COUNTS__SEMANTIC_HISTORICAL_HOLD",
        "frozen_cases": 336,
        "frozen_story_ids": 172,
        "json_shape_counts": row,
        "historical_story_version_verified": False,
        "historical_actual_sent_system_verified": False,
        "semantic_world_alias_verified": False,
        "world_component_isolation_verified": False,
        "reviewer_independence_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "database_modified": False,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "model_requests": 0,
        "private_values_emitted": False,
    }


def query(stories: list[str], dsn: str) -> dict:
    if not dsn:
        raise Hold("DSN_NOT_SET_HOLD")
    import psycopg

    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("SET LOCAL statement_timeout='15000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("""
                    SELECT current_user,current_setting('transaction_read_only'),
                           current_setting('row_security'),r.rolbypassrls,r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                """)
                locator.private.assert_guard(cur.fetchone())
                cur.execute(SQL, (stories,))
                result = cur.fetchone()
                return validate(result)
        finally:
            conn.rollback()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    try:
        stories = locator.scoped_stories(*_frozen(args))
        if not args.execute:
            result = {
                "schema": SCHEMA,
                "status": "BASE336_JSON_SHAPE_PRECHECK__NO_DB",
                "frozen_story_ids": len(stories),
                "train_admitted": 0, "database_accessed": False,
                "database_modified": False, "gpu_started": False,
                "private_values_emitted": False,
            }
        else:
            result = query(stories, os.getenv("R60_READONLY_DATABASE_URL", ""))
            result["database_accessed"] = True
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - suppress all content and exception text
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE336_STORY_JSON_SHAPE_HOLD",
            "train_admitted": 0, "database_modified": False,
            "private_values_emitted": False, "gpu_started": False,
        }, sort_keys=True))
        return 42


def _frozen(args: argparse.Namespace) -> tuple[list[dict], dict]:
    import hashlib
    import json

    identity = locator.identity
    quarantine = locator.quarantine
    private = locator.private
    cases, report = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir)
    raw = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    expected = quarantine.construct(cases, report, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME, quarantine.MAX_PRIVATE_REPORT))
    if expected != saved:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    return cases, saved


if __name__ == "__main__":
    sys.exit(main())
