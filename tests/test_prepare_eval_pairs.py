import json

import pytest

from scripts.prepare_eval_pairs import prepare_pairs


def _fixtures(tmp_path):
    rows = [{"messages": [{"role": "user", "content": "a"}]},
            {"messages": [{"role": "user", "content": "b"}]}]
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text("".join(json.dumps(r) + chr(10) for r in rows))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"count": 2, "samples": [
        {"sample_id": "a", "prompt_sha256": "aa"},
        {"sample_id": "b", "prompt_sha256": "bb"}]}))
    base = tmp_path / "base.jsonl"
    tuned = tmp_path / "tuned.jsonl"
    base.write_text("".join(json.dumps({**r, "response": "base " + str(i)}) + chr(10)
                            for i, r in enumerate(rows)))
    tuned.write_text("".join(json.dumps({**r, "response": "tuned " + str(i)}) + chr(10)
                             for i, r in enumerate(rows)))
    return rows, prompts, manifest, base, tuned


def test_paired_output_is_blind_and_has_separate_key(tmp_path):
    _, prompts, manifest, base, tuned = _fixtures(tmp_path)
    output, key = tmp_path / "blind.jsonl", tmp_path / "key.json"
    assert prepare_pairs(manifest, base, tuned, output, key, prompts) == 2
    pairs = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(json.loads(key.read_text())) == 2
    assert all("base" not in row and "adapter" not in row for row in pairs)
    with pytest.raises(FileExistsError):
        prepare_pairs(manifest, base, tuned, output, key, prompts)


def test_missing_output_is_rejected(tmp_path):
    _, prompts, manifest, base, tuned = _fixtures(tmp_path)
    base.write_text(base.read_text().splitlines()[0] + chr(10))
    with pytest.raises(ValueError, match="expected 2"):
        prepare_pairs(manifest, base, tuned, tmp_path / "o", tmp_path / "k", prompts)


def test_reordered_output_is_rejected(tmp_path):
    _, prompts, manifest, base, tuned = _fixtures(tmp_path)
    base.write_text(chr(10).join(base.read_text().splitlines()[::-1]) + chr(10))
    with pytest.raises(ValueError, match="mismatched prompt"):
        prepare_pairs(manifest, base, tuned, tmp_path / "o", tmp_path / "k", prompts)


def test_missing_prompt_context_is_rejected(tmp_path):
    _, prompts, manifest, base, tuned = _fixtures(tmp_path)
    base.write_text('{"response":"first"}' + chr(10) + '{"response":"second"}' + chr(10))
    with pytest.raises(ValueError, match="missing or mismatched prompt"):
        prepare_pairs(manifest, base, tuned, tmp_path / "o", tmp_path / "k", prompts)
