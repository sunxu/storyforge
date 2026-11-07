"""Synthetic-only S3B tests; no database or private Gold192 source needed."""
import hashlib
import json
import unittest
from unittest.mock import patch

from experiments.r58_quality import r60_reply_job_session_diagnostic as diagnostic


def synthetic_inputs():
    rows = [
        {
            "case_id": f"synthetic-{i:03}",
            "story_id": f"story-{i % 12:02}",
            "session_id": f"session-{i:03}",
            "turn_index": i + 1,
            "source_status": "EXACT_MATCH",
        }
        for i in range(192)
    ]
    raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    receipt = {
        "schema": diagnostic.SOURCE_SCHEMA,
        "status": diagnostic.SOURCE_STATUS,
        "gold192": 192,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "private_values_emitted": False,
        "artifacts": {
            "R60_SOURCE_LOCATORS_192.jsonl": {"records": 192, "sha256": digest},
        },
    }
    return raw, json.dumps(receipt).encode(), digest


class ReplyJobSessionDiagnosticTests(unittest.TestCase):
    def test_story_diverse_selection_is_deterministic_and_safe(self):
        raw, receipt, digest = synthetic_inputs()
        with patch.object(diagnostic, "EXPECTED_SOURCE_SHA", digest):
            targets, distinct_stories = diagnostic.select_diverse(raw, receipt)
        self.assertEqual(len(targets), 8)
        self.assertEqual(len(set(targets)), 8)
        self.assertEqual(distinct_stories, 12)
        self.assertEqual([x[0] for x in targets], [
            "session-000", "session-001", "session-002", "session-003",
            "session-004", "session-005", "session-006", "session-007",
        ])

    def test_source_tampering_or_wrong_pin_holds(self):
        raw, receipt, digest = synthetic_inputs()
        with self.assertRaisesRegex(ValueError, "SOURCE_PIN_INVALID"):
            diagnostic.select_diverse(raw, receipt)
        with (
            patch.object(diagnostic, "EXPECTED_SOURCE_SHA", digest),
            self.assertRaisesRegex(ValueError, "SOURCE_PIN_INVALID"),
        ):
            diagnostic.select_diverse(raw + b" ", receipt)

    def test_distinguish_absent_session_and_missing_turn(self):
        results = [(False, 0, 0), (True, 0, 0), (True, 1, 2)] + [(False, 0, 0)] * 5
        safe = diagnostic.summarize_diagnostic(results, 12)
        self.assertEqual(safe["session_not_found"], 6)
        self.assertEqual(safe["session_found_exact_turn_missing"], 1)
        self.assertEqual(safe["exact_turn_found"], 1)
        self.assertEqual(safe["matched_job_attempt_count_sum"], 2)
        self.assertEqual(safe["input_evidence_class_counts"]["UNKNOWN_NOT_REVIEWED"], 192)
        self.assertNotIn("session-000", json.dumps(safe))

    def test_inconsistent_session_turn_requires_hold(self):
        with self.assertRaisesRegex(ValueError, "INVALID_DATABASE_RESULT"):
            diagnostic.summarize_diagnostic([(False, 1, 2)] * 8, 12)


if __name__ == "__main__":
    unittest.main()
