import copy
import json
from pathlib import Path
import tempfile
import unittest

from r58_gold195_blind_quality_pilot13 import (
    CROSSWALK_SCHEMA, PILOT_SCHEMA, prepare, select_world_pilot,
    safe_preflight,
)
from gold195_six_dimension_review_tasks import prepare_row
from test_gold195_six_dimension_review_tasks import example


class Gold195BlindPilot13Tests(unittest.TestCase):
    def source(self):
        rows = []
        for i in range(195):
            r = example(i, leading=(i % 3 != 0))
            r["story_uuid"] = f"private_world_{i % 13}"
            rows.append(r)
        return rows

    def test_representative_by_world_and_never_train(self):
        prepared = [prepare_row(x)[0] for x in self.source()]
        chosen = select_world_pilot(prepared)
        self.assertEqual(len(chosen), 13)
        self.assertEqual(len({r["story_uuid"] for r in chosen}), 13)
        for r in chosen:
            self.assertFalse(r["training_authorized"])
            self.assertFalse(r["quality_v1_admitted"])
            self.assertIsNone(r["split"])
            self.assertEqual(r["review_status"], "UNREVIEWED")

    def test_two_independent_blind_packets_and_crosswalk(self):
        with tempfile.TemporaryDirectory() as td:
            private = Path(td) / "private"
            private.mkdir(mode=0o700)
            source = private / "source.jsonl"
            source.write_text("\n".join(json.dumps(x, ensure_ascii=False)
                                        for x in self.source()) + "\n")
            source.chmod(0o600)
            out = private / "blind_pilot13"
            receipt = prepare(source, out, Path(td) / "repo")
            self.assertEqual(receipt["source_rows_checked"], 195)
            self.assertEqual(receipt["pilot_cases"], 13)
            self.assertEqual(receipt["reviewer_cases_each"], 13)
            self.assertEqual(receipt["quality_v1_admitted"], 0)
            self.assertFalse(receipt["training_authorized"])
            self.assertEqual((out.stat().st_mode & 0o777), 0o700)

            a = [json.loads(l) for l in
                 (out / "reviewer_A.private.jsonl").read_text().splitlines()]
            b = [json.loads(l) for l in
                 (out / "reviewer_B.private.jsonl").read_text().splitlines()]
            owner = json.loads((out / "owner_crosswalk.private.json").read_text())
            self.assertEqual(owner["schema"], CROSSWALK_SCHEMA)
            self.assertEqual(len(owner["selected"]), 13)
            self.assertEqual(len(a), 13)
            self.assertEqual(len(b), 13)
            ids_a = {x["blind_id"] for x in a}
            ids_b = {x["blind_id"] for x in b}
            self.assertFalse(ids_a & ids_b)
            self.assertEqual(ids_a, {x["reviewer_a_blind_id"] for x in owner["selected"]})
            self.assertEqual(ids_b, {x["reviewer_b_blind_id"] for x in owner["selected"]})
            for record in a + b:
                self.assertEqual(record["schema"], PILOT_SCHEMA)
                self.assertNotIn("source_case_id", record)
                self.assertNotIn("story_uuid", record)
                self.assertEqual(record["response"]["decision"], None)
                self.assertTrue(all(v is None for v in
                                    record["response"]["scores"].values()))
                self.assertFalse(record["training_authorized"])
                self.assertFalse(record["quality_v1_admitted"])
            for name in ("reviewer_A.private.jsonl",
                         "reviewer_B.private.jsonl", "owner_crosswalk.private.json"):
                self.assertEqual((out / name).stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                prepare(source, out, Path(td) / "repo")

    def test_safe_diagnostic_identifies_missing_input_and_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            private = Path(td) / "private"
            private.mkdir(mode=0o700)
            output = private / "new-output"
            absent = private / "missing.jsonl"
            report = safe_preflight(absent, output, Path(td) / "repo")
            self.assertEqual(report["reason_code"],
                             "PRIVATE_INPUT_NOT_FOUND_OR_PATH_INVALID")
            source = private / "source.jsonl"
            source.write_text("\\n".join(json.dumps(x, ensure_ascii=False)
                                         for x in self.source()) + "\\n")
            source.chmod(0o644)
            report = safe_preflight(source, output, Path(td) / "repo")
            self.assertEqual(report["reason_code"], "PRIVATE_INPUT_PERMISSIONS_INVALID")
            source.chmod(0o600)
            report = safe_preflight(source, output, Path(td) / "repo")
            self.assertEqual(report["reason_code"], "READY")
            self.assertEqual(report["review_tasks_prepared"], 195)
            self.assertEqual(report["source_world_count"], 13)
            self.assertTrue(report["no_output_written"])
            self.assertFalse(output.exists())
            output.mkdir()
            report = safe_preflight(source, output, Path(td) / "repo")
            self.assertEqual(report["reason_code"], "OUTPUT_ALREADY_EXISTS")

    def test_safe_diagnostic_rejects_incomplete_without_echoing_text(self):
        with tempfile.TemporaryDirectory() as td:
            private = Path(td) / "private"
            private.mkdir(mode=0o700)
            source = private / "source.jsonl"
            rows = self.source()
            rows[2]["original_history"][0]["role"] = "system"
            source.write_text("\\n".join(json.dumps(x, ensure_ascii=False)
                                         for x in rows) + "\\n")
            source.chmod(0o600)
            report = safe_preflight(source, private / "output", Path(td) / "repo")
            self.assertEqual(report["reason_code"], "REVIEW_TASKS_INCOMPLETE")
            self.assertEqual(report["source_rows_checked"], 195)
            self.assertEqual(report["review_tasks_prepared"], 194)
            self.assertNotIn("PRIVATE_", json.dumps(report))
            self.assertFalse((private / "output").exists())

    def test_unresolved_and_duplicate_worlds_do_not_pass(self):
        prepared = [prepare_row(r)[0] for r in self.source()]
        fake = copy.deepcopy(prepared)
        fake[0]["split"] = "train"
        with self.assertRaises(ValueError):
            select_world_pilot(fake)
        fake = copy.deepcopy(prepared)
        fake[0]["story_uuid"] = "world-14"
        with self.assertRaises(ValueError):
            select_world_pilot(fake)


if __name__ == "__main__":
    unittest.main()
