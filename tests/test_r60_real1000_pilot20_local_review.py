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
    assert payload["max_tokens"] == 8192


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


def test_finished_length_is_technical_hold_not_reject(monkeypatch):
    class MockResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, _count):
            return json.dumps({
                "choices": [{"finish_reason": "length", "message": {
                    "content": '{"decision":"REJ'
                }}]
            }).encode()
    class MockOpener:
        def open(self, req, timeout):
            assert timeout == 20
            payload = json.loads(req.data)
            assert payload["max_tokens"] == 8192
            return MockResponse()
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic-key")
    monkeypatch.setattr(mod.urllib.request, "build_opener", lambda *args: MockOpener())
    try:
        mod.proxy_request(
            "https://4router.ai/v1/chat/completions",
            "claude-opus-5-5", "synthetic", 20,
        )
    except mod.Hold as exc:
        assert str(exc) == "PROXY_TRUNCATED_HOLD"
    else:
        raise AssertionError("truncated output must remain a technical HOLD")


def test_response_diagnostic_categories_are_specific_and_safe():
    def envelope(content, finish="stop"):
        return json.dumps({"choices": [{"finish_reason": finish,
            "message": {"content": content}}]}).encode()
    for raw, expected in [
        (b"{not json", "PROXY_ENVELOPE_JSON_HOLD"),
        (json.dumps({"choices": []}).encode(), "PROXY_ENVELOPE_STRUCTURE_HOLD"),
        (envelope("not json"), "PROXY_MODEL_JSON_HOLD"),
        (envelope("[]"), "PROXY_RUBRIC_SCHEMA_HOLD"),
        (envelope(""), "PROXY_EMPTY_HOLD"),
        (envelope("not json", "length"), "PROXY_TRUNCATED_HOLD"),
    ]:
        try:
            mod.parse_proxy_response(raw)
        except mod.Hold as exc:
            assert str(exc) == expected
            assert mod.safe_reason_code(exc) == expected
        else:
            raise AssertionError("expected specific technical HOLD")


def test_failed_response_is_private_and_create_only(monkeypatch, tmp_path):
    setup_private(monkeypatch, tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    raw = b'{"choices":[{"finish_reason":"stop","message":{"content":"secret"}}]}'
    mod.save_failed_response(folder, 1, raw)
    target = tmp_path / "out-response-diagnostics-v1" / (
        "R60_PILOT20_FAILED_0001_PRIVATE.json"
    )
    assert target.read_bytes() == raw
    mod.save_failed_response(folder, 1, b"do-not-overwrite")
    assert target.read_bytes() == raw


def test_successful_response_remains_valid():
    raw = json.dumps({"choices": [{"finish_reason": "stop",
        "message": {"content": json.dumps(model_answer())}}]}).encode()
    assert mod.parse_proxy_response(raw) == model_answer()


def test_standalone_json_fence_validated_without_loose_extraction():
    answer = json.dumps(model_answer(), ensure_ascii=False)
    def wrapped(text, finish="stop"):
        return json.dumps({"choices": [{"finish_reason": finish,
            "message": {"content": text}}]}).encode()
    for content in (f"```json\n{answer}\n```", f"```JSON\n{answer}\n```"):
        assert mod.parse_proxy_response(wrapped(content)) == model_answer()
    for content in (
        f"Here is the review:\n```json\n{answer}\n```",
        f"```json\n{answer}\n```\nextra",
        f"```json\n{answer}",
        f"```python\n{answer}\n```",
    ):
        try:
            mod.parse_proxy_response(wrapped(content))
        except mod.Hold as exc:
            assert str(exc) == "PROXY_MODEL_JSON_HOLD"
        else:
            raise AssertionError("reject loose or malformed fence")


def test_replay_snapshot_is_cpu_only_and_advisory(monkeypatch, tmp_path):
    packet_dir = setup_private(monkeypatch, tmp_path)
    output = tmp_path / "output"
    mod.initialize(packet_dir, output, "https://4router.ai/v1",
                   "claude-opus-5-5", 30)
    raw = json.dumps({"id": "synthetic-message-1",
        "model": "claude-opus-5-5",
        "choices": [{"finish_reason": "stop", "message": {
            "content": "```json\n" + json.dumps(model_answer()) + "\n```"
        }}]}).encode()
    mod.save_failed_response(output, 1, raw)
    try:
        mod.replay_private_snapshot(output, position=1)
    except mod.Hold as exc:
        assert str(exc) == "SNAPSHOT_PROVENANCE_CONFIRMATION_REQUIRED"
    else:
        raise AssertionError("provenance approval required")
    progress = mod.replay_private_snapshot(
        output, position=1, confirm_provenance=True)
    assert progress["model_reviewed"] == 1
    assert progress["model_decisions_advisory"]["REJECT"] == 1
    assert progress["quality_v1_admitted"] == 0
    assert progress["train_admitted"] == 0
    try:
        mod.replay_private_snapshot(
            output, position=1, confirm_provenance=True)
    except mod.Hold as exc:
        assert str(exc) == "REPLAY_POSITION_HOLD"
    else:
        raise AssertionError("replay is create-only, no overwrite")


def test_replay_rejects_wrong_model_snapshot(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    output = tmp_path / "output"
    mod.initialize(packets_dir, output, "https://4router.ai/v1",
                   "claude-opus-5-5", 30)
    raw = json.dumps({"id": "synthetic-message-1", "model": "wrong-model",
        "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(model_answer())}}]}).encode()
    mod.save_failed_response(output, 1, raw)
    try:
        mod.replay_private_snapshot(
            output, position=1, confirm_provenance=True)
    except mod.Hold as exc:
        assert str(exc) == "SNAPSHOT_MODEL_BINDING_HOLD"
    else:
        raise AssertionError("wrong model snapshot accepted")
    assert mod.get_state(output)[2]["model_reviewed"] == 0


def test_fenced_pass_below_frozen_floor_is_not_admitted():
    answer = model_answer()
    answer["decision"] = "PASS"
    answer["severe_flags"] = {
        "serious_player_agency": False, "hard_fact_or_ban": False,
        "safety_exclusion": False,
    }
    # Frozen chinese_prose floor is 4; the reviewer scored 3.
    answer["scores"]["chinese_prose"] = 3
    raw = json.dumps({"choices": [{"finish_reason": "stop",
        "message": {"content": "```json\n" +
                    json.dumps(answer, ensure_ascii=False) + "\n```"}}]}).encode()
    try:
        mod.parse_proxy_response(raw)
    except mod.Hold as exc:
        assert str(exc) == "PROXY_PASS_BELOW_FLOOR_HOLD"
        assert mod.safe_reason_code(exc) == "PROXY_PASS_BELOW_FLOOR_HOLD"
    else:
        raise AssertionError("PASS below frozen floor must not be accepted")


def test_quarantine_conflict_preserves_original_and_unblocks_next(monkeypatch, tmp_path):
    packet_dir = setup_private(monkeypatch, tmp_path)
    output = tmp_path / "out"
    mod.initialize(packet_dir, output, "https://4router.ai/v1",
                   "claude-opus-5-5", 30)
    answer = model_answer()
    answer["decision"] = "PASS"
    answer["severe_flags"]["serious_player_agency"] = False
    answer["scores"]["chinese_prose"] = 3
    raw = json.dumps({"id": "synthetic-message", "model": "claude-opus-5-5",
        "choices": [{"finish_reason": "stop", "message": {
            "content": "```json\n" + json.dumps(answer) + "\n```"
        }}]}).encode()
    mod.save_failed_response(output, 1, raw)
    result = mod.quarantine_private_conflict(
        output, position=1, confirm_provenance=True)
    assert result["processed"] == 1
    assert result["model_reviewed"] == 0
    assert result["conflict_pending"] == 1
    assert result["remaining"] == 19
    assert result["quality_v1_admitted"] == 0
    assert result["train_admitted"] == 0
    assert not (output / mod.receipt_name(1)).exists()
    row = json.loads((output / mod.conflict_name(1)).read_bytes())
    assert row["original_decision"] == "PASS"
    assert row["scores"]["chinese_prose"] == 3
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic-key")
    monkeypatch.setattr(mod, "proxy_request", lambda *args: model_answer())
    next_state = mod.advance(output, 1, execute=True,
                             allow_private_data_egress=True)
    assert next_state["processed"] == 2
    assert next_state["model_reviewed"] == 1
    assert next_state["conflict_pending"] == 1
    assert (output / mod.receipt_name(2)).exists()
    assert not (output / mod.receipt_name(1)).exists()
    try:
        mod.quarantine_private_conflict(
            output, position=1, confirm_provenance=True)
    except mod.Hold as exc:
        assert str(exc) == "REPLAY_POSITION_HOLD"
    else:
        raise AssertionError("must be create-only")


def test_advance_auto_conflict_continues_batch_without_extra_request(
        monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    output = tmp_path / "out"
    mod.initialize(packets_dir, output, "https://4router.ai/v1",
                   "claude-opus-5-5", 30)
    conflict = model_answer()
    conflict["decision"] = "PASS"
    conflict["severe_flags"]["serious_player_agency"] = False
    conflict["scores"]["chinese_prose"] = 3
    replies = [mod.QualityConflict(conflict), model_answer()]
    calls = []
    def fake_proxy(*args):
        calls.append(args[-1])
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic")
    monkeypatch.setattr(mod, "proxy_request", fake_proxy)
    state = mod.advance(output, 2, execute=True, allow_private_data_egress=True)
    assert calls == [1, 2]
    assert state["processed"] == 2
    assert state["conflict_pending"] == 1
    assert state["model_reviewed"] == 1
    assert state["remaining"] == 18
    assert state["train_admitted"] == 0
    record = json.loads((output / mod.conflict_name(1)).read_bytes())
    assert record["original_decision"] == "PASS"
    assert record["scores"]["chinese_prose"] == 3
    assert (output / mod.receipt_name(2)).exists()
    assert not (output / mod.receipt_name(1)).exists()


def test_batch_stops_on_technical_hold_and_preserves_prior(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    output = tmp_path / "out"
    mod.initialize(packets_dir, output, "https://4router.ai/v1",
                   "claude-opus-5-5", 30)
    calls = []
    def fake_proxy(*args):
        calls.append(args[-1])
        if len(calls) == 2:
            raise mod.Hold("PROXY_HTTP_502_HOLD")
        return model_answer()
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic")
    monkeypatch.setattr(mod, "proxy_request", fake_proxy)
    try:
        mod.advance(output, 3, execute=True, allow_private_data_egress=True)
    except mod.Hold as exc:
        assert str(exc) == "PROXY_HTTP_502_HOLD"
    else:
        raise AssertionError("technical HOLD must interrupt the batch")
    assert calls == [1, 2]
    assert mod.get_state(output)[2]["processed"] == 1
    assert (output / mod.receipt_name(1)).exists()
    assert not (output / mod.receipt_name(2)).exists()


def test_proxy_live_path_creates_recoverable_conflict_and_snapshot(
        monkeypatch, tmp_path):
    setup_private(monkeypatch, tmp_path)
    output = tmp_path / "out"
    output.mkdir()
    answer = model_answer()
    answer["decision"] = "PASS"
    answer["severe_flags"]["serious_player_agency"] = False
    answer["scores"]["chinese_prose"] = 3
    payload = json.dumps({"id": "synthetic", "model": "claude-opus-5-5",
        "choices": [{"finish_reason": "stop",
                     "message": {"content": "```json\n" +
                                 json.dumps(answer) + "\n```"}}]}).encode()
    class MockResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, count):
            assert count > len(payload)
            return payload
    class MockOpener:
        def open(self, request, timeout):
            return MockResponse()
    monkeypatch.setenv("CLI_PROXY_API_KEY", "synthetic-key")
    monkeypatch.setattr(mod.urllib.request, "build_opener",
                        lambda *args: MockOpener())
    try:
        mod.proxy_request(
            "https://4router.ai/v1/chat/completions",
            "claude-opus-5-5", "synthetic prompt", 20,
            output, 1,
        )
    except mod.QualityConflict as exc:
        assert exc.answer == answer
    else:
        raise AssertionError("expected recoverable model quality conflict")
    snapshot = tmp_path / "out-response-diagnostics-v1" / (
        "R60_PILOT20_FAILED_0001_PRIVATE.json")
    assert snapshot.read_bytes() == payload


def test_exact_single_extra_closing_brace_repaired_with_original_rubric():
    answer = model_answer()
    answer["decision"] = "HOLD"
    answer["scores"]["chinese_prose"] = 3
    answer["severe_flags"]["serious_player_agency"] = False
    text = json.dumps(answer, ensure_ascii=False)
    raw = json.dumps({"choices": [{"finish_reason": "stop", "message": {
        "content": "```json\n" + text + "}\n```"
    }}]}).encode()
    assert mod.parse_proxy_response(raw) == answer
    assert mod.decoded_model_json(raw) == answer


def test_terminal_extra_brace_repair_rejects_any_other_mutation():
    raw = '{"decision":"HOLD"}'
    for text in (
        raw + "}}", raw + "} trailing", "prefix " + raw + "}",
        raw[:-1] + "}} junk", '{"a":1}{"b":2}',
        '{"a":1}}\nmore', '{"a":1} ]',
    ):
        try:
            mod.parse_strict_model_json(text)
        except mod.Hold as exc:
            assert str(exc) == "PROXY_MODEL_JSON_HOLD"
        else:
            raise AssertionError("must reject anything but one extra terminal brace")
    assert mod.parse_strict_model_json(raw + "}") == {"decision": "HOLD"}


def test_extra_brace_does_not_bypass_frozen_rubric():
    answer = model_answer()
    answer["decision"] = "PASS"
    answer["severe_flags"]["serious_player_agency"] = False
    answer["scores"]["chinese_prose"] = 3
    raw = json.dumps({"choices": [{"finish_reason": "stop", "message": {
        "content": json.dumps(answer) + "}"
    }}]}).encode()
    try:
        mod.parse_proxy_response(raw)
    except mod.Hold as exc:
        assert str(exc) == "PROXY_PASS_BELOW_FLOOR_HOLD"
    else:
        raise AssertionError("normalization must not weaken rubric")
