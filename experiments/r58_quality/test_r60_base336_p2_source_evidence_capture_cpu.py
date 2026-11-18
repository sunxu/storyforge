"""Synthetic-only tests for Owner-local P2/Base336 source evidence capture."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r60_base336_p2_source_evidence_capture_cpu as audit


def p2_source(i: int) -> dict:
    return {
        "source_key": f"S{i:02d}",
        "story_id": f"p2-story-{i}",
        "public_content_revision": 7,
        "public_content_hash": "a" * 64,
        "submission_snapshot_sha256": "b" * 64,
        "world_json_md5": "c" * 32,
        "moderation_submission_id": f"submission-{i}",
        "permission_event_id": f"permission-{i}",
        "permission_kind": "ai",
        "permission_result": "ai_approved",
        "permission_submission_id": f"submission-{i}",
        "permission_submission_bound": True,
        "permission_to_visibility": "public",
        "snapshot_matches_current_public_v2": True,
        "snapshot_hash_matches_submission_sha256": True,
    }


def p2_doc() -> dict:
    return {
        "schema": audit.P2_MANIFEST_SCHEMA,
        "status": audit.P2_MANIFEST_STATUS,
        "rights_scope": (
            "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
            "NO_TRAINING_OR_REDISTRIBUTION"
        ),
        "selection": {
            "selected_stories": 8,
            "authors": 5,
            "distinct_world_json": 8,
            "created_before_gpu_run": 3,
            "created_after_gpu_run": 5,
            "private_session_bodies_read": False,
        },
        "sources": [p2_source(i) for i in range(1, 9)],
    }


def p2_rows(sources: list[dict]) -> list[tuple]:
    rows = []
    for source in sources:
        fields = {
            "world": {"worldSentence": "A public world"},
            "character": {"name": "A"},
            "characters": [{"name": "A"}],
            "opening": {"opening": "A beginning"},
        }
        rows.append((
            source["story_id"], source["public_content_revision"],
            source["public_content_hash"], fields,
            source["moderation_submission_id"], source["public_content_revision"],
            source["submission_snapshot_sha256"], fields, "public",
            source["permission_event_id"], source["permission_submission_id"],
            "public", source["permission_kind"], source["permission_result"],
            source["world_json_md5"],
        ))
    return rows


def test_load_p2_manifest_accepts_exact_eight_source_contract(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(p2_doc()), encoding="utf-8")
    os.chmod(path, 0o600)
    doc, raw, sources = audit.load_p2_manifest(path)
    assert doc["status"] == audit.P2_MANIFEST_STATUS
    assert len(raw) > 0
    assert len(sources) == 8


def test_load_p2_manifest_rejects_duplicate_story_ids(tmp_path):
    doc = p2_doc()
    doc["sources"][1]["story_id"] = doc["sources"][0]["story_id"]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    os.chmod(path, 0o600)
    try:
        audit.load_p2_manifest(path)
    except audit.Hold as exc:
        assert str(exc) == "P2_SOURCE_DUPLICATE_HOLD"
    else:
        raise AssertionError("duplicate P2 story IDs must HOLD")


def test_p2_rows_require_exact_revision_snapshot_and_permission_binding():
    sources = [p2_source(i) for i in range(1, 9)]
    rows = p2_rows(sources)
    records, coverage = audit._p2_records(rows, sources)
    assert len(records) == 8
    assert coverage == {field: 8 for field in audit.FIELDS}


def test_p2_rows_reject_snapshot_drift():
    sources = [p2_source(i) for i in range(1, 9)]
    rows = p2_rows(sources)
    first = list(rows[0])
    first[7] = {"world": {"worldSentence": "changed"}}
    rows[0] = tuple(first)
    try:
        audit._p2_records(rows, sources)
    except audit.Hold as exc:
        assert str(exc) == "P2_SNAPSHOT_CURRENT_MISMATCH_HOLD"
    else:
        raise AssertionError("snapshot drift must HOLD")


def test_p2_rows_reject_permission_submission_mismatch():
    sources = [p2_source(i) for i in range(1, 9)]
    rows = p2_rows(sources)
    first = list(rows[0])
    first[10] = "wrong-submission"
    rows[0] = tuple(first)
    try:
        audit._p2_records(rows, sources)
    except audit.Hold as exc:
        assert str(exc) == "P2_REVISION_PERMISSION_BINDING_HOLD"
    else:
        raise AssertionError("permission binding drift must HOLD")


def test_base_records_require_current_coverage_for_all_172_stories():
    stories = [f"base-story-{i}" for i in range(172)]
    rows = [
        ("current", story, None, "2026-11-19T00:00:00Z",
         {"world": "w"}, {"character": "c"}, [], {"opening": "o"}, "d" * 32)
        for story in stories
    ]
    records, stats = audit._base_records(rows, stories)
    assert len(records) == 172
    assert stats["current_rows"] == 172
    assert stats["archived_version_rows"] == 0
    assert stats["field_nonnull_counts"] == {field: 172 for field in audit.FIELDS}


def test_base_records_reject_missing_current_story():
    stories = [f"base-story-{i}" for i in range(172)]
    rows = [
        ("current", story, None, None, None, None, None, None, None)
        for story in stories[:-1]
    ]
    rows.append(("archived", stories[0], 1, None, None, None, None, None, None))
    try:
        audit._base_records(rows, stories)
    except audit.Hold as exc:
        assert str(exc) == "BASE_CURRENT_COVERAGE_HOLD"
    else:
        raise AssertionError("missing current story must HOLD")


def test_exact_field_matches_report_counts_without_emitting_values():
    p2 = [{
        "source_key_PRIVATE": "S01",
        "story_id_PRIVATE": "secret-p2-id",
        "source_fields_PRIVATE": {field: {"same": field} for field in audit.FIELDS},
    }]
    base = [{
        "source_kind": "current",
        "story_id_PRIVATE": "secret-base-id",
        "revision_id_PRIVATE": None,
        "source_fields_PRIVATE": {field: {"same": field} for field in audit.FIELDS},
    }]
    counts, pairs = audit.exact_field_matches(p2, base)
    assert all(counts[field]["p2_sources"] == 1 for field in audit.FIELDS)
    assert len(pairs) == len(audit.FIELDS)
    safe = audit.safe_summary(
        {"current_rows": 172, "archived_version_rows": 0,
         "field_nonnull_counts": {field: 172 for field in audit.FIELDS}},
        {field: 8 for field in audit.FIELDS}, p2, 0, counts, 1234,
    )
    rendered = json.dumps(safe)
    assert "secret-p2-id" not in rendered
    assert "secret-base-id" not in rendered
    assert safe["historical_actual_sent_verified"] is False
    assert safe["reviewer_independence_verified"] is False
    assert safe["train_admitted"] == 0


def test_output_target_is_create_only_and_private(tmp_path, monkeypatch):
    os.chmod(tmp_path, 0o700)
    monkeypatch.setattr(audit.private, "BASE", tmp_path)
    target = tmp_path / "new-output"
    audit.validate_output_target(target)
    target.mkdir(mode=0o700)
    try:
        audit.validate_output_target(target)
    except audit.Hold as exc:
        assert str(exc) == "OUTPUT_TARGET_HOLD"
    else:
        raise AssertionError("existing output target must HOLD")


def test_private_writer_uses_0600_and_refuses_overwrite(tmp_path):
    path = tmp_path / "private.json"
    audit._write_new(path, b'{"private":true}')
    assert path.stat().st_mode & 0o777 == 0o600
    try:
        audit._write_new(path, b'{"private":false}')
    except FileExistsError:
        pass
    else:
        raise AssertionError("private output must be create-only")
