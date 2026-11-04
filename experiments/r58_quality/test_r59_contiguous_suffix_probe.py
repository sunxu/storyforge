"""Synthetic-only tests for strict, non-splicing history suffix probe."""
from __future__ import annotations

import unittest

from r59_contiguous_suffix_probe import probe


def m(role, content="word", status="completed"):
    return {"role": role, "content": content, "status": status}


class SuffixTests(unittest.TestCase):
    def test_full_and_proper_suffix(self):
        rows = [
            {"history": [m("assistant"), m("user")]},
            {"history": [m("assistant"), m("user", "", "failed"), m("assistant"), m("user")]},
            {"history": [m("assistant"), m("assistant"), m("user")]},
        ]
        c = probe(rows)["case_category_counts"]
        self.assertEqual(c["fully_valid_unchanged_history"], 1)
        self.assertEqual(c["proper_suffix_only"], 2)
        self.assertEqual(c["at_least_one_prior_assistant_turn"], 3)
        self.assertNotIn("at_least_four_contiguous_messages", c)

    def test_last_user_only_not_successful_recovery(self):
        r = probe([{"history": [m("assistant", "", "failed"), m("user")]},
                   {"history": [m("assistant"), m("user", "", "failed")]},
                   {"history": [m("assistant"), m("user"), m("assistant", "x", "failed")]}])
        c = r["case_category_counts"]
        self.assertEqual(c["last_user_only_no_assistant_context"], 1)
        self.assertEqual(c["last_message_invalid_or_not_user"], 2)
        self.assertNotIn("at_least_one_prior_assistant_turn", c)
        self.assertEqual(r["longest_valid_suffix_messages_distribution"], {"0": 2, "1": 1})

    def test_no_mutation_or_private_text(self):
        rows = [{"history": [m("assistant", "秘密中文"), m("user", "行动")]}]
        before = repr(rows)
        r = probe(rows)
        self.assertEqual(before, repr(rows))
        self.assertNotIn("秘密中文", repr(r))
        self.assertFalse(r["projected_histories_persisted"])
        self.assertEqual(r["quality_v1_admitted"], 0)


if __name__ == "__main__":
    unittest.main()
