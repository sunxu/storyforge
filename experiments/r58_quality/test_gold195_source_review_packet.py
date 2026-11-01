import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from gold195_source_review_packet import (
    ROOTS, INDEX, assemble, normalize_record, write_private,
)


class SourceReviewPacketTests(unittest.TestCase):
    @staticmethod
    def fixture(root):
        ipath = root / INDEX
        ipath.parent.mkdir(parents=True, exist_ok=True)
        with ipath.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=["candidate_id", "target_sha256", "story_id"])
            writer.writeheader()
            for cohort, relative, count in ROOTS:
                dest = root / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("w", encoding="utf-8") as f:
                    for i in range(count):
                        target = "private-gold-" + str(i)
                        digest = hashlib.sha256(target.encode()).hexdigest()
                        item = {
                            "id": cohort + "-" + str(i),
                            "metadata": {"story_id": "private-world", "target_sha256_utf8": digest},
                            "messages": [
                                {"role": "assistant", "content": "private-opening"},
                                {"role": "user", "content": "private-player"},
                                {"role": "assistant", "content": target},
                            ],
                        }
                        if cohort == "gold108":
                            item["metadata"] = {}
                            writer.writerow({
                                "candidate_id": item["id"], "target_sha256": digest,
                                "story_id": "" if i < 3 else "private-world",
                            })
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def test_realistic_count_only_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            result, packets = assemble(root)
            self.assertEqual(result["counts"]["source_rows_checked"], 195)
            self.assertEqual(result["counts"]["story_uuid_hold"], 3)
            self.assertEqual(result["counts"]["leading_assistant_context_hold"], 195)
            self.assertEqual(result["train_admitted"], 0)
            self.assertFalse(packets)
            self.assertNotIn("private-gold", json.dumps(result))
            self.assertNotIn("private-world", json.dumps(result))

    def test_private_packet_retains_unresolved_lead_and_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            _, packets = assemble(root, collect=True)
            p = packets[0]
            self.assertEqual(p["frozen_messages"][0]["content"], "private-opening")
            self.assertEqual(p["target_assistant_text"], "private-gold-0")
            self.assertEqual(p["current_user_text"], "private-player")
            self.assertIsNone(p["world_component_id"])
            self.assertIsNone(p["split"])
            self.assertEqual(p["system_source"], "UNRESOLVED")
            self.assertIn("LEADING_ASSISTANT_CONTEXT_UNRESOLVED", p["hold_reasons"])

    def test_tampered_hash_rejected(self):
        row = {
            "id": "x", "metadata": {"target_sha256_utf8": "0" * 64, "story_id": "world"},
            "messages": [
                {"role": "user", "content": "u"},
                {"role": "assistant", "content": "gold"},
            ],
        }
        with self.assertRaises(ValueError):
            normalize_record(row, "gold87", {})

    def test_private_output_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            repo.mkdir()
            private = base / "private"
            private.mkdir(mode=0o700)
            target = private / "review.jsonl"
            write_private(target, repo, [{"secret": "private"}])
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                write_private(target, repo, [])

    def test_private_output_under_repo_forbidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with self.assertRaises(ValueError):
                write_private(repo / "bad.jsonl", repo, [])


if __name__ == "__main__":
    unittest.main()
