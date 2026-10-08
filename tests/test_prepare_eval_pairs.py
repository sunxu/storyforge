import json

import pytest

from scripts.prepare_eval_pairs import prepare_pairs


def test_prepare_pairs_keeps_grader_blind_and_separate_key(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "count": 2,
        "samples": [{"sample_id": "a", "prompt_sha256": "ha"},
                    {"sample_id": "b", "prompt_sha256": "hb"}],
    }), encoding="utf-8")
    base = tmp_path / "base.jsonl"
    adapter = tmp_path / "adapter.jsonl"
    base.write_text('{"response":"base one"}\n{"response":"base two"}\n', encoding="utf-8")
    adapter.write_text('{"response":"tuned one"}\n{"response":"tuned two"}\n', encoding="utf-8")
    output = tmp_path / "blind.jsonl"
    key = tmp_path / "private-mapping.json"
    assert prepare_pairs(manifest, base, adapter, output, key) == 2
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    mapping = json.loads(key.read_text(encoding="utf-8"))
    assert len(rows) == len(mapping) == 2
    assert all("base" not in row.keys() and "adapter" not in row.keys() for row in rows)
    for i, row in enumerate(rows):
        candidates = {row["response_a"], row["response_b"]}
        assert candidates == {f"base {['one', 'two'][i]}", f"tuned {['one', 'two'][i]}"}
    with pytest.raises(FileExistsError):
        prepare_pairs(manifest, base, adapter, output, key)


def test_prepare_pairs_rejects_short_inference(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"count": 2, "samples": [
        {"sample_id": "a", "prompt_sha256": "aa"},
        {"sample_id": "b", "prompt_sha256": "bb"},
    ]}), encoding="utf-8")
    base = tmp_path / "base.jsonl"
    adapter = tmp_path / "adapter.jsonl"
    base.write_text('{"response":"only one"}\n', encoding="utf-8")
    adapter.write_text('{"response":"one"}\n{"response":"two"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="expected 2"):
        prepare_pairs(manifest, base, adapter, tmp_path / "blind", tmp_path / "secret")
