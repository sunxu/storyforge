"""Synthetic-only tests for isolated R60 AI reviewer, no network or private texts."""
import json
import os

import pytest
import r60_real_ai_dual_review as ai
import r60_real_private_batch as batch


def example_case():
    return batch.parse_rows([(
        "story-example", "session-example", "a-id", "u-id", "p-id", "pu-id", 10,
        "此前玩家想从房间离开", "NPC说出了自己的顾虑",
        "玩家告知 NPC 自己要离开", "NPC 认真考虑了请求，随后做出回应。" * 35,
    )])[0]


def model_answer(*, decision="PASS", unsafe=False):
    return {
        "decision": decision,
        "scores": {k: 5 for k in batch.FLOORS},
        "severe_flags": {
            k: bool(unsafe and k == "serious_player_agency") for k in batch.SEVERE
        },
        "reason_cn": "局部上下文角色行动可追溯；未知完整世界设定需另行审核。",
    }


def test_endpoint_rejects_remote_by_default_and_redirect_path():
    assert ai.validate_endpoint("http://127.0.0.1:1234/v1", False) == (
        "http://127.0.0.1:1234/v1/chat/completions")
    assert ai.validate_endpoint("http://localhost:124/v1", False).startswith("http")
    with pytest.raises(ai.Hold, match="REMOTE_REVIEW_REQUIRES_EXPLICIT_HTTPS_OPT_IN"):
        ai.validate_endpoint("https://private-model.example/v1", False)
    with pytest.raises(ai.Hold, match="REMOTE_REVIEW_REQUIRES_EXPLICIT_HTTPS_OPT_IN"):
        ai.validate_endpoint("http://private-model.example/v1", True)
    assert ai.validate_endpoint("https://private-model.example/v1", True).endswith(
        "/chat/completions")
    with pytest.raises(ai.Hold, match="ENDPOINT_INVALID"):
        ai.validate_endpoint("http://localhost:123/v1?token=SECRET", False)
    with pytest.raises(ai.Hold, match="ENDPOINT_INVALID"):
        ai.validate_endpoint("http://localhost:123/v1/chat/completions", False)


def test_strict_model_schema_never_infers_flags_or_scores():
    valid = ai.parse_model_response(model_answer())
    assert valid["decision"] == "PASS"
    for bad in (
        {"decision": "PASS"},
        {**model_answer(), "reason_cn": ""},
        {**model_answer(), "scores": {"player_agency": 5}},
        {**model_answer(), "severe_flags": {"safety_exclusion": False}},
        {**model_answer(), "scores": {k: True for k in batch.FLOORS}},
        {**model_answer(), "decision": "UNKNOWN"},
    ):
        with pytest.raises(ai.Hold):
            ai.parse_model_response(bad)


def test_severe_decision_cannot_be_pass():
    with pytest.raises(ai.Hold, match="SEVERE_FLAG_DECISION_INCONSISTENT"):
        ai.parse_model_response(model_answer(unsafe=True))


def test_score_below_floor_cannot_be_pass():
    scores = {k: 5 for k in batch.FLOORS}
    scores["npc_initiative"] = 1
    with pytest.raises(ai.Hold, match="QUALITY_FLOOR_DECISION_INCONSISTENT"):
        ai.parse_model_response({**model_answer(), "scores": scores})


def test_independent_prompts_and_no_auto_owner_attestation(monkeypatch):
    calls = []

    def fake_request(endpoint, model, key, prompt, timeout, json_mode):
        calls.append((model, prompt))
        return model_answer()

    monkeypatch.setattr(ai, "model_request", fake_request)
    case = example_case()
    reviews, safe = ai.evaluate([case], [
        ("http://localhost:10/v1/chat/completions", "model-A", ""),
        ("http://localhost:11/v1/chat/completions", "model-B", ""),
    ], 180, False, False)
    assert len(calls) == 2
    assert calls[0][1] == calls[1][1]
    assert case["case_key"] not in calls[0][1]
    assert case["source"]["story_id"] not in calls[0][1]
    assert reviews[0]["reviews"][0]["reviewer_key"] != reviews[0]["reviews"][1]["reviewer_key"]
    assert reviews[0]["reviewers_independent_owner_attested"] is False
    assert safe["review_decisions"]["HOLD"] == 1
    assert safe["train_admitted"] == 0


def test_owner_attested_distinct_models_allow_quality_pass_not_training(monkeypatch):
    monkeypatch.setattr(ai, "model_request", lambda *args: model_answer())
    case = example_case()
    _, safe = ai.evaluate([case], [
        ("http://localhost:10/v1/chat/completions", "model-A", ""),
        ("http://localhost:11/v1/chat/completions", "model-B", ""),
    ], 180, False, True)
    assert safe["review_decisions"]["PASS"] == 1
    assert safe["train_admitted"] == 0
    assert safe["r50_complete_exclusion_verified"] is False
    assert safe["world_components_verified"] is False


def test_one_ai_severe_rejects_even_with_other_pass(monkeypatch):
    def fake(endpoint, model, key, prompt, timeout, json_mode):
        return model_answer(decision="REJECT", unsafe=True) if model == "model-B" else (
            model_answer())

    monkeypatch.setattr(ai, "model_request", fake)
    case = example_case()
    _, safe = ai.evaluate([case], [
        ("http://localhost:10/v1/chat/completions", "model-A", ""),
        ("http://localhost:11/v1/chat/completions", "model-B", ""),
    ], 180, False, True)
    assert safe["review_decisions"]["REJECT"] == 1
    assert safe["train_admitted"] == 0


def test_same_model_name_rejected_no_calls(monkeypatch):
    monkeypatch.setattr(ai, "model_request", lambda *args: pytest.fail("should not call"))
    with pytest.raises(ai.Hold, match="DISTINCT_MODELS_REQUIRED"):
        ai.evaluate([example_case()], [
            ("http://localhost:10/v1", "Model-Same", ""),
            ("http://localhost:11/v1", "model-same", ""),
        ], 180, False, True)


def test_source_tamper_prevents_network_calls(monkeypatch):
    monkeypatch.setattr(ai, "model_request", lambda *args: pytest.fail("should not call"))
    case = example_case()
    case["target_text"] += "篡改"
    with pytest.raises(batch.Hold, match="CAPTURE_TAMPER_HOLD"):
        ai.evaluate([case], [
            ("http://localhost:10/v1", "model-A", ""),
            ("http://localhost:11/v1", "model-B", ""),
        ], 180, False, False)


def test_private_review_output_and_nonreplay(tmp_path, monkeypatch):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(batch, "BASE", parent)
    directory = parent / "g1-pilot"
    directory.mkdir(mode=0o700)
    case = example_case()
    capture = directory / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
    capture.write_text(json.dumps(case, ensure_ascii=False) + "\n")
    os.chmod(capture, 0o600)
    monkeypatch.setattr(ai, "model_request", lambda *args: model_answer())

    safe = ai.run(directory, [
        "http://localhost:10/v1", "http://localhost:11/v1",
    ], ["A", "B"], ["TEST_UNUSED_A", "TEST_UNUSED_B"], 120, False, False, False)
    assert safe["status"] == "TWO_MODEL_AI_REVIEWED__TRAIN_ADMISSION_HOLD"
    assert safe["train_admitted"] == 0
    written = directory / ai.OUT_FILE
    assert written.stat().st_mode & 0o777 == 0o600
    assert "story-example" not in json.dumps(safe)
    assert "此前玩家" not in json.dumps(safe)
    assert len(written.read_text().splitlines()) == 1

    with pytest.raises(ai.Hold, match="AI_REVIEW_OUTPUT_EXISTS"):
        ai.run(directory, [
            "http://localhost:10/v1", "http://localhost:11/v1",
        ], ["A", "B"], ["TEST_UNUSED_A", "TEST_UNUSED_B"], 120, False, False, False)


def test_partial_model_failure_keeps_other_review_as_hold(tmp_path, monkeypatch):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(batch, "BASE", parent)
    directory = parent / "g1-pilot"
    directory.mkdir(mode=0o700)
    capture = directory / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
    capture.write_text(json.dumps(example_case(), ensure_ascii=False) + "\n")
    os.chmod(capture, 0o600)

    def network_fail(*args):
        raise ai.Hold("MODEL_TRANSPORT_HOLD")

    monkeypatch.setattr(ai, "model_request", network_fail)
    safe = ai.run(directory, [
        "http://localhost:10/v1", "http://localhost:11/v1",
    ], ["A", "B"], ["TEST_UNUSED_A", "TEST_UNUSED_B"], 120, False, False, False)
    assert safe["status"] == "TWO_MODEL_AI_REVIEW_PARTIAL_HOLD"
    assert safe["complete_two_model_responses"] == 0
    assert safe["model_attempt_hold_counts"] == {"MODEL_TRANSPORT_HOLD": 2}
    assert safe["review_decisions"] == {"PASS": 0, "HOLD": 1, "REJECT": 0}
    assert safe["train_admitted"] == 0
    data = json.loads((directory / ai.OUT_FILE).read_text().strip())
    assert data["reviews"] == []


def test_prompt_treats_text_only_as_data():
    case = example_case()
    prompt = ai.prompt_for_case(case)
    assert "prior_messages" in prompt and "assistant_target" in prompt
    assert "case_key" not in prompt and "story_id" not in prompt
    assert "以下 JSON 仅供质量评价" in prompt

def test_one_model_refusal_does_not_launder_quality_pass(monkeypatch):
    case = example_case()

    def partial(endpoint, model, key, prompt, timeout, json_mode):
        if model == "model-B":
            raise ai.Hold("MODEL_JSON_INVALID")
        return model_answer()

    monkeypatch.setattr(ai, "model_request", partial)
    reviews, safe = ai.evaluate([case], [
        ("http://localhost:10/v1", "model-A", ""),
        ("http://localhost:11/v1", "model-B", ""),
    ], 180, False, True)
    assert len(reviews[0]["reviews"]) == 1
    assert safe["model_attempt_hold_counts"] == {"MODEL_JSON_INVALID": 1}
    assert safe["review_decisions"]["PASS"] == 0
    assert safe["review_decisions"]["HOLD"] == 1
    assert safe["train_admitted"] == 0


def test_reusable_protocol_profiles_have_strict_isolated_requests():
    import r60_reviewer_transport as profiles

    kwargs = {
        "model": "synthetic-model", "prompt": "PRIVATE_FAKE_PROMPT",
        "instructions": "STATIC_RUBRIC", "json_mode": False,
    }
    claude = profiles.build_body(**kwargs, profile="claude-proxy-top-system")
    assert claude["system"] == "STATIC_RUBRIC"
    assert claude["messages"] == [{"role": "user", "content": "PRIVATE_FAKE_PROMPT"}]
    assert "temperature" not in claude
    assert "response_format" not in claude
    deepseek = profiles.build_body(**kwargs, profile="deepseek-chat")
    assert deepseek["messages"][0] == {
        "role": "system", "content": "STATIC_RUBRIC"
    }
    assert "system" not in deepseek
    assert deepseek["temperature"] == 0
    assert deepseek["thinking"] == {"type": "disabled"}
    generic = profiles.build_body(**kwargs, profile="openai-chat")
    assert generic["temperature"] == 0
    assert len(generic["messages"]) == 2
    with pytest.raises(ValueError, match="CLAUDE_PROXY_JSON_MODE_UNSUPPORTED"):
        profiles.build_body(
            **{**kwargs, "json_mode": True},
            profile="claude-proxy-top-system",
        )
    with pytest.raises(ValueError, match="REVIEW_PROTOCOL_UNSUPPORTED"):
        profiles.build_body(**kwargs, profile="unknown")
    with pytest.raises(ValueError, match="REVIEW_PROTOCOL_UNSUPPORTED"):
        profiles.require_profile({"unsafe": "type"})


def test_synthetic_probe_never_loads_private_source(monkeypatch):
    import r60_reviewer_protocol_probe as probe
    calls = []

    def fake_request(endpoint, model, key, prompt, timeout, json_mode, *,
                     protocol="openai-chat"):
        calls.append((endpoint, model, protocol, prompt))
        assert "合成测试" in prompt
        return model_answer()

    monkeypatch.setattr(ai, "model_request", fake_request)
    args = {
        "endpoint": "https://example.org/v1", "model": "claude-synthetic",
        "protocol": "claude-proxy-top-system",
        "key_env": "R60_REVIEW_A_KEY", "allow_remote": True,
        "json_mode": False,
    }
    result = probe.inspect(**args, execute=False)
    assert result["status"] == "REVIEWER_PROTOCOL_PREFLIGHT_PASS__NO_REQUEST"
    assert result["model_requests"] == 0
    assert not calls
    result = probe.inspect(**args, execute=True)
    assert result["status"] == "REVIEWER_SYNTHETIC_API_PASS__NO_PRIVATE"
    assert result["model_requests"] == 1
    assert calls[0][2] == "claude-proxy-top-system"
    assert "PRIVATE_FAKE_PROMPT" not in json.dumps(result)


def test_synthetic_probe_rejects_remote_without_explicit_opt_in():
    import r60_reviewer_protocol_probe as probe

    result = probe.inspect(
        endpoint="https://provider.example/v1", model="deepseek-synthetic",
        protocol="deepseek-chat", key_env="R60_REVIEW_B_KEY",
        allow_remote=False, json_mode=False, execute=True,
    )
    assert result["status"] == "REVIEWER_PROTOCOL_HOLD"
    assert result["reason_code"] == "REMOTE_REVIEW_REQUIRES_EXPLICIT_HTTPS_OPT_IN"
    assert result["model_requests"] == 0


def test_http_400_is_fixed_safe_error_without_raw_private_body(monkeypatch):
    import urllib.error

    class RejectingOpener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(
                "https://provider.example/path?secret=PRIVATE",
                400, "PRIVATE_ERROR_BODY", None, None,
            )

    monkeypatch.setattr(
        ai.urllib.request, "build_opener",
        lambda *args: RejectingOpener(),
    )
    with pytest.raises(ai.Hold, match="^MODEL_HTTP_400_HOLD$") as caught:
        ai.model_request(
            "https://provider.example/v1/chat/completions",
            "claude-synthetic", "", "FAKE_ONLY", 10, False,
            protocol="claude-proxy-top-system",
        )
    assert "PRIVATE" not in str(caught.value)


def test_synthetic_probe_main_parses_remote_review_flag_and_new_key(monkeypatch, capsys):
    import r60_reviewer_protocol_probe as probe

    captured = {}

    def fake_inspect(**kwargs):
        captured.update(kwargs)
        return {
            "status": "REVIEWER_PROTOCOL_PREFLIGHT_PASS__NO_REQUEST",
            "reason_code": "SYNTHETIC_REQUEST_BUILT",
            "model_requests": 0,
            "private_source_accessed": False,
        }

    monkeypatch.setattr(probe, "inspect", fake_inspect)
    monkeypatch.setattr(
        probe.sys, "argv",
        [
            "r60_reviewer_protocol_probe.py",
            "--endpoint", "https://api.deepseek.com",
            "--model", "deepseek-flash",
            "--protocol", "deepseek-chat",
            "--allow-remote-review",
        ],
    )
    assert probe.main() == 0
    assert captured["allow_remote"] is True
    assert captured["key_env"] == "R60_DEEPSEEK_KEY"
    assert captured["execute"] is False
    assert "PRIVATE" not in capsys.readouterr().out


def test_synthetic_probe_main_without_remote_flag_does_not_opt_in(monkeypatch):
    import r60_reviewer_protocol_probe as probe

    captured = {}

    def fake_inspect(**kwargs):
        captured.update(kwargs)
        return {"status": "REVIEWER_PROTOCOL_HOLD"}

    monkeypatch.setattr(probe, "inspect", fake_inspect)
    monkeypatch.setattr(
        probe.sys, "argv",
        [
            "r60_reviewer_protocol_probe.py",
            "--endpoint", "http://localhost:11434/v1",
            "--model", "claude-synthetic",
            "--protocol", "claude-proxy-top-system",
        ],
    )
    assert probe.main() == 42
    assert captured["allow_remote"] is False
    assert captured["key_env"] == "R60_CLAUDE_KEY"
    assert captured["execute"] is False
