"""Offline tests for the real 20-case Qwen/DeepSeek API runner."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/r58_quality"))
import r60_real1000_qwen_deepseek20_live as live


def fake_config():
    return live.config_payload(
        "a" * 64,
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen3.7-flash",
        "https://api.deepseek.com",
        "deepseek-flash",
    )


def fake_answer(decision="HOLD"):
    return {
        "decision": decision,
        "scores": {k: 4 for k in live.private.FLOORS},
        "severe_flags": {k: False for k in live.private.SEVERE},
        "reason_cn": "证据不足，保持待定。",
    }


def test_config_rejects_untrusted_hosts():
    for qwen in (
        "https://dashscope.aliyuncs.com.evil.org/compatible-mode/v1",
        "https://attacker.aliyuncs.com/compatible-mode/v1",
    ):
        try:
            live.config_payload("a" * 64, qwen, "qwen3.7-flash",
                                "https://api.deepseek.com", "deepseek-flash")
        except live.Hold as exc:
            assert str(exc) == "MODEL_OR_ENDPOINT_HOLD"
        else:
            raise AssertionError("untrusted Qwen API host accepted")


def test_resume_keeps_prior_receipts_without_model_calls(monkeypatch, tmp_path):
    cfg = fake_config()
    monkeypatch.setattr(live, "load_input", lambda p: (
        {"packets_sha256": "a" * 64},
        {"packets": [{
            "history_messages": [
                {"role": "user", "content": "一"},
                {"role": "assistant", "content": "二"},
                {"role": "user", "content": "三"},
            ], "assistant_target": "四" * 340,
        } for _ in range(20)]}, {}))
    monkeypatch.setattr(live.private, "private_dir",
                        lambda path, create: Path(path).mkdir(
                            exist_ok=create) if create else None)
    monkeypatch.setattr(live.private, "read_private",
                        lambda path, max_bytes: Path(path).read_bytes())
    monkeypatch.setattr(live.private, "write_new",
                        lambda path, data: Path(path).write_bytes(data))
    monkeypatch.setenv("DASHSCOPE_API_KEY", "fake-qwen")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-deepseek")

    calls = []
    def model_call(endpoint, model, provider, key, prompt, timeout, json_mode):
        calls.append((model, provider))
        return fake_answer()

    monkeypatch.setattr(live, "call_provider", model_call)
    args = argparse.Namespace(
        command="init", review_dir=tmp_path, output_dir=tmp_path / "out",
        qwen_url=live.DEFAULT_URLS["qwen"],
        qwen_model=live.DEFAULT_MODELS["qwen"],
        deepseek_url=live.DEFAULT_URLS["deepseek"],
        deepseek_model=live.DEFAULT_MODELS["deepseek"],
        authorize_remote_private_review=False, max_calls=40,
        timeout=60, json_mode=False,
    )
    first = live.execute(args)
    assert first["complete_provider_reviews"] == 0
    assert calls == []
    args.command = "run"
    args.authorize_remote_private_review = True
    args.max_calls = 2
    second = live.execute(args)
    assert second["complete_provider_reviews"] == 2
    assert second["complete_two_provider_pairs"] == 1
    assert len(calls) == 2
    third = live.execute(args)
    assert third["complete_provider_reviews"] == 4
    assert third["complete_two_provider_pairs"] == 2
    assert len(calls) == 4
    args.command = "inspect"
    report = live.execute(args)
    assert report["complete_provider_reviews"] == 4
    assert report["model_inference_calls_this_run"] == 0
    assert cfg["reviewer_configs"]["deepseek"]["model"] == "deepseek-flash"


def test_deepseek_call_disables_thinking(monkeypatch):
    class Reply:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, n):
            return json.dumps({
                "choices": [{"message": {
                    "content": json.dumps(fake_answer(), ensure_ascii=False)
                }}],
            }).encode()

    class Opener:
        def open(self, request, timeout):
            body = json.loads(request.data)
            assert body["thinking"] == {"type": "disabled"}
            assert body["model"] == "deepseek-flash"
            return Reply()

    monkeypatch.setattr(live.urllib.request, "build_opener",
                        lambda *x: Opener())
    answer = live.call_provider(
        "https://api.deepseek.com/chat/completions",
        "deepseek-flash", "deepseek", "fake", "test prompt", 50, True)
    assert answer["decision"] == "HOLD"


def test_receipt_tamper_rejected(monkeypatch, tmp_path):
    cfg = fake_config()
    p = tmp_path / live.receipt_name(1, "qwen")
    row = {
        "schema": live.RECEIPT_SCHEMA,
        "packets_sha256": cfg["packets_sha256"],
        "position": 1,
        "provider": "qwen",
        "model": "qwen3.7-flash",
        "result": fake_answer(),
        "sha256": "tampered",
    }
    p.write_text(json.dumps(row))
    monkeypatch.setattr(live.private, "read_private",
                        lambda path, max_bytes: Path(path).read_bytes())
    try:
        live.read_receipts(tmp_path, cfg)
    except live.Hold as exc:
        assert str(exc) == "RECEIPT_BINDING_HOLD"
    else:
        raise AssertionError("tampered model receipt accepted")
