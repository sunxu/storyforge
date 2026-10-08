import csv
import hashlib
import json

import pytest

from scripts.export_context_blind_review import export_context_review


def test_context_csv_preserves_context_and_blindness(tmp_path):
    messages = [{"role": "system", "content": "background"}, 
                {"role": "user", "content": "earlier"},
                {"role": "assistant", "content": "history"},
                {"role": "user", "content": "latest"}]
    prompts, pairs, entries = [], [], []
    for i in range(15):
        value = json.dumps({"messages": messages}, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        sid = f"sample-{i:02d}"
        prompts.append({"messages": messages})
        pairs.append({"sample_id": sid, "prompt_sha256": digest,
                      "response_a": "text A", "response_b": "text B"})
        entries.append({"sample_id": sid, "prompt_sha256": digest})
    prompt_path = tmp_path / "prompts.jsonl"
    pairs_path = tmp_path / "pairs.jsonl"
    manifest_path = tmp_path / "manifest.json"
    prompt_path.write_text("".join(json.dumps(r) + chr(10) for r in prompts))
    pairs_path.write_text("".join(json.dumps(r) + chr(10) for r in pairs))
    manifest_path.write_text(json.dumps({"schema": "storyforge-blind-v1",
                                          "count": 15, "samples": entries}))
    out_dir = tmp_path / "review"
    assert export_context_review(prompt_path, manifest_path, pairs_path, out_dir) == 15
    sheets = sorted(out_dir.glob("StoryForge_Reviewer_*.csv"))
    assert len(sheets) == 3
    with sheets[0].open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 15
    assert rows[0]["当前用户输入"] == "latest"
    assert "background" in rows[0]["故事背景与系统规则"]
    assert "history" in rows[0]["历史对话"]
    assert rows[0]["回复A"] == "text A"
    assert "base" not in rows[0] and "adapter" not in rows[0]
    with pytest.raises(FileExistsError):
        export_context_review(prompt_path, manifest_path, pairs_path, out_dir)
