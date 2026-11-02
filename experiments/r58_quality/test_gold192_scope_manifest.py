"""Synthetic-only private Gold192 scope manifest tests."""
import json
import tempfile
import unittest
from pathlib import Path

from gold192_scope_manifest import build_scope, write_manifest


class TestGold192ScopeManifest(unittest.TestCase):
    def test_statuses_do_not_approve_training(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            queue = root / "queue.jsonl"
            rows = [
                {"case_id": "synthetic-a", "reason_code": "WORLD_OR_TARGET_IDENTITY_HOLD"},
                {"case_id": "synthetic-b", "reason_code": "CONTEXT_EQUIVALENCE_UNVERIFIED"},
            ]
            queue.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            result = build_scope(queue)
            self.assertEqual(result[0]["scope_status"], "EXCLUDED_WORLD_ID_UNRESOLVED")
            self.assertEqual(result[1]["scope_status"], "CANDIDATE_ONLY_QUALITY_HOLD")
            self.assertTrue(all(r["quality_v1_admitted"] is False for r in result))
            self.assertTrue(all(r["training_authorized"] is False for r in result))

    def test_refuse_output_via_repo_symlink_alias(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real_repo = base / "real-repo"
            real_repo.mkdir()
            alias = base / "repo-alias"
            alias.symlink_to(real_repo, target_is_directory=True)
            output = real_repo / "manifest.jsonl"
            with self.assertRaisesRegex(ValueError, "SCOPE_OUTPUT_INVALID"):
                write_manifest(output, alias, [])
            self.assertFalse(output.exists())

    def test_refuse_output_inside_repo_and_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / "manifest.jsonl"
            with self.assertRaisesRegex(ValueError, "SCOPE_OUTPUT_INVALID"):
                write_manifest(output, root, [])
            other_repo = root / "unrelated"
            other_repo.mkdir()
            output.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SCOPE_OUTPUT_INVALID"):
                write_manifest(output, other_repo, [])


if __name__ == "__main__":
    unittest.main()
