"""Offline synthetic-only DeepSeek single-side fast review tests."""
from __future__ import annotations

import json

import pytest
import r60_real1000_deepseek_single as single
import r60_real_private_batch as private
from test_r60_real1000_offline_prefilter import candidates


def setup_case(tmp_path, monkeypatch):
    monkeypatch.setattr(private, "BASE", tmp_path)
    rows = candidates()
    old_dir = tmp_path / "r60-quality-fast1000-api-v1"
    old_dir.mkdir(mode=0o700)
    old = {
        "source": str(tmp_path / "source"),
        "model_b": single.MODEL,
        "endpoint_b": single.URL,
        "protocol_b": single.PROTOCOL,
    }
    monkeypatch.setattr(single, "old_state",
                        lambda _old: (old, rows, "synthetic-pool"))
    out = tmp_path / "r60-quality-fast1000-deepseek-single-v1"
    return old_dir, out


def reply(decision="PASS"):
    return {
        "decision": decision,
        "scores": dict(private.FLOORS),
        "severe_flags": {key: False for key in private.SEVERE},
        "reason_cn": "合成样例，仅验证评分与决定一致。",
    }


def test_init_unchanged_old_batch_and_progress(tmp_path, monkeypatch):
    old, out = setup_case(tmp_path, monkeypatch)
    safe = single.initialize(old, out)
    assert safe["single_cases_reviewed"] == 0
    assert safe["total_positions_attempted"] == 255
    assert safe["remaining_single_cases"] == 745
    assert list(old.iterdir()) == []
    assert single.verify(out, old)[2] == safe


def test_two_immutable_receipts_and_no_promotion(tmp_path, monkeypatch):
    old, out = setup_case(tmp_path, monkeypatch)
    single.initialize(old, out)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-only")
    sent = []

    def call(url, model, key, prompt, timeout, json_mode, *, protocol):
        sent.append((url, model, key, protocol))
        return reply()

    monkeypatch.setattr(single.ai, "model_request", call)
    safe = single.advance(old, out, 2, True, True)
    assert safe["single_cases_reviewed"] == 2
    assert safe["single_decisions"]["PROVISIONAL_PASS"] == 2
    assert safe["train_admitted"] == 0
    assert len(sent) == 2
    assert all(x[:2] == (single.URL, single.MODEL) for x in sent)
    assert single.verify(out, old)[2] == safe
    with pytest.raises(single.Hold, match="SINGLE_REMOTE_APPROVAL_REQUIRED"):
        single.advance(old, out, 1, False, True)


def test_auth_error_does_not_commit_receipt(tmp_path, monkeypatch):
    old, out = setup_case(tmp_path, monkeypatch)
    single.initialize(old, out)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-only")

    def call(*args, **kwargs):
        raise single.ai.Hold("MODEL_HTTP_401_HOLD")

    monkeypatch.setattr(single.ai, "model_request", call)
    with pytest.raises(single.Hold, match="DEEPSEEK_SERVICE_BLOCKED_HOLD"):
        single.advance(old, out, 5, True, True)
    assert single.verify(out, old)[2]["single_cases_reviewed"] == 0


def test_model_invalid_decision_is_technical_hold(tmp_path, monkeypatch):
    old, out = setup_case(tmp_path, monkeypatch)
    single.initialize(old, out)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-only")

    def call(*args, **kwargs):
        raise single.ai.Hold("QUALITY_FLOOR_DECISION_INCONSISTENT")

    monkeypatch.setattr(single.ai, "model_request", call)
    safe = single.advance(old, out, 1, True, True)
    assert safe["single_decisions"]["TECHNICAL_HOLD"] == 1
    assert safe["technical_hold_counts"] == {
        "QUALITY_FLOOR_DECISION_INCONSISTENT": 1,
    }
    assert json.loads((out / single.receipt_name(256)).read_text())["response"] is None


def test_tamper_fails_closed(tmp_path, monkeypatch):
    old, out = setup_case(tmp_path, monkeypatch)
    single.initialize(old, out)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-only")
    monkeypatch.setattr(single.ai, "model_request",
                        lambda *args, **kwargs: reply())
    single.advance(old, out, 1, True, True)
    record = out / single.receipt_name(256)
    obj = json.loads(record.read_text())
    obj["status"] = "PROVISIONAL_REJECT"
    record.write_text(json.dumps(obj))
    record.chmod(0o600)
    with pytest.raises(single.Hold, match="SINGLE_RECEIPT_SIGNATURE_HOLD"):
        single.verify(out, old)
