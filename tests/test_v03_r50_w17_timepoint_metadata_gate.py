"""Synthetic W17 private full-source timeline checks: no source text or AI."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "w17timepoint", SCRIPTS / "v03_r50_w17_timepoint_metadata_gate.py"
)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def scenario() -> tuple[dict, dict, list[dict], dict]:
    story_id = "SYNTHETIC_W17_STORY_ID"
    messages = [
        {"role": "assistant", "created_at": "2026-08-01T08:00:00+00:00",
         "content": f"SYNTHETIC COMPLETE MESSAGE {i}"}
        for i in range(80)
    ]
    transcript = {"rank": 17, "story_id": story_id, "messages": messages}
    card = {
        "rank": 17, "story_id": story_id,
        "chat_window": {
            "first_message_at": "2026-07-25T11:04:39+00:00",
            "last_message_at": "2026-10-07T13:45:10+00:00",
        },
        "export_time_card": {
            "created_at": "2026-06-19T21:47:30+00:00",
            "updated_at": "2026-06-22T08:46:14+00:00",
            "observed_at": "2026-10-15T03:05:40+00:00",
        },
        "current_author_card": {
            "updated_at": "2026-06-22T08:46:14+00:00",
        },
        "current_public_projection": {
            "observed_at": "2026-10-15T03:35:50+00:00",
        },
        "content_versions": [],
        "moderation_source_snapshots": [],
    }
    dossiers = []
    reviews = []
    for gap in range(7):
        refs = []
        records = []
        for j in range(49 + int(gap == 6)):
            rank = 17 if j % 5 == 0 else (2, 4, 7, 10)[(j-1) % 4]
            source = messages[j]["content"] if rank == 17 else f"old world {rank} {j}"
            records.append({
                "source_rank": rank,
                "original_source_message_index": j,
                "full_source_text": source,
                "original_message_sha256": m.review.sha(source.encode("utf8")),
            })
        # Explicitly point to W17 original message indices 0,5,10.
        # Fill up to user-provided counts 11/10 with old-world references.
        need = 10 if gap in (3, 6) else 11
        refs = [{
            "source_rank": r["source_rank"],
            "source_message_index": r["original_source_message_index"],
        } for r in records[:need]]
        dossiers.append({
            "gap_index": gap,
            "full_original_messages": records,
        })
        reviews.append({"gap_index": gap, "source_refs": refs})
    return card, transcript, dossiers, {"gap_reviews": reviews}


class W17TimepointMetadataTests(unittest.TestCase):
    def test_temporal_last_edit_is_not_card_at_cutoff_certification(self):
        card, transcript, dossiers, review = scenario()
        result = m.audit_w17_timepoint(card, transcript, dossiers, review)
        self.assertEqual(result["total_dossier_message_entries"], 344)
        self.assertEqual(result["full_review_source_citations"], 75)
        self.assertEqual(result["content_version_snapshot_count"], 0)
        self.assertEqual(result["moderation_source_snapshot_count"], 0)
        self.assertTrue(result["export_card_last_edit_precedes_first_chat_message"])
        self.assertEqual(result["w17_citations_earlier_than_export_card_last_edit"], 0)
        self.assertEqual(result["all_historical_card_fields_valid_at_actual_prompt_cutoff"],
                         "NOT_CERTIFIED")
        self.assertEqual(result["semantic_world_graph_gate"], "HOLD")

    def test_original_message_hash_mismatch_hard_fails(self):
        card, transcript, dossiers, review = scenario()
        transcript["messages"][0]["content"] = "TAMPERED"
        with self.assertRaisesRegex(
            ValueError, "W17_DOSSIER_TEXT_NOT_EQUAL_TO_FROZEN_SOURCE"
        ):
            m.audit_w17_timepoint(card, transcript, dossiers, review)

    def test_non_timezone_timestamp_fails_closed(self):
        card, transcript, dossiers, review = scenario()
        transcript["messages"][0]["created_at"] = "2026-08-01 08:00:00"
        with self.assertRaisesRegex(ValueError, "SOURCE_TIMEZONE_REQUIRED"):
            m.audit_w17_timepoint(card, transcript, dossiers, review)

    def test_bad_card_metadata_timestamp_order_fails_closed(self):
        card, transcript, dossiers, review = scenario()
        card["export_time_card"]["observed_at"] = "2026-06-01T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError,
                                    "W17_CARD_METADATA_TIME_INCONSISTENT"):
            m.audit_w17_timepoint(card, transcript, dossiers, review)

    def test_missing_version_history_is_not_filled_or_inferred(self):
        card, transcript, dossiers, review = scenario()
        card["content_versions"] = [{"source_updated_at": "2026-06-20T00:00:00+00:00"}]
        report = m.audit_w17_timepoint(card, transcript, dossiers, review)
        self.assertEqual(report["content_version_snapshot_count"], 1)
        self.assertEqual(report["full_chat_story_arc_and_transitive_alias_graph"], "HOLD")

    def test_message_outside_chat_window_flagged_not_silently_accepted(self):
        card, transcript, dossiers, review = scenario()
        transcript["messages"][0]["created_at"] = "2025-01-01T00:00:00+00:00"
        result = m.audit_w17_timepoint(card, transcript, dossiers, review)
        self.assertGreater(result["w17_citations_outside_reported_chat_window"], 0)
        self.assertEqual(result["semantic_world_graph_gate"], "HOLD")

    def test_wrong_reviewed_message_total_fails(self):
        card, transcript, dossiers, review = scenario()
        dossiers[0]["full_original_messages"].pop()
        with self.assertRaisesRegex(ValueError,
                                    "PRIVATE_COMPLETE_MESSAGE_TOTAL_CHANGED"):
            m.audit_w17_timepoint(card, transcript, dossiers, review)

    def test_story_id_mismatch_fails(self):
        card, transcript, dossiers, review = scenario()
        transcript["story_id"] = "WRONG_SYNTHETIC_ID"
        with self.assertRaisesRegex(ValueError,
                                    "W17_FROZEN_CARD_TRANSCRIPT_ID_MISMATCH"):
            m.audit_w17_timepoint(card, transcript, dossiers, review)


if __name__ == "__main__":
    unittest.main()
