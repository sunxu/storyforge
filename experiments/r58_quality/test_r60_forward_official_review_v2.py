"""Synthetic-only Reviewer V2: source precondition, real client mock, no network."""
import json
import stat

import pytest
import r60_forward_official_review_v2 as target
from test_r60_forward_evidence_gate_v1 import protection, source, world

H = "a" * 64


def bundle():
    case = {
        "history_messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "早上好"},
            {"role": "user", "content": "出发吗"},
        ],
        "target_text": "一起出发。",
    }
    original = source()
    original.update({
        "case_sha256": target.private.digest(case),
        "history_sha256": target.private.digest(case["history_messages"]),
        "target_sha256": target.private.digest(case["target_text"]),
    })
    protected, components = protection(), world()
    protected["case_sha256"] = original["case_sha256"]
    components["case_sha256"] = original["case_sha256"]
    return {
        "schema": target.INPUT_SCHEMA, "source": original,
        "protection": protected, "world": components, "case": case,
    }


def response():
    return {
        "decision": "PASS",
        "scores": {
            "chinese_prose": 4, "character_consistency": 4,
            "npc_initiative": 3, "player_agency": 4,
            "rule_fidelity": 4, "narrative_continuity": 4,
        },
        "severe_flags": {
            "serious_player_agency": False, "hard_fact_or_ban": False,
            "safety_exclusion": False,
        },
        "reason_cn": "完全合成审核",
    }


def setup(monkeypatch, tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(target.private, "BASE", root)
    return root / "forward-test"


def test_preflight_no_network_no_files(monkeypatch, tmp_path):
    dest = setup(monkeypatch, tmp_path)
    out = target.run(bundle(), dest, execute=False,
                     allow_remote_private_review=False)
    assert out["status"] == "FORWARD_OFFICIAL_V2_PREFLIGHT__NO_REQUEST"
    assert out["model_requests"] == 0
    assert not dest.exists()


@pytest.mark.parametrize(("section", "key"), [
    ("source", "historical_cutoff_verified"),
    ("protection", "covers_all_protected_sets"),
    ("world", "semantic_components_adjudicated"),
])
def test_missing_pre_review_guards_zero_requests(monkeypatch, tmp_path, section, key):
    dest = setup(monkeypatch, tmp_path)
    value = bundle()
    value[section][key] = False
    calls = []
    with pytest.raises(target.gate.Hold):
        target.run(
            value, dest, execute=True, allow_remote_private_review=True,
            model_request=lambda *args, **kwargs: calls.append(1))
    assert not calls
    assert not dest.exists()


def test_case_changed_rejected_before_request(monkeypatch, tmp_path):
    dest = setup(monkeypatch, tmp_path)
    value = bundle()
    value["case"]["target_text"] += "已篡改"
    with pytest.raises(target.Hold, match="SOURCE_CONTENT_BINDING_HOLD"):
        target.run(value, dest, execute=True, allow_remote_private_review=True)
    assert not dest.exists()


def test_real_client_mock_observations_no_training(monkeypatch, tmp_path):
    dest = setup(monkeypatch, tmp_path)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "synthetic-test-a")
    monkeypatch.setenv("R60_DEEPSEEK_KEY", "synthetic-test-b")
    seen = []

    def fake(url, model, key, prompt, timeout, json_mode, **kwargs):
        side = len(seen)
        assert (dest / "PRE_REVIEW_SEAL_PRIVATE.json").exists()
        assert (dest / ("REQUEST_A_PRIVATE.json" if side == 0
                           else "REQUEST_B_PRIVATE.json")).exists()
        assert "严重标志" in kwargs["instructions"]
        assert (model, kwargs["protocol"]) in (
            ("qwen3.7-flash", "openai-chat"),
            ("deepseek-flash", "deepseek-chat"),
        )
        assert "synthetic-test-" in key
        assert "完全合成审核" not in prompt
        kwargs["evidence_sink"]({
            "provider_response_id_observed": "mock-server-123456",
            "provider_evidence_authenticated": False,
        })
        seen.append(model)
        return response()

    out = target.run(
        bundle(), dest, execute=True, allow_remote_private_review=True,
        model_request=fake)
    assert seen == ["qwen3.7-flash", "deepseek-flash"]
    assert out["model_requests"] == 2
    assert out["schema_valid_reviews"] == 2
    assert out["train_admitted"] == 0
    assert out["provider_execution_independence_verified"] is False
    assert len(list(dest.iterdir())) == 5
    assert all(stat.S_IMODE(f.stat().st_mode) == 0o600 for f in dest.iterdir())
    for side in ("A", "B"):
        doc = json.loads((dest / f"OUTCOME_{side}_PRIVATE.json").read_text())
        assert doc["provider_evidence_authenticated"] is False
        assert "synthetic-test" not in json.dumps(doc)
    with pytest.raises(target.Hold, match="CREATE_ONLY_HOLD"):
        target.run(bundle(), dest, execute=True,
                   allow_remote_private_review=True, model_request=fake)
    assert len(seen) == 2


def test_deepseek_floor_hold_does_not_emit_pass_or_retry(monkeypatch, tmp_path):
    dest = setup(monkeypatch, tmp_path)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "synthetic-test-a")
    monkeypatch.setenv("R60_DEEPSEEK_KEY", "synthetic-test-b")
    called = []

    def fake(url, model, key, prompt, timeout, json_mode, **kwargs):
        called.append(model)
        kwargs["evidence_sink"]({
            "provider_evidence_authenticated": False,
            "provider_response_id_observed": "sample-123456",
        })
        if len(called) == 1:
            raise target.ai.Hold("QUALITY_FLOOR_DECISION_INCONSISTENT")
        return response()

    out = target.run(bundle(), dest, execute=True,
                     allow_remote_private_review=True, model_request=fake)
    assert called == ["qwen3.7-flash"]
    assert out["schema_valid_reviews"] == 0
    assert out["train_admitted"] == 0
    recorded = json.loads((dest / "OUTCOME_A_PRIVATE.json").read_text())
    assert recorded["reason_code"] == "QUALITY_FLOOR_DECISION_INCONSISTENT"
    assert not (dest / "REQUEST_B_PRIVATE.json").exists()


def test_no_provider_call_without_explicit_opt_in(monkeypatch, tmp_path):
    dest = setup(monkeypatch, tmp_path)
    with pytest.raises(target.Hold, match="REMOTE_REVIEW_OPT_IN_REQUIRED_HOLD"):
        target.run(bundle(), dest, execute=True,
                   allow_remote_private_review=False)
    assert not dest.exists()
