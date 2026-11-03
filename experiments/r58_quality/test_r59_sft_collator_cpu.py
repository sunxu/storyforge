import hashlib
import unittest

from r59_sft_collator_cpu import validate_preview_row


def row():
    target = "目标回复"
    return {
        "messages": [
            {"role": "system", "content": "system", "loss": False},
            {"role": "assistant", "content": "history", "loss": False},
            {"role": "user", "content": "current", "loss": False},
            {"role": "assistant", "content": target, "loss": True},
        ],
        "metadata": {
            "source_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
            "status": "ENGINEERING_PREVIEW_NOT_ADMITTED",
        },
    }


class R59SFTCollatorInputTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
