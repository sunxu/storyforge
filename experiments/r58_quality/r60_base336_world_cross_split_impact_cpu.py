"""Scope-bound aggregate impact of exact cross-split V2 world reuse.

Counts *distinct* affected story IDs and frozen candidate cases for the
existing 276/60 provisional split. Compares current worlds and
current+archived versions, with only aggregate rows leaving PostgreSQL.
Equality is not evidence of semantic identity or historical prompt use.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import r60_base336_story_db_locator_cpu as locator
import r60_base336_story_json_shape_cpu as prior
import r60_base336_world_exact_value_cpu as equality

SCHEMA = "storyforge_r60_base336_world_cross_split_impact_safe_v1"
SQL = """
WITH scope AS (
 SELECT s.story_id, s.split, s.case_count
 FROM unnest(%s::text[], %s::text[], %s::int[])
 AS s(story_id, split, case_count)
),
records AS (
 SELECT 'current'::text AS kind, s.id AS story_id,
        i.split, s.v2_data->'world' AS world
 FROM scope i JOIN public.user_stories s ON s.id=i.story_id
 UNION ALL
 SELECT 'version'::text AS kind, v.story_id,
        i.split, v.v2_data->'world' AS world
 FROM scope i JOIN public.story_content_versions v ON v.story_id=i.story_id
),
compared AS (
 SELECT 'current'::text AS comparison, story_id, split, world
 FROM records WHERE kind='current'
 UNION ALL
 SELECT 'current_plus_versions'::text, story_id, split, world
 FROM records
),
membership AS (
 SELECT DISTINCT comparison, world, story_id, split
 FROM compared
 WHERE jsonb_typeof(world)='object' AND world <> '{}'::jsonb
),
cross_world AS (
 SELECT comparison, world
 FROM membership
 GROUP BY comparison, world
 HAVING count(*) FILTER (WHERE split='train') > 0
    AND count(*) FILTER (WHERE split='validation') > 0
),
affected AS (
 SELECT DISTINCT m.comparison, m.story_id, m.split
 FROM membership m JOIN cross_world c
 ON c.comparison=m.comparison AND c.world=m.world
)
SELECT
 comparison,
 count(*) FILTER (WHERE split='train')::int AS train_stories,
 count(*) FILTER (WHERE split='validation')::int AS val_stories,
 coalesce(sum(s.case_count) FILTER (WHERE a.split='train'),0)::int
    AS train_cases,
 coalesce(sum(s.case_count) FILTER (WHERE a.split='validation'),0)::int
    AS val_cases
FROM affected a JOIN scope s ON s.story_id=a.story_id
GROUP BY comparison ORDER BY comparison
"""
NAMES = ("train_stories", "validation_stories", "train_cases", "validation_cases")


class Hold(ValueError):
    pass


def candidate_counts(cases: list[dict], manifest: dict, stories: list[str]) -> list[int]:
    valid = set(stories)
    counter: Counter[str] = Counter()
    for row in manifest["remaining_full_r50_hold"]:
        pos = row["position"]
        src = cases[pos - 1]["source"]["story_id"]
        if src not in valid:
            raise Hold("SCOPE_CASE_COUNT_HOLD")
        counter[src] += 1
    counts = [counter[s] for s in stories]
    if len(counts) != 172 or sum(counts) != 336 or any(n < 1 for n in counts):
        raise Hold("SCOPE_CASE_COUNT_HOLD")
    return counts


def verify(rows: list[tuple]) -> dict:
    if (type(rows) is not list or len(rows) > 2 or
            any(type(r) is not tuple or len(r) != 5 for r in rows) or
            any(r[0] not in {"current", "current_plus_versions"} for r in rows)
            or len({r[0] for r in rows}) != len(rows)):
        raise Hold("IMPACT_RESULT_SHAPE_HOLD")
    out = {
        key: dict.fromkeys(NAMES, 0)
        for key in ("current", "current_plus_versions")
    }
    for kind, *values in rows:
        if any(type(x) is not int or x < 0 for x in values):
            raise Hold("IMPACT_RESULT_TYPE_HOLD")
        t, v, tc, vc = values
        if t+v > 172 or tc+vc > 336 or tc < t or vc < v or (t == 0) != (v == 0):
            raise Hold("IMPACT_RESULT_BOUNDS_HOLD")
        out[kind] = dict(zip(NAMES, values, strict=True))
    for name in NAMES:
        if out["current_plus_versions"][name] < out["current"][name]:
            raise Hold("IMPACT_MONOTONICITY_HOLD")
    return {
        "schema": SCHEMA,
        "status": "BASE336_EXACT_WORLD_CROSS_SPLIT_IMPACT__SPLIT_HOLD",
        "frozen_cases": 336, "frozen_story_ids": 172,
        "cross_split_affected": out,
        "old_276_60_preview_valid_for_admission": False,
        "same_world_definition_is_not_semantic_identity_proof": True,
        "historical_version_at_target_verified": False,
        "world_component_isolation_verified": False,
        "reviewer_independence_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "database_modified": False,
        "hf_jobs_submitted": 0, "model_requests": 0,
        "gpu_started": False, "private_values_emitted": False,
    }


def query(stories: list[str], counts: list[int], dsn: str) -> dict:
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
                cur.execute(SQL, (stories, equality.split_labels(stories), counts))
                return verify(cur.fetchall())
        finally:
            conn.rollback()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        cases, manifest = prior._frozen(args)
        stories = locator.scoped_stories(cases, manifest)
        counts = candidate_counts(cases, manifest, stories)
        if args.execute:
            safe = query(stories, counts, os.getenv("R60_READONLY_DATABASE_URL", ""))
            safe["database_accessed"] = True
        else:
            safe = {
                "schema": SCHEMA,
                "status": "BASE336_WORLD_CROSS_SPLIT_IMPACT_PRECHECK__NO_DB",
                "frozen_cases": 336, "frozen_story_ids": 172,
                "database_accessed": False,
                "train_admitted": 0, "gpu_started": False,
                "database_modified": False, "private_values_emitted": False,
            }
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - never disclose DB/private text
        print(json.dumps({
            "schema": SCHEMA,
            "status": "BASE336_WORLD_CROSS_SPLIT_IMPACT_HOLD",
            "database_accessed": None,
            "train_admitted": 0, "gpu_started": False,
            "database_modified": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
