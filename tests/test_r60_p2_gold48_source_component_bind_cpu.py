"""Synthetic-only proof for Gold48 public-card snapshot binding."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from test_r60_p2_gold48_candidate_preflight_cpu import private_file, synthetic_bundle

spec = importlib.util.spec_from_file_location(
    "r60_p2_gold48_source_component_bind_cpu",
    ROOT / "scripts/r60_p2_gold48_source_component_bind_cpu.py",
)
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)


def setup_documents(tmp_path):
    (tmp_path / "candidate").mkdir(mode=0o700)
    candidates = synthetic_bundle(tmp_path / "candidate")
    manifest_path = tmp_path / "manifest.json"
    evidence_path = tmp_path / "evidence.json"
    sources, records = [], []
    for i in range(8):
        story = f"synthetic-story-{i}"
        key = f"S{i + 1:02d}"
        snapshot = "a" * 64
        sources.append({
            "story_id": story,
            "source_key": key,
            "public_content_revision": 1,
            "submission_snapshot_sha256": snapshot,
            "world_json_md5": "c" * 32,
            "snapshot_matches_current_public_v2": True,
            "snapshot_hash_matches_submission_sha256": True,
            "permission_submission_bound": True,
            "permission_to_visibility": "public",
        })
        records.append({
            "story_id_PRIVATE": story,
            "source_key_PRIVATE": key,
            "public_content_revision_PRIVATE": 1,
            "submission_snapshot_sha256_PRIVATE": snapshot,
            "world_json_md5_PRIVATE": "c" * 32,
            "source_fields_PRIVATE": {
                "world": {"worldSentence": "this is a synthetic world"},
                "character": None,
                "characters": [{"name": "synthetic"}],
                "opening": {"text": "synthetic opening"},
            },
        })
    private_file(manifest_path, {
        "schema": binding.INVENTORY_SCHEMA,
        "status": binding.INVENTORY_STATUS,
        "rights_scope": (
            "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
            "NO_TRAINING_OR_REDISTRIBUTION"
        ),
        "sources": sources,
    })
    private_file(evidence_path, {
        "schema": binding.EVIDENCE_SCHEMA,
        "p2_scope": {
            "manifest_sha256_PRIVATE": binding.sha(manifest_path.read_bytes()),
            "source_records_PRIVATE": records,
        },
    })
    return candidates, evidence_path, manifest_path


def test_eight_source_four_component_binding_not_freeze(tmp_path):
    candidate, evidence, manifest = setup_documents(tmp_path)
    package, safe = binding.join(candidate, evidence, manifest)
    assert safe["status"] == "GOLD48_PUBLIC_SOURCE_COMPONENTS_BOUND__INPUT_NOT_FROZEN"
    assert safe["case_count"] == 48
    assert safe["source_count"] == 8
    assert safe["owner_gold48_freeze"] is False
    assert safe["database_accessed"] is False
    assert package["eval_input_contract"] == "RECONSTRUCTED_EVALUATION_INPUT"
    assert len(package["cases_PRIVATE"]) == 48
    assert all(row["public_component_provenance"] == "EVALUATION_TIME_SNAPSHOT"
               for row in package["cases_PRIVATE"])
    assert all(row["reconstructed_messages_frozen"] is False
               and row["original_reference_included"] is False
               for row in package["cases_PRIVATE"])
    assert not any("original response" in json.dumps(row)
                   for row in package["cases_PRIVATE"])


def test_source_evidence_manifest_mismatch_holds(tmp_path):
    candidate, evidence, manifest = setup_documents(tmp_path)
    data = json.loads(manifest.read_text())
    data["sources"][0]["public_content_revision"] = 2
    private_file(manifest, data)
    with pytest.raises(binding.Hold, match="SOURCE_EVIDENCE_MANIFEST_SHA_HOLD"):
        binding.join(candidate, evidence, manifest)


def test_case_source_revision_mismatch_holds(tmp_path):
    candidate, evidence, manifest = setup_documents(tmp_path)
    data = json.loads(evidence.read_text())
    data["p2_scope"]["source_records_PRIVATE"][0]["public_content_revision_PRIVATE"] = 2
    private_file(evidence, data)
    with pytest.raises(binding.Hold, match="SOURCE_REVISION_SNAPSHOT_CROSSWALK_HOLD"):
        binding.join(candidate, evidence, manifest)


def test_source_missing_world_holds(tmp_path):
    candidate, evidence, manifest = setup_documents(tmp_path)
    data = json.loads(evidence.read_text())
    data["p2_scope"]["source_records_PRIVATE"][0]["source_fields_PRIVATE"]["world"] = None
    private_file(evidence, data)
    with pytest.raises(binding.Hold, match="PUBLIC_STORY_COMPONENTS_INCOMPLETE_HOLD"):
        binding.join(candidate, evidence, manifest)


def test_source_permission_mismatch_holds(tmp_path):
    candidate, evidence, manifest = setup_documents(tmp_path)
    doc = json.loads(manifest.read_text())
    doc["sources"][0]["permission_submission_bound"] = False
    private_file(manifest, doc)
    evidence_doc = json.loads(evidence.read_text())
    evidence_doc["p2_scope"]["manifest_sha256_PRIVATE"] = binding.sha(manifest.read_bytes())
    private_file(evidence, evidence_doc)
    with pytest.raises(binding.Hold, match="INVENTORY_SOURCE_IDENTITY_OR_RIGHTS_HOLD"):
        binding.join(candidate, evidence, manifest)
