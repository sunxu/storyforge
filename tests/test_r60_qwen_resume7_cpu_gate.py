"""Qwen CPU-only A7 resume prefix gate, with fake frozen reviewer."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_qwen_resume7_cpu_gate.py")
spec = importlib.util.spec_from_file_location("r60_qwen_resume7", SOURCE)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixture(tmp_path, monkeypatch):
    source = tmp_path / "source.private.jsonl"
    runner = tmp_path / "runner.py"
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    rows = [{"blind_id": f"{pos:032x}", "content": "private-input"}
            for pos in range(1, 26)]
    source.write_text("".join(json.dumps(x) + "\n" for x in rows))
    runner.write_text(
        "import json\n"
        "from pathlib import Path\n"
        "def validate_input(row):\n"
        "    assert set(row) == {'blind_id', 'content'}\n"
        "def checkpoint_name(position):\n"
        "    return f'review_{position:04d}.private.json'\n"
        "def read_checkpoint(path, position, row, model, revision):\n"
        "    record=json.loads(path.read_text())\n"
        "    assert record['blind_id']==row['blind_id']\n"
        "    assert record['model']==model\n"
        "    assert record['revision']==revision\n"
        "    return record\n")
    for pos in range(1, 7):
        (receipts / f"review_{pos:04d}.private.json").write_text(json.dumps({
            "blind_id": rows[pos - 1]["blind_id"],
            "model": gate.MODEL,
            "revision": gate.REV,
        }))
    monkeypatch.setattr(gate, "SOURCE_SHA", hashlib.sha256(source.read_bytes()).hexdigest())
    return runner, source, receipts


def test_exact_six_verified_and_no_write(tmp_path, monkeypatch):
    runner, source, receipts = fixture(tmp_path, monkeypatch)
    result = gate.check(runner, source, receipts)
    assert result["status"] == "QWEN_RESUME7_CPU_GATE_PASS"
    assert result["checkpoint_prefix_verified"] == 6
    assert result["next_position"] == 7
    assert result["gpu_started"] is False
    assert len(list(receipts.iterdir())) == 6
    assert "private-input" not in str(result)


def test_extra_or_missing_record_holds(tmp_path, monkeypatch):
    runner, source, receipts = fixture(tmp_path, monkeypatch)
    (receipts / "review_0007.private.json").write_text("{}")
    with pytest.raises(gate.GateHold, match="PREFIX_INVENTORY_HOLD"):
        gate.check(runner, source, receipts)
    (receipts / "review_0007.private.json").unlink()
    (receipts / "review_0001.private.json").unlink()
    with pytest.raises(gate.GateHold, match="PREFIX_INVENTORY_HOLD"):
        gate.check(runner, source, receipts)


def test_modified_model_or_identity_holds(tmp_path, monkeypatch):
    runner, source, receipts = fixture(tmp_path, monkeypatch)
    file = receipts / "review_0002.private.json"
    record = json.loads(file.read_text())
    record["model"] = "OTHER"
    file.write_text(json.dumps(record))
    with pytest.raises(gate.GateHold, match="PREFIX_VALIDATION_HOLD"):
        gate.check(runner, source, receipts)


def test_changed_source_checksum_holds(tmp_path, monkeypatch):
    runner, source, receipts = fixture(tmp_path, monkeypatch)
    source.write_text(source.read_text() + "\n")
    with pytest.raises(gate.GateHold, match="SOURCE_SHA_HOLD"):
        gate.check(runner, source, receipts)
