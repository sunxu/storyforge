import hashlib
import json

import pytest

from scripts.prepare_gold_comparisons import prepare_gold_comparisons


def _fixture(tmp_path, n=2):
    compiled, prompts, manifest, pairs, key = [], [], [], [], []
    for idx in range(n):
        context = [
            {"role": "system", "content": "世界规则"},
            {"role": "user", "content": f"动作 {idx}"},
        ]
        compiled.append({"messages": context + [{"role": "assistant", "content": f"GOLD {idx}"}]})
        prompts.append({"messages": context})
        digest = hashlib.sha256(json.dumps({"messages": context}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        sid = f"eval-{idx:03d}-{digest[:12]}"
        manifest.append({"sample_id": sid, "prompt_sha256": digest, "source_line": idx + 1})
        pairs.append({"sample_id": sid, "prompt_sha256": digest, "response_a": f"BASE {idx}", "response_b": f"ADAPTER {idx}"})
        key.append({"sample_id": sid, "a": "base", "b": "adapter"})
    paths = [tmp_path / x for x in ("test.jsonl", "prompts.jsonl", "manifest.json", "pairs.jsonl", "key.json")]
    for file, rows in ((paths[0], compiled), (paths[1], prompts), (paths[3], pairs)):
        file.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    paths[2].write_text(json.dumps({"schema": "storyforge-blind-v1", "count": n, "samples": manifest}), encoding="utf-8")
    paths[4].write_text(json.dumps(key), encoding="utf-8")
    return paths


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_exports_two_blind_pair_sets_with_exact_gold_and_separate_keys(tmp_path):
    source = _fixture(tmp_path)
    output = tmp_path / "output"
    assert prepare_gold_comparisons(*source, output, expected_count=2) == 2
    for model in ("base", "adapter"):
        pairs = _read_jsonl(output / f"gold-vs-{model}-blind-pairs.jsonl")
        keys = json.loads((output / f"gold-vs-{model}-answer-key.json").read_text())
        assert len(pairs) == len(keys) == 2
        for i, (row, key) in enumerate(zip(pairs, keys)):
            restored = {key["a"]: row["response_a"], key["b"]: row["response_b"]}
            assert restored == {"gold": f"GOLD {i}", model: f"{model.upper()} {i}"}
    audit = json.loads((output / "audit.json").read_text())
    assert audit["status"] == "SOURCE_ALIGNMENT_PASS__REVIEW_NOT_YET_PERFORMED"
    assert len(audit["input_sha256"]) == 5
    with pytest.raises(FileExistsError):
        prepare_gold_comparisons(*source, output, expected_count=2)


def test_rejects_prompt_mismatch_without_writing(tmp_path):
    source = _fixture(tmp_path)
    rows = _read_jsonl(source[1])
    rows[0]["messages"][1]["content"] = "tampered"
    source[1].write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    with pytest.raises(ValueError, match="exact prompt mismatch"):
        prepare_gold_comparisons(*source, tmp_path / "out", expected_count=2)
    assert not (tmp_path / "out").exists()


def test_rejects_bad_identity_map(tmp_path):
    source = _fixture(tmp_path)
    key = json.loads(source[4].read_text())
    key[0]["b"] = "base"
    source[4].write_text(json.dumps(key))
    with pytest.raises(ValueError, match="invalid original model mapping"):
        prepare_gold_comparisons(*source, tmp_path / "out", expected_count=2)


def test_rejects_modified_gold_source_order(tmp_path):
    source = _fixture(tmp_path)
    rows = _read_jsonl(source[0])
    rows.reverse()
    source[0].write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    with pytest.raises(ValueError, match="exact prompt mismatch"):
        prepare_gold_comparisons(*source, tmp_path / "out", expected_count=2)
