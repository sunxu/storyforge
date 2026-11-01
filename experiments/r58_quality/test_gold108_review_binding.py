import csv
import json
from pathlib import Path
import tempfile
import unittest

from gold108_review_binding import BASE, check, score_ok


class Gold108BindingTests(unittest.TestCase):
    def build(self, root, mutate=None):
        base = root / BASE
        base.mkdir(parents=True)
        cols = ["blind_id", "candidate_id", "story_number", "story_id",
                "target_sha256", "reviewer1_decision", "reviewer2_decision",
                "reviewer1_scores", "reviewer2_scores"]
        with (base / "gold_108_index.csv").open("w", encoding="utf-8", newline="") as f, (base / "dual_accept_review_evidence_108.jsonl").open("w", encoding="utf-8") as e:
            writer = csv.DictWriter(f, fieldnames=cols)
            writer.writeheader()
            for i in range(108):
                item = {
                    "blind_id": f"B{i}", "candidate_id": f"secret-{i}",
                    "story_number": "06", "story_id": "private-world",
                    "target_sha256": "a" * 64,
                    "reviewer1_decision": "ACCEPT", "reviewer2_decision": "ACCEPT",
                    "reviewer1_scores": "4,4,4,4,4",
                    "reviewer2_scores": "4,4,5,4,4",
                }
                proof = {**item, "story_number": 6,
                         "reviewer1_evidence": "private quote",
                         "reviewer2_evidence": "private quote"}
                if mutate and i == 0:
                    mutate(item, proof)
                writer.writerow(item)
                e.write(json.dumps(proof) + "\n")

    def test_pass_counts_only_and_no_private_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.build(Path(tmp))
            result = check(Path(tmp))
            self.assertEqual(result["index_rows_with_review_link"], 108)
            self.assertEqual(result["training_admitted"], 0)
            encoded = json.dumps(result)
            self.assertNotIn("secret-", encoded)
            self.assertNotIn("private quote", encoded)
            self.assertNotIn("private-world", encoded)

    def test_disagreeing_scores_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.build(Path(tmp), lambda row, proof: proof.update(reviewer1_scores="5,5,5,5,5"))
            self.assertEqual(check(Path(tmp))["status"], "LEGACY_EVIDENCE_BINDING_HOLD")

    def test_missing_hash_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.build(Path(tmp), lambda row, proof: row.update(target_sha256=""))
            self.assertIn("target_hash_missing_or_malformed_in_index", check(Path(tmp))["errors"])

    def test_missing_evidence_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.build(Path(tmp), lambda row, proof: proof.update(reviewer2_evidence=""))
            self.assertEqual(check(Path(tmp))["status"], "LEGACY_EVIDENCE_BINDING_HOLD")

    def test_score_dimensions_fail_closed(self):
        self.assertTrue(score_ok("4,4,4,5,5"))
        for s in ("4,4,4,3,5", "4,4,4,4", "4,4,4,4,True", None):
            self.assertFalse(score_ok(s))


if __name__ == "__main__":
    unittest.main()
