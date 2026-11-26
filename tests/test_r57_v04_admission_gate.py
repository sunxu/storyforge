"""Synthetic, private-text-free tests for R57 V04 intake gate."""

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "r57_v04_admission_gate.py"
spec = importlib.util.spec_from_file_location("r57_v04_admission_gate", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SHA = "a" * 64


def row(token="sample-a", component="world-component-one", decision="ACCEPT", split="TRAIN"):
    return {
        "record_id": token,
        "source_pool": "GOLD87",
        "source_target_sha256": SHA,
        "source_file_sha256": "b" * 64,
        "history_sha256": "c" * 64,
        "target_time_rules_sha256": "d" * 64,
        "target_time_canon": "VERIFIED",
        "world_component_token": component,
        "rights_basis": "OWNER_ATTESTED_SCOPED",
        "content_boundary": "CASE_VERIFIED_PASS",
        "source_provenance_verified": True,
        "world_isolation_verified": True,
        "historical_train_exposure": "NO_OBSERVED_MATCH",
        "historical_validation_exposure": "NO_OBSERVED_MATCH",
        "historical_dev_exposure": "NO_OBSERVED_MATCH",
        "protected_test_isolation": "CUSTODIAN_METADATA_ATTESTED_CLEAR",
        "corpus_kind": "CANONICAL_GOLD",
        "parent_target_sha256": None,
        "derivation_delta_sha256": None,
        "source_quality_labels": ["NATURAL_NARRATIVE", "PLAYER_AGENCY"],
        "reviews": [
            {"reviewer_key": "r-one", "kind": "AI_ASSISTED", "outcome": "ACCEPT", "evidence_sha256": "e" * 64},
            {"reviewer_key": "r-two", "kind": "HUMAN", "outcome": "ACCEPT", "evidence_sha256": "f" * 64},
        ],
        "owner_signoff": "APPROVED",
        "decision": decision,
        "split": split,
        "rationale": "Synthetic source-evidence review: all required gates demonstrated.",
    }


def manifest(rows=None):
    return {
        "schema": mod.FORMAT,
        "no_r50_content_accessed": True,
        "training_authorized": False,
        "records": [] if rows is None else rows,
    }


class R57V04Test(unittest.TestCase):
    def assert_hold(self, packet, *, admission=False):
        with self.assertRaises(mod.GateError):
            mod.check_manifest(packet, require_admission=admission)

    def test_01_schema_declares_strict_manifest(self):
        path = ROOT / "evaluations" / "v0.3" / "r57" / "R57_DATASET_V04_ADMISSION_SCHEMA.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema"]["const"], mod.FORMAT)
        self.assertFalse(schema["additionalProperties"])

    def test_02_empty_draft_pass_zero(self):
        r = mod.check_manifest(manifest())
        self.assertEqual(r["admitted_total"], 0)
        self.assertEqual(r["record_count"], 0)

    def test_03_empty_admission_blocks(self):
        self.assert_hold(manifest(), admission=True)

    def test_04_one_accepted_passes_structurally(self):
        r = mod.check_manifest(manifest([row()]), require_admission=True)
        self.assertEqual(r["admitted_total"], 1)
        self.assertEqual(r["isolated_world_component_count_for_accepted"], 1)
        self.assertNotIn("sample-a", json.dumps(r))

    def test_05_r50_access_blocks(self):
        d = manifest()
        d["no_r50_content_accessed"] = False
        self.assert_hold(d)

    def test_06_training_authorization_blocks(self):
        d = manifest()
        d["training_authorized"] = True
        self.assert_hold(d)

    def test_07_missing_owner_signoff_blocks(self):
        x = row()
        x["owner_signoff"] = "PENDING"
        self.assert_hold(manifest([x]))

    def test_08_one_reviewer_blocks(self):
        x = row()
        x["reviews"] = x["reviews"][:1]
        self.assert_hold(manifest([x]))

    def test_09_duplicate_reviewer_blocks(self):
        x = row()
        x["reviews"][1]["reviewer_key"] = x["reviews"][0]["reviewer_key"]
        self.assert_hold(manifest([x]))

    def test_10_world_leak_blocks(self):
        x = row()
        y = row("sample-b", component="world-component-one", split="VALIDATION")
        y["source_target_sha256"] = "9" * 64
        self.assert_hold(manifest([x, y]))

    def test_11_different_world_split_passes(self):
        x = row()
        y = row("sample-b", component="world-component-two", split="VALIDATION")
        y["source_target_sha256"] = "9" * 64
        r = mod.check_manifest(manifest([x, y]), require_admission=True)
        self.assertEqual(r["isolated_world_component_count_for_accepted"], 2)

    def test_12_same_target_duplicate_blocks(self):
        x = row()
        y = row("sample-b", component="world-component-two", split="TRAIN")
        self.assert_hold(manifest([x, y]))

    def test_13_unreviewed_age_risk_blocks(self):
        x = row()
        x["content_boundary"] = "HOLD"
        self.assert_hold(manifest([x]))

    def test_14_bad_historical_dev_exposure_blocks(self):
        x = row()
        x["historical_dev_exposure"] = "MATCHED_DISCLOSED"
        self.assert_hold(manifest([x]))

    def test_15_missing_protected_test_attestation_blocks(self):
        x = row()
        x["protected_test_isolation"] = "HOLD_NOT_CHECKED"
        self.assert_hold(manifest([x]))

    def test_16_diagnostic_negative_cannot_train(self):
        x = row()
        x["corpus_kind"] = "DIAGNOSTIC_NEGATIVE"
        self.assert_hold(manifest([x]))

    def test_17_derived_target_needs_parent(self):
        x = row()
        x["corpus_kind"] = "DERIVED_FROM_ORIGINAL"
        self.assert_hold(manifest([x]))

    def test_18_valid_derived_target_with_provenance(self):
        x = row()
        x["corpus_kind"] = "DERIVED_FROM_ORIGINAL"
        x["parent_target_sha256"] = "1" * 64
        x["derivation_delta_sha256"] = "2" * 64
        r = mod.check_manifest(manifest([x]), require_admission=True)
        self.assertEqual(r["admitted_total"], 1)

    def test_19_hold_kept_out_of_training(self):
        x = row(decision="HOLD", split="NONE")
        x["owner_signoff"] = "PENDING"
        x["reviews"] = []
        r = mod.check_manifest(manifest([x]))
        self.assertEqual(r["count_by_decision"]["HOLD"], 1)

    def test_20_hold_cannot_have_validation_split(self):
        x = row(decision="HOLD", split="VALIDATION")
        x["owner_signoff"] = "PENDING"
        self.assert_hold(manifest([x]))

    def test_21_unknown_metadata_fails_closed(self):
        x = row()
        x["raw_story_content"] = "synthetic dummy; field not allowed"
        self.assert_hold(manifest([x]))

    def test_22_unresolved_target_canon_blocks(self):
        x = row()
        x["target_time_canon"] = "NOT_CHECKED"
        self.assert_hold(manifest([x]))

    def test_23_source_rights_not_checked_blocks(self):
        x = row()
        x["rights_basis"] = "NOT_CHECKED"
        self.assert_hold(manifest([x]))

    def test_24_actual_source_requires_explicit_provenance(self):
        x = row()
        x["source_provenance_verified"] = False
        self.assert_hold(manifest([x]))

    def test_25_source_inventory_count_only(self):
        path = ROOT / "docs" / "evidence" / "R57_DATA_SOURCE_INVENTORY_SAFE.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(sum(p["rows"] for p in obj["frozen_source_pools"]), 195)
        self.assertEqual(obj["dataset_v04"]["admitted_train"], 0)
        self.assertFalse(obj["dataset_v04"]["protected_test_body_accessed"])

    def test_26_no_private_counters_in_safe_report(self):
        packet = manifest([row()])
        r = mod.check_manifest(packet)
        encoded = json.dumps(r)
        for bad in ["record_id", "world-component-one", "source_target_sha256", "reviewer_key"]:
            self.assertNotIn(bad, encoded)

    def test_27_synthetic_cannot_be_accepted(self):
        x = row()
        x["corpus_kind"] = "SYNTHETIC"
        self.assert_hold(manifest([x]))

    def test_28_duplicate_quality_labels_blocks(self):
        x = row()
        x["source_quality_labels"].append("PLAYER_AGENCY")
        self.assert_hold(manifest([x]))

    def test_29_bad_hash_blocks(self):
        x = row()
        x["source_file_sha256"] = "0" * 63
        self.assert_hold(manifest([x]))

    def test_30_root_extra_field_blocks(self):
        d = manifest()
        d["private_answers"] = []
        self.assert_hold(d)


if __name__ == "__main__":
    unittest.main()
