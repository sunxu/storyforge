import json

import pytest

from scripts.audit_gold_token_lengths import calculate, gold_contents, percentile


class Tokenizer:
    def encode(self, text, add_special_tokens=False):
        assert not add_special_tokens
        return text.split()


def test_gold_token_stats_count_only_final_assistant(tmp_path):
    path = tmp_path / "train.jsonl"
    row = {"messages": [
        {"role": "system", "content": "unrelated very long text"},
        {"role": "user", "content": "continue"},
        {"role": "assistant", "content": "gold answer"},
    ]}
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    texts = gold_contents(path)
    assert texts == ["gold answer"]
    summary = calculate({"train": texts}, Tokenizer())
    assert summary["all"]["mean"] == 2
    assert summary["all"]["max"] == 2
    assert summary["all"]["over_128"] == 0


def test_percentile_linear_interpolation():
    assert percentile([1, 3, 5, 7], 50) == 4
    assert percentile([1, 3, 5, 7], 95) == pytest.approx(6.7)


def test_gold_validation_rejects_bad_tail(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"messages": [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "old"},
        {"role": "assistant", "content": "bad"},
    ]}) + "\n")
    with pytest.raises(ValueError, match="user/Gold assistant"):
        gold_contents(path)
