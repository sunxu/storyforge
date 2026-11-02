"""Synthetic-only tests for private AI arbitration evidence import."""
from __future__ import annotations

import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path

from storyforge_gold_quality.import_ai_arbitration import import_ai_arbitration
from storyforge_gold_quality.manifest import append_events, load_events, make_event
from storyforge_gold_quality.reconcile import reconcile_gold192, CANONICAL_REVIEWER_B_SHA256

A_SOURCE = "r58_reviewer_a_recovered_v6_20261102"
SCORES = {name: 4 for name in (
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
)}
TYPES = ["A_PASS_B_HOLD"] * 6 + ["A_PASS_B_REJECT"] + ["A_HISTORICAL_REJECT_B_PASS"] * 4
DECISIONS = ["HOLD"] * 4 + ["PASS", "PASS", "PASS", "HOLD", "HOLD", "HOLD", "PASS"]


class AIArbitrationImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.private_dir = root / "private"
        self.private_dir.mkdir(mode=0o700)
        self.manifest = self.private_dir / "events.jsonl"
        self.input = self.private_dir / "arbitration.private.json"
        self.safe = self.private_dir / "arbitration.safe.json"
        self.queue = self.private_dir / "queue.private.json"
        self.args = types.SimpleNamespace(
            input=self.input, safe_summary=self.safe, queue=self.queue,
            manifest=self.manifest, repo_root=self.repo)
        self._make_sources_and_manifest()

    def _make_sources_and_manifest(self):
        queue_cases, report_cases, events = [], [], []
        for i, kind in enumerate(TYPES):
            digest = f"{i + 1:064x}"
            b_decision = "HOLD" if kind == "A_PASS_B_HOLD" else (
                "REJECT" if kind == "A_PASS_B_REJECT" else "PASS")
            a_decision = "PASS_ONLY" if kind != "A_HISTORICAL_REJECT_B_PASS" else "REJECT"
            blind_id = f"RB-{i + 1:04d}"
            b = {"case_id": "reviewer-b:" + digest, "target_sha256": digest,
                 "reviewer_role": "REVIEWER_B",
                 "reviewer_source_sha256": CANONICAL_REVIEWER_B_SHA256,
                 "decision": b_decision, "scores": SCORES, "blind_case_id": blind_id}
            events.append(make_event("gold192", "BLIND_REVIEW", b, "t"))
            if a_decision == "REJECT":
                a = {"case_id": "reviewer-a:" + digest, "target_sha256": digest,
                     "reviewer_role": "REVIEWER_A", "reviewer_source": A_SOURCE,
                     "decision": "REJECT", "score_state": "UNAVAILABLE_NOT_SYNTHESIZED",
                     "evidence_tier": "FINAL_V6_REJECT_GROUP_ONLY"}
                events.append(make_event("gold192", "HISTORICAL_REJECT_EVIDENCE", a, "t"))
            else:
                a = {"case_id": "reviewer-a:" + digest, "target_sha256": digest,
                     "reviewer_role": "REVIEWER_A", "decision": "PASS_ONLY",
                     "scores": SCORES}
                events.append(make_event("gold192", "INCREMENTAL_REVIEW", a, "t"))
            queue_cases.append({
                "target_sha256": digest, "original_case_id": None,
                "disagreement_type": kind, "status": "PENDING_OWNER_ARBITRATION",
                "decision": None,
                "reviewer_a": {"decision": a_decision, "scores_missing": a_decision == "REJECT"},
                "reviewer_b": {"blind_case_id": blind_id, "decision": b_decision},
            })
            report_cases.append({
                "case_id": f"synthetic-case-{i}", "target_sha256": digest,
                "reviewer_b_blind_case_id": blind_id,
                "previous_disagreement_type": kind,
                "reviewer_a_previous_decision": a_decision,
                "reviewer_b_previous_decision": b_decision,
                "arbitration_decision": DECISIONS[i],
                "rationale_cn": "合成测试理由",
                "scope_limit_cn": "不构成准入",
                "review_basis": ["visible_history", "target_assistant_text"],
                "human_owner_approval": False, "quality_v1_admitted": False,
            })
        queue_doc = {"schema": "storyforge_gold192_arbitration_queue_private_v1",
                     "status": "PENDING_OWNER_ARBITRATION", "case_count": 11,
                     "cases": queue_cases}
        queue_raw = (json.dumps(queue_doc, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.queue.write_bytes(queue_raw)
        report = {
            "schema": "storyforge_gold192_ai_disagreement_arbitration_private_v1",
            "status": "AI_ARBITRATION_11_COMPLETED__OWNER_ADMISSION_HOLD",
            "source_integrity": {"arbitration_queue_sha256": hashlib.sha256(queue_raw).hexdigest(),
                                 "packet_case_count": 192, "matched_disagreements": 11},
            "cases": report_cases,
        }
        report_raw = (json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.input.write_bytes(report_raw)
        safe = {
            "schema": "storyforge_gold192_ai_disagreement_arbitration_safe_v1",
            "private_report_sha256": hashlib.sha256(report_raw).hexdigest(),
            "disagreements_matched": 11,
            "arbitration_decision_counts": {"PASS": 6, "HOLD": 5},
            "prior_a_b_decisions_preserved": True,
            "quality_v1_admitted": 0, "training_authorized": False,
            "gpu_started": False, "r50_accessed": False,
        }
        self.safe.write_text(json.dumps(safe), encoding="utf-8")
        append_events(self.manifest, events, self.repo)

    def test_imports_11_as_separate_non_owner_events_and_is_idempotent(self):
        first = import_ai_arbitration(self.args)
        second = import_ai_arbitration(self.args)
        self.assertEqual(first["events_appended"], 11)
        self.assertEqual(first["decision_counts"], {"HOLD": 5, "PASS": 6})
        self.assertEqual(second["events_appended"], 0)
        events = load_events(self.manifest)
        self.assertEqual(sum(e["event_type"] == "AI_ARBITRATION" for e in events), 11)
        result = reconcile_gold192(events)
        self.assertEqual(result["counts"]["ai_arbitration_events_present"], 11)
        self.assertEqual(result["counts"]["ai_arbitration_pass"], 6)
        self.assertEqual(result["counts"]["ai_arbitration_hold"], 5)
        self.assertEqual(result["counts"]["paired_case_count"], 7)
        self.assertEqual(result["quality_v1_admitted"], 0)
        self.assertFalse(result["training_authorized"])

    def test_report_tampering_fails_before_append(self):
        self.input.write_text(self.input.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ARBITRATION_SOURCE_PIN_OR_SCHEMA_MISMATCH"):
            import_ai_arbitration(self.args)
        self.assertEqual(sum(e["event_type"] == "AI_ARBITRATION"
                             for e in load_events(self.manifest)), 0)

    def test_previous_decision_mismatch_fails_before_append(self):
        report = json.loads(self.input.read_text())
        report["cases"][0]["reviewer_b_previous_decision"] = "PASS"
        raw = (json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.input.write_bytes(raw)
        safe = json.loads(self.safe.read_text())
        safe["private_report_sha256"] = hashlib.sha256(raw).hexdigest()
        self.safe.write_text(json.dumps(safe), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ARBITRATION_PRIOR_DECISION_MISMATCH"):
            import_ai_arbitration(self.args)
        self.assertEqual(sum(e["event_type"] == "AI_ARBITRATION"
                             for e in load_events(self.manifest)), 0)


if __name__ == "__main__":
    unittest.main()
