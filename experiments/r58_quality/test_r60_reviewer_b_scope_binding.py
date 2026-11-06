"""Synthetic-only tests for Reviewer B source binding audit."""
from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch

from experiments.r58_quality import r60_reviewer_b_scope_binding as m


SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def _jsonl(rows):
    return b"".join(json.dumps(row, sort_keys=True).encode() + b"\n" for row in rows)


def fixture():
    source_packets = []
    blind_packets = []
    map_rows = []
    result_rows = []
    for story_index in range(13):
        story_uuid = f"story-{story_index:02d}"
        source_cases = []
        blind_cases = []
        start = len(map_rows)
        end = min(192, start + (15 if story_index < 10 else 14))
        for i in range(start, end):
            digest = f"{i + 1:064x}"
            blind_id = f"RB-{i + 1:04d}"
            original_id = f"gold-case-{i + 1:04d}"
            source_cases.append({"case_id": original_id, "target_sha256": digest})
            blind_cases.append({"blind_case_id": blind_id, "target_sha256": digest})
            map_rows.append({
                "blind_case_id": blind_id,
                "original_case_id": original_id,
                "original_story_uuid": story_uuid,
                "target_sha256": digest,
            })
            decision = "PASS" if i < 178 else "HOLD" if i < 190 else "REJECT"
            result_rows.append({
                "blind_case_id": blind_id,
                "target_sha256": digest,
                "scores_1_to_5": dict(SCORES),
                "decision": decision,
                "severe_flags": ["serious_player_agency"] if decision == "REJECT" else [],
                "evidence_summary": "Synthetic-only evidence summary",
            })
        source_packets.append({
            "schema": m.SOURCE_PACKET_SCHEMA,
            "status": "PRIVATE_STORY_REVIEW_PACKET_NOT_REVIEWED",
            "story_uuid": story_uuid,
            "cases": source_cases,
        })
        blind_packets.append({
            "schema": m.BLIND_PACKET_SCHEMA,
            "reviewer": "B",
            "blind_story_packet_id": f"RB-STORY-{story_index + 1:02d}",
            "cases": blind_cases,
        })

    blind_raw = _jsonl(blind_packets)
    map_raw = json.dumps({
        "schema": m.ID_MAP_SCHEMA,
        "reviewer": "B",
        "mapping": map_rows,
    }, sort_keys=True).encode()
    instructions_raw = b"Synthetic-only reviewer B blind instructions"
    source_raw = _jsonl(source_packets)
    result_raw = json.dumps({
        "schema": m.RESULT_SCHEMA,
        "reviewer": "B",
        "status": "REVIEW_COMPLETE",
        "counts": {"PASS": 178, "HOLD": 12, "REJECT": 2},
        "cases": result_rows,
    }, sort_keys=True).encode()
    pins = {
        "B_BLIND_INPUT_SHA256": hashlib.sha256(blind_raw).hexdigest(),
        "B_ID_MAP_SHA256": hashlib.sha256(map_raw).hexdigest(),
        "B_INSTRUCTIONS_SHA256": hashlib.sha256(instructions_raw).hexdigest(),
        "GOLD192_SOURCE_SHA256": hashlib.sha256(source_raw).hexdigest(),
        "B_RESULTS_SHA256": hashlib.sha256(result_raw).hexdigest(),
    }
    return blind_raw, map_raw, instructions_raw, source_raw, result_raw, pins


class ReviewerBScopeBindingTests(unittest.TestCase):
    def _audit_with_pins(self, values):
        blind_raw, map_raw, instructions_raw, source_raw, result_raw, pins = values
        with (
            patch.object(m, "B_BLIND_INPUT_SHA256", pins["B_BLIND_INPUT_SHA256"]),
            patch.object(m, "B_ID_MAP_SHA256", pins["B_ID_MAP_SHA256"]),
            patch.object(m, "B_INSTRUCTIONS_SHA256", pins["B_INSTRUCTIONS_SHA256"]),
            patch.object(m, "GOLD192_SOURCE_SHA256", pins["GOLD192_SOURCE_SHA256"]),
            patch.object(m, "B_RESULTS_SHA256", pins["B_RESULTS_SHA256"]),
        ):
            return m.audit(blind_raw, map_raw, instructions_raw, source_raw, result_raw)

    def test_all_192_cases_bind_input_map_source_and_result(self):
        result = self._audit_with_pins(fixture())
        self.assertEqual(
            result["status"],
            "REVIEWER_B_SCOPE_BINDING_VERIFIED__INDEPENDENCE_PROVENANCE_HOLD",
        )
        self.assertEqual(result["reviewer_b_input_to_owner_map_matches"], 192)
        self.assertEqual(result["owner_id_map_to_gold192_source_matches"], 192)
        self.assertEqual(result["reviewer_b_result_to_owner_map_matches"], 192)
        self.assertTrue(result["reviewer_b_source_binding_verified"])
        self.assertFalse(result["reviewer_b_separate_session_execution_provenance_verified"])
        self.assertFalse(result["reviewer_b_independence_verified"])
        self.assertEqual(result["quality_v1_admitted"], 0)

    def test_blind_input_owner_identity_leak_fails_closed(self):
        values = list(fixture())
        blind_raw = values[0].replace(
            b'"blind_case_id": "RB-0001"',
            b'"blind_case_id": "RB-0001", "original_case_id": "leak"',
            1,
        )
        values[0] = blind_raw
        values[5]["B_BLIND_INPUT_SHA256"] = hashlib.sha256(blind_raw).hexdigest()
        with self.assertRaisesRegex(m.AuditHold, "BLIND_INPUT_OWNER_OR_REVIEWER_A_DATA_LEAK"):
            self._audit_with_pins(tuple(values))

    def test_owner_map_target_mismatch_fails_closed(self):
        values = list(fixture())
        mapping = json.loads(values[1])
        mapping["mapping"][0]["target_sha256"] = "f" * 64
        values[1] = json.dumps(mapping, sort_keys=True).encode()
        values[5]["B_ID_MAP_SHA256"] = hashlib.sha256(values[1]).hexdigest()
        with self.assertRaisesRegex(m.AuditHold, "BLIND_INPUT_OWNER_MAP_TARGET_MISMATCH"):
            self._audit_with_pins(tuple(values))

    def test_owner_map_source_case_mismatch_fails_closed(self):
        values = list(fixture())
        mapping = json.loads(values[1])
        mapping["mapping"][0]["original_case_id"] = "not-in-source"
        values[1] = json.dumps(mapping, sort_keys=True).encode()
        values[5]["B_ID_MAP_SHA256"] = hashlib.sha256(values[1]).hexdigest()
        with self.assertRaisesRegex(m.AuditHold, "OWNER_MAP_SOURCE_CASE_ID_MISSING"):
            self._audit_with_pins(tuple(values))

    def test_result_target_mismatch_fails_closed(self):
        values = list(fixture())
        result = json.loads(values[4])
        result["cases"][0]["target_sha256"] = "f" * 64
        values[4] = json.dumps(result, sort_keys=True).encode()
        values[5]["B_RESULTS_SHA256"] = hashlib.sha256(values[4]).hexdigest()
        with self.assertRaisesRegex(m.AuditHold, "B_RESULT_TARGET_SHA_INVALID"):
            self._audit_with_pins(tuple(values))

    def test_missing_score_fails_closed(self):
        values = list(fixture())
        result = json.loads(values[4])
        del result["cases"][0]["scores_1_to_5"]["player_agency"]
        values[4] = json.dumps(result, sort_keys=True).encode()
        values[5]["B_RESULTS_SHA256"] = hashlib.sha256(values[4]).hexdigest()
        with self.assertRaisesRegex(m.AuditHold, "B_RESULT_CASE_EVIDENCE_INCOMPLETE"):
            self._audit_with_pins(tuple(values))


if __name__ == "__main__":
    unittest.main()
