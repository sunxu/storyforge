"""Aggregate-only exact V2 world equality screen for the frozen 172 Story IDs.

JSONB world definitions are compared inside PostgreSQL, not returned to Python.
Includes current-current and current+archived cross-story candidate links.
Equal world JSON is an evidence hint, NOT a semantic alias verdict: generic
templates can match. Version records are NOT proven actual-sent snapshots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import r60_base336_story_db_locator_cpu as locator
import r60_base336_story_json_shape_cpu as prior
import r60_base_start_world_split_preview as split

SCHEMA = "storyforge_r60_base336_world_exact_value_screen_safe_v1"
SQL = """
WITH scope AS (
 SELECT ids.story_id, ids.split
 FROM unnest(%s::text[], %s::text[]) AS ids(story_id, split)
),
records AS (
 SELECT 'current'::text AS record_kind, s.id AS story_id,
        i.split, s.v2_data->'world' AS world
 FROM scope i JOIN public.user_stories s ON s.id=i.story_id
 UNION ALL
 SELECT 'version'::text AS record_kind, v.story_id,
        i.split, v.v2_data->'world' AS world
 FROM scope i JOIN public.story_content_versions v ON v.story_id=i.story_id
),
comparisons AS (
 SELECT 'current'::text AS comparison, story_id, split, world
 FROM records WHERE record_kind='current'
 UNION ALL
 SELECT 'current_plus_versions'::text AS comparison, story_id, split, world
 FROM records
),
world_groups AS (
 SELECT comparison, world,
        count(DISTINCT story_id)::int AS distinct_stories,
        count(DISTINCT story_id) FILTER (WHERE split='train')::int AS train_stories,
        count(DISTINCT story_id) FILTER (WHERE split='validation')::int AS val_stories
 FROM comparisons
 WHERE jsonb_typeof(world)='object' AND world <> '{}'::jsonb
 GROUP BY comparison, world
),
result AS (
 SELECT comparison,
        count(*)::int AS distinct_nonempty_world_values,
        count(*) FILTER (WHERE distinct_stories > 1)::int AS cross_story_groups,
        coalesce(sum(distinct_stories*(distinct_stories-1)/2)
          FILTER (WHERE distinct_stories > 1), 0)::int AS cross_story_pair_instances,
        count(*) FILTER (WHERE train_stories>0 AND val_stories>0)::int
          AS train_validation_crossing_groups
 FROM world_groups
 GROUP BY comparison
)
SELECT comparison, distinct_nonempty_world_values, cross_story_groups,
       cross_story_pair_instances, train_validation_crossing_groups
FROM result ORDER BY comparison
"""
COLUMNS = (
    "distinct_nonempty_world_values", "cross_story_groups",
    "cross_story_pair_instances", "train_validation_crossing_groups",
)


class Hold(ValueError):
    pass


def split_labels(stories: list[str]) -> list[str]:
    if type(stories) is not list or len(stories) != 172 or len(set(stories)) != 172:
        raise Hold("STORY_SCOPE_HOLD")
    return [
        "validation" if int.from_bytes(
            hashlib.sha256(split.SALT + world.encode("utf-8")).digest()[:8],
            "big",
        ) % 100 < split.VAL_PERCENT else "train"
        for world in stories
    ]


def verify(rows: list[tuple]) -> dict:
    if (type(rows) is not list or len(rows) != 2
            or any(type(r) is not tuple or len(r) != 5 for r in rows)
            or {r[0] for r in rows} != {"current", "current_plus_versions"}):
        raise Hold("WORLD_EQUALITY_RESULT_HOLD")
    checked = {}
    for kind, *values in rows:
        if any(type(n) is not int or n < 0 for n in values):
            raise Hold("WORLD_EQUALITY_TYPE_HOLD")
        distinct, groups, pairs, crossing = values
        if (distinct > 372 or groups > distinct
                or crossing > groups or pairs < groups
                or pairs > (172*171//2)*distinct):
            raise Hold("WORLD_EQUALITY_BOUNDS_HOLD")
        checked[kind] = dict(zip(COLUMNS, values, strict=True))
    if (checked["current"]["distinct_nonempty_world_values"] > 172
            or checked["current"]["cross_story_pair_instances"] > 172*171//2
            or checked["current"]["cross_story_groups"] >
               checked["current_plus_versions"]["cross_story_groups"]
               + checked["current_plus_versions"]["distinct_nonempty_world_values"]):
        raise Hold("WORLD_EQUALITY_SCOPE_HOLD")
    return {
        "schema": SCHEMA,
        "status": "BASE336_WORLD_EXACT_VALUE_SCREEN__SEMANTIC_HISTORY_HOLD",
        "frozen_cases": 336, "frozen_story_ids": 172,
        "world_equality_counts": checked,
        "world_json_or_digest_returned_to_client": False,
        "cross_story_equal_world_is_provisional_evidence": True,
        "world_definition_semantic_alias_verified": False,
        "historical_actual_sent_version_verified": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
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
                cur.execute(SQL, (stories, split_labels(stories)))
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
                "schema": SCHEMA,
                "status": "BASE336_WORLD_EXACT_VALUE_PRECHECK__NO_DB",
                "frozen_story_ids": len(stories), "database_accessed": False,
                "database_modified": False, "train_admitted": 0,
                "gpu_started": False, "private_values_emitted": False,
            }
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no DB exception, text or private ID emitted
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE336_WORLD_EXACT_VALUE_HOLD",
            "database_accessed": None, "train_admitted": 0,
            "database_modified": False, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
