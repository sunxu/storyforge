"""Synthetic Gold87 historical index audit tests; no private samples."""
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from gold87_legacy_index_audit import inspect


class Gold87IndexAuditTests(unittest.TestCase):
    def make_index(self, path, bad=None):
        columns = [
            "story_id", "sample_target_sha256", "sample_id",
            "review_A", "review_B", "review_C", "quality_decision",
            "training_admission", "split", "A_citation_status",
            "age_and_consent_status",
        ]
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            for i in range(87):
                row = {
                    "story_id": f"synthetic-world-{i}",
                    "sample_target_sha256": hashlib.sha256(str(i).encode()).hexdigest(),
                    "sample_id": f"synthetic-{i}",
                    "review_A": "ACCEPT",
                    "review_B": "ACCEPT",
                    "review_C": "ACCEPT" if i < 2 else "NOT_REVIEWED",
                    "quality_decision": "GOLD_QUALITY_ACCEPTED_BY_OWNER",
                    "training_admission": "PENDING_NOT_APPROVED",
                    "split": "UNASSIGNED",
                    "A_citation_status": (
                        "SEGMENT_MATCH_ONLY__REQUOTE_RECOMMENDED" if i == 0
                        else "STRICT_CONTIGUOUS_PASS" if i < 7
                        else "ORIGINAL_EXACT_OR_VALID_COMPRESSED_QUOTE"
                    ),
                    "age_and_consent_status": (
                        "TARGET_TIME_AGE_NOT_VERIFIED" if i < 10
                        else "NOT_REVALIDATED_AT_QUALITY_SELECTION"
                    ),
                }
                if bad == "accept" and i == 0:
                    row["review_B"] = "REJECT"
                if bad == "citation" and i == 0:
                    row["A_citation_status"] = "UNRECOGNIZED"
                writer.writerow(row)

    def test_index_attestation_does_not_approve_training(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "index.csv"
            self.make_index(path)
            result = inspect(path)
            self.assertEqual(result["frozen_rows_checked"], 87)
            self.assertEqual(result["historical_review_c_accept_indexed"], 2)
            self.assertEqual(result["citation_status_counts"]["SEGMENT_MATCH_ONLY__REQUOTE_RECOMMENDED"], 1)
            self.assertFalse(result["historic_reviewer_text_and_scores_verified"])
            self.assertEqual(result["quality_v1_admitted"], 0)

    def test_changed_review_decision_holds(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "index.csv"
            self.make_index(path, bad="accept")
            with self.assertRaisesRegex(ValueError, "GOLD87_INDEX_STATUS_INVALID"):
                inspect(path)

    def test_unrecognized_citation_holds(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "index.csv"
            self.make_index(path, bad="citation")
            with self.assertRaisesRegex(ValueError, "GOLD87_INDEX_STATUS_INVALID"):
                inspect(path)


if __name__ == "__main__":
    unittest.main()
