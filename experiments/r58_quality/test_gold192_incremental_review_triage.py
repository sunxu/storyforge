"""Synthetic regression checks for Gold192 incremental review routing."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from gold192_incremental_review_triage import inspect
from legacy_gold_target_reuse import canonical


def fixtures(root, *, tamper=None):
    tasks = root / "tasks.jsonl"
    queue = root / "queue.jsonl"
    scope = root / "scope.jsonl"
    with (tasks.open("w", encoding="utf-8") as tf,
          queue.open("w", encoding="utf-8") as qf,
          scope.open("w", encoding="utf-8") as sf):
        for i in range(195):
            reason = (
                "WORLD_OR_TARGET_IDENTITY_HOLD" if i < 3
                else "CONTEXT_EQUIVALENCE_UNVERIFIED" if i < 108
                else "HISTORICAL_EVIDENCE_NOT_FULLY_BOUND"
            )
            excluded = i < 3
            messages = [
                {"role": "system", "content": "synthetic card"},
                {"role": "assistant", "content": "prior synthetic story"} if i % 2
                else {"role": "user", "content": "prior synthetic request"},
                {"role": "user", "content": "synthetic request"},
            ]
            # Keep valid alternation for the assistant-first branch only;
            # user-first synthetic cases should have no history.
            if i % 2 == 0:
                messages.pop(1)
            row = {
                "schema": "r58_gold195_six_dimension_review_task_private_v1",
                "case_id": f"synthetic-{i}",
                "story_uuid": f"synthetic-world-{i % 6}",
                "messages": messages,
                "target_text": "synthetic response",
                "target_sha256": hashlib.sha256(b"synthetic response").hexdigest(),
                "input_messages_sha256": hashlib.sha256(canonical(messages)).hexdigest(),
                "source_history_starts_with_assistant": bool(i % 2),
                "input_design_status": "PROPOSED_OFFLINE_CARD_NOT_APPROVED",
                "card_source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
                "quality_v1_admitted": False,
                "training_authorized": False,
                "review_status": "UNREVIEWED",
                "review_results": [],
                "split": None,
                "world_component_id": None,
            }
            if tamper == "leading" and i == 5:
                row["source_history_starts_with_assistant"] = False
            tf.write(json.dumps(row) + "\n")
            qf.write(json.dumps({
                "case_id": f"synthetic-{i}", "reason_code": reason,
            }) + "\n")
            sf.write(json.dumps({
                "case_id": f"synthetic-{i}",
                "scope_status": ("EXCLUDED_WORLD_ID_UNRESOLVED" if excluded
                                 else "CANDIDATE_ONLY_QUALITY_HOLD"),
                "quality_v1_admitted": False,
                "training_authorized": False,
            }) + "\n")
    return tasks, queue, scope


class Gold192IncrementalTriageTests(unittest.TestCase):
    def test_195_scoped_and_no_quality_admission(self):
        with tempfile.TemporaryDirectory() as td:
            result = inspect(*fixtures(Path(td)))
            self.assertEqual(result["counts"]["gold108_candidates"], 105)
            self.assertEqual(result["counts"]["gold87_candidates"], 87)
            self.assertEqual(result["counts"]["excluded_world_identity_unresolved"], 3)
            self.assertEqual(result["quality_v1_admitted"], 0)
            self.assertFalse(result["world_component_isolation_proven"])
            self.assertNotIn("synthetic-world", json.dumps(result))

    def test_leading_flag_tamper_holds(self):
        with (
            tempfile.TemporaryDirectory() as td,
            self.assertRaisesRegex(ValueError, "TRIAGE_LEADING_FLAG_INVALID"),
        ):
            inspect(*fixtures(Path(td), tamper="leading"))


if __name__ == "__main__":
    unittest.main()
