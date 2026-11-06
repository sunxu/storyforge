"""Synthetic-only tests for the Owner-only Reviewer B2 audit."""
from __future__ import annotations

import hashlib
import json
import unittest

from experiments.r58_quality import r60_reviewer_b2_audit as m


SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 3,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def fixture():
    blind_cases = []
    owner_rows = []
    result_rows = []
    for i in range(72):
        blind_id = f"B2-{i:04d}"
        digest = f"{i + 1:064x}"
        blind_cases.append({
            "blind_case_id": blind_id,
            "target_sha256": digest,
        })
        owner_rows.append({
            "blind_case_id": blind_id,
            "original_case_id": f"private-{i:04d}",
            "original_story_uuid": f"story-{i % 13:02d}",
            "target_sha256": digest,
        })
        result_rows.append({
            "blind_case_id": blind_id,
            "target_sha256": digest,
            "scores_1_to_5": dict(SCORES),
            "decision": "PASS",
            "severe_flags": [],
            "evidence_summary": "Synthetic-only review evidence.",
        })
    blind_raw = (
        json.dumps({
            "schema": m.BLIND_SCHEMA,
            "reviewer": "B2",
            "cases": blind_cases,
        }, sort_keys=True).encode() + b"\n"
    )
    instructions_raw = b"Synthetic B2 instructions"
    map_raw = json.dumps({
        "schema": m.MAP_SCHEMA,
        "reviewer": "B2",
        "mapping": owner_rows,
    }, sort_keys=True).encode()
    result_raw = json.dumps({
        "schema": m.RESULT_SCHEMA,
        "reviewer": "B2",
        "status": "REVIEW_COMPLETE",
        "counts": {"PASS": 72, "HOLD": 0, "REJECT": 0},
        "cases": result_rows,
    }, sort_keys=True).encode()
    execution_raw = b"Synthetic-only execution transcript/provider record"
    receipt = {
        "schema": m.EXECUTION_SCHEMA,
        "reviewer": "B2",
        "execution_mode": "STATELESS_API",
        "provider": "synthetic-provider",
        "model_id": "synthetic-model",
        "session_or_request_id": "req-synthetic",
        "started_at_utc": "2026-11-06T09:00:00Z",
        "completed_at_utc": "2026-11-06T09:05:00Z",
        "blind_input_sha256": hashlib.sha256(blind_raw).hexdigest(),
        "instructions_sha256": hashlib.sha256(instructions_raw).hexdigest(),
        "result_sha256": hashlib.sha256(result_raw).hexdigest(),
        "transcript_or_provider_record_sha256": hashlib.sha256(execution_raw).hexdigest(),
        "attestations": {key: True for key in m.ATTESTATIONS},
        "owner_verification": {key: True for key in m.OWNER_VERIFICATION},
    }
    receipt_raw = json.dumps(receipt, sort_keys=True).encode()
    return blind_raw, instructions_raw, map_raw, result_raw, receipt_raw, execution_raw


class ReviewerB2AuditTests(unittest.TestCase):
    def test_valid_binding_and_attestation_stays_not_proven(self):
        result = m.audit(*fixture())
        self.assertEqual(
            result["status"],
            "B2_RESULT_BINDING_VALID__EXECUTION_ATTESTATION_PRESENT_NOT_PROVEN",
        )
        self.assertEqual(result["blind_input_to_owner_map_matches"], 72)
        self.assertEqual(result["owner_map_to_result_matches"], 72)
        self.assertEqual(result["scores_complete"], 72)
        self.assertTrue(result["owner_verification_complete"])
        self.assertTrue(result["reviewer_b2_independence_owner_attested"])
        self.assertFalse(result["cryptographic_independence_proven"])
        self.assertFalse(result["reviewer_b2_independence_verified"])
        self.assertEqual(result["quality_v1_admitted"], 0)

    def test_result_hash_mismatch_fails_closed(self):
        values = list(fixture())
        receipt = json.loads(values[4])
        receipt["result_sha256"] = "0" * 64
        values[4] = json.dumps(receipt).encode()
        with self.assertRaisesRegex(m.AuditHold, "B2_EXECUTION_HASH_BINDING_MISMATCH"):
            m.audit(*values)

    def test_result_target_sha_mismatch_fails_closed(self):
        values = list(fixture())
        result = json.loads(values[3])
        result["cases"][0]["target_sha256"] = "f" * 64
        values[3] = json.dumps(result).encode()
        receipt = json.loads(values[4])
        receipt["result_sha256"] = hashlib.sha256(values[3]).hexdigest()
        values[4] = json.dumps(receipt).encode()
        with self.assertRaisesRegex(m.AuditHold, "B2_RESULT_OWNER_MAP_SET_MISMATCH"):
            m.audit(*values)

    def test_pass_below_floor_fails_closed(self):
        values = list(fixture())
        result = json.loads(values[3])
        result["cases"][0]["scores_1_to_5"]["player_agency"] = 2
        values[3] = json.dumps(result).encode()
        receipt = json.loads(values[4])
        receipt["result_sha256"] = hashlib.sha256(values[3]).hexdigest()
        values[4] = json.dumps(receipt).encode()
        with self.assertRaisesRegex(m.AuditHold, "B2_PASS_GATE_VIOLATION"):
            m.audit(*values)

    def test_owner_record_inspection_is_required(self):
        values = list(fixture())
        receipt = json.loads(values[4])
        receipt["owner_verification"]["execution_record_inspected"] = False
        values[4] = json.dumps(receipt).encode()
        with self.assertRaisesRegex(m.AuditHold, "B2_OWNER_VERIFICATION_INCOMPLETE"):
            m.audit(*values)

    def test_missing_independence_attestation_fails_closed(self):
        values = list(fixture())
        receipt = json.loads(values[4])
        receipt["attestations"]["prior_conversations_or_memory_not_used"] = False
        values[4] = json.dumps(receipt).encode()
        with self.assertRaisesRegex(m.AuditHold, "B2_EXECUTION_ATTESTATIONS_INCOMPLETE"):
            m.audit(*values)


if __name__ == "__main__":
    unittest.main()
