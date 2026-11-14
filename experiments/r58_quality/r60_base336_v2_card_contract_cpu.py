"""Scoped V2 runtime-card structural coverage, aggregate-only.

Keys are grounded in pinned RolePlay V2 chat route:
v2Draft.cardType==='story' ? v2Draft.characters : [v2Draft.character].
No JSON text, character names, story IDs, or prompt content are selected.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import r60_base336_story_db_locator_cpu as locator
import r60_base336_story_json_shape_cpu as prior

SCHEMA = "storyforge_r60_base336_v2_card_contract_safe_v1"
SQL = """
WITH scope AS (SELECT unnest(%s::text[]) AS story_id),
current_rows AS (
 SELECT s.v2_data AS d
 FROM scope i JOIN public.user_stories s ON s.id=i.story_id
),
version_rows AS (
 SELECT v.v2_data AS d
 FROM scope i JOIN public.story_content_versions v ON v.story_id=i.story_id
),
combined AS (
 SELECT 'current'::text AS origin, d FROM current_rows
 UNION ALL SELECT 'version', d FROM version_rows
)
SELECT origin,
 count(*)::int AS total,
 count(*) FILTER (WHERE d->>'cardType'='story')::int AS story_type,
 count(*) FILTER (WHERE d->>'cardType'='character')::int AS character_type,
 count(*) FILTER (WHERE d->>'cardType' IS NULL)::int AS absent_type,
 count(*) FILTER (WHERE jsonb_typeof(d->'characters')='array')::int AS char_array,
 count(*) FILTER (WHERE CASE WHEN jsonb_typeof(d->'characters')='array'
  THEN jsonb_array_length(d->'characters') > 0 ELSE false END)::int AS nonempty_char_array,
 count(*) FILTER (WHERE jsonb_typeof(d->'character')='object')::int AS char_object,
 count(*) FILTER (WHERE d ? 'opening')::int AS opening_key,
 count(*) FILTER (WHERE d ? 'world')::int AS world_key
FROM combined GROUP BY origin ORDER BY origin
"""
KEYS = ("total", "story_type", "character_type", "absent_type",
        "char_array", "nonempty_char_array", "char_object", "opening_key",
        "world_key")


class Hold(ValueError):
    pass


def verify(rows: list[tuple]) -> dict:
    if (type(rows) is not list or len(rows) != 2
            or {r[0] for r in rows if type(r) is tuple and len(r) == 10}
            != {"current", "version"}):
        raise Hold("CARD_RESULT_SHAPE_HOLD")
    out = {}
    for row in rows:
        label, *values = row
        if any(type(n) is not int or n < 0 for n in values):
            raise Hold("CARD_RESULT_TYPE_HOLD")
        counts = dict(zip(KEYS, values, strict=True))
        if (counts["total"] > (172 if label == "current" else 10000)
                or any(n > counts["total"] for n in values[1:])
                or counts["nonempty_char_array"] > counts["char_array"]
                or counts["story_type"] + counts["character_type"]
                + counts["absent_type"] > counts["total"]):
            raise Hold("CARD_RESULT_BOUNDS_HOLD")
        out[label] = counts
    return {
        "schema": SCHEMA,
        "status": "BASE336_V2_CARD_STRUCTURE_COVERAGE__SEMANTIC_HISTORY_HOLD",
        "frozen_cases": 336,
        "frozen_story_ids": 172,
        "card_contract_counts": out,
        "historical_actual_sent_prompt_verified": False,
        "story_version_at_target_verified": False,
        "semantic_world_alias_verified": False,
        "world_component_isolation_verified": False,
        "reviewer_independence_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "model_requests": 0,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "database_modified": False,
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
                return verify(cur.fetchall())
        finally:
            conn.rollback()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    try:
        stories = locator.scoped_stories(*prior._frozen(args))
        if not args.execute:
            safe = {
                "schema": SCHEMA, "status": "BASE336_V2_CARD_PRECHECK__NO_DB",
                "frozen_story_ids": len(stories),
                "database_accessed": False, "database_modified": False,
                "train_admitted": 0, "gpu_started": False,
                "private_values_emitted": False,
            }
        else:
            safe = query(stories, os.getenv("R60_READONLY_DATABASE_URL", ""))
            safe["database_accessed"] = True
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - private values never emitted
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE336_V2_CARD_CONTRACT_HOLD",
            "train_admitted": 0, "database_modified": False,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
