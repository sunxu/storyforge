"""Synthetic-only regression tests; no private StoryForge source is committed."""
from __future__ import annotations

import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from storyforge_gold_quality import recover_reviewer_a as module
from storyforge_gold_quality.manifest import append_events, load_events, make_event
from storyforge_gold_quality.reconcile import reconcile_gold192

SCORES = {name: 4 for name in (
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
)}


class ReviewerARecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.bundle = root / "private"
        self.bundle.mkdir(mode=0o700)
        self.manifest = self.bundle / "events.jsonl"
        all_ids = [f"case-{i:03}" for i in range(192)]
        rejects = sorted(module.EXPECTED_REJECT_IDS)
        all_ids[:4] = rejects
        mapping = [{"original_case_id": case,
                    "blind_case_id": f"RB-{i:04}",
                    "target_sha256": f"{i + 1:064x}"}
                   for i, case in enumerate(all_ids)]
        all_rows = [
            {"case_id": case, "decision": "REJECT" if case in rejects[:3] else
             "AI_SEMANTIC_PASS_ONLY",
             "scores_1_to_5": None if case in rejects[:3] else SCORES,
             "note": "Synthetic case-level evidence"}
            for case in all_ids[:82]
        ]
        # Three unscored rejects in the recovered 82 and the fourth outside.
        all_rows = [r for r in all_rows if r["case_id"] != rejects[3]]
        all_rows.append({"case_id": all_ids[82], "decision": "AI_SEMANTIC_PASS_ONLY",
                         "scores_1_to_5": SCORES, "note": "Synthetic case"})
        self.assertEqual(len(all_rows), 82)
        self.assertEqual(sum(r["decision"] == "REJECT" for r in all_rows), 3)
        docs = {
            "initial": {"cases": all_rows[:31]},
            "remaining": {"cases": all_rows[31:]},
            "supplement": {"reject_groups": [
                {"case_ids": [case]} for case in rejects]},
            "mapping": {"mapping": mapping},
            "safe": {"ai_review_counts": {
                "semantic_pass_only": 188, "hold": 0, "reject": 4,
                "semantic_review_pending": 0}},
        }
        self.pins = {}
        for key, (relative, _) in module.FILES.items():
            raw = json.dumps(docs[key]).encode()
            path = self.bundle / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.pins[key] = (relative, hashlib.sha256(raw).hexdigest())
        events = [make_event("gold192", "BLIND_REVIEW", {
            "case_id": "reviewer-b:" + row["target_sha256"],
            "target_sha256": row["target_sha256"],
            "reviewer_role": "REVIEWER_B",
            "reviewer_source_sha256": module.__dict__.get(
                "CANONICAL_B_SHA", "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"),
            "decision": "PASS",
            "scores": SCORES,
        }, "2026-11-02T00:00:00Z") for row in mapping]
        append_events(self.manifest, events, self.repo)
        self.args = types.SimpleNamespace(
            bundle_root=self.bundle, manifest=self.manifest, repo_root=self.repo)

    def test_exact_scored_recovery_and_idempotency(self):
        with patch.object(module, "FILES", self.pins):
            result = module.recover_reviewer_a(self.args)
            again = module.recover_reviewer_a(self.args)
        self.assertEqual(result["scored_pass_cases_imported"], 79)
        self.assertEqual(result["events_appended"], 79)
        self.assertEqual(again["events_appended"], 0)
        report = reconcile_gold192(load_events(self.manifest))
        self.assertEqual(report["counts"]["paired_case_count"], 79)
        self.assertEqual(report["counts"]["missing_reviewer_a"], 113)
        self.assertEqual(report["quality_v1_admitted"], 0)

    def test_recovery_rejects_tampered_private_file(self):
        with patch.object(module, "FILES", self.pins):
            path = self.bundle / self.pins["initial"][0]
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "REVIEWER_A_SOURCE_PIN_MISMATCH"):
                module.recover_reviewer_a(self.args)
        self.assertEqual(len(load_events(self.manifest)), 192)

    def test_b_target_set_mismatch_fails_closed(self):
        events = load_events(self.manifest)
        events[0]["payload"]["target_sha256"] = "f" * 64
        self.manifest.write_text("".join(json.dumps(e) + "\n" for e in events),
                                 encoding="utf-8")
        with (patch.object(module, "FILES", self.pins),
              self.assertRaisesRegex(ValueError, "REVIEWER_A_B_TARGET_SET_MISMATCH")):
            module.recover_reviewer_a(self.args)


if __name__ == "__main__":
    unittest.main()
