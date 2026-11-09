from __future__ import annotations

import json
import os
import stat
import sys

import pytest

from scripts import r60_p2b_claude_review_client_v1 as client
from storyforge_gold_quality import hf_severity_evidence_v2 as severity


def packet(index: int) -> dict:
    return {
        "schema": client.PACKET_SCHEMA,
        "calibration_id": f"{index:032x}",
        "visible_history": [{"role": "user", "content": "I choose tea."}],
        "target_text": "The innkeeper waits for the player's answer.",
        "verified_world_components": [],
    }


def test_validate_packets_requires_thirty_unique_packets():
    rows = [packet(index) for index in range(30)]
    assert len(client.validate_packets(rows)) == 30
    with pytest.raises(client.Hold, match="PACKET_COUNT_HOLD"):
        client.validate_packets(rows[:29])
    with pytest.raises(client.Hold, match="BLIND_ID_HOLD"):
        client.validate_packets([packet(0)] * 30)


def test_request_payload_uses_top_level_system_and_no_temperature():
    payload = client.build_request_payload("claude-opus-5-5", "cases", "rubric", 12000)
    assert payload["system"].startswith("rubric")
    assert payload["messages"] == [{"role": "user", "content": "cases"}]
    assert payload["stream"] is False
    assert "temperature" not in payload


def test_endpoint_normalizes_chat_completions_and_rejects_http():
    assert client.endpoint("https://4router.net/v1") == (
        "https://4router.net/v1/chat/completions"
    )
    with pytest.raises(client.Hold, match="HTTPS_REQUIRED"):
        client.endpoint("http://proxy.example/v1")


def test_output_normalizes_locator_metadata_without_changing_verdict():
    packets = [packet(index) for index in range(5)]
    rows = []
    for source in packets:
        assessments = {}
        for dimension in client.DIMS:
            reviewed = {
                "player_agency": ["interaction_contract"],
                "hard_rule": ["history_system", "history_user", "verified_world_component"],
                "safety": ["safety_policy"],
            }[dimension]
            assessments[dimension] = {
                "verdict": "NOT_SUPPORTED",
                "evidence": [{
                    "source": "history", "message_index": 1, "component_ref": "",
                    "start_char": 0, "end_char": 13, "quote": "I choose tea.",
                    "role": "user_instruction",
                }],
                "rule_basis": [],
                "reasoning_summary": "The target waits for the player and does not decide for them.",
                "missing_context": [],
                "context_coverage": {
                    "history_complete": True, "target_complete": True,
                    "relevant_context_complete": True,
                    "reviewed_rule_sources": reviewed,
                    "summary": "Checked.",
                },
                "confidence": 0.7,
            }
        rows.append({"calibration_id": source["calibration_id"],
                     "reviewer_type": client.REVIEWER, "assessments": assessments})
    output = client.validate_output("\n".join(json.dumps(row) for row in rows), {
        source["calibration_id"]: source for source in packets
    })
    assert len(output) == 5
    for row in output:
        for assessment in row["assessments"].values():
            assert assessment["verdict"] == "NOT_SUPPORTED"
            assert assessment["evidence"][0]["message_index"] == 0
            assert assessment["evidence"][0]["role"] == "context"
            assert len(assessment["context_coverage"]["summary"]) >= 12


def test_dry_run_creates_only_manifest_and_safe_stdout(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    input_dir.mkdir(mode=0o700)
    packet_path = input_dir / "P2B_BLIND_PACKETS_PRIVATE.jsonl"
    packet_path.write_bytes(b"".join(
        json.dumps(packet(index), ensure_ascii=False).encode() + b"\n"
        for index in range(30)
    ))
    os.chmod(packet_path, 0o600)
    rubric_path = tmp_path / "rubric.md"
    rubric_path.write_text("Synthetic rubric", encoding="utf-8")
    manifest = {
        "schema": "storyforge_r60_p2b_manifest_private_v1",
        "status": "P2B_HELDOUT_PACKETS_FROZEN__OWNER_REVIEW_NOT_STARTED",
        "rubric_version": severity.RUBRIC_VERSION,
        "packet_sha256": client.digest(packet_path.read_bytes()),
        "rubric_sha256": client.digest(rubric_path.read_bytes()),
        "case_count": 30,
        "old_owner_labels_exposed": False,
        "development_cases_exposed": False,
    }
    manifest["receipt_sha256"] = client.digest(client.canonical(manifest))
    manifest_path = input_dir / "P2B_MANIFEST_PRIVATE.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    manifest_path.chmod(0o600)
    schema_path = input_dir / "P2B_OWNER_SCHEMA_V2.json"
    schema_path.write_bytes(client.canonical(severity.response_schema_v2()) + b"\n")
    schema_path.chmod(0o600)
    output_dir = tmp_path / "output"
    output_dir.mkdir(mode=0o700)
    output_dir.chmod(0o700)
    monkeypatch.setattr(sys, "argv", [
        "r60_p2b_claude_review_client_v1",
        "--input-dir", str(input_dir), "--output-dir", str(output_dir),
        "--base-url", "https://4router.net/v1", "--rubric", str(rubric_path),
    ])
    assert client.main() == 0
    safe = json.loads(capsys.readouterr().out)
    assert safe["status"] == "P2B_CLAUDE_PREFLIGHT_PASS__NO_EXTERNAL_CALLS"
    assert safe["case_count"] == 30
    assert safe["dimension_count"] == 90
    assert stat.S_IMODE(output_dir.stat().st_mode) == 0o700
    assert (output_dir / "P2B_CLAUDE_RUN_MANIFEST_PRIVATE.json").exists()
    assert not (output_dir / "P2B_CLAUDE_ADVISORY_PRIVATE.jsonl").exists()
