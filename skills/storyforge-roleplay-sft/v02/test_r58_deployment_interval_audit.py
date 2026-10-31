"""Synthetic-only tests; NEVER uses actual deployment, cases or HF objects."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import r58_deployment_interval_audit as m


def fixture():
    return {
        "schema": m.SCHEMA,
        "source_pin": m.SOURCE_PIN,
        "frozen_target_claims": [
            {"generated_at_utc": f"2026-10-20T{n:02}:30:00Z", "serving_backend": "PRIMARY"}
            for n in (10, 11, 12)
        ],
        "deployment_intervals": [{
            "serving_backend": "PRIMARY",
            "deploy_sha": m.SOURCE_PIN,
            "active_from_utc": "2026-10-20T10:00:00Z",
            "active_until_utc": "2026-10-20T13:00:00Z",
            "activation_receipt_type": "SUCCESS_CUTOVER_RECEIPT_REPORTED",
            "termination_receipt_type": "NEXT_CUTOVER_RECEIPT_REPORTED",
            "activation_receipt_sha256": "a" * 64,
            "termination_receipt_sha256": "b" * 64,
        }],
    }


class DeploymentIntervalTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def test_coverage_still_never_grants_pass(self):
        r = m.analyze(self.data)
        self.assertEqual(r["structurally_covered_target_count"], 3)
        self.assertEqual(r["claimed_source_pin_target_count"], 3)
        self.assertEqual(r["reported_start_end_receipts_target_count"], 3)
        self.assertFalse(r["target_time_deployed_sha_proven"])
        self.assertEqual((r["g1_clearance"], r["g2_clearance"]), ("HOLD", "HOLD"))

    def test_private_times_and_hashes_never_exported(self):
        out = json.dumps(m.analyze(self.data))
        self.assertNotIn("2026-10-20", out)
        self.assertNotIn(m.SOURCE_PIN, out)
        self.assertNotIn("a" * 64, out)
        self.assertNotIn("PRIMARY", out)

    def test_missing_target_fails_closed(self):
        self.data["frozen_target_claims"].pop()
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_repeated_target_time_fails(self):
        self.data["frozen_target_claims"][1]["generated_at_utc"] = "2026-10-20T10:30:00Z"
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_unknown_backend_is_not_covered(self):
        self.data["frozen_target_claims"][0]["serving_backend"] = "UNKNOWN"
        r = m.analyze(self.data)
        self.assertEqual(r["target_backend_unknown_count"], 1)
        self.assertEqual(r["structurally_covered_target_count"], 2)

    def test_no_intervals_stays_hold(self):
        self.data["deployment_intervals"] = []
        r = m.analyze(self.data)
        self.assertEqual(r["structurally_covered_target_count"], 0)
        self.assertEqual(r["g2_clearance"], "HOLD")

    def test_boundary_uses_half_open_interval(self):
        self.data["frozen_target_claims"][-1]["generated_at_utc"] = "2026-10-20T13:00:00Z"
        r = m.analyze(self.data)
        self.assertEqual(r["structurally_covered_target_count"], 2)

    def test_bad_date_rejected(self):
        self.data["frozen_target_claims"][0]["generated_at_utc"] = "2026-10-33T10:30:00Z"
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_timezone_offset_rejected(self):
        self.data["deployment_intervals"][0]["active_from_utc"] = "2026-10-20T10:00:00+00:00"
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_overlapping_deployments_rejected(self):
        item = dict(self.data["deployment_intervals"][0])
        item["active_from_utc"] = "2026-10-20T12:00:00Z"
        item["active_until_utc"] = "2026-10-20T14:00:00Z"
        self.data["deployment_intervals"].append(item)
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_distinct_backend_intervals_allowed(self):
        item = dict(self.data["deployment_intervals"][0])
        item["serving_backend"] = "V2_REPLICA"
        self.data["deployment_intervals"].append(item)
        r = m.analyze(self.data)
        self.assertEqual(r["structurally_covered_target_count"], 3)

    def test_claimed_current_marker_not_historical_proof(self):
        self.data["deployment_intervals"][0]["activation_receipt_type"] = "CURRENT_DEPLOYED_SHA_ONLY"
        r = m.analyze(self.data)
        self.assertEqual(r["reported_start_end_receipts_target_count"], 0)
        self.assertEqual(r["g2_clearance"], "HOLD")

    def test_claimed_source_not_pinned(self):
        self.data["deployment_intervals"][0]["deploy_sha"] = "c" * 40
        r = m.analyze(self.data)
        self.assertEqual(r["claimed_source_pin_target_count"], 0)
        self.assertEqual(r["structurally_covered_target_count"], 3)

    def test_bad_sha_and_digest_fail(self):
        self.data["deployment_intervals"][0]["deploy_sha"] = "a" * 20
        with self.assertRaises(m.Hold):
            m.analyze(self.data)
        self.data = fixture()
        self.data["deployment_intervals"][0]["activation_receipt_sha256"] = "no"
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_reused_start_end_digest_fail(self):
        self.data["deployment_intervals"][0]["termination_receipt_sha256"] = "a" * 64
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_extra_story_text_field_rejected(self):
        self.data["deployment_intervals"][0]["story_text"] = "private text"
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_illegal_claimed_receipt_class_rejected(self):
        self.data["deployment_intervals"][0]["activation_receipt_type"] = "INDEPENDENTLY_VERIFIED"
        with self.assertRaises(m.Hold):
            m.analyze(self.data)

    def test_cli_uses_private_existing_file_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".storyforge-r58-private"
            root.mkdir(mode=0o700)
            manifest = root / "existing.json"
            manifest.write_text(json.dumps(self.data), encoding="utf8")
            manifest.chmod(0o600)
            before = manifest.read_bytes()
            out = io.StringIO()
            with patch.object(Path, "home", return_value=Path(tmp)), redirect_stdout(out):
                code = m.main(["--private-manifest", str(manifest)])
            self.assertEqual(code, 0)
            self.assertEqual(manifest.read_bytes(), before)
            self.assertEqual(json.loads(out.getvalue())["g2_clearance"], "HOLD")

    def test_cli_outside_path_is_hold_without_leak(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = m.main(["--private-manifest", "/tmp/no-access-private.json"])
        self.assertEqual(code, 42)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("/tmp/no-access-private.json", err.getvalue())


if __name__ == "__main__":
    unittest.main()
