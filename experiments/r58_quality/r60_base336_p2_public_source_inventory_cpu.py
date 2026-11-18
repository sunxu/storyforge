"""Owner-local, read-only inventory for the R60 Base336 P2 Supabase source set.

The selector is deterministic: public original story sources after the Base336
release cutoff, with 3 selected before the Base336 GPU run and 5 after it,
ordered by creation time. It reads only public story data plus moderation /
permission metadata; it never reads private chat/session tables.

This creates a private source manifest only. The query is bounded to the P2 public-source
candidate window; it does not perform a full database export. It does not construct prompts,
change Supabase, prove semantic isolation against private Base336/R50/R47/R48/R55
sets, or authorize training/model inference.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from . import r60_real_private_batch as private
except ImportError:  # direct script execution from experiments/r58_quality
    import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_p2_public_source_inventory_private_v1"
SAFE = "storyforge_r60_base336_p2_public_source_inventory_safe_v1"
FILENAME = "R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json"
BASE336_CUTOFF = "2026-11-16T02:03:25Z"
GPU_RUN_START = "2026-11-17T05:56:22Z"
EXPECTED_SELECTED = 8
EXPECTED_BEFORE_GPU = 3
EXPECTED_AFTER_GPU = 5


class Hold(ValueError):
    """Fixed, non-sensitive inventory failure."""


SQL = """
WITH candidates AS (
    SELECT
        us.id AS story_id,
        us.author_id,
        us.created_at,
        us.first_public_approved_at,
        us.public_updated_at,
        us.public_content_revision,
        us.public_content_hash,
        us.public_v2_data,
        row_number() OVER (
            PARTITION BY (us.created_at < %s::timestamptz)
            ORDER BY us.created_at, us.id
        ) AS time_rank
    FROM public.user_stories us
    WHERE us.visibility = 'public'
      AND us.status = 'published'
      AND us.deleted_at IS NULL
      AND us.moderation_state IN ('ai_approved', 'human_approved')
      AND us.source_type = 'original'
      AND us.created_at >= %s::timestamptz
      AND us.public_v2_data->>'cardType' = 'story'
      AND us.public_v2_data->'opening'->>'originality' = 'original'
      AND us.public_v2_data->'opening'->>'visibility' = '公开'
      AND length(us.public_v2_data->'world'->>'worldSentence') > 5
),
selected AS (
    SELECT * FROM candidates
    WHERE (
        created_at < %s::timestamptz
        AND time_rank <= %s
    ) OR (
        created_at >= %s::timestamptz
        AND time_rank <= %s
    )
),
latest_submission AS (
    SELECT DISTINCT ON (sm.story_id)
        sm.story_id,
        sm.id AS moderation_submission_id,
        sm.content_revision,
        sm.content_hash,
        sm.snapshot,
        sm.requested_visibility
    FROM public.story_moderation_submissions sm
    JOIN selected s ON s.story_id = sm.story_id::text
    ORDER BY sm.story_id, sm.submission_sequence DESC, sm.created_at DESC
),
latest_permission AS (
    SELECT DISTINCT ON (e.story_id)
        e.story_id,
        e.id AS permission_event_id,
        e.kind AS permission_kind,
        e.result AS permission_result,
        e.to_visibility,
        e.submission_id,
        e.occurred_at
    FROM public.story_permission_events e
    JOIN selected s ON s.story_id = e.story_id
    ORDER BY e.story_id, e.occurred_at DESC, e.id DESC
),
older_worlds AS (
    SELECT DISTINCT md5((us.public_v2_data->'world')::text) AS world_json_md5
    FROM public.user_stories us
    WHERE us.created_at < %s::timestamptz
      AND us.source_type = 'original'
      AND us.public_v2_data->'world' IS NOT NULL
)
SELECT
    s.story_id,
    s.author_id,
    s.created_at,
    s.first_public_approved_at,
    s.public_updated_at,
    s.public_content_revision,
    s.public_content_hash,
    md5((s.public_v2_data->'world')::text) AS world_json_md5,
    length(s.public_v2_data->'world'->>'worldSentence') AS world_sentence_length,
    s.time_rank,
    ls.moderation_submission_id,
    ls.content_revision AS submission_revision,
    ls.content_hash AS submission_content_hash,
    ls.snapshot,
    ls.requested_visibility,
    lp.permission_event_id,
    lp.permission_kind,
    lp.permission_result,
    lp.to_visibility,
    lp.submission_id AS permission_submission_id,
    lp.occurred_at AS permission_occurred_at,
    EXISTS (
        SELECT 1 FROM older_worlds ow
        WHERE ow.world_json_md5 = md5((s.public_v2_data->'world')::text)
    ) AS exact_world_overlap_pre_cutoff
FROM selected s
LEFT JOIN latest_submission ls ON ls.story_id = s.story_id::uuid
LEFT JOIN latest_permission lp ON lp.story_id = s.story_id
ORDER BY s.created_at, s.story_id;
"""


def _iso(value: object) -> datetime:
    if not isinstance(value, str):
        raise Hold("SOURCE_TIMESTAMP_HOLD")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise Hold("SOURCE_TIMESTAMP_HOLD") from exc
    if result.tzinfo is None:
        raise Hold("SOURCE_TIMESTAMP_HOLD")
    return result


def _sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def select_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the deterministic 3-before/5-after source set from safe rows."""
    if type(rows) is not list:
        raise Hold("SOURCE_QUERY_SHAPE_HOLD")
    cutoff = _iso(BASE336_CUTOFF)
    gpu = _iso(GPU_RUN_START)
    before = sorted(
        (row for row in rows if _iso(row["created_at"]) < gpu
         and _iso(row["created_at"]) >= cutoff),
        key=lambda row: (_iso(row["created_at"]), str(row["story_id"])),
    )
    after = sorted(
        (row for row in rows if _iso(row["created_at"]) >= gpu),
        key=lambda row: (_iso(row["created_at"]), str(row["story_id"])),
    )
    if len(before) < EXPECTED_BEFORE_GPU or len(after) < EXPECTED_AFTER_GPU:
        raise Hold("SOURCE_TIME_POOL_HOLD")
    return before[:EXPECTED_BEFORE_GPU] + after[:EXPECTED_AFTER_GPU]


def validate_rows(rows: list[dict[str, Any]]) -> dict:
    if len(rows) != EXPECTED_SELECTED:
        raise Hold("SOURCE_COUNT_HOLD")
    stories = {row.get("story_id") for row in rows}
    authors = {row.get("author_id") for row in rows}
    worlds = {row.get("world_json_md5") for row in rows}
    if len(stories) != 8:
        raise Hold("SOURCE_STORY_ID_UNIQUENESS_HOLD")
    if len(authors) != 5:
        raise Hold("SOURCE_AUTHOR_COUNT_HOLD")
    if len(worlds) != 8:
        raise Hold("SOURCE_WORLD_DEDUP_HOLD")

    cutoff = _iso(BASE336_CUTOFF)
    gpu = _iso(GPU_RUN_START)
    before = after = 0
    manifest_sources = []
    for row in rows:
        created = _iso(row.get("created_at"))
        approved = _iso(row.get("first_public_approved_at"))
        if created < cutoff or approved < created:
            raise Hold("SOURCE_TIME_BINDING_HOLD")
        if created < gpu:
            before += 1
        else:
            after += 1

        if (
            type(row.get("story_id")) is not str
            or not row["story_id"]
            or type(row.get("author_id")) is not str
            or not row["author_id"]
            or type(row.get("public_content_revision")) is not int
            or row["public_content_revision"] < 0
            or not _sha256(row.get("submission_content_hash"))
            or type(row.get("world_json_md5")) is not str
            or len(row["world_json_md5"]) != 32
            or any(ch not in "0123456789abcdef" for ch in row["world_json_md5"])
            or row.get("world_sentence_length", 0) <= 5
            or type(row.get("moderation_submission_id")) is not str
            or not row["moderation_submission_id"]
            or type(row.get("permission_event_id")) is not str
            or not row["permission_event_id"]
            or row.get("submission_revision") != row["public_content_revision"]
            or row.get("requested_visibility") != "public"
            or row.get("permission_to_visibility", row.get("to_visibility"))
            != "public"
            or row.get("permission_submission_id")
            != row.get("moderation_submission_id")
            or row.get("permission_submission_bound") is False
            or row.get("permission_kind") not in {"ai", "update"}
            or (
                row.get("permission_kind") == "ai"
                and row.get("permission_result") != "ai_approved"
            )
            or (
                row.get("permission_kind") == "update"
                and row.get("permission_result") != "approved"
            )
            or row.get("snapshot_v2_match") is False
            or row.get("exact_world_overlap_pre_cutoff") is True
        ):
            raise Hold("SOURCE_BINDING_HOLD")

        manifest_sources.append({
            "source_key": f"S{len(manifest_sources) + 1:02d}",
            "story_id": row["story_id"],
            "public_content_revision": row["public_content_revision"],
            "public_content_hash": row.get("public_content_hash"),
            "created_at_utc": created.isoformat().replace("+00:00", "Z"),
            "first_public_approved_at_utc": approved.isoformat().replace("+00:00", "Z"),
            "public_updated_at_utc": (
                _iso(row["public_updated_at"]).isoformat().replace("+00:00", "Z")
                if row.get("public_updated_at") else None
            ),
            "submission_snapshot_sha256": row["submission_content_hash"],
            "world_json_md5": row["world_json_md5"],
            "world_json_md5_scope": "public_v2_data.world_exact_json_text",
            "moderation_submission_id": row["moderation_submission_id"],
            "permission_event_id": row["permission_event_id"],
            "permission_kind": row["permission_kind"],
            "permission_result": row["permission_result"],
            "permission_submission_id": row["permission_submission_id"],
            "permission_submission_bound": True,
            "permission_to_visibility": "public",
            "snapshot_matches_current_public_v2": True,
            "snapshot_hash_matches_submission_sha256": True,
        })

    if (before, after) != (EXPECTED_BEFORE_GPU, EXPECTED_AFTER_GPU):
        raise Hold("SOURCE_TIME_ACCOUNTING_HOLD")

    return {
        "schema": SCHEMA,
        "status": "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING",
        "selection": {
            "base336_release_cutoff_utc": BASE336_CUTOFF,
            "gpu_run_start_utc": GPU_RUN_START,
            "selected_stories": EXPECTED_SELECTED,
            "authors": len(authors),
            "distinct_world_json": len(worlds),
            "created_before_gpu_run": before,
            "created_after_gpu_run": after,
            "private_session_bodies_read": False,
        },
        "rights_scope": (
            "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
            "NO_TRAINING_OR_REDISTRIBUTION"
        ),
        "sources": manifest_sources,
        "gates": {
            "base336_private_source_crosswalk": "HOLD_OWNER_PRIVATE_METADATA_REQUIRED",
            "r50_metadata_exclusion": "HOLD_OWNER_PRIVATE_METADATA_REQUIRED",
            "r47_r48_r55_exposure_exclusion": "HOLD_OWNER_PRIVATE_METADATA_REQUIRED",
            "semantic_world_isolation": "HOLD",
            "prompt_source_fidelity_review": "PENDING",
            "independent_reviewer_review": "PENDING",
            "owner_freeze": "PENDING",
        },
        "non_actions": {
            "supabase_modified": False,
            "gpu_started": False,
            "hf_jobs_submitted": 0,
            "model_requests": 0,
            "train_admitted": 0,
            "quality_v1_admitted": 0,
            "model_promoted": False,
        },
    }


def _fetch(dsn: str) -> list[dict[str, Any]]:
    if not dsn:
        raise Hold("DB_DSN_NOT_SET_HOLD")
    import psycopg

    with psycopg.connect(dsn, connect_timeout=10, autocommit=False) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("SET LOCAL statement_timeout='30000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("""
                    SELECT current_user,current_setting('transaction_read_only'),
                           current_setting('row_security'),r.rolbypassrls,r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                """)
                guard = cur.fetchone()
                private.assert_guard(guard)
                cur.execute(
                    SQL,
                    (
                        GPU_RUN_START, BASE336_CUTOFF,
                        GPU_RUN_START, EXPECTED_BEFORE_GPU,
                        GPU_RUN_START, EXPECTED_AFTER_GPU,
                        BASE336_CUTOFF,
                    ),
                )
                columns = [desc[0] for desc in cur.description]
                raw_rows = [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]
                return raw_rows
        finally:
            conn.rollback()


def run(args: argparse.Namespace) -> dict:
    private.private_dir(args.output_dir, create=False)
    if args.output_dir.is_symlink() or stat.S_IMODE(args.output_dir.stat().st_mode) != 0o700:
        raise Hold("PRIVATE_DIR_PERMISSION_HOLD")
    output = args.output_dir / FILENAME
    if output.exists() or output.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    if not args.execute:
        return {
            "schema": SAFE,
            "status": "P2_PUBLIC_SOURCE_INVENTORY_PRECHECK__NO_DB",
            "database_accessed": False,
            "private_file_created": False,
            "train_admitted": 0,
            "gpu_started": False,
            "private_values_emitted": False,
        }

    rows = _fetch(os.getenv("R60_READONLY_DATABASE_URL", ""))
    # The query already binds the snapshot to current public_v2_data; normalize
    # the private-only booleans here so synthetic tests and DB rows share one gate.
    for row in rows:
        snapshot = row.get("snapshot")
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except (TypeError, ValueError):
                snapshot = None
        row["snapshot_v2_match"] = (
            isinstance(snapshot, dict)
            and snapshot.get("source", {}).get("v2Data") == row.get("public_v2_data")
        )
        row["permission_submission_bound"] = (
            row.get("permission_submission_id")
            == row.get("moderation_submission_id")
        )
        row["permission_to_visibility"] = row.get("to_visibility")
    selected = select_rows(rows)
    doc = validate_rows(selected)
    private.write_new(
        output,
        (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(),
    )
    if stat.S_IMODE(output.stat().st_mode) != 0o600:
        raise Hold("OUTPUT_PERMISSION_HOLD")
    doc["database_accessed"] = True
    doc["private_file_created"] = True
    return {
        "schema": SAFE,
        "status": "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING",
        "selected_stories": 8,
        "authors": 5,
        "distinct_world_json": 8,
        "created_before_gpu_run": 3,
        "created_after_gpu_run": 5,
        "revision_snapshot_permission_verified": True,
        "exact_world_overlap_pre_cutoff_public_original": 0,
        "rights_scope_owner_confirmed_only": True,
        "protected_crosswalk_verified": False,
        "database_accessed": True,
        "private_file_created": True,
        "database_modified": False,
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "model_requests": 0,
        "model_promoted": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        reason = str(exc) if isinstance(exc, Hold) else "P2_PUBLIC_SOURCE_INVENTORY_RUNTIME_HOLD"
        print(json.dumps({
            "schema": SAFE,
            "status": "P2_PUBLIC_SOURCE_INVENTORY_HOLD",
            "reason_code": reason if reason.endswith("_HOLD") else "P2_PUBLIC_SOURCE_INVENTORY_RUNTIME_HOLD",
            "database_modified": False,
            "gpu_started": False,
            "train_admitted": 0,
            "quality_v1_admitted": 0,
            "model_promoted": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
