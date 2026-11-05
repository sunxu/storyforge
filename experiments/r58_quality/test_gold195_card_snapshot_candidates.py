import io
import hashlib
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from gold195_card_snapshot_candidates import find_cards, write_private


class CardSnapshotCandidateTests(unittest.TestCase):
    def sample_zip(self, card):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("private-story.json", json.dumps(
                {"story": {"id": "PRIVATE_WORLD", "v2_data": card}}))
        buf.seek(0)
        return buf

    def test_source_card_identity_and_no_log_content(self):
        items, counts = {}, Counter()
        find_cards(self.sample_zip({"character": "PRIVATE_CHARACTER"}),
                   "source_archive", items, counts)
        self.assertEqual(len(items), 1)
        self.assertEqual(items["PRIVATE_WORLD"]["review_status"],
                         "NOT_APPROVED_FOR_SYSTEM")
        self.assertEqual(counts["card_objects_found"], 1)
        self.assertNotIn("PRIVATE_CHARACTER", str(counts))

    def test_source_conflict_not_overwritten(self):
        items, counts = {}, Counter()
        find_cards(self.sample_zip({"character": "A"}), "src", items, counts)
        find_cards(self.sample_zip({"character": "B"}), "src", items, counts)
        self.assertEqual(counts["conflicting_story_snapshot_versions"], 1)
        self.assertEqual(items["PRIVATE_WORLD"]["snapshot_card_json"]["character"], "A")

    def test_output_is_private_and_not_in_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            folder = root / "private"
            folder.mkdir(mode=0o700)
            file = folder / "cards.json"
            write_private(file, repo, [{"story_uuid":"PRIVATE_WORLD"}])
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
            data = json.loads(file.read_text())
            self.assertEqual(data["status"], "CANDIDATE_ONLY_NOT_APPROVED")
            with self.assertRaises(ValueError):
                write_private(file, repo, [])
            with self.assertRaises(ValueError):
                write_private(repo / "unsafe.json", repo, [])


if __name__ == "__main__":
    unittest.main()
