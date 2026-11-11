"""CPU synthetic tests for a localhost-only 20-case literary review pilot."""
from __future__ import annotations

import importlib.util
import sys
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
    monkeypatch.setattr(mod.reviewer, "model_request", fake_request)
    folder = tmp_path / "output"
    result = mod.initialize(packets_dir, folder, "http://127.0.0.1:11434/v1",
                            "local-test-model", True, 30)
    assert result["model_reviewed"] == 0
    result = mod.advance(folder, 5)
    assert result["model_reviewed"] == 5
    assert result["model_decisions_advisory"]["REJECT"] == 5
    assert result["quality_v1_admitted"] == 0
    result = mod.advance(folder, 5)
    assert result["model_reviewed"] == 10
    assert len(calls) == 10
    assert mod.get_state(folder)[2]["model_reviewed"] == 10


def test_failed_model_does_not_write_receipt(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    folder = tmp_path / "out"
    mod.initialize(packets_dir, folder, "http://localhost:11434/v1",
                   "local-test-model", False, 20)
    def fail(*args):
        raise mod.reviewer.Hold("MODEL_TRANSPORT_HOLD")
    monkeypatch.setattr(mod.reviewer, "model_request", fail)
    try:
        mod.advance(folder, 1)
    except mod.reviewer.Hold:
        pass
    else:
        raise AssertionError("expected reviewer failure")
    assert mod.get_state(folder)[2]["model_reviewed"] == 0


def test_tampered_packet_rejected(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    folder = tmp_path / "out"
    mod.initialize(packets_dir, folder, "http://127.0.0.1:11434/v1",
                   "local-test-model", False, 20)
    p = packets_dir / mod.pilot.FILENAME
    p.write_bytes(p.read_bytes() + b" ")
    try:
        mod.get_state(folder)
    except mod.Hold:
        return
    raise AssertionError("expected packet binding failure")


def test_remote_endpoint_refused(monkeypatch, tmp_path):
    packets_dir = setup_private(monkeypatch, tmp_path)
    try:
        mod.initialize(packets_dir, tmp_path / "out", "https://example.com/v1",
                       "test-model", True, 20)
    except mod.reviewer.Hold:
        return
    raise AssertionError("expected remote endpoint rejection")
