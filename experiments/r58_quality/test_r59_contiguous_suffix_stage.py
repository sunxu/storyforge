"""Synthetic-only tests for the pinned R59 suffix source stage."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from gold_source_context_stage import stage_source
from quality_v1 import canonical, sha
from r59_contiguous_suffix_stage import rebuild, run


def sample(cid, target, invalid_prefix=False):
    h = [
        {"role": "assistant", "content": "此前的故事", "status": "completed"},
        {"role": "user", "content": "玩家走近", "status": "completed"},
        {"role": "assistant", "content": "角色回应", "status": "completed"},
        {"role": "user", "content": "继续", "status": "completed"},
    ]
    if invalid_prefix:
        h = [{"role": "assistant", "content": "", "status": "failed"}, *h]
    return {
        "case_id": cid,
        "story_id": "world-1",
        "session_id": "session-1",
        "target_assistant_text": target,
        "target_sha256": sha(target.encode("utf-8")),
        "history": h,
    }


class SuffixStageTests(unittest.TestCase):
    def test_exact_suffix_only_preserves_target_and_original_ready(self):
        rows = [sample("A", "目标 A"), sample("B", "目标 B", invalid_prefix=True)]
        before = copy.deepcopy(rows)
        old, _ = stage_source(rows, "固定 System")
        built, safe = rebuild(rows, old, "固定 System")
        self.assertEqual(rows, before)
        self.assertEqual(safe["context_staged"], 2)
        self.assertEqual(safe["original_ready_unchanged"], 1)
        self.assertEqual(safe["previously_held_now_structurally_staged"], 1)
        self.assertEqual(built[0]["input_messages_sha256"], old[0]["input_messages_sha256"])
        self.assertEqual(built[1]["history_suffix_provenance"]["prefix_messages_excluded"], 1)
        self.assertEqual(built[1]["target_sha256"], rows[1]["target_sha256"])
        self.assertEqual(built[1]["messages"][-1]["content"], "继续")
        self.assertFalse(safe["private_values_emitted"])

    def test_invalid_final_message_holds(self):
        row = sample("B", "目标 B", invalid_prefix=True)
        row["history"][-1]["status"] = "failed"
        old, _ = stage_source([row], "固定 System")
        with self.assertRaisesRegex(ValueError, "FINAL_USER_NOT_VALID"):
            rebuild([row], old, "固定 System")

    def test_run_hash_pins_and_create_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "private"
            root.mkdir(mode=0o700)
            src = root / "input.jsonl"
            prev = root / "stage.jsonl"
            safe = root / "safe.json"
            rows = [sample("A", "目标 A"), sample("B", "目标 B", invalid_prefix=True)]
            old, meta = stage_source(rows, "固定 System")
            src_bytes = b"".join(canonical(x) + b"\n" for x in rows)
            old_bytes = b"".join(canonical(x) + b"\n" for x in old)
            src.write_bytes(src_bytes)
            prev.write_bytes(old_bytes)
            meta.update({
                "source_context_file_sha256": hashlib.sha256(src_bytes).hexdigest(),
                "staged_file_sha256": hashlib.sha256(old_bytes).hexdigest(),
                "system_prompt_sha256": sha("固定 System".encode("utf-8")),
            })
            safe.write_text(json.dumps(meta), encoding="utf-8")
            for file in (src, prev, safe):
                os.chmod(file, 0o600)
            dest = root / "new-stage"
            result = run(src, prev, safe, dest)
            self.assertEqual(result["context_staged"], 2)
            self.assertEqual(result["previously_held_now_structurally_staged"], 1)
            self.assertEqual((dest / "GOLD_SOURCE_STAGING_PRIVATE.jsonl").stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                run(src, prev, safe, dest)
            self.assertNotIn("目标 B", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
