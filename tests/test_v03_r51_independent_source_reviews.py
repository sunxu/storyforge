"""Synthetic-only checks for independent R51 private source reviews."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r51_independent_source_reviews as reviews


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def fake_packet(i, rank):
    body = f"synthetic-target-{i}"
    return {
        "schema": reviews.INPUT_SCHEMA,
        "candidate_id": f"synthetic-{i}",
        "private_do_not_commit": True,
        "story_rank": rank,
        "target_sha256": digest(body),
        "target_original_array_index": i * 10 + 1,
        "target_content_for_review_only": body,
        "frozen_visible_first_role": "assistant" if i % 2 else "user",
        "frozen_visible_history": [{
            "role": "user", "content": f"synthetic-visible-{i}",
            "original_source_array_index": i * 10,
            "source_body_sha256": digest(f"synthetic-visible-{i}"),
        }],
        "preceding_source_preview_NOT_PART_OF_FROZEN_INPUT": [],
        "historical_card_version_verified": False,
        "training_admission": "PENDING_NOT_APPROVED",
        "split": None,
    }


def fixture():
    return [fake_packet(i, i % 8 + 6) for i in range(108)]


def result_for(task):
    v = task["frozen_visible_history"][0]
    return {
        "schema": reviews.RESULT_SCHEMA,
        "reviewer": task["reviewer"],
        "candidate_id": task["candidate_id"],
        "target_sha256": task["target_sha256"],
        "batch_number": task["batch_number"],
        "route": "CONTEXT_ONLY_POSSIBLE__HOLD",
        "source_citations": [
            {"scope": "FROZEN_VISIBLE",
             "original_source_array_index": v["original_source_array_index"],
             "source_body_sha256": v["source_body_sha256"]},
            {"scope": "TARGET",
             "original_source_array_index": task["target_original_array_index"],
             "source_body_sha256": task["target_sha256"]},
        ],
        "rationale": "Synthetic visible context supports the synthetic reply.",
        "training_admission": "PENDING_NOT_APPROVED",
    }


class TestIndependentReviews(unittest.TestCase):
    def test_batched_complete_and_priority(self):
        packets = fixture()
        batches = reviews.batches_for(packets)
        self.assertEqual(len(batches), 5)
        self.assertEqual([len(x) for x in batches], [24, 24, 24, 24, 12])
        self.assertEqual(len({p["candidate_id"] for b in batches for p in b}), 108)
        tasks, receipt = reviews.build_batch(packets, 1)
        self.assertEqual(len(tasks["A"]), len(tasks["B"]))
        self.assertEqual(receipt["training_admitted"], 0)
        self.assertEqual(receipt["unique_candidates"], 24)
        self.assertEqual(
            {t["candidate_id"] for t in tasks["A"]},
            {t["candidate_id"] for t in tasks["B"]})
        self.assertTrue(all(t["training_admission"] == "PENDING_NOT_APPROVED"
                            for t in tasks["A"]))

    def test_two_complete_reviews_reconcile_but_never_admit(self):
        tasks, _ = reviews.build_batch(fixture(), 1)
        a = [result_for(t) for t in tasks["A"]]
        b = [result_for(t) for t in tasks["B"]]
        merged, receipt = reviews.reconcile(tasks["A"], tasks["B"], a, b)
        self.assertEqual(receipt["same_route"], 24)
        self.assertEqual(receipt["agreed_context_only_possible_hold"], 24)
        self.assertEqual(receipt["train_admitted"], 0)
        self.assertTrue(all(r["training_admission"] == "PENDING_NOT_APPROVED"
                            for r in merged))
        self.assertNotIn("synthetic-visible", json.dumps(receipt))

    def test_review_missing_or_fake_citation_fails_closed(self):
        tasks, _ = reviews.build_batch(fixture(), 1)
        good = [result_for(t) for t in tasks["A"]]
        with self.assertRaisesRegex(ValueError, "INCOMPLETE"):
            reviews.validate_review(good[:-1], tasks["A"], "A")
        good[0]["source_citations"][0]["source_body_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "NOT_IN_AUTHENTIC_PACKET"):
            reviews.validate_review(good, tasks["A"], "A")


    def test_error_reporting_redacts_private_strings_and_identifies_stage(self):
        self.assertEqual(
            reviews.diagnostic_error(
                "REVIEWER_B_VALIDATE",
                ValueError("REVIEWER_RESPONSE_SCHEMA_OR_PIN_INVALID")),
            "R51_REVIEW_TASK_HOLD__REVIEWER_B_VALIDATE__"
            "REVIEWER_RESPONSE_SCHEMA_OR_PIN_INVALID")
        self.assertEqual(
            reviews.diagnostic_error(
                "REVIEWER_B_READ", ValueError("SECRET_CHARACTER_OR_DIALOGUE")),
            "R51_REVIEW_TASK_HOLD__REVIEWER_B_READ__ValueError")

    def test_never_certify_card_or_rights(self):
        tasks, _ = reviews.build_batch(fixture(), 1)
        self.assertTrue(all(t["historical_card_version_verified"] is False
                            and t["rights_or_license_certified"] is False
                            for t in tasks["A"]))


if __name__ == "__main__":
    unittest.main()
