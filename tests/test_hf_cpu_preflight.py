import json
from pathlib import Path

import pytest

from scripts.hf_cpu_preflight import check_config, check_data


def test_preflight_accepts_explicit_last_answer_mask(tmp_path: Path):
    path = tmp_path / "sample.jsonl"
    sample = {"messages": [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "history", "loss": False},
        {"role": "user", "content": "new"},
        {"role": "assistant", "content": "gold", "loss": True},
    ]}
    path.write_text(json.dumps(sample) + "\n", encoding="utf-8")
    assert check_data(path)["targets"] == 1


def test_preflight_rejects_unmasked_history(tmp_path: Path):
    path = tmp_path / "sample.jsonl"
    sample = {"messages": [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "history", "loss": True},
        {"role": "user", "content": "new"},
        {"role": "assistant", "content": "gold", "loss": True},
    ]}
    path.write_text(json.dumps(sample) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="historical assistant"):
        check_data(path)


def test_preflight_accepts_smoke_and_baseline_configs():
    root = Path(__file__).resolve().parents[1]
    smoke = check_config(root / "configs/qwen38-27b-qlora-smoke.yaml")
    baseline = check_config(root / "configs/qwen38-27b-qlora-v0.1.yaml")
    assert smoke["mode"] == "smoke"
    assert baseline["mode"] == "baseline"


def test_preflight_rejects_baseline_with_smoke_step_override(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    source = (root / "configs/qwen38-27b-qlora-v0.1.yaml").read_text(encoding="utf-8")
    config = tmp_path / "bad.yaml"
    config.write_text(source + chr(10) + "max_steps: 3" + chr(10), encoding="utf-8")
    with pytest.raises(ValueError, match="smoke requires lora_rank=32"):
        check_config(config)
