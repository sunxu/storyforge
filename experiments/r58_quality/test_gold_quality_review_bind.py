"""Synthetic-only coverage for Owner-local Gold192 review evidence binding."""
from __future__ import annotations

import copy
import contextlib
import io
import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import gold_quality_review_bind as binder
from gold_source_context_stage import StageHold, stage_source
from quality_v1 import EVIDENCE, FLOORS, SCORES, SEVERE, canonical, sha


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
    a = {"records": [{
        "case_id": source["case_id"], "target_sha256": digest,
        "decision_for_strict_ab_pairing": "PASS_ONLY",
        "case_level_scored_review_present": True,
        "evidence_granularity": "CASE_LEVEL_SCORED_REVIEW",
        "scores_1_to_5": a_scores,
    }]}
    b = {"cases": [{
        "target_sha256": digest, "decision": "PASS",
        "scores_1_to_5": a_scores, "severe_flags": [],
        "blind_case_id": "blind-001",
    }]}
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
        "reviewer_a_severe_flags": {k: False for k in SEVERE},
        "reviewer_a_evidence_ref": "private-a-case",
        "reviewer_b_evidence_ref": "private-b-case",
    }]
    # The strict 192/11 contract is exercised with real synthetic identities.
    aa = a["records"][0]
    bb = b["cases"][0]
    for i in range(1, 192):
        fake_hash = f"{i:064x}"
        a["records"].append({**aa, "case_id": f"synthetic-{i}", "target_sha256": fake_hash})
        b["cases"].append({**bb, "target_sha256": fake_hash})
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

    def test_aggregate_a_pass_without_case_scores_holds(self):
        args = fixture()
        args[1]["records"][0]["scores_1_to_5"] = None
        args[1]["records"][0]["case_level_scored_review_present"] = False
        result, safe = bind(*args)
        self.assertFalse(result)
        self.assertEqual(safe["hold_reasons"], {"CASE_LEVEL_SCORES_MISSING": 1})

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
            source_pin = "d" * 64
            stage_pin = sha(inputs["stage.jsonl"])
            owner[0]["staged_file_sha256"] = stage_pin
            inputs["owner.jsonl"] = b"".join(canonical(x) + b"\n" for x in owner)
            receipt = {
                "schema": "storyforge-gold-quality-supabase-source-stage-safe-v1",
                "staged_file_sha256": stage_pin,
                "source_context_file_sha256": source_pin,
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
            with (patch.object(binder, "A_SHA", sha(inputs["a.json"])),
                  patch.object(binder, "B_SHA", sha(inputs["b.json"])),
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
