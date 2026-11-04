from __future__ import annotations

import hashlib
import json
import unittest

from r59_history_density import build_report, load_rows

FINGERPRINT = "a" * 64
SCHEMA = "storyforge-r59-semantic-review-prompt-private-v1"


def make_rows() -> list[dict]:
    rows = []
    for index in range(8):
        rows.append(
            {
                "schema": SCHEMA,
                "pilot_index": index,
                "prompt_fingerprint": FINGERPRINT,
                "review_decision": None,
                "gpu_started": False,
                "quality_v1_admitted": False,
                "messages": [
                    {"role": "system", "content": "S" * 4},
                    {"role": "user", "content": "U" * (100 + index)},
                ],
                "history_coverage": {
                    "scope": "FULL_STAGED_SUFFIX_ONLY",
                    "retained_history_messages": index + 1,
                    "removed_upstream_prefix_messages": index * 2,
                    "context_semantically_verified": True,
                    "historical_world_card_approved": False,
                    "history_origin_verified_from_database": True,
                },
            }
        )
    return rows


class HistoryDensityTests(unittest.TestCase):
    def test_builds_aggregate_without_private_text(self):
        rows = make_rows()
        raw = b"\n".join(json.dumps(row).encode() for row in rows)
        parsed = load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)
        report = build_report(parsed, hashlib.sha256(raw).hexdigest(), None)
        self.assertEqual(report["aggregate"]["retained_history_messages_total"], 36)
        self.assertEqual(report["aggregate"]["removed_upstream_prefix_messages_total"], 56)
        self.assertEqual(report["cases"][2]["serialized_user_prompt_chars"], 102)
        self.assertNotIn("UUUU", json.dumps(report))
        self.assertFalse(report["gpu_started"])
        self.assertEqual(report["quality_v1_admitted"], 0)

    def test_rejects_hash_mismatch(self):
        raw = b"\n".join(json.dumps(row).encode() for row in make_rows())
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256_MISMATCH"):
            load_rows(raw, "0" * 64, FINGERPRINT)

    def test_rejects_wrong_case_count(self):
        raw = json.dumps(make_rows()[0]).encode()
        with self.assertRaisesRegex(ValueError, "INPUT_CASE_COUNT_INVALID"):
            load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)

    def test_rejects_wrong_order(self):
        rows = make_rows()
        rows[0]["pilot_index"] = 1
        raw = b"\n".join(json.dumps(row).encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "PROMPT_IDENTITY_INVALID_CASE_0"):
            load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)

    def test_rejects_missing_history_count(self):
        rows = make_rows()
        del rows[0]["history_coverage"]["retained_history_messages"]
        raw = b"\n".join(json.dumps(row).encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "HISTORY_COVERAGE_FIELD_INVALID"):
            load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)

    def test_rejects_negative_history_count(self):
        rows = make_rows()
        rows[0]["history_coverage"]["removed_upstream_prefix_messages"] = -1
        raw = b"\n".join(json.dumps(row).encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "HISTORY_COVERAGE_FIELD_INVALID"):
            load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)

    def test_rejects_wrong_history_scope(self):
        rows = make_rows()
        rows[0]["history_coverage"]["scope"] = "OTHER"
        raw = b"\n".join(json.dumps(row).encode() for row in rows)
        with self.assertRaisesRegex(ValueError, "HISTORY_COVERAGE_SCOPE_INVALID"):
            load_rows(raw, hashlib.sha256(raw).hexdigest(), FINGERPRINT)


if __name__ == "__main__":
    unittest.main()
