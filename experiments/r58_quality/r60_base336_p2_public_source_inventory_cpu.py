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
import hashlib
import json
import os
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

try:
    from . import r60_readonly_db as db
    from . import r60_real_private_batch as private
except ImportError:  # direct script execution from experiments/r58_quality
    import r60_readonly_db as db
    import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base336_p2_public_source_inventory_private_v1"
SAFE = "storyforge_r60_base336_p2_public_source_inventory_safe_v1"
FILENAME = "R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_PRIVATE.json"
BASE336_CUTOFF = "2026-11-16T02:03:25Z"
GPU_RUN_START = "2026-11-17T05:56:22Z"
EXPECTED_SELECTED = 8
EXPECTED_BEFORE_GPU = 3
EXPECTED_AFTER_GPU = 5
SOURCE_FIRST_SCHEMA = "storyforge_r60_base336_p2_public_source_inventory_private_v2"
SOURCE_FIRST_INPUT_SCHEMA = "storyforge_r60_p2_gold48_source_ids_private_v1"
SOURCE_FIRST_INPUT_STATUS = "GOLD48_COMPLETE_HISTORY_SOURCE_IDS__OWNER_FREEZE_PENDING"
SOURCE_FIRST_MODE = "gold48_historical_full_prefix_source_first_v1"
SOURCE_FIRST_BEFORE_GPU = 2
SOURCE_FIRST_AFTER_GPU = 6
SOURCE_FIRST_AUTHORS = 7
SOURCE_FIRST_CREATION_CUTOFF = "2026-11-19T15:30:00Z"


class Hold(ValueError):
    """Fixed, non-sensitive inventory failure."""


class BindingDiagnosticHold(Hold):
    """Aggregate-only source binding failure; never stores source values."""

    def __init__(self, failed_checks: dict[str, int], selected_rows: int):
        self.safe_diagnostics = {
            "schema": "storyforge_r60_p2_source_binding_diagnostic_v1",
            "selected_rows": selected_rows,
            "failed_checks": dict(sorted(failed_checks.items())),
            "private_values_emitted": False,
        }
        super().__init__("SOURCE_BINDING_HOLD")


class RlsPolicyHold(Hold):
    """Required reader RLS policies are absent or unusable."""

    def __init__(self, failed_tables: list[str]):
        self.safe_diagnostics = {
            "schema": "storyforge_r60_p2_reader_rls_preflight_v1",
            "reader_role": db.DEFAULT_READER_ROLE,
            "failed_tables": sorted(set(failed_tables)),
            "private_values_emitted": False,
        }
        super().__init__("SOURCE_METADATA_RLS_POLICY_HOLD")


RLS_PREFLIGHT_SQL = """
WITH required(table_name, policy_name) AS (
    VALUES
        (
            'story_moderation_submissions',
            'r58_export_reader_p2_current_public_submissions_select'
        ),
        (
            'story_permission_events',
            'r58_export_reader_p2_current_public_permission_events_select'
        )
)
SELECT
    required.table_name,
    c.relrowsecurity AS rls_enabled,
    has_table_privilege(current_user, c.oid, 'SELECT') AS select_granted,
    EXISTS (
        SELECT 1
        FROM pg_catalog.pg_policies p
        WHERE p.schemaname = 'public'
          AND p.tablename = required.table_name
          AND p.policyname = required.policy_name
          AND p.cmd IN ('SELECT', 'ALL')
          AND p.permissive = 'PERMISSIVE'
          AND 'r58_export_reader' = ANY(p.roles)
    ) AS policy_present
FROM required
JOIN pg_catalog.pg_class c ON c.relname = required.table_name
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
ORDER BY required.table_name;
"""

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
    JOIN selected s ON sm.story_id::text = s.story_id
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
    s.public_v2_data AS current_public_v2_data,
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
LEFT JOIN latest_submission ls ON ls.story_id::text = s.story_id
LEFT JOIN latest_permission lp ON lp.story_id = s.story_id
ORDER BY s.created_at, s.story_id;
"""


# Explicit source-first selection changes only the selected CTE. All public
# revision, moderation, permission and older-world joins are unchanged.
SQL_SOURCE_FIRST = (
    SQL[:SQL.index("selected AS (")]
    + "selected AS (\n    SELECT * FROM candidates WHERE story_id = ANY(%s::text[])\n),\n"
    + SQL[SQL.index("latest_submission AS ("):]
)


def _iso(value: object) -> datetime:
    try:
        return db.normalize_timestamp(value)
    except db.ReadOnlyDBHold as exc:
        raise Hold("SOURCE_TIMESTAMP_HOLD") from exc


def _sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _same_identifier(left: object, right: object) -> bool:
    """Compare DB identifiers across psycopg UUID and text representations."""
    if left is None or right is None:
        return False
    return str(left) == str(right)


def load_source_first_ids(path: Path) -> tuple[list[str], str]:
    """Read an explicit 0600 Owner-private eight-Story candidate list."""
    raw = private.read_private(path, 8_192)
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeError):
        raise Hold("SOURCE_FIRST_INPUT_JSON_HOLD") from None
    if (type(doc) is not dict
            or doc.get("schema") != SOURCE_FIRST_INPUT_SCHEMA
            or doc.get("status") != SOURCE_FIRST_INPUT_STATUS
            or doc.get("source_selection_mode") != SOURCE_FIRST_MODE):
        raise Hold("SOURCE_FIRST_INPUT_CONTRACT_HOLD")
    ids = doc.get("story_ids")
    if type(ids) is not list or len(ids) != EXPECTED_SELECTED:
        raise Hold("SOURCE_FIRST_INPUT_COUNT_HOLD")
    for value in ids:
        if type(value) is not str:
            raise Hold("SOURCE_FIRST_INPUT_IDENTIFIER_HOLD")
        try:
            if str(UUID(value)) != value:
                raise ValueError("noncanonical")
        except ValueError:
            raise Hold("SOURCE_FIRST_INPUT_IDENTIFIER_HOLD") from None
    if len(set(ids)) != EXPECTED_SELECTED:
        raise Hold("SOURCE_FIRST_INPUT_DUPLICATE_HOLD")
    return ids, hashlib.sha256(raw).hexdigest()


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


def validate_rls_preflight(rows: list[dict[str, Any]]) -> None:
    """Require the two reviewed, table-scoped reader SELECT policies."""
    expected = {
        "story_moderation_submissions",
        "story_permission_events",
    }
    observed: set[str] = set()
    failed: list[str] = []
    for row in rows:
        table = row.get("table_name")
        if table not in expected or table in observed:
            failed.append("preflight_result_shape")
            continue
        observed.add(table)
        if row.get("rls_enabled") is not True:
            failed.append(f"{table}:rls_not_enabled")
        if row.get("select_granted") is not True:
            failed.append(f"{table}:select_not_granted")
        if row.get("policy_present") is not True:
            failed.append(f"{table}:required_policy_missing")
    for table in sorted(expected - observed):
        failed.append(f"{table}:preflight_row_missing")
    if failed:
        raise RlsPolicyHold(failed)


def source_binding_diagnostics(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Return aggregate-only counts, separating invisible joins from bad bindings.

    Missing LEFT JOIN rows are reported once at the metadata boundary. Their
    dependent NULL columns are not misreported as independent data defects.
    """
    checks: dict[str, int] = {}

    def fail(code: str) -> None:
        checks[code] = checks.get(code, 0) + 1

    for row in rows:
        for field in ("story_id", "author_id"):
            try:
                row[field] = db.normalize_identifier(row.get(field), field=field)
            except db.ReadOnlyDBHold:
                fail(f"identifier_{field}_invalid")

        submission_visible = row.get("moderation_submission_id") is not None
        permission_visible = row.get("permission_event_id") is not None

        if not submission_visible:
            fail("moderation_submission_metadata_not_visible")
        else:
            try:
                row["moderation_submission_id"] = db.normalize_identifier(
                    row.get("moderation_submission_id"),
                    field="moderation_submission_id",
                )
            except db.ReadOnlyDBHold:
                fail("identifier_moderation_submission_id_invalid")
            if row.get("submission_revision") != row.get("public_content_revision"):
                fail("submission_revision_mismatch")
            if row.get("requested_visibility") != "public":
                fail("requested_visibility_not_public")
            if row.get("snapshot_v2_match") is False:
                fail("snapshot_v2_mismatch")

        if not permission_visible:
            fail("permission_event_metadata_not_visible")
        else:
            try:
                row["permission_event_id"] = db.normalize_identifier(
                    row.get("permission_event_id"),
                    field="permission_event_id",
                )
            except db.ReadOnlyDBHold:
                fail("identifier_permission_event_id_invalid")
            try:
                row["permission_submission_id"] = db.normalize_identifier(
                    row.get("permission_submission_id"),
                    field="permission_submission_id",
                )
            except db.ReadOnlyDBHold:
                fail("identifier_permission_submission_id_invalid")

            if row.get("permission_to_visibility", row.get("to_visibility")) != "public":
                fail("permission_visibility_not_public")
            if submission_visible:
                if not _same_identifier(
                    row.get("permission_submission_id"),
                    row.get("moderation_submission_id"),
                ):
                    fail("permission_submission_id_mismatch")
                if row.get("permission_submission_bound") is False:
                    fail("permission_submission_bound_false")

            kind = row.get("permission_kind")
            if kind not in {"ai", "update"}:
                fail("permission_kind_not_supported")
            elif kind == "ai" and row.get("permission_result") != "ai_approved":
                fail("ai_permission_result_not_approved")
            elif kind == "update" and row.get("permission_result") != "approved":
                fail("update_permission_result_not_approved")

        if row.get("exact_world_overlap_pre_cutoff") is True:
            fail("exact_world_overlap_pre_cutoff")

    return dict(sorted(checks.items()))


def validate_rows(rows: list[dict[str, Any]], *, source_first: bool = False) -> dict:
    if len(rows) != EXPECTED_SELECTED:
        raise Hold("SOURCE_COUNT_HOLD")
    failed_checks = source_binding_diagnostics(rows)
    if failed_checks:
        raise BindingDiagnosticHold(failed_checks, len(rows))

    stories = {row.get("story_id") for row in rows}
    authors = {row.get("author_id") for row in rows}
    worlds = {row.get("world_json_md5") for row in rows}
    if len(stories) != 8:
        raise Hold("SOURCE_STORY_ID_UNIQUENESS_HOLD")
    expected_authors = SOURCE_FIRST_AUTHORS if source_first else 5
    if len(authors) != expected_authors:
        raise Hold("SOURCE_AUTHOR_COUNT_HOLD")
    if len(worlds) != 8:
        raise Hold("SOURCE_WORLD_DEDUP_HOLD")

    cutoff = _iso(BASE336_CUTOFF)
    gpu = _iso(GPU_RUN_START)
    before = after = 0
    manifest_sources = []
    for row in rows:
        if not isinstance(row.get("current_public_v2_data"), dict):
            raise Hold("SOURCE_CURRENT_V2_DATA_HOLD")
        created = _iso(row.get("created_at"))
        approved = _iso(row.get("first_public_approved_at"))
        if (created < cutoff or approved < created or
                (source_first and created > _iso(SOURCE_FIRST_CREATION_CUTOFF))):
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
            or not _same_identifier(
                row.get("permission_submission_id"),
                row.get("moderation_submission_id"),
            )
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

    expected_times = ((SOURCE_FIRST_BEFORE_GPU, SOURCE_FIRST_AFTER_GPU)
                      if source_first else (EXPECTED_BEFORE_GPU, EXPECTED_AFTER_GPU))
    if (before, after) != expected_times:
        raise Hold("SOURCE_TIME_ACCOUNTING_HOLD")

    return {
        "schema": SOURCE_FIRST_SCHEMA if source_first else SCHEMA,
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
            **({"source_selection_mode": SOURCE_FIRST_MODE,
                "source_first_creation_cutoff_utc": SOURCE_FIRST_CREATION_CUTOFF,
                "owner_freeze": "PENDING"} if source_first else {}),
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


def _fetch(dsn: str, source_first_ids: list[str] | None = None) -> list[dict[str, Any]]:
    try:
        db_options = {
            "expected_role": db.DEFAULT_READER_ROLE,
            "connect_timeout": 10,
            "statement_timeout_ms": 30_000,
            "lock_timeout_ms": 1_000,
        }
        rls_rows = db.fetch_dict_rows(dsn, RLS_PREFLIGHT_SQL, **db_options)
        validate_rls_preflight(rls_rows)
        return db.fetch_dict_rows(
            dsn,
            SQL_SOURCE_FIRST if source_first_ids is not None else SQL,
            ((GPU_RUN_START, BASE336_CUTOFF, source_first_ids, BASE336_CUTOFF)
             if source_first_ids is not None else
             (GPU_RUN_START, BASE336_CUTOFF,
              GPU_RUN_START, EXPECTED_BEFORE_GPU,
              GPU_RUN_START, EXPECTED_AFTER_GPU,
              BASE336_CUTOFF)),
            **db_options,
        )
    except db.ReadOnlyDBHold as exc:
        raise Hold(str(exc)) from exc


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

    source_first_file = getattr(args, "source_first_ids_file", None)
    source_first_ids, source_first_hash = (None, None)
    if source_first_file is not None:
        source_first_ids, source_first_hash = load_source_first_ids(source_first_file)
    rows = _fetch(os.getenv("R60_READONLY_DATABASE_URL", ""), source_first_ids)
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
            and snapshot.get("source", {}).get("v2Data") == row.get("current_public_v2_data")
        )
        row["permission_submission_bound"] = _same_identifier(
            row.get("permission_submission_id"),
            row.get("moderation_submission_id"),
        )
        row["permission_to_visibility"] = row.get("to_visibility")
    selected = rows if source_first_ids is not None else select_rows(rows)
    if (source_first_ids is not None
            and {row["story_id"] for row in selected} != set(source_first_ids)):
        raise Hold("SOURCE_FIRST_DB_COVERAGE_HOLD")
    doc = validate_rows(selected, source_first=source_first_ids is not None)
    if source_first_ids is not None:
        doc["selection"]["private_selected_ids_file_sha256"] = source_first_hash
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
        "authors": len({row["author_id"] for row in selected}),
        "distinct_world_json": len({row["world_json_md5"] for row in selected}),
        "created_before_gpu_run": doc["selection"]["created_before_gpu_run"],
        "created_after_gpu_run": doc["selection"]["created_after_gpu_run"],
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
    parser.add_argument("--source-first-ids-file", type=Path, default=None,
                        help="Optional 0600 Owner-private Gold48 eight-Story ID list")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001
        is_hold = isinstance(exc, Hold)
        reason = str(exc) if is_hold else "P2_PUBLIC_SOURCE_INVENTORY_RUNTIME_HOLD"
        payload = {
            "schema": SAFE,
            "status": "P2_PUBLIC_SOURCE_INVENTORY_HOLD",
            "reason_code": reason if reason.endswith("_HOLD") else "P2_PUBLIC_SOURCE_INVENTORY_RUNTIME_HOLD",
            "database_modified": False,
            "gpu_started": False,
            "train_admitted": 0,
            "quality_v1_admitted": 0,
            "model_promoted": False,
            "private_values_emitted": False,
        }
        if isinstance(exc, BindingDiagnosticHold):
            payload["binding_diagnostics"] = exc.safe_diagnostics
        if isinstance(exc, RlsPolicyHold):
            payload["rls_diagnostics"] = exc.safe_diagnostics
        if not is_hold:
            payload["runtime_error_type"] = type(exc).__name__
            payload["runtime_error_message"] = str(exc)
            payload["runtime_error_repr"] = repr(exc)
            sqlstate = getattr(exc, "sqlstate", None)
            if isinstance(sqlstate, str) and len(sqlstate) == 5:
                payload["runtime_error_sqlstate"] = sqlstate
            diag = getattr(exc, "diag", None)
            if diag is not None:
                for key in (
                    "severity",
                    "severity_nonlocalized",
                    "message_primary",
                    "message_detail",
                    "message_hint",
                    "context",
                    "schema_name",
                    "table_name",
                    "column_name",
                    "datatype_name",
                    "constraint_name",
                ):
                    value = getattr(diag, key, None)
                    if value:
                        payload[f"runtime_error_{key}"] = str(value)
            import traceback
            print("=== P2 runtime exception detail ===", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("=== P2 runtime exception detail end ===", file=sys.stderr)
        print(json.dumps(payload, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
