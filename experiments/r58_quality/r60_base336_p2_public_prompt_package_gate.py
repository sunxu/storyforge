"""Validate the draft-only R60 Base336 P2 public-story prompt package.

This is a local structural/integrity gate only. It cannot establish semantic
World isolation, R50 exclusion, rights, reviewer independence, or Owner freeze.
It never connects to Supabase, reads private chat bodies, calls a model, or
admits training/evaluation inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SCHEMA = "storyforge_r60_base336_p2_public_prompt_package_draft_v1"
SAFE_SCHEMA = "storyforge_r60_base336_p2_public_prompt_package_gate_safe_v1"
EXPECTED_STATUS = "DRAFT_ONLY__WORLD_COMPONENT_CROSSWALK_AND_OWNER_FREEZE_PENDING"
EXPECTED_DIMENSIONS = (
    "chinese_prose",
    "character_consistency",
    "npc_initiative",
    "player_agency",
    "rule_fidelity",
    "narrative_continuity",
)
EXPECTED_ROLES = ("user", "assistant", "user")
MAX_PROMPT_BYTES = 1_000_000
MAX_MANIFEST_BYTES = 100_000
MAX_MESSAGE_CHARS = 4_096
BASE336_CUTOFF = "2026-11-16T02:03:25Z"
GPU_RUN_START = "2026-11-17T05:56:22Z"
RECORD_KEYS = {
    "sample_id", "source_key", "source_story_id", "source_revision",
    "source_snapshot_sha256", "world_json_md5_nonsemantic",
    "quality_dimension", "messages",
}


class Hold(ValueError):
    """A fixed, non-sensitive validation failure."""


def _read_regular(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Hold("INPUT_FILE_TYPE_HOLD")
    if path.stat().st_size <= 0 or path.stat().st_size > maximum:
        raise Hold("INPUT_FILE_SIZE_HOLD")
    return path.read_bytes()


def _is_sha256(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def validate(prompt_path: Path, manifest_path: Path) -> dict:
    prompt_raw = _read_regular(prompt_path, MAX_PROMPT_BYTES)
    manifest_raw = _read_regular(manifest_path, MAX_MANIFEST_BYTES)
    try:
        manifest = json.loads(manifest_raw)
        rows = [json.loads(line) for line in prompt_raw.splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Hold("JSON_PARSE_HOLD") from exc

    if (type(manifest) is not dict
            or manifest.get("schema") != SCHEMA
            or manifest.get("status") != EXPECTED_STATUS):
        raise Hold("MANIFEST_CONTRACT_HOLD")

    package = manifest.get("prompt_package")
    if (type(package) is not dict
            or package.get("file") != prompt_path.name
            or package.get("records") != 48
            or package.get("records_per_source") != 6
            or package.get("dimensions") != list(EXPECTED_DIMENSIONS)
            or package.get("messages_per_record") != 3
            or package.get("role_sequence") != list(EXPECTED_ROLES)
            or package.get("contains_system_message") is not False
            or package.get("contains_target_answer") is not False
            or package.get("contains_reference_answer") is not False
            or package.get("contains_private_session_text") is not False
            or package.get("bytes") != len(prompt_raw)
            or package.get("sha256") != hashlib.sha256(prompt_raw).hexdigest()):
        raise Hold("PROMPT_DIGEST_OR_CONTRACT_HOLD")

    selection = manifest.get("source_selection")
    if (type(selection) is not dict
            or selection.get("base336_release_cutoff_utc") != BASE336_CUTOFF
            or selection.get("selected_stories") != 8
            or selection.get("lineages") != 8
            or selection.get("authors") != 5
            or selection.get("distinct_world_json") != 8
            or selection.get("created_before_gpu_run") != 3
            or selection.get("created_after_gpu_run") != 5
            or selection.get("private_session_bodies_read") is not False):
        raise Hold("SOURCE_SELECTION_CONTRACT_HOLD")

    sources = manifest.get("sources")
    if type(sources) is not list or len(sources) != 8:
        raise Hold("SOURCE_COUNT_HOLD")
    source_map: dict[str, dict] = {}
    source_ids: set[str] = set()
    before_gpu = 0
    after_gpu = 0
    cutoff = datetime.fromisoformat(BASE336_CUTOFF.replace("Z", "+00:00"))
    gpu_start = datetime.fromisoformat(GPU_RUN_START.replace("Z", "+00:00"))
    for source in sources:
        if type(source) is not dict:
            raise Hold("SOURCE_ROW_HOLD")
        key = source.get("source_key")
        story_id = source.get("story_id")
        revision = source.get("public_content_revision")
        try:
            created_at = datetime.fromisoformat(
                source.get("created_at_utc", "").replace("Z", "+00:00")
            )
            approved_at = datetime.fromisoformat(
                source.get("first_public_approved_at_utc", "").replace("Z", "+00:00")
            )
        except (AttributeError, ValueError) as exc:
            raise Hold("SOURCE_TIMESTAMP_HOLD") from exc
        if (type(key) is not str or not key or key in source_map
                or type(story_id) is not str or not story_id
                or story_id in source_ids
                or type(revision) is not int or revision < 0
                or created_at.tzinfo is None or approved_at.tzinfo is None
                or created_at < cutoff or approved_at < created_at
                or not _is_sha256(source.get("submission_snapshot_sha256"))
                or type(source.get("world_json_md5")) is not str
                or len(source.get("world_json_md5")) != 32
                or any(ch not in "0123456789abcdef" for ch in source.get("world_json_md5"))
                or source.get("requested_visibility") != "public"
                or source.get("permission_to_visibility") != "public"
                or type(source.get("moderation_submission_id")) is not str
                or not source.get("moderation_submission_id")
                or type(source.get("permission_event_id")) is not str
                or not source.get("permission_event_id")
                or source.get("permission_submission_id")
                != source.get("moderation_submission_id")
                or source.get("permission_submission_bound") is not True
                or source.get("permission_kind") not in {"ai", "update"}
                or (source.get("permission_kind") == "ai"
                    and source.get("permission_result") != "ai_approved")
                or (source.get("permission_kind") == "update"
                    and source.get("permission_result") != "approved")
                or source.get("snapshot_matches_current_public_v2") is not True
                or source.get("snapshot_hash_matches_submission_sha256") is not True):
            raise Hold("SOURCE_BINDING_HOLD")
        if created_at < gpu_start:
            before_gpu += 1
        else:
            after_gpu += 1
        source_map[key] = source
        source_ids.add(story_id)
    if before_gpu != 3 or after_gpu != 5:
        raise Hold("SOURCE_TIME_ACCOUNTING_HOLD")

    if len(rows) != 48:
        raise Hold("PROMPT_ROW_COUNT_HOLD")
    sample_ids: set[str] = set()
    per_source: Counter[str] = Counter()
    per_dimension: Counter[str] = Counter()
    for row in rows:
        if type(row) is not dict or set(row) != RECORD_KEYS:
            raise Hold("PROMPT_ROW_SCHEMA_HOLD")
        sid = row.get("sample_id")
        key = row.get("source_key")
        dim = row.get("quality_dimension")
        if (type(sid) is not str or not sid or sid in sample_ids
                or key not in source_map or dim not in EXPECTED_DIMENSIONS):
            raise Hold("PROMPT_IDENTITY_HOLD")
        source = source_map[key]
        if (row.get("source_story_id") != source["story_id"]
                or row.get("source_revision") != source["public_content_revision"]
                or row.get("source_snapshot_sha256") != source["submission_snapshot_sha256"]
                or row.get("world_json_md5_nonsemantic") != source["world_json_md5"]
                or sid != f"P2-{key}-{dim.upper()}"):
            raise Hold("PROMPT_SOURCE_CROSSWALK_HOLD")
        messages = row.get("messages")
        if type(messages) is not list or len(messages) != 3:
            raise Hold("MESSAGE_COUNT_HOLD")
        for message, role in zip(messages, EXPECTED_ROLES, strict=True):
            if (type(message) is not dict or set(message) != {"role", "content"}
                    or message.get("role") != role
                    or type(message.get("content")) is not str
                    or not message["content"].strip()
                    or len(message["content"]) > MAX_MESSAGE_CHARS):
                raise Hold("MESSAGE_CONTRACT_HOLD")
        sample_ids.add(sid)
        per_source[key] += 1
        per_dimension[dim] += 1

    if (set(per_source) != set(source_map)
            or any(per_source[key] != 6 for key in source_map)
            or set(per_dimension) != set(EXPECTED_DIMENSIONS)
            or any(per_dimension[dim] != 8 for dim in EXPECTED_DIMENSIONS)):
        raise Hold("PROMPT_BALANCE_HOLD")

    gates = manifest.get("gates")
    if (type(gates) is not dict
            or gates.get("world_component_semantic_isolation_against_base336")
            != "HOLD_NOT_CROSSWALKED"
            or gates.get("protected_r50_metadata_exclusion")
            != "HOLD_OWNER_PRIVATE_METADATA_NOT_AVAILABLE"
            or gates.get("r47_r48_r55_exposure_exclusion") != "HOLD_NOT_VERIFIED"
            or gates.get("prompt_source_fidelity_review") != "PENDING"
            or gates.get("independent_reviewer_review") != "PENDING"
            or gates.get("author_platform_rights_scope")
            != (
                "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
                "NO_TRAINING_OR_REDISTRIBUTION"
            )
            or gates.get("owner_freeze") != "PENDING"):
        raise Hold("OPEN_GATE_STATUS_HOLD")

    non_actions = manifest.get("non_actions")
    if (type(non_actions) is not dict
            or non_actions.get("supabase_modified") is not False
            or non_actions.get("gpu_started") is not False
            or non_actions.get("hf_jobs_submitted") != 0
            or non_actions.get("model_requests") != 0
            or non_actions.get("train_admitted") != 0
            or non_actions.get("quality_v1_admitted") != 0
            or non_actions.get("model_promoted") is not False):
        raise Hold("NON_ACTIONS_CONTRACT_HOLD")

    return {
        "schema": SAFE_SCHEMA,
        "status": "P2_PROMPT_PACKAGE_STRUCTURE_PASS__WORLD_CROSSWALK_HOLD",
        "prompt_rows": 48,
        "source_stories": 8,
        "rows_per_source": 6,
        "dimensions": len(EXPECTED_DIMENSIONS),
        "rows_per_dimension": 8,
        "message_count_per_prompt": 3,
        "prompt_sha256_verified": True,
        "source_revision_and_snapshot_bindings_verified": True,
        "world_component_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "r47_r48_r55_exposure_exclusion_verified": False,
        "rights_scope_owner_confirmed_only": True,
        "reviewer_independence_verified": False,
        "owner_freeze": False,
        "train_admitted": 0,
        "quality_v1_admitted": 0,
        "model_promoted": False,
        "database_modified": False,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "model_requests": 0,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.prompts, args.manifest)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no source values or local paths in SAFE
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "P2_PROMPT_PACKAGE_GATE_HOLD",
            "train_admitted": 0,
            "quality_v1_admitted": 0,
            "model_promoted": False,
            "database_modified": False,
            "gpu_started": False,
            "hf_jobs_submitted": 0,
            "model_requests": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
