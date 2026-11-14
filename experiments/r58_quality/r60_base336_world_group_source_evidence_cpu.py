"""Owner-private bounded world-source evidence for eight frozen cross-split groups.

Recheck every roster member and revision inside a single REPEATABLE READ READ
ONLY transaction before retrieving one exact world JSON per group. Never log
world text, character names, story IDs, hashes, DSN or DB exceptions. This is
source evidence for independent review, NOT a semantic decision or prompt replay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import r60_base336_story_db_locator_cpu as locator
import r60_base336_story_json_shape_cpu as frozen
import r60_base336_world_cross_split_private_roster_cpu as roster
import r60_base336_world_review_decisions_template_cpu as decisions
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_world_evidence_private_v1"
SAFE = "storyforge_r60_base336_world_evidence_safe_v1"
FILENAME = "R60_BASE336_EIGHT_WORLD_SOURCE_EVIDENCE_PRIVATE.json"
MAX_EVIDENCE_BYTES = 400_000
MAX_ONE_WORLD_BYTES = 32_000

SQL_CURRENT = """
SELECT v2_data->'world' FROM public.user_stories
WHERE id=%s AND jsonb_typeof(v2_data->'world')='object'
"""
SQL_VERSION = """
SELECT v2_data->'world' FROM public.story_content_versions
WHERE id=%s AND story_id=%s AND jsonb_typeof(v2_data->'world')='object'
"""


class Hold(ValueError):
    pass


def load(roster_dir: Path) -> tuple[dict, list[dict], bytes]:
    private.private_dir(roster_dir, create=False)
    source = private.read_private(roster_dir / roster.FILENAME, decisions.ROSTER_LIMIT)
    groups = decisions.validate(json.loads(source))
    template = private.read_private(roster_dir / decisions.FILENAME, 100_000)
    doc = json.loads(template)
    if (doc.get("schema") != decisions.SCHEMA or
            doc.get("roster_sha256_PRIVATE") != hashlib.sha256(source).hexdigest()
            or doc.get("train_admitted") != 0
            or doc.get("all_decisions_pending") is not True or
            [r.get("group_ordinal") for r in doc.get("group_reviews_PRIVATE", [])]
            != list(range(1, 9)) or
            any(r.get("decision") != "HOLD"
                for r in doc["group_reviews_PRIVATE"])):
        raise Hold("TEMPLATE_CONTRACT_HOLD")
    return json.loads(source), groups, template


def expected_rows(groups: list[dict]) -> list[tuple]:
    result = []
    for g in groups:
        for m in g["members_PRIVATE"]:
            result.append((
                g["group_ordinal"], m["story_id_PRIVATE"], m["split"],
                m["current_world_match"], tuple(m["archived_revision_ids_PRIVATE"]),
            ))
    return sorted(result)


def normalize_db_rows(rows: list[tuple]) -> list[tuple]:
    if not isinstance(rows, list):
        raise Hold("ROSTER_REPLAY_HOLD")
    out = []
    for row in rows:
        if not isinstance(row, tuple) or len(row) != 5:
            raise Hold("ROSTER_REPLAY_HOLD")
        no, story, split, current, revisions = row
        if (type(no) is not int or type(story) is not str
                or split not in {"train", "validation"}
                or type(current) is not bool or not isinstance(revisions, list)
                or any(type(v) is not int for v in revisions)):
            raise Hold("ROSTER_REPLAY_HOLD")
        out.append((no, story, split, current, tuple(revisions)))
    return sorted(out)


def source_member(group: dict) -> dict:
    members = group["members_PRIVATE"]
    matching = [m for m in members if m["current_world_match"]]
    return sorted(matching or members, key=lambda m: m["story_id_PRIVATE"])[0]


def collect(cur, stories: list[str], groups: list[dict]) -> list[dict]:
    from r60_base336_world_exact_value_cpu import split_labels

    cur.execute(roster.SQL, (stories, split_labels(stories)))
    if normalize_db_rows(cur.fetchall()) != expected_rows(groups):
        raise Hold("ROSTER_SNAPSHOT_DRIFT_HOLD")

    evidence = []
    for group in groups:
        member = source_member(group)
        is_current = member["current_world_match"]
        revisions = member["archived_revision_ids_PRIVATE"]
        if is_current:
            cur.execute(SQL_CURRENT, (member["story_id_PRIVATE"],))
            ref = {"source_kind": "current", "story_id_PRIVATE": member["story_id_PRIVATE"]}
        else:
            if not revisions:
                raise Hold("NO_VERSION_SOURCE_HOLD")
            cur.execute(SQL_VERSION, (revisions[0], member["story_id_PRIVATE"]))
            ref = {
                "source_kind": "version",
                "story_id_PRIVATE": member["story_id_PRIVATE"],
                "revision_id_PRIVATE": revisions[0],
            }
        rows = cur.fetchall()
        if len(rows) != 1:
            raise Hold("WORLD_SOURCE_COUNT_HOLD")
        value = rows[0][0]
        if isinstance(value, str):
            value = json.loads(value)
        if type(value) is not dict or not value:
            raise Hold("WORLD_SOURCE_TYPE_HOLD")
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        if len(encoded) > MAX_ONE_WORLD_BYTES:
            raise Hold("WORLD_SOURCE_SIZE_HOLD")
        evidence.append({
            "group_ordinal": group["group_ordinal"],
            "reference_PRIVATE": ref,
            "source_field": "v2_data.world",
            "world_value_PRIVATE": value,
            "current_world_cross_split": group["current_world_cross_split"],
            "review_decision": "HOLD",
        })
    return evidence


def fetch(stories: list[str], groups: list[dict], dsn: str) -> list[dict]:
    if not dsn:
        raise Hold("DSN_NOT_SET_HOLD")
    import psycopg

    with psycopg.connect(dsn, connect_timeout=10, autocommit=False) as db:
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
                private.assert_guard(cur.fetchone())
                return collect(cur, stories, groups)
        finally:
            db.rollback()


def run(args: argparse.Namespace) -> dict:
    _, groups, template = load(args.roster_dir)
    cases, manifest = frozen._frozen(args)
    stories = locator.scoped_stories(cases, manifest)
    scoped = {m["story_id_PRIVATE"]
              for g in groups for m in g["members_PRIVATE"]}
    if not scoped.issubset(set(stories)) or len(scoped) != 38:
        raise Hold("FROZEN_SCOPE_DRIFT_HOLD")
    output = args.roster_dir / FILENAME
    if output.exists() or output.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    if not args.execute:
        return {
            "schema": SAFE,
            "status": "BASE336_WORLD_EVIDENCE_PRECHECK__NO_DB",
            "groups": 8, "frozen_story_ids": 172,
            "source_content_read": False, "database_accessed": False,
            "file_created": False, "database_modified": False,
            "gpu_started": False, "train_admitted": 0,
            "private_values_emitted": False,
        }
    evidence = fetch(stories, groups, os.getenv("R60_READONLY_DATABASE_URL", ""))
    if len(evidence) != 8:
        raise Hold("EVIDENCE_GROUP_COUNT_HOLD")
    payload = {
        "schema": SCHEMA,
        "roster_sha256_PRIVATE": hashlib.sha256(
            private.read_private(args.roster_dir / roster.FILENAME,
                                 decisions.ROSTER_LIMIT)).hexdigest(),
        "template_sha256_PRIVATE": hashlib.sha256(template).hexdigest(),
        "actual_sent_prompt_verified": False,
        "semantic_review_completed": False,
        "all_decisions": "HOLD",
        "train_admitted": 0,
        "evidence_groups_PRIVATE": evidence,
    }
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise Hold("OUTPUT_TOO_LARGE_HOLD")
    private.write_new(output, raw)
    if stat.S_IMODE(output.stat().st_mode) != 0o600:
        raise Hold("OUTPUT_PERMISSION_HOLD")
    return {
        "schema": SAFE,
        "status": "BASE336_EIGHT_WORLD_SOURCE_EVIDENCE_PRIVATE_READY__REVIEW_HOLD",
        "groups": 8, "distinct_affected_stories": 38,
        "affected_cases": 82, "source_world_objects": 8,
        "roster_snapshot_reverified": True, "source_bound": True,
        "evidence_file_created": True, "database_accessed": True,
        "world_content_emitted_to_terminal": False,
        "historical_actual_sent_prompt_verified": False,
        "semantic_review_completed": False,
        "train_admitted": 0, "model_requests": 0, "gpu_started": False,
        "database_modified": False, "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", type=Path, required=True)
    p.add_argument("--roster-dir", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no user data, ids or DB exceptions in output
        print(json.dumps({
            "schema": SAFE,
            "status": "BASE336_EIGHT_WORLD_SOURCE_EVIDENCE_HOLD",
            "train_admitted": 0, "gpu_started": False,
            "database_modified": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
