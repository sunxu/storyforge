import hashlib
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from gold195_archive_source_discovery import walk_zip, audit


class ArchiveSourceDiscoveryTests(unittest.TestCase):
    @staticmethod
    def archive(files):
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as f:
            for name, payload in files.items():
                f.writestr(name, payload)
        return out.getvalue()

    def test_nested_source_inventory_no_leak(self):
        nested = self.archive({"private-story-cards.json": b'{"secret":"PRIVATE_CANARY"}',
                               "private_messages.jsonl": b'{"content":"PRIVATE_CANARY"}'})
        outer = self.archive({"sources/private.zip": nested,
                              "metadata/info.json": b'{}'})
        from collections import Counter
        counts = Counter()
        walk_zip(io.BytesIO(outer), counts)
        self.assertEqual(counts["nested_zips"], 1)
        self.assertEqual(counts["card_name_candidates"], 1)
        self.assertEqual(counts["json_members"], 2)
        self.assertEqual(counts["jsonl_members"], 1)
        self.assertNotIn("PRIVATE_CANARY", str(counts))

    def test_missing_lfs_is_hold(self):
        with tempfile.TemporaryDirectory() as td:
            result = audit(Path(td))
            self.assertEqual(result["status"], "ARCHIVES_MISSING__HOLD")
            self.assertEqual(result["training_admitted"], 0)

    def test_wrong_lfs_pointer_size_is_hold(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "evaluations/v0.2/source-archives/06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip"
            p.parent.mkdir(parents=True)
            p.write_text("version https://git-lfs.github.com/spec/v1")
            self.assertEqual(audit(Path(td))["sources"]["gold108_06_15"]["status"],
                             "EXPECTED_LFS_ARCHIVE_NOT_PRESENT")

    def test_corrupt_inner_archive_fails(self):
        outer = self.archive({"sources/private.zip": b"INVALID"})
        from collections import Counter
        with self.assertRaises(zipfile.BadZipFile):
            walk_zip(io.BytesIO(outer), Counter())


if __name__ == "__main__":
    unittest.main()
