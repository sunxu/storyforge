"""Bounded private character/opening evidence for all 8 world-crossing groups.

Use ONLY the 38 frozen scoped stories and roster-listed matched revisions.
Recheck group membership in one strictly read-only DB snapshot. Store exact
current/archived v2_data.character, characters and opening privately, not
world JSON, names or excerpts in stdout. No semantic verdict or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

import r60_base336_story_db_locator_cpu as locator
import r60_base336_story_json_shape_cpu as frozen
import r60_base336_world_cross_split_private_roster_cpu as roster
import r60_base336_world_group_source_evidence_cpu as world
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_card_opening_evidence_private_v1"
SAFE = "storyforge_r60_base336_card_opening_evidence_safe_v1"
OUTPUT_PREFIX = "R60_BASE336_WORLD_GROUP_"
MAX_FIELD_BYTES = 24000
MAX_GROUP_BYTES = 185000
MAX_RECORDS = 256
FIELDS = ("character", "characters", "opening")

SQL_CURRENT = """
SELECT v2_data->'character', v2_data->'characters', v2_data->'opening'
FROM public.user_stories WHERE id=%s
"""
SQL_VERSION = """
SELECT v2_data->'character', v2_data->'characters', v2_data->'opening'
FROM public.story_content_versions WHERE id=%s AND story_id=%s
"""


class Hold(ValueError):
    pass


# Only fixed, non-sensitive values may be emitted on a failed Owner-local run.
FAILURE_PHASES = frozenset({
    "ROSTER_TEMPLATE", "FROZEN_INPUT", "FROZEN_SCOPE",
    "OUTPUT_GUARD", "DB_CONNECT", "DB_GUARD", "DB_WORLD_AND_FIELDS",
    "PACKAGE_BUILD", "OUTPUT_WRITE",
})
KNOWN_HOLD_CODES = frozenset({
    "FIELD_TYPE_HOLD", "SOURCE_ROW_HOLD", "FIELD_TOO_LARGE_HOLD",
    "WORLD_GROUP_SNAPSHOT_DRIFT_HOLD", "RECORD_LIMIT_HOLD",
    "DSN_NOT_SET_HOLD", "DATABASE_GUARD_HOLD",
    "FROZEN_SCOPE_HOLD", "OUTPUT_DIR_GUARD_HOLD",
    "GROUPS_EXTRACTED_HOLD", "GROUP_ORDER_HOLD",
    "GROUP_TOO_LARGE_HOLD", "OUTPUT_PERMISSION_HOLD",
})


class DiagnosticHold(Hold):
    def __init__(self, phase: str, reason_code: str):
        if phase not in FAILURE_PHASES:
            phase = "PACKAGE_BUILD"
        if reason_code not in KNOWN_HOLD_CODES:
            reason_code = "UNEXPECTED_HOLD"
        self.failure_phase = phase
        self.reason_code = reason_code
        super().__init__(reason_code)


def diagnosed(phase: str, action):
    try:
        return action()
    except DiagnosticHold:
        raise
    except Exception as exc:  # noqa: BLE001 - redact untrusted DB/errors
        reason = str(exc) if type(exc) is Hold else "UNEXPECTED_HOLD"
        raise DiagnosticHold(phase, reason) from None


def normalized(value: object) -> object:
    if isinstance(value, str):
        # psycopg may return JSONB as decoded Python, including a genuine string.
        return value
    if value is None or isinstance(value, (dict, list, int, float, bool)):
        return value
    raise Hold("FIELD_TYPE_HOLD")


def source_fields(rows: list[tuple]) -> dict:
    if len(rows) != 1 or not isinstance(rows[0], tuple) or len(rows[0]) != 3:
        raise Hold("SOURCE_ROW_HOLD")
    result = {}
    for field, value in zip(FIELDS, rows[0], strict=True):
        obj = normalized(value)
        raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                         allow_nan=False).encode("utf-8")
        if len(raw) > MAX_FIELD_BYTES:
            raise Hold("FIELD_TOO_LARGE_HOLD")
        result[field + "_PRIVATE"] = obj
    return result


def build(cur, stories: list[str], groups: list[dict]) -> list[dict]:
    # DB state MUST agree with frozen roster before private text is selected.
    from r60_base336_world_exact_value_cpu import split_labels

    cur.execute(roster.SQL, (stories, split_labels(stories)))
    if world.normalize_db_rows(cur.fetchall()) != world.expected_rows(groups):
        raise Hold("WORLD_GROUP_SNAPSHOT_DRIFT_HOLD")
    result = []
    count = 0
    for group in groups:
        records = []
        for member in group["members_PRIVATE"]:
            story = member["story_id_PRIVATE"]
            if member["current_world_match"]:
                cur.execute(SQL_CURRENT, (story,))
                fields = source_fields(cur.fetchall())
                records.append({
                    "source_kind": "current", "story_id_PRIVATE": story,
                    "source_fields": fields,
                })
                count += 1
            for revision in member["archived_revision_ids_PRIVATE"]:
                cur.execute(SQL_VERSION, (revision, story))
                fields = source_fields(cur.fetchall())
                records.append({
                    "source_kind": "version", "story_id_PRIVATE": story,
                    "revision_id_PRIVATE": revision, "source_fields": fields,
                })
                count += 1
            if count > MAX_RECORDS:
                raise Hold("RECORD_LIMIT_HOLD")
        result.append({
            "group_ordinal": group["group_ordinal"],
            "current_world_cross_split": group["current_world_cross_split"],
            "matched_source_records_PRIVATE": records,
            "semantic_verdict": "UNREVIEWED_IN_THIS_EVIDENCE",
            "historical_actual_sent_verified": False,
        })
    return result


def capture(stories: list[str], groups: list[dict], dsn: str) -> list[dict]:
    if not dsn:
        raise Hold("DSN_NOT_SET_HOLD")
    import psycopg

    conn = diagnosed("DB_CONNECT", lambda: psycopg.connect(
        dsn, autocommit=False, connect_timeout=10,
    ))
    with conn:
        try:
            with conn.cursor() as cur:
                def guard() -> None:
                    cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    cur.execute("SET LOCAL row_security=on")
                    cur.execute("SET LOCAL statement_timeout='30000ms'")
                    cur.execute("SET LOCAL lock_timeout='1000ms'")
                    cur.execute("""
                        SELECT current_user,current_setting('transaction_read_only'),
                               current_setting('row_security'),r.rolbypassrls,r.rolsuper
                        FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                    """)
                    private.assert_guard(cur.fetchone())

                diagnosed("DB_GUARD", guard)
                return diagnosed(
                    "DB_WORLD_AND_FIELDS", lambda: build(cur, stories, groups),
                )
        finally:
            conn.rollback()


def _generate(args: argparse.Namespace, phase: list[str]) -> dict:
    phase[0] = "ROSTER_TEMPLATE"
    _, groups, _ = world.load(args.roster_dir)
    phase[0] = "FROZEN_INPUT"
    cases, manifest = frozen._frozen(args)
    phase[0] = "FROZEN_SCOPE"
    stories = locator.scoped_stories(cases, manifest)
    members = {m["story_id_PRIVATE"]
               for group in groups for m in group["members_PRIVATE"]}
    if len(members) != 38 or not members.issubset(set(stories)):
        raise Hold("FROZEN_SCOPE_HOLD")
    phase[0] = "OUTPUT_GUARD"
    private.private_dir(args.roster_dir, create=False)
    if args.output_dir.parent != private.BASE or args.output_dir.exists() or (
        args.output_dir.is_symlink()
    ):
        raise Hold("OUTPUT_DIR_GUARD_HOLD")
    if not args.execute:
        return {
            "schema": SAFE,
            "status": "BASE336_CARD_OPENING_EVIDENCE_PRECHECK__NO_DB",
            "groups": 8, "affected_story_ids": 38,
            "database_accessed": False, "private_files_created": False,
            "train_admitted": 0, "gpu_started": False,
            "database_modified": False, "private_values_emitted": False,
        }
    phase[0] = "DB_WORLD_AND_FIELDS"
    extracted = capture(stories, groups, os.getenv("R60_READONLY_DATABASE_URL", ""))
    phase[0] = "PACKAGE_BUILD"
    raw_roster = private.read_private(args.roster_dir / roster.FILENAME,
                                      5242880)
    source_digest = hashlib.sha256(raw_roster).hexdigest()
    packages = []
    if len(extracted) != 8:
        raise Hold("GROUPS_EXTRACTED_HOLD")
    for i, group in enumerate(extracted, 1):
        if group["group_ordinal"] != i:
            raise Hold("GROUP_ORDER_HOLD")
        item = {
            "schema": SCHEMA, "roster_sha256_PRIVATE": source_digest,
            "source_scope": "ROSTER_MATCHED_CURRENT_AND_ARCHIVED_ONLY",
            "train_admitted": 0, "historical_actual_sent_verified": False,
            "group_evidence_PRIVATE": group,
        }
        data = (json.dumps(item, ensure_ascii=False, sort_keys=True,
                           indent=2, allow_nan=False) + "\n").encode()
        if len(data) > MAX_GROUP_BYTES:
            raise Hold("GROUP_TOO_LARGE_HOLD")
        packages.append(data)
    # Validate all group lengths and source reads before creating the folder.
    phase[0] = "OUTPUT_WRITE"
    private.private_dir(args.output_dir, create=True)
    for i, data in enumerate(packages, 1):
        private.write_new(args.output_dir / f"{OUTPUT_PREFIX}{i:02d}_CARD_OPENING_PRIVATE.json", data)
    if (any(stat.S_IMODE(path.stat().st_mode) != 0o600
            for path in args.output_dir.iterdir())
            or len(list(args.output_dir.iterdir())) != 8):
        raise Hold("OUTPUT_PERMISSION_HOLD")
    kinds = Counter(
        rec["source_kind"] for g in extracted
        for rec in g["matched_source_records_PRIVATE"]
    )
    return {
        "schema": SAFE,
        "status": "BASE336_EIGHT_GROUP_CARD_OPENING_PRIVATE_READY__SEMANTIC_HOLD",
        "groups": 8,
        "affected_story_ids": 38, "affected_candidate_cases": 82,
        "source_records_current": kinds["current"],
        "source_records_archived": kinds["version"],
        "private_files_created": 8, "source_roster_bound": True,
        "historical_actual_sent_verified": False,
        "semantic_world_alias_verified": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0, "model_requests": 0,
        "gpu_started": False, "hf_jobs_submitted": 0,
        "database_accessed": True, "database_modified": False,
        "private_values_emitted": False,
    }


def generate(args: argparse.Namespace) -> dict:
    # Preserve the original call contract while keeping diagnostics finite.
    phase = ["ROSTER_TEMPLATE"]
    try:
        return _generate(args, phase)
    except DiagnosticHold:
        raise
    except Exception as exc:  # noqa: BLE001 - redact untrusted DB/errors
        reason = str(exc) if type(exc) is Hold else "UNEXPECTED_HOLD"
        raise DiagnosticHold(phase[0], reason) from None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        p.add_argument(f"--{name}-dir", type=Path, required=True)
    p.add_argument("--roster-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(generate(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never print private exceptions
        safe = {
            "schema": SAFE, "status": "BASE336_CARD_OPENING_EVIDENCE_HOLD",
            "failure_phase": (
                exc.failure_phase if isinstance(exc, DiagnosticHold)
                else "UNEXPECTED_HOLD"
            ),
            "reason_code": (
                exc.reason_code if isinstance(exc, DiagnosticHold)
                else "UNEXPECTED_HOLD"
            ),
            "database_accessed": None,  # An exception cannot prove access.
            "train_admitted": 0, "gpu_started": False,
            "database_modified": False, "private_values_emitted": False,
        }
        print(json.dumps(safe, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
