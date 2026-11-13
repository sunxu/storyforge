"""Synthetic-only tests of explicit, immutable Pilot5 replay runner."""
from __future__ import annotations

import json

import r60_pilot5_v2_replay_execute as runner


def setup(tmp_path, monkeypatch):
    output = tmp_path / "private"
    output.mkdir(mode=0o700)
    quality_dir = tmp_path / "v1"
    quality_dir.mkdir()
    case = {
        "history_messages": [
            {"role": "user", "content": "synthetic first"},
            {"role": "assistant", "content": "synthetic second"},
            {"role": "user", "content": "synthetic third"},
        ],
        "target_text": "synthetic candidate",
    }
    slots = [
        {"position": 1, "side": "b", "model_id": "deepseek",
         "protocol": "deepseek-chat",
         "original_receipt_sha256": "r1", "history_messages_sha256": "h1",
         "assistant_target_sha256": "t1", "original_failure": "MODEL_JSON_INVALID"},
        {"position": 3, "side": "a", "model_id": "claude",
         "protocol": "claude-proxy-top-system",
         "original_receipt_sha256": "r3", "history_messages_sha256": "h3",
         "assistant_target_sha256": "t3", "original_failure": "MODEL_JSON_INVALID"},
        {"position": 3, "side": "b", "model_id": "deepseek",
         "protocol": "deepseek-chat",
         "original_receipt_sha256": "r3", "history_messages_sha256": "h3",
         "assistant_target_sha256": "t3", "original_failure": "MODEL_JSON_INVALID"},
    ]
    config = {
        "allow_remote": True, "timeout": 120, "json_mode": False,
        "model_a": "claude", "model_b": "deepseek",
        "protocol_a": "claude-proxy-top-system",
        "protocol_b": "deepseek-chat",
        "endpoint_a": "https://synthetic.example/v1/chat/completions",
        "endpoint_b": "https://synthetic.example/v1/chat/completions",
    }
    monkeypatch.setattr(runner, "verify",
                        lambda q, d: (config, [case, case, case], slots))
    monkeypatch.setenv("R60_CLAUDE_KEY", "test-key-a")
    monkeypatch.setenv("R60_DEEPSEEK_KEY", "test-key-b")
    return quality_dir, output, slots


def test_default_preflight_never_calls_models(tmp_path, monkeypatch):
    quality_dir, output, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(runner.ai, "model_request", lambda *a, **kw:
                        (_ for _ in ()).throw(AssertionError("API was invoked")))
    safe = runner.run(quality_dir, output, execute=False,
                      allow_private_data_egress=False, max_requests=3)
    assert safe["status"] == "PILOT5_V2_REPLAY_PREFLIGHT_PASS__NO_REQUEST"
    assert safe["planned_slots"] == 3
    assert safe["model_requests"] == 0
    assert safe["train_admitted"] == 0


def test_no_explicit_egress_never_calls_models(tmp_path, monkeypatch):
    quality_dir, output, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(runner.ai, "model_request", lambda *a, **kw:
                        (_ for _ in ()).throw(AssertionError("API was invoked")))
    safe = runner.run(quality_dir, output, execute=True,
                      allow_private_data_egress=False, max_requests=3)
    assert safe["status"] == "PILOT5_V2_REPLAY_HOLD"
    assert safe["model_requests"] == 0


def test_only_three_failed_slots_and_resume_skips_written(tmp_path, monkeypatch):
    quality_dir, output, slots = setup(tmp_path, monkeypatch)
    calls = []

    def fake_api(endpoint, model, key, prompt, timeout, json_mode, *, protocol):
        calls.append((model, protocol))
        return {
            "decision": "HOLD",
            "scores": {k: 3 for k in runner.private.FLOORS},
            "severe_flags": {k: False for k in runner.private.SEVERE},
            "reason_cn": "synthetic test only",
        }

    monkeypatch.setattr(runner.ai, "model_request", fake_api)
    safe = runner.run(quality_dir, output, execute=True,
                      allow_private_data_egress=True, max_requests=2)
    assert safe["status"] == "PILOT5_V2_REPLAY_ATTEMPTS_SAVED__NO_PROMOTION"
    assert safe["model_requests"] == 2
    assert calls == [("deepseek", "deepseek-chat"),
                     ("claude", "claude-proxy-top-system")]
    first_path = runner.receipt_file(output, 1, "b")
    original = first_path.read_bytes()
    assert first_path.stat().st_mode & 0o777 == 0o600
    second = runner.run(quality_dir, output, execute=True,
                        allow_private_data_egress=True, max_requests=3)
    assert second["model_requests"] == 1
    assert second["successes"] == 1
    assert first_path.read_bytes() == original
    assert len(calls) == 3
    assert all(runner.receipt_file(output, s["position"], s["side"]).exists()
               for s in slots)
    third = runner.run(quality_dir, output, execute=True,
                       allow_private_data_egress=True, max_requests=3)
    assert third["model_requests"] == 0
    assert len(calls) == 3


def test_failed_request_still_generates_immutable_private_hold(
        tmp_path, monkeypatch):
    quality_dir, output, _ = setup(tmp_path, monkeypatch)

    def fake_api(*args, **kwargs):
        raise runner.ai.Hold("MODEL_JSON_INVALID")

    monkeypatch.setattr(runner.ai, "model_request", fake_api)
    safe = runner.run(quality_dir, output, execute=True,
                      allow_private_data_egress=True, max_requests=1)
    assert safe["attempt_holds"] == 1
    row = json.loads(runner.receipt_file(output, 1, "b").read_text())
    assert row["attempt_status"] == "HOLD"
    assert row["failure_code"] == "MODEL_JSON_INVALID"
    assert row["review"] is None
    assert row["train_admitted"] == 0
    second = runner.run(quality_dir, output, execute=True,
                        allow_private_data_egress=True, max_requests=1)
    assert second["already_recorded_slots"] == 1
    assert runner.receipt_file(output, 1, "b").read_bytes()


def test_invalid_budget_prevents_network(tmp_path, monkeypatch):
    quality_dir, output, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(runner.ai, "model_request", lambda *a, **kw:
                        (_ for _ in ()).throw(AssertionError("API was invoked")))
    assert runner.run(quality_dir, output, execute=True,
                      allow_private_data_egress=True,
                      max_requests=5)["status"] == "PILOT5_V2_REPLAY_HOLD"
