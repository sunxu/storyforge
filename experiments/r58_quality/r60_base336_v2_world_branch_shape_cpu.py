"""Aggregate-only V2 world and runtime card branch shape for frozen 172 stories.

Grounded in RolePlay pinned V2 route selecting characters when cardType='story',
or single character otherwise. No raw JSON, names, keys enumerated or IDs.
Historical actual-sent prompt and semantic alias independence remain HOLD.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import r60_base336_story_db_locator_cpu as locator
import r60_base336_story_json_shape_cpu as prior

SCHEMA = "storyforge_r60_base336_v2_world_branch_shape_safe_v1"
FIELDS = (
    "total", "story_branch", "nonstory_branch",
    "story_branch_characters_nonempty", "story_branch_characters_empty",
    "nonstory_branch_character_object",
    "world_object", "world_array", "world_string", "world_null",
    "world_empty_object", "world_empty_array", "world_empty_string",
    "world_nested_nonempty_object", "opening_object", "opening_string",
    "opening_array",
)
SQL = """
WITH scope AS (SELECT unnest(%s::text[]) AS story_id),
records AS (
 SELECT 'current'::text AS origin, s.v2_data AS d
 FROM scope i JOIN public.user_stories s ON s.id=i.story_id
 UNION ALL
 SELECT 'version'::text AS origin, v.v2_data AS d
 FROM scope i JOIN public.story_content_versions v ON v.story_id=i.story_id
)
SELECT origin,
 count(*)::int,
 count(*) FILTER (WHERE d->>'cardType' = 'story')::int,
 count(*) FILTER (WHERE d->>'cardType' IS DISTINCT FROM 'story')::int,
 count(*) FILTER (WHERE d->>'cardType' = 'story' AND
    CASE WHEN jsonb_typeof(d->'characters')='array'
      THEN jsonb_array_length(d->'characters')>0 ELSE false END)::int,
 count(*) FILTER (WHERE d->>'cardType' = 'story' AND
    d->'characters'='[]'::jsonb)::int,
 count(*) FILTER (WHERE d->>'cardType' IS DISTINCT FROM 'story'
    AND jsonb_typeof(d->'character')='object')::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'world')='object')::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'world')='array')::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'world')='string')::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'world') IS NULL
    OR jsonb_typeof(d->'world')='null')::int,
 count(*) FILTER (WHERE d->'world'='{}'::jsonb)::int,
 count(*) FILTER (WHERE d->'world'='[]'::jsonb)::int,
 count(*) FILTER (WHERE d->'world'='""'::jsonb)::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'world')='object'
    AND d->'world'<>'{}'::jsonb)::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'opening')='object')::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'opening')='string')::int,
 count(*) FILTER (WHERE jsonb_typeof(d->'opening')='array')::int
FROM records GROUP BY origin ORDER BY origin
"""


class Hold(ValueError):
    pass


def verify(rows: list[tuple]) -> dict:
    if (type(rows) is not list or len(rows) != 2 or
            any(type(r) is not tuple or len(r) != len(FIELDS) + 1
                for r in rows) or
            {r[0] for r in rows} != {"current", "version"}):
        raise Hold("WORLD_SHAPE_RESULT_HOLD")
    results = {}
    for origin, *values in rows:
        if any(type(n) is not int or n < 0 for n in values):
            raise Hold("WORLD_SHAPE_TYPE_HOLD")
        x = dict(zip(FIELDS, values, strict=True))
        n = x["total"]
        if (n > (172 if origin == "current" else 10000)
                or any(v > n for v in values[1:])
                or x["story_branch"] + x["nonstory_branch"] != n
                or x["story_branch_characters_nonempty"]
                   + x["story_branch_characters_empty"] > x["story_branch"]
                or x["nonstory_branch_character_object"] > x["nonstory_branch"]
                or (x["world_object"] + x["world_array"] +
                    x["world_string"] + x["world_null"]) != n
                or x["world_empty_object"] +
                   x["world_nested_nonempty_object"] != x["world_object"]
                or x["world_empty_array"] > x["world_array"]
                or x["world_empty_string"] > x["world_string"]
                or x["opening_object"] + x["opening_string"] +
                   x["opening_array"] > n):
            raise Hold("WORLD_SHAPE_BOUNDS_HOLD")
        results[origin] = x
    return {
        "schema": SCHEMA,
        "status": "BASE336_V2_WORLD_BRANCH_COUNTS__SEMANTIC_HISTORY_HOLD",
        "frozen_cases": 336, "frozen_story_ids": 172,
        "shape_counts": results,
        "world_text_or_character_data_read": False,
        "historical_actual_sent_prompt_verified": False,
        "historical_story_version_verified": False,
        "semantic_world_alias_verified": False,
        "world_component_isolation_verified": False,
        "reviewer_independence_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0, "model_requests": 0,
        "hf_jobs_submitted": 0, "gpu_started": False,
        "database_modified": False, "private_values_emitted": False,
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
                return verify(cur.fetchall())
        finally:
            conn.rollback()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        stories = locator.scoped_stories(*prior._frozen(args))
        if args.execute:
            safe = query(stories, os.getenv("R60_READONLY_DATABASE_URL", ""))
            safe["database_accessed"] = True
        else:
            safe = {
                "schema": SCHEMA, "status": "BASE336_V2_WORLD_BRANCH_PRECHECK__NO_DB",
                "frozen_story_ids": len(stories),
                "database_accessed": False, "database_modified": False,
                "train_admitted": 0, "gpu_started": False,
                "private_values_emitted": False,
            }
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - suppress private source and DB error text
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE336_V2_WORLD_BRANCH_HOLD",
            "train_admitted": 0, "database_modified": False,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
