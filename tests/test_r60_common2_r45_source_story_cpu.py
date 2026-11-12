"""Synthetic R45 Common2 story gate tests; never check in real story IDs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/r60_common2_r45_source_story_cpu.py"
spec = importlib.util.spec_from_file_location("r45_common2_story", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(tmp_path, monkeypatch, overlap=None):
    paths = []
    for kind, n in (("train", 49), ("validation", 15)):
        p = tmp_path / (kind + ".jsonl")
        p.write_text("".join(json.dumps({"metadata": {"source_story_id": f"fake-{kind}-{i % 3}"}}) + "\n" for i in range(n)))
        os.chmod(p, 0o600)
        monkeypatch.setitem(m.PINS, kind, (hashlib.sha256(p.read_bytes()).hexdigest(), n))
        paths.append(p)
    stories = ["common-a", "common-b"]
    if overlap:
        stories[0] = f"fake-{overlap}-0"
    manifest = {
        "schema": m.RECOVERY_SCHEMA, "status": m.RECOVERY_STATUS,
        "train_admitted": 0,
        "cases": [{"story_id": stories[i], "assistant_message_id": f"target-{i}",
                   "last_three_exact_source_match": True} for i in range(2)],
    }
    p = tmp_path / "recovery.json"
    p.write_text(json.dumps(manifest))
    os.chmod(p, 0o600)
    return (*paths, p)


def test_no_overlap_still_semantic_train_hold(tmp_path, monkeypatch):
    report = m.audit(*fixture(tmp_path, monkeypatch))
    assert report["common2_r45_exact_story_disjoint_verified"] is True
    assert report["status"] == "COMMON2_R45_ORIGINAL_STORY_IDS_DISJOINT__SEMANTIC_TRAIN_HOLD"
    assert report["r45_train_rows_checked"] == 49
    assert report["r45_validation_rows_checked"] == 15
    assert report["r45_semantic_world_isolation_verified"] is False
    assert report["train_admitted"] == 0
    assert "common-a" not in json.dumps(report)


def test_train_validation_overlap_hold(tmp_path, monkeypatch):
    for split in ("train", "validation"):
        report = m.audit(*fixture(tmp_path, monkeypatch, overlap=split))
        assert report["status"] == "COMMON2_R45_ORIGINAL_STORY_OVERLAP__TRAIN_HOLD"
        assert report[f"{split}_story_overlap_count"] == 1
        assert report["train_admitted"] == 0


def test_hash_tamper_holds(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    paths[0].write_bytes(paths[0].read_bytes() + b" ")
    assert m.audit(*paths)["reason_code"] == "R45_ORIGINAL_SHA_HOLD"


def test_permissions_holds(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    os.chmod(paths[0], 0o644)
    assert m.audit(*paths)["reason_code"] == "PRIVATE_INPUT_MODE_SIZE_HOLD"


def test_duplicate_target_holds(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    doc = json.loads(paths[-1].read_text())
    doc["cases"][1]["assistant_message_id"] = doc["cases"][0]["assistant_message_id"]
    paths[-1].write_text(json.dumps(doc))
    assert m.audit(*paths)["reason_code"] == "COMMON2_DUPLICATE_TARGET_HOLD"
