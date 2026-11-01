import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_hf_review_batch import (
    input_record, make_package, check_output, audit,
)
from gold195_hf_review_gpu_runner import (
    make_prompt, parse_answer, atomic_write,
)
from gold195_assistant_first_full132 import build
from test_gold195_assistant_first_semantic_pilot import example
from gold195_source_review_packet import canon

REV = "a" * 40
MODEL = "Qwen/Qwen3-32B"


class HFReviewTests(unittest.TestCase):
    def setUp(self):
        self.comparisons = [example(i) for i in range(132)]
        self.tasks = build(self.comparisons)[1]
        self.source = input_record(self.tasks[0])

    def response(self, policy="PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS"):
        return {
            "policy": policy,
            "judgments": {k: "UNCERTAIN" for k in (
                "lost_identity_or_relationship", "lost_events_or_chronology",
                "lost_hard_rules_or_bans", "lost_player_agency_context",
                "essential_facts_reestablished_later",
                "source_card_sufficient_without_future_leakage")},
            "leading_assistant_exact_quotes": ["PRIVATE_LEADING_0"],
            "later_history_exact_quotes": [],
            "gold_exact_quotes": [],
            "reasoning": "根据首条 Assistant 的事实内容暂时建议保留，需继续进行技术和语义复核，不能自动批准删减历史。",
            "uncertainty": "尚无独立语义认证",
        }

    def test_private_package_does_not_expose_ids_or_approve(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            output = private / "hf-review"
            receipt = make_package(self.tasks, output, repo)
            self.assertEqual(receipt["source_rows_verified"], 132)
            self.assertEqual(receipt["quality_v1_admitted"], 0)
            self.assertFalse(receipt["hf_job_started"])
            self.assertNotIn("PRIVATE_LEADING_0", json.dumps(receipt))
            self.assertEqual((output / "input132.private.jsonl").stat().st_mode & 0o777, 0o600)
            lines = (output / "input132.private.jsonl").read_text().splitlines()
            self.assertEqual(len(lines), 132)
            self.assertNotIn("case_id", lines[0])
            self.assertNotIn("story_uuid", lines[0])
            self.assertIn("PRIVATE_LEADING_0", lines[0])
            with self.assertRaises(ValueError):
                make_package(self.tasks, output, repo)

    def test_valid_and_invalid_evidence_and_policy(self):
        response = parse_answer(json.dumps(self.response()), self.source, MODEL, REV)
        self.assertEqual(check_output(response, self.source), "PRESERVE_RECOMMENDATION")
        modified = copy.deepcopy(response)
        modified["leading_assistant_exact_quotes"] = ["NOT_IN_SOURCE"]
        self.assertEqual(check_output(modified, self.source), "EVIDENCE_QUOTE_INVALID")
        altered = self.response("CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW")
        with self.assertRaises(ValueError):
            parse_answer(json.dumps(altered), self.source, MODEL, REV)
        self.assertIn("PRIVATE_LEADING_0", make_prompt(self.source))

    def test_checkpoint_atomic_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "full001.json"
            response = parse_answer(json.dumps(self.response()), self.source, MODEL, REV)
            atomic_write(p, response)
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                atomic_write(p, response)

    def test_audit_missing_results_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            packaged = private / "packaged"
            make_package(self.tasks, packaged, repo)
            results = private / "results"
            results.mkdir(mode=0o700)
            first = parse_answer(json.dumps(self.response()), self.source, MODEL, REV)
            atomic_write(results / "full001.json", first)
            report = audit(packaged / "input132.private.jsonl", results, calibration_only=True)
            self.assertEqual(report["cases_expected"], 10)
            self.assertEqual(report["review_state_counts"]["MISSING_RESPONSE"], 9)
            self.assertEqual(report["status"], "REVIEW_RESULTS_INCOMPLETE_OR_UNCERTAIN__HOLD")
            self.assertEqual(report["quality_v1_admitted"], 0)
            self.assertNotIn("PRIVATE", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
