import json
from pathlib import Path
import tempfile
import unittest

from gold195_grok_web_export import export
from gold195_grok_web_triage import triage
from test_gold195_grok_web_pilot import task, review


class GrokWebTriageTests(unittest.TestCase):
    def test_case_labels_only_and_remediation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            folder = private / "pilot"
            export(repo, folder, [task(1), task(2), task(3)])
            def store(case, who, value):
                p = folder / ("case%02d-reviewer-%s.json" % (case, who))
                p.write_text(json.dumps(value, ensure_ascii=False))
                p.chmod(0o600)
            store(1, "A", review(task(1)["target_text"]))
            store(1, "B", review(task(1)["target_text"]))
            store(2, "A", review(task(2)["target_text"]))
            bad = review(task(2)["target_text"])
            bad["evidence_quotes"] = ["NOT_PRESENT_IN_TARGET"]
            store(2, "B", bad)
            severe = review(task(3)["target_text"])
            severe["severe_flags"]["hard_fact_or_ban"] = True
            store(3, "A", severe)
            store(3, "B", {"bad": "format"})
            result = triage(folder)
            self.assertEqual(result["cases"][0]["label"], "case01")
            self.assertTrue(result["cases"][0]["two_reviews_provisional_pass"])
            self.assertTrue(result["cases"][1]["retest_needed"])
            self.assertEqual(result["cases"][1]["reviewer_B"]["state"],
                             "EVIDENCE_QUOTE_NOT_IN_GOLD")
            self.assertTrue(result["cases"][2]["serious_issue_flagged"])
            self.assertEqual(result["cases"][2]["reviewer_B"]["state"], "MALFORMED")
            self.assertEqual(result["quality_v1_admitted"], 0)
            self.assertFalse(result["original_reviews_modified"])
            dumped = json.dumps(result)
            self.assertNotIn("PRIVATE_CASE", dumped)
            self.assertNotIn("PRIVATE_GOLD", dumped)
            self.assertNotIn("NOT_PRESENT_IN_TARGET", dumped)

    def test_missing_reviewer_is_not_approved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            folder = private / "pilot"
            export(repo, folder, [task(1), task(2), task(3)])
            result = triage(folder)
            self.assertEqual(result["case_count"], 3)
            self.assertTrue(all(case["retest_needed"] for case in result["cases"]))
            self.assertTrue(all(not case["two_reviews_provisional_pass"]
                                for case in result["cases"]))


if __name__ == "__main__":
    unittest.main()
