import copy
import json
from pathlib import Path
import tempfile
import unittest

from gold195_assistant_first_grok_batches import (
    batch_cases, expected_manifest, export, inspect, label, packet,
    response_template, validate_review,
)
from gold195_assistant_first_full132 import build
from test_gold195_assistant_first_semantic_pilot import example


class GrokBatchTests(unittest.TestCase):
    def setUp(self):
        self.comparisons = [example(i) for i in range(132)]
        _, self.tasks = build(self.comparisons)

    def completed(self, n, i, policy="PRESERVE_LEADING_ASSISTANT_IF_RUNTIME_SUPPORTS"):
        case = batch_cases(self.tasks, n)[i - 1]
        response = response_template(label(n, i))
        response["policy"] = policy
        response["independent_reasoning"] = "这一条需要根据首条 Assistant 和后续历史逐字核实是否丢失人物关系，当前只是合成测试。"
        response["leading_assistant_exact_quotes"] = [
            case["first_assistant_message"]
        ]
        return response

    def test_11_disjoint_batches_cover_exactly_132(self):
        keys = []
        for n in range(1, 12):
            cases = batch_cases(self.tasks, n)
            self.assertEqual(len(cases), 12)
            keys += [x["case_id"] for x in cases]
        self.assertEqual(len(set(keys)), 132)
        self.assertEqual(set(keys), {x["case_id"] for x in self.tasks})
        p = packet(self.tasks[0], "B01-01").decode()
        self.assertIn("PRIVATE_LEADING_0", p)
        self.assertNotIn(self.tasks[0]["case_id"], p)
        self.assertNotIn(self.tasks[0]["story_uuid"], p)

    def test_missing_and_semantic_hold_blocks_next_export(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            first = private / "batch01"
            self.assertEqual(export(self.tasks, 1, first, repo), 13)
            self.assertEqual(len(list(first.iterdir())), 13)
            self.assertEqual((first / "manifest.private.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(inspect(self.tasks, 1, first, repo)["status"],
                             "BATCH_QUALITY_OR_EVIDENCE_HOLD")
            with self.assertRaises(ValueError):
                export(self.tasks, 2, private / "batch02", repo, first, True)
            for i in range(1, 13):
                response = self.completed(1, i)
                output = first / (label(1, i) + ".json")
                output.write_text(json.dumps(response, ensure_ascii=False))
                output.chmod(0o600)
            report = inspect(self.tasks, 1, first, repo)
            self.assertEqual(report["status"], "BATCH_VALIDATED__OWNER_GATE_REQUIRED")
            self.assertFalse(report["next_batch_automatically_authorized"])
            with self.assertRaises(ValueError):
                export(self.tasks, 2, private / "batch02", repo, first, False)
            self.assertEqual(export(self.tasks, 2, private / "batch02", repo,
                                    first, True), 13)
            with self.assertRaises(ValueError):
                export(self.tasks, 2, private / "batch02", repo, first, True)

    def test_invalid_quote_and_drop_policy_stop(self):
        case = self.tasks[0]
        r = self.completed(1, 1)
        self.assertEqual(validate_review(r, case, "B01-01"),
                         "PRESERVE_RECOMMENDATION__RUNTIME_UNVERIFIED")
        altered = copy.deepcopy(r)
        altered["leading_assistant_exact_quotes"] = ["NOT_IN_PRIVATE_SOURCE"]
        self.assertEqual(validate_review(altered, case, "B01-01"),
                         "EVIDENCE_QUOTE_INVALID")
        altered = copy.deepcopy(r)
        altered["policy"] = "CONSIDER_DROP_ONLY_AFTER_EXPLICIT_FACT_REVIEW"
        self.assertEqual(validate_review(altered, case, "B01-01"),
                         "DROP_CLAIM_UNSUPPORTED_HOLD")
        for key in list(altered["judgments"])[:4]:
            altered["judgments"][key] = "NO"
        for key in list(altered["judgments"])[4:]:
            altered["judgments"][key] = "YES"
        altered["later_history_exact_quotes"] = ["PRIVATE_USER_0"]
        self.assertEqual(validate_review(altered, case, "B01-01"),
                         "PROVISIONAL_DROP_REVIEW__NOT_APPROVED")
        self.assertNotIn("PRIVATE_TARGET_0", json.dumps(expected_manifest(self.tasks, 1)))


if __name__ == "__main__":
    unittest.main()
