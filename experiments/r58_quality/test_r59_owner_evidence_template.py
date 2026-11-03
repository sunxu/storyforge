import unittest

from r59_owner_evidence_template import (
    NEGATIVE_EVIDENCE,
    SEVERE_FLAGS,
    STAGE_SCHEMA,
    STAGE_STATUS,
    TemplateHold,
    build_template,
)
from quality_v1 import EVIDENCE


class OwnerEvidenceTemplateTests(unittest.TestCase):
    def setUp(self):
        self.stage = {
            "schema": STAGE_SCHEMA,
            "status": STAGE_STATUS,
            "case_id": "private-case",
            "target_sha256": "a" * 64,
            "story_id": "private-story",
            "session_id": "private-session",
        }
        self.staged_sha = "b" * 64
        self.context_sha = "c" * 64

    def test_copies_identity_and_pins_but_no_attestations(self):
        rows = build_template(
            [self.stage, {"schema": "other", "status": "SOURCE_STRUCTURE_HOLD"}],
            self.staged_sha,
            self.context_sha,
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["case_id"], "private-case")
        self.assertEqual(row["target_sha256"], "a" * 64)
        self.assertEqual(row["staged_file_sha256"], self.staged_sha)
        self.assertEqual(row["source_context_file_sha256"], self.context_sha)
        self.assertIsNone(row["source_version_sha256"])
        self.assertIsNone(row["world_graph_sha256"])
        self.assertIsNone(row["world_component_id"])
        self.assertIsNone(row["split"])
        self.assertIsNone(row["reviewer_a_evidence_ref"])
        self.assertIsNone(row["reviewer_b_evidence_ref"])
        self.assertEqual(row["reviewer_a_severe_flags"], {key: None for key in SEVERE_FLAGS})
        self.assertEqual(row["evidence"], {key: None for key in (*EVIDENCE, *NEGATIVE_EVIDENCE)})

    def test_duplicate_candidate_identity_holds(self):
        with self.assertRaisesRegex(TemplateHold, "DUPLICATE"):
            build_template([self.stage, self.stage], self.staged_sha, self.context_sha)

    def test_invalid_target_hash_holds(self):
        row = dict(self.stage, target_sha256="not-a-hash")
        with self.assertRaisesRegex(TemplateHold, "TARGET_PIN"):
            build_template([row], self.staged_sha, self.context_sha)

    def test_invalid_staging_pin_holds(self):
        with self.assertRaisesRegex(TemplateHold, "STAGING_PIN"):
            build_template([self.stage], "bad", self.context_sha)

    def test_no_eligible_staging_rows_holds(self):
        row = dict(self.stage, status="SOURCE_STRUCTURE_HOLD")
        with self.assertRaisesRegex(TemplateHold, "NO_STAGED"):
            build_template([row], self.staged_sha, self.context_sha)


if __name__ == "__main__":
    unittest.main()
