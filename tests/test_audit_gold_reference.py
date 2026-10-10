import hashlib
import json

import pytest

from scripts.audit_gold_reference import audit


def _fixture(tmp_path):
    canonical, prompts, samples, triplets = [], [], [], []
    for index in range(20):
        context = [
            {"role": "system", "content": "world"},
            {"role": "user", "content": f"turn {index}"},
        ]
        gold = f"original gold {index}"
        digest = hashlib.sha256(
            json.dumps({"messages": context}, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        sid = f"eval-{index:03d}-{digest[:12]}"
        canonical.append({"messages": context + [{"role": "assistant", "content": gold}]})
        prompts.append({"messages": context})
        samples.append({"sample_id": sid, "prompt_sha256": digest, "source_line": index + 1})
        triplets.append({"id": sid, "index": index, "gold": gold})
    paths = [tmp_path / name for name in
             ("test.jsonl", "prompts.jsonl", "manifest.json", "triplets.json")]
    for path, data in zip(paths[:2], (canonical, prompts)):
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in data))
    paths[2].write_text(json.dumps({
        "schema": "storyforge-blind-v1", "count": 20, "samples": samples
    }))
    paths[3].write_text(json.dumps(triplets))
    return paths


def test_canonical_gold_matches_all_20(tmp_path):
    paths = _fixture(tmp_path)
    out = tmp_path / "audit.json"
    report = audit(*paths, out)
    assert report["status"] == "CANONICAL_GOLD_MATCH_PASS"
    assert report["exact_match_count"] == 20
    assert report["mismatch_count"] == 0
    assert report["candidate_is_canonical"] is True
    assert len(report["results"]) == 20
    assert len(report["source_sha256"]) == 4
    with pytest.raises(FileExistsError):
        audit(*paths, out)


def test_text_mismatch_fails_without_claiming_pass(tmp_path):
    paths = _fixture(tmp_path)
    triplets = json.loads(paths[-1].read_text())
    triplets[6]["gold"] += " different"
    paths[-1].write_text(json.dumps(triplets))
    report = audit(*paths, tmp_path / "audit.json")
    assert report["status"] == "CANONICAL_GOLD_MISMATCH__REBUILD_REVIEW_SHEETS"
    assert report["exact_match_count"] == 19
    assert report["mismatch_count"] == 1
    assert report["results"][6]["exact_match"] is False


def test_canonical_prompt_mismatch_rejected(tmp_path):
    paths = _fixture(tmp_path)
    rows = [json.loads(line) for line in paths[0].read_text().splitlines()]
    rows[0]["messages"][1]["content"] = "changed context"
    paths[0].write_text("".join(json.dumps(row) + "\n" for row in rows))
    out = tmp_path / "audit.json"
    with pytest.raises(ValueError, match="canonical prompt differs"):
        audit(*paths, out)
    assert not out.exists()


def test_candidate_mismatched_ids_rejected(tmp_path):
    paths = _fixture(tmp_path)
    triplets = json.loads(paths[-1].read_text())
    triplets[0]["id"] = triplets[1]["id"]
    paths[-1].write_text(json.dumps(triplets))
    with pytest.raises(ValueError, match="duplicate candidate"):
        audit(*paths, tmp_path / "audit.json")
