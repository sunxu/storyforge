"""Synthetic-only tests for the Owner-only Gold72 A/B2 crosswalk."""
from __future__ import annotations

import hashlib
import json
import unittest
from importlib import import_module
from unittest.mock import patch

m = import_module("experiments.r58_quality.r60_reviewer_ab2_gold72_crosswalk")
b2 = import_module("experiments.r58_quality.r60_reviewer_b2_audit")


SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


def fixture():
    selected = list(range(28)) + list(range(31, 75))
    a_records = []
    for i in range(192):
        digest = f"{i + 1:064x}"
        case_level = i < 31
        explicit_hold = 31 <= i < 82
        if case_level:
            granularity, decision, strict = "CASE_LEVEL_SCORED_REVIEW", "PASS_ONLY", "PASS_ONLY"
            scored, aggregate, scores = True, False, dict(SCORES)
        elif explicit_hold:
            granularity, decision, strict = "CASE_ID_IN_EXPLICIT_HOLD_GROUP", "HOLD", "HOLD"
            scored, aggregate, scores = False, False, None
        else:
            granularity, decision, strict = "AGGREGATE_COMPLEMENT_ONLY", "PASS_ONLY", None
            scored, aggregate, scores = False, True, None
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
    a_report = {
        "schema": m.canonical.A_SCHEMA,
        "status": m.canonical.A_STATUS,
        "source_pins": dict(m.canonical.A_SOURCE_PINS),
        "records": a_records,
    }
    a_raw = encoded(a_report)

    staged_rows = []
    owner_rows = []
    blind_rows = []
    map_rows = []
    result_rows = []
    for n, i in enumerate(selected):
        digest = f"{i + 1:064x}"
        case_id = f"case-{i:03d}"
        staged_rows.append({
            "schema": m.canonical.STAGE_SCHEMA,
            "status": m.canonical.STAGE_STATUS,
            "case_id": case_id,
            "target_sha256": digest,
        })
        owner_rows.append({
            "case_id": case_id,
            "target_sha256": digest,
            "staged_file_sha256": "",
            "source_context_file_sha256": "a" * 64,
            "evidence": {"reviewers_blinded_and_independent_attested": None},
        })
        blind_rows.append({"blind_case_id": f"B2-{n:04d}", "target_sha256": digest})
        map_rows.append({
            "blind_case_id": f"B2-{n:04d}",
            "original_case_id": case_id,
            "original_story_uuid": f"story-{i % 13:02d}",
            "target_sha256": digest,
        })
        decision = "PASS" if n < 51 else "HOLD" if n < 67 else "REJECT"
        result_rows.append({
            "blind_case_id": f"B2-{n:04d}",
            "target_sha256": digest,
            "scores_1_to_5": dict(SCORES),
            "decision": decision,
            "severe_flags": [],
            "evidence_summary": "Synthetic-only evidence.",
        })

    staged_raw = b"".join(encoded(row) + b"\n" for row in staged_rows)
    staged_sha = hashlib.sha256(staged_raw).hexdigest()
    for row in owner_rows:
        row["staged_file_sha256"] = staged_sha
    owner_raw = b"".join(encoded(row) + b"\n" for row in owner_rows)
    staging_safe = {
        "schema": m.canonical.RECEIPT_SCHEMA,
        "status": m.canonical.RECEIPT_STATUS,
        "staged_file_sha256": staged_sha,
        "source_context_file_sha256": "a" * 64,
        "source_rows": 72,
        "context_staged": 72,
        "context_structure_hold": 0,
        "source_histories_mutated": False,
        "original_staging_mutated": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }
    staging_safe_raw = encoded(staging_safe)
    blind_raw = encoded({
        "schema": b2.BLIND_SCHEMA,
        "reviewer": "B2",
        "cases": blind_rows,
    }) + b"\n"
    instructions_raw = b"Synthetic-only B2 instructions"
    map_raw = encoded({
        "schema": b2.MAP_SCHEMA,
        "reviewer": "B2",
        "mapping": map_rows,
    })
    result_raw = encoded({
        "schema": b2.RESULT_SCHEMA,
        "reviewer": "B2",
        "status": "REVIEW_COMPLETE",
        "counts": {"PASS": 51, "HOLD": 16, "REJECT": 5},
        "cases": result_rows,
    })
    execution_raw = b"Synthetic-only execution record"
    receipt = {
        "schema": b2.EXECUTION_SCHEMA,
        "reviewer": "B2",
        "status": "EXECUTION_COMPLETE",
        "execution_mode": "STATELESS_API",
        "provider": "synthetic-provider",
        "model_id": "synthetic-model",
        "session_or_request_id": "synthetic-request",
        "started_at_utc": "2026-11-06T09:00:00Z",
        "completed_at_utc": "2026-11-06T09:05:00Z",
        "blind_input_sha256": hashlib.sha256(blind_raw).hexdigest(),
        "instructions_sha256": hashlib.sha256(instructions_raw).hexdigest(),
        "result_sha256": hashlib.sha256(result_raw).hexdigest(),
        "transcript_or_provider_record_sha256": hashlib.sha256(execution_raw).hexdigest(),
        "attestations": {key: True for key in b2.ATTESTATIONS},
        "owner_verification": {key: True for key in b2.OWNER_VERIFICATION},
    }
    receipt_raw = encoded(receipt)
    b2_safe = b2.audit(
        blind_raw, instructions_raw, map_raw, result_raw, receipt_raw, execution_raw
    )
    return {
        "staged_raw": staged_raw,
        "staging_safe_raw": staging_safe_raw,
        "owner_raw": owner_raw,
        "a_raw": a_raw,
        "blind_raw": blind_raw,
        "instructions_raw": instructions_raw,
        "map_raw": map_raw,
        "result_raw": result_raw,
        "receipt_raw": receipt_raw,
        "execution_raw": execution_raw,
        "b2_safe_raw": encoded(b2_safe),
    }


def run(values):
    return m.audit(
        values["staged_raw"],
        values["staging_safe_raw"],
        values["owner_raw"],
        values["a_raw"],
        values["blind_raw"],
        values["instructions_raw"],
        values["map_raw"],
        values["result_raw"],
        values["receipt_raw"],
        values["execution_raw"],
        values["b2_safe_raw"],
    )


class ReviewerAB2Gold72CrosswalkTests(unittest.TestCase):
    def _audit(self, values):
        with patch.object(
            m.canonical, "A_REPORT_SHA256", hashlib.sha256(values["a_raw"]).hexdigest()
        ):
            return run(values)

    def test_crosswalk_reports_decisions_and_score_comparison(self):
        result = self._audit(fixture())
        self.assertEqual(result["status"], m.SAFE_STATUS)
        self.assertEqual(result["reviewer_a_evidence_granularity"], {
            "CASE_LEVEL_SCORED_PASS": 28,
            "EXPLICIT_HOLD": 44,
        })
        self.assertEqual(result["reviewer_b2_decisions"], {
            "PASS": 51, "HOLD": 16, "REJECT": 5,
        })
        self.assertEqual(result["a_b2_comparable_decision_cases"], 72)
        self.assertEqual(result["a_b2_semantic_decision_disagreements"], 28)
        self.assertEqual(result["a_b2_semantic_decision_agreements"], 44)
        self.assertEqual(
            result["a_case_level_scored_pass_and_b2_pass_no_severe_flags"], 28
        )
        self.assertEqual(result["a_explicit_nonpass_b2_pass"], 23)
        self.assertEqual(result["score_comparable_cases"], 28)
        for metric in result["score_comparison_by_dimension"].values():
            self.assertEqual(metric["exact_matches"], 28)
            self.assertEqual(metric["mean_absolute_difference"], 0.0)
        self.assertFalse(result["reviewer_b2_independence_verified"])
        self.assertFalse(result["cryptographic_independence_proven"])
        self.assertEqual(result["quality_v1_admitted"], 0)
        self.assertFalse(result["private_values_emitted"])

    def test_b2_owner_map_case_id_mismatch_fails_closed(self):
        values = fixture()
        mapping = json.loads(values["map_raw"])
        mapping["mapping"][0]["original_case_id"] = "wrong-case"
        values["map_raw"] = encoded(mapping)
        receipt = json.loads(values["receipt_raw"])
        receipt["owner_verification"]["case_binding_rechecked"] = True
        values["receipt_raw"] = encoded(receipt)
        values["b2_safe_raw"] = encoded(b2.audit(
            values["blind_raw"], values["instructions_raw"], values["map_raw"],
            values["result_raw"], values["receipt_raw"], values["execution_raw"]
        ))
        with patch.object(
            m.canonical, "A_REPORT_SHA256", hashlib.sha256(values["a_raw"]).hexdigest()
        ), self.assertRaisesRegex(m.CrosswalkHold, "B2_TO_GOLD72_TARGET_BINDING_MISMATCH"):
            run(values)

    def test_stale_b2_safe_fails_closed(self):
        values = fixture()
        safe = json.loads(values["b2_safe_raw"])
        safe["result_sha256"] = "0" * 64
        values["b2_safe_raw"] = encoded(safe)
        with patch.object(
            m.canonical, "A_REPORT_SHA256", hashlib.sha256(values["a_raw"]).hexdigest()
        ), self.assertRaisesRegex(m.CrosswalkHold, "B2_AUDIT_SAFE_INVALID_OR_STALE"):
            run(values)

    def test_receipt_hash_mismatch_fails_closed(self):
        values = fixture()
        receipt = json.loads(values["receipt_raw"])
        receipt["result_sha256"] = "0" * 64
        values["receipt_raw"] = encoded(receipt)
        with patch.object(
            m.canonical, "A_REPORT_SHA256", hashlib.sha256(values["a_raw"]).hexdigest()
        ), self.assertRaisesRegex(b2.AuditHold, "B2_EXECUTION_HASH_BINDING_MISMATCH"):
            run(values)

    def test_a_report_pin_mismatch_fails_closed(self):
        values = fixture()
        with self.assertRaisesRegex(m.CrosswalkHold, "REVIEWER_A_V3_REPORT_PIN_MISMATCH"):
            run(values)


if __name__ == "__main__":
    unittest.main()
