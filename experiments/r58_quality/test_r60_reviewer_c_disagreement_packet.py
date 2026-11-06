"""Synthetic-only tests for the private Gold72 Reviewer C packet builder."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experiments.r58_quality.r60_reviewer_c_disagreement_packet import (
    PackageHold,
    _create_package,
    build,
    validate_crosswalk_safe,
)

SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 3,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def fixture():
    pairs = (
        [("CASE_LEVEL_SCORED_PASS", "PASS")] * 21
        + [("CASE_LEVEL_SCORED_PASS", "HOLD")] * 5
        + [("CASE_LEVEL_SCORED_PASS", "REJECT")] * 2
        + [("EXPLICIT_HOLD", "HOLD")] * 11
        + [("EXPLICIT_HOLD", "PASS")] * 30
        + [("EXPLICIT_HOLD", "REJECT")] * 3
    )
    staged, a_records, blind_cases, mappings, b_results = [], [], [], [], []
    for i, (a_class, b_decision) in enumerate(pairs):
        digest = f"{i + 1:064x}"
        case_id = f"private-case-{i:03d}"
        blind_id = f"B2-old-{i:03d}"
        staged.append({"case_id": case_id, "target_sha256": digest})
        if a_class == "CASE_LEVEL_SCORED_PASS":
            a_records.append({
                "case_id": case_id,
                "target_sha256": digest,
                "evidence_granularity": "CASE_LEVEL_SCORED_REVIEW",
                "reported_final_decision": "PASS_ONLY",
                "decision_for_strict_ab_decision_comparison": "PASS_ONLY",
                "case_level_scored_review_present": True,
                "aggregate_complement_only": False,
                "scores_1_to_5": dict(SCORES),
            })
        else:
            a_records.append({
                "case_id": case_id,
                "target_sha256": digest,
                "evidence_granularity": "CASE_ID_IN_EXPLICIT_HOLD_GROUP",
                "reported_final_decision": "HOLD",
                "decision_for_strict_ab_decision_comparison": "HOLD",
                "case_level_scored_review_present": False,
                "aggregate_complement_only": False,
                "scores_1_to_5": None,
            })
        blind_cases.append({
            "blind_case_id": blind_id,
            "priority": "normal",
            "history_starts_with_assistant": False,
            "review_focus": ["continuity", "player_agency"],
            "history": [{"role": "user", "content": f"synthetic history {i}"}],
            "current_user_text": f"synthetic user {i}",
            "target_assistant_text": f"synthetic target {i}",
            "target_sha256": digest,
        })
        mappings.append({
            "blind_case_id": blind_id,
            "original_case_id": case_id,
            "original_story_uuid": f"story-{i % 4}",
            "target_sha256": digest,
        })
        b_results.append({
            "blind_case_id": blind_id,
            "target_sha256": digest,
            "decision": b_decision,
        })

    for i in range(72, 192):
        digest = f"{i + 1:064x}"
        a_records.append({
            "case_id": f"other-case-{i:03d}",
            "target_sha256": digest,
            "evidence_granularity": "AGGREGATE_COMPLEMENT_ONLY",
            "reported_final_decision": "PASS_ONLY",
            "decision_for_strict_ab_decision_comparison": None,
            "case_level_scored_review_present": False,
            "aggregate_complement_only": True,
            "scores_1_to_5": None,
        })

    return (
        staged,
        {"records": a_records},
        [{"schema": "r60_gold72_reviewer_b2_blind_story_packet_v1",
          "reviewer": "B2", "cases": blind_cases}],
        {"schema": "r60_gold72_reviewer_b2_private_id_map_v1",
         "reviewer": "B2", "mapping": mappings},
        {"schema": "r60_gold72_reviewer_b2_results_v1",
         "reviewer": "B2", "status": "REVIEW_COMPLETE", "cases": b_results},
    )


class ReviewerCPacketTests(unittest.TestCase):
    def setUp(self):
        self.sources = fixture()
        self.counter = 0

    def token(self):
        self.counter += 1
        return f"tok{self.counter:08d}"

    @staticmethod
    def no_shuffle(_items):
        return None

    def test_builds_exact_40_disagreements_and_excludes_32_agreements(self):
        packets, owner_map, safe = build(
            *self.sources, token_factory=self.token, shuffle=self.no_shuffle
        )
        cases = [case for packet in packets for case in packet["cases"]]
        self.assertEqual(len(cases), 40)
        self.assertEqual(owner_map["candidate_count"], 40)
        self.assertEqual(len(owner_map["mapping"]), 40)
        self.assertEqual(safe["pair_counts"], {
            "CASE_LEVEL_SCORED_PASS__B2_HOLD": 5,
            "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
            "EXPLICIT_HOLD__B2_PASS": 30,
            "EXPLICIT_HOLD__B2_REJECT": 3,
        })
        self.assertEqual(safe["status"],
                         "REVIEWER_C_DISAGREEMENT_PACKAGE_BUILT__AWAITING_INDEPENDENT_REVIEW")
        self.assertEqual(len({case["blind_case_id"] for case in cases}), 40)
        self.assertFalse(safe["reviewer_c_execution_started"])
        self.assertEqual(safe["quality_v1_admitted"], 0)

    def test_blind_packet_has_new_ids_and_no_prior_review_or_owner_fields(self):
        packets, owner_map, _safe = build(
            *self.sources, token_factory=self.token, shuffle=self.no_shuffle
        )
        cases = [case for packet in packets for case in packet["cases"]]
        old_ids = {row["blind_case_id"] for row in self.sources[2][0]["cases"]}
        self.assertTrue(all(row["blind_case_id"] not in old_ids for row in cases))
        forbidden = {
            "case_id", "original_case_id", "original_story_uuid", "story_uuid",
            "reviewer_a_decision", "reviewer_b2_decision", "disagreement_type",
            "prior_b2_blind_case_id",
        }
        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)
        self.assertFalse(forbidden & set(keys(packets)))
        self.assertEqual(len(owner_map["mapping"]), 40)
        self.assertTrue(all("reviewer_a_decision" in row
                            and "reviewer_b2_decision" in row
                            for row in owner_map["mapping"]))

    def test_stale_crosswalk_safe_fails_closed(self):
        from experiments.r58_quality import r60_reviewer_ab2_gold72_crosswalk as crosswalk

        fresh = {
            "candidate_count": 72,
            "staging_sha256": "a" * 64,
            "source_context_sha256": "b" * 64,
            "reviewer_a_v3_report_sha256": "c" * 64,
            "reviewer_b2_blind_input_sha256": "d" * 64,
            "reviewer_b2_instructions_sha256": "e" * 64,
            "reviewer_b2_owner_map_sha256": "f" * 64,
            "reviewer_b2_result_sha256": "1" * 64,
            "reviewer_b2_execution_record_sha256": "2" * 64,
            "reviewer_a_evidence_granularity": {"CASE_LEVEL_SCORED_PASS": 28, "EXPLICIT_HOLD": 44},
            "reviewer_b2_decisions": {"PASS": 51, "HOLD": 16, "REJECT": 5},
            "a_b2_pair_counts": {},
            "a_b2_comparable_decision_cases": 72,
            "a_b2_semantic_decision_disagreements": 40,
            "a_b2_semantic_decision_agreements": 32,
        }
        safe = dict(fresh, schema=crosswalk.SAFE_SCHEMA, status=crosswalk.SAFE_STATUS)
        validate_crosswalk_safe(safe, fresh)
        safe["reviewer_b2_result_sha256"] = "9" * 64
        with self.assertRaisesRegex(PackageHold, "CROSSWALK_SAFE_STALE_OR_MISMATCH"):
            validate_crosswalk_safe(safe, fresh)

    def test_owner_identity_join_mismatch_holds(self):
        staged, a, blind, owner, result = self.sources
        owner["mapping"][0]["original_case_id"] = "wrong-case"
        with self.assertRaisesRegex(PackageHold, "CASE_SOURCE_JOIN_MISMATCH"):
            build(staged, a, blind, owner, result,
                  token_factory=self.token, shuffle=self.no_shuffle)

    def test_changed_decision_distribution_holds(self):
        staged, a, blind, owner, result = self.sources
        result["cases"][0]["decision"] = "HOLD"
        with self.assertRaisesRegex(PackageHold, "GOLD72_DISAGREEMENT_PAIR_COUNTS_MISMATCH"):
            build(staged, a, blind, owner, result,
                  token_factory=self.token, shuffle=self.no_shuffle)

    def test_duplicate_random_ids_hold(self):
        staged, a, blind, owner, result = self.sources
        with self.assertRaisesRegex(PackageHold, "C_BLIND_ID_COLLISION"):
            build(staged, a, blind, owner, result,
                  token_factory=lambda: "same-token-123", shuffle=self.no_shuffle)

    def test_missing_context_field_holds(self):
        staged, a, blind, owner, result = self.sources
        del blind[0]["cases"][21]["target_assistant_text"]
        with self.assertRaisesRegex(PackageHold, "BLIND_CASE_CONTEXT_FIELD_MISSING"):
            build(staged, a, blind, owner, result,
                  token_factory=self.token, shuffle=self.no_shuffle)

    def test_create_only_private_package(self):
        packets, owner_map, safe = build(
            *self.sources, token_factory=self.token, shuffle=self.no_shuffle
        )
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            parent.chmod(0o700)
            output = parent / "reviewer-c"
            instructions = b"# Reviewer C instructions\n" + b"x" * 128
            _create_package(output, packets, owner_map, safe, instructions)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            for path in output.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            safe = json.loads((output / "R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json").read_text())
            template = json.loads((output / "R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json").read_text())
            self.assertEqual(template["reviewer"], "C")
            self.assertEqual(template["status"], "PENDING_INDEPENDENT_REVIEW_EXECUTION")
            self.assertEqual(safe["execution_receipt_template_sha256"],
                             hashlib.sha256(
                                 (output / "R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json").read_bytes()
                             ).hexdigest())
            with self.assertRaisesRegex(PackageHold, "OUTPUT_DIR_INVALID_OR_EXISTS"):
                _create_package(output, packets, owner_map, safe, instructions)


if __name__ == "__main__":
    unittest.main()
