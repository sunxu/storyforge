import json
from pathlib import Path

import pytest

from scripts.hf_job_runner import Runner, check_inference_result, training_evidence


def _checkpoint(tmp_path: Path, *, loss=1.0, eval_loss=2.0, step=3, weights=True):
    checkpoint = tmp_path / "checkpoint-3"
    checkpoint.mkdir()
    (checkpoint / "trainer_state.json").write_text(json.dumps({
        "global_step": step,
        "log_history": [{"loss": loss}, {"eval_loss": eval_loss}],
    }), encoding="utf-8")
    (checkpoint / "adapter_config.json").write_text("{}", encoding="utf-8")
    if weights:
        (checkpoint / "adapter_model.safetensors").write_bytes(b"weights")
    return checkpoint


def test_training_evidence_requires_finite_losses_and_adapter(tmp_path):
    checkpoint = _checkpoint(tmp_path)
    evidence = training_evidence(tmp_path)
    assert evidence["global_step"] == 3
    assert evidence["adapter"] == str(checkpoint)
    (checkpoint / "adapter_model.safetensors").unlink()
    with pytest.raises(RuntimeError, match="adapter weights"):
        training_evidence(tmp_path)


def test_training_evidence_rejects_nonfinite_eval_loss(tmp_path):
    _checkpoint(tmp_path, eval_loss="nan")
    with pytest.raises(RuntimeError, match="finite eval_loss"):
        training_evidence(tmp_path)


def test_inference_result_requires_nonempty_response(tmp_path):
    path = tmp_path / "results.jsonl"
    path.write_text('{"response": ""}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="non-empty response"):
        check_inference_result(path)
    path.write_text('{"response": "ok"}\n', encoding="utf-8")
    check_inference_result(path)


def test_stream_drains_both_pipes_without_deadlock(tmp_path):
    runner = Runner(tmp_path)
    try:
        code = runner.stream([
            "python3", "-c",
            ("import sys; [print('o'*100) for _ in range(3000)]; "
             "[print('e'*100, file=sys.stderr) for _ in range(3000)]"),
        ])
        assert code == 0
    finally:
        runner.close()
    assert (tmp_path / "stdout.log").stat().st_size > 100_000
    assert (tmp_path / "stderr.log").stat().st_size > 100_000
