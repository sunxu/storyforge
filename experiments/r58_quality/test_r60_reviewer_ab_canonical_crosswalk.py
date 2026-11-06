"""Synthetic-only tests for the canonical Gold72 A/B crosswalk."""
from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch

from experiments.r58_quality import r60_reviewer_ab_canonical_crosswalk as m


SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def fixture():
    a_records = []
    b_cases = []
    for i in range(192):
        digest = f"{i + 1:064x}"
        if i < 31:
            granularity = "CASE_LEVEL_SCORED_REVIEW"
            decision = "PASS_ONLY"
            strict = "PASS_ONLY"
            scored = True
            aggregate = False
            scores = dict(SCORES)
        elif i < 82:
            granularity = "CASE_ID_IN_EXPLICIT_HOLD_GROUP"
            decision = "HOLD"
            strict = "HOLD"
            scored = False
            aggregate = False
            scores = None
        elif i == 82:
            granularity = "CASE_ID_IN_EXPLICIT_REJECT_GROUP"
            decision = "REJECT"
            strict = "REJECT"
            scored = False
            aggregate = False
            scores = None
        else:
            granularity = "AGGREGATE_COMPLEMENT_ONLY"
            decision = "PASS_ONLY"
            strict = None
            scored = False
            aggregate = True
            scores = None
        a_records.append({
            "case_id": f"case-{i:03d}",
            "target_sha256": digest,
            "reported_final_decision": decision,
            "decision_for_strict_ab_decision_comparison": strict,
            "evidence_granularity": granularity,
            "case_level_scored_review_present": scored,
            "aggregate_complement_only": aggregate,
            "scores_1_to_5": scores,
        })
        b_decision = "PASS" if i < 178 else "HOLD" if i < 190 else "REJECT"
        b_cases.append({
            "target_sha256": digest,
            "blind_case_id": f"blind-{i:03d}",
            "decision": b_decision,
            "scores_1_to_5": dict(SCORES),
            "severe_flags": [],
            "evidence_summary": "Synthetic-only evidence",
        })

    a_report = {
        "schema": m.A_SCHEMA,
        "status": m.A_STATUS,
        "source_pins": dict(m.A_SOURCE_PINS),
        "records": a_records,
    }
    b_report = {
        "schema": m.B_SCHEMA,
        "counts": {"PASS": 178, "HOLD": 12, "REJECT": 2},
        "cases": b_cases,
    }
    staged_rows = [
        {
            "schema": m.STAGE_SCHEMA,
            "status": m.STAGE_STATUS,
            "case_id": f"case-{i:03d}",
            "target_sha256": f"{i + 1:064x}",
        }
        for i in range(72)
    ]
    staged_raw = b"".join(
        json.dumps(row, sort_keys=True).encode() + b"\n" for row in staged_rows
    )
    staged_sha = hashlib.sha256(staged_raw).hexdigest()
    source_sha = "a" * 64
    receipt = {
        "schema": m.RECEIPT_SCHEMA,
        "status": m.RECEIPT_STATUS,
        "staged_file_sha256": staged_sha,
        "source_context_file_sha256": source_sha,
        "source_rows": 72,
        "context_staged": 72,
        "context_structure_hold": 0,
        "source_histories_mutated": False,
        "original_staging_mutated": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }
    owner_rows = [
        {
            "case_id": f"case-{i:03d}",
            "target_sha256": f"{i + 1:064x}",
            "staged_file_sha256": staged_sha,
            "source_context_file_sha256": source_sha,
            "evidence": {"reviewers_blinded_and_independent_attested": None},
        }
        for i in range(72)
    ]
    b_raw = json.dumps(b_report, sort_keys=True).encode()
    return staged_raw, receipt, owner_rows, a_report, b_report, b_raw


class CanonicalCrosswalkTests(unittest.TestCase):
    def test_crosswalk_distinguishes_case_level_and_aggregate_pass(self):
        staged_raw, receipt, owners, a, b, b_raw = fixture()
        digest = hashlib.sha256(b_raw).hexdigest()
        pins = dict(m.A_SOURCE_PINS)
        pins["reviewer_b"] = digest
        a["source_pins"] = dict(pins)
        with (
            patch.object(m, "B_SHA256", digest),
            patch.dict(m.A_SOURCE_PINS, pins, clear=True),
        ):
            result = m.audit(staged_raw, receipt, owners, a, b, b_raw)
        self.assertEqual(result["status"], "CANONICAL_CROSSWALK_COMPLETE__ADMISSION_HOLD")
        self.assertEqual(result["reviewer_a_evidence_granularity"], {
            "AGGREGATE_COMPLEMENT_PASS_ONLY": 41,
            "CASE_LEVEL_SCORED_PASS": 31,
        })
        self.assertEqual(result["reviewer_b_decisions"], {"PASS": 72})
        self.assertEqual(result["owner_independent_blind_attestation"], {"MISSING": 72})
        self.assertFalse(result["reviewer_independence_proven"])
        self.assertEqual(result["quality_v1_admitted"], 0)

    def test_superseded_a_artifact_is_rejected(self):
        staged_raw, receipt, owners, a, b, b_raw = fixture()
        digest = hashlib.sha256(b_raw).hexdigest()
        pins = dict(m.A_SOURCE_PINS)
        pins["reviewer_b"] = digest
        a["source_pins"] = dict(pins)
        a["schema"] = "old-superseded-reviewer-a-schema"
        with (
            patch.object(m, "B_SHA256", digest),
            patch.dict(m.A_SOURCE_PINS, pins, clear=True),
            self.assertRaisesRegex(m.AuditHold, "CANONICAL_REVIEWER_A_V3_REQUIRED"),
        ):
            m.audit(staged_raw, receipt, owners, a, b, b_raw)

    def test_owner_identity_or_staging_pin_mismatch_fails_closed(self):
        staged_raw, receipt, owners, a, b, b_raw = fixture()
        owners[0]["staged_file_sha256"] = "0" * 64
        digest = hashlib.sha256(b_raw).hexdigest()
        pins = dict(m.A_SOURCE_PINS)
        pins["reviewer_b"] = digest
        a["source_pins"] = dict(pins)
        with (
            patch.object(m, "B_SHA256", digest),
            patch.dict(m.A_SOURCE_PINS, pins, clear=True),
            self.assertRaisesRegex(m.AuditHold, "OWNER_STAGING_IDENTITY_OR_PIN_MISMATCH"),
        ):
            m.audit(staged_raw, receipt, owners, a, b, b_raw)

    def test_b_source_pin_mismatch_fails_closed(self):
        staged_raw, receipt, owners, a, b, b_raw = fixture()
        with self.assertRaisesRegex(m.AuditHold, "REVIEWER_B_SOURCE_PIN_MISMATCH"):
            m.audit(staged_raw, receipt, owners, a, b, b_raw + b"tampered")


if __name__ == "__main__":
    unittest.main()
