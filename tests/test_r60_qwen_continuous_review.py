"""CPU synthetic: 25-case gating, repeated batches, one engine, resume checks."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_qwen_continuous_review.py")
spec = importlib.util.spec_from_file_location("r60_continuous", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic(tmp_path, *, first_bad=False, error_at=None):
    output = tmp_path / "output"
    output.mkdir()
    local = tmp_path / "local"
    local.mkdir()
    calls = {"model": [], "tokenizer": [], "batch": []}
    saved = {}

    def tokenizer_fn(model, **kwargs):
        calls["tokenizer"].append(model)
        return object()

    def llm_fn(**kwargs):
        calls["model"].append(kwargs)
        return object()

    tokenizer = type("Tokenizer", (), {
        "from_pretrained": staticmethod(tokenizer_fn)})
    vllm = SimpleNamespace(LLM=llm_fn)

    def write(path, record):
        saved[record["position"]] = record
        Path(path).write_text(json.dumps(record))

    def read(path, pos, row, model, revision):
        if pos == 1 and first_bad:
            return None
        assert (model, revision) == (mod.MODEL, mod.REV)
        return saved.get(pos)

    def infer(rows, out, model, revision, start, limit,
              max_model_len, max_output_tokens, max_wall_seconds):
        calls["batch"].append((start, limit))
        tokenizer.from_pretrained(model, revision=revision)
        vllm.LLM(model=model, revision=revision, tokenizer_revision=revision)
        for pos in range(start, start + limit):
            if pos == error_at:
                raise RuntimeError("private-detail")
            worker.write_checkpoint(
                out / worker.checkpoint_name(pos), {"position": pos})
        return {"cases_completed": limit}

    worker = SimpleNamespace(
        read_checkpoint=read, write_checkpoint=write,
        checkpoint_name=lambda n: f"review_{n:04d}.private.json",
        inference=infer,
    )
    rows = [{"pos": i} for i in range(1, 26)]
    return worker, rows, output, local, tokenizer, vllm, calls, saved


def run(state, *, limit=25, batch_size=5, resume=False):
    worker, rows, out, local, tok, vl, _calls, _saved = state
    return mod.run_batches(worker, rows, out, local, limit=limit,
                           batch_size=batch_size, max_model_len=32768,
                           max_output_tokens=2400, wall_seconds=1200,
                           resume=resume, hf_tokenizer=tok, vllm=vl)


def test_five_batches_one_engine_and_first_gate(tmp_path, capsys):
    state = synthetic(tmp_path)
    result = run(state)
    assert result == {"completed": 25, "complete": True}
    assert len(state[6]["model"]) == 1
    assert len(state[6]["tokenizer"]) == 1
    assert state[6]["batch"] == [(1, 5), (6, 5), (11, 5), (16, 5), (21, 5)]
    log = capsys.readouterr().out
    assert "FIRST_CHECKPOINT_GATE_PASS" in log
    assert "CONTINUOUS_REVIEW_COMPLETE" in log
    assert "REAL_ENGINE_REUSED" in log


def test_first_failure_stops_second(tmp_path, capsys):
    state = synthetic(tmp_path, first_bad=True)
    with pytest.raises(mod.Hold, match="REVIEW_CHECKPOINT_READBACK_HOLD"):
        run(state)
    assert not (state[2] / "review_0002.private.json").exists()
    assert "CONTINUOUS_REVIEW_COMPLETE" not in capsys.readouterr().out


def test_mid_batch_fail_no_false_completion(tmp_path, capsys):
    state = synthetic(tmp_path, error_at=7)
    with pytest.raises(RuntimeError):
        run(state)
    assert len(state[7]) == 6
    assert "CONTINUOUS_REVIEW_COMPLETE" not in capsys.readouterr().out


def test_reject_noncontiguous_prefix_and_invalid_resume(tmp_path):
    state = synthetic(tmp_path)
    (state[2] / "review_0002.private.json").write_text("{}")
    with pytest.raises(mod.Hold, match="REVIEW_PREFIX_GAP_HOLD"):
        run(state, resume=True)
    with pytest.raises(mod.Hold, match="REVIEW_OUTPUT_NONEMPTY_HOLD"):
        run(state)


def test_resume_valid_prefix_and_one_engine(tmp_path, capsys):
    state = synthetic(tmp_path)
    worker, _rows, output, _local, _tokenizer, _vllm, calls, saved = state
    for pos in range(1, 6):
        saved[pos] = {"position": pos}
        (output / worker.checkpoint_name(pos)).write_text("{}")
    result = run(state, resume=True)
    assert result["complete"]
    assert calls["batch"][0] == (6, 5)
    assert len(calls["model"]) == 1
    assert "REVIEW_PREFIX_VERIFIED" in capsys.readouterr().out


def test_reject_manifest_tamper(tmp_path):
    local = tmp_path / "weights"
    local.mkdir()
    (local / mod.MANIFEST).write_text(json.dumps({
        "model": mod.MODEL, "revision": mod.REV,
        "integrity_mode": "size-only-upstream-sha-declared",
        "files": [{"name": "../escape", "size": 2, "sha256": "0" * 64}],
    }))
    with pytest.raises(mod.Hold, match="LOCAL_MANIFEST_INVALID"):
        mod.verify_local_manifest(local)
