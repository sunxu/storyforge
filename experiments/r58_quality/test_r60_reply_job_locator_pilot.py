"""Synthetic-only tests: Gold192 source pin and Reply Job metadata pilot."""
import hashlib
import json
import unittest

from experiments.r58_quality.r60_reply_job_locator_pilot import (
    select_targets,
    summarize,
)


def synthetic_source():
    rows = [
        {"case_id": f"c{i:03}", "session_id": f"private-session-{i}",
         "turn_index": i + 1, "source_status": "EXACT_MATCH"}
        for i in range(192)
    ]
    raw = ("\n".join(json.dumps(x) for x in rows) + "\n").encode()
    safe = {
        "schema": "r60_gold192_supabase_extract_v3_safe_v1",
        "status": "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED",
        "gold192": 192,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "private_values_emitted": False,
        "artifacts": {
            "R60_SOURCE_LOCATORS_192.jsonl": {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "records": 192,
            },
        },
    }
    return raw, json.dumps(safe).encode()


class ReplyJobPilotTests(unittest.TestCase):
    def test_select_limited_and_pinned(self):
        raw, safe = synthetic_source()
        selected = select_targets(raw, safe, 8)
        self.assertEqual(len(selected), 8)
        self.assertEqual(selected[0], ("private-session-0", 1))

    def test_rejects_tampering_and_limits(self):
        raw, safe = synthetic_source()
        with self.assertRaisesRegex(ValueError, "SOURCE_PIN_INVALID"):
            select_targets(raw + b"\n", safe, 8)
        for n in (0, 9):
            with self.assertRaisesRegex(ValueError, "PILOT_LIMIT_INVALID"):
                select_targets(raw, safe, n)

    def test_metadata_summary_no_identifiers_or_promotion(self):
        result = summarize([(1, 2), (0, 0), (1, 1)], 3)
        self.assertEqual(result["reply_job_exact_locator_matches"], 2)
        self.assertEqual(result["matched_job_attempt_count_sum"], 3)
        self.assertIsNone(result["input_evidence_class_counts"]["A"])
        self.assertEqual(result["quality_v1_admitted"], 0)
        self.assertNotIn("private-session", json.dumps(result))

    def test_multiple_jobs_holds(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_REPLY_JOB_RESULT"):
            summarize([(2, 2)], 1)


if __name__ == "__main__":
    unittest.main()
