"""Synthetic R60 E0-E3 bridge tests, no private stories or historical records."""
from __future__ import annotations

import hashlib
import json

import pytest

import r60_experimental_e03_bridge as e03
from r60_experimental_shape_adapter import GATES, NOT_ACTUAL_SENT
from r60_p3_stage_pair_probe import Hold


def raw(rows):
    return b"".join(json.dumps(x, ensure_ascii=False).encode() + b"\n" for x in rows)


def fixtures(monkeypatch):
    packets = [{
        "schema": "synthetic-packet-v1", "world_card": {},
        "world_card_sha256": None, "world_card_source_kind": "synthetic",
        "world_card_review_status": "unknown",
        "world_card_approved_for_system": False,
        "cases": [],
    } for _ in range(13)]
    stage, tasks, previews = [], [], []
    for i in range(3):
        cid, user, target = f"synthetic-{i}", f"user-{i}", f"target-{i}"
        digest = hashlib.sha256(target.encode()).hexdigest()
        stage.append({
            "schema": "storyforge-quality-v1-source-staging-private-v1",
            "status": "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
            "case_id": cid, "target_sha256": digest,
        })
        packets[i]["cases"].append({
            "case_id": cid, "target_sha256": digest,
            "history": [], "current_user_text": user,
            "target_assistant_text": target,
        })
        tasks.append({
            "case_id": cid, "source_target_sha256": digest,
            "context_provenance": NOT_ACTUAL_SENT,
            "gates": {g: "HOLD_UNREVIEWED" for g in GATES},
        })
        previews.append({
            "messages": [
                {"role": "system", "content": "synthetic"},
                {"role": "user", "content": user},
                {"role": "assistant", "content": target},
            ],
            "metadata": {"source_target_sha256": digest},
        })
    p_raw, s_raw = raw(packets), raw(stage)
    monkeypatch.setattr(e03, "PACKETS_SHA", hashlib.sha256(p_raw).hexdigest())
    stage_sha = hashlib.sha256(s_raw).hexdigest()
    for task in tasks:
        task["stage_file_sha256"] = stage_sha
    return p_raw, s_raw, previews, tasks, stage_sha


def test_reuses_packet_inventory_and_does_not_admit(monkeypatch):
    p_raw, s_raw, previews, tasks, pin = fixtures(monkeypatch)
    private, safe = e03.bridge(p_raw, s_raw, previews, tasks, pin)
    assert safe["packet_assoc_exact_cases"] == 3
    assert safe["packet_target_exact_equal"] == 3
    assert safe["packet_user_exact_equal"] == 3
    assert safe["e0_e3_owner_review_complete"] == 0
    assert safe["quality_v1_admitted"] == 0
    assert all(p["gates"]["E0_SOURCE_AND_RIGHTS"] == "HOLD_UNREVIEWED"
               for p in private)


def test_target_mismatch_stays_visible_not_promoted(monkeypatch):
    p_raw, s_raw, previews, tasks, pin = fixtures(monkeypatch)
    packets = [json.loads(x) for x in p_raw.splitlines()]
    packets[0]["cases"][0]["target_assistant_text"] = "different"
    new_raw = raw(packets)
    monkeypatch.setattr(e03, "PACKETS_SHA", hashlib.sha256(new_raw).hexdigest())
    private, safe = e03.bridge(new_raw, s_raw, previews, tasks, pin)
    assert safe["packet_target_not_equal"] == 1
    assert private[0]["packet_target_exact_equal"] is False
    assert safe["quality_v1_admitted"] == 0


def test_changed_task_identity_rejected(monkeypatch):
    p_raw, s_raw, previews, tasks, pin = fixtures(monkeypatch)
    tasks[0]["gates"]["E0_SOURCE_AND_RIGHTS"] = "PASS"
    with pytest.raises(Hold, match="EXPERIMENTAL_TASK_IDENTITY_OR_GATE_DRIFT"):
        e03.bridge(p_raw, s_raw, previews, tasks, pin)
