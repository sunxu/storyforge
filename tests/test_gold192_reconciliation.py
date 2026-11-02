"""Synthetic Gold192 disagreement and privacy regression tests."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storyforge_gold_quality.manifest import (
    ManifestError,
    append_events,
    load_events,
    make_event,
)
from storyforge_gold_quality.reconcile import reconcile_gold192

SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def review(case, role, decision, kind="BLIND_REVIEW", digest=None):
    return make_event("gold192", kind, {
        "case_id": case,
        "target_sha256": digest or "a" * 64,
        "reviewer_role": role,
        "decision": decision,
        "scores": SCORES,
    }, "2026-11-02T00:00:00Z")


class ReconcileGold192Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.private = root / "private"
        self.private.mkdir(mode=0o700)
        self.manifest = self.private / "events.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def test_a_reject_b_pass_preserved_no_admission(self):
        append_events(self.manifest, [
            review("PRIVATE_CASE", "REVIEWER_A", "REJECT"),
            review("PRIVATE_CASE", "REVIEWER_B", "PASS"),
        ], self.repo)
        result = reconcile_gold192(load_events(self.manifest))
        self.assertEqual(result["counts"]["reviewer_a_reject_b_pass_disagreement"], 1)
        self.assertEqual(result["counts"]["any_reject_hold_for_arbitration"], 1)
        self.assertEqual(result["quality_v1_admitted"], 0)
        rendered = json.dumps(result)
        self.assertNotIn("PRIVATE_CASE", rendered)
        self.assertNotIn("a" * 64, rendered)

    def test_two_passes_do_not_admit(self):
        events = [
            review("c1", "REVIEWER_A", "PASS_ONLY"),
            review("c1", "REVIEWER_B", "PASS"),
        ]
        result = reconcile_gold192(events)
        self.assertEqual(result["counts"]["declared_both_pass_not_admitted"], 1)
        self.assertFalse(result["reviewer_independence_verified"])

    def test_duplicate_review_round_never_selects_a_winner(self):
        events = [
            review("c1", "REVIEWER_A", "REJECT"),
            review("c1", "REVIEWER_A", "PASS"),
            review("c1", "REVIEWER_B", "PASS"),
        ]
        result = reconcile_gold192(events)
        self.assertEqual(result["counts"]["multiple_review_rounds_need_binding"], 1)
        self.assertEqual(result["counts"]["any_reject_hold_for_arbitration"], 1)
        self.assertNotIn("declared_both_pass_not_admitted", result["counts"])

    def test_three_excluded_remain_separate_from_192(self):
        events = []
        for i in range(192):
            events.append(review(f"case-{i}", "REVIEWER_A", "PASS",
                                 digest=f"{i + 1:064x}"))
        for i in range(3):
            events.append(make_event("gold192", "EXCLUSION", {
                "case_id": f"excluded-{i}", "target_sha256": f"{193 + i:064x}",
                "reason_code": "WORLD_IDENTITY_UNRESOLVED",
            }, "t"))
        result = reconcile_gold192(events)
        self.assertEqual(result["nonexcluded_cases_observed"], 192)
        self.assertEqual(result["counts"]["excluded_world_identity_hold"], 3)
        self.assertEqual(result["coverage_unknown_or_missing"], 0)
        self.assertEqual(result["counts"]["missing_reviewer_b"], 192)

    def test_bad_exclusion_reason_is_hold(self):
        event = make_event("gold192", "EXCLUSION", {
            "case_id": "c1", "target_sha256": "b" * 64,
            "reason_code": "PRIVATE_REASON",
        }, "t")
        with self.assertRaisesRegex(ManifestError, "EXCLUSION_INVALID"):
            reconcile_gold192([event])

    def test_adjudication_does_not_erase_prior_reject(self):
        events = [
            review("c1", "REVIEWER_A", "REJECT"),
            review("c1", "REVIEWER_B", "PASS"),
            review("c1", "OWNER_ARBITER", "PASS", kind="ADJUDICATION"),
        ]
        result = reconcile_gold192(events)
        self.assertEqual(result["counts"]["owner_arbitration_events_present"], 1)
        self.assertEqual(result["counts"]["any_reject_hold_for_arbitration"], 1)
        self.assertEqual(result["quality_v1_admitted"], 0)

    def test_changed_target_fails_closed(self):
        events = [
            review("c1", "REVIEWER_A", "PASS", digest="a" * 64),
            review("c1", "REVIEWER_B", "PASS", digest="b" * 64),
        ]
        with self.assertRaisesRegex(ManifestError, "CASE_TARGET_HASH_CHANGED"):
            reconcile_gold192(events)

    def test_more_than_192_nonexcluded_rejected(self):
        events = [
            review(f"case-{i}", "REVIEWER_A", "PASS", digest=f"{i + 1:064x}")
            for i in range(193)
        ]
        with self.assertRaisesRegex(ManifestError, "SCOPE_COUNTS_EXCEED_EXPECTED"):
            reconcile_gold192(events)

    def test_unknown_role_rejected(self):
        with self.assertRaisesRegex(ManifestError, "REVIEW_INVALID"):
            reconcile_gold192([review("c1", "PRIVATE_ROLE", "PASS")])


if __name__ == "__main__":
    unittest.main()
