import json
from pathlib import Path
import tempfile
import unittest

from gold195_grok_web_export import export
from gold195_grok_web_followup import make_packets, write_packets
from gold195_grok_web_followup_validate import followup, check_arbiter
from test_gold195_grok_web_pilot import task, review


class FollowupVerdictTests(unittest.TestCase):
    def create(self, root):
        repo = root / "repo"
        repo.mkdir()
        private = root / "private"
        private.mkdir(mode=0o700)
        pilot = private / "pilot"
        export(repo, pilot, [task(1), task(2), task(3)])

        def store(case, who, obj):
            path = pilot / ("case%02d-reviewer-%s.json" % (case, who))
            path.write_text(json.dumps(obj))
            path.chmod(0o600)

        for who in "AB":
            store(1, who, review(task(1)["target_text"]))
        severe = review(task(2)["target_text"])
        severe["severe_flags"]["hard_fact_or_ban"] = True
        store(2, "A", severe)
        store(2, "B", review(task(2)["target_text"]))
        store(3, "A", {"invalid": True})
        wrong = review(task(3)["target_text"])
        wrong["evidence_quotes"] = ["NOT_FOUND_QUOTE"]
        store(3, "B", wrong)
        target = private / "followup"
        write_packets(make_packets(pilot), target, repo)
        return pilot, target

    def test_preserve_original_severe_and_validate_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            pilot, folder = self.create(Path(tmp))
            baseline = followup(pilot, folder)
            self.assertEqual(baseline["review_states"]["case02_arbiter"], "NOT_SUBMITTED")
            self.assertEqual(baseline["quality_v1_admitted"], 0)
            self.assertFalse(baseline["case03_retries_both_provisional_pass"])
            for who in "AB":
                path = folder / ("case03-reviewer-%s-retry.json" % who)
                path.write_text(json.dumps(review(task(3)["target_text"])))
                path.chmod(0o600)
            arbiter = {
                "arbiter_verdict": "NOT_SUPPORTED",
                "severe_flag_names": ["hard_fact_or_ban"],
                "gold_exact_quotes": [task(2)["target_text"][:10]],
                "rule_or_card_evidence": ["Source rules do not establish this ban"],
                "analysis": "No explicit conflict based on provided evidence",
                "remaining_uncertainty": "",
            }
            path = folder / "case02-independent-severe-arbitration.json"
            path.write_text(json.dumps(arbiter))
            path.chmod(0o600)
            result = followup(pilot, folder)
            self.assertTrue(result["case03_retries_both_provisional_pass"])
            self.assertEqual(result["review_states"]["case02_arbiter"],
                             "ARBITER_DISPUTES_SEVERE__MANUAL_RESOLUTION_REQUIRED")
            self.assertTrue(result["initial_severe_flag_preserved"])
            self.assertEqual(result["quality_v1_admitted"], 0)
            self.assertNotIn("PRIVATE_GOLD", json.dumps(result))

    def test_exact_evidence_required(self):
        obj = {
            "arbiter_verdict": "CONFIRMED_SEVERE",
            "severe_flag_names": ["hard_fact_or_ban"],
            "gold_exact_quotes": ["NOT_IN_TARGET"],
            "rule_or_card_evidence": ["a rule"],
            "analysis": "reason",
            "remaining_uncertainty": "",
        }
        self.assertEqual(check_arbiter(obj, "Original response"),
                         "ARBITER_QUOTE_NOT_IN_GOLD")
        obj["gold_exact_quotes"] = []
        self.assertEqual(check_arbiter(obj, "Original response"),
                         "ARBITER_EVIDENCE_INCOMPLETE_HOLD")


if __name__ == "__main__":
    unittest.main()
