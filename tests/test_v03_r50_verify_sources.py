"""R50 metadata-only source verification tests; no story texts or GPU."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from v03_r50_verify_sources import digest_file, verify


class R50SourceVerifyTests(unittest.TestCase):
    def fixture(self, base: Path) -> tuple[dict, Path]:
        prefix = Path("evaluations/v0.2/source-archives/16-20")
        entries = []
        for world in range(5):
            for number in range(7):
                relative = prefix / f"story-{world + 16}" / f"source-{number}.json"
                path = base / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"world": world, "item": number}), encoding="utf-8")
                size, blob, _ = digest_file(path)
                entries.append({
                    "path": str(relative),
                    "size_bytes": size,
                    "git_blob_sha1": blob,
                })
        receipt = {
            "schema": "storyforge-r50-source-receipt-v1",
            "source_root": str(prefix),
            "source_commit": "f" * 40,
            "files": entries,
            "worlds": [{"story_id": f"unique-world-{i}"} for i in range(5)],
        }
        return receipt, base / Path(entries[0]["path"])

    def test_verified_source_bytes_and_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            receipt, _ = self.fixture(repo)
            result = verify(repo, receipt)
            self.assertEqual(result["file_count"], 35)
            self.assertEqual(result["world_count"], 5)
            self.assertEqual(len(result["files"]), 35)
            self.assertEqual(result["status"], "SOURCE_BYTES_VERIFIED_ONLY__NO_HELDOUT_ADMISSION")

    def test_changed_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            receipt, original = self.fixture(repo)
            original.write_bytes(b"mutated")
            with self.assertRaisesRegex(ValueError, "source changed"):
                verify(repo, receipt)

    def test_unregistered_extra_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            receipt, original = self.fixture(repo)
            (original.parent / "unregistered.json").write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inventory mismatch"):
                verify(repo, receipt)

    def test_malformed_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            receipt, _ = self.fixture(repo)
            receipt["source_root"] = "../outside"
            with self.assertRaisesRegex(ValueError, "invalid source root"):
                verify(repo, receipt)
            receipt["source_root"] = "evaluations/v0.2/source-archives/16-20"
            receipt["worlds"][0]["story_id"] = receipt["worlds"][1]["story_id"]
            with self.assertRaisesRegex(ValueError, "five different"):
                verify(repo, receipt)


if __name__ == "__main__":
    unittest.main()
