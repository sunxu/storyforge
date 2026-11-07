"""CPU-only tests for the R60 Canonical A V3 history adapter."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

try:
    from . import r60_gold192_history_recovery_v3 as adapter
except ImportError:
    import r60_gold192_history_recovery_v3 as adapter


class V3HistoryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "case_id": "case-001-t12",
            "story_id": "story-001",
            "turn_index": 12,
            "target_sha256": "a" * 64,
        }

    def locator(self, **overrides):
        row = {
            **self.case,
            "source_status": "EXACT_MATCH",
            "matched_message_count": 1,
            "message_id": "message-001",
            "session_id": "session-001",
        }
        row.update(overrides)
        return row

    def test_unique_exact_match_passes_local_precheck(self):
        self.assertIsNone(adapter._precheck_candidate(
            self.case, self.locator()
        ))

    def test_duplicate_exact_match_requires_database_reverification(self):
        # The local precheck only permits it into the DB reverification stage.
        self.assertIsNone(adapter._precheck_candidate(
            self.case, self.locator(matched_message_count=3)
        ))

    def test_ambiguous_source_is_held_even_with_multiple_exact_matches(self):
        reason = adapter._precheck_candidate(
            self.case,
            self.locator(
                source_status="IDENTITY_AMBIGUOUS",
                matched_message_count=2,
                message_id=None,
                session_id=None,
            ),
        )
        self.assertEqual(reason, "SOURCE_IDENTITY_NOT_CANONICAL")

    def test_incomplete_locator_is_held(self):
        reason = adapter._precheck_candidate(
            self.case, self.locator(session_id=None)
        )
        self.assertEqual(reason, "SOURCE_LOCATOR_INCOMPLETE")

    def test_locator_mismatch_is_held(self):
        reason = adapter._precheck_candidate(
            self.case, self.locator(target_sha256="b" * 64)
        )
        self.assertEqual(reason, "SOURCE_LOCATOR_IDENTITY_MISMATCH")

    def test_invalid_match_count_is_held(self):
        reason = adapter._precheck_candidate(
            self.case, self.locator(matched_message_count=True)
        )
        self.assertEqual(reason, "SOURCE_MATCH_COUNT_INVALID")

    def test_duplicate_status_reverification_rejects_status_drift(self):
        rows = [
            ("message-1", "exact target", "completed"),
            ("message-2", "exact target", "pending"),
        ]
        # Replace the hash function only for this synthetic status-gate test.
        original = adapter.source.sha_text
        try:
            def fake_hash(value):
                return "a" * 64 if value == "exact target" else "b" * 64

            adapter.source.sha_text = fake_hash
            reason = adapter._duplicate_target_statuses_valid(
                rows, 2, "a" * 64
            )
        finally:
            adapter.source.sha_text = original
        self.assertEqual(reason, "DUPLICATE_TARGET_STATUS_DRIFT")

    def test_duplicate_status_reverification_rejects_match_count_drift(self):
        rows = [("message-1", "exact target", "completed")]
        original = adapter.source.sha_text
        try:
            def fake_hash(value):
                return "a" * 64

            adapter.source.sha_text = fake_hash
            reason = adapter._duplicate_target_statuses_valid(
                rows, 2, "a" * 64
            )
        finally:
            adapter.source.sha_text = original
        self.assertEqual(reason, "DUPLICATE_SOURCE_MATCH_COUNT_DRIFT")

    def test_private_input_rejects_hard_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            original = root / "source.json"
            original.write_bytes(b'{"safe":true}')
            original.chmod(0o600)
            linked = root / "linked.json"
            os.link(original, linked)
            with self.assertRaisesRegex(ValueError, "PERMISSIONS_LINK_OR_SIZE"):
                adapter._read_private(linked, "TEST_INPUT")

    def test_source_receipt_requires_v3_schema_and_locator_pin(self):
        locator_bytes = b'{"case_id":"private"}\\n'
        safe = {
            "schema": "r60_gold192_supabase_extract_v3_safe_v1",
            "status": "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED",
            "gold192": 192,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "private_values_emitted": False,
            "artifacts": {
                "R60_SOURCE_LOCATORS_192.jsonl": {
                    "records": 192,
                    "sha256": adapter.recovery.digest(locator_bytes),
                }
            },
        }
        adapter._validate_source_receipt(safe, locator_bytes)
        safe["schema"] = "r59_gold192_supabase_extract_safe_v1"
        with self.assertRaisesRegex(ValueError, "SOURCE_SAFE_RECEIPT_INVALID"):
            adapter._validate_source_receipt(safe, locator_bytes)


if __name__ == "__main__":
    unittest.main()
