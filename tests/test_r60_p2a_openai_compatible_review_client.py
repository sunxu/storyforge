from __future__ import annotations

import json

import pytest

from scripts import r60_p2a_openai_compatible_review_client as client


def packet(blind_id="a" * 32):
    return {
        "schema": "storyforge_r60_p2a_second_model_cross_review_v1",
        "blind_id": blind_id,
        "visible_history": [{"role": "user", "content": "I refuse."}],
        "target_text": "The character respects the refusal.",
        "verified_world_components": [],
        "review_targets": {
            dim: {
                "owner_verdict_to_assess": "SUPPORTED",
                "owner_evidence_to_assess": [{"quote": "I refuse."}],
                "owner_rule_basis_to_assess": [],
                "owner_context_coverage_to_assess": {},
                "owner_missing_context_to_assess": [],
            }
            for dim in client.DIMS
        },
    }


def output_rows(rows):
    return "\n".join(json.dumps({
        "blind_id": row["blind_id"],
        "dimension": dim,
        "reviewer_type": client.REVIEWER,
        "conclusion": "SUPPORTS_VERDICT",
        "reviewed_evidence_indexes": [0],
        "reasoning_summary": "The quoted evidence supports the stated boundary.",
        "unresolved_context": [],
    }) for row in rows for dim in client.DIMS)


def test_validate_packets_requires_twenty_unique_blind_cases():
    rows = [packet(f"{i:032x}") for i in range(20)]
    assert len(client.validate_packets(rows)) == 20
    with pytest.raises(client.Hold, match="PACKET_COUNT_HOLD"):
        client.validate_packets(rows[:19])
    with pytest.raises(client.Hold, match="BLIND_ID_HOLD"):
        client.validate_packets([packet()] * 20)


def test_output_validator_requires_exact_sixty_dimensions_and_evidence_coverage():
    rows = [packet(f"{i:032x}") for i in range(20)]
    expected = client.validate_packets(rows)
    checked = client.validate_output(output_rows(rows), expected)
    assert len(checked) == 60
    with pytest.raises(client.Hold, match="OUTPUT_COVERAGE_HOLD"):
        client.validate_output("\n".join(output_rows(rows).splitlines()[:-1]), expected)
    bad = output_rows(rows).replace('"reviewed_evidence_indexes": [0]', '"reviewed_evidence_indexes": []', 1)
    with pytest.raises(client.Hold, match="OUTPUT_EVIDENCE_COVERAGE_LINE_1"):
        client.validate_output(bad, expected)


def test_output_validator_rejects_owner_identity_spoofing_and_extra_keys():
    rows = [packet(f"{i:032x}") for i in range(20)]
    expected = client.validate_packets(rows)
    bad = output_rows(rows).replace(client.REVIEWER, "OWNER_INDEPENDENT", 1)
    with pytest.raises(client.Hold, match="OUTPUT_ENUM_LINE_1"):
        client.validate_output(bad, expected)
    obj = json.loads(output_rows(rows).splitlines()[0])
    obj["reviewer_ref"] = "forged"
    bad = "\n".join([json.dumps(obj)] + output_rows(rows).splitlines()[1:])
    with pytest.raises(client.Hold, match="OUTPUT_KEYSET_LINE_1"):
        client.validate_output(bad, expected)


def test_remote_endpoint_requires_https_and_normalizes_openai_path():
    assert client.endpoint("https://proxy.example/api/v1") == "https://proxy.example/api/v1/chat/completions"
    assert client.endpoint("https://proxy.example/api/v1/chat/completions") == "https://proxy.example/api/v1/chat/completions"
    with pytest.raises(client.Hold, match="HTTPS_REQUIRED"):
        client.endpoint("http://proxy.example/v1")


def test_claude_request_uses_top_level_system_not_system_message():
    payload = client.build_request_payload(
        "claude-opus-5-5",
        "review these cases",
        "independent reviewer prompt",
        12000,
    )
    assert payload["system"].startswith("independent reviewer prompt")
    assert payload["messages"] == [{"role": "user", "content": "review these cases"}]
    assert all(message["role"] != "system" for message in payload["messages"])
    assert payload["stream"] is False
    assert "temperature" not in payload
