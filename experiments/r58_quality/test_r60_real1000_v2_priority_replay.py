"""Synthetic-only V2 priority replay: no real model calls or private inputs."""
from __future__ import annotations

import json

import pytest
import r60_real1000_v2_priority_replay as v2
import r60_real_private_batch as private


def source(i):
    return {"case_key": f"synthetic-{i}",
            "history_messages_sha256": f"history-{i}",
            "assistant_target_sha256": f"target-{i}"}


def answer():
    return {"decision": "PASS", "scores": dict(private.FLOORS),
            "severe_flags": {name: False for name in private.SEVERE},
            "reason_cn": "仅测试结果结构。"}


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(private, "BASE", tmp_path)
    old = tmp_path / "old"
    plan = tmp_path / "plan"
    old.mkdir(mode=0o700)
    plan.mkdir(mode=0o700)
    out = tmp_path / "r60-real1000-v2-priority-replay-synthetic"
    selected = [
        {"position": 2,
         "original_receipt_sha256": "v1-receipt-2",
         "missing_slots": [{"side": "a"}]},
        {"position": 3,
         "original_receipt_sha256": "v1-receipt-3",
         "missing_slots": [{"side": "b"}]},
    ]
    cfg = {
        "pool_sha256": "synthetic-pool",
        "model_a": "qwen3.7-flash", "model_b": "deepseek-flash",
        "endpoint_a": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "endpoint_b": "https://api.deepseek.com/chat/completions",
        "protocol_a": "openai-chat",
        "protocol_b": "deepseek-chat",
        "timeout": 180,
        "json_mode": False,
    }
    monkeypatch.setattr(v2, "_plan_state", lambda _o, _p: (
        cfg, [source(1), source(2), source(3)], selected,
        b"frozen-plan-fixture"))
    monkeypatch.setattr(v2.ai, "prompt_for_case",
                        lambda case: "synthetic prompt")
    return old, plan, out


def test_init_inspect_no_requests(tmp_path, monkeypatch):
    old, plan, out = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(v2.ai, "model_request",
                        lambda *a, **kw: pytest.fail("network forbidden"))
    s = v2.initialize(out, old, plan)
    assert s["planned_slots"] == 2
    assert s["reviewed_slots"] == 0
    assert s["remaining_slots"] == 2
    assert v2.inspect(out, old, plan) == s
    assert not list(old.iterdir())


def test_missing_only_and_resumable(tmp_path, monkeypatch):
    old, plan, out = setup(tmp_path, monkeypatch)
    v2.initialize(out, old, plan)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "synthetic-qwen")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-deepseek")
    calls = []

    def request(endpoint, model, key, prompt, timeout, json_mode, *, protocol):
        calls.append((model, key, protocol))
        return answer()

    monkeypatch.setattr(v2.ai, "model_request", request)
    s = v2.advance(out, old, plan, 1, execute=True,
                   allow_private_data_egress=True)
    assert s["reviewed_slots"] == 1
    assert s["result_counts"] == {"V2_PASS": 1}
    s = v2.advance(out, old, plan, 1, execute=True,
                   allow_private_data_egress=True)
    assert s["status"] == "V2_PRIORITY_REPLAY_COMPLETE__NO_ADMISSION"
    assert calls == [
        ("qwen3.7-flash", "synthetic-qwen", "openai-chat"),
        ("deepseek-flash", "synthetic-deepseek", "deepseek-chat"),
    ]
    assert s["train_admitted"] == 0
    assert len(list(out.glob("R60_V2_REPLAY_*_PRIVATE.json"))) == 2


def test_outage_does_not_commit(tmp_path, monkeypatch):
    old, plan, out = setup(tmp_path, monkeypatch)
    v2.initialize(out, old, plan)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "synthetic")

    def outage(*args, **kwargs):
        raise v2.ai.Hold("MODEL_HTTP_401_HOLD")

    monkeypatch.setattr(v2.ai, "model_request", outage)
    with pytest.raises(v2.Hold, match="V2_REVIEWER_SERVICE_UNAVAILABLE_HOLD"):
        v2.advance(out, old, plan, 2, execute=True,
                   allow_private_data_egress=True)
    assert v2.inspect(out, old, plan)["reviewed_slots"] == 0


def test_technical_error_saved_and_tamper_blocked(tmp_path, monkeypatch):
    old, plan, out = setup(tmp_path, monkeypatch)
    v2.initialize(out, old, plan)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "synthetic")

    def malformed(*args, **kwargs):
        raise v2.ai.Hold("QUALITY_FLOOR_DECISION_INCONSISTENT")

    monkeypatch.setattr(v2.ai, "model_request", malformed)
    state = v2.advance(out, old, plan, 1, execute=True,
                       allow_private_data_egress=True)
    assert state["result_counts"] == {"TECHNICAL_HOLD": 1}
    path = out / v2.receipt_name(1)
    record = json.loads(path.read_text())
    assert record["result"] is None
    record["side"] = "b"
    path.write_text(json.dumps(record))
    path.chmod(0o600)
    with pytest.raises(v2.Hold, match="V2_CASE_BINDING_HOLD"):
        v2.inspect(out, old, plan)


def test_execute_flags_required(tmp_path, monkeypatch):
    old, plan, out = setup(tmp_path, monkeypatch)
    v2.initialize(out, old, plan)
    with pytest.raises(v2.Hold, match="V2_EXPLICIT_EXECUTION_REQUIRED"):
        v2.advance(out, old, plan, 1, execute=False,
                   allow_private_data_egress=False)
