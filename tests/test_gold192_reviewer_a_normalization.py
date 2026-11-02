"""Synthetic-only normalization tests: no private story text or identifiers."""
from __future__ import annotations

import unittest
from copy import deepcopy

from storyforge_gold_quality.manifest import ManifestError
from storyforge_gold_quality.normalize_reviewer_a import normalize

SCORES = {name: 4 for name in (
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
)}


def synthetic_sources():
    rejected = [
        "xz-gold-t02108", "s06-gold-t03412",
        "s15-gold-r03-t02216", "s06-gold-t03930",
    ]
    ids = rejected + [f"synthetic-{i:03d}" for i in range(188)]
    mapping = [{"original_case_id": case_id, "target_sha256": f"{i + 1:064x}"}
               for i, case_id in enumerate(ids)]
    # First 82 reviewed cases contain exactly three unscored rejects and 79 scored passes.
    reviewed_ids = rejected[1:] + ids[4:83]
    assert len(reviewed_ids) == 82
    reviews = []
    for case_id in reviewed_ids:
        decision = "REJECT" if case_id in rejected else "AI_SEMANTIC_PASS_ONLY"
        reviews.append({
            "case_id": case_id, "cohort": "gold87",
            "decision": decision,
            "scores_1_to_5": None if decision == "REJECT" else dict(SCORES),
            "note": "仅用于合成测试",
        })
    sources = {
        "initial": {"cases": reviews[:31]},
        "remaining": {"cases": reviews[31:]},
        "mapping": {"mapping": mapping},
        "supplement": {"reject_groups": [{"case_ids": [x]} for x in rejected]},
        "safe": {"ai_review_counts": {"semantic_pass_only": 188, "hold": 0,
                                      "reject": 4, "semantic_review_pending": 0}},
    }
    return sources, {m["target_sha256"] for m in mapping}


class NormalizeReviewerATests(unittest.TestCase):
    def test_complete_identity_index_not_fake_scores(self):
        sources, hashes = synthetic_sources()
        report, counts = normalize(sources, hashes)
        self.assertEqual(len(report["records"]), 192)
        self.assertEqual(dict(counts), {
            "case_level_scored_pass": 79,
            "reject_case_level_unscored": 3,
            "reject_group_only_unscored": 1,
            "pass_aggregate_only_pending": 109,
        })
        self.assertEqual(sum(r["decision_for_strict_ab_pairing"] == "PASS_ONLY"
                             for r in report["records"]), 79)
        self.assertEqual(sum(r["scores_1_to_5"] is None for r in report["records"]), 113)
        self.assertEqual(sum(r["v6_aggregate_complement_only"]
                             for r in report["records"]), 109)
        self.assertEqual(report["quality_v1_admitted"], 0)

    def test_target_set_mismatch_fails_closed(self):
        sources, hashes = synthetic_sources()
        with self.assertRaisesRegex(ManifestError, "TARGET_SET_MISMATCH"):
            normalize(sources, hashes - {min(hashes)})

    def test_duplicate_case_id_fails_closed(self):
        sources, hashes = synthetic_sources()
        bad = deepcopy(sources)
        bad["remaining"]["cases"][0]["case_id"] = bad["initial"]["cases"][0]["case_id"]
        with self.assertRaisesRegex(ManifestError, "DUPLICATE"):
            normalize(bad, hashes)

    def test_unscored_pass_cannot_be_promoted(self):
        sources, hashes = synthetic_sources()
        bad = deepcopy(sources)
        bad["initial"]["cases"][3]["scores_1_to_5"] = None
        with self.assertRaisesRegex(ManifestError, "SCORED_PASS_INVALID"):
            normalize(bad, hashes)


if __name__ == "__main__":
    unittest.main()
