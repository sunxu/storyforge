import json

import pytest

from scripts.prepare_blind_eval import build_prompts


def test_blind_prompt_export_excludes_gold_and_loss(tmp_path):
    source = tmp_path / "validation.jsonl"
    sample = {"messages": [
        {"role": "system", "content": "instructions"},
        {"role": "user", "content": "past"},
        {"role": "assistant", "content": "historical", "loss": False},
        {"role": "user", "content": "continue"},
        {"role": "assistant", "content": "SECRET_GOLD", "loss": True},
    ]}
    source.write_text(json.dumps(sample) + "\n", encoding="utf-8")
    target = tmp_path / "prompts.jsonl"
    manifest = tmp_path / "manifest.json"
    assert build_prompts(source, target, manifest) == 1
    text = target.read_text(encoding="utf-8")
    assert "SECRET_GOLD" not in text
    assert '"loss"' not in text
    assert json.loads(text)["messages"][-1]["role"] == "user"
    assert json.loads(manifest.read_text())["count"] == 1
    with pytest.raises(FileExistsError):
        build_prompts(source, target, manifest)


def test_blind_prompt_export_rejects_bad_tail(tmp_path):
    source = tmp_path / "validation.jsonl"
    source.write_text(json.dumps({"messages": [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "not explicitly gold"},
    ]}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Gold"):
        build_prompts(source, tmp_path / "o", tmp_path / "m")
