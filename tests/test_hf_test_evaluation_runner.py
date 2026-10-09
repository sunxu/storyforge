"""Held-out evaluation uses independent paths and frozen inference flags."""
from pathlib import Path

from scripts import hf_test_evaluation_runner as test_runner
from scripts.hf_evaluation_runner import infer_command as validation_command


def test_final_test_isolated_with_frozen_generation_settings():
    result = Path("/tmp/result.jsonl")
    base = test_runner.infer_command(result, adapter=False)
    tuned = test_runner.infer_command(result, adapter=True)
    val = validation_command(result, adapter=False)
    assert "--adapters" not in base
    assert "--adapters" in tuned
    assert base[base.index("--val_dataset") + 1].endswith("test-prompts.jsonl")
    assert val[val.index("--val_dataset") + 1].endswith("validation-prompts.jsonl")
    for flag in ("--max_new_tokens", "--seed", "--data_seed", "--temperature",
                 "--val_dataset_shuffle", "--quant_bits", "--infer_backend"):
        assert base[base.index(flag) + 1] == val[val.index(flag) + 1]
        assert tuned[tuned.index(flag) + 1] == val[val.index(flag) + 1]
    assert base[base.index("--max_new_tokens") + 1] == "1536"


def test_test_launch_protected_and_20_samples_required():
    root = Path(__file__).resolve().parents[1]
    runner = (root / "scripts/hf_test_evaluation_runner.py").read_text()
    launcher = (root / "scripts/hf_submit_test_evaluation.sh").read_text()
    assert "len(rows) != 20" in runner
    assert "evaluation-runs/test" in runner
    assert "STORYFORGE_ALLOW_PAID_GPU" in launcher
    assert "test-prompts.jsonl" in launcher
    assert "validation-prompts.jsonl" not in launcher
