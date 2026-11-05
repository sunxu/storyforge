"""Synthetic, database-free tests for the Gold192 history adapter."""
import hashlib
import unittest

from experiments.r58_quality import r59_gold192_history_recovery as adapter


class Gold192HistoryAdapterTests(unittest.TestCase):
    def test_source_receipt_requires_exact_locator_bytes(self):
        raw = b'{"case_id":"safe-only"}\n'
        safe = {
            "schema": "r59_gold192_supabase_extract_safe_v1",
            "status": "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED",
            "gold192": 192,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "private_values_emitted": False,
            "artifacts": {
                "R59_SOURCE_LOCATORS_192.jsonl": {
                    "records": 192, "sha256": hashlib.sha256(raw).hexdigest()
                }
            },
        }
        adapter.validate_source_receipt(safe, raw)
        with self.assertRaisesRegex(ValueError, "SOURCE_LOCATOR_PIN_MISMATCH"):
            adapter.validate_source_receipt(safe, raw + b"\n")

    def test_source_receipt_rejects_admission_or_training(self):
        safe = {
            "schema": "r59_gold192_supabase_extract_safe_v1",
            "status": "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED",
            "gold192": 192, "quality_v1_admitted": 1,
            "training_authorized": False, "gpu_started": False,
            "private_values_emitted": False,
            "artifacts": {},
        }
        with self.assertRaisesRegex(ValueError, "SOURCE_SAFE_RECEIPT_INVALID"):
            adapter.validate_source_receipt(safe, b"x")

    def test_story_level_source_packets_expand_to_192_cases(self):
        packets = []
        remaining = 192
        for story_index in range(13):
            count = min(15, remaining)
            if story_index == 12:
                count = remaining
            cases = []
            for turn in range(1, count + 1):
                target = f"synthetic target {story_index}-{turn}"
                cases.append({
                    "case_id": f"story-{story_index}-t{turn:05d}",
                    "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
                    "target_assistant_text": target,
                })
            packets.append({
                "story_uuid": f"story-{story_index}",
                "cases": cases,
            })
            remaining -= count
        self.assertEqual(sum(len(packet["cases"]) for packet in packets), 192)
        indexed = adapter.index_source_packets(packets)
        self.assertEqual(len(indexed), 192)
        self.assertEqual(len({row["target_sha256"] for row in indexed.values()}), 192)
        with self.assertRaisesRegex(ValueError, "SOURCE_PACKET_STORY_COUNT_INVALID"):
            adapter.index_source_packets(packets[:-1])

    def test_locator_index_requires_complete_exact_identity_set(self):
        packets = {
            "case-a": {
                "case_id": "case-a", "target_sha256": "a" * 64,
                "story_id": "story-a", "turn_index": 12,
            }
        }
        row = {
            "case_id": "case-a", "target_sha256": "a" * 64,
            "story_id": "story-a", "turn_index": 12,
            "source_status": "EXACT_MATCH",
            "message_id": "message-a", "session_id": "session-a",
        }
        self.assertEqual(
            adapter.validate_locators([row], packets)["case-a"]["session_id"],
            "session-a",
        )
        bad = dict(row, target_sha256="b" * 64)
        with self.assertRaisesRegex(ValueError, "SOURCE_LOCATOR_IDENTITY_INVALID"):
            adapter.validate_locators([bad], packets)

    def test_root_fallback_with_multiple_exact_matches_is_held(self):
        priority = [{
            "case_id": "case-a", "story_id": "story-a",
            "turn_index": 12, "target_sha256": "a" * 64,
        }]
        locator = {
            "case_id": "case-a", "source_status": "EXACT_MATCH",
            "matched_message_count": 2, "message_id": "message-root",
            "session_id": "root-session",
        }
        with self.assertRaisesRegex(ValueError, "PILOT_SOURCE_IDENTITY_HOLD") as caught:
            adapter.build_recovery_cases(priority, {"case-a": locator})
        self.assertEqual(
            caught.exception.counts, {"SOURCE_MATCH_COUNT_NOT_UNIQUE": 1}
        )
        self.assertEqual(
            caught.exception.safe_indices,
            [{
                "pilot_index": 0,
                "reason": "SOURCE_MATCH_COUNT_NOT_UNIQUE",
                "matched_message_count": 2,
            }],
        )

    def test_unique_exact_match_is_accepted(self):
        priority = [{
            "case_id": "case-a", "story_id": "story-a",
            "turn_index": 12, "target_sha256": "a" * 64,
        }]
        locator = {
            "case_id": "case-a", "source_status": "EXACT_MATCH",
            "matched_message_count": 1, "message_id": "message-a",
            "session_id": "session-a",
        }
        self.assertEqual(
            adapter.build_recovery_cases(priority, {"case-a": locator}),
            [{
                "case_id": "case-a", "story_id": "story-a",
                "session_id": "session-a", "turn_index": 12,
                "target_sha256": "a" * 64,
            }],
        )

    def test_owner_scope_requires_all_13_stories_and_one_uuid(self):
        owner = "11111111-1111-4111-8111-111111111111"
        class Cursor:
            def execute(self, query, params):
                self.query = query
                self.params = params
            def fetchall(self):
                return [
                    {"story_id": story, "owner_id": owner}
                    for story in self.params[0]
                ]
        ids = [f"story-{index}" for index in range(13)]
        cursor = Cursor()
        adapter.verify_story_owner_scope(cursor, ids)
        self.assertIn("id::text = ANY(%s)", cursor.query)
        self.assertIn("author_id::text AS owner_id", cursor.query)

    def test_owner_scope_accepts_multiple_owners(self):
        owner_a = "11111111-1111-4111-8111-111111111111"
        owner_b = "22222222-2222-4222-8222-222222222222"
        class Cursor:
            def execute(self, query, params):
                self.params = params
            def fetchall(self):
                return [
                    {"story_id": story, "owner_id": owner_a if i < 12 else owner_b}
                    for i, story in enumerate(self.params[0])
                ]
        ids = [f"story-{index}" for index in range(13)]
        self.assertEqual(adapter.verify_story_owner_scope(Cursor(), ids), 2)

    def test_locator_index_rejects_duplicates(self):
        packets = {
            "case-a": {
                "case_id": "case-a", "target_sha256": "a" * 64,
                "story_id": "story-a", "turn_index": 12,
            }
        }
        row = {
            "case_id": "case-a", "target_sha256": "a" * 64,
            "story_id": "story-a", "turn_index": 12,
        }
        with self.assertRaisesRegex(ValueError, "SOURCE_LOCATOR_IDENTITY_INVALID"):
            adapter.validate_locators([row, row], packets)


if __name__ == "__main__":
    unittest.main()
