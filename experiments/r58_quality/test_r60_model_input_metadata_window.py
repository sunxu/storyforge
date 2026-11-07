"""Synthetic-only tests: bounded UTC time windows and fail-closed catalog gate."""
import datetime as dt
import unittest

from experiments.r58_quality.r60_model_input_metadata_window import (
    check_catalog,
    validate_window,
)


class R60MetadataWindowTests(unittest.TestCase):
    def test_utc_window_max_24_hours(self):
        a, b = validate_window("2026-08-01T00:00:00+08:00",
                               "2026-08-02T00:00:00+08:00")
        self.assertEqual(b - a, dt.timedelta(days=1))
        self.assertEqual(a.tzinfo, dt.timezone.utc)

    def test_unbounded_or_naive_window_holds(self):
        pairs = [
            ("2026-08-01T00:00:00", "2026-08-01T01:00:00"),
            ("2026-08-01T00:00:00Z", "2026-08-03T00:00:00Z"),
            ("2026-08-02T00:00:00Z", "2026-08-01T00:00:00Z"),
        ]
        for start, end in pairs:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                validate_window(start, end)

    def test_catalog_holds_without_date_index(self):
        catalog = {
            name: {"status": "CATALOG_POLICY_MATCHED_COUNTS_NOT_RUN",
                   "index_names": []}
            for name in ("v2_chat_reply_jobs", "chat_abnormal_snapshot",
                         "chat_latency_metrics")
        }
        with self.assertRaisesRegex(ValueError, "DATE_INDEX_MISSING"):
            check_catalog(catalog)

    def test_catalog_holds_on_policy_mismatch(self):
        catalog = {
            name: {"status": "RLS_POLICY_MISMATCH_HOLD", "index_names": []}
            for name in ("v2_chat_reply_jobs", "chat_abnormal_snapshot",
                         "chat_latency_metrics")
        }
        with self.assertRaisesRegex(ValueError, "CATALOG_POLICY_HOLD"):
            check_catalog(catalog)


if __name__ == "__main__":
    unittest.main()
