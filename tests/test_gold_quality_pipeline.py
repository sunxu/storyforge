from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from storyforge_gold_quality.cli import (  # noqa: E402
    append_exclusion, append_review, import_exposure, import_history,
)
from storyforge_gold_quality.manifest import (  # noqa: E402
    ManifestError, append_events, load_events, make_event, safe_report,
)


class GoldQualityPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.manifest = self.private / "manifest.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_only_preserves_two_reviewers_and_target_pin(self):
        a = make_event("gold192", "INCREMENTAL_REVIEW",
                       {"case_id":"c1", "target_sha256":"a"*64, "decision":"REJECT"}, "t1")
        b = make_event("gold192", "BLIND_REVIEW",
                       {"case_id":"c1", "target_sha256":"a"*64, "decision":"PASS"}, "t2")
        append_events(self.manifest, [a], self.repo)
        append_events(self.manifest, [b], self.repo)
        self.assertEqual(len(load_events(self.manifest)), 2)

    def test_changed_target_is_rejected(self):
        a = make_event("gold192", "INCREMENTAL_REVIEW",
                       {"case_id":"c1", "target_sha256":"a"*64}, "t1")
        b = make_event("gold192", "BLIND_REVIEW",
                       {"case_id":"c1", "target_sha256":"b"*64}, "t2")
        append_events(self.manifest, [a], self.repo)
        with self.assertRaisesRegex(ManifestError, "CASE_TARGET_HASH_CHANGED"):
            append_events(self.manifest, [b], self.repo)

    def test_private_manifest_cannot_be_written_inside_checkout(self):
        event = make_event("gold87", "SOURCE_METADATA", {"row_count":87}, "t")
        with self.assertRaisesRegex(ManifestError, "OUTSIDE_REPOSITORY"):
            append_events(self.repo / "manifest.jsonl", [event], self.repo)

    def test_safe_report_does_not_leak_case_uuid_hash_or_text(self):
        event = make_event("gold192", "INCREMENTAL_REVIEW",
                           {"case_id":"SECRET_CASE", "target_sha256":"c"*64,
                            "story_uuid":"SECRET_UUID", "evidence_summary":"SECRET_TEXT",
                            "decision":"REJECT"}, "t")
        append_events(self.manifest, [event], self.repo)
        rendered = json.dumps(safe_report(load_events(self.manifest)))
        for value in ("SECRET_CASE", "SECRET_UUID", "SECRET_TEXT", "c"*64):
            self.assertNotIn(value, rendered)

    def test_gold87_keeps_batch_selection_separate_from_row_metadata(self):
        from argparse import Namespace
        rows = [{"scope":"BATCH", "event_type":"LEGACY_SELECTION_EVIDENCE", "case_count":87,
                 "binding_granularity":"BATCH_LEVEL", "selection_outcome":"DUAL_ACCEPT_RECORDED",
                 "reviewer_independence_proven":False}]
        for i in range(87):
            rows.append({"scope":"CASE", "event_type":"SOURCE_METADATA", "case_id":f"c{i}",
                         "target_sha256":f"{i+1:064x}", "independent_gold_review":"NOT_RUN",
                         "scores_are_subjective_single_review":True})
        source = self.private / "gold87.jsonl"
        source.write_text("".join(json.dumps(x)+"\n" for x in rows), encoding="utf-8")
        with patch("storyforge_gold_quality.cli.verify_source", return_value={"all_sources_pass": True}):
            result = import_history(Namespace(batch="gold87", input=source, manifest=self.manifest,
                                              repo_root=self.repo))
        self.assertEqual(result["unique_cases_imported"], 87)
        events = load_events(self.manifest)
        self.assertEqual(sum(x["event_type"] == "SOURCE_METADATA" for x in events), 87)
        self.assertEqual(sum(x["event_type"] == "LEGACY_SELECTION_EVIDENCE" for x in events), 1)

    def test_gold108_requires_case_bindings_and_batch_receipt(self):
        from argparse import Namespace
        rows = [{"scope":"BATCH", "event_type":"LEGACY_REVIEW", "case_count":108,
                 "binding_granularity":"BATCH_LEVEL",
                 "binding_status":"HISTORICAL_DUAL_REVIEW_INDEX_BINDING_ONLY__NO_QUALITY_V1_ADMISSION",
                 "reviewer_independence_proven":False, "old_review_dimensions":5}]
        for i in range(108):
            rows.append({"scope":"CASE", "event_type":"LEGACY_REVIEW", "case_id":f"g{i}",
                         "target_sha256":f"{i+1:064x}", "rubric":"FIVE_DIMENSION_LEGACY",
                         "new_quality_v1":False, "reviewer1_decision":"ACCEPT",
                         "reviewer2_decision":"ACCEPT"})
        source = self.private / "gold108.jsonl"
        source.write_text("".join(json.dumps(x)+"\n" for x in rows), encoding="utf-8")
        with patch("storyforge_gold_quality.cli.verify_source", return_value={"all_sources_pass": True}):
            result = import_history(Namespace(batch="gold108", input=source, manifest=self.manifest,
                                              repo_root=self.repo))
        self.assertEqual(result["unique_cases_imported"], 108)

    def test_safe_exposure_aggregate_does_not_create_fake_case_rows(self):
        from argparse import Namespace
        source = self.private / "exposure.json"
        source.write_text(json.dumps({"schema":"r57-safe", "gold_totals":{"ever_train":66}}))
        result = import_exposure(Namespace(kind="safe-aggregate", input=source, batch="gold195",
                                           manifest=self.manifest, repo_root=self.repo))
        self.assertEqual(result["case_level_rows_imported"], 0)
        self.assertEqual(result["case_level_state"], "UNKNOWN_NOT_IMPORTED")

    def test_gold192_exclusions_are_three_append_only_events(self):
        from argparse import Namespace
        source = self.private / "exclusions.jsonl"
        rows = [{"case_id":f"x{i}", "target_sha256":f"{i+1:064x}",
                 "reason_code":"WORLD_IDENTITY_UNRESOLVED"} for i in range(3)]
        source.write_text("".join(json.dumps(x)+"\n" for x in rows))
        result = append_exclusion(Namespace(batch="gold192", input=source, manifest=self.manifest,
                                            repo_root=self.repo))
        self.assertEqual(result["exclusion_events_appended"], 3)

    def test_review_requires_six_dimensions(self):
        from argparse import Namespace
        scores = {k:4 for k in ("chinese_prose","character_consistency","npc_initiative",
                                "player_agency","narrative_continuity","rule_fidelity")}
        row = {"case_id":"c", "target_sha256":"d"*64, "reviewer_role":"REVIEWER_A",
               "decision":"REJECT", "scores":scores}
        source = self.private / "review.jsonl"
        source.write_text(json.dumps(row)+"\n")
        result = append_review(Namespace(input=source, batch="gold192", manifest=self.manifest,
                                         repo_root=self.repo, event_type="INCREMENTAL_REVIEW"))
        self.assertEqual(result["events_appended"], 1)


if __name__ == "__main__":
    unittest.main()
