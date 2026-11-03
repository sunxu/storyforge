"""Synthetic-only Supabase Gold context staging tests (no private source)."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from quality_v1 import sha
from gold_source_context_stage import StageHold, run, stage_source


def sample(cid="case-1"):
    target = "她递来一封信，等待玩家决定。"
    return {
        "case_id": cid,
        "story_id": "story-1",
        "session_id": "session-1",
        "target_sha256": sha(target.encode("utf-8")),
        "target_assistant_text": target,
        "history": [
            {"role": "assistant", "content": "先前的角色台词。", "status": "completed"},
            {"role": "user", "content": "我接下来怎么办？", "status": "completed"},
        ],
    }


class StageTests(unittest.TestCase):
    def test_stage_context_without_making_up_reviewer_evidence(self):
        rows, safe = stage_source([sample()], "通用原创虚构剧情系统提示。")
        self.assertEqual(safe["context_staged"], 1)
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertFalse(safe["reviewer_scores_imported"])
        self.assertEqual(rows[0]["messages"][1]["role"], "assistant")
        self.assertIsNone(rows[0]["world_component_id"])
        self.assertIsNone(rows[0]["split"])
        self.assertIsNone(rows[0]["reviews"])
        self.assertFalse(rows[0]["historical_system_prompt_verified"])

    def test_future_or_repeated_role_is_not_silently_cleaned(self):
        a = sample()
        a["history"].append({
            "role": "user", "content": "重复用户消息", "status": "completed",
        })
        rows, safe = stage_source([a], "通用系统提示")
        self.assertEqual(safe["context_structure_hold"], 1)
        self.assertEqual(rows[0]["status"], "SOURCE_STRUCTURE_HOLD")
        self.assertNotIn("messages", rows[0])

    def test_target_hash_mismatch_holds(self):
        a = sample()
        a["target_assistant_text"] += "被改变"
        with self.assertRaisesRegex(StageHold, "SOURCE_TARGET_IDENTITY_INVALID"):
            stage_source([a], "系统")

    def test_duplicate_target_holds(self):
        a = sample()
        b = copy.deepcopy(a)
        b["case_id"] = "case-2"
        with self.assertRaisesRegex(StageHold, "SOURCE_TARGET_IDENTITY_INVALID"):
            stage_source([a, b], "系统")

    def test_private_output_and_system_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "private"
            parent.mkdir(mode=0o700)
            source = parent / "source.jsonl"
            prompt = parent / "prompt.txt"
            source.write_text(json.dumps(sample(), ensure_ascii=False) + "\n")
            prompt.write_text("通用原创虚构剧情 System 提示。")
            for path in (source, prompt):
                os.chmod(path, 0o600)
            digest = hashlib.sha256(prompt.read_bytes()).hexdigest()
            dest = parent / "out"
            safe = run(source, prompt, digest, dest)
            self.assertEqual(safe["context_staged"], 1)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
            self.assertEqual(
                stat.S_IMODE((dest / "GOLD_SOURCE_STAGING_PRIVATE.jsonl").stat().st_mode),
                0o600,
            )
            self.assertNotIn("她递来", json.dumps(safe, ensure_ascii=False))
            with self.assertRaisesRegex(StageHold, "OUTPUT_EXISTS"):
                run(source, prompt, digest, dest)
            with self.assertRaisesRegex(StageHold, "SYSTEM_PROMPT_PIN_MISMATCH"):
                run(source, prompt, "a" * 64, parent / "next")


if __name__ == "__main__":
    unittest.main()
