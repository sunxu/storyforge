import copy
import json
from pathlib import Path
import tempfile
import unittest

from gold195_assistant_first_full132 import build
from gold195_assistant_first_full132_decisions import blank, evaluate, verify
from gold195_assistant_first_semantic_pilot import read_comparisons, write_private
from gold195_assistant_first_semantic_decisions import write_new, read_jsonl
from test_gold195_assistant_first_semantic_pilot import example
from gold195_source_review_packet import canon


class Full132SemanticTests(unittest.TestCase):
    def setUp(self):
        self.rows = [example(i) for i in range(132)]
        self.receipt, self.tasks = build(self.rows)

    def test_all_132_and_all_worlds_are_included(self):
        self.assertEqual(self.receipt["review_tasks"], 132)
        self.assertEqual(self.receipt["distinct_worlds"], 13)
        self.assertEqual(self.receipt["semantic_reviews_completed"], 0)
        self.assertEqual([x["review_label"] for x in self.tasks],
                         ["full%03d" % i for i in range(1, 133)])
        self.assertEqual(len({x["case_id"] for x in self.tasks}), 132)
        self.assertTrue(all(x["training_candidate_messages"] is None for x in self.tasks))
        self.assertTrue(all(x["recommended_policy"] == "HOLD_PENDING_SEMANTIC_REVIEW"
                            for x in self.tasks))
        self.assertEqual(self.receipt["quality_v1_admitted"], 0)
        self.assertNotIn("PRIVATE_TARGET", json.dumps(self.receipt))

    def test_binding_and_all_blank_reviews(self):
        verify(self.tasks, self.rows)
        decisions = [blank(x) for x in self.tasks]
        summary = evaluate(self.tasks, decisions)
        self.assertEqual(summary["unreviewed_cases"], 132)
        self.assertEqual(summary["reviewed_cases"], 0)
        self.assertEqual(summary["quality_v1_admitted"], 0)
        changed = copy.deepcopy(self.tasks)
        changed[10]["frozen_target_text"] = "TAMPERED"
        with self.assertRaises(ValueError):
            verify(changed, self.rows)
        changed = copy.deepcopy(decisions)
        changed[25]["review_label"] = "full001"
        with self.assertRaises(ValueError):
            evaluate(self.tasks, changed)

    def test_review_policy_never_approves_truncation(self):
        decisions = [blank(x) for x in self.tasks]
        row = decisions[0]
        row["policy"] = "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW"
        row["reviewer_label"] = "real-person-or-model-id"
        row["reasoning"] = "原文对照确认首条事件在后续历史有明确复述，但仍需独立审核后才能批准历史修改。"
        row["review_completed"] = True
        row["leading_assistant_exact_quotes"] = ["PRIVATE_LEADING_0"]
        with self.assertRaises(ValueError):
            evaluate(self.tasks, decisions)
        for q in list(row["judgments"])[:4]:
            row["judgments"][q] = "NO"
        row["judgments"]["essential_facts_reestablished_later"] = "YES"
        row["judgments"]["source_card_sufficient_without_future_leakage"] = "YES"
        report = evaluate(self.tasks, decisions)
        self.assertEqual(report["reviewed_cases"], 1)
        self.assertFalse(report["history_truncation_approved"])
        self.assertEqual(report["quality_v1_admitted"], 0)
        row["leading_assistant_exact_quotes"] = ["INVALID_QUOTE"]
        with self.assertRaises(ValueError):
            evaluate(self.tasks, decisions)

    def test_local_private_files_and_existing_pilot_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            source = private / "comparisons.jsonl"
            source.write_bytes(b"".join(canon(x) + b"\n" for x in self.rows))
            source.chmod(0o600)
            verified = read_comparisons(source)
            _, tasks = build(verified)
            original = source.read_bytes()
            tasks_file = private / "full-tasks.jsonl"
            write_private(tasks_file, repo, tasks)
            decision_file = private / "full-decisions.jsonl"
            write_new(decision_file, repo, [blank(t) for t in tasks])
            self.assertEqual(len(read_jsonl(tasks_file, 132)), 132)
            self.assertEqual(len(read_jsonl(decision_file, 132)), 132)
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(all((p.stat().st_mode & 0o777) == 0o600
                                for p in [tasks_file, decision_file]))
            with self.assertRaises(ValueError):
                write_private(tasks_file, repo, tasks)
            with self.assertRaises(ValueError):
                write_new(decision_file, repo, [])


if __name__ == "__main__":
    unittest.main()
