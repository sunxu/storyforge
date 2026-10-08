"""Static safety checks for the one-epoch baseline candidate.

These checks do not imply rank-64 capacity or end-to-end acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_baseline_has_more_frequent_evaluation_and_saving():
    config = (ROOT / "configs/qwen38-27b-qlora-v0.1.yaml").read_text()
    assert "num_train_epochs: 1" in config
    assert "eval_strategy: steps" in config
    assert "save_strategy: steps" in config
    assert "eval_steps: 3" in config
    assert "save_steps: 3" in config
    assert "loss_scale: last_round" in config
    assert "disable_ignore_empty_think: true" in config
    assert "add_non_thinking_prefix: false" in config


def test_existing_launcher_is_not_misidentified_as_baseline():
    launcher = (ROOT / "scripts/hf_submit_smoke.sh").read_text()
    assert "--name storyforge-qlora-smoke" in launcher
    runner = (ROOT / "scripts/hf_job_runner.py").read_text()
    assert '"--max_steps", "3"' in runner
