import json
from pathlib import Path

import pytest

from scripts.hf_cpu_preflight import check_data


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
