"""Only synthetic Gold48 reconstructed input draft tests; no real private data."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))

from test_r60_p2_gold48_candidate_preflight_cpu import private_file
from test_r60_p2_gold48_source_component_bind_cpu import setup_documents

spec = importlib.util.spec_from_file_location(
    "r60_p2_gold48_reconstructed_input_draft_cpu",
    ROOT / "scripts/r60_p2_gold48_reconstructed_input_draft_cpu.py",
)
draft_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft_module)

from r60_p2_gold48_source_component_bind_cpu import join as source_join


def prepare(tmp_path, *, bad_memory=False):
    candidate, evidence, manifest = setup_documents(tmp_path)
    locator_path = candidate / "GOLD48_CANDIDATE_LOCATORS_PRIVATE.json"
    prefix_path = candidate / "GOLD48_CANDIDATE_PREFIXES_PRIVATE.json"
    locators = json.loads(locator_path.read_text())
    prefixes = json.loads(prefix_path.read_text())
    for case in locators["cases_PRIVATE"]:
        case["target_created_at_PRIVATE"] = "2026-11-17T00:00:00+00:00"
    for i, case in enumerate(prefixes["cases_PRIVATE"]):
        recovered = case["history_recovery_PRIVATE"]
        if i == 0:
            recovered["summary_status"] = "PRETARGET_SUMMARY_AVAILABLE"
            recovered["pretarget_summaries"] = [{
                "status": "PRETARGET_COVERAGE_VERIFIED",
                "used": True,
                "updated_at": (
                    "2026-11-18T00:00:00+00:00"
                    if bad_memory else "2026-11-16T00:00:00+00:00"
                ),
                "fields": {"memory_summary": "synthetic verified memory"},
            }]
        else:
            recovered["summary_status"] = "NO_VERIFIED_PRETARGET_SUMMARY"
            recovered["pretarget_summaries"] = []
    private_file(locator_path, locators)
    private_file(prefix_path, prefixes)
    bind_doc, bind_safe = source_join(candidate, evidence, manifest)
    bind_root = tmp_path / "bindings"
    bind_root.mkdir(mode=0o700)
    private_file(bind_root / "GOLD48_SOURCE_COMPONENT_BINDINGS_PRIVATE.json", bind_doc)
    private_file(bind_root / "GOLD48_SOURCE_COMPONENT_BINDING_SAFE.json", bind_safe)
    return candidate, bind_root, evidence, manifest


def test_48_drafts_with_verified_pretarget_memory_and_no_reference(tmp_path):
    candidate, bound, evidence, manifest = prepare(tmp_path)
    # Draft builder never opens the historical reply reference file.
    (candidate / "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json").unlink()
    doc, safe = draft_module.draft(candidate, bound, evidence, manifest)
    assert safe["status"] == "GOLD48_RECONSTRUCTED_INPUT_DRAFT_48_READY__NOT_FROZEN"
    assert safe["case_count"] == 48
    assert safe["memory_pretarget_verified_count"] == 1
    assert safe["memory_unverified_omitted_count"] == 47
    assert safe["original_reference_read"] is False
    assert safe["owner_gold48_freeze"] is False
    assert safe["gpu_started"] is False
    assert doc["original_reference_not_read_or_included"] is True
    assert len(doc["cases_PRIVATE"]) == 48
    first = doc["cases_PRIVATE"][0]
    second = doc["cases_PRIVATE"][1]
    assert first["memory_provenance"] == "VERIFIED_PRETARGET_SESSION_SUMMARY"
    assert second["memory_provenance"] == "NO_VERIFIED_PRETARGET_MEMORY"
    assert first["reconstructed_messages_PRIVATE"][-1] == {
        "role": "user", "content": "final input 0",
    }
    assert first["reconstructed_messages_PRIVATE"][0]["role"] == "system"
    assert "synthetic verified memory" in first["reconstructed_messages_PRIVATE"][0]["content"]
    assert "synthetic verified memory" not in second["reconstructed_messages_PRIVATE"][0]["content"]
    for row in doc["cases_PRIVATE"]:
        messages = row["reconstructed_messages_PRIVATE"]
        assert "original response" not in json.dumps(messages)
        assert row["reconstructed_messages_sha256_PRIVATE"] == draft_module.sha(
            draft_module.canonical(messages)
        )


def test_future_memory_is_rejected_instead_of_backfilled(tmp_path):
    candidate, bound, evidence, manifest = prepare(tmp_path, bad_memory=True)
    with pytest.raises(draft_module.Hold, match="PRETARGET_SUMMARY_TIMESTAMP_HOLD"):
        draft_module.draft(candidate, bound, evidence, manifest)


def test_source_snapshot_bytes_tamper_refused(tmp_path):
    candidate, bound, evidence, manifest = prepare(tmp_path)
    evidence_doc = json.loads(evidence.read_text())
    evidence_doc["p2_scope"]["source_records_PRIVATE"][0]["source_fields_PRIVATE"]["world"] = {
        "worldSentence": "tampered",
    }
    private_file(evidence, evidence_doc)
    with pytest.raises(draft_module.Hold, match="CANDIDATE_SOURCE_EVIDENCE_FILE_BINDING_HOLD"):
        draft_module.draft(candidate, bound, evidence, manifest)


def test_previously_bound_prefix_file_tamper_refused(tmp_path):
    candidate, bound, evidence, manifest = prepare(tmp_path)
    prefix_path = candidate / "GOLD48_CANDIDATE_PREFIXES_PRIVATE.json"
    prefixes = json.loads(prefix_path.read_text())
    prefixes["cases_PRIVATE"][0]["prefix_messages_PRIVATE"][-1]["content"] = "tampered"
    private_file(prefix_path, prefixes)
    with pytest.raises(draft_module.Hold, match="CANDIDATE_SOURCE_EVIDENCE_FILE_BINDING_HOLD"):
        draft_module.draft(candidate, bound, evidence, manifest)
