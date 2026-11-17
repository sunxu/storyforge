"""Synthetic-only P2 public prompt package gate tests; no DB or model calls."""
import hashlib
import json

import pytest

from experiments.r58_quality import r60_base336_p2_public_prompt_package_gate as target


def package(tmp_path):
    sources = []
    for i in range(8):
        sources.append({
            "source_key": f"S{i}",
            "story_id": f"story-{i}",
            "public_content_revision": i,
            "submission_snapshot_sha256": f"{i:064x}",
            "world_json_md5": f"{i:032x}",
            "created_at_utc": (
                "2026-11-16T06:33:25.08Z" if i == 0 else
                "2026-11-16T14:56:46.188Z" if i == 1 else
                "2026-11-17T02:34:17.829Z" if i == 2 else
                "2026-11-17T10:05:16.221Z"
            ),
            "first_public_approved_at_utc": (
                "2026-11-16T07:43:27.101446Z" if i == 0 else
                "2026-11-16T14:57:34.942758Z" if i == 1 else
                "2026-11-17T02:34:51.477365Z" if i == 2 else
                "2026-11-17T10:06:00.809790Z"
            ),
            "moderation_submission_id": f"submission-{i}",
            "permission_event_id": f"event-{i}",
            "permission_kind": "ai",
            "permission_result": "ai_approved",
            "requested_visibility": "public",
            "permission_to_visibility": "public",
            "permission_submission_id": f"submission-{i}",
            "permission_submission_bound": True,
            "snapshot_matches_current_public_v2": True,
            "snapshot_hash_matches_submission_sha256": True,
        })
    rows = []
    for i, source in enumerate(sources):
        for dimension in target.EXPECTED_DIMENSIONS:
            rows.append({
                "sample_id": f"P2-{source['source_key']}-{dimension.upper()}",
                "source_key": source["source_key"],
                "source_story_id": source["story_id"],
                "source_revision": source["public_content_revision"],
                "source_snapshot_sha256": source["submission_snapshot_sha256"],
                "world_json_md5_nonsemantic": source["world_json_md5"],
                "quality_dimension": dimension,
                "messages": [
                    {"role": "user", "content": f"scene {i} {dimension}"},
                    {"role": "assistant", "content": "prior neutral action"},
                    {
                        "role": "user",
                        "content": "continue without deciding the player action",
                    },
                ],
            })
    raw = b"".join(
        (
            json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n"
        ).encode()
        for row in rows
    )
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_bytes(raw)
    manifest = {
        "schema": target.SCHEMA,
        "status": target.EXPECTED_STATUS,
        "source_selection": {
            "base336_release_cutoff_utc": "2026-11-16T02:03:25Z",
            "selected_stories": 8,
            "lineages": 8,
            "authors": 5,
            "distinct_world_json": 8,
            "created_before_gpu_run": 3,
            "created_after_gpu_run": 5,
            "private_session_bodies_read": False,
        },
        "sources": sources,
        "prompt_package": {
            "file": prompts.name,
            "records": 48,
            "records_per_source": 6,
            "dimensions": list(target.EXPECTED_DIMENSIONS),
            "messages_per_record": 3,
            "role_sequence": list(target.EXPECTED_ROLES),
            "contains_system_message": False,
            "contains_target_answer": False,
            "contains_reference_answer": False,
            "contains_private_session_text": False,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "gates": {
            "world_component_semantic_isolation_against_base336": (
                "HOLD_NOT_CROSSWALKED"
            ),
            "protected_r50_metadata_exclusion": (
                "HOLD_OWNER_PRIVATE_METADATA_NOT_AVAILABLE"
            ),
            "r47_r48_r55_exposure_exclusion": "HOLD_NOT_VERIFIED",
            "prompt_source_fidelity_review": "PENDING",
            "independent_reviewer_review": "PENDING",
            "author_platform_rights_scope": (
                "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
                "NO_TRAINING_OR_REDISTRIBUTION"
            ),
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
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return prompts, manifest_path, rows, manifest


def test_valid_draft_package_passes_structure_but_not_world_gate(tmp_path):
    prompts, manifest, _, _ = package(tmp_path)
    result = target.validate(prompts, manifest)
    assert result["status"] == "P2_PROMPT_PACKAGE_STRUCTURE_PASS__WORLD_CROSSWALK_HOLD"
    assert result["prompt_rows"] == 48
    assert result["source_stories"] == 8
    assert result["world_component_isolation_verified"] is False
    assert result["train_admitted"] == 0


def test_wrong_message_role_fails_closed(tmp_path):
    prompts, manifest, rows, m = package(tmp_path)
    rows[0]["messages"][1]["role"] = "system"
    raw = b"".join(
        (
            json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        for x in rows
    )
    prompts.write_bytes(raw)
    m["prompt_package"]["sha256"] = hashlib.sha256(raw).hexdigest()
    m["prompt_package"]["bytes"] = len(raw)
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="MESSAGE_CONTRACT_HOLD"):
        target.validate(prompts, manifest)


def test_digest_mismatch_fails_closed(tmp_path):
    prompts, manifest, _, m = package(tmp_path)
    m["prompt_package"]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="PROMPT_DIGEST_OR_CONTRACT_HOLD"):
        target.validate(prompts, manifest)


def test_missing_prompt_row_fails_closed(tmp_path):
    prompts, manifest, rows, m = package(tmp_path)
    raw = b"".join(
        (
            json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        for x in rows[:-1]
    )
    prompts.write_bytes(raw)
    m["prompt_package"]["sha256"] = hashlib.sha256(raw).hexdigest()
    m["prompt_package"]["bytes"] = len(raw)
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="PROMPT_ROW_COUNT_HOLD"):
        target.validate(prompts, manifest)


def test_source_binding_mismatch_fails_closed(tmp_path):
    prompts, manifest, rows, m = package(tmp_path)
    rows[0]["source_revision"] = 999
    raw = b"".join(
        (
            json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        for x in rows
    )
    prompts.write_bytes(raw)
    m["prompt_package"]["sha256"] = hashlib.sha256(raw).hexdigest()
    m["prompt_package"]["bytes"] = len(raw)
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="PROMPT_SOURCE_CROSSWALK_HOLD"):
        target.validate(prompts, manifest)


def test_r50_gate_cannot_be_promoted_by_prompt_structure(tmp_path):
    prompts, manifest, _, m = package(tmp_path)
    m["gates"]["protected_r50_metadata_exclusion"] = "PASS"
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="OPEN_GATE_STATUS_HOLD"):
        target.validate(prompts, manifest)


def test_nonpublic_permission_target_fails_closed(tmp_path):
    prompts, manifest, _, m = package(tmp_path)
    m["sources"][0]["permission_to_visibility"] = "private"
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="SOURCE_BINDING_HOLD"):
        target.validate(prompts, manifest)


def test_source_before_base336_cutoff_fails_closed(tmp_path):
    prompts, manifest, _, m = package(tmp_path)
    m["sources"][0]["created_at_utc"] = "2026-11-15T23:59:59Z"
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="SOURCE_BINDING_HOLD"):
        target.validate(prompts, manifest)


def test_permission_event_must_bind_latest_submission(tmp_path):
    prompts, manifest, _, m = package(tmp_path)
    m["sources"][0]["permission_submission_id"] = "older-submission"
    manifest.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(target.Hold, match="SOURCE_BINDING_HOLD"):
        target.validate(prompts, manifest)
