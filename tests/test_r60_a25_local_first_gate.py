"""Synthetic CPU-only A25 end-to-end gate; no real model or private inputs."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_a25_local_first_gate.py")
spec = importlib.util.spec_from_file_location("a25_first_gate", SOURCE)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixture_worker(tmp_path, *, invalid_first=False, fail_at=None):
    model_calls = []
    tokenizer_calls = []
    saved = {}

    def tokenizer(model, **kwargs):
        tokenizer_calls.append((model, kwargs))
        return object()

    def llm(**kwargs):
        model_calls.append(kwargs)
        return object()

    hf = SimpleNamespace(
        AutoTokenizer=type("AutoTokenizer", (), {
            "from_pretrained": staticmethod(tokenizer),
        }))
    vllm = SimpleNamespace(LLM=llm)

    def write(path, record):
        saved[record["position"]] = record
        Path(path).write_text(json.dumps(record))

    def read(path, pos, row, model, rev):
        assert (model, rev) == (gate.MODEL, gate.REV)
        if invalid_first and pos == 1:
            return None
        return saved.get(pos)

    def review(rows, output, model, revision, start, limit,
               max_model_len, max_output_tokens, max_wall_seconds):
        hf.AutoTokenizer.from_pretrained(model, revision=revision,
                                         trust_remote_code=False)
        vllm.LLM(model=model, revision=revision,
                 tokenizer_revision=revision, dtype="bfloat16")
        for pos in range(start, start + limit):
            if pos == fail_at:
                raise RuntimeError("private-value-should-not-log")
            worker.write_checkpoint(
                output / worker.checkpoint_name(pos), {"position": pos})
        return {"cases_completed": limit}

    worker = SimpleNamespace(
        inference=review, write_checkpoint=write,
        read_checkpoint=read,
        checkpoint_name=lambda n: f"review_{n:04d}.private.json",
    )
    return worker, hf, vllm, model_calls, tokenizer_calls


def call(worker, tmp_path):
    return worker.inference(
        rows=[{"position": i} for i in range(1, 26)],
        output=tmp_path, model=gate.MODEL, revision=gate.REV,
        start=1, limit=25, max_model_len=32768,
        max_output_tokens=2400, max_wall_seconds=3000)


def test_one_local_engine_and_all_25(tmp_path, capsys):
    local = tmp_path / "weights"
    local.mkdir()
    worker, hf, vl, model_calls, tokenizer_calls = fixture_worker(tmp_path)
    state = gate.install_first_gate(worker, local, hf, vl)
    result = call(worker, tmp_path)
    assert result["cases_completed"] == 25
    assert state["first_pass"] and state["validated"] == 25
    assert len(model_calls) == 1
    assert model_calls[0]["model"] == str(local)
    assert model_calls[0]["tokenizer"] == str(local)
    assert "revision" not in model_calls[0]
    assert tokenizer_calls[0][0] == str(local)
    log = capsys.readouterr().out
    assert "A25_FIRST_GATE_PASS" in log and "A25_ALL_VERIFIED" in log
    assert "private-value-should-not-log" not in log


def test_invalid_first_prevents_second(tmp_path):
    local = tmp_path / "weights"
    local.mkdir()
    worker, hf, vl, models, tokens = fixture_worker(
        tmp_path, invalid_first=True)
    state = gate.install_first_gate(worker, local, hf, vl)
    with pytest.raises(gate.Hold, match="A25_CHECKPOINT_READBACK_HOLD"):
        call(worker, tmp_path)
    assert state["validated"] == 0
    assert len(models) == 1
    assert not (tmp_path / "review_0002.private.json").exists()


def test_failure_midway_no_completion(tmp_path, capsys):
    local = tmp_path / "weights"
    local.mkdir()
    worker, hf, vl, models, tokens = fixture_worker(tmp_path, fail_at=7)
    state = gate.install_first_gate(worker, local, hf, vl)
    with pytest.raises(RuntimeError):
        call(worker, tmp_path)
    assert state["validated"] == 6
    assert "A25_ALL_VERIFIED" not in capsys.readouterr().out


def test_scope_rejects_before_model_import(tmp_path):
    local = tmp_path / "weights"
    local.mkdir()
    worker, hf, vl, models, tokens = fixture_worker(tmp_path)
    gate.install_first_gate(worker, local, hf, vl)
    with pytest.raises(gate.Hold, match="A25_INFERENCE_CONTRACT_HOLD"):
        worker.inference([{}], tmp_path, gate.MODEL, gate.REV,
                         1, 1, 32768, 2400, 3000)
    assert not models
