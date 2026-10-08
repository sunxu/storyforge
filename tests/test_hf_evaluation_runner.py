"""Unit tests for Phase 3 GPU inference command and read-only validation policy."""
from pathlib import Path

from scripts.hf_evaluation_runner import infer_command


def test_base_and_adapter_use_same_prompt_and_decoding():
    base = infer_command(Path("/tmp/base.jsonl"), adapter=False)
    tuned = infer_command(Path("/tmp/tuned.jsonl"), adapter=True)
    assert "--adapters" not in base
    assert "--adapters" in tuned
    for option in ("--val_dataset", "--max_new_tokens", "--quant_method", "--quant_bits"):
        assert base[base.index(option) + 1] == tuned[tuned.index(option) + 1]
    assert "--val_dataset_sample" not in base
    assert base[base.index("--max_new_tokens") + 1] == "512"
    assert tuned[tuned.index("--max_new_tokens") + 1] == "512"
    assert base[base.index("--temperature") + 1] == "0"
    assert tuned[tuned.index("--temperature") + 1] == "0"


def test_eval_launch_is_opt_in_and_validation_only():
    root = Path(__file__).resolve().parents[1]
    shell = (root / "scripts/hf_submit_evaluation.sh").read_text()
    runner = (root / "scripts/hf_evaluation_runner.py").read_text()
    assert 'MODE="${1:-sync}"' in shell
    assert 'STORYFORGE_ALLOW_PAID_GPU:-' in shell
    assert "validation-prompts.jsonl" in runner
    assert "baseline-runs/baseline/6ac75bafdf2184ac91acb293" in runner
    assert "test.jsonl" not in runner
