"""Synthetic-only checks for the scoped Gold48 capture thin adapter."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r60_p2_gold48_recovery_capture.py"
spec = importlib.util.spec_from_file_location("r60_p2_gold48_recovery_capture", SCRIPT)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def fixture_docs():
    ids = [f"story-{i:02d}" for i in range(8)]
    id_doc = {
        "schema": capture.IDS_SCHEMA,
        "status": "GOLD48_COMPLETE_HISTORY_SOURCE_IDS__OWNER_FREEZE_PENDING",
        "story_ids": ids,
    }
    sources = []
    bindings = []
    for i, story in enumerate(ids):
        key = f"S{i + 1:02d}"
        sources.append({
            "source_key": key, "story_id": story,
            "public_content_revision": 7,
            "created_at_utc": "2026-11-17T12:00:00Z",
            "first_public_approved_at_utc": "2026-11-17T12:01:00Z",
            "public_updated_at_utc": "2026-11-17T12:02:00Z",
            "permission_to_visibility": "public",
            "permission_submission_bound": True,
            "snapshot_matches_current_public_v2": True,
            "permission_kind": "ai",
            "permission_result": "ai_approved",
        })
        bindings.append({
            "reviewer_ref_PRIVATE": f"P{i + 1:02d}",
            "source_key_PRIVATE": key,
            "story_id_PRIVATE": story,
            "public_content_revision_PRIVATE": 7,
        })
    manifest = {
        "schema": "storyforge_r60_base336_p2_public_source_inventory_private_v2",
        "status": "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING",
        "sources": sources,
        "selection": {
            "created_before_gpu_run": 2, "created_after_gpu_run": 6,
            "authors": 7,
        },
    }
    return id_doc, manifest, {"bindings_PRIVATE": bindings}


def test_source_revision_and_flagged_identity_bind_by_content_not_order():
    ids, manifest, binding = fixture_docs()
    rows, flagged = capture.validate_sources(ids, manifest, binding)
    assert len(rows) == 8
    assert flagged == "story-03"


def test_unbound_reviewer_revision_fails_closed():
    ids, manifest, binding = fixture_docs()
    binding["bindings_PRIVATE"][3]["public_content_revision_PRIVATE"] += 1
    with pytest.raises(capture.Hold, match="REVIEWER_SOURCE_REVISION_HOLD"):
        capture.validate_sources(ids, manifest, binding)


def test_old_three_five_manifest_is_not_accepted():
    ids, manifest, binding = fixture_docs()
    manifest["selection"]["created_before_gpu_run"] = 3
    with pytest.raises(capture.Hold, match="SOURCE_COHORT_HOLD"):
        capture.validate_sources(ids, manifest, binding)


def test_history_edit_markers_are_rejected():
    assert capture.edited({"editedAt": "2026-11-19"}) is True
    assert capture.edited({"originalContent": "prior"}) is True
    assert capture.edited({"editedAt": None}) is False


def test_prompt_hash_depends_on_full_prefix_not_just_final_user():
    a = [{"role": "user", "content": "A"}, {"role": "assistant", "content": "B"},
         {"role": "user", "content": "same"}]
    b = [{"role": "user", "content": "different"}, {"role": "assistant", "content": "B"},
         {"role": "user", "content": "same"}]
    assert capture.digest(a) != capture.digest(b)


def test_generation_prefixes_never_contain_original_reference():
    sample = {
        "candidate_case_id_PRIVATE": "G48-C01",
        "story_id_PRIVATE": "story-private",
        "prefix_messages_PRIVATE": [{"role": "user", "content": "scene"}],
        "original_reply_PRIVATE": "withheld-reference",
        "history_recovery_PRIVATE": {"history": []},
        "prefix_sha256_PRIVATE": "a" * 64,
        "original_reply_sha256_PRIVATE": "b" * 64,
    }
    locators, prompts, references = capture.partition_cases([sample])
    assert "original_reply_PRIVATE" not in locators[0]
    assert "original_reply_PRIVATE" not in prompts[0]
    assert "prefix_messages_PRIVATE" not in references[0]
    assert prompts[0]["candidate_case_id_PRIVATE"] == references[0]["candidate_case_id_PRIVATE"]


def test_phase_is_updated_before_database_queries():
    import inspect

    body = inspect.getsource(capture.try_case)
    assert 'phase[0] = "HISTORY_LEDGER_RECOVERY"' in body
    assert 'phase[0] = "UNIQUE_REQUEST_MATCH"' in body
    assert 'phase[0] = "COMPLETED_HISTORY_EDIT_SCREEN"' in body


def test_postgres_error_message_is_not_exposed_by_safe_contract():
    import inspect

    body = inspect.getsource(capture.run)
    assert 'SQLSTATE_' in body
    assert 'str(exc)' not in body
