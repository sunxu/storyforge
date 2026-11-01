import copy
import json
from pathlib import Path
import tempfile
import unittest

from r58_gold195_blind_quality_pilot13 import prepare
from r58_gold195_pilot13_dual_review_validate import (
    analyze, collect, validate_response, read_private,
)
from test_r58_gold195_blind_quality_pilot13 import Gold195BlindPilot13Tests


class DualReviewValidateTests(unittest.TestCase):
    def fixtures(self, directory):
        root = Path(directory)
        private = root / "private"
        private.mkdir(mode=0o700)
        source = private / "gold195.review.jsonl"
        entries = Gold195BlindPilot13Tests().source()
        source.write_text("\n".join(
            json.dumps(x, ensure_ascii=False) for x in entries
        ) + "\n")
        source.chmod(0o600)
        out = private / "review"
        prepare(source, out, root / "repo")
        a = read_private(out / "reviewer_A.private.jsonl", True)
        b = read_private(out / "reviewer_B.private.jsonl", True)
        owner = read_private(out / "owner_crosswalk.private.json", False)
        return a, b, owner

    def completed(self, source):
        rows = copy.deepcopy(source)
        for row in rows:
            row["response"].update({
                "decision": "PASS",
                "scores": {
                    "chinese_prose": 4,
                    "character_consistency": 4,
                    "npc_initiative": 3,
                    "player_agency": 4,
                    "rule_fidelity": 4,
                    "narrative_continuity": 4,
                },
                "severe_flags": {
                    "serious_player_agency": False,
                    "hard_fact_or_ban": False,
                    "safety_exclusion": False,
                },
                "card_snapshot_suitable_for_offline_training": True,
                "card_conflicts_with_visible_history_or_gold": False,
                "specific_source_quotes": [row["messages"][1]["content"]],
                "specific_target_quotes": [row["target_text"]],
                "literary_quality_notes": "这是纯合成审阅验证理由，不是对真实文学质量的评价。",
                "uncertainty": None,
            })
        return rows

    def test_complete_dual_review_not_automatic_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, owner = self.fixtures(tmp)
            result = analyze(a, self.completed(a), b, self.completed(b), owner)
            self.assertEqual(result["reviewer_a"]["PASS"], 13)
            self.assertEqual(result["reviewer_b"]["PASS"], 13)
            self.assertEqual(result["both_pass_review_only"], 13)
            self.assertEqual(result["quality_v1_admitted"], 0)
            self.assertFalse(result["training_authorized"])
            self.assertFalse(result["reviewer_independence_proven_by_validator"])
            self.assertNotIn("PRIVATE_", json.dumps(result))

    def test_tampered_content_and_quotes_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, owner = self.fixtures(tmp)
            done = self.completed(a)
            done[0]["target_text"] += "CHANGED"
            with self.assertRaises(ValueError):
                collect(a, done)
            done = self.completed(a)
            done[0]["response"]["specific_source_quotes"] = ["NOT_IN_HISTORY"]
            with self.assertRaises(ValueError):
                collect(a, done)
            done = self.completed(a)
            done[0]["response"]["specific_target_quotes"] = ["NOT_IN_GOLD"]
            with self.assertRaises(ValueError):
                collect(a, done)
            done = self.completed(a)
            done[0]["response"]["severe_flags"]["serious_player_agency"] = True
            with self.assertRaises(ValueError):
                collect(a, done)
            done = self.completed(a)
            done[0]["response"]["scores"]["chinese_prose"] = 2
            with self.assertRaises(ValueError):
                collect(a, done)

    def test_incomplete_reviews_or_wrong_crosswalk_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, owner = self.fixtures(tmp)
            with self.assertRaises(ValueError):
                collect(a, a)
            modified = copy.deepcopy(owner)
            modified["selected"][0]["card_snapshot_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                analyze(a, self.completed(a), b, self.completed(b), modified)
            done = self.completed(a)
            done[0]["response"]["decision"] = "HOLD"
            done[0]["response"]["uncertainty"] = "仍需核对来源设定。"
            done[0]["response"]["scores"]["chinese_prose"] = None
            self.assertEqual(validate_response(done[0]["response"], a[0]), "HOLD")
            done[0]["response"]["uncertainty"] = None
            with self.assertRaises(ValueError):
                validate_response(done[0]["response"], a[0])


if __name__ == "__main__":
    unittest.main()
