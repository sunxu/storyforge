"""Synthetic tests for private Gold108 source-context review packets."""
import hashlib
import io
import json
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import v03_r51_prepare_private_review_packets as packets
import v03_r51_gold195_source_replay as replay
import v03_r51_gold195_private_triage as triage


def digest(t):
    return hashlib.sha256(t.encode()).hexdigest()


def source_zip(raw):
    io_out = io.BytesIO()
    with zipfile.ZipFile(io_out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("story.jsonl", raw)
    return io_out.getvalue()


class ContextPacketTests(unittest.TestCase):
    def fixture(self):
        source = [
            {"id": "u-prior", "role": "user", "content": "private before",
             "turn_index": 0},
            {"id": "a-prior", "role": "assistant", "content": "private context",
             "turn_index": 1},
            {"id": "u-now", "role": "user", "content": "private current",
             "turn_index": 2},
            {"id": "a-target", "role": "assistant", "content": "private target",
             "turn_index": 3},
        ]
        raw = (json.dumps({"messages": source}, ensure_ascii=False) + "\n").encode()
        zipped = source_zip(raw)
        row = {
            "candidate_id": "synthetic",
            "cohort": 108,
            "source_rank": 6,
            "source_story_id": "synthetic-world",
            "original_target_message_id": "a-target",
            "original_target_sha256": digest("private target"),
            "history_fingerprints": [
                {"role": "user", "sha256": digest("private current")}],
            "source_reference": {},
            "holds": ["CONTENT_OR_RIGHTS_HOLD",
                      "SOURCE_POINTER_RECONCILIATION_HOLD"],
            "source_review": {
                "raw_source_receipt": {
                    "original_root_messages_array_index": 3,
                    "raw_zip_sha256": replay.sha256(zipped),
                    "source_jsonl_sha256": replay.sha256(raw),
                }
            },
        }
        gold = {
            "id": "synthetic",
            "messages": [
                {"role": "user", "content": "private current"},
                {"role": "assistant", "content": "private target"},
            ],
        }
        return source, row, gold, raw, zipped

    def test_packet_uses_exact_source_window_and_labeled_prior(self):
        source, row, gold, raw, zipped = self.fixture()
        pkt = packets.verified_review_packet(
            row, gold, source, replay.sha256(raw), replay.sha256(zipped))
        self.assertEqual(len(pkt["frozen_visible_history"]), 1)
        self.assertEqual(len(
            pkt["preceding_source_preview_NOT_PART_OF_FROZEN_INPUT"]), 2)
        self.assertEqual(pkt["frozen_visible_history"][0]["content"],
                         "private current")
        self.assertEqual(pkt["target_content_for_review_only"], "private target")
        self.assertEqual(pkt["context_only_route"],
                         "UNDECIDED__SOURCE_REVIEW_REQUIRED")
        self.assertEqual(pkt["training_admission"], "PENDING_NOT_APPROVED")

    def test_original_history_mutation_holds(self):
        source, row, gold, raw, zipped = self.fixture()
        source[2]["content"] = "different data"
        with self.assertRaisesRegex(ValueError,
                                    "VISIBLE_HISTORY_ROLE_OR_BODY_MISMATCH"):
            packets.verified_review_packet(
                row, gold, source, replay.sha256(raw), replay.sha256(zipped))

    def test_prior_context_is_not_silently_added_to_training_input(self):
        source, row, gold, raw, zipped = self.fixture()
        pkt = packets.verified_review_packet(
            row, gold, source, replay.sha256(raw), replay.sha256(zipped))
        self.assertNotEqual(pkt["frozen_visible_history"],
                            pkt["preceding_source_preview_NOT_PART_OF_FROZEN_INPUT"])
        self.assertFalse(pkt["historical_card_version_verified"])
        self.assertFalse(pkt["rights_or_license_certified"])
        self.assertEqual(pkt["reviewer_1"]["decision"], "PENDING")

    def test_summary_counts_only_and_private_write(self):
        source, row, gold, raw, zipped = self.fixture()
        pool = [dict(row, candidate_id=f"synthetic-{i}") for i in range(108)]
        golds = [dict(gold, id=f"synthetic-{i}") for i in range(108)]
        with patch.object(packets.base, "read_pinned_rows", return_value=golds):
            with patch.object(packets.replay, "choose_source_jsonl",
                              return_value=raw):
                output, summary = packets.prepare(
                    Path("."), pool, {6: zipped})
        self.assertEqual(len(output), 108)
        self.assertEqual(summary["packets_created"], 108)
        self.assertEqual(summary["starts_with_user"], 108)
        self.assertEqual(summary["train_admitted"], 0)
        self.assertNotIn("private target", json.dumps(summary))
        self.assertNotIn("synthetic-1", json.dumps(summary))
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "protected"
            parent.mkdir(mode=0o700)
            dest = parent / "review.jsonl"
            triage.write_private(dest, output, Path(temp) / "gitrepo")
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o600)
            self.assertEqual(len(dest.read_text().splitlines()), 108)
            with self.assertRaises(FileExistsError):
                triage.write_private(dest, output, Path(temp) / "gitrepo")


if __name__ == "__main__":
    unittest.main()
