import json
from pathlib import Path
import tempfile
import unittest

from r58_hf_gpu_review_stage import stage, refresh_code, BUNDLED_CODE
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
                for filename, source_code in BUNDLED_CODE.items():
                    self.assertEqual((inp / filename).stat().st_mode & 0o777, 0o600)
                    self.assertEqual((inp / filename).read_bytes(), source_code.read_bytes())
                self.assertEqual(len(read_source(inp / "source.private.jsonl")), 13)
                self.assertNotIn("owner_crosswalk.private.json",
                                 [x.name for x in inp.iterdir()])
                self.assertNotIn(f"reviewer_{'B' if slot == 'A' else 'A'}.private.jsonl",
                                 [x.name for x in inp.iterdir()])
            with self.assertRaises(ValueError):
                stage(pilot, work, root / "repo")

    def test_refresh_existing_stage_only_updates_code(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pilot = root / "private"
            pilot.mkdir(mode=0o700)
            for slot in ("A", "B"):
                records = source_rows()
                for i, row in enumerate(records):
                    row["blind_id"] = f"{slot}_{i}"
                item = pilot / f"reviewer_{slot}.private.jsonl"
                item.write_bytes(b"".join(canon(x) + b"\\n" for x in records))
                item.chmod(0o600)
            crosswalk = pilot / "owner_crosswalk.private.json"
            crosswalk.write_text('{"private": true}')
            crosswalk.chmod(0o600)
            work = pilot / "stage"
            stage(pilot, work, root / "repo")
            before = {slot: (work / f"input_{slot}" / "source.private.jsonl").read_bytes()
                      for slot in ("A", "B")}
            for slot in ("A", "B"):
                (work / f"output_{slot}" / "r58_rw_probe.txt").write_text("HF RW OK")
            stale = work / "input_A" / "runner.py"
            stale.write_text("OLD_VERSION")
            receipt = refresh_code(pilot, work, root / "repo")
            self.assertEqual(receipt["status"],
                             "R58_A_B_PRIVATE_CODE_REFRESHED__SOURCES_UNCHANGED")
            self.assertEqual(receipt["code_files_updated"], 1)
            self.assertEqual(stale.read_bytes(), BUNDLED_CODE["runner.py"].read_bytes())
            for slot in ("A", "B"):
                self.assertEqual((work / f"input_{slot}" / "source.private.jsonl").read_bytes(),
                                 before[slot])
                self.assertEqual((work / f"output_{slot}" / "r58_rw_probe.txt").read_text(),
                                 "HF RW OK")
            again = refresh_code(pilot, work, root / "repo")
            self.assertEqual(again["code_files_updated"], 0)
            (work / "output_A" / "checkpoint_00.private.json").write_text("{}")
            with self.assertRaises(ValueError):
                refresh_code(pilot, work, root / "repo")

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
