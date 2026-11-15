"""Synthetic transport evidence regression; no network, no private stories."""
import io
import json

import pytest
import r60_real_ai_dual_review as ai


def sample():
    return {
        "decision": "PASS",
        "scores": {
            "chinese_prose": 4, "character_consistency": 4,
            "npc_initiative": 4, "player_agency": 4,
            "rule_fidelity": 4, "narrative_continuity": 4,
        },
        "severe_flags": {
            "serious_player_agency": False, "hard_fact_or_ban": False,
            "safety_exclusion": False,
        },
        "reason_cn": "合成记录",
    }


def test_observer_records_actual_mock_envelope_metadata(monkeypatch):
    data = json.dumps({
        "id": "mock-server-request-123456",
        "choices": [{"finish_reason": "stop",
                     "message": {"content": json.dumps(sample())}}],
    }).encode()
    class FakeResponse(io.BytesIO):
        def __init__(self, payload):
            super().__init__(payload)
            self.headers = {"x-request-id": "mock-header-678910"}

    class FakeOpener:
        def open(self, request, timeout):
            return FakeResponse(data)

    monkeypatch.setattr(ai.urllib.request, "build_opener",
                        lambda *args: FakeOpener())
    observed = []
    out = ai.model_request(
        "https://example.invalid/v1/chat/completions", "qwen3.7-flash",
        "", "合成消息", 10, True, evidence_sink=observed.append,
    )
    assert out == sample()
    assert len(observed) == 1
    assert observed[0]["provider_response_id_observed"] == "mock-server-request-123456"
    assert observed[0]["provider_header_request_id_observed"] == "mock-header-678910"
    assert len(observed[0]["request_body_sha256"]) == 64
    assert len(observed[0]["response_wire_sha256"]) == 64
    assert observed[0]["provider_evidence_authenticated"] is False
    assert "合成消息" not in json.dumps(observed[0], ensure_ascii=False)


def test_observer_survives_bad_model_json(monkeypatch):
    data = b'{"id":"mock-deepseek-987654","choices":[{"message":{"content":"bad-json"}}]}'
    class FakeOpener:
        def open(self, request, timeout):
            return io.BytesIO(data)
    monkeypatch.setattr(ai.urllib.request, "build_opener",
                        lambda *args: FakeOpener())
    observed = []
    with pytest.raises(ai.Hold, match="MODEL_JSON_INVALID"):
        ai.model_request(
            "https://example.invalid/v1/chat/completions", "deepseek-flash",
            "", "synthetic", 10, True, protocol="deepseek-chat",
            evidence_sink=observed.append,
        )
    assert observed[0]["provider_response_id_observed"] == "mock-deepseek-987654"
    assert observed[0]["provider_evidence_authenticated"] is False


def test_legacy_no_observer_unchanged(monkeypatch):
    class FakeOpener:
        def open(self, request, timeout):
            return io.BytesIO(json.dumps({
                "choices": [{"message": {"content": json.dumps(sample())}}],
            }).encode())
    monkeypatch.setattr(ai.urllib.request, "build_opener",
                        lambda *args: FakeOpener())
    assert ai.model_request("https://example.invalid", "test", "", "x", 10, False) == sample()
