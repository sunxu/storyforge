#!/usr/bin/env python3
"""Synthetic-only R58 G2 release-note date triage tests. No source-file reads."""
from __future__ import annotations

import json
import unittest

from r58_g2_frozen_target_release_date_triage_safe_20261101 import (
    CATEGORIES, SCHEMA, ScopeHold, aggregate_frozen_dates, bucket,
)


def cases(times):
    return [
        {"cohort": "AUTHOR", "target_time": times[0]},
        {"cohort": "CURRENT_PUBLIC", "target_time": times[1]},
        {"cohort": "OLD_PUBLIC", "target_time": times[2]},
    ]


class ReleaseDateTriageTest(unittest.TestCase):
    def test_utc_buckets_before_between_after(self):
        result = aggregate_frozen_dates(cases([
            "2026-10-08T23:59:59Z",
            "2026-10-19T13:00:00+00:00",
            "2026-10-30T00:00:00Z",
        ]))
        self.assertEqual(result["private_frozen_source_rows_verified"], 3)
        self.assertEqual(sum(result["release_document_date_bucket_counts"].values()), 3)
        self.assertEqual(result["release_document_date_bucket_counts"][CATEGORIES[0]], 1)
        self.assertEqual(result["release_document_date_bucket_counts"][CATEGORIES[2]], 1)
        self.assertEqual(result["release_document_date_bucket_counts"][CATEGORIES[4]], 1)

    def test_utc_date_bucket_boundaries(self):
        self.assertEqual(bucket("2026-10-09T00:00:00Z"), CATEGORIES[1])
        self.assertEqual(bucket("2026-10-18T00:00:00Z"), CATEGORIES[2])
        self.assertEqual(bucket("2026-10-28T00:00:00Z"), CATEGORIES[3])
        self.assertEqual(bucket("2026-10-30T00:00:00Z"), CATEGORIES[4])

    def test_timezone_offset_to_utc(self):
        self.assertEqual(bucket("2026-10-09T07:59:59+08:00"), CATEGORIES[0])
        self.assertEqual(bucket("2026-10-09T08:00:00+08:00"), CATEGORIES[1])
        self.assertEqual(bucket("2026-10-28T08:00:00+08:00"), CATEGORIES[3])

    def test_reject_missing_duplicate_or_extra_case(self):
        for targets in [
            [],
            cases(["2026-10-29T00:00:00Z"] * 3)[:2],
            cases(["2026-10-29T00:00:00Z"] * 3) + [{"cohort": "X", "target_time": "2026-10-29T00:00:00Z"}],
        ]:
            with self.subTest(n=len(targets)), self.assertRaises(ScopeHold):
                aggregate_frozen_dates(targets)

    def test_reject_duplicate_or_unknown_cohorts(self):
        ts = ["2026-10-11T00:00:00Z"] * 3
        for wrong in [
            [{"cohort": "AUTHOR", "target_time": ts[0]}] * 3,
            [{"cohort": x, "target_time": t} for x,t in zip(("AUTHOR","OLD_PUBLIC","X"),ts)],
        ]:
            with self.assertRaises(ScopeHold):
                aggregate_frozen_dates(wrong)

    def test_reject_invalid_timestamps(self):
        for ts in ["", None, "2026-10-28T01:02:03", "not-a-date", "2026-13-01T00:00:00Z"]:
            with self.subTest(ts=ts), self.assertRaises(ScopeHold):
                bucket(ts)

    def test_safe_aggregate_has_no_per_case_names_or_exact_times(self):
        ts = [
            "2026-10-11T00:01:02Z",
            "2026-10-23T03:04:05Z",
            "2026-11-01T04:05:06Z",
        ]
        result = aggregate_frozen_dates(cases(ts))
        data = json.dumps(result, sort_keys=True)
        for t in ts:
            self.assertNotIn(t, data)
        for private_name in ["CURRENT_PUBLIC", "OLD_PUBLIC", "AUTHOR", "target_id", "story_id"]:
            self.assertNotIn(private_name, data)

    def test_success_still_rejects_g2_clearance(self):
        r = aggregate_frozen_dates(cases(["2026-11-01T12:00:00Z"] * 3))
        self.assertEqual(r["schema"], SCHEMA)
        self.assertEqual(r["g2_clearance"], "HOLD")
        self.assertEqual(r["g1_clearance"], "HOLD")
        self.assertFalse(r["historical_deployed_sha_proven"])
        self.assertFalse(r["target_message_to_request_id_link_proven"])
        self.assertEqual(r["train_admitted"], 0)
        self.assertFalse(r["expansion_allowed"])

    def test_uses_existing_private_integrity_claim_only(self):
        r = aggregate_frozen_dates(cases(["2026-10-28T23:59:00Z"] * 3))
        self.assertTrue(r["source_data_file_contains_private_narrative_read_locally"])
        self.assertTrue(r["private_source_content_or_ids_exported"] is False)
        self.assertEqual(r["private_per_case_fingerprints_verified"], 12)
        self.assertEqual(r["reported_release_candidate_catalog_commits"], 13)


if __name__ == "__main__":
    unittest.main()
