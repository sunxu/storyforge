"""Synthetic tests for R46-vs-R60 System-role audit, no private data."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "r60_r46_common2_system_contract_cpu",
    ROOT / "scripts/r60_r46_common2_system_contract_cpu.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_independent_source_checks_report_difference_only(monkeypatch, tmp_path):
    seen = []
    def original(path, kind):
        seen.append(kind)
        return (49, 49) if kind == "train" else (15, 15)
    monkeypatch.setattr(m, "original_split", original)
    monkeypatch.setattr(m, "common2_input", lambda p: (2, 0))
    result = m.inspect(tmp_path / "tr.jsonl", tmp_path / "va.jsonl", tmp_path / "private")
    assert seen == ["train", "validation"]
    assert result["status"] == "R46_R60_SYSTEM_ROLE_CONTRACT_DIFFERENCE_CONFIRMED__TRAIN_HOLD"
    assert result["r45_rows_with_initial_system"] == 64
    assert result["common2_rows_with_system"] == 0
    assert result["historical_vs_current_system_contract_equal"] is False
    assert result["r46_runtime_template_equivalence_verified"] is False
    assert result["training_input_policy_approved"] is False
    assert result["train_admitted"] == 0


def test_bad_train_source_returns_fixed_hold(monkeypatch, tmp_path):
    def reject(path, kind):
        raise m.Hold("R45_FROZEN_SHA_HOLD")
    monkeypatch.setattr(m, "original_split", reject)
    out = m.inspect(tmp_path / "train", tmp_path / "val", tmp_path / "input")
    assert out["reason_code"] == "R45_FROZEN_SHA_HOLD"
    assert out["train_admitted"] == 0


def test_unknown_private_text_never_leaks(monkeypatch, tmp_path):
    def reject(path, kind):
        raise ValueError("SECRET STORY CONTENT")
    monkeypatch.setattr(m, "original_split", reject)
    out = m.inspect(tmp_path / "train", tmp_path / "val", tmp_path / "input")
    assert out["reason_code"] == "INPUT_OR_RUNTIME_HOLD"
    assert "SECRET STORY CONTENT" not in json.dumps(out)


def test_reference_order_and_unsupported_loss_rejected(tmp_path, monkeypatch):
    def fake_bytes(path):
        row = {"messages": [
            {"role": "system", "content": "synthetic", "loss": False},
            {"role": "user", "content": "prompt", "loss": True},
            {"role": "assistant", "content": "target", "loss": True},
        ]}
        return (json.dumps(row) + "\n").encode()
    monkeypatch.setattr(m.r45, "private_bytes", fake_bytes)
    monkeypatch.setitem(m.r45.PINS, "train", ("ignore", 1))
    monkeypatch.setattr(m.r45.hashlib, "sha256", lambda data: type("H", (), {"hexdigest":lambda self:"ignore"})())
    try:
        m.original_split(tmp_path / "sample", "train")
        assert False, "must reject historical user supervision"
    except m.Hold as e:
        assert str(e) == "R46_DATA_ROLE_LOSS_HOLD"


def test_common2_unexpected_system_is_not_allowed(tmp_path, monkeypatch):
    folder = tmp_path / "input"
    folder.mkdir(mode=0o700)
    row = {
        "messages": [{"role":"system","content":"fabricated"}],
    }
    raw = (json.dumps(row) + "\n").encode()
    monkeypatch.setattr(m.readiness, "private_bytes", lambda path, limit: raw if path.name == m.sft.DATA_NAME else b"{}")
    monkeypatch.setattr(m.audit, "validate_payload", lambda rows,manifest,raw:None)
    try:
        m.common2_input(folder)
        assert False, "unexpected system should hold"
    except m.Hold as e:
        assert str(e) == "COMMON2_UNEXPECTED_SYSTEM_HOLD"
