"""Synthetic tests for the Strict28 private history-recovery adapter."""
import json
import unittest

from experiments.r58_quality import r59_strict28_history_recovery as adapter


def synthetic_rows():
    rows = []
    for index in range(28):
        story_id = "story-a" if index < 14 else "story-b"
        rows.append({
            "case_id": f"case-{index:02d}-t{index + 1:05d}",
            "story_uuid": story_id,
            "current_story_id": story_id,
            "current_session_id": f"session-{index:02d}",
            "target_sha256": f"{index + 1:064x}",
        })
    return rows


class Strict28AdapterTests(unittest.TestCase):
    def test_exact_28_locators_and_two_story_scope(self):
        rows = synthetic_rows()
        raw = b"".join(
            (json.dumps(row, sort_keys=True) + "\n").encode() for row in rows
        )
        result = adapter.validate_strict28_ledger(raw, adapter._sha(raw))
        self.assertEqual(len(result), 28)
        self.assertEqual({row["story_id"] for row in result}, {"story-a", "story-b"})
        self.assertEqual(result[0]["turn_index"], 1)
        self.assertEqual(result[-1]["turn_index"], 28)

    def test_wrong_case_count_holds(self):
        rows = synthetic_rows()[:-1]
        raw = b"".join((json.dumps(row) + "\n").encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "STRICT28_LEDGER_SCOPE_INVALID"):
            adapter.validate_strict28_ledger(raw, adapter._sha(raw))

    def test_duplicate_target_holds(self):
        rows = synthetic_rows()
        rows[1]["target_sha256"] = rows[0]["target_sha256"]
        raw = b"".join((json.dumps(row) + "\n").encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "STRICT28_LEDGER_SCOPE_INVALID"):
            adapter.validate_strict28_ledger(raw, adapter._sha(raw))

    def test_story_uuid_must_match_resolved_story(self):
        rows = synthetic_rows()
        rows[0]["story_uuid"] = "different-story"
        raw = b"".join((json.dumps(row) + "\n").encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "STRICT28_LEDGER_LOCATOR_INVALID"):
            adapter.validate_strict28_ledger(raw, adapter._sha(raw))

    def test_turn_index_must_be_encoded_in_case_id(self):
        rows = synthetic_rows()
        rows[0]["case_id"] = "case-without-turn"
        raw = b"".join((json.dumps(row) + "\n").encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "STRICT28_LEDGER_LOCATOR_INVALID"):
            adapter.validate_strict28_ledger(raw, adapter._sha(raw))

    def test_duplicate_json_keys_hold(self):
        row = synthetic_rows()[0]
        raw_row = json.dumps(row).replace('"case_id":', '"case_id":"shadow","case_id":')
        raw = (raw_row + "\n").encode()
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            adapter.validate_strict28_ledger(raw, adapter._sha(raw))

    def test_same_run_safe_receipt_binds_private_ledger(self):
        receipt = {
            "schema": "r59_strict28_historical_exposure_safe_v1",
            "status": "STRICT28_HISTORICAL_TARGET_AND_CONTEXT_EXPOSURE_CLASSIFIED__NO_ADMISSION",
            "strict28_cases": 28,
            "strict28_contexts_verified": 28,
            "review_intersection_verified": True,
            "strict28_exclusions_overlap": 0,
            "historical_sources_byte_pinned": True,
            "system_prompt_equivalence_proven": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
            "private_ledger": {
                "records": 28,
                "file": "R59_STRICT28_HISTORICAL_EXPOSURE_PRIVATE.jsonl",
                "sha256": "a" * 64,
            },
        }
        self.assertEqual(adapter.validate_safe_receipt(receipt), "a" * 64)
        receipt["training_authorized"] = True
        with self.assertRaisesRegex(ValueError, "STRICT28_SAFE_RECEIPT_INVALID"):
            adapter.validate_safe_receipt(receipt)

    def test_ledger_digest_must_match_same_run_safe_receipt(self):
        raw = b'{"case_id":"not-a-full-ledger"}\\n'
        with self.assertRaisesRegex(ValueError, "STRICT28_LEDGER_SHA256_MISMATCH"):
            adapter.validate_strict28_ledger(raw, "0" * 64)

    def test_output_is_create_only_and_private(self):
        import hashlib
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.chmod(0o700)
            path = root / "private.jsonl"
            digest = adapter._create_only(path, b'{"private":true}\n')
            self.assertEqual(digest, hashlib.sha256(b'{"private":true}\n').hexdigest())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                adapter._create_only(path, b'{"overwrite":true}\n')
            self.assertEqual(path.read_bytes(), b'{"private":true}\n')


if __name__ == "__main__":
    unittest.main()
