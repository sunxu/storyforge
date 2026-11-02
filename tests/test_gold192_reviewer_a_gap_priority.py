"""Synthetic-only tests: select seven A evidence gaps, never create reviews."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storyforge_gold_quality.arbitration_queue import write_private_queue
from storyforge_gold_quality.manifest import ManifestError, make_event
from storyforge_gold_quality.reconcile import CANONICAL_REVIEWER_B_SHA256
from storyforge_gold_quality.reviewer_a_gap_priority import (
    A_STATE,
    build_a_gap_priority,
)


def fixture():
    records, events = [], []
    for i in range(192):
        digest = f"{i + 1:064x}"
        # 79 scored, 4 unscored rejects, 109 V6-only aggregate passes.
        if i < 79:
            state, aggregate = "CASE_LEVEL_SCORED_PASS", False
        elif i < 83:
            state, aggregate = "REJECT_CASE_LEVEL_WITHOUT_SCORES", False
        else:
            state, aggregate = A_STATE, True
        records.append({
            "case_id": f"synthetic-{i}", "target_sha256": digest,
            "review_evidence_state": state,
            "v6_aggregate_complement_only": aggregate,
            "case_level_evidence_present": not aggregate,
            "scores_1_to_5": None, "decision_for_strict_ab_pairing": None,
            "reported_final_decision": "PASS_ONLY" if aggregate else "REJECT",
        })
        b_decision = ("REJECT" if i == 83 else
                      "HOLD" if 84 <= i < 90 else "PASS")
        events.append(make_event("gold192", "BLIND_REVIEW", {
            "case_id": f"rb-{i}", "target_sha256": digest,
            "reviewer_role": "REVIEWER_B",
            "reviewer_source_sha256": CANONICAL_REVIEWER_B_SHA256,
            "decision": b_decision,
            "blind_case_id": f"RB-{i:04}",
            "scores": {"chinese_prose": 4},
            "evidence_summary": "Synthetic B explanation",
            "severe_flags": [],
        }, "t"))
        if i < 79:
            events.append(make_event("gold192", "INCREMENTAL_REVIEW", {
                "case_id": f"ra-{i}", "target_sha256": digest,
                "reviewer_role": "REVIEWER_A", "decision": "PASS_ONLY",
            }, "t"))
        elif i < 83:
            events.append(make_event("gold192", "HISTORICAL_REJECT_EVIDENCE", {
                "case_id": f"ra-{i}", "target_sha256": digest,
                "reviewer_role": "REVIEWER_A", "decision": "REJECT",
            }, "t"))
    normalized = {
        "schema": "r58_gold192_reviewer_a_results_normalized_private_v1",
        "status": "NORMALIZED_192_IDENTITIES__CASE_LEVEL_GAPS_EXPLICIT",
        "reviewer": "A", "quality_v1_admitted": 0,
        "case_level_evidence_counts": {
            "case_level_scored_pass": 79, "pass_aggregate_only_pending": 109,
            "reject_case_level_unscored": 3, "reject_group_only_unscored": 1,
        },
        "records": records,
    }
    return normalized, events


class GapPriorityTests(unittest.TestCase):
    def test_109_aggregate_only_yields_exact_7_priority(self):
        safe, cases = build_a_gap_priority(*fixture())
        self.assertEqual(len(cases), 7)
        self.assertEqual(safe["priority_reviewer_b_decisions"],
                         {"HOLD": 6, "REJECT": 1})
        self.assertEqual(safe["other_aggregate_only_b_pass"], 102)
        self.assertTrue(all(r["reviewer_a_scores_1_to_5"] is None
                            and r["reviewer_a_actual_case_level_decision"] is None
                            and r["status"] == "PENDING_A_EVIDENCE_RECOVERY"
                            for r in cases))
        self.assertEqual(safe["quality_v1_admitted"], 0)
        self.assertNotIn("synthetic-", str(safe))

    def test_missing_b_canonical_target_fails(self):
        a, events = fixture()
        events = [e for e in events if e["payload"].get("target_sha256") != f"{192:064x}"]
        with self.assertRaisesRegex(ManifestError, "A_GAP_CANONICAL_B_SET_MISMATCH"):
            build_a_gap_priority(a, events)

    def test_aggregate_pass_with_score_is_not_accepted(self):
        a, events = fixture()
        a["records"][83]["scores_1_to_5"] = {"chinese_prose": 5}
        with self.assertRaisesRegex(ManifestError, "A_GAP_AGGREGATE_ONLY_STATE_INVALID"):
            build_a_gap_priority(a, events)

    def test_private_writer_refuses_overwrite(self):
        safe, cases = build_a_gap_priority(*fixture())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, private = root / "repo", root / "private"
            repo.mkdir()
            private.mkdir(mode=0o700)
            target = private / "queue.json"
            write_private_queue(target, cases, repo)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_private_queue(target, cases, repo)
            self.assertEqual(safe["priority_case_count"], 7)


if __name__ == "__main__":
    unittest.main()
