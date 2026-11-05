import json
from pathlib import Path
import tempfile
import unittest

from gold195_grok_web_pilot_closure import close
from test_gold195_case02_final_disposition import FinalDispositionTests


class PilotClosureTests(FinalDispositionTests):
    # Existing synthetic fixture includes 3 cases, original and follow-up results.
    def test_provisional_two_plus_unresolved_is_closure_not_approval(self):
        decision = self.private / "case02-final.json"
        from gold195_case02_final_disposition import make_template
        template = make_template(self.pilot, self.follow)
        decision.write_text(json.dumps(template, ensure_ascii=False))
        decision.chmod(0o600)
        summary = close(self.pilot, self.follow, decision)
        self.assertEqual(summary["dual_provisional_pass_cases"], 2)
        self.assertEqual(summary["unresolved_severe_dispute_cases"], 1)
        self.assertEqual(summary["quality_v1_admitted"], 0)
        self.assertEqual(summary["remaining_user_first_cases_external_review_authorized"], 0)
        self.assertFalse(summary["network_called"])
        self.assertFalse(summary["literary_quality_independently_proven"])
        self.assertNotIn("PRIVATE_CASE", json.dumps(summary))
        self.assertNotIn("PRIVATE_GOLD", json.dumps(summary))

    def test_non_hold_cannot_be_mislabelled_as_unresolved_closure(self):
        from gold195_case02_final_disposition import make_template
        template = make_template(self.pilot, self.follow)
        template.update({
            "decision": "NOT_SUPPORTED_WITH_EVIDENCE",
            "decision_completed": True,
            "decision_maker": "actual reviewer",
            "independent_reasoning": "可见故事卡的规则和这个目标回复并不冲突，而且初审证据不足以构成明确严重违规。",
            "gold_exact_quotes": ["PRIVATE_GOLD"],
            "actual_source_evidence": ["confirmed private source evidence"],
        })
        decision = self.private / "case02-different.json"
        decision.write_text(json.dumps(template, ensure_ascii=False))
        decision.chmod(0o600)
        with self.assertRaises(ValueError):
            close(self.pilot, self.follow, decision)


if __name__ == "__main__":
    unittest.main()
