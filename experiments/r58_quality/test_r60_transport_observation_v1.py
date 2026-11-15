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


def test_probe_create_only_observation_binds_to_existing_client(monkeypatch, tmp_path):
    import r60_real_private_batch as private
    import r60_reviewer_protocol_probe as probe

    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(private, "BASE", root)
    target = root / "qwen-test"
    calls = []

    def fake_request(endpoint, model, key, prompt, timeout, json_mode, **kwargs):
        assert (target / "ATTEMPT_PRIVATE.json").exists()
        calls.append(model)
        kwargs["evidence_sink"]({
            "provider_response_id_observed": "synthetic-qwen-id",
            "provider_evidence_authenticated": False,
        })
        return sample()

    monkeypatch.setattr(ai, "model_request", fake_request)
    result = probe.inspect(
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3.7-flash", protocol="openai-chat",
        key_env="DASHSCOPE_API_KEY", allow_remote=True,
        json_mode=True, execute=True, evidence_dir=target,
    )
    assert calls == ["qwen3.7-flash"]
    assert result["status"] == "REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE"
    data = json.loads((target / "OUTCOME_PRIVATE.json").read_text())
    assert data["provider_execution_independence_verified"] is False
    assert data["observations"][0]["provider_response_id_observed"] == "synthetic-qwen-id"
    assert all(f.stat().st_mode & 0o777 == 0o600 for f in target.iterdir())
    again = probe.inspect(
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3.7-flash", protocol="openai-chat",
        key_env="DASHSCOPE_API_KEY", allow_remote=True,
        json_mode=True, execute=True, evidence_dir=target,
    )
    assert again["status"] == "REVIEWER_PROTOCOL_HOLD"
    assert calls == ["qwen3.7-flash"]


def test_probe_observation_retained_when_invalid_json(monkeypatch, tmp_path):
    import r60_real_private_batch as private
    import r60_reviewer_protocol_probe as probe

    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(private, "BASE", root)
    target = root / "deepseek-test"

    def fake_request(endpoint, model, key, prompt, timeout, json_mode, **kwargs):
        kwargs["evidence_sink"]({
            "provider_response_id_observed": "synthetic-deepseek-id",
            "provider_evidence_authenticated": False,
        })
        raise ai.Hold("MODEL_JSON_INVALID")

    monkeypatch.setattr(ai, "model_request", fake_request)
    result = probe.inspect(
        endpoint="https://api.deepseek.com",
        model="deepseek-flash", protocol="deepseek-chat",
        key_env="R60_DEEPSEEK_KEY", allow_remote=True,
        json_mode=True, execute=True, evidence_dir=target,
    )
    assert result["reason_code"] == "MODEL_JSON_INVALID"
    observed = json.loads((target / "OUTCOME_PRIVATE.json").read_text())
    assert observed["observations"][0]["provider_response_id_observed"] == (
        "synthetic-deepseek-id"
    )
    assert observed["provider_execution_independence_verified"] is False
