"""B25 first-checkpoint gate synthetic CPU tests: no vLLM, GPU or private inputs."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_b25_single_engine_gate.py")
spec = importlib.util.spec_from_file_location("r60_b25_gate", SOURCE)
assert spec is not None and spec.loader is not None
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def build_worker(tmp_path, *, bad_first=False, fail_at=None):
    loads = {"count": 0}
    observed = {}

    def write_checkpoint(path, record):
        Path(path).write_text(str(record["position"]))
        observed[record["position"]] = record

    def read_checkpoint(path, position, row, model, revision):
        assert model == gate.B_MODEL and revision == gate.B_REV
        if bad_first and position == 1:
            return None
        return observed.get(position)

    def inference(rows, output, model, revision, start, limit,
                  max_model_len, max_output_tokens, max_wall_seconds):
        loads["count"] += 1
        for pos in range(start, start + limit):
            if fail_at and pos == fail_at:
                raise ValueError("PRIVATE_GENERATION_FAILED")
            worker.write_checkpoint(
                output / worker.checkpoint_name(pos), {"position": pos})
        return {"cases_total": len(rows), "cases_completed": limit}

    worker = SimpleNamespace(
        inference=inference, write_checkpoint=write_checkpoint,
        read_checkpoint=read_checkpoint,
        checkpoint_name=lambda pos: f"review_{pos:04}.private.json",
    )
    return worker, loads


def call(worker, out):
    return worker.inference(
        rows=[{"blind_id": str(i)} for i in range(gate.EXPECTED_COUNT)],
        output=out, model=gate.B_MODEL, revision=gate.B_REV,
        start=1, limit=gate.EXPECTED_COUNT, max_model_len=32768,
        max_output_tokens=2400, max_wall_seconds=3000)


def test_one_engine_25_and_first_gate(tmp_path, capsys):
    worker, loads = build_worker(tmp_path)
    state = gate.install_gate(worker)
    result = call(worker, tmp_path)
    assert result["cases_completed"] == 25
    assert loads["count"] == 1
    assert state["first_verified"]
    assert state["verified_count"] == 25
    log = capsys.readouterr().out
    assert '"event":"B25_FIRST_GATE_PASS"' in log
    assert '"event":"B25_ALL_VERIFIED"' in log
    assert "PRIVATE" not in log


def test_first_checkpoint_bad_stops_before_second(tmp_path):
    worker, loads = build_worker(tmp_path, bad_first=True)
    state = gate.install_gate(worker)
    with pytest.raises(gate.GateHold, match="CHECKPOINT_READBACK_HOLD"):
        call(worker, tmp_path)
    assert loads["count"] == 1
    assert state["verified_count"] == 0
    assert not (tmp_path / "review_0002.private.json").exists()


def test_midrun_failure_does_not_claim_25(tmp_path, capsys):
    worker, loads = build_worker(tmp_path, fail_at=7)
    state = gate.install_gate(worker)
    with pytest.raises(ValueError, match="PRIVATE_GENERATION_FAILED"):
        call(worker, tmp_path)
    assert state["verified_count"] == 6
    assert "B25_ALL_VERIFIED" not in capsys.readouterr().out


def test_reject_partial_scope_before_load(tmp_path):
    worker, loads = build_worker(tmp_path)
    gate.install_gate(worker)
    with pytest.raises(gate.GateHold, match="INFERENCE_CONTRACT_HOLD"):
        worker.inference(
            [{"blind_id": "x"}], tmp_path, gate.B_MODEL, gate.B_REV,
            1, 1, 32768, 2400, 3000)
    assert loads["count"] == 0
