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
        with self.assertRaisesRegex(ValueError, "PILOT_SOURCE_IDENTITY_HOLD"):
            adapter.build_recovery_cases(priority, {"case-a": locator})

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
