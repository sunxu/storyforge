"""CPU regression: shared per-case isolation, strict receipts, resume, one engine."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_review_isolation_core.py")
spec = importlib.util.spec_from_file_location("r60_isolation", SOURCE)
assert spec and spec.loader
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class ReviewError(ValueError):
    pass


def fixture(tmp_path, fail_at=None, *, unknown=False, model="Qwen/Qwen3-32B"):
    out = tmp_path / "output"
    local = tmp_path / "weights"
    out.mkdir()
    local.mkdir()
    rows = [{"position": pos} for pos in range(1, 26)]
    events = {"engines": 0, "tokens": 0, "positions": []}
    revision = "a" * 40

    def tokenizer_load(name, **kwargs):
        events["tokens"] += 1
        return object()

    tokenizer = type("AutoTokenizer", (), {
        "from_pretrained": staticmethod(tokenizer_load)})

    def engine_load(**kwargs):
        events["engines"] += 1
        tokenizer.from_pretrained(kwargs["tokenizer"])
        return object()

    vllm = SimpleNamespace(LLM=engine_load)

    def read(path, pos, row, model_id, rev):
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        assert data["pos"] == pos
        assert model_id == model and rev == revision
        return data

    def infer(input_rows, output, model_id, rev, start, limit, *_args):
        assert limit == 1
        events["positions"].append(start)
        tokenizer.from_pretrained(model_id, revision=rev)
        vllm.LLM(model=model_id, revision=rev, tokenizer_revision=rev)
        if start == fail_at:
            raise ReviewError("unexpected private secret" if unknown
                              else "MODEL_NONEXACT_QUOTE_HOLD")
        (output / f"review_{start:04d}.private.json").write_text(
            json.dumps({"pos": start}))

    worker = SimpleNamespace(
        POLICY="frozen-review-policy", ReviewError=ReviewError,
        input_digest=lambda row: core.sha(row),
        read_checkpoint=read,
        checkpoint_name=lambda pos: f"review_{pos:04d}.private.json",
        inference=infer,
    )
    return (worker, rows, out, local, tokenizer, vllm,
            events, revision, model)


def run(data, *, resume=False, limit=25, batch_size=5):
    worker, rows, out, local, tok, vl, _events, rev, model = data
    return core.run_isolated(
        worker, rows, out, local, model=model, revision=rev,
        limit=limit, batch_size=batch_size, max_model_len=32768,
        max_output_tokens=2400, wall_seconds=1200, resume=resume,
        hf_tokenizer=tok, vllm=vl)


def test_glm_first_failure_then_24_pass_single_engine(tmp_path, capsys):
    data = fixture(tmp_path, fail_at=1, model="zai-org/GLM-4-32B-0414")
    result = run(data)
    assert result == {"attempted": 25, "verified": 24,
                      "technical_failures": 1, "all_attempted": True,
                      "all_verified": False}
    assert data[6]["engines"] == 1
    assert data[6]["positions"] == list(range(1, 26))
    assert (data[2] / "technical_failure_0001.safe.json").exists()
    assert not (data[2] / "review_0001.private.json").exists()
    assert (data[2] / "review_0025.private.json").exists()
    log = capsys.readouterr().out
    assert "ALL_CASES_ATTEMPTED" in log
    assert "CONTINUOUS_REVIEW_COMPLETE" not in log


def test_qwen_resumes_six_checkpoints_then_one_failure(tmp_path, capsys):
    data = fixture(tmp_path, fail_at=7)
    worker, _rows, out, _local, _tok, _vl, events, _revision, _model = data
    for pos in range(1, 7):
        (out / worker.checkpoint_name(pos)).write_text(json.dumps({"pos": pos}))
    result = run(data, resume=True)
    assert result["attempted"] == 25
    assert result["verified"] == 24
    assert result["technical_failures"] == 1
    assert events["positions"] == list(range(7, 26))
    assert events["engines"] == 1
    assert "ISOLATION_RESUME_VERIFIED" in capsys.readouterr().out


def test_resume_mixed_technical_and_success(tmp_path):
    data = fixture(tmp_path, fail_at=2)
    first = run(data, limit=5, batch_size=5)
    assert first["attempted"] == 5
    assert first["technical_failures"] == 1
    result = run(data, resume=True)
    assert result["attempted"] == 25
    assert result["technical_failures"] == 1
    assert data[6]["positions"] == list(range(1, 26))
    assert data[6]["engines"] == 2  # separate resume invocation = new Job


def test_corrupt_receipt_prevents_resume(tmp_path):
    data = fixture(tmp_path, fail_at=1)
    run(data, limit=1)
    f = data[2] / core.failure_name(1)
    payload = json.loads(f.read_text())
    payload["technical_reason_code"] = "MODEL_JSON_HOLD"
    f.write_text(json.dumps(payload))
    with pytest.raises(core.IsolationHold, match="TECHNICAL_RECEIPT_IDENTITY_HOLD"):
        run(data, resume=True)


def test_missing_middle_and_mixed_duplicate_prevent_resume(tmp_path):
    data = fixture(tmp_path, fail_at=2)
    run(data, limit=5)
    (data[2] / "review_0003.private.json").unlink()
    with pytest.raises(core.IsolationHold, match="OUTPUT_NONCONTIGUOUS_ATTEMPTS_HOLD"):
        run(data, resume=True)
    (data[2] / "review_0003.private.json").write_text('{"pos":3}')
    (data[2] / "review_0002.private.json").write_text('{"pos":2}')
    with pytest.raises(core.IsolationHold, match="OUTPUT_DUPLICATE_ATTEMPT_HOLD"):
        run(data, resume=True)


def test_unknown_private_error_halts_without_leaking(tmp_path, capsys):
    data = fixture(tmp_path, fail_at=1, unknown=True)
    with pytest.raises(core.IsolationHold, match="UNKNOWN_REVIEW_ERROR_CODE_HOLD"):
        run(data)
    log = capsys.readouterr().out
    assert "unexpected private secret" not in log
    assert not list(data[2].iterdir())


def test_nonreview_runtime_error_not_isolated(tmp_path, capsys):
    data = fixture(tmp_path)
    data[0].inference = lambda *_args: (_ for _ in ()).throw(RuntimeError("engine down"))
    with pytest.raises(RuntimeError):
        run(data)
    assert "UNEXPECTED_RUNTIME_HOLD" in capsys.readouterr().out
    assert not list(data[2].iterdir())


def test_all_valid_remains_full_completion(tmp_path, capsys):
    data = fixture(tmp_path)
    result = run(data)
    assert result["all_verified"]
    assert result["technical_failures"] == 0
    assert "CONTINUOUS_REVIEW_COMPLETE" in capsys.readouterr().out
