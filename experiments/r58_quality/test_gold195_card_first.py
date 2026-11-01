import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from gold195_card_first import bind, load_manifest, write_private


class CardFirstTests(unittest.TestCase):
    def packet(self, leading=False, world="world-a"):
        target = "原样目标"
        messages = [{"role": "user", "content": "玩家输入"},
                    {"role": "assistant", "content": target}]
        if leading:
            messages.insert(0, {"role": "assistant", "content": "孤立历史"})
        return {"case_id": "hidden", "story_uuid": world,
                "source_record_sha256": "b" * 64,
                "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
                "frozen_messages": messages}

    def card(self):
        body = "已审核的虚构世界设定"
        return {"story_uuid": "world-a", "card_text": body,
                "card_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "card_version": "v1", "source_ref": "owner-private-source"}

    def test_card_first_draft_preserves_target(self):
        p = self.packet()
        d, e = bind(p, {"world-a": self.card()})
        self.assertIsNone(e)
        self.assertEqual(d["messages"][0]["content"], self.card()["card_text"])
        self.assertEqual(d["messages"][1:], p["frozen_messages"][:-1])
        self.assertEqual(d["target_text"], "原样目标")
        self.assertFalse(d["training_admitted"])
        self.assertIsNone(d["split"])

    def test_leading_assistant_not_silently_removed(self):
        d, e = bind(self.packet(leading=True), {"world-a": self.card()})
        self.assertIsNone(d)
        self.assertEqual(e, "LEADING_ASSISTANT_NEEDS_CONTEXT_REVIEW")

    def test_missing_card_holds(self):
        d, e = bind(self.packet(), {})
        self.assertIsNone(d)
        self.assertEqual(e, "TRUSTED_CARD_NOT_PROVIDED")

    def test_source_hash_tamper(self):
        p = self.packet()
        p["target_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            bind(p, {"world-a": self.card()})

    def test_private_manifest_sha_check(self):
        with tempfile.TemporaryDirectory() as td:
            m = Path(td) / "cards.json"
            m.write_text(json.dumps({"schema": "r58_gold195_card_binding_private_v1",
                                     "cards": [self.card()]}, ensure_ascii=False))
            m.chmod(0o600)
            self.assertEqual(len(load_manifest(m)), 1)
            broken = self.card()
            broken["card_text"] = "改过文本"
            m.write_text(json.dumps({"schema": "r58_gold195_card_binding_private_v1",
                                     "cards": [broken]}, ensure_ascii=False))
            with self.assertRaises(ValueError):
                load_manifest(m)

    def test_private_path_requires_safe_dir(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with self.assertRaises(ValueError):
                write_private(p / "example.jsonl", p, [])


if __name__ == "__main__":
    unittest.main()
