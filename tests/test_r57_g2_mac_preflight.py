"""Synthetic-only zero-write tests for Owner Mac R57 G2 source-pin preflight."""

import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "r57_g2_mac_preflight", ROOT / "scripts" / "r57_g2_mac_preflight.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class TestOwnerMacPreflight(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path("/synthetic-repo")
        self.private = pathlib.Path("/synthetic-owner-private")
        self.data = {}
        for name, (_, path, _) in mod.frozen.SOURCE_PATHS.items():
            self.data[path] = ("synthetic file " + name).encode("utf-8")
        git_pins = {
            name: mod.frozen._git_blob(self.data[mod.frozen.SOURCE_PATHS[name][1]])
            for name in mod.PUBLIC
        }
        trainer_pins = {
            name: hashlib.sha256(self.data[mod.frozen.SOURCE_PATHS[name][1]]).hexdigest()
            for name in mod.PRIVATE
        }
        first = mock.patch.object(mod.frozen, "GIT_BLOBS", git_pins)
        second = mock.patch.object(mod.frozen, "HISTORICAL_TRAINER_SHA256", trainer_pins)
        first.start()
        second.start()
        self.addCleanup(first.stop)
        self.addCleanup(second.stop)

    def read(self, root, path, limit):
        return self.data[path]

    def test_eight_pins_pass_but_not_exact_overlap_or_admission(self):
        summary, ok = mod.preflight(self.repo, self.private, reader=self.read)
        self.assertTrue(ok)
        self.assertEqual(summary["byte_pin_pass_count"], 8)
        self.assertIn("EXACT_OVERLAP_AND_WORLD_STILL_PENDING", summary["status"])
        self.assertFalse(summary["exact_target_lineage_replayed"])
        self.assertFalse(summary["world_alias_graph_certified"])
        self.assertFalse(summary["protected_evaluation_accessed"])
        self.assertEqual(summary["v04_admitted"], 0)

    def test_only_four_public_git_pins_pass(self):
        summary, ok = mod.preflight(self.repo, only_public=True, reader=self.read)
        self.assertTrue(ok)
        self.assertEqual(summary["checked_collection_count"], 4)
        self.assertEqual(set(summary["source_status"]), set(mod.PUBLIC))
        self.assertIn("NOT_FULL_G2", summary["status"])

    def test_missing_private_root_blocks_eight(self):
        summary, ok = mod.preflight(self.repo, reader=self.read)
        self.assertFalse(ok)
        self.assertEqual(summary["byte_pin_pass_count"], 4)
        self.assertTrue(all(summary["source_status"][name] == "MISSING_PRIVATE_ROOT"
                            for name in mod.PRIVATE))

    def test_missing_private_file_is_safe_hold(self):
        missing_path = mod.frozen.SOURCE_PATHS["R54_TRAIN"][1]

        def missing(root, relative, limit):
            if relative == missing_path:
                raise FileNotFoundError()
            return self.read(root, relative, limit)

        summary, ok = mod.preflight(self.repo, self.private, reader=missing)
        self.assertFalse(ok)
        self.assertEqual(summary["source_status"]["R54_TRAIN"], "MISSING")
        self.assertEqual(summary["byte_pin_pass_count"], 7)

    def test_changed_historical_trainer_bytes_are_detected(self):
        bad = mod.frozen.SOURCE_PATHS["R46_TRAIN"][1]

        def changed(root, relative, limit):
            return b"tampered synthetic bytes" if relative == bad else self.read(root, relative, limit)

        summary, ok = mod.preflight(self.repo, self.private, reader=changed)
        self.assertFalse(ok)
        self.assertEqual(summary["source_status"]["R46_TRAIN"], "BYTE_PIN_MISMATCH")

    def test_changed_git_blob_bytes_are_detected(self):
        bad = mod.frozen.SOURCE_PATHS["GOLD108"][1]

        def changed(root, relative, limit):
            return b"tampered synthetic bytes" if relative == bad else self.read(root, relative, limit)

        summary, ok = mod.preflight(self.repo, self.private, only_public=True, reader=changed)
        self.assertFalse(ok)
        self.assertEqual(summary["source_status"]["GOLD108"], "BYTE_PIN_MISMATCH")

    def test_unsafe_symlink_raises_private_safe_hold(self):
        def denied(root, relative, limit):
            raise mod.frozen.ExportHold("symlink input/output path forbidden")

        summary, ok = mod.preflight(self.repo, self.private, reader=denied)
        self.assertFalse(ok)
        self.assertEqual(set(summary["source_status"].values()), {"UNSAFE_OR_UNREADABLE"})

    def test_private_folder_inside_repo_is_rejected_without_any_read(self):
        def should_not_read(*args):
            raise AssertionError("this must never be called")

        summary, ok = mod.preflight(
            self.repo, self.repo / "private", reader=should_not_read
        )
        self.assertFalse(ok)
        self.assertEqual(summary["source_status"], {})
        self.assertIn("NOT_SEPARATE", summary["status"])

    def test_fixed_safe_result_has_no_raw_text_path_or_digest(self):
        report, _ = mod.preflight(self.repo, self.private, reader=self.read)
        public = json.dumps(report)
        self.assertNotIn("synthetic file", public)
        self.assertNotIn("synthetic-owner-private", public)
        self.assertNotIn("e3b0c442", public)
        self.assertNotIn("r50", public.lower().replace("r50_content_accessed", ""))


if __name__ == "__main__":
    unittest.main()
