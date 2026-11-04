"""Synthetic-only checks for the private-safe history diagnostic."""
from __future__ import annotations

import unittest

from r59_history_structure_diagnostic import diagnose


class DiagnosticTests(unittest.TestCase):
    def test_mixed_faults_are_reported_once_per_case(self):
        rows = [
            {"history": [
                {"role": "user", "content": "问题", "status": "completed"},
                {"role": "user", "content": "继续", "status": "pending"},
            ]},
            {"history": [
                {"role": "assistant", "content": "先前回复", "status": "completed"},
                {"role": "user", "content": "行动", "status": "completed"},
            ]},
            {"history": [
                {"role": "assistant", "content": "", "status": None},
            ]},
        ]
        result = diagnose(rows)
        self.assertEqual(result["source_rows"], 3)
        self.assertEqual(result["cases_with_violations"], 2)
        self.assertEqual(result["cases_without_violations"], 1)
        self.assertEqual(result["case_violation_counts"]["REPEATED_ROLE"], 1)
        self.assertEqual(result["case_violation_counts"]["STATUS_NOT_COMPLETED"], 2)
        self.assertEqual(result["case_violation_counts"]["CONTENT_EMPTY_OR_INVALID"], 1)
        self.assertEqual(result["case_violation_counts"]["HISTORY_LAST_ROLE_NOT_USER"], 1)
        self.assertEqual(result["message_status_category_counts"]["completed"], 3)
        self.assertFalse(result["private_values_emitted"])
        self.assertEqual(result["quality_v1_admitted"], 0)
        self.assertNotIn("问题", repr(result))

    def test_non_list_and_non_object_are_classified(self):
        r = diagnose([
            {"history": None},
            {"history": []},
            {"history": [None, {"role": "user", "content": "hi", "status": "completed"}]},
        ])
        self.assertEqual(r["cases_with_violations"], 3)
        self.assertEqual(r["case_violation_counts"]["HISTORY_NOT_LIST"], 1)
        self.assertEqual(r["case_violation_counts"]["HISTORY_EMPTY"], 1)
        self.assertEqual(r["case_violation_counts"]["MESSAGE_NOT_OBJECT"], 1)

    def test_invalid_role_and_status_are_classified(self):
        r = diagnose([{"history": [
            {"role": "tool", "content": "x", "status": 1},
            {"role": "user", "content": "y"},
        ]}])
        self.assertEqual(r["case_violation_counts"]["ROLE_INVALID"], 1)
        self.assertEqual(r["case_violation_counts"]["STATUS_NOT_COMPLETED"], 1)
        self.assertEqual(r["message_status_category_counts"]["other_type"], 1)
        self.assertEqual(r["message_status_category_counts"]["null_or_missing"], 1)


if __name__ == "__main__":
    unittest.main()
