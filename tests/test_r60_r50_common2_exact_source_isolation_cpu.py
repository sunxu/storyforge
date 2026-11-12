"""Synthetic-only tests; no R50 or Common2 private IDs in repository."""
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "r50_common2_check", ROOT / "scripts/r60_r50_common2_exact_source_isolation_cpu.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixtures(tmp_path, monkeypatch, overlap=None):
    r50 = []
    for i in range(50):
        r50.append({
            "case_id": f"fake-case-{i}",
            "source_story_id": f"fake-r50-story-{i%5}",
            "source_session_id": f"fake-r50-session-{i}",
            "cutoff_message_id": f"fake-r50-cutoff-{i}",
            "history_message_ids": [f"fake-r50-history-{i}"],
        })
    rpath = tmp_path / "r50.jsonl"
    rpath.write_text("".join(json.dumps(x) + "\n" for x in r50))
    os.chmod(rpath, 0o600)
    # Override frozen fixture receipt only for synthetic tests.
    monkeypatch.setitem(sys.modules[
        "scripts.r60_r50_original50_complement_cpu"].ORIGINAL_SHA,
        "provenance", hashlib.sha256(rpath.read_bytes()).hexdigest())
    monkeypatch.setitem(sys.modules[
        "scripts.r60_r50_original50_complement_cpu"].SIZE,
        "provenance", rpath.stat().st_size)
    cases = []
    for i in range(2):
        stories = f"fake-common2-story-{i}"
        sessions = f"fake-common2-session-{i}"
        histid = f"fake-common2-history-{i}"
        if overlap == "story" and i == 0:
            stories = r50[0]["source_story_id"]
        if overlap == "session" and i == 0:
            sessions = r50[0]["source_session_id"]
        if overlap == "message" and i == 0:
            histid = r50[0]["history_message_ids"][0]
        cases.append({
            "story_id": stories, "session_id": sessions,
            "assistant_message_id": f"fake-common2-target-{i}",
            "last_three_exact_source_match": True,
            "history_messages": [{"id": histid, "role": "user", "content": "fiction"}],
            "message_count_before_target": 1,
        })
    body = {
        "schema": m.RECOVERY_SCHEMA,
        "status": m.RECOVERY_STATUS,
        "train_admitted": 0, "cases": cases,
    }
    cpath = tmp_path / "common2.json"
    cpath.write_text(json.dumps(body))
    os.chmod(cpath, 0o600)
    return rpath, cpath


def test_disjoint_exact_keys_still_never_admits_training(tmp_path, monkeypatch):
    result = m.audit(*fixtures(tmp_path, monkeypatch))
    assert result["status"] == "R50_COMMON2_EXACT_KEYS_DISJOINT__SEMANTIC_R45_SEAL_HOLD"
    assert result["r50_original_sha_verified"] is True
    assert result["r50_cases_checked"] == 50
    assert result["common2_cases_checked"] == 2
    assert result["exact_source_id_disjoint_verified"] is True
    assert result["semantic_world_alias_isolation_verified"] is False
    assert result["r50_complete_exclusion_verified"] is False
    assert result["train_admitted"] == 0
    assert "fake-" not in json.dumps(result)


def test_overlapping_story_session_message_all_fail_closed(tmp_path, monkeypatch):
    for dimension in ("story", "session", "message"):
        result = m.audit(*fixtures(tmp_path, monkeypatch, overlap=dimension))
        assert result["status"] == "R50_COMMON2_EXACT_SOURCE_OVERLAP__TRAIN_HOLD"
        assert result[f"exact_{dimension}_overlap_count"] == 1
        assert result["exact_source_id_disjoint_verified"] is False
        assert result["train_admitted"] == 0


def test_wrong_recovery_status_holds(tmp_path, monkeypatch):
    a, b = fixtures(tmp_path, monkeypatch)
    data = json.loads(b.read_text())
    data["status"] = "NOT_THE_FROZEN_RECOVERY"
    b.write_text(json.dumps(data))
    result = m.audit(a, b)
    assert result["reason_code"] == "COMMON2_RECOVERY_CONTRACT_HOLD"
    assert result["exact_source_id_disjoint_verified"] is False


def test_private_mode_and_wrong_source_hash_holds(tmp_path, monkeypatch):
    a, b = fixtures(tmp_path, monkeypatch)
    os.chmod(a, 0o644)
    assert m.audit(a, b)["status"] == "R50_COMMON2_EXACT_ISOLATION_HOLD"
    os.chmod(a, 0o600)
    a.write_bytes(a.read_bytes() + b" ")
    assert m.audit(a, b)["reason_code"] == "ORIGINAL_SHA_HOLD"
