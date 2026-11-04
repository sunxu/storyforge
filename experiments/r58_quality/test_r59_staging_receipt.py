"""Synthetic-only receipt verification for legacy and suffix R59 staging."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from gold_source_context_stage import stage_source
from quality_v1 import canonical
from r59_owner_evidence_template import run as build_owner_template
from r59_staging_receipt import NEW_SCHEMA, NEW_STATUS, OLD_SCHEMA, valid_staging_receipt


class ReceiptTests(unittest.TestCase):
    def test_legacy(self):
        r = {"schema": OLD_SCHEMA, "status": "GOLD_SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
             "staged_file_sha256": "a" * 64}
        self.assertTrue(valid_staging_receipt(r, "a" * 64))
        self.assertFalse(valid_staging_receipt({**r, "status": "FAILED"}, "a" * 64))

    def test_new(self):
        r = {"schema": NEW_SCHEMA, "status": NEW_STATUS, "staged_file_sha256": "a" * 64,
             "context_staged": 72, "source_rows": 72, "context_structure_hold": 0,
             "source_histories_mutated": False, "original_staging_mutated": False,
             "quality_v1_admitted": 0, "training_authorized": False, "gpu_started": False,
             "source_context_file_sha256": "b" * 64,
             "previous_staged_file_sha256": "c" * 64}
        self.assertTrue(valid_staging_receipt(r, "a" * 64))
        for changed in [
            {"staged_file_sha256": "d" * 64}, {"context_staged": 71},
            {"quality_v1_admitted": 1}, {"source_histories_mutated": True},
            {"training_authorized": True}, {"status": "OTHER"}, {"schema": "UNKNOWN"},
        ]:
            self.assertFalse(valid_staging_receipt({**r, **changed}, "a" * 64))

    def test_new_stage_to_real_owner_template_integration(self):
        """The actual template run must accept a pinned suffix staging receipt."""
        source = {
            "case_id": "synthetic-only",
            "story_id": "synthetic-story",
            "session_id": "synthetic-session",
            "target_assistant_text": "原创回复",
            "target_sha256": hashlib.sha256("原创回复".encode()).hexdigest(),
            "history": [
                {"role": "assistant", "content": "开场", "status": "completed"},
                {"role": "user", "content": "下一步", "status": "completed"},
            ],
        }
        staged, _ = stage_source([source], "合成系统指令")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "private"
            root.mkdir(mode=0o700)
            stage_file = root / "staged.jsonl"
            safe_file = root / "staged-safe.json"
            payload = b"".join(canonical(row) + b"\\n" for row in staged)
            stage_file.write_bytes(payload)
            safe_file.write_text(json.dumps({
                "schema": NEW_SCHEMA,
                "status": NEW_STATUS,
                "source_rows": 1,
                "context_staged": 1,
                "context_structure_hold": 0,
                "staged_file_sha256": hashlib.sha256(payload).hexdigest(),
                "source_context_file_sha256": "b" * 64,
                "previous_staged_file_sha256": "c" * 64,
                "source_histories_mutated": False,
                "original_staging_mutated": False,
                "quality_v1_admitted": 0,
                "training_authorized": False,
                "gpu_started": False,
            }))
            os.chmod(stage_file, 0o600)
            os.chmod(safe_file, 0o600)
            result = build_owner_template(stage_file, safe_file, root / "output")
            self.assertEqual(result["staged_candidates"], 1)
            self.assertFalse(result["owner_evidence_populated"])
            self.assertEqual(result["quality_v1_admitted"], 0)

    def test_unknown_fails(self):
        self.assertFalse(valid_staging_receipt({"schema": "anything"}, "a" * 64))


if __name__ == "__main__":
    unittest.main()
