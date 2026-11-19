"""Synthetic contract tests. No private Story or P2 content."""
from __future__ import annotations

import hashlib
import json

import pytest
from r60_p2c_existing_source_package_preflight_cpu import Hold, evaluate, main


def synthetic():
    ids = [f"base-{i:03d}" for i in range(172)]
    p2_ids = [f"new-{i}" for i in range(8)]
    selected = [{"story_id": sid, "source_key": f"src-{i}",
                 "public_content_revision": 1, "moderation_submission_id": f"sub-{i}",
                 "permission_event_id": f"perm-{i}",
                 "submission_snapshot_sha256": "a" * 64, "world_json_md5": "b" * 32}
                for i, sid in enumerate(p2_ids)]
    manifest = {"schema": "storyforge_r60_base336_p2_public_source_inventory_private_v1",
                "sources": selected}
    raw = json.dumps(manifest).encode()
    package = {
        "schema": "storyforge_r60_base336_p2_source_evidence_private_v1",
        "base336_scope": {
            "cases": 336, "story_ids_PRIVATE": ids,
            "candidate_source_bindings_PRIVATE": [
                {"candidate_position_1based_PRIVATE": i + 1,
                 "story_id_PRIVATE": ids[i % 172]} for i in range(336)
            ],
            "source_records_PRIVATE": [
                {"story_id_PRIVATE": sid, "source_kind": "current",
                 "revision_id_PRIVATE": None,
                 "source_fields_PRIVATE": dict.fromkeys(("world", "character", "characters", "opening"))}
                for sid in ids
            ],
        },
        "p2_scope": {"manifest_sha256_PRIVATE": hashlib.sha256(raw).hexdigest(),
                     "source_records_PRIVATE": [
                         {"story_id_PRIVATE": s["story_id"],
                          "source_key_PRIVATE": s["source_key"],
                          "public_content_revision_PRIVATE": s["public_content_revision"],
                          "submission_id_PRIVATE": s["moderation_submission_id"],
                          "permission_event_id_PRIVATE": s["permission_event_id"],
                          "submission_snapshot_sha256_PRIVATE": s["submission_snapshot_sha256"],
                          "world_json_md5_PRIVATE": s["world_json_md5"],
                          "source_fields_PRIVATE": dict.fromkeys(("world", "character", "characters", "opening"))}
                         for s in selected]},
        "exact_field_match_pairs_PRIVATE": [],
    }
    return package, manifest, hashlib.sha256(raw).hexdigest()


def test_complete_source_package_still_holds_semantics():
    package, manifest, digest = synthetic()
    safe = evaluate(package, manifest, digest)
    assert safe["base336_stories"] == 172
    assert safe["p2_sources"] == 8
    assert safe["base336_case_source_bindings"] == 336
    assert safe["p2_c"] == "HOLD"
    assert safe["all_p2_sources_semantically_independent_verified"] is False
    assert safe["database_accessed"] is False


def test_truncated_base_current_holds():
    package, manifest, digest = synthetic()
    package["base336_scope"]["source_records_PRIVATE"].pop()
    with pytest.raises(Hold, match="BASE_SOURCE_ROWS_HOLD"):
        evaluate(package, manifest, digest)


def test_p2_manifest_binding_holds():
    package, manifest, _digest = synthetic()
    with pytest.raises(Hold, match="P2_MANIFEST_BINDING_HOLD"):
        evaluate(package, manifest, "0" * 64)


def test_p2_overlap_holds():
    package, manifest, digest = synthetic()
    manifest["sources"][0]["story_id"] = "base-000"
    package["p2_scope"]["source_records_PRIVATE"][0]["story_id_PRIVATE"] = "base-000"
    with pytest.raises(Hold, match="BASE_P2_EXACT_STORY_OVERLAP_HOLD"):
        evaluate(package, manifest, digest)


def test_missing_package_is_safe(tmp_path, monkeypatch, capsys):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    manifest.chmod(0o600)
    monkeypatch.setattr("sys.argv", ["preflight", "--package", str(tmp_path / "missing.json"),
                                   "--p2-manifest", str(manifest)])
    assert main() == 42
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "P2_8X172_SOURCE_PACKAGE_HOLD"
    assert output["reason_code"] == "INPUT_MISSING_OR_TYPE_HOLD"
    assert output["private_values_emitted"] is False
