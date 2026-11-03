import hashlib
import json
import stat
import tempfile
import unittest
from pathlib import Path

from r59_sft_collator_cpu import MODEL_REVISION, validate_preview_row, write_safe_report

SYSTEM = (
    "你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。\n"
    "保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。\n"
    "不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。"
)


def row():
    target = "目标回复"
    source_messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "assistant", "content": "history"},
        {"role": "user", "content": "current"},
    ]
    input_digest = hashlib.sha256(json.dumps(
        source_messages, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "messages": [
            {"role": "system", "content": SYSTEM, "loss": False},
            {"role": "assistant", "content": "history", "loss": False},
            {"role": "user", "content": "current", "loss": False},
            {"role": "assistant", "content": target, "loss": True},
        ],
        "metadata": {
            "source_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
            "input_messages_sha256": input_digest,
            "status": "ENGINEERING_PREVIEW_NOT_ADMITTED",
        },
    }


class R59SFTCollatorInputTests(unittest.TestCase):
    def test_qwen_model_revision_is_immutable(self):
        self.assertEqual(
            MODEL_REVISION,
            "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
        )

    def test_prompt_fixture_matches_r27_pin(self):
        self.assertEqual(
            hashlib.sha256(SYSTEM.encode("utf-8")).hexdigest(),
            "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83",
        )

    def test_valid_assistant_first_preview_row(self):
        self.assertEqual(validate_preview_row(row()), 4)

    def test_rejects_historical_supervision(self):
        item = row()
        item["messages"][1]["loss"] = True
        with self.assertRaises(ValueError):
            validate_preview_row(item)

    def test_rejects_nonfinal_target_loss(self):
        item = row()
        item["messages"][-1]["loss"] = False
        with self.assertRaises(ValueError):
            validate_preview_row(item)

    def test_rejects_target_hash_mismatch(self):
        item = row()
        item["metadata"]["source_target_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_preview_row(item)

    def test_rejects_consecutive_roles(self):
        item = row()
        item["messages"][2]["role"] = "assistant"
        with self.assertRaises(ValueError):
            validate_preview_row(item)

    def test_rejects_nonpreview_metadata(self):
        item = row()
        item["metadata"]["status"] = "ADMITTED"
        with self.assertRaises(ValueError):
            validate_preview_row(item)

    def test_safe_report_is_private_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "safe.json"
            report = {"status": "PASS", "private_values_emitted": False}
            write_safe_report(path, report)
            self.assertEqual(json.loads(path.read_text()), report)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                write_safe_report(path, report)


if __name__ == "__main__":
    unittest.main()
