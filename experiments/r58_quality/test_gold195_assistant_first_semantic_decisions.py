import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_assistant_first_semantic_decisions import (
    blank, evaluate, read_jsonl, verified_tasks, write_new,
)
from gold195_source_review_packet import canon


def task(i):
    original = [{"role": "assistant", "content": "LEADING_PRIVATE_" + str(i)},
                {"role": "user", "content": "USER_PRIVATE_" + str(i)},
                {"role": "assistant", "content": "REPLY_PRIVATE_" + str(i)}]
    target = "FROZEN_PRIVATE_" + str(i)
    return {
        "schema": "r58_gold195_assistant_first_semantic_pilot_private_v1",
        "pilot_label": "pilot%02d" % (i + 1),
        "story_uuid": "world-" + str(i),
        "source_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
        "original_history_sha256": hashlib.sha256(canon(original)).hexdigest(),
        "proposed_history_sha256": hashlib.sha256(canon(original[1:])).hexdigest(),
        "leading_assistant_sha256": hashlib.sha256(original[0]["content"].encode()).hexdigest(),
        "first_assistant_message": original[0]["content"],
        "original_history": original,
        "candidate_history_after_drop": original[1:],
        "frozen_target_text": target,
        "review_status": "UNREVIEWED",
        "recommended_policy": "HOLD_PENDING_SEMANTIC_REVIEW",
        "approved_history_transform": False,
        "quality_v1_admitted": False,
        "training_candidate_messages": None,
        "training_authorized": False,
    }


class SemanticDecisionTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [task(i) for i in range(10)]

    def test_blank_templates_are_not_reviews(self):
        rows = [blank(t) for t in self.tasks]
        report = evaluate(self.tasks, rows)
        self.assertEqual(report["reviewed_cases"], 0)
        self.assertEqual(report["review_states"]["unreviewed"], 10)
        self.assertFalse(report["history_truncation_approved"])
        self.assertEqual(report["quality_v1_admitted"], 0)
        self.assertNotIn("PRIVATE_", json.dumps(report))

    def test_completed_hold_and_preserve(self):
        rows = [blank(t) for t in self.tasks]
        rows[0].update({
            "policy": "HOLD_CONTEXT_UNRECOVERABLE",
            "review_completed": True,
            "reviewer_label": "human1",
            "reasoning": "首条回复携带未由后续重新说明的事实，因此保留 HOLD 不建议截断。",
            "leading_assistant_exact_quotes": ["LEADING_PRIVATE_0"],
        })
        rows[1].update({
            "policy": "PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS",
            "review_completed": True,
            "reviewer_label": "human1",
            "reasoning": "首条回复是历史关键部分，保留是候选方案，仍须单独验证运行时。",
            "leading_assistant_exact_quotes": ["LEADING_PRIVATE_1"],
        })
        result = evaluate(self.tasks, rows)
        self.assertEqual(result["reviewed_cases"], 2)
        self.assertEqual(result["quality_v1_admitted"], 0)

    def test_drop_recommendation_requires_all_facts(self):
        rows = [blank(t) for t in self.tasks]
        d = rows[0]
        d.update({
            "policy": "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW",
            "review_completed": True,
            "reviewer_label": "human1",
            "reasoning": "首段中的全部有效信息在后续历史和世界卡中明确重复，并无时序泄漏风险。",
            "leading_assistant_exact_quotes": ["LEADING_PRIVATE_0"],
        })
        with self.assertRaises(ValueError):
            evaluate(self.tasks, rows)
        for k in list(d["judgments"])[:4]:
            d["judgments"][k] = "NO"
        d["judgments"]["essential_facts_reestablished_later"] = "YES"
        d["judgments"]["source_card_sufficient_without_future_leakage"] = "YES"
        result = evaluate(self.tasks, rows)
        self.assertFalse(result["history_truncation_approved"])
        self.assertEqual(result["reviewed_cases"], 1)
        changed = copy.deepcopy(rows)
        changed[0]["leading_assistant_exact_quotes"] = ["invented"]
        with self.assertRaises(ValueError):
            evaluate(self.tasks, changed)

    def test_private_write_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            path = private / "decisions.jsonl"
            write_new(path, repo, [blank(t) for t in self.tasks])
            self.assertEqual(len(read_jsonl(path, 10)), 10)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                write_new(path, repo, [])
            with self.assertRaises(ValueError):
                write_new(repo / "bad.jsonl", repo, [])

    def test_source_mismatch_holds(self):
        rows = copy.deepcopy(self.tasks)
        rows[0]["frozen_target_text"] = "changed"
        with self.assertRaises(ValueError):
            verified_tasks(rows)


if __name__ == "__main__":
    unittest.main()
