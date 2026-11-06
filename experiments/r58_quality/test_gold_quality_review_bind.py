"""Synthetic-only coverage for Owner-local Gold192 review evidence binding."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import gold_quality_review_bind as binder
from gold_source_context_stage import stage_source
from quality_v1 import EVIDENCE, FLOORS, SCORES, SEVERE, canonical, sha

try:
    from .r60_gold192_canonical_a_v3 import (
        A_SHA, A_SCHEMA, A_STATUS, A_SOURCE_PINS, B_SHA, B_SCHEMA, B_COUNTS,
    )
except ImportError:
    from r60_gold192_canonical_a_v3 import (
        A_SHA, A_SCHEMA, A_STATUS, A_SOURCE_PINS, B_SHA, B_SCHEMA, B_COUNTS,
    )


def fixture():
    target = "她把信递给玩家，等待回应。"
    source = {
        "case_id": "story-t00001", "story_id": "story-1",
        "session_id": "session-1", "target_sha256": sha(target.encode()),
        "target_assistant_text": target,
        "history": [
            {"role": "assistant", "content": "角色先说话。", "status": "completed"},
            {"role": "user", "content": "接下来怎么办？", "status": "completed"},
        ],
    }
    staged, _ = stage_source([source], "通用系统提示")
    digest = source["target_sha256"]
    a_scores = {k: max(4, FLOORS[k]) for k in SCORES}
    a_records = []
    for i in range(192):
        if i < 31:
            granularity = "CASE_LEVEL_SCORED_REVIEW"
            decision, strict, scored, aggregate, scores = (
                "PASS_ONLY", "PASS_ONLY", True, False, dict(a_scores)
            )
        elif i < 82:
            granularity = "CASE_ID_IN_EXPLICIT_HOLD_GROUP"
            decision, strict, scored, aggregate, scores = (
                "HOLD", "HOLD", False, False, None
            )
        elif i == 82:
            granularity = "CASE_ID_IN_EXPLICIT_REJECT_GROUP"
            decision, strict, scored, aggregate, scores = (
                "REJECT", "REJECT", False, False, None
            )
        else:
            granularity = "AGGREGATE_COMPLEMENT_ONLY"
            decision, strict, scored, aggregate, scores = (
                "PASS_ONLY", None, False, True, None
            )
        a_records.append({
            "case_id": source["case_id"] if i == 0 else f"synthetic-{i}",
            "target_sha256": digest if i == 0 else f"{i:064x}",
            "reported_final_decision": decision,
            "decision_for_strict_ab_decision_comparison": strict,
            "evidence_granularity": granularity,
            "case_level_scored_review_present": scored,
            "aggregate_complement_only": aggregate,
            "scores_1_to_5": scores,
        })
    a = {
        "schema": A_SCHEMA,
        "status": A_STATUS,
        "source_pins": dict(A_SOURCE_PINS),
        "records": a_records,
    }
    b_cases = []
    for i in range(192):
        target_hash = digest if i == 0 else f"{i:064x}"
        decision = "PASS" if i < 178 else "HOLD" if i < 190 else "REJECT"
        b_cases.append({
            "target_sha256": target_hash,
            "decision": decision,
            "scores_1_to_5": a_scores,
            "severe_flags": [],
            "blind_case_id": f"blind-{i:03d}",
        })
    b = {"schema": B_SCHEMA, "counts": dict(B_COUNTS), "cases": b_cases}
    evidence = {k: True for k in EVIDENCE}
    evidence.update({
        "known_protected_overlap": False,
        "final_heldout_overlap": False,
        "protected_test_body_accessed": False,
    })
    owner = [{
        "case_id": source["case_id"], "target_sha256": digest,
        "story_id": "story-1", "session_id": "session-1",
        "staged_file_sha256": "c" * 64,
        "source_context_file_sha256": "d" * 64,
        "source_version_sha256": "a" * 64,
        "world_graph_sha256": "b" * 64,
        "world_component_id": "component-1",
        "split": "train", "evidence": evidence,
        "owner_supplemental_severe_flags": {k: False for k in SEVERE},
        "owner_supplemental_severe_evidence_ref": "owner-private-review",
        "reviewer_a_evidence_ref": f"sha256:{A_SHA}#records[0]",
        "reviewer_b_evidence_ref": f"sha256:{B_SHA}#cases[0]",
    }]
    exclusions = [
        {"target_sha256": f"{i:064x}",
         "exclusion_reason": "EXCLUDED_FROM_TRAINING_DISAGREEMENT"}
        for i in range(1, 12)
    ]
    return staged, a, b, exclusions, owner


def bind(*args):
    return binder.bind(*args, "c" * 64, "d" * 64)


class BindTests(unittest.TestCase):
    def test_one_scored_case_stays_unadmitted(self):
        result, safe = bind(*fixture())
        self.assertEqual(len(result), 1)
        self.assertEqual(safe["review_bound_candidates"], 1)
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertFalse(safe["reviewer_independence_independently_proven"])
        self.assertEqual(result[0]["reviews"][0]["scores"]["chinese_prose"], 4)

    def test_source_structure_hold_is_not_misreported_as_owner_evidence_hold(self):
        staged, a, b, exclusions, owners = fixture()
        source_hold = copy.deepcopy(staged[0])
        source_hold["case_id"] = "source-structure-hold"
        source_hold["target_sha256"] = f"{1:064x}"
        source_hold["schema"] = None
        source_hold["status"] = "SOURCE_STRUCTURE_HOLD"
        source_hold["private_reason_code"] = "HISTORY_STRUCTURE_INVALID"
        staged.append(source_hold)

        result, safe = bind(staged, a, b, exclusions, owners)
        self.assertEqual(len(result), 1)
        self.assertEqual(safe["input_staged"], 2)
        self.assertEqual(safe["source_stage_ready"], 1)
        self.assertEqual(safe["source_stage_held"], 1)
        self.assertEqual(
            safe["source_stage_hold_reasons"], {"HISTORY_STRUCTURE_INVALID": 1}
        )
        self.assertEqual(safe["review_candidate_held"], 0)
        self.assertEqual(safe["hold_reasons"], {})

    def test_owner_safety_screen_is_separate_from_reviewer_a(self):
        result, _safe = bind(*fixture())
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["reviews"][0]["severe_flags"])
        self.assertEqual(
            result[0]["owner_supplemental_safety_review"]["scope"],
            "SUPPLEMENTAL_SEVERE_FLAG_SCREEN",
        )

    def test_owner_safety_positive_flag_holds(self):
        args = fixture()
        args[4][0]["owner_supplemental_severe_flags"]["safety_exclusion"] = True
        result, safe = bind(*args)
        self.assertEqual(result, [])
        self.assertEqual(safe["hold_reasons"], {
            "OWNER_SUPPLEMENTAL_SEVERE_FLAG_PRESENT": 1
        })

    def test_aggregate_a_pass_without_case_scores_holds_even_with_legacy_alias(self):
        args = fixture()
        first = args[1]["records"][0]
        replacement_scored = args[1]["records"][83]
        first.update({
            "reported_final_decision": "PASS_ONLY",
            "decision_for_strict_ab_decision_comparison": None,
            "decision_for_strict_ab_pairing": "PASS_ONLY",
            "evidence_granularity": "AGGREGATE_COMPLEMENT_ONLY",
            "case_level_scored_review_present": False,
            "aggregate_complement_only": True,
            "scores_1_to_5": None,
        })
        replacement_scored.update({
            "reported_final_decision": "PASS_ONLY",
            "decision_for_strict_ab_decision_comparison": "PASS_ONLY",
            "evidence_granularity": "CASE_LEVEL_SCORED_REVIEW",
            "case_level_scored_review_present": True,
            "aggregate_complement_only": False,
            "scores_1_to_5": dict(args[1]["records"][1]["scores_1_to_5"]),
        })
        result, safe = bind(*args)
        self.assertFalse(result)
        self.assertEqual(safe["hold_reasons"], {"CASE_LEVEL_SCORES_MISSING": 1})

    def test_superseded_a_report_schema_is_rejected(self):
        args = fixture()
        args[1]["schema"] = "superseded-r59-a-schema"
        with self.assertRaisesRegex(binder.BindHold, "CANONICAL_A_V3_REQUIRED"):
            bind(*args)

    def test_excluded_target_is_never_bound(self):
        args = fixture()
        digest = args[0][0]["target_sha256"]
        args[3][0]["target_sha256"] = digest
        result, safe = bind(*args)
        self.assertEqual(result, [])
        self.assertEqual(safe["hold_reasons"], {"EXCLUDED_BY_FROZEN_DISAGREEMENT_SET": 1})

    def test_missing_owner_evidence_holds_without_invention(self):
        args = fixture()
        args[4][0]["evidence"]["owner_quality_approved"] = False
        result, safe = bind(*args)
        self.assertEqual(result, [])
        self.assertEqual(safe["hold_reasons"], {"OWNER_REQUIRED_EVIDENCE_INCOMPLETE": 1})

    def test_mismatched_stage_pin_holds(self):
        args = fixture()
        args[4][0]["staged_file_sha256"] = "f" * 64
        result, safe = bind(*args)
        self.assertFalse(result)
        self.assertEqual(safe["hold_reasons"], {"OWNER_SOURCE_CONTEXT_PINS_MISMATCH": 1})

    def test_superseded_or_wrong_reviewer_a_locator_holds(self):
        args = fixture()
        args[4][0]["reviewer_a_evidence_ref"] = (
            "sha256:641b71e10a14318b57e69cb0239172f7016fe5b9d2149923f876308f5e6fe1e4"
            "#records[0]"
        )
        result, safe = bind(*args)
        self.assertFalse(result)
        self.assertEqual(safe["hold_reasons"], {"REVIEWER_EVIDENCE_REF_MISMATCH": 1})

    def test_world_overlap_in_candidate_set_holds(self):
        staged, a, b, exclusion, owners = fixture()
        two = copy.deepcopy(staged[0])
        two["case_id"] = "case-two"
        two["target_text"] = "另一个结尾"
        two["target_sha256"] = sha(two["target_text"].encode())
        two["messages"][-1]["content"] = "不同的玩家选择"
        two["input_messages_sha256"] = sha(canonical(two["messages"]))
        staged.append(two)
        a["records"][12]["case_id"] = "case-two"
        a["records"][12]["target_sha256"] = two["target_sha256"]
        b["cases"][12]["target_sha256"] = two["target_sha256"]
        b["cases"][12]["decision"] = "PASS"
        owner2 = copy.deepcopy(owners[0])
        owner2["case_id"] = "case-two"
        owner2["target_sha256"] = two["target_sha256"]
        owner2["split"] = "validation"
        owners.append(owner2)
        with self.assertRaisesRegex(binder.BindHold, "WORLD_OR_DUPLICATE_CANDIDATE_COLLISION"):
            bind(staged, a, b, exclusion, owners)

    def test_exclusions_accept_frozen_jsonl_and_json_array(self):
        rows = [
            {"target_sha256": "a" * 64, "exclusion_reason": "FROZEN"},
            {"target_sha256": "b" * 64, "exclusion_reason": "FROZEN"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "exclusions.jsonl"
            for payload in (
                b"".join(canonical(row) + b"\n" for row in rows),
                canonical(rows),
            ):
                path.write_bytes(payload)
                os.chmod(path, 0o600)
                self.assertEqual(
                    binder._jsonl_or_json_file(path, sha(payload), label="EXCLUSIONS"),
                    rows,
                )

    def test_private_input_hold_is_scoped_to_input_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "owner.jsonl"
            path.write_text("{}")
            os.chmod(path, 0o644)
            with self.assertRaisesRegex(
                binder.BindHold, "OWNER_EVIDENCE_SOURCE_PERMISSIONS_OR_SIZE"
            ):
                binder._private_input(path, "OWNER_EVIDENCE")

    def test_canonical_pinned_file_rejects_wrong_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.json"
            path.write_text("{}")
            os.chmod(path, 0o600)
            with self.assertRaisesRegex(binder.BindHold, "PINNED_SOURCE_MISMATCH"):
                binder._file(path, "0" * 64)

    def test_cli_emits_fixed_safe_reason_code(self):
        output = io.StringIO()
        argv = [
            "gold_quality_review_bind.py",
            "--staged-jsonl", "/private/staged.jsonl",
            "--staging-safe", "/private/staging-safe.json",
            "--reviewer-a", "/private/a.json",
            "--reviewer-b", "/private/b.json",
            "--exclusions", "/private/exclusions.jsonl",
            "--owner-evidence-jsonl", "/private/owner.jsonl",
            "--output-dir", "/private/out",
        ]
        with (
            contextlib.redirect_stdout(output),
            mock.patch.object(sys, "argv", argv),
            unittest.mock.patch.object(
                binder, "run", side_effect=binder.BindHold("PINNED_SOURCE_MISMATCH")
            ),
        ):
            code = binder.main()
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 42)
        self.assertEqual(payload["reason_code"], "PINNED_SOURCE_MISMATCH")
        self.assertFalse(payload["private_values_emitted"])
        self.assertEqual(payload["quality_v1_admitted"], 0)

    def test_secure_output_private_only(self):
        # Exercise IO with source fixtures pinned to local test bytes.
        staged, a, b, exclusions, owner = fixture()
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp) / "private"
            private.mkdir(mode=0o700)
            inputs = {
                "stage.jsonl": b"".join(canonical(x) + b"\n" for x in staged),
                "a.json": canonical(a),
                "b.json": canonical(b),
                "ex.json": canonical(exclusions),
                "owner.jsonl": b"".join(canonical(x) + b"\n" for x in owner),
            }
            a_pin = sha(inputs["a.json"])
            b_pin = sha(inputs["b.json"])
            owner[0]["reviewer_a_evidence_ref"] = f"sha256:{a_pin}#records[0]"
            owner[0]["reviewer_b_evidence_ref"] = f"sha256:{b_pin}#cases[0]"
            inputs["owner.jsonl"] = b"".join(canonical(x) + b"\\n" for x in owner)
            source_pin = "d" * 64
            stage_pin = sha(inputs["stage.jsonl"])
            owner[0]["staged_file_sha256"] = stage_pin
            inputs["owner.jsonl"] = b"".join(canonical(x) + b"\n" for x in owner)
            receipt = {
                "schema": "storyforge-r59-contiguous-suffix-stage-safe-v1",
                "status": "CONTIGUOUS_SUFFIX_SOURCE_STAGE_BUILT__NOT_QUALITY_ADMITTED",
                "source_rows": 1,
                "context_staged": 1,
                "context_structure_hold": 0,
                "staged_file_sha256": stage_pin,
                "source_context_file_sha256": source_pin,
                "previous_staged_file_sha256": "e" * 64,
                "source_histories_mutated": False,
                "original_staging_mutated": False,
                "quality_v1_admitted": 0,
                "training_authorized": False,
                "gpu_started": False,
            }
            inputs["safe.json"] = canonical(receipt)
            paths = {}
            for name, data in inputs.items():
                p = private / name
                p.write_bytes(data)
                os.chmod(p, 0o600)
                paths[name] = p
            # Patch canonical pins for synthetic-only IO test.
            from unittest.mock import patch
            with (patch.object(binder, "A_SHA", a_pin),
                  patch.object(binder, "B_SHA", b_pin),
                  patch.object(binder, "EX_SHA", sha(inputs["ex.json"]))):
                out = private / "out"
                safe = binder.run(
                    paths["stage.jsonl"], paths["safe.json"], paths["a.json"],
                    paths["b.json"], paths["ex.json"], paths["owner.jsonl"], out
                )
            self.assertEqual(safe["quality_v1_admitted"], 0)
            self.assertEqual(safe["review_bound_candidates"], 1)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
            result_file = out / "OWNER_REVIEWED_GOLD_CANDIDATES.jsonl"
            self.assertEqual(stat.S_IMODE(result_file.stat().st_mode), 0o600)
            self.assertNotIn(staged[0]["target_text"], json.dumps(safe))
            self.assertEqual(len(result_file.read_text().splitlines()), 1)
            self.assertEqual(
                hashlib.sha256(result_file.read_bytes()).hexdigest(),
                safe["reviewed_candidates_file_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
