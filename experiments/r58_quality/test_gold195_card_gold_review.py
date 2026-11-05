import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gold195_card_gold_review import build, verified_cards, write_private
from gold195_card_snapshot_candidates import card_utf8


class CardGoldReviewTests(unittest.TestCase):
    def card(self):
        body = {"characters": [{"name": "PRIVATE_NAME"}], "world": "PRIVATE_SECRET"}
        return {
            "story_uuid": "private-world",
            "snapshot_card_json": body,
            "card_sha256": hashlib.sha256(card_utf8(body)).hexdigest(),
            "snapshot_version": "source-v1",
            "source_archive": "early_raw_backup",
            "source_kind": "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST",
            "review_status": "NOT_APPROVED_FOR_SYSTEM",
        }

    def record(self, leading=False):
        h = [{"role": "user", "content": "historic private"}]
        if leading:
            h = [{"role": "assistant", "content": "orphan"}]
        h += [{"role": "user", "content": "current private"},
              {"role": "assistant", "content": "gold private"}]
        return {
            "case_id": "secret-case", "corpus": "gold87", "story_uuid": "private-world",
            "target_sha256": "a" * 64, "source_record_sha256": "b" * 64,
            "frozen_messages": h, "current_user_text": "current private",
            "target_assistant_text": "gold private",
        }

    def test_private_review_bound_but_not_trained(self):
        rows = [self.record(), self.record(leading=True)]
        with patch("gold195_card_gold_review.assemble",
                   return_value=({"counts": {"source_rows_checked": 195}}, rows)):
            receipt, packets = build(Path("."), {"private-world": self.card()}, True)
        self.assertEqual(receipt["counts"]["card_hash_bound"], 2)
        self.assertEqual(receipt["counts"]["leading_assistant_context_requires_review"], 1)
        self.assertEqual(receipt["quality_v1_admitted"], 0)
        self.assertEqual(packets[0]["card_snapshot"], self.card()["snapshot_card_json"])
        self.assertIsNone(packets[0]["candidate_messages"])
        self.assertIsNone(packets[0]["split"])
        self.assertFalse(packets[1]["quality_v1_admitted"])
        self.assertNotIn("PRIVATE_SECRET", json.dumps(receipt))
        self.assertNotIn("secret-case", json.dumps(receipt))

    def test_hash_tamper_rejects_private_card(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "cards.json"
            entry = self.card()
            entry["snapshot_card_json"]["world"] = "changed"
            p.write_text(json.dumps({
                "schema": "r58_gold195_card_snapshot_candidates_private_v1",
                "status": "CANDIDATE_ONLY_NOT_APPROVED",
                "cards": [entry],
            }))
            p.chmod(0o600)
            with self.assertRaises(ValueError):
                verified_cards(p)

    def test_private_path_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            home = Path(t)
            root = home / "repo"
            root.mkdir()
            private = home / "private"
            private.mkdir(mode=0o700)
            target = private / "review.jsonl"
            write_private(target, root, [{"secret": "PRIVATE_SECRET"}])
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                write_private(target, root, [])


if __name__ == "__main__":
    unittest.main()
