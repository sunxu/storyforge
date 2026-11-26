import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_grok_web_export import canon, create_files, export, packet
from gold195_grok_web_validate import check_review, audit, DIMENSIONS, FLAGS


def task(i):
    messages = [
        {"role": "system", "content": "PRIVATE_WORLD"},
        {"role": "user", "content": "PRIVATE_PLAYER"},
    ]
    target = "PRIVATE_GOLD_TARGET_%02d" % i
    return {
        "schema": "r58_gold195_six_dimension_review_task_private_v1",
        "case_id": "PRIVATE_CASE_%02d" % i,
        "input_design_status": "PROPOSED_OFFLINE_CARD_NOT_APPROVED",
        "review_results": [], "review_status": "UNREVIEWED",
        "messages": messages, "target_text": target,
        "input_messages_sha256": hashlib.sha256(canon(messages)).hexdigest(),
        "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
        "training_authorized": False, "quality_v1_admitted": False,
    }


def review(target):
    return {
        "scores": dict(zip(DIMENSIONS, (5, 4, 4, 5, 4, 4))),
        "severe_flags": {name: False for name in FLAGS},
        "reasons": {name: "依据可见剧情与设定判断" for name in DIMENSIONS},
        "card_design_verdict": "ACCEPTABLE_FOR_OFFLINE_REVIEW",
        "card_gold_conflicts": [],
        "evidence_quotes": [target[:10]],
    }


class GrokWebPilotTests(unittest.TestCase):
    def test_export_six_packets_but_no_reviews(self):
        files = create_files([task(1), task(2), task(3)])
        self.assertEqual(len(files), 7)
        self.assertIn("case01-reviewer-A.md", files)
        self.assertIn("case01-reviewer-B.md", files)
        self.assertNotIn(b"PRIVATE_GOLD_TARGET_02", files["case01-reviewer-A.md"])
        self.assertNotIn(b"PRIVATE_GOLD_TARGET_02", files["case01-reviewer-B.md"])
        self.assertEqual(files["case01-reviewer-A.md"].count(b"PRIVATE_GOLD_TARGET_01"), 1)
        self.assertNotIn(b"Reviewer B", files["case01-reviewer-A.md"])
        self.assertNotIn(b"Reviewer A", files["case01-reviewer-B.md"])

    def test_reviewer_evidence_and_severe_validation(self):
        target = "真实候选回复中的逐字引证"
        self.assertEqual(check_review(review(target), target), "PROVISIONAL_REVIEW_PASS")
        altered = review(target)
        altered["evidence_quotes"] = ["不存在的原文"]
        self.assertEqual(check_review(altered, target), "EVIDENCE_QUOTE_NOT_IN_GOLD")
        altered = review(target)
        altered["severe_flags"]["hard_fact_or_ban"] = True
        self.assertEqual(check_review(altered, target), "SEVERE_FLAG")
        altered = review(target)
        altered["scores"]["chinese_prose"] = 2
        self.assertEqual(check_review(altered, target), "BELOW_SCORE_FLOOR")
        altered = review(target)
        altered["evidence_quotes"] = []
        self.assertEqual(check_review(altered, target),
                         "PASS_CANNOT_BE_SUPPORTED_WITHOUT_QUOTES")
        altered = review(target)
        altered["scores"]["npc_initiative"] = True
        self.assertEqual(check_review(altered, target), "MALFORMED")

    def test_missing_reviews_are_hold_not_pass(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir(mode=0o700)
            folder = private / "web"
            self.assertEqual(export(repo, folder, [task(1), task(2), task(3)]), 7)
            for file in folder.iterdir():
                self.assertEqual(file.stat().st_mode & 0o777, 0o600)
            receipt = audit(folder)
            self.assertEqual(receipt["review_state_counts"]["MISSING_REVIEW"], 6)
            self.assertEqual(receipt["quality_v1_admitted"], 0)
            self.assertFalse(receipt["all_six_reviews_present"])
            self.assertNotIn("PRIVATE_GOLD", json.dumps(receipt))
            for i in range(1, 4):
                for who in "AB":
                    path = folder / ("case%02d-reviewer-%s.json" % (i, who))
                    path.write_text(json.dumps(review(task(i)["target_text"])))
                    path.chmod(0o600)
            receipt = audit(folder)
            self.assertEqual(receipt["two_reviewers_provisional_pass_cases"], 3)
            self.assertEqual(receipt["quality_v1_admitted"], 0)
            self.assertFalse(receipt["reviewer_independence_proven_by_software"])
            with self.assertRaises(ValueError):
                export(repo, folder, [task(1), task(2), task(3)])


if __name__ == "__main__":
    unittest.main()
