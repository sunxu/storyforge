import json
from pathlib import Path

from scripts.prepare_sft import convert


def test_only_last_assistant_has_loss(tmp_path: Path):
    source = tmp_path / "raw.jsonl"
    dest = tmp_path / "train.jsonl"
    source.write_text(json.dumps({"id": "test", "messages": [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "before"},
        {"role": "assistant", "content": "old"},
        {"role": "user", "content": "current"},
        {"role": "assistant", "content": "gold"},
    ]}) + "\n")
    assert convert(source, dest) == 1
    result = json.loads(dest.read_text())["messages"]
    assert [m.get("loss") for m in result if m["role"] == "assistant"] == [False, True]
    assert list(json.loads(dest.read_text())) == ["messages"]
