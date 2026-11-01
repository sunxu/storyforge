import json
from pathlib import Path
import tempfile
import unittest

from r58_hf_gpu_review_stage import stage
from r58_hf_gpu_literary_reviewer import canon, read_source
from test_r58_hf_gpu_literary_reviewer import source_rows


class StageSafetyTests(unittest.TestCase):
    def test_staging_separates_slots_and_crosswalk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pilot = root / "private"
            pilot.mkdir(mode=0o700)
            for slot in ("A", "B"):
                rows = source_rows()
                for i, row in enumerate(rows):
                    row["blind_id"] = f"{slot}_{i}"
                path = pilot / f"reviewer_{slot}.private.jsonl"
                path.write_bytes(b"".join(canon(x) + b"\n" for x in rows))
                path.chmod(0o600)
            owner = pilot / "owner_crosswalk.private.json"
            owner.write_text(json.dumps({"private_owner": "must-never-be-copied"}))
            owner.chmod(0o600)
            work = pilot / "gpu-work"
            receipt = stage(pilot, work, root / "repo")
            self.assertEqual(receipt["slots"], 2)
            self.assertEqual(receipt["cases_per_slot"], 13)
            self.assertFalse(receipt["paid_gpu_submitted"])
            self.assertFalse(receipt["owner_crosswalk_uploaded"])
            for slot in ("A", "B"):
                inp = work / f"input_{slot}"
                out = work / f"output_{slot}"
                self.assertEqual(inp.stat().st_mode & 0o777, 0o700)
                self.assertEqual(out.stat().st_mode & 0o777, 0o700)
                self.assertEqual(
                    (inp / "source.private.jsonl").stat().st_mode & 0o777, 0o600
                )
                self.assertEqual((inp / "runner.py").stat().st_mode & 0o777, 0o600)
                self.assertEqual(len(read_source(inp / "source.private.jsonl")), 13)
                self.assertNotIn("owner_crosswalk.private.json",
                                 [x.name for x in inp.iterdir()])
                self.assertNotIn(f"reviewer_{'B' if slot == 'A' else 'A'}.private.jsonl",
                                 [x.name for x in inp.iterdir()])
            with self.assertRaises(ValueError):
                stage(pilot, work, root / "repo")

    def test_missing_owner_crosswalk_is_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pilot = root / "pilot"
            pilot.mkdir(mode=0o700)
            for slot in ("A", "B"):
                rows = source_rows()
                for i, row in enumerate(rows):
                    row["blind_id"] = f"{slot}_{i}"
                p = pilot / f"reviewer_{slot}.private.jsonl"
                p.write_bytes(b"".join(canon(x) + b"\n" for x in rows))
                p.chmod(0o600)
            with self.assertRaises(ValueError):
                stage(pilot, pilot / "work", root / "repo")


if __name__ == "__main__":
    unittest.main()
