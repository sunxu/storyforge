"""Synthetic tests for the SHA-pinned canonical Reviewer B importer."""
from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile
import types
import unittest
import unittest.mock

from storyforge_gold_quality.cli import import_reviewer_b
from storyforge_gold_quality.manifest import load_events


SCORES = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 4,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}


def source_bytes():
    rows = []
    for i in range(192):
        decision = "PASS" if i < 178 else "HOLD" if i < 190 else "REJECT"
        rows.append({
            "blind_case_id": f"RB-{i + 1:04d}",
            "target_sha256": f"{i + 1:064x}",
            "scores_1_to_5": SCORES,
            "decision": decision,
            "severe_flags": ["synthetic_flag"] if decision == "REJECT" else [],
            "evidence_summary": "synthetic-only fixture",
        })
    value = {
        "schema": "r58_gold192_reviewer_b_results_v1",
        "reviewer": "B",
        "status": "REVIEW_COMPLETE",
        "counts": {"PASS": 178, "HOLD": 12, "REJECT": 2},
        "cases": rows,
    }
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class ReviewerBImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.temp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.private = root / "private"
        self.private.mkdir(mode=0o700)
        self.source = self.private / "reviewer_b.json"
        self.manifest = self.private / "events.jsonl"
        self.raw = source_bytes()
        self.source.write_bytes(self.raw)
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.args = types.SimpleNamespace(
            input=self.source, manifest=self.manifest, repo_root=self.repo,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_imports_exactly_192_and_is_idempotent(self):
        with unittest.mock.patch("storyforge_gold_quality.cli.REVIEWER_B_CANONICAL_SHA256", self.digest):
            result = import_reviewer_b(self.args)
            again = import_reviewer_b(self.args)
        self.assertEqual(result["events_appended"], 192)
        self.assertEqual(result["decision_counts"], {"PASS": 178, "HOLD": 12, "REJECT": 2})
        self.assertEqual(again["status"], "CANONICAL_SOURCE_ALREADY_IMPORTED")
        self.assertEqual(len(load_events(self.manifest)), 192)
        self.assertFalse(result["private_values_emitted"])

    def test_source_pin_mismatch_fails_closed(self):
        with (
            unittest.mock.patch("storyforge_gold_quality.cli.REVIEWER_B_CANONICAL_SHA256", "0" * 64),
            self.assertRaisesRegex(ValueError, "REVIEWER_B_SOURCE_PIN_MISMATCH"),
        ):
            import_reviewer_b(self.args)

    def test_private_evidence_not_in_safe_import_receipt(self):
        with unittest.mock.patch("storyforge_gold_quality.cli.REVIEWER_B_CANONICAL_SHA256", self.digest):
            result = import_reviewer_b(self.args)
        rendered = json.dumps(result)
        self.assertNotIn("synthetic-only fixture", rendered)
        self.assertNotIn("RB-0001", rendered)
        self.assertNotIn("target_sha256", rendered)


if __name__ == "__main__":
    unittest.main()
