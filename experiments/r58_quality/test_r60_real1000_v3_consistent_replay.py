"""Synthetic tests for isolated V3 strict-B replay. No internet or private text."""
from __future__ import annotations

import json

import pytest
import r60_real1000_v3_consistent_replay as v3
import r60_real_private_batch as private


def _source(position):
    return {
        "case_key": f"synthetic-{position}",
        "history_messages_sha256": f"history-{position}",
        "assistant_target_sha256": f"target-{position}",
    }


def fixture_state(tmp_path, monkeypatch):
    monkeypatch.setattr(private, "BASE", tmp_path)
    old = tmp_path / "old"
    plan = tmp_path / "plan"
    v2 = tmp_path / "v2"
    for p in (old, plan, v2):
        p.mkdir(mode=0o700)
    out = tmp_path / "r60-real1000-v3-consistent-replay-synthetic"
    cases = [_source(i) for i in range(1, 4)]
    cfg = {
        "pool_sha256": "source-sha",
        "model_a": "qwen3.7-flash", "model_b": "deepseek-flash",
        "endpoint_a": "https://example.org/qwen/chat/completions",
        "endpoint_b": "https://example.org/deepseek/chat/completions",
        "protocol_a": "openai-chat",
        "protocol_b": "deepseek-chat",
        "timeout": 60, "json_mode": False,
    }
    queue = [
        {
            "position": 2, "v2_ordinal": 2, "side": "b",
            **cases[1],
            "v1_receipt_sha256": "v1-2",
            "v2_receipt_sha256": "v2-2",
            "source_status": "V2_TECHNICAL_HOLD",
            "v2_reason_code": "QUALITY_FLOOR_DECISION_INCONSISTENT",
        },
        {
            "position": 3, "v2_ordinal": 3, "side": "a",
            **cases[2],
            "v1_receipt_sha256": "v1-3",
            "v2_receipt_sha256": None,
            "source_status": "V2_UNREVIEWED",
            "v2_reason_code": None,
        },
    ]
    fingerprint = {
        "v1_source_sha256": "source-sha",
        "v2_completed": 2,
        "v2_receipt_chain_sha256": "fixture-chain",
        "v3_queue_sha256": private.digest(queue),
        "planned_slots": 2,
        "strict_b_instruction_sha256": "fixture-instruction",
    }
    monkeypatch.setattr(v3, "source_state", lambda *args: (
        cfg, cases, queue, fingerprint
    ))
    monkeypatch.setattr(v3.ai, "prompt_for_case",
                        lambda case: "synthetic-only")
    return old, plan, v2, out


def _answer():
    return {
        "decision": "PASS",
        "scores": dict(private.FLOORS),
        "severe_flags": {name: False for name in private.SEVERE},
        "reason_cn": "合成数据，满足六维门槛。",
    }


def test_init_and_inspect_never_call_api(tmp_path, monkeypatch):
    old, plan, v2dir, out = fixture_state(tmp_path, monkeypatch)
    monkeypatch.setattr(v3.ai, "model_request",
                        lambda *a, **kw: pytest.fail("unexpected API"))
    result = v3.initialize(out, old, plan, v2dir)
    assert result["planned_slots"] == 2
    assert result["reviewed_slots"] == 0
    assert result["v2_receipts_preserved"] == 2
    assert v3.inspect(out, old, plan, v2dir) == result


def test_strict_b_only_and_successful_resume(tmp_path, monkeypatch):
    old, plan, v2dir, out = fixture_state(tmp_path, monkeypatch)
    v3.initialize(out, old, plan, v2dir)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "fake-qwen")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-deepseek")
    calls = []

    def request(endpoint, model, key, prompt, timeout, json_mode, *,
                protocol, instructions):
        calls.append((model, key, instructions))
        return _answer()

    monkeypatch.setattr(v3.ai, "model_request", request)
    result = v3.advance(
        out, old, plan, v2dir, 1, execute=True,
        allow_private_data_egress=True)
    assert result["reviewed_slots"] == 1
    assert calls[0] == ("deepseek-flash", "fake-deepseek",
                        v3.ai.REVIEW_INSTRUCTIONS_V3_CONSISTENT)
    result = v3.advance(
        out, old, plan, v2dir, 1, execute=True,
        allow_private_data_egress=True)
    assert calls[1] == ("qwen3.7-flash", "fake-qwen",
                        v3.ai.REVIEW_INSTRUCTIONS)
    assert result["status"] == "V3_CONSISTENT_REPLAY_COMPLETE__NO_ADMISSION"
    assert result["result_counts"] == {"V3_PASS": 2}
    assert result["train_admitted"] == 0


def test_holds_prevent_overwrite_or_api_replay(tmp_path, monkeypatch):
    old, plan, v2dir, out = fixture_state(tmp_path, monkeypatch)
    v3.initialize(out, old, plan, v2dir)
    with pytest.raises(v3.Hold, match="V3_EXPLICIT_EXECUTION_REQUIRED"):
        v3.advance(out, old, plan, v2dir, 1)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-deepseek")

    def fail(*a, **kw):
        raise v3.ai.Hold("MODEL_HTTP_401_HOLD")

    monkeypatch.setattr(v3.ai, "model_request", fail)
    with pytest.raises(v3.Hold, match="V3_SERVICE_UNAVAILABLE_HOLD"):
        v3.advance(out, old, plan, v2dir, 1, execute=True,
                   allow_private_data_egress=True)
    assert v3.inspect(out, old, plan, v2dir)["reviewed_slots"] == 0


def test_tampered_receipt_detected(tmp_path, monkeypatch):
    old, plan, v2dir, out = fixture_state(tmp_path, monkeypatch)
    v3.initialize(out, old, plan, v2dir)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-deepseek")
    monkeypatch.setattr(v3.ai, "model_request",
                        lambda *a, **kw: _answer())
    v3.advance(out, old, plan, v2dir, 1,
               execute=True, allow_private_data_egress=True)
    path = out / v3.receipt_name(1)
    content = json.loads(path.read_text())
    content["side"] = "a"
    path.write_text(json.dumps(content))
    path.chmod(0o600)
    with pytest.raises(v3.Hold, match="V3_CASE_BINDING_HOLD"):
        v3.inspect(out, old, plan, v2dir)


def test_config_drift_detected(tmp_path, monkeypatch):
    old, plan, v2dir, out = fixture_state(tmp_path, monkeypatch)
    v3.initialize(out, old, plan, v2dir)
    cfg = json.loads((out / v3.CONFIG).read_text())
    cfg["v2_completed"] = 999
    (out / v3.CONFIG).write_text(json.dumps(cfg))
    (out / v3.CONFIG).chmod(0o600)
    with pytest.raises(v3.Hold, match="V3_SOURCE_OR_CONFIG_DRIFT_HOLD"):
        v3.inspect(out, old, plan, v2dir)
