"""Synthetic fixtures for read-only all-blank history projection."""
from __future__ import annotations

import unittest

from r59_blank_history_projection import project


def m(role, content, status="completed"):
    return {"role": role, "content": content, "status": status}


class BlankProjectionTests(unittest.TestCase):
    def test_blank_filter_recovery_and_counts(self):
        result = project([{"history": [
            m("assistant", "开场"), m("assistant", "", "failed"),
            m("user", "行动"),
        ]}])
        self.assertEqual(result["case_counts"]["structurally_valid_after_all_blank_projection"], 1)
        self.assertEqual(result["case_counts"]["original_repeated_roles"], 1)
        self.assertEqual(result["case_counts"]["original_repeats_resolved_by_filter"], 1)
        self.assertEqual(result["message_counts"]["excluded_unfinished_blank"], 1)
        self.assertNotIn("开场", str(result))

    def test_created_repeated_roles_and_completed_blank(self):
        result = project([{"history": [
            m("assistant", "a"), m("user", "", "completed"),
            m("assistant", "b"), m("user", "c"),
        ]}])
        self.assertEqual(result["case_counts"]["repeated_roles_created_by_filter"], 1)
        self.assertEqual(result["case_counts"]["still_invalid_after_all_blank_projection"], 1)
        self.assertEqual(result["message_counts"]["excluded_completed_blank"], 1)

    def test_trailing_blank_boundary_and_unfinished_nonblank(self):
        result = project([
            {"history": [m("user", "x"), m("assistant", "", "failed")]},
            {"history": [m("assistant", "x", "pending"), m("user", "y")]},
        ])
        self.assertEqual(result["case_counts"]["structurally_valid_after_all_blank_projection"], 1)
        self.assertEqual(result["case_counts"]["still_invalid_after_all_blank_projection"], 1)
        self.assertEqual(result["message_counts"]["retained_unfinished_nonblank"], 1)

    def test_malformed_is_never_approved(self):
        result = project([{"history": [None, m("user", "hello")]}])
        self.assertEqual(result["case_counts"]["malformed_source_message_or_role"], 1)
        self.assertEqual(result["case_counts"]["still_invalid_after_all_blank_projection"], 1)
        self.assertFalse(result["source_mutated"])
        self.assertEqual(result["quality_v1_admitted"], 0)


if __name__ == "__main__":
    unittest.main()
