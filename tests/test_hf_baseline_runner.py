"""CPU-only baseline runner safety tests."""
import json

import pytest

from scripts import hf_baseline_runner as baseline


def test_capacity_is_bounded_and_disables_save_eval(tmp_path):
    command = baseline.build_train_command(tmp_path, mode="capacity")
    assert command[command.index("--max_steps") + 1] == "1"
    assert command[command.index("--save_strategy") + 1] == "no"
    assert command[command.index("--eval_strategy") + 1] == "no"
    assert "--custom_register_path" in command


def test_baseline_has_no_step_override(tmp_path):
    command = baseline.build_train_command(tmp_path, mode="baseline")
    assert "--max_steps" not in command
    assert "qwen38-27b-qlora-v0.1.yaml" in " ".join(command)


def test_invalid_mode_rejected(tmp_path):
    with pytest.raises(ValueError):
        baseline.build_train_command(tmp_path, mode="smoke")


def test_capacity_requires_finite_one_step_state(tmp_path):
    ckpt = tmp_path / "checkpoint-1"
    ckpt.mkdir()
    state = ckpt / "trainer_state.json"
    state.write_text(json.dumps({"global_step": 1, "log_history": [{"loss": 1.4}]}))
    assert baseline.validate_capacity_evidence(tmp_path) == 1
    state.write_text(json.dumps({"global_step": 1, "log_history": [{"loss": "nan"}]}))
    with pytest.raises(RuntimeError, match="finite loss"):
        baseline.validate_capacity_evidence(tmp_path)
    state.write_text(json.dumps({"global_step": 2, "log_history": [{"loss": 1.0}]}))
    with pytest.raises(RuntimeError, match="exactly one step"):
        baseline.validate_capacity_evidence(tmp_path)


def test_script_refuses_implicit_gpu():
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "scripts/hf_submit_baseline.sh").read_text()
    assert 'STORYFORGE_ALLOW_PAID_GPU:-' in script
    assert 'MODE="${1:-sync}"' in script
    assert "--capacity-job-id" in script


def test_baseline_requires_prior_matching_capacity():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts/hf_baseline_runner.py").read_text()
    assert 'prior / "CAPACITY_PASS"' in source
    assert 'f"config_sha256: {sha256(CONFIG)}"' in source
