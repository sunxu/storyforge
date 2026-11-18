"""Owner-local source capture for P2 x all frozen Base336 stories.

Captures only World/Character/Opening fields from the 172 frozen Base336
stories (current + archived) and the exact approved public snapshots for the
8 P2 sources. Full values remain in a create-only 0600 Owner-private package.
Stdout contains bounded counts only. This is source evidence, NOT semantic
adjudication, actual-sent proof, Reviewer signoff, or admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import r60_base336_story_db_locator_cpu as locator
import r60_base336_p2_public_source_inventory_cpu as p2_inventory
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_p2_source_evidence_private_v1"
SAFE_SCHEMA = "storyforge_r60_base336_p2_source_evidence_safe_v1"
PRIVATE_FILENAME = "R60_BASE336_P2_SOURCE_EVIDENCE_PRIVATE.json"
P2_MANIFEST_SCHEMA = "storyforge_r60_base336_p2_public_source_inventory_private_v1"
P2_MANIFEST_STATUS = "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING"
FIELDS = ("world", "character", "characters", "opening")
MAX_MANIFEST_BYTES = 2_000_000
MAX_SOURCE_RECORDS = 10_000
MAX_FIELD_BYTES = 1_048_576
MAX_PACKAGE_BYTES = 100_000_000

SQL_BASE336 = """
WITH scope AS (SELECT unnest(%s::text[]) AS story_id)
SELECT
    'current'::text AS source_kind,
    s.id::text AS story_id,
    NULL::bigint AS revision_id,
    s.created_at::text AS source_time,
    s.v2_data->'world' AS world,
    s.v2_data->'character' AS character,
    s.v2_data->'characters' AS characters,
    s.v2_data->'opening' AS opening,
    md5((s.v2_data->'world')::text) AS world_json_md5
FROM scope i
JOIN public.user_stories s ON s.id::text = i.story_id
UNION ALL
SELECT
    'archived'::text,
    v.story_id::text,
    v.id::bigint,
    v.source_updated_at::text,
    v.v2_data->'world',
    v.v2_data->'character',
    v.v2_data->'characters',
    v.v2_data->'opening',
    md5((v.v2_data->'world')::text)
FROM scope i
JOIN public.story_content_versions v ON v.story_id::text = i.story_id
ORDER BY story_id, source_kind, revision_id NULLS FIRST
"""

SQL_P2 = """
WITH selected AS (
    SELECT *
    FROM unnest(%s::text[], %s::integer[], %s::text[], %s::text[])
         AS x(story_id, content_revision, submission_id, permission_event_id)
)
SELECT
    s.id::text,
    s.public_content_revision,
    s.public_content_hash,
    s.public_v2_data,
    sm.id::text,
    sm.content_revision,
    sm.content_hash,
    sm.snapshot->'source'->'v2Data' AS snapshot_v2_data,
    sm.requested_visibility,
    e.id::text,
    e.submission_id::text,
    e.to_visibility,
    e.kind,
    e.result,
    md5((s.public_v2_data->'world')::text) AS world_json_md5
FROM selected x
JOIN public.user_stories s
  ON s.id::text = x.story_id
JOIN public.story_moderation_submissions sm
  ON sm.id::text = x.submission_id
 AND sm.story_id::text = s.id::text
 AND sm.content_revision = x.content_revision
JOIN public.story_permission_events e
  ON e.id::text = x.permission_event_id
 AND e.story_id::text = s.id::text
 AND e.submission_id = sm.id
WHERE s.public_content_revision = x.content_revision
ORDER BY s.id
"""


class Hold(ValueError):
    pass


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if type(value) is str:
        return value
    raise Hold("TIMESTAMP_SHAPE_HOLD")


def _json_value(value: object) -> object:
    if value is None or type(value) in (str, dict, list, int, float, bool):
        return value
    raise Hold("JSON_FIELD_TYPE_HOLD")


def _json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise Hold("JSON_FIELD_SERIALIZE_HOLD") from None


def load_p2_manifest(path: Path) -> tuple[dict, bytes, list[dict]]:
    raw = private.read_private(path, MAX_MANIFEST_BYTES)
    try:
        doc = json.loads(raw)
    except (UnicodeError, ValueError):
        raise Hold("P2_MANIFEST_JSON_HOLD") from None
    if (type(doc) is not dict
            or doc.get("schema") != P2_MANIFEST_SCHEMA
            or doc.get("status") != P2_MANIFEST_STATUS
            or doc.get("rights_scope") != (
                "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
                "NO_TRAINING_OR_REDISTRIBUTION"
            )):
        raise Hold("P2_MANIFEST_CONTRACT_HOLD")
    selection = doc.get("selection")
    if (type(selection) is not dict
            or selection.get("selected_stories") != 8
            or selection.get("authors") != 5
            or selection.get("distinct_world_json") != 8
            or selection.get("created_before_gpu_run") != 3
            or selection.get("created_after_gpu_run") != 5
            or selection.get("private_session_bodies_read") is not False):
        raise Hold("P2_SELECTION_SCOPE_HOLD")
    sources = doc.get("sources")
    if type(sources) is not list or len(sources) != 8:
        raise Hold("P2_SOURCE_COUNT_HOLD")
    required = (
        "source_key", "story_id", "public_content_revision",
        "public_content_hash", "submission_snapshot_sha256",
        "world_json_md5", "moderation_submission_id", "permission_event_id",
        "permission_kind", "permission_result", "permission_submission_id",
        "permission_submission_bound", "permission_to_visibility",
        "snapshot_matches_current_public_v2",
        "snapshot_hash_matches_submission_sha256",
    )
    ids, keys = set(), set()
    for row in sources:
        if type(row) is not dict or any(k not in row for k in required):
            raise Hold("P2_SOURCE_FIELDS_HOLD")
        if (type(row["story_id"]) is not str or not row["story_id"]
                or type(row["source_key"]) is not str or not row["source_key"]
                or type(row["public_content_revision"]) is not int
                or row["public_content_revision"] < 0
                or type(row["moderation_submission_id"]) is not str
                or not row["moderation_submission_id"]
                or type(row["permission_event_id"]) is not str
                or not row["permission_event_id"]
                or row["permission_submission_bound"] is not True
                or row["permission_to_visibility"] != "public"
                or row["snapshot_matches_current_public_v2"] is not True
                or row["snapshot_hash_matches_submission_sha256"] is not True):
            raise Hold("P2_SOURCE_BINDING_FIELDS_HOLD")
        if row["story_id"] in ids or row["source_key"] in keys:
            raise Hold("P2_SOURCE_DUPLICATE_HOLD")
        if row["permission_kind"] not in {"ai", "update"}:
            raise Hold("P2_PERMISSION_KIND_HOLD")
        expected = "ai_approved" if row["permission_kind"] == "ai" else "approved"
        if row["permission_result"] != expected:
            raise Hold("P2_PERMISSION_RESULT_HOLD")
        if (type(row["world_json_md5"]) is not str or len(row["world_json_md5"]) != 32
                or any(c not in "0123456789abcdef" for c in row["world_json_md5"]):
            raise Hold("P2_WORLD_DIGEST_SHAPE_HOLD")
        if (type(row["submission_snapshot_sha256"]) is not str
                or len(row["submission_snapshot_sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in row["submission_snapshot_sha256"]):
            raise Hold("P2_SNAPSHOT_DIGEST_SHAPE_HOLD")
        ids.add(row["story_id"])
        keys.add(row["source_key"])
    return doc, raw, sources


def load_base336(args: argparse.Namespace) -> tuple[list[dict], list[str], bytes]:
    cases, crosswalk = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir, args.v3_dir, args.audit_dir
    )
    raw_audit = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT,
    )
    expected = quarantine.construct(cases, crosswalk, hashlib.sha256(raw_audit).hexdigest())
    raw_quarantine = private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT,
    )
    try:
        saved = json.loads(raw_quarantine)
    except (UnicodeError, ValueError):
        raise Hold("QUARANTINE_JSON_HOLD") from None
    if saved != expected:
        raise Hold("QUARANTINE_BINDING_HOLD")
    stories = locator.scoped_stories(cases, saved)
    if len(cases) != 1000 or len(stories) != 172:
        raise Hold("BASE336_SCOPE_HOLD")
    return cases, stories, raw_quarantine, saved


def validate_output_target(path: Path) -> None:
    if (not path.is_absolute() or path.parent != private.BASE
            or path.exists() or path.is_symlink()
            or private.BASE.is_symlink() or not private.BASE.is_dir()
            or stat.S_IMODE(private.BASE.stat().st_mode) != 0o700):
        raise Hold("OUTPUT_TARGET_HOLD")


def _base_records(rows: list[tuple], stories: list[str]) -> tuple[list[dict], dict]:
    if not 172 <= len(rows) <= MAX_SOURCE_RECORDS:
        raise Hold("BASE_SOURCE_RECORD_COUNT_HOLD")
    records = []
    current = set()
    seen_versions = set()
    coverage = {field: 0 for field in FIELDS}
    current_count = version_count = 0
    for row in rows:
        if not isinstance(row, tuple) or len(row) != 9:
            raise Hold("BASE_SOURCE_ROW_SHAPE_HOLD")
        kind, story, revision, source_time, *rest = row
        if kind not in {"current", "archived"} or type(story) is not str or story not in set(stories):
            raise Hold("BASE_SOURCE_IDENTITY_HOLD")
        if kind == "current":
            if revision is not None or story in current:
                raise Hold("BASE_CURRENT_DUPLICATE_HOLD")
            current.add(story)
            current_count += 1
        else:
            if type(revision) is not int or revision < 1 or (story, revision) in seen_versions:
                raise Hold("BASE_VERSION_IDENTITY_HOLD")
            seen_versions.add((story, revision))
            version_count += 1
        fields = {}
        for name, value in zip(FIELDS, rest[:4], strict=True):
            normalized = _json_value(value)
            if len(_json_bytes(normalized)) > MAX_FIELD_BYTES:
                raise Hold("BASE_FIELD_SIZE_HOLD")
            fields[name] = normalized
            coverage[name] += int(normalized is not None)
        world_md5 = rest[4]
        if world_md5 is not None and (
            type(world_md5) is not str or len(world_md5) != 32
        ):
            raise Hold("BASE_WORLD_DIGEST_SHAPE_HOLD")
        records.append({
            "source_kind": kind,
            "story_id_PRIVATE": story,
            "revision_id_PRIVATE": revision,
            "source_time_PRIVATE": _iso(source_time),
            "world_json_md5_PRIVATE": world_md5,
            "source_fields_PRIVATE": fields,
        })
    if current != set(stories):
        raise Hold("BASE_CURRENT_COVERAGE_HOLD")
    return records, {
        "current_rows": current_count,
        "archived_version_rows": version_count,
        "field_nonnull_counts": coverage,
    }


def _p2_records(rows: list[tuple], sources: list[dict]) -> tuple[list[dict], dict]:
    if len(rows) != 8:
        raise Hold("P2_DB_ROW_COUNT_HOLD")
    by_id = {row["story_id"]: row for row in sources}
    seen = set()
    records = []
    coverage = {field: 0 for field in FIELDS}
    for row in rows:
        if not isinstance(row, tuple) or len(row) != 15:
            raise Hold("P2_DB_ROW_SHAPE_HOLD")
        (story, revision, public_hash, current_v2, submission_id, submission_revision,
         submission_hash, snapshot_v2, requested_visibility, permission_id,
         permission_submission_id, permission_visibility, permission_kind,
         permission_result, world_md5) = row
        manifest = by_id.get(story)
        if manifest is None or story in seen:
            raise Hold("P2_DB_IDENTITY_HOLD")
        seen.add(story)
        current_v2 = _json_value(current_v2)
        snapshot_v2 = _json_value(snapshot_v2)
        if (type(current_v2) is not dict or type(snapshot_v2) is not dict
                or current_v2 != snapshot_v2):
            raise Hold("P2_SNAPSHOT_CURRENT_MISMATCH_HOLD")
        if (
            revision != manifest["public_content_revision"]
            or submission_revision != revision
            or public_hash != manifest["public_content_hash"]
            or submission_hash != manifest["submission_snapshot_sha256"]
            or submission_id != manifest["moderation_submission_id"]
            or permission_id != manifest["permission_event_id"]
            or permission_submission_id != submission_id
            or permission_submission_id != manifest["permission_submission_id"]
            or requested_visibility != "public"
            or permission_visibility != "public"
            or permission_kind != manifest["permission_kind"]
            or permission_result != manifest["permission_result"]
            or world_md5 != manifest["world_json_md5"]
        ):
            raise Hold("P2_REVISION_PERMISSION_BINDING_HOLD")
        fields = {}
        for name in FIELDS:
            value = _json_value(snapshot_v2.get(name))
            if len(_json_bytes(value)) > MAX_FIELD_BYTES:
                raise Hold("P2_FIELD_SIZE_HOLD")
            fields[name] = value
            coverage[name] += int(value is not None)
        records.append({
            "source_key_PRIVATE": manifest["source_key"],
            "story_id_PRIVATE": story,
            "public_content_revision_PRIVATE": revision,
            "submission_id_PRIVATE": submission_id,
            "permission_event_id_PRIVATE": permission_id,
            "submission_snapshot_sha256_PRIVATE": submission_hash,
            "world_json_md5_PRIVATE": world_md5,
            "source_fields_PRIVATE": fields,
        })
    if seen != set(by_id):
        raise Hold("P2_DB_COVERAGE_HOLD")
    return records, coverage


def exact_field_matches(p2_records: list[dict], base_records: list[dict]) -> tuple[dict, list[dict]]:
    counts = {field: {"p2_sources": 0, "base_story_ids": 0, "record_pairs": 0}
              for field in FIELDS}
    private_pairs = []
    for field in FIELDS:
        matched_p2, matched_stories, pair_keys = set(), set(), set()
        for p2 in p2_records:
            p2_value = p2["source_fields_PRIVATE"][field]
            if p2_value is None:
                continue
            for base in base_records:
                if base["source_fields_PRIVATE"][field] == p2_value:
                    key = (p2["story_id_PRIVATE"], base["story_id_PRIVATE"],
                           base["source_kind"], base["revision_id_PRIVATE"])
                    pair_keys.add(key)
                    matched_p2.add(p2["story_id_PRIVATE"])
                    matched_stories.add(base["story_id_PRIVATE"])
                    private_pairs.append({
                        "field_PRIVATE": field,
                        "p2_source_key_PRIVATE": p2["source_key_PRIVATE"],
                        "p2_story_id_PRIVATE": p2["story_id_PRIVATE"],
                        "base_story_id_PRIVATE": base["story_id_PRIVATE"],
                        "base_source_kind_PRIVATE": base["source_kind"],
                        "base_revision_id_PRIVATE": base["revision_id_PRIVATE"],
                    })
        counts[field] = {
            "p2_sources": len(matched_p2),
            "base_story_ids": len(matched_stories),
            "record_pairs": len(pair_keys),
        }
    return counts, private_pairs


def safe_summary(base_stats: dict, p2_coverage: dict, p2_records: list[dict],
                 base_p2_overlap: int,
                 exact_counts: dict, package_bytes: int) -> dict:
    return {
        "schema": SAFE_SCHEMA,
        "status": (
            "P2_BASE336_SOURCE_EVIDENCE_CAPTURED__EXACT_STORY_ID_OVERLAP_HOLD"
            if base_p2_overlap else
            "P2_BASE336_SOURCE_EVIDENCE_CAPTURED__SEMANTIC_REVIEW_REQUIRED"
        ),
        "base336_cases": 336,
        "base336_story_ids": 172,
        "base336_case_source_bindings": 336,
        "base336_current_rows": base_stats["current_rows"],
        "base336_archived_version_rows": base_stats["archived_version_rows"],
        "base336_field_nonnull_counts": base_stats["field_nonnull_counts"],
        "p2_sources": len(p2_records),
        "p2_snapshot_bindings": len(p2_records),
        "p2_permission_bindings": len(p2_records),
        "p2_field_nonnull_counts": p2_coverage,
        "p2_base336_exact_story_id_overlap": base_p2_overlap,
        "exact_field_match_counts": exact_counts,
        "private_package_bytes": package_bytes,
        "p2_manifest_binding_rows_verified": len(p2_records) == 8,
        "historical_actual_sent_verified": False,
        "semantic_world_alias_verified": False,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "reviewer_independence_verified": False,
        "train_admitted": 0,
        "database_accessed": True,
        "database_modified": False,
        "private_values_emitted": False,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "model_requests": 0,
        "model_promoted": False,
    }


def fetch(dsn: str, stories: list[str], sources: list[dict]) -> tuple[list[tuple], list[tuple]]:
    if not dsn:
        raise Hold("DB_DSN_HOLD")
    import psycopg

    with psycopg.connect(dsn, connect_timeout=10, autocommit=False) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout='60000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("""
                    SELECT current_user,current_setting('transaction_read_only'),
                           current_setting('row_security'),r.rolbypassrls,r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                """)
                private.assert_guard(cur.fetchone())
                cur.execute(p2_inventory.RLS_PREFLIGHT_SQL)
                p2_inventory.validate_rls_preflight(cur.fetchall())
                cur.execute(SQL_BASE336, (stories,))
                base_rows = cur.fetchall()
                cur.execute(
                    SQL_P2,
                    (
                        [s["story_id"] for s in sources],
                        [s["public_content_revision"] for s in sources],
                        [s["moderation_submission_id"] for s in sources],
                        [s["permission_event_id"] for s in sources],
                    ),
                )
                p2_rows = cur.fetchall()
                return base_rows, p2_rows
        finally:
            conn.rollback()


def _write_new(path: Path, data: bytes) -> None:
    if not 0 < len(data) <= MAX_PACKAGE_BYTES:
        raise Hold("PRIVATE_PACKAGE_SIZE_HOLD")
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise Hold("PRIVATE_OUTPUT_MODE_HOLD")


def run(args: argparse.Namespace) -> dict:
    _, p2_raw, p2_sources = load_p2_manifest(args.p2_manifest)
    cases, stories, quarantine_raw, saved = load_base336(args)
    validate_output_target(args.output_dir)
    overlap = len(set(stories) & {row["story_id"] for row in p2_sources})
    if not args.execute:
        return {
            "schema": SAFE_SCHEMA,
            "status": "P2_BASE336_SOURCE_EVIDENCE_PRECHECK__NO_DB",
            "base336_cases": 336,
            "base336_story_ids": 172,
            "p2_sources": 8,
            "p2_base336_exact_story_id_overlap": overlap,
            "database_accessed": False,
            "database_modified": False,
            "private_file_created": False,
            "private_values_emitted": False,
            "train_admitted": 0,
            "gpu_started": False,
            "hf_jobs_submitted": 0,
            "model_requests": 0,
        }
    base_rows, p2_rows = fetch(
        os.getenv("R60_READONLY_DATABASE_URL", ""), stories, p2_sources
    )
    base_records, base_stats = _base_records(base_rows, stories)
    p2_records, p2_coverage = _p2_records(p2_rows, p2_sources)
    exact_counts, exact_pairs = exact_field_matches(p2_records, base_records)
    case_bindings = []
    for entry in saved["remaining_full_r50_hold"]:
        position = entry.get("position")
        if type(position) is not int or not 1 <= position <= len(cases):
            raise Hold("BASE_CASE_SOURCE_BINDING_HOLD")
        case = cases[position - 1]
        source = case.get("source")
        required_source = ("story_id", "session_id", "assistant_message_id",
                           "prior_user_message_id", "previous_assistant_message_id",
                           "previous_user_message_id", "assistant_turn_index")
        if (type(source) is not dict or any(k not in source for k in required_source)
                or any(type(source[k]) is not str or not source[k]
                       for k in required_source[:-1])
                or type(source["assistant_turn_index"]) is not int
                or source["story_id"] not in set(stories)):
            raise Hold("BASE_CASE_SOURCE_BINDING_HOLD")
        case_bindings.append({
            "candidate_position_1based_PRIVATE": position,
            "story_id_PRIVATE": source["story_id"],
            "session_id_PRIVATE": source.get("session_id"),
            "assistant_message_id_PRIVATE": source.get("assistant_message_id"),
            "prior_user_message_id_PRIVATE": source.get("prior_user_message_id"),
            "previous_assistant_message_id_PRIVATE": source.get("previous_assistant_message_id"),
            "previous_user_message_id_PRIVATE": source.get("previous_user_message_id"),
            "assistant_turn_index_PRIVATE": source.get("assistant_turn_index"),
        })
    if len(case_bindings) != 336:
        raise Hold("BASE_CASE_SOURCE_BINDING_HOLD")
    package = {
        "schema": SCHEMA,
        "base336_scope": {
            "cases": 336,
            "story_ids_PRIVATE": stories,
            "candidate_source_bindings_PRIVATE": case_bindings,
            "quarantine_manifest_sha256_PRIVATE": hashlib.sha256(quarantine_raw).hexdigest(),
            "source_records_PRIVATE": base_records,
        },
        "p2_scope": {
            "manifest_sha256_PRIVATE": hashlib.sha256(p2_raw).hexdigest(),
            "source_records_PRIVATE": p2_records,
        },
        "exact_field_match_pairs_PRIVATE": exact_pairs,
        "non_actions": {
            "historical_actual_sent_verified": False,
            "semantic_world_alias_verified": False,
            "world_component_isolation_verified": False,
            "r50_complete_exclusion_verified": False,
            "reviewer_independence_verified": False,
            "train_admitted": 0,
            "model_requests": 0,
            "gpu_started": False,
            "hf_jobs_submitted": 0,
        },
    }
    package_raw = (json.dumps(
        package, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ) + "\n").encode("utf-8")
    if len(package_raw) > MAX_PACKAGE_BYTES:
        raise Hold("PRIVATE_PACKAGE_SIZE_HOLD")
    safe = safe_summary(
        base_stats, p2_coverage, p2_records,
        overlap, exact_counts, len(package_raw),
    )
    private.private_dir(args.output_dir, create=True)
    _write_new(args.output_dir / PRIVATE_FILENAME, package_raw)
    safe["private_file_created"] = True
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    parser.add_argument("--p2-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - private values and DB errors are suppressed
        known = {
            "P2_MANIFEST_JSON_HOLD", "P2_MANIFEST_CONTRACT_HOLD",
            "P2_SELECTION_SCOPE_HOLD", "P2_SOURCE_COUNT_HOLD", "P2_SOURCE_FIELDS_HOLD",
            "P2_SOURCE_BINDING_FIELDS_HOLD", "P2_SOURCE_DUPLICATE_HOLD",
            "P2_PERMISSION_KIND_HOLD", "P2_PERMISSION_RESULT_HOLD",
            "P2_WORLD_DIGEST_SHAPE_HOLD", "P2_SNAPSHOT_DIGEST_SHAPE_HOLD",
            "BASE336_SCOPE_HOLD", "BASE_CASE_SOURCE_BINDING_HOLD", "OUTPUT_TARGET_HOLD", "DB_DSN_HOLD",
            "BASE_SOURCE_RECORD_COUNT_HOLD", "BASE_SOURCE_ROW_SHAPE_HOLD",
            "BASE_SOURCE_IDENTITY_HOLD", "BASE_CURRENT_DUPLICATE_HOLD",
            "BASE_VERSION_IDENTITY_HOLD", "BASE_FIELD_SIZE_HOLD",
            "BASE_WORLD_DIGEST_SHAPE_HOLD", "BASE_CURRENT_COVERAGE_HOLD",
            "P2_DB_ROW_COUNT_HOLD", "P2_DB_ROW_SHAPE_HOLD",
            "P2_DB_IDENTITY_HOLD", "P2_SNAPSHOT_CURRENT_MISMATCH_HOLD",
            "P2_REVISION_PERMISSION_BINDING_HOLD", "P2_FIELD_SIZE_HOLD",
            "P2_DB_COVERAGE_HOLD", "PRIVATE_PACKAGE_SIZE_HOLD",
            "PRIVATE_OUTPUT_MODE_HOLD",
        }
        code = str(exc) if type(exc) is Hold and str(exc) in known else "SOURCE_CAPTURE_OR_RUNTIME_HOLD"
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "P2_BASE336_SOURCE_EVIDENCE_HOLD",
            "reason_code": code,
            "database_accessed": None if args.execute else False,
            "database_modified": False,
            "private_file_created": False,
            "private_values_emitted": False,
            "train_admitted": 0,
            "gpu_started": False,
            "hf_jobs_submitted": 0,
            "model_requests": 0,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
