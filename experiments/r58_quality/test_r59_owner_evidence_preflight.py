import json
import unittest

from quality_v1 import EVIDENCE, SEVERE
from r59_owner_evidence_preflight import NEGATIVE, preflight


PIN_A = "a" * 64
PIN_B = "b" * 64
PIN_C = "c" * 64


def stage_row():
    return {
        "schema": "storyforge-quality-v1-source-staging-private-v1",
        "status": "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
        "case_id": "private-case-1",
        "target_sha256": PIN_A,
        "story_id": "private-story-1",
        "session_id": "private-session-1",
    }


def owner_row():
    return {
        "case_id": "private-case-1",
        "target_sha256": PIN_A,
        "story_id": "private-story-1",
        "session_id": "private-session-1",
        "owner_supplemental_severe_flags": {key: False for key in SEVERE},
        "owner_supplemental_severe_evidence_ref": "private-owner-review-ref",
        "evidence": {
            **{key: True for key in EVIDENCE},
            **{key: False for key in NEGATIVE},
        },
        "source_version_sha256": PIN_B,
        "world_graph_sha256": PIN_C,
        "world_component_id": "private-world-component",
        "split": "train",
        "reviewer_a_evidence_ref": "private-a-ref",
        "reviewer_b_evidence_ref": "private-b-ref",
        "staged_file_sha256": PIN_A,
        "source_context_file_sha256": PIN_B,
    }


class OwnerEvidencePreflightTests(unittest.TestCase):
    def test_blank_template_reports_all_missing_dimensions(self):
        owner = owner_row()
        owner["owner_supplemental_severe_flags"] = {
            key: None for key in SEVERE
        }
        owner["owner_supplemental_severe_evidence_ref"] = None
        owner["evidence"] = {key: None for key in (*EVIDENCE, *NEGATIVE)}
        for key in (
            "source_version_sha256", "world_graph_sha256",
            "world_component_id", "split", "reviewer_a_evidence_ref",
            "reviewer_b_evidence_ref", "staged_file_sha256",
            "source_context_file_sha256",
        ):
            owner[key] = None
        report = preflight([stage_row()], [owner], PIN_A, PIN_B)
        self.assertEqual(report["status"], "OWNER_EVIDENCE_PREFLIGHT_HOLD")
        self.assertEqual(report["identity_matched"], 1)
        self.assertEqual(report["field_checks_missing"]["supplemental_severe_flags_complete"], 1)
        self.assertEqual(report["field_checks_missing"]["evidence_true:" + EVIDENCE[0]], 1)
        self.assertEqual(report["field_checks_missing"]["negative_evidence_false:" + NEGATIVE[0]], 1)

    def test_complete_fields_do_not_claim_independence_or_admission(self):
        report = preflight([stage_row()], [owner_row()], PIN_A, PIN_B)
        self.assertEqual(
            report["status"],
            "OWNER_EVIDENCE_FIELDS_COMPLETE__BINDER_AND_OWNER_ATTESTATION_STILL_REQUIRED",
        )
        self.assertFalse(report["reviewer_independence_independently_proven"])
        self.assertFalse(report["protected_set_completeness_independently_proven"])
        self.assertEqual(report["quality_v1_admitted"], 0)
        self.assertFalse(report["training_authorized"])

    def test_identity_mismatch_is_aggregate_only(self):
        owner = owner_row()
        owner["target_sha256"] = "d" * 64
        report = preflight([stage_row()], [owner], PIN_A, PIN_B)
        self.assertEqual(report["identity_missing_or_mismatched"], 1)
        rendered = json.dumps(report)
        self.assertNotIn("private-case-1", rendered)
        self.assertNotIn("private-story-1", rendered)
        self.assertNotIn(PIN_A, rendered)

    def test_duplicate_owner_identity_holds(self):
        with self.assertRaises(ValueError):
            preflight([stage_row()], [owner_row(), owner_row()], PIN_A, PIN_B)


if __name__ == "__main__":
    unittest.main()
