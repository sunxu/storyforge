"""Synthetic-only receipt verification for legacy and suffix R59 staging."""
from __future__ import annotations

import unittest

from r59_staging_receipt import NEW_SCHEMA, NEW_STATUS, OLD_SCHEMA, valid_staging_receipt


class ReceiptTests(unittest.TestCase):
    def test_legacy(self):
        r = {"schema": OLD_SCHEMA, "status": "GOLD_SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING",
             "staged_file_sha256": "a" * 64}
        self.assertTrue(valid_staging_receipt(r, "a" * 64))
        self.assertFalse(valid_staging_receipt({**r, "status": "FAILED"}, "a" * 64))

    def test_new(self):
        r = {"schema": NEW_SCHEMA, "status": NEW_STATUS, "staged_file_sha256": "a" * 64,
             "context_staged": 72, "source_rows": 72, "context_structure_hold": 0,
             "source_histories_mutated": False, "original_staging_mutated": False,
             "quality_v1_admitted": 0, "training_authorized": False, "gpu_started": False,
             "source_context_file_sha256": "b" * 64,
             "previous_staged_file_sha256": "c" * 64}
        self.assertTrue(valid_staging_receipt(r, "a" * 64))
        for changed in [
            {"staged_file_sha256": "d" * 64}, {"context_staged": 71},
            {"quality_v1_admitted": 1}, {"source_histories_mutated": True},
            {"training_authorized": True}, {"status": "OTHER"}, {"schema": "UNKNOWN"},
        ]:
            self.assertFalse(valid_staging_receipt({**r, **changed}, "a" * 64))

    def test_unknown_fails(self):
        self.assertFalse(valid_staging_receipt({"schema": "anything"}, "a" * 64))


if __name__ == "__main__":
    unittest.main()
