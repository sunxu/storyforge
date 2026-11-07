"""Synthetic tests for private E0-E3 review packet preparation."""
from __future__ import annotations

import hashlib

import pytest
from quality_v1 import FLOORS, SEVERE, canonical, sha
from r59_sft_shape_preview import R27_SYSTEM_SHA256
from r60_experimental_semantic_review import QUESTIONS, prepare
from r60_experimental_shape_adapter import GATES, NOT_ACTUAL_SENT
from r60_p3_stage_pair_probe import Hold

SYSTEM = (
    "你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。\n"
    "保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。\n"
    "不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。"
)


def fixtures():
    assert sha(SYSTEM.encode()) == R27_SYSTEM_SHA256
    locators, previews = [], []
    for i in range(3):
        target = f"synthetic assistant {i}"
        th = hashlib.sha256(target.encode()).hexdigest()
        input_messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "assistant", "content": f"synthetic previous {i}"},
            {"role": "user", "content": f"synthetic user {i}"},
        ]
        previews.append({
            "messages": [
                *[dict(m, loss=False) for m in input_messages],
                {"role": "assistant", "content": target, "loss": True},
            ],
            "metadata": {
                "status": "ENGINEERING_PREVIEW_NOT_ADMITTED",
                "source_target_sha256": th,
                "input_messages_sha256": sha(canonical(input_messages)),
            },
        })
        locators.append({
            "case_id": f"synthetic_case_{i}",
            "source_target_sha256": th,
            "context_provenance": NOT_ACTUAL_SENT,
            "packet_target_exact_equal": True,
            "packet_current_user_exact_equal": True,
            "gates": {g: "HOLD_UNREVIEWED" for g in GATES},
            "packet_source_sha256": "a" * 64,
            "packet_case_locator": f"synthetic:{i}",
            "packet_snapshot_sha256": "b" * 64,
            "stage_file_sha256": "c" * 64,
        })
    return locators, previews


def test_three_reviews_prepared_without_minting_decisions():
    locators, previews = fixtures()
    packets, safe = prepare(locators, previews)
    assert safe["review_packets"] == 3
    assert safe["owner_e0_e3_attestations_created"] == 0
    assert safe["quality_v1_admitted"] == 0
    assert packets[0]["quality_floors"] == FLOORS
    assert packets[0]["severe_flag_names"] == list(SEVERE)
    assert set(packets[0]["review_questions"]) == set(QUESTIONS)
    assert packets[0]["gate_decisions"]["E2_TARGET_SEMANTICS"]["decision"] == "HOLD_UNREVIEWED"
    assert packets[0]["review_record"]["semantic_decision"] is None
    assert packets[0]["context_provenance"] == NOT_ACTUAL_SENT


def test_modified_target_rejected():
    locators, previews = fixtures()
    previews[0]["messages"][-1]["content"] = "tampered"
    with pytest.raises((Hold, ValueError)):
        prepare(locators, previews)


def test_packet_mismatch_rejected():
    locators, previews = fixtures()
    locators[0]["packet_current_user_exact_equal"] = False
    with pytest.raises(Hold, match="E03_LINKAGE_OR_GATE_DRIFT"):
        prepare(locators, previews)


def test_no_duplicate_cases():
    locators, previews = fixtures()
    locators[1]["case_id"] = locators[0]["case_id"]
    with pytest.raises(Hold, match="E03_LINKAGE_OR_GATE_DRIFT"):
        prepare(locators, previews)
