"""Synthetic-only tests of R59 counterfactual blank/unfinished probe."""
from __future__ import annotations

import unittest

from r59_history_recovery_probe import probe


def msg(role, content, status="completed"):
    return {"role": role, "content": content, "status": status}


class RecoveryProbeTests(unittest.TestCase):
    def test_potentially_recoverable_without_outputting_text(self):
        r = probe([{"history": [
            msg("assistant", "序幕"),
            msg("assistant", "", "canceled"),
            msg("user", "行动"),
        ]}])
        c = r["case_category_counts"]
        self.assertEqual(c["potentially_recoverable_by_blank_unfinished_exclusion"], 1)
        self.assertEqual(r["message_category_counts"]["unfinished_blank"], 1)
        self.assertNotIn("序幕", str(r))
        self.assertFalse(r["source_mutated"])

    def test_remaining_roles_and_nonblank_unfinished_hold(self):
        r = probe([
            {"history": [msg("assistant", "开场"), msg("user", "", "error"),
                         msg("assistant", "结束"), msg("user", "行动")]},
            {"history": [msg("assistant", "开场"), msg("user", "", "canceled"),
                         msg("assistant", "未完成内容", "pending"),
                         msg("user", "行动")]},
            {"history": [msg("assistant", "开场"), msg("user", "行动")]},
        ])
        c = r["case_category_counts"]
        self.assertEqual(c["filtered_repeated_roles"], 1)
        self.assertEqual(c["requires_other_semantic_or_structure_review"], 1)
        self.assertEqual(c["already_structurally_valid"], 1)

    def test_boundary_and_completed_blank_are_not_auto_accepted(self):
        r = probe([
            {"history": [msg("user", "行动"), msg("assistant", "", "failed"),
                         msg("assistant", "结束")]},
            {"history": [msg("assistant", "", "completed"), msg("user", "行动")]},
        ])
        c = r["case_category_counts"]
        self.assertEqual(c["filtered_boundary_invalid"], 1)
        self.assertEqual(c["requires_other_semantic_or_structure_review"], 1)
        self.assertEqual(c["invalid_without_unfinished_blank"], 1)
        self.assertNotIn("potentially_recoverable_by_blank_unfinished_exclusion", c)
        self.assertEqual(r["quality_v1_admitted"], 0)


if __name__ == "__main__":
    unittest.main()
