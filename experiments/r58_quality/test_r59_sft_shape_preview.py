import hashlib
import json
import unittest

from r59_sft_shape_preview import (
    PreviewHold,
    R27_SYSTEM_SHA256,
    build_preview,
)

SYSTEM = (
    "你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。\n"
    "保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。\n"
    "不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。"
)


def stage(history=None):
    history = history or [
        {"role": "user", "content": "玩家输入"},
        {"role": "assistant", "content": "历史回复"},
        {"role": "user", "content": "当前输入"},
    ]
    messages = [{"role": "system", "content": SYSTEM}, *history]
    target = "目标回复"
    return {
        "schema": "storyforge-quality-v1-source-staging-private-v1",
        "status": "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
        "case_id": "private-case",
        "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
        "target_text": target,
        "messages": messages,
        "input_messages_sha256": hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


class R59SFTShapePreviewTests(unittest.TestCase):
    def test_approved_prompt_hash_is_exact(self):
        self.assertEqual(
            hashlib.sha256(SYSTEM.encode("utf-8")).hexdigest(),
            R27_SYSTEM_SHA256,
        )
        self.assertEqual(len(SYSTEM.encode("utf-8")), 449)

    def test_preserves_assistant_first_history_and_last_only_loss(self):
        row = stage([
            {"role": "assistant", "content": "开头助手上下文"},
            {"role": "user", "content": "玩家接续"},
        ])
        packed, safe = build_preview([row])
        messages = packed[0]["messages"]
        self.assertEqual([m["role"] for m in messages],
                         ["system", "assistant", "user", "assistant"])
        self.assertEqual([m["loss"] for m in messages], [False, False, False, True])
        self.assertEqual(messages[-1]["content"], "目标回复")
        self.assertEqual(safe["assistant_first_histories"], 1)
        self.assertEqual(safe["historical_messages_preserved"], 2)
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertFalse(safe["training_authorized"])

    def test_preserves_user_first_history(self):
        packed, safe = build_preview([stage()])
        self.assertEqual(packed[0]["messages"][-1]["loss"], True)
        self.assertEqual(safe["preview_rows"], 1)

    def test_unapproved_or_wrong_system_bytes_hold(self):
        row = stage()
        row["messages"][0]["content"] = "not approved"
        with self.assertRaises(PreviewHold):
            build_preview([row])

    def test_target_tampering_holds(self):
        row = stage()
        row["target_text"] = "changed target"
        with self.assertRaises(PreviewHold):
            build_preview([row])

    def test_repeated_case_or_target_holds(self):
        row = stage()
        duplicate = dict(row)
        with self.assertRaises(PreviewHold):
            build_preview([row, duplicate])

    def test_hold_rows_are_not_emitted(self):
        row = stage()
        held = {"status": "SOURCE_STRUCTURE_HOLD", "case_id": "private-held"}
        packed, safe = build_preview([row, held])
        self.assertEqual(len(packed), 1)
        self.assertEqual(safe["preview_rows"], 1)


if __name__ == "__main__":
    unittest.main()
