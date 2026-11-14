"""Create-only Owner-private review roster for frozen R60 cross-split world reuse.

World JSONB never leaves PostgreSQL. Return only source IDs/version IDs for
the 8 crossing world-value groups, write to Owner-private 0600 file, and print
aggregate SAFE counts. This DOES NOT certify semantic identity or admit SFT.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from collections import defaultdict
from pathlib import Path

import r60_base336_story_db_locator_cpu as locator
import r60_base336_story_json_shape_cpu as prior
import r60_base336_world_exact_value_cpu as equality

SCHEMA = "storyforge_r60_base336_world_cross_split_review_private_v1"
SAFE_SCHEMA = "storyforge_r60_base336_world_cross_split_review_safe_v1"
FILENAME = "R60_BASE336_WORLD_CROSS_SPLIT_REVIEW_PRIVATE.json"
SQL = """
WITH scope AS (
 SELECT story_id, split
 FROM unnest(%s::text[], %s::text[]) AS x(story_id,split)
),
records AS (
 SELECT 'current'::text AS kind, s.id AS story_id,
        i.split, NULL::bigint AS revision_id, s.v2_data->'world' AS world
 FROM scope i JOIN public.user_stories s ON s.id=i.story_id
 UNION ALL
 SELECT 'version'::text, v.story_id, i.split,
        v.id AS revision_id, v.v2_data->'world' AS world
 FROM scope i JOIN public.story_content_versions v ON v.story_id=i.story_id
),
grouped AS (
 SELECT world
 FROM records
 WHERE jsonb_typeof(world)='object' AND world <> '{}'::jsonb
 GROUP BY world
 HAVING count(DISTINCT story_id) FILTER (WHERE split='train') > 0
    AND count(DISTINCT story_id) FILTER (WHERE split='validation') > 0
),
ranked AS (
 SELECT row_number() OVER (ORDER BY world)::int AS group_ordinal, world
 FROM grouped
)
SELECT g.group_ordinal, r.story_id, r.split,
       bool_or(r.kind='current') AS current_present,
       coalesce(array_agg(r.revision_id ORDER BY r.revision_id)
         FILTER (WHERE r.kind='version'), ARRAY[]::bigint[]) AS version_ids
FROM ranked g JOIN records r ON r.world=g.world
GROUP BY g.group_ordinal,r.story_id,r.split
ORDER BY g.group_ordinal,r.split,r.story_id
"""


class Hold(ValueError):
    pass


def compile_roster(
    rows: list[tuple], cases: list[dict], manifest: dict,
    stories: list[str],
) -> tuple[dict, dict]:
    if type(rows) is not list or not rows or len(rows) > 172 * 8:
        raise Hold("ROW_COUNT_HOLD")
    positions = defaultdict(list)
    for item in manifest["remaining_full_r50_hold"]:
        pos = item["position"]
        if type(pos) is not int or not 1 <= pos <= 1000:
            raise Hold("POSITION_HOLD")
        story = cases[pos - 1]["source"]["story_id"]
        positions[story].append(pos)
    if set(positions) != set(stories) or sum(map(len, positions.values())) != 336:
        raise Hold("SCOPE_HOLD")

    groups = defaultdict(list)
    seen_pairs = set()
    for row in rows:
        if type(row) is not tuple or len(row) != 5:
            raise Hold("ROW_SHAPE_HOLD")
        ordinal, story, split, current, versions = row
        if (type(ordinal) is not int or not 1 <= ordinal <= 8
                or type(story) is not str or story not in positions
                or split != equality.split_labels([*stories])[stories.index(story)]
                or type(current) is not bool or type(versions) is not list
                or not current and not versions
                or any(type(n) is not int or n < 1 for n in versions)
                or len(set(versions)) != len(versions)):
            raise Hold("ROW_IDENTITY_HOLD")
        if (ordinal, story) in seen_pairs:
            raise Hold("DUPLICATE_MEMBER_HOLD")
        seen_pairs.add((ordinal, story))
        groups[ordinal].append({
            "story_id_PRIVATE": story,
            "split": split,
            "candidate_positions_1based_PRIVATE": sorted(positions[story]),
            "current_world_match": current,
            "archived_revision_ids_PRIVATE": versions,
        })
    if set(groups) != set(range(1, 9)):
        raise Hold("CROSS_GROUP_COUNT_HOLD")
    affected = set()
    curr_cross_groups = 0
    review = []
    for no in sorted(groups):
        members = groups[no]
        splits = {m["split"] for m in members}
        if splits != {"train", "validation"}:
            raise Hold("CROSS_GROUP_MEMBER_HOLD")
        current_splits = {
            m["split"] for m in members if m["current_world_match"]
        }
        is_current_crossing = current_splits == {"train", "validation"}
        curr_cross_groups += is_current_crossing
        affected.update(m["story_id_PRIVATE"] for m in members)
        review.append({
            "group_ordinal": no,
            "current_world_cross_split": is_current_crossing,
            "members_PRIVATE": members,
            "semantic_verdict": "UNREVIEWED",
            "review_evidence_reference_PRIVATE": "",
            "review_notes_PRIVATE": "",
        })
    train_stories = sum(equality.split_labels(stories)[stories.index(story)] == "train"
                        for story in affected)
    val_stories = len(affected) - train_stories
    train_cases = sum(len(positions[s]) for s in affected
                      if equality.split_labels(stories)[stories.index(s)] == "train")
    val_cases = sum(len(positions[s]) for s in affected
                    if equality.split_labels(stories)[stories.index(s)] == "validation")
    if (curr_cross_groups, len(affected), train_stories, val_stories,
            train_cases, val_cases) != (7, 38, 28, 10, 65, 17):
        raise Hold("OWNER_SAFE_CROSSWALK_DRIFT_HOLD")

    private_payload = {
        "schema": SCHEMA,
        "scope": "FROZEN_336_CASES_172_STORIES__8_CROSSING_WORLD_JSON_VALUES",
        "source_kind": "CURRENT_AND_ARCHIVED_JSONB_EXACT_EQUALITY__NOT_SEMANTIC_IDENTITY",
        "actual_sent_version_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "semantic_review_completed": False,
        "train_admitted": 0,
        "groups_PRIVATE": review,
    }
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "BASE336_CROSS_SPLIT_EIGHT_GROUP_PRIVATE_REVIEW_READY__SEMANTIC_HOLD",
        "crossing_world_value_groups": len(groups),
        "current_only_crossing_groups": curr_cross_groups,
        "distinct_affected_stories": len(affected),
        "distinct_affected_train_stories": train_stories,
        "distinct_affected_validation_stories": val_stories,
        "affected_train_cases": train_cases,
        "affected_validation_cases": val_cases,
        "all_group_verdicts_unreviewed": True,
        "world_json_returned_from_db": False,
        "world_component_isolation_verified": False,
        "historical_actual_sent_version_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "model_requests": 0,
        "database_modified": False,
        "private_values_emitted": False,
    }
    return private_payload, safe


def fetch(stories: list[str], dsn: str) -> list[tuple]:
    if not dsn:
        raise Hold("DB_DSN_HOLD")
    import psycopg

    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as db:
        try:
            with db.cursor() as cur:
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
                cur.execute(SQL, (stories, equality.split_labels(stories)))
                return cur.fetchall()
        finally:
            db.rollback()


def execute(args: argparse.Namespace) -> dict:
    cases, manifest = prior._frozen(args)
    stories = locator.scoped_stories(cases, manifest)
    parent = args.private_output_dir.parent
    if (args.private_output_dir.is_symlink()
            or args.private_output_dir.exists()
            or parent != locator.private.BASE or parent.is_symlink()
            or not parent.is_dir() or
            stat.S_IMODE(parent.stat().st_mode) != 0o700):
        raise Hold("PRIVATE_DESTINATION_HOLD")
    if not args.execute:
        return {
            "schema": SAFE_SCHEMA,
            "status": "BASE336_WORLD_REVIEW_ROSTER_PRECHECK__NO_DB",
            "frozen_cases": 336, "frozen_story_ids": 172,
            "private_file_created": False,
            "train_admitted": 0, "database_accessed": False,
            "database_modified": False, "gpu_started": False,
            "private_values_emitted": False,
        }
    rows = fetch(stories, os.getenv("R60_READONLY_DATABASE_URL", ""))
    payload, safe = compile_roster(rows, cases, manifest, stories)
    raw = (json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
    locator.private.private_dir(args.private_output_dir, create=True)
    locator.private.write_new(args.private_output_dir / FILENAME, raw)
    safe["private_file_created"] = True
    safe["database_accessed"] = True
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        result = execute(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - never show private IDs or credentials
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "BASE336_WORLD_REVIEW_ROSTER_HOLD",
            "private_values_emitted": False, "train_admitted": 0,
            "gpu_started": False, "database_modified": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
