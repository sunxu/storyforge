#!/usr/bin/env python3
"""Synthetic-only tests; never reads owner PRIVATE files or opens a network."""
from __future__ import annotations

import json
import unittest

from r58_g2_frozen_target_cutover_window_triage_safe_20261101 import (
    REPORTED_EVENTS, SCHEMA, ScopeHold, WINDOW_IDS, event_boundaries,
    parse_time, summarize,
)


def cases(times):
    return [
        {"cohort": "AUTHOR", "target_time": times[0]},
        {"cohort": "CURRENT_PUBLIC", "target_time": times[1]},
        {"cohort": "OLD_PUBLIC", "target_time": times[2]},
    ]


class TestReportedCutoverWindows(unittest.TestCase):
    def test_reported_boundaries_sorted(self):
        bounds = event_boundaries()
        self.assertEqual(len(bounds), 6)
        self.assertEqual(len(set(bounds)), 6)
        self.assertEqual(len(WINDOW_IDS), 7)

    def test_windows_include_each_cutover_and_utc_oct30_boundary(self):
        bounds = [s for s, _ in REPORTED_EVENTS]
        expected_windows = (1, 2, 3, 4, 5, 6)
        from bisect import bisect_right
        for when, expected in zip(bounds, expected_windows):
            with self.subTest(when=when):
                self.assertEqual(bisect_right(event_boundaries(), parse_time(when)), expected)

    def test_timezone_offset_adjustment(self):
        self.assertEqual(
            parse_time("2026-10-29T12:07:06+08:00"),
            parse_time("2026-10-29T04:07:06Z"),
        )

    def test_three_records_count_and_gate_hold(self):
        r = summarize(cases([
            "2026-10-28T01:20:00Z",
            "2026-10-29T03:00:00Z",
            "2026-10-30T13:00:00Z",
        ]))
        self.assertEqual(sum(r["owner_reported_cutover_window_counts"].values()), 3)
        self.assertEqual(r["owner_reported_cutover_window_counts"]["window_0"], 1)
        self.assertEqual(r["owner_reported_cutover_window_counts"]["window_4"], 1)
        self.assertEqual(r["owner_reported_cutover_window_counts"]["window_6"], 1)
        self.assertEqual(r["g2_clearance"], "HOLD")
        self.assertFalse(r["actual_historical_deployment_sha_proven"])
        self.assertFalse(r["expansion_allowed"])

    def test_boundary_inclusive_on_event_claim(self):
        r = summarize(cases([
            "2026-10-28T07:28:16Z",
            "2026-10-28T08:57:00Z",
            "2026-10-29T04:07:06Z",
        ]))
        hist = r["owner_reported_cutover_window_counts"]
        self.assertEqual((hist["window_2"], hist["window_3"], hist["window_5"]), (1, 1, 1))

    def test_reject_bad_cohorts_and_count(self):
        base = cases(["2026-10-30T00:00:00Z"] * 3)
        for bad in [
            base[:2],
            base + [base[0]],
            [base[0], base[0], base[2]],
            [base[0], base[1], {"cohort": "UNKNOWN", "target_time": base[2]["target_time"]}],
        ]:
            with self.subTest(case_count=len(bad)), self.assertRaises(ScopeHold):
                summarize(bad)

    def test_reject_invalid_timestamps(self):
        for t in ["", None, "invalid", "2026-10-29T00:00:00", "2026-13-01T00:00:00Z"]:
            with self.subTest(time=t), self.assertRaises(ScopeHold):
                parse_time(t)

    def test_no_raw_times_or_case_identifiers_exported(self):
        times = ["2026-10-28T03:04:05Z",
                 "2026-10-29T06:07:08Z", "2026-10-30T11:12:13Z"]
        result = summarize(cases(times))
        blob = json.dumps(result, sort_keys=True)
        for forbidden in (*times, "AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC",
                          "story_id", "SYNTHETIC_SECRET_ID_123", "target_message_id"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, blob)
        self.assertFalse(result["private_raw_timestamp_or_identity_exported"])
        self.assertFalse(result["case_to_cohort_or_window_mapping_exported"])

    def test_never_claims_production_model_or_provider_proven(self):
        result = summarize(cases(["2026-11-01T01:02:03Z"] * 3))
        self.assertEqual(result["schema"], SCHEMA)
        self.assertFalse(result["time_window_proves_active_deployment_or_backend"])
        self.assertFalse(result["historical_runtime_model_version_proven"])
        self.assertFalse(result["original_provider_request_bytes_verified"])
        self.assertEqual(result["train_admitted"], 0)


if __name__ == "__main__":
    unittest.main()
