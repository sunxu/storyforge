"""Synthetic integration: reuse existing R59 preview packer + CPU shape check."""
from __future__ import annotations

import hashlib
import json

import pytest

from r59_sft_shape_preview import R27_SYSTEM_SHA256
from r60_experimental_shape_adapter import NOT_ACTUAL_SENT, make_preview
from r60_p3_stage_pair_probe import Hold

SYSTEM = (
    "你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。\n"
    "保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。\n"
    "不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。"
)


def test_system_fixture_pin():
    assert hashlib.sha256(SYSTEM.encode()).hexdigest() == R27_SYSTEM_SHA256


def test_bad_pair_fails_before_reading():
    with pytest.raises(Hold, match="PAIRS_OR_FROZEN_QUEUE_INVALID"):
        make_preview([], [], lambda *_: b"")


def test_duplicate_queue_fail_closed():
    queue = [{"case_id": "duplicate", "target_sha256": "a" * 64}] * 28
    with pytest.raises(Hold, match="FROZEN_QUEUE_IDENTITY_INVALID"):
        make_preview([{}], queue, lambda *_: b"")


def test_provenance_and_gate_contract():
    assert NOT_ACTUAL_SENT == "RECONSTRUCTED_NOT_ACTUAL_SENT"
    assert "ACTUAL_SENT" not in json.dumps({"provenance": NOT_ACTUAL_SENT}).replace(
        "NOT_ACTUAL_SENT", ""
    )
