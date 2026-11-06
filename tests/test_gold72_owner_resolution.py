from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from storyforge_gold_quality import gold72_owner_resolution as owner_resolution
from storyforge_gold_quality.gold72_owner_resolution import (
    OwnerResolutionHold,
    import_owner_resolution,
    prepare_owner_resolution,
    validate_owner_resolution,
)
from storyforge_gold_quality.manifest import ManifestError, load_events, safe_report


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Gold72OwnerResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir(mode=0o700)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.paths = {}
        self._build_fixtures()
        pin_patch = patch.multiple(
            owner_resolution,
            CANONICAL_A_V3_SHA256=hashlib.sha256(self.a_report_path.read_bytes()).hexdigest(),
            CANONICAL_B2_RESULTS_SHA256=hashlib.sha256(self.b2_result_path.read_bytes()).hexdigest(),
        )
        pin_patch.start()
        self.addCleanup(pin_patch.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, raw, *, private=True):
        path = self.private / name if private else self.repo / name
        path.write_bytes(raw)
        if private:
            path.chmod(0o600)
        return path

    def json_file(self, name, value, *, private=True):
        return self.write(
            name,
            (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(),
            private=private,
        )

    def _build_fixtures(self):
        self.instructions = self.write("instructions.md", b"synthetic reviewer instructions\n", private=False)
        blind_cases, owner_rows, result_rows = [], [], []
        for i in range(40):
            if i < 5:
                a_class, a_decision, b_decision = "CASE_LEVEL_SCORED_PASS", "PASS", "HOLD"
            elif i < 7:
                a_class, a_decision, b_decision = "CASE_LEVEL_SCORED_PASS", "PASS", "REJECT"
            elif i < 37:
                a_class, a_decision, b_decision = "EXPLICIT_HOLD", "HOLD", "PASS"
            else:
                a_class, a_decision, b_decision = "EXPLICIT_HOLD", "HOLD", "REJECT"
            blind_id = f"C-SYNTH-{i:02d}"
            digest = sha(f"target-{i}")
            blind_cases.append({
                "blind_case_id": blind_id,
                "target_sha256": digest,
                "history": [{"role": "user", "content": f"synthetic history {i}"}],
                "current_user_text": f"synthetic user {i}",
                "target_assistant_text": f"synthetic answer {i}",
            })
            owner_rows.append({
                "blind_case_id": blind_id,
                "original_case_id": f"owner-case-{i:02d}",
                "original_story_uuid": f"story-{i:02d}",
                "target_sha256": digest,
                "reviewer_a_decision": a_decision,
                "reviewer_b2_decision": b_decision,
                "reviewer_a_evidence_class": a_class,
                "disagreement_type": f"{a_class}__B2_{b_decision}",
                "prior_b2_blind_case_id": f"B2-SYNTH-{i:02d}",
            })
            if i < 38:
                decision, scores = "PASS", {
                    "chinese_prose": 4, "character_consistency": 4,
                    "npc_initiative": 3, "player_agency": 4,
                    "narrative_continuity": 4, "rule_fidelity": 4,
                }
            elif i == 38:
                decision, scores = "HOLD", {
                    "chinese_prose": 3, "character_consistency": 4,
                    "npc_initiative": 3, "player_agency": 4,
                    "narrative_continuity": 4, "rule_fidelity": 4,
                }
            else:
                decision, scores = "REJECT", {
                    "chinese_prose": 2, "character_consistency": 2,
                    "npc_initiative": 2, "player_agency": 2,
                    "narrative_continuity": 2, "rule_fidelity": 2,
                }
            result_rows.append({
                "blind_case_id": blind_id,
                "target_sha256": digest,
                "decision": decision,
                "scores_1_to_5": scores,
                "severe_flags": [],
                "evidence_summary": f"synthetic evidence summary {i}",
            })

        a_records = []
        b2_rows = []
        for i, owner_row in enumerate(owner_rows):
            digest = owner_row["target_sha256"]
            is_scored = owner_row["reviewer_a_evidence_class"] == "CASE_LEVEL_SCORED_PASS"
            a_decision = "PASS_ONLY" if is_scored else "HOLD"
            a_scores = {
                "chinese_prose": 4, "character_consistency": 4,
                "npc_initiative": 3, "player_agency": 4,
                "narrative_continuity": 4, "rule_fidelity": 4,
            } if is_scored else None
            a_records.append({
                "target_sha256": digest,
                "case_id": owner_row["original_case_id"],
                "reported_final_decision": a_decision,
                "decision_for_strict_ab_decision_comparison": a_decision,
                "case_level_scored_review_present": is_scored,
                "aggregate_complement_only": False,
                "evidence_granularity": "CASE_LEVEL_SCORED_REVIEW" if is_scored else "CASE_ID_IN_EXPLICIT_HOLD_GROUP",
                "scores_1_to_5": a_scores,
            })
            b2_rows.append({
                "blind_case_id": owner_row["prior_b2_blind_case_id"],
                "target_sha256": digest,
                "decision": owner_row["reviewer_b2_decision"],
                "scores_1_to_5": {
                    "chinese_prose": 4, "character_consistency": 4,
                    "npc_initiative": 3, "player_agency": 4,
                    "narrative_continuity": 4, "rule_fidelity": 4,
                },
                "severe_flags": [],
                "evidence_summary": f"synthetic B2 evidence {i}",
            })

        for i in range(32):
            digest = sha(f"agreement-{i}")
            is_scored = i < 21
            decision = "PASS_ONLY" if is_scored else "HOLD"
            b_decision = "PASS" if is_scored else "HOLD"
            a_records.append({
                "target_sha256": digest,
                "case_id": f"agreement-case-{i:02d}",
                "reported_final_decision": decision,
                "decision_for_strict_ab_decision_comparison": decision,
                "case_level_scored_review_present": is_scored,
                "aggregate_complement_only": False,
                "evidence_granularity": "CASE_LEVEL_SCORED_REVIEW" if is_scored else "CASE_ID_IN_EXPLICIT_HOLD_GROUP",
                "scores_1_to_5": {
                    "chinese_prose": 4, "character_consistency": 4,
                    "npc_initiative": 3, "player_agency": 4,
                    "narrative_continuity": 4, "rule_fidelity": 4,
                } if is_scored else None,
            })
            b2_rows.append({
                "blind_case_id": f"B2-AGREEMENT-{i:02d}",
                "target_sha256": digest,
                "decision": b_decision,
                "scores_1_to_5": {
                    "chinese_prose": 4, "character_consistency": 4,
                    "npc_initiative": 3, "player_agency": 4,
                    "narrative_continuity": 4, "rule_fidelity": 4,
                },
                "severe_flags": [],
                "evidence_summary": f"synthetic B2 agreement evidence {i}",
            })
        for i in range(120):
            a_records.append({
                "target_sha256": sha(f"other-a-record-{i}"),
                "case_id": f"other-a-case-{i:03d}",
                "reported_final_decision": "PASS_ONLY",
                "decision_for_strict_ab_decision_comparison": "PASS_ONLY",
                "case_level_scored_review_present": True,
                "aggregate_complement_only": False,
                "evidence_granularity": "CASE_LEVEL_SCORED_REVIEW",
                "scores_1_to_5": {
                    "chinese_prose": 4, "character_consistency": 4,
                    "npc_initiative": 3, "player_agency": 4,
                    "narrative_continuity": 4, "rule_fidelity": 4,
                },
            })
        self.a_report = {
            "schema": "r58_gold192_reviewer_a_results_v3_reconciled_private_v1",
            "status": "V3_SOURCES_NORMALIZED__192_IDENTITIES_VERIFIED__EVIDENCE_GRANULARITY_EXPLICIT",
            "records": a_records,
        }
        self.b2_result = {
            "schema": "r60_gold72_reviewer_b2_results_v1",
            "reviewer": "B2",
            "status": "REVIEW_COMPLETE",
            "counts": {"PASS": 51, "HOLD": 16, "REJECT": 5},
            "cases": b2_rows,
        }
        self.blind_raw = (
            json.dumps({
                "schema": "r60_gold72_reviewer_c_blind_story_packet_v1",
                "reviewer": "C",
                "blind_story_packet_id": "C-STORY-SYNTH",
                "case_count": 40,
                "cases": blind_cases,
            }, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        self.map = {
            "schema": "r60_gold72_reviewer_c_private_id_map_v1",
            "status": "OWNER_ONLY_PRIVATE_MAPPING",
            "reviewer": "C",
            "candidate_count": 40,
            "mapping": owner_rows,
        }
        self.result = {
            "schema": "r60_gold72_reviewer_c_results_v1",
            "reviewer": "C",
            "status": "REVIEW_COMPLETE",
            "counts": {"PASS": 38, "HOLD": 1, "REJECT": 1},
            "cases": result_rows,
        }
        self.receipt_template = {
            "schema": "r60_gold72_reviewer_c_execution_receipt_v1",
            "reviewer": "C",
            "status": "PENDING_INDEPENDENT_REVIEW_EXECUTION",
            "blind_input_sha256": hashlib.sha256(self.blind_raw).hexdigest(),
            "instructions_sha256": hashlib.sha256(self.instructions.read_bytes()).hexdigest(),
            "attestations": {
                "reviewer_a_materials_not_provided": None,
                "reviewer_b2_materials_not_provided": None,
                "owner_id_map_not_provided": None,
                "prior_conversations_or_memory_not_used": None,
                "tools_and_connectors_not_used": None,
                "all_40_cases_reviewed_independently": None,
            },
            "owner_verification": {
                "input_hashes_rechecked": False,
                "execution_record_inspected": False,
                "result_hash_rechecked": False,
                "case_binding_rechecked": False,
            },
        }
        self.resolution_template = {
            "schema": "r60_gold72_owner_disagreement_resolution_private_v1",
            "status": "PENDING_REVIEWER_C_AND_OWNER_DECISION",
            "case_count": 40,
            "cases": [
                {
                    **row,
                    "reviewer_c_decision": None,
                    "reviewer_c_scores_1_to_5": None,
                    "reviewer_c_severe_flags": None,
                    "reviewer_c_evidence_summary": None,
                    "owner_decision": None,
                    "owner_rationale_cn": None,
                    "owner_evidence_refs": [],
                    "owner_decided_at_utc": None,
                    "owner_signoff": False,
                }
                for row in owner_rows
            ],
        }
        self.blind = self.write("blind.jsonl", self.blind_raw)
        self.owner_map = self.json_file("owner-map.json", self.map)
        self.result_path = self.json_file("result.json", self.result)
        self.receipt_template_path = self.json_file("receipt-template.json", self.receipt_template)
        self.resolution_template_path = self.json_file("resolution-template.json", self.resolution_template)
        self.package_safe = {
            "schema": "r60_gold72_reviewer_c_disagreement_package_safe_v1",
            "status": "REVIEWER_C_DISAGREEMENT_PACKAGE_BUILT__AWAITING_INDEPENDENT_REVIEW",
            "candidate_count": 40,
            "blind_input_sha256": hashlib.sha256(self.blind.read_bytes()).hexdigest(),
            "instructions_sha256": hashlib.sha256(self.instructions.read_bytes()).hexdigest(),
            "owner_map_sha256": hashlib.sha256(self.owner_map.read_bytes()).hexdigest(),
            "execution_receipt_template_sha256": hashlib.sha256(self.receipt_template_path.read_bytes()).hexdigest(),
            "owner_resolution_template_sha256": hashlib.sha256(self.resolution_template_path.read_bytes()).hexdigest(),
        }
        self.package_safe_path = self.json_file("package-safe.json", self.package_safe)
        self.results_only_safe = {
            "schema": "r60_gold72_reviewer_c_results_only_safe_v1",
            "status": "C_RESULTS_BINDING_VALID__EXECUTION_RECORD_UNAVAILABLE",
            "candidate_count": 40,
            "case_bindings_valid": 40,
            "decision_counts": {"PASS": 38, "HOLD": 1, "REJECT": 1},
            "package_pins_rechecked": True,
            "execution_metadata_sha256": None,
            "execution_record_available": False,
            "execution_attestation_complete": False,
            "reviewer_c_independence_verified": False,
            "cryptographic_independence_proven": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }
        self.results_only_path = self.json_file("results-only-safe.json", self.results_only_safe)
        self.a_report_path = self.json_file("a-v3.json", self.a_report)
        self.b2_result_path = self.json_file("b2-results.json", self.b2_result)
        self.crosswalk_safe = {
            "schema": "r60_gold72_reviewer_a_b2_crosswalk_safe_v1",
            "status": "A_B2_CROSSWALK_COMPLETE__ADMISSION_HOLD",
            "candidate_count": 72,
            "a_b2_comparable_decision_cases": 72,
            "a_b2_semantic_decision_disagreements": 40,
            "a_b2_semantic_decision_agreements": 32,
            "reviewer_a_v3_report_sha256": hashlib.sha256(self.a_report_path.read_bytes()).hexdigest(),
            "reviewer_b2_result_sha256": hashlib.sha256(self.b2_result_path.read_bytes()).hexdigest(),
            "reviewer_b2_decisions": {"PASS": 51, "HOLD": 16, "REJECT": 5},
            "a_b2_pair_counts": {
                "CASE_LEVEL_SCORED_PASS__B2_PASS": 21,
                "CASE_LEVEL_SCORED_PASS__B2_HOLD": 5,
                "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
                "EXPLICIT_HOLD__B2_PASS": 30,
                "EXPLICIT_HOLD__B2_HOLD": 11,
                "EXPLICIT_HOLD__B2_REJECT": 3,
            },
        }
        self.crosswalk_safe_path = self.json_file("crosswalk-safe.json", self.crosswalk_safe)

    def common_args(self, **extra):
        values = {
            "package_safe": self.package_safe_path,
            "receipt_template": self.receipt_template_path,
            "blind_input": self.blind,
            "instructions": self.instructions,
            "owner_map": self.owner_map,
            "result": self.result_path,
            "results_only_safe": self.results_only_path,
            "resolution_template": self.resolution_template_path,
            "reviewer_a_v3": self.a_report_path,
            "b2_results": self.b2_result_path,
            "crosswalk_safe": self.crosswalk_safe_path,
            "repo_root": self.repo,
        }
        values.update(extra)
        return Namespace(**values)

    def prepared_resolution(self):
        output = self.private / "owner-resolution.json"
        result = prepare_owner_resolution(self.common_args(output=output))
        self.assertEqual(result["status"], "OWNER_RESOLUTION_WORKSHEET_CREATED__PENDING_40_OWNER_DECISIONS")
        return output

    def complete_resolution(self, path):
        value = json.loads(path.read_text(encoding="utf-8"))
        for i, row in enumerate(value["cases"]):
            row["owner_decision"] = "PASS" if i < 38 else ("HOLD" if i == 38 else "REJECT")
            row["owner_decision_basis"] = "CROSS_REVIEWER_SYNTHESIS"
            row["owner_rationale_cn"] = f"Synthetic Owner rationale with source-based reasoning for case {i:02d}."
            row["owner_evidence_refs"] = [f"synthetic-evidence:{i:02d}#review"]
            row["owner_decided_at_utc"] = "2026-11-06T12:00:00Z"
            row["owner_signoff"] = True
        value["status"] = "OWNER_DECISIONS_COMPLETE_PENDING_IMPORT"
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)

    def test_prepare_pins_sources_and_copies_c_results_only(self):
        output = self.prepared_resolution()
        value = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(value["candidate_count"], 40)
        self.assertEqual(value["status"], "PENDING_OWNER_DECISIONS")
        self.assertEqual(value["source_pins"]["result_sha256"], hashlib.sha256(self.result_path.read_bytes()).hexdigest())
        self.assertEqual(value["source_pins"]["reviewer_a_v3_sha256"], hashlib.sha256(self.a_report_path.read_bytes()).hexdigest())
        self.assertEqual(value["source_pins"]["b2_results_sha256"], hashlib.sha256(self.b2_result_path.read_bytes()).hexdigest())
        self.assertEqual([row["reviewer_c_decision"] for row in value["cases"]].count("PASS"), 38)
        self.assertIn("reviewer_a_scores_1_to_5", value["cases"][0])
        self.assertIn("reviewer_b2_scores_1_to_5", value["cases"][0])
        self.assertIn("reviewer_b2_evidence_summary", value["cases"][0])
        self.assertTrue(all(row["owner_decision"] is None and row["owner_signoff"] is False for row in value["cases"]))
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertFalse(value["reviewer_c_independence_verified"])

    def test_prepare_is_create_only(self):
        output = self.prepared_resolution()
        with self.assertRaisesRegex(OwnerResolutionHold, "OUTPUT_PATH_INVALID_OR_EXISTS"):
            prepare_owner_resolution(self.common_args(output=output))

    def test_prepare_rejects_changed_package_pin(self):
        self.package_safe["blind_input_sha256"] = "f" * 64
        self.package_safe_path.write_text(json.dumps(self.package_safe))
        self.package_safe_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "PACKAGE_PIN_MISMATCH"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_prepare_rejects_noncanonical_a_v3_bytes(self):
        self.a_report["records"][0]["case_id"] = "tampered"
        self.a_report_path.write_text(json.dumps(self.a_report))
        self.a_report_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "CANONICAL_A_B2_CROSSWALK_PIN_OR_COHORT_INVALID"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_prepare_rejects_noncanonical_b2_result_bytes(self):
        self.b2_result["cases"][0]["evidence_summary"] = "tampered"
        self.b2_result_path.write_text(json.dumps(self.b2_result))
        self.b2_result_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "CANONICAL_A_B2_CROSSWALK_PIN_OR_COHORT_INVALID"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_prepare_rejects_unbound_execution_metadata_digest(self):
        self.results_only_safe["execution_metadata_sha256"] = "a" * 64
        self.results_only_path.write_text(json.dumps(self.results_only_safe))
        self.results_only_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "RESULTS_ONLY_SAFE_INVALID"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_prepare_rejects_results_only_safe_with_promoted_independence(self):
        self.results_only_safe["reviewer_c_independence_verified"] = True
        self.results_only_path.write_text(json.dumps(self.results_only_safe))
        self.results_only_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "RESULTS_ONLY_SAFE_INVALID"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_prepare_rejects_wrong_c_decision_counts(self):
        self.results_only_safe["decision_counts"] = {"PASS": 37, "HOLD": 2, "REJECT": 1}
        self.results_only_path.write_text(json.dumps(self.results_only_safe))
        self.results_only_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "RESULTS_ONLY_SAFE_INVALID"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_prepare_rejects_blind_owner_map_target_mismatch(self):
        self.map["mapping"][0]["target_sha256"] = "f" * 64
        self.owner_map.write_text(json.dumps(self.map))
        self.owner_map.chmod(0o600)
        self.package_safe["owner_map_sha256"] = hashlib.sha256(self.owner_map.read_bytes()).hexdigest()
        self.package_safe_path.write_text(json.dumps(self.package_safe))
        self.package_safe_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "BLIND_OWNER_MAP_SET_MISMATCH"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_prepare_rejects_result_owner_map_mismatch(self):
        self.result["cases"][0]["target_sha256"] = "f" * 64
        self.result_path.write_text(json.dumps(self.result))
        self.result_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "RESULT_OWNER_MAP_SET_MISMATCH"):
            prepare_owner_resolution(self.common_args(output=self.private / "never.json"))

    def test_validate_requires_all_owner_decisions(self):
        output = self.prepared_resolution()
        value = json.loads(output.read_text(encoding="utf-8"))
        value["status"] = "OWNER_DECISIONS_COMPLETE_PENDING_IMPORT"
        output.write_text(json.dumps(value))
        output.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_DECISION_MISSING_OR_INVALID"):
            validate_owner_resolution(self.common_args(
                owner_resolution=output, safe_output=self.private / "safe.json"
            ))

    def test_validate_complete_owner_resolution_creates_aggregate_safe(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        safe_path = self.private / "owner-resolution-safe.json"
        result = validate_owner_resolution(self.common_args(
            owner_resolution=output, safe_output=safe_path
        ))
        self.assertEqual(result["status"], "OWNER_RESOLUTION_COMPLETE__AGGREGATE_SAFE_CREATED")
        safe = json.loads(safe_path.read_text(encoding="utf-8"))
        self.assertEqual(safe["owner_decisions"], {"PASS": 38, "HOLD": 1, "REJECT": 1})
        self.assertEqual(safe["reviewer_c_decisions"], {"PASS": 38, "HOLD": 1, "REJECT": 1})
        self.assertEqual(sum(safe["resolution_matrix"].values()), 40)
        self.assertNotIn("owner_rationale_cn", json.dumps(safe))
        self.assertNotIn("original_case_id", json.dumps(safe))
        self.assertFalse(safe["execution_record_available"])
        self.assertFalse(safe["reviewer_c_independence_verified"])

    def test_validate_rejects_changed_c_result_copy(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        value = json.loads(output.read_text())
        value["cases"][0]["reviewer_c_decision"] = "REJECT"
        output.write_text(json.dumps(value))
        output.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_RESOLUTION_REVIEWER_C_VALUE_CHANGED"):
            validate_owner_resolution(self.common_args(
                owner_resolution=output, safe_output=self.private / "safe.json"
            ))

    def test_validate_rejects_missing_owner_signoff(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        value = json.loads(output.read_text())
        value["cases"][0]["owner_signoff"] = False
        output.write_text(json.dumps(value))
        output.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_SIGNOFF_MISSING"):
            validate_owner_resolution(self.common_args(
                owner_resolution=output, safe_output=self.private / "safe.json"
            ))

    def test_validate_rejects_short_rationale(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        value = json.loads(output.read_text())
        value["cases"][0]["owner_rationale_cn"] = "太短"
        output.write_text(json.dumps(value))
        output.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_RATIONALE_TOO_SHORT"):
            validate_owner_resolution(self.common_args(
                owner_resolution=output, safe_output=self.private / "safe.json"
            ))

    def test_validate_rejects_unsafe_evidence_reference(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        value = json.loads(output.read_text())
        value["cases"][0]["owner_evidence_refs"] = ["../../private/secret"]
        output.write_text(json.dumps(value))
        output.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_EVIDENCE_REFERENCES_INVALID"):
            validate_owner_resolution(self.common_args(
                owner_resolution=output, safe_output=self.private / "safe.json"
            ))

    def test_validate_rejects_naive_timestamp(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        value = json.loads(output.read_text())
        value["cases"][0]["owner_decided_at_utc"] = "2026-11-06T12:00:00"
        output.write_text(json.dumps(value))
        output.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_DECISION_TIMESTAMP_INVALID"):
            validate_owner_resolution(self.common_args(
                owner_resolution=output, safe_output=self.private / "safe.json"
            ))

    def test_validate_requires_hold_for_insufficient_evidence_basis(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        value = json.loads(output.read_text())
        value["cases"][0]["owner_decision_basis"] = "INSUFFICIENT_EVIDENCE_HOLD"
        output.write_text(json.dumps(value))
        output.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_INSUFFICIENT_EVIDENCE_MUST_HOLD"):
            validate_owner_resolution(self.common_args(
                owner_resolution=output, safe_output=self.private / "safe.json"
            ))

    def test_import_is_aggregate_only_and_idempotent(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        safe_path = self.private / "owner-resolution-safe.json"
        validate_owner_resolution(self.common_args(owner_resolution=output, safe_output=safe_path))
        manifest = self.private / "manifest.jsonl"
        args = Namespace(input=safe_path, manifest=manifest, repo_root=self.repo)
        first = import_owner_resolution(args)
        second = import_owner_resolution(args)
        self.assertEqual(first["status"], "GOLD72_OWNER_RESOLUTION_APPENDED")
        self.assertEqual(second["status"], "GOLD72_OWNER_RESOLUTION_ALREADY_IMPORTED")
        self.assertEqual(len(load_events(manifest)), 1)
        event_raw = manifest.read_text(encoding="utf-8")
        for forbidden in ("owner_rationale_cn", "owner_evidence_refs", "original_case_id", "story_uuid"):
            self.assertNotIn(forbidden, event_raw)
        report = json.dumps(safe_report(load_events(manifest)), ensure_ascii=False)
        self.assertIn('"owner_decisions"', report)
        self.assertNotIn("source_receipt_sha256", report)

    def test_import_rejects_changed_safe_after_canonical_import(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        safe_path = self.private / "owner-resolution-safe.json"
        validate_owner_resolution(self.common_args(owner_resolution=output, safe_output=safe_path))
        args = Namespace(input=safe_path, manifest=self.private / "manifest.jsonl", repo_root=self.repo)
        import_owner_resolution(args)
        value = json.loads(safe_path.read_text())
        value["owner_decisions"] = {"PASS": 37, "HOLD": 2, "REJECT": 1}
        safe_path.write_text(json.dumps(value))
        safe_path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "OWNER_RESOLUTION_SAFE_MATRIX_MARGINAL_MISMATCH"):
            import_owner_resolution(args)

    def test_manifest_event_rejects_independence_promotion(self):
        output = self.prepared_resolution()
        self.complete_resolution(output)
        safe_path = self.private / "owner-resolution-safe.json"
        validate_owner_resolution(self.common_args(owner_resolution=output, safe_output=safe_path))
        safe = json.loads(safe_path.read_text())
        safe["reviewer_c_independence_verified"] = True
        with self.assertRaises(ManifestError):
            from storyforge_gold_quality.gold72_owner_resolution import _validate_safe
            _validate_safe(safe)

    def test_duplicate_json_keys_fail_closed(self):
        path = self.private / "bad.json"
        path.write_text('{"schema":"a","schema":"b"}')
        path.chmod(0o600)
        with self.assertRaisesRegex(OwnerResolutionHold, "DUPLICATE_JSON_KEY"):
            prepare_owner_resolution(self.common_args(
                package_safe=path, output=self.private / "never.json"
            ))


if __name__ == "__main__":
    unittest.main()
