"""Owner-scoped aggregate-only DB metadata locator for frozen 336/172.

No story text/card/system fields are selected or exported. No broad source
scan. Database read requires --execute, exact R58 read-only role and RLS.
This is current DB metadata coverage, not historical actual-sent snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_story_db_locator_safe_v1"

SQL_STORIES = """
WITH scope AS (SELECT unnest(%s::text[]) AS story_id)
SELECT
 count(*)::integer,
 count(*) FILTER (WHERE s.world_setting IS NOT NULL)::integer,
 count(*) FILTER (WHERE s.initial_system_prompt IS NOT NULL)::integer,
 count(*) FILTER (WHERE s.characters IS NOT NULL)::integer,
 count(*) FILTER (WHERE s.v2_data IS NOT NULL)::integer,
 count(*) FILTER (WHERE s.deleted_at IS NOT NULL)::integer
FROM scope i JOIN public.user_stories s ON s.id = i.story_id
"""

SQL_VERSIONS = """
WITH scope AS (SELECT unnest(%s::text[]) AS story_id)
SELECT count(DISTINCT v.story_id)::integer, count(*)::integer,
       count(*) FILTER (WHERE v.v2_data IS NOT NULL)::integer,
       count(*) FILTER (WHERE v.source_updated_at IS NOT NULL)::integer
FROM scope i JOIN public.story_content_versions v ON v.story_id = i.story_id
"""


class Hold(ValueError):
    pass


def scoped_stories(cases: list[dict], manifest: dict) -> list[str]:
    if (len(cases) != 1000 or manifest.get("schema") != quarantine.SCHEMA
            or manifest.get("status") != "R50_KNOWN5_QUARANTINE__FULL_R50_HOLD"
            or manifest.get("r50_complete_exclusion_verified") is not False
            or manifest.get("train_admitted") != 0
            or len(manifest.get("excluded_known5", [])) != 3
            or len(manifest.get("remaining_full_r50_hold", [])) != 336):
        raise Hold("SCOPE_HOLD")
    positions = set()
    stories = set()
    for item in manifest["remaining_full_r50_hold"]:
        position = item.get("position")
        if (type(position) is not int or not 1 <= position <= 1000
                or position in positions or item.get("status") !=
                "PARTIAL_KNOWN5_CLEAR__FULL_R50_HOLD"):
            raise Hold("HELD_POSITION_HOLD")
        positions.add(position)
        story = cases[position - 1].get("source", {}).get("story_id")
        if type(story) is not str or not story or len(story) > 256:
            raise Hold("STORY_ID_HOLD")
        if story in quarantine.known.KNOWN_R50_STORIES:
            raise Hold("R50_KNOWN5_LEAK_HOLD")
        stories.add(story)
    if len(positions) != 336 or len(stories) != 172:
        raise Hold("EXPECTED_336_172_HOLD")
    return sorted(stories)


def aggregate(stories: list[str], story_row: tuple, version_row: tuple) -> dict:
    if (len(stories) != 172 or len(story_row) != 6
            or len(version_row) != 4
            or any(type(v) is not int or v < 0 for v in (*story_row, *version_row))):
        raise Hold("RESULT_SHAPE_HOLD")
    found, world, system, cards, v2, deleted = story_row
    distinct, versions, version_v2, source_times = version_row
    if not (0 <= found <= 172 and
            max(world, system, cards, v2, deleted) <= found and
            0 <= distinct <= 172 and distinct <= versions and
            max(version_v2, source_times) <= versions):
        raise Hold("RESULT_BOUNDS_HOLD")
    return {
        "schema": SCHEMA,
        "status": "BASE336_SCOPED_STORY_DB_METADATA_COUNTS__HISTORICAL_HOLD",
        "frozen_cases": 336,
        "frozen_distinct_story_ids": 172,
        "current_user_stories_matching_ids": found,
        "current_world_setting_nonnull_stories": world,
        "current_initial_system_prompt_nonnull_stories": system,
        "current_characters_nonnull_stories": cards,
        "current_v2_data_nonnull_stories": v2,
        "current_deleted_stories": deleted,
        "versioned_story_ids_found": distinct,
        "story_content_versions_count": versions,
        "versions_with_v2_data": version_v2,
        "versions_with_source_updated_at": source_times,
        "historical_actual_sent_snapshot_verified": False,
        "historical_story_version_at_target_verified": False,
        "semantic_world_alias_complete": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "model_requests": 0,
        "database_modified": False,
        "private_values_emitted": False,
    }


def fetch(dsn: str, stories: list[str]) -> dict:
    import psycopg

    if not dsn:
        raise Hold("DSN_NOT_SET_HOLD")
    with psycopg.connect(dsn, connect_timeout=10, autocommit=False) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout='15000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("""
                    SELECT current_user, current_setting('transaction_read_only'),
                           current_setting('row_security'), r.rolbypassrls, r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname = current_user
                """)
                private.assert_guard(cur.fetchone())
                cur.execute(SQL_STORIES, (stories,))
                story_row = cur.fetchone()
                cur.execute(SQL_VERSIONS, (stories,))
                version_row = cur.fetchone()
                return aggregate(stories, story_row, version_row)
        finally:
            conn.rollback()


def run(args: argparse.Namespace) -> dict:
    cases, crosswalk = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir)
    raw = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    expected = quarantine.construct(
        cases, crosswalk, hashlib.sha256(raw).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if expected != saved:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    stories = scoped_stories(cases, saved)
    if not args.execute:
        return {
            "schema": SCHEMA,
            "status": "BASE336_SCOPED_STORY_DB_PRECHECK__NO_DB",
            "frozen_cases": 336,
            "frozen_distinct_story_ids": len(stories),
            "database_accessed": False,
            "database_modified": False,
            "train_admitted": 0,
            "gpu_started": False,
            "private_values_emitted": False,
        }
    result = fetch(os.getenv("R60_READONLY_DATABASE_URL", ""), stories)
    result["database_accessed"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        out = run(args)
        print(json.dumps(out, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - private IDs and DB diagnostics suppressed
        print(json.dumps({
            "schema": SCHEMA, "status": "BASE336_SCOPED_STORY_DB_LOCATOR_HOLD",
            "reason_code": "SOURCE_SCOPE_DB_ROLE_OR_RUNTIME_HOLD",
            "database_modified": False, "train_admitted": 0,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
