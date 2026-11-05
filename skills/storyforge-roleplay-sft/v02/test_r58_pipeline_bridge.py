"""Synthetic-only contract tests; no RolePlay, R50 or protected fixtures."""
import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import r58_pipeline_bridge as bridge


def fake(**changes):
    row = {
        "story_id": "fictional-story-1", "story_type": "v2_sandbox",
        "moderation_status": "approved", "not_deleted": "t",
        "assistant_completed": "50", "session_count": "2",
        "has_world": "t", "has_character": "f", "has_characters": "t",
        "has_opening": "true", "source_type": "original",
    }
    row.update(changes)
    return row


class BridgeTests(unittest.TestCase):
    def inventory(self, root, rows):
        path = root / "private_inventory.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=sorted(bridge.REQUIRED))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_round1_minimum_and_psql_booleans(self):
        self.assertTrue(bridge.eligible(fake()))
        self.assertTrue(bridge.eligible(fake(not_deleted="True", has_characters="yes")))
        self.assertFalse(bridge.eligible(fake(session_count="1")))
        self.assertFalse(bridge.eligible(fake(assistant_completed="49")))

    def test_character_either_and_director_not_required(self):
        self.assertTrue(bridge.eligible(fake(has_character="t", has_characters="f")))
        self.assertFalse(bridge.eligible(fake(has_character="f", has_characters="f")))
        self.assertNotIn("has_director", bridge.REQUIRED)

    def test_invalid_boolean_holds(self):
        with self.assertRaises(bridge.Hold):
            bridge.boolean("sometimes")

    def test_invalid_counts_hold(self):
        for value in ("", "-1", "1.5", "1e2", "x"):
            with self.subTest(value=value), self.assertRaises(bridge.Hold):
                bridge.count(value)

    def test_only_source_allowlist(self):
        self.assertFalse(bridge.eligible(fake(source_type="unknown")))
        self.assertTrue(bridge.eligible(fake(source_type="dice_cocreate")))
        self.assertTrue(bridge.eligible(fake(source_type="ai_assisted")))

    def test_safe_aggregate_no_ids_no_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [fake(), fake(story_id="fictional-story-2", session_count="1")]
            result = bridge.inspect_inventory(self.inventory(root, rows))
            self.assertEqual((result["inventory_rows"], result["metadata_eligible"]), (2, 1))
            self.assertEqual(result["selected_new_worlds"], 0)
            self.assertNotIn("fictional-story-1", str(result))

    def test_duplicate_id_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.inventory(root, [fake(), fake(story_id=" FICTIONAL-STORY-1 ")])
            with self.assertRaises(bridge.Hold):
                bridge.inspect_inventory(path)

    def test_file_symlink_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.inventory(root, [fake()])
            link = root / "link.csv"
            link.symlink_to(path)
            with self.assertRaises(bridge.Hold):
                bridge.inspect_inventory(link)

    def test_gate_freeze_refuse_known_hold(self):
        for action in ("gate", "freeze"):
            with self.subTest(action=action):
                result = bridge.pipeline_decision(action, {
                    "status": "G1_G2_SAFE_EVIDENCE_RECONCILED__BOTH_HOLD",
                    "g1_clearance": "HOLD", "g2_clearance": "HOLD",
                    "training_admitted": 0, "expansion_allowed": False})
                self.assertEqual(result["status"], "HOLD_G1_G2_UNPROVEN__NO_V01_EXECUTION")
                self.assertFalse(result["output_data_written"])

    def test_no_self_declared_pass_escalation(self):
        for candidate in (
            {"status": "PASS", "g1_clearance": "PASS", "g2_clearance": "PASS",
             "training_admitted": 1, "expansion_allowed": True},
            {"status": "G1_G2_SAFE_EVIDENCE_RECONCILED__BOTH_HOLD",
             "g1_clearance": "PASS", "g2_clearance": "HOLD",
             "training_admitted": 0, "expansion_allowed": False},
            {},
        ):
            with self.assertRaises(bridge.Hold):
                bridge.pipeline_decision("freeze", candidate)

    def test_missing_git_repo_cli_refuses_without_private_path_leak(self):
        with tempfile.TemporaryDirectory() as temp:
            err = io.StringIO()
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = bridge.main(["gate", "--repo-root", temp])
            self.assertEqual(code, 42)
            self.assertEqual(out.getvalue(), "")
            self.assertNotIn(temp, err.getvalue())

    def test_g1_audit_cli_rejects_unapproved_paths_without_leaking_them(self):
        with tempfile.TemporaryDirectory() as temp:
            private_path = str(Path(temp) / "not_authorized_PRIVATE.json")
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = bridge.main([
                    "g1-audit", "--private-manifest", private_path,
                    "--prior-sft-ledger", private_path,
                ])
            self.assertEqual(code, 42)
            self.assertEqual(out.getvalue(), "")
            self.assertNotIn(private_path, err.getvalue())

    def test_shortlist_cli_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.inventory(root, [fake()])
            out = io.StringIO()
            with redirect_stdout(out):
                code = bridge.main(["shortlist", "--inventory", str(source)])
            self.assertEqual(code, 0)
            self.assertIn('"metadata_eligible": 1', out.getvalue())
            self.assertEqual(len(list(root.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
