"""Synthetic-only offline Gold48 candidate artifact contract tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/r60_p2_gold48_candidate_preflight_cpu.py"
spec = importlib.util.spec_from_file_location("r60_p2_gold48_candidate_preflight_cpu", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def private_file(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)


def synthetic_bundle(tmp_path):
    tmp_path.chmod(0o700)
    locators, prefixes, references = [], [], []
    for i in range(48):
        story_index = i // 6
        case = f"G48-C{i + 1:02d}"
        story, session = f"synthetic-story-{story_index}", f"session-{i}"
        target, request = f"target-{i}", f"request-{i}"
        messages = [
            {"role": "user", "content": f"scene start {i}"},
            {"role": "assistant", "content": f"historical assistant {i}"},
            {"role": "user", "content": f"final input {i}"},
        ]
        reply = f"original response {i}"
        digest = module.sha_utf8(module.canonical(messages))
        gold_hash = module.sha_utf8(reply)
        locators.append({
            "candidate_case_id_PRIVATE": case,
            "story_id_PRIVATE": story,
            "session_id_PRIVATE": session,
            "source_key_PRIVATE": f"S{story_index + 1:02d}",
            "assistant_message_id_PRIVATE": target,
            "request_id_PRIVATE": request,
            "source_snapshot_sha256_PRIVATE": "a" * 64,
            "source_public_revision_PRIVATE": 1,
            "prefix_sha256_PRIVATE": digest,
            "original_reply_sha256_PRIVATE": gold_hash,
            "exclude_from_42_sensitivity": story_index == 3,
        })
        prefixes.append({
            "candidate_case_id_PRIVATE": case,
            "prefix_messages_PRIVATE": messages,
            "prefix_sha256_PRIVATE": digest,
            "history_recovery_PRIVATE": {
                "story_id": story,
                "session_id": session,
                "target": {"message_id": target},
                "target_sha256": gold_hash,
                "history_message_count": len(messages),
                "history_materialized_in_leaf_session": True,
                "history": messages,
            },
        })
        references.append({
            "candidate_case_id_PRIVATE": case,
            "original_reply_PRIVATE": reply,
            "original_reply_sha256_PRIVATE": gold_hash,
        })
    for filename, rows in zip(module.SCHEMAS, (locators, prefixes, references),
                              strict=True):
        private_file(tmp_path / filename, {
            "schema": module.SCHEMAS[filename],
            "status": module.SHARED_STATUS,
            "origin_identity": module.ORIGIN,
            "eval_input_contract": module.CONTRACT,
            "cases_PRIVATE": rows,
        })
    private_file(tmp_path / "GOLD48_CAPTURE_SAFE.json", {
        "schema": "storyforge_r60_p2_gold48_private_recovery_capture_safe_v1",
        "status": "NEW_GOLD48_PRIVATE_CANDIDATES_CAPTURED__NOT_FROZEN",
        "case_count": 48, "original_reference_count": 48,
        "request_metadata_unique_count": 48, "session_count": 48,
        "flagged_story_case_count": 6,
        "primary_count": 48, "sensitivity_count": 42,
        "owner_final_gold48_freeze": False,
    })
    return tmp_path


def test_valid_synthetic_bundle_stays_not_frozen(tmp_path):
    root = synthetic_bundle(tmp_path)
    safe = module.evaluate(root)
    assert safe["status"] == "GOLD48_PRIVATE_CANDIDATE_PREFLIGHT_PASS__NOT_FROZEN"
    assert safe["case_count"] == 48
    assert safe["source_count"] == 8
    assert safe["sensitivity_count"] == 42
    assert safe["owner_gold48_freeze"] is False
    assert safe["database_accessed"] is False


def test_original_reference_tamper_holds(tmp_path):
    root = synthetic_bundle(tmp_path)
    path = root / "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json"
    data = json.loads(path.read_text())
    data["cases_PRIVATE"][0]["original_reply_PRIVATE"] = "tampered"
    private_file(path, data)
    with pytest.raises(module.Hold, match="SHA_BINDING"):
        module.evaluate(root)


def test_wrong_six_case_allocation_holds(tmp_path):
    root = synthetic_bundle(tmp_path)
    path = root / "GOLD48_CANDIDATE_LOCATORS_PRIVATE.json"
    data = json.loads(path.read_text())
    data["cases_PRIVATE"][0]["source_key_PRIVATE"] = "S02"
    private_file(path, data)
    with pytest.raises(module.Hold):
        module.evaluate(root)


def test_insecure_reference_file_mode_holds(tmp_path):
    root = synthetic_bundle(tmp_path)
    path = root / "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json"
    path.chmod(0o644)
    with pytest.raises(module.Hold, match="PERMISSION_OR_SIZE_HOLD"):
        module.evaluate(root)


def test_wrong_session_receipt_holds(tmp_path):
    root = synthetic_bundle(tmp_path)
    path = root / "GOLD48_CAPTURE_SAFE.json"
    data = json.loads(path.read_text())
    data["session_count"] = 25
    private_file(path, data)
    with pytest.raises(module.Hold, match="SENSITIVITY_SCOPE_HOLD"):
        module.evaluate(root)
