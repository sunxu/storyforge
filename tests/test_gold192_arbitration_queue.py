"""Synthetic tests for private-only arbitration queue."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storyforge_gold_quality.arbitration_queue import (
    build_disagreements,
    write_private_queue,
)
from storyforge_gold_quality.manifest import ManifestError, make_event
from storyforge_gold_quality.reconcile import CANONICAL_REVIEWER_B_SHA256

SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def fixture():
    items = []
    for i in range(192):
        digest = f"{i + 1:064x}"
        b_decision = ("HOLD" if 72 <= i < 78 else
                      "REJECT" if i in (78, 110) else "PASS")
        b_payload = {
            "case_id": "b-" + digest,
            "target_sha256": digest,
            "reviewer_role": "REVIEWER_B",
            "reviewer_source_sha256": CANONICAL_REVIEWER_B_SHA256,
            "decision": b_decision,
            "scores": SCORES,
            "blind_case_id": f"RB-{i + 1:04d}",
            "evidence_summary": "SYNTHETIC_B_PRIVATE_SUMMARY",
        }
        items.append(make_event("gold192", "BLIND_REVIEW", b_payload, "t"))
        if i < 79:
            a_payload = {
                "case_id": "a-" + digest,
                "target_sha256": digest,
                "reviewer_role": "REVIEWER_A",
                "decision": "PASS_ONLY",
                "scores": SCORES,
                "evidence_summary": "SYNTHETIC_A_PRIVATE_SUMMARY",
            }
            items.append(make_event("gold192", "INCREMENTAL_REVIEW", a_payload, "t"))
        elif 79 <= i < 83:
            hist = {
                "case_id": "a-" + digest,
                "target_sha256": digest,
                "reviewer_role": "REVIEWER_A",
                "reviewer_source": "r58_reviewer_a_recovered_v6_20261102",
                "decision": "REJECT",
                "score_state": "UNAVAILABLE_NOT_SYNTHESIZED",
                "evidence_tier": "FINAL_V6_REJECT_GROUP_ONLY",
            }
            items.append(make_event(
                "gold192", "HISTORICAL_REJECT_EVIDENCE", hist, "t"))
    return items


class ArbitrationQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)

    def test_exact_11_private_queue_and_safe_counts(self):
        safe, cases = build_disagreements(fixture())
        self.assertEqual(safe["disagreement_count"], 11)
        self.assertEqual(safe["disagreement_types"], {
            "A_HISTORICAL_REJECT_B_PASS": 4,
            "A_PASS_B_HOLD": 6,
            "A_PASS_B_REJECT": 1,
        })
        self.assertEqual(len({c["target_sha256"] for c in cases}), 11)
        self.assertTrue(all(c["status"] == "PENDING_OWNER_ARBITRATION"
                            and c["decision"] is None for c in cases))
        self.assertEqual(sum(c["reviewer_a"]["scores_missing"] for c in cases), 4)
        self.assertNotIn("SYNTHETIC_B_PRIVATE_SUMMARY", json.dumps(safe))
        self.assertNotIn("target_sha256", json.dumps(safe))
        self.assertEqual(safe["quality_v1_admitted"], 0)

    def test_private_output_no_overwrite_and_not_in_repo(self):
        _, cases = build_disagreements(fixture())
        dest = self.private / "queue.json"
        write_private_queue(dest, cases, self.repo)
        loaded = json.loads(dest.read_text(encoding="utf-8"))
        self.assertEqual(loaded["case_count"], 11)
        self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            write_private_queue(dest, cases, self.repo)
        with self.assertRaisesRegex(ManifestError, "ARBITRATION_OUTPUT_INSIDE_REPOSITORY"):
            write_private_queue(self.repo / "queue.json", cases, self.repo)

    def test_missing_or_duplicate_reviewer_b_fails_closed(self):
        rows = fixture()
        rows.pop(0)
        with self.assertRaisesRegex(ManifestError, "ARBITRATION_REVIEW_ROUNDS_AMBIGUOUS"):
            build_disagreements(rows)
        rows = fixture()
        rows.append(rows[0])
        with self.assertRaisesRegex(ManifestError, "DUPLICATE_EVENT_ID"):
            build_disagreements(rows)


if __name__ == "__main__":
    unittest.main()
