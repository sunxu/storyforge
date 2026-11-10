"""Synthetic R60 E0-E3 bridge tests, no private stories or historical records."""
from __future__ import annotations

import hashlib
import json

import pytest
import r60_experimental_e03_bridge as e03
from r60_experimental_shape_adapter import GATES, NOT_ACTUAL_SENT
from r60_p3_stage_pair_probe import Hold

SYSTEM = (
    "你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。\n"
    "保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。\n"
    "不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。"
)

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
        input_messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "assistant", "content": f"prior-{i}"},
            {"role": "user", "content": user},
        ]
        input_hash = hashlib.sha256(json.dumps(
            input_messages, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()).hexdigest()
        previews.append({
            "messages": [
                *[dict(m, loss=False) for m in input_messages],
                {"role": "assistant", "content": target, "loss": True},
            ],
            "metadata": {
                "status": "ENGINEERING_PREVIEW_NOT_ADMITTED",
                "source_target_sha256": digest,
                "input_messages_sha256": input_hash,
            },
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
