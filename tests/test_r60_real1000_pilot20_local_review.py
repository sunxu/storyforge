"""CPU synthetic tests for the explicit-egress 4Router Claude pilot20."""
from __future__ import annotations

import importlib.util
import io
import json
import socket
import ssl
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "experiments/r58_quality"
sys.path.insert(0, str(SRC))
SPEC = importlib.util.spec_from_file_location(
    "r60_real1000_pilot20_local_review",
    SRC / "r60_real1000_pilot20_local_review.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def packet_fixture():
    packets = []
    bins = (["300_499"] * 11 + ["500_999"] * 8 + ["1000_1500"])
    length = {"300_499": 350, "500_999": 750, "1000_1500": 1100}
    for i, group in enumerate(bins, 1):
        packets.append({
            "pilot_position": i,
            "sample100_position": i,
            "target_char_bin": group,
            "history_messages": [
                {"role": "user", "content": "我打开门。"},
                {"role": "assistant", "content": "门外有人。"},
                {"role": "user", "content": "继续。"},
            ],
            "assistant_target": "中" * length[group],
            "human_reference_status": "NOT_ADJUDICATED",
            "model_quality_status": "NOT_REVIEWED",
        })
    return {
        "schema": mod.pilot.SCHEMA,
        "status": "PILOT20_PACKETS_PRIVATE__NOT_REVIEWED",
        "sample100_binding": "RECOMPUTED_EXACT",
        "packets": packets,
        "quality_review_performed": False,
        "train_admitted": 0,
    }


def setup_private(monkeypatch, tmp_path):
    monkeypatch.setattr(mod.private, "private_dir",
                        lambda path, create: path.mkdir(exist_ok=False)
                        if create else None)
    monkeypatch.setattr(mod.private, "read_private",
                        lambda path, limit: path.read_bytes())
    monkeypatch.setattr(mod.private, "write_new",
                        lambda path, value: path.write_bytes(value))
    packets_dir = tmp_path / "packets"
    packets_dir.mkdir()
    (packets_dir / mod.pilot.FILENAME).write_bytes(
        mod.canonical(packet_fixture()))
    return packets_dir


def model_answer():
    return {
        "decision": "REJECT",
        "scores": {
            "chinese_prose": 3, "character_consistency": 3,
            "npc_initiative": 3, "player_agency": 3,
            "rule_fidelity": 3, "narrative_continuity": 3,
        },
        "severe_flags": {
            "serious_player_agency": True, "hard_fact_or_ban": False,
            "safety_exclusion": False,
        },
        "reason_cn": "仅作为本地合成测试。",
    }


def test_local_resume_and_advisory_only(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    calls = []
    def fake_request(*args):
        calls.append(1)
        return model_answer()
    monkeypatch.setattr(mod, "proxy_request", fake_request)
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic-key")
    folder = tmp_path / "output"
    result = mod.initialize(packets_dir, folder, "https://api.4router.ai/v1",
                            "claude-opus-5-5", 30)
    assert result["model_reviewed"] == 0
    result = mod.advance(
        folder, 5, execute=True, allow_private_data_egress=True,
    )
    assert result["model_reviewed"] == 5
    assert result["model_decisions_advisory"]["REJECT"] == 5
    assert result["quality_v1_admitted"] == 0
    result = mod.advance(
        folder, 5, execute=True, allow_private_data_egress=True,
    )
    assert result["model_reviewed"] == 10
    assert len(calls) == 10
    assert mod.get_state(folder)[2]["model_reviewed"] == 10


def test_failed_model_does_not_write_receipt(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    folder = tmp_path / "out"
    mod.initialize(packets_dir, folder, "https://api.4router.ai/v1",
                   "claude-opus-5-5", 20)
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic-key")
    def fail(*args):
        raise mod.reviewer.Hold("MODEL_TRANSPORT_HOLD")
    monkeypatch.setattr(mod, "proxy_request", fail)
    try:
        mod.advance(
            folder, 1, execute=True, allow_private_data_egress=True,
        )
    except mod.reviewer.Hold:
        pass
    else:
        raise AssertionError("expected reviewer failure")
    assert mod.get_state(folder)[2]["model_reviewed"] == 0


def test_tampered_packet_rejected(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    folder = tmp_path / "out"
    mod.initialize(packets_dir, folder, "https://api.4router.ai/v1",
                   "claude-opus-5-5", 20)
    p = packets_dir / mod.pilot.FILENAME
    p.write_bytes(p.read_bytes() + b" ")
    try:
        mod.get_state(folder)
    except mod.Hold:
        return
    raise AssertionError("expected packet binding failure")


def test_unapproved_remote_host_refused(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    try:
        mod.initialize(packets_dir, tmp_path / "out", "https://example.com/v1",
                       "claude-opus-5-5", 20)
    except mod.Hold:
        return
    raise AssertionError("expected endpoint rejection")


def test_prior_claude_system_contract():
    payload = mod.claude_payload("claude-opus-5-5", "private sample")
    assert payload["messages"] == [{"role": "user", "content": "private sample"}]
    assert payload["system"] == mod.reviewer.REVIEW_INSTRUCTIONS
    assert "temperature" not in payload
    assert "response_format" not in payload
    assert payload["stream"] is False


def test_explicit_egress_flags_required(monkeypatch, tmp_path):
    packet_dir = setup_private(monkeypatch, tmp_path)
    folder = tmp_path / "out"
    mod.initialize(packet_dir, folder, "https://api.4router.ai/v1",
                   "claude-opus-5-5", 20)
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic-key")
    try:
        mod.advance(folder, 1, execute=False, allow_private_data_egress=True)
    except mod.Hold:
        pass
    else:
        raise AssertionError("expected consent HOLD")
    assert mod.get_state(folder)[2]["model_reviewed"] == 0


def test_proxy_path_rejects_credentials_and_http():
    for bad in ("http://api.4router.ai/v1",
                "https://secret@api.4router.ai/v1",
                "https://api.4router.ai/v1?key=secret",
                "https://api.4router.ai.evil.example/v1"):
        try:
            mod.proxy_endpoint(bad)
        except mod.Hold:
            continue
        raise AssertionError("invalid 4Router endpoint accepted")


def test_safe_reason_code_allowlist_never_echoes_secrets():
    assert mod.safe_reason_code(mod.Hold("PROXY_API_KEY_REQUIRED")) == (
        "PROXY_API_KEY_REQUIRED"
    )
    assert mod.safe_reason_code(mod.Hold("private data or token secret")) == (
        "REVIEW_CONTRACT_HOLD"
    )
    assert mod.safe_reason_code(FileNotFoundError("private/path")) == (
        "PRIVATE_FILE_MISSING_HOLD"
    )


def test_only_dedicated_4router_key_authorizes_calls(monkeypatch, tmp_path):
    packet_dir = setup_private(monkeypatch, tmp_path)
    folder = tmp_path / "out"
    mod.initialize(packet_dir, folder, "https://api.4router.ai/v1",
                   "claude-opus-5-5", 20)
    monkeypatch.delenv("CLI_PROXY_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-router-key")
    try:
        mod.advance(folder, 1, execute=True, allow_private_data_egress=True)
    except mod.Hold as exc:
        assert str(exc) == "PROXY_API_KEY_REQUIRED"
    else:
        raise AssertionError("must require dedicated Router key")
    assert mod.get_state(folder)[2]["model_reviewed"] == 0


def test_http_error_status_and_provider_category():
    def error(code, body):
        return urllib.error.HTTPError(
            "https://api.4router.ai/v1/chat/completions", code, "error", {},
            io.BytesIO(json.dumps(body).encode()),
        )
    assert mod.safe_http_code(error(
        400, {"error": {"type": "invalid_request_error", "message": "secret"}},
    )) == "PROXY_HTTP_400_INVALID_REQUEST_HOLD"
    assert mod.safe_http_code(error(
        401, {"error": {"type": "authentication_error", "message": "secret"}},
    )) == "PROXY_HTTP_401_AUTH_HOLD"
    assert mod.safe_http_code(error(
        429, {"error": {"type": "rate_limit_error", "code": "opaque-private"}},
    )) == "PROXY_HTTP_429_RATE_LIMIT_HOLD"
    assert mod.safe_http_code(error(
        502, {"error": {"type": "unknown-sensitive", "message": "secret"}},
    )) == "PROXY_HTTP_502_HOLD"


def test_transport_diagnostics():
    assert mod.safe_transport_code(
        urllib.error.URLError(socket.gaierror(-2, "secret"))
    ) == "PROXY_DNS_HOLD"
    assert mod.safe_transport_code(
        urllib.error.URLError(TimeoutError("private host"))
    ) == "PROXY_TIMEOUT_HOLD"
    assert mod.safe_transport_code(
        urllib.error.URLError(ConnectionRefusedError("private host"))
    ) == "PROXY_CONNECTION_REFUSED_HOLD"
    assert mod.safe_transport_code(
        urllib.error.URLError(ssl.SSLError("private TLS"))
    ) == "PROXY_TLS_HANDSHAKE_HOLD"


def test_detail_safe_reason_whitelist():
    assert mod.safe_reason_code(mod.Hold(
        "PROXY_HTTP_400_INVALID_REQUEST_HOLD"
    )) == "PROXY_HTTP_400_INVALID_REQUEST_HOLD"
    assert mod.safe_reason_code(mod.Hold(
        "PROXY_HTTP_500_hidden-secret_HOLD"
    )) == "REVIEW_CONTRACT_HOLD"
    assert mod.safe_reason_code(mod.Hold(
        "PROXY_TLS_CERT_VERIFY_HOLD"
    )) == "PROXY_TLS_CERT_VERIFY_HOLD"
