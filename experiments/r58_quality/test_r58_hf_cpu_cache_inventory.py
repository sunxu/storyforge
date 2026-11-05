"""Synthetic-only tests: no HF, network, model tokenizer or private user files."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from r58_hf_cpu_cache_inventory import inspect, RECEIPT_NAME
from r58_hf_cpu_literary_token_preflight import check_all, save_receipt
from r58_hf_gpu_literary_reviewer import MODELS, canon
from test_r58_hf_cpu_literary_token_preflight import FakeTokenizer
from test_r58_hf_gpu_literary_reviewer import source_rows


class CacheInventoryTests(unittest.TestCase):
    def make_stage(self, td):
        stage = Path(td) / "stage"
        stage.mkdir(mode=0o700)
        for slot in ("A", "B"):
            inp = stage / f"input_{slot}"
            out = stage / f"output_{slot}"
            inp.mkdir(mode=0o700)
            out.mkdir(mode=0o700)
            rows = source_rows()
            for i, row in enumerate(rows):
                row["blind_id"] = f"{slot}_{i}"
            source = inp / "source.private.jsonl"
            source.write_bytes(b"".join(canon(x) + b"\n" for x in rows))
            source.chmod(0o600)
        return stage

    def populate(self, stage, slot="A"):
        source = stage / f"input_{slot}" / "source.private.jsonl"
        out = stage / f"output_{slot}"
        args = SimpleNamespace(
            slot=slot, model=MODELS[slot], revision="a" * 40,
            input=source, output_dir=out,
            transformers_version="4.57.1", max_model_len=32768,
            max_output_tokens=2400,
        )
        receipt = check_all(
            args, tokenizer_factory=lambda *a, **kw: FakeTokenizer(),
            package_version="4.57.1",
        )
        save_receipt(out, receipt)
        return out / RECEIPT_NAME

    def planned(self, stage, **overrides):
        # Planned values are independent of the receipt under inspection.
        params = {
            "revisions": {"A": "a" * 40, "B": "a" * 40},
            "transformers_versions": {"A": "4.57.1", "B": "4.57.1"},
            "max_model_len": 32768,
            "reserved_output_tokens": 2400,
        }
        params.update(overrides)
        return inspect(stage, **params)

    def test_no_receipts_reports_missing_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            result = inspect(stage)
            self.assertEqual(result["counts"]["MISSING"], 2)
            self.assertEqual(result["counts"]["HOLD"], 0)
            self.assertFalse(result["hf_origin_proven"])
            self.assertFalse(result["hf_job_submitted"])

    def test_matching_receipt_still_unverified_origin(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            self.populate(stage, "A")
            result = self.planned(stage)
            self.assertEqual(result["slots"]["A"], "LOCAL_MATCH_ORIGIN_UNVERIFIED")
            self.assertEqual(result["slots"]["B"], "MISSING")
            self.assertFalse(result["gpu_runtime_equivalence_proven"])
            self.assertNotIn(str(stage), json.dumps(result))
            self.assertNotIn("private_input_sha256", json.dumps(result))

    def test_corrupted_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            path = self.populate(stage, "B")
            raw = json.loads(path.read_text())
            raw["reserved_output_tokens"] = 2401
            path.write_text(json.dumps(raw))
            result = self.planned(stage)
            self.assertEqual(result["slots"]["B"], "HOLD")
            self.assertEqual(result["status"], "R58_CPU_CACHE_INVENTORY_HOLD")

    def test_malformed_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            target = stage / "output_A" / RECEIPT_NAME
            target.write_text("not json")
            target.chmod(0o600)
            self.assertEqual(self.planned(stage)["slots"]["A"], "HOLD")

    def test_symlink_or_unsafe_mode_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            receipt = self.populate(stage, "A")
            receipt.chmod(0o644)
            self.assertEqual(self.planned(stage)["slots"]["A"], "HOLD")
            receipt.unlink()
            receipt.symlink_to(stage / "input_A" / "source.private.jsonl")
            self.assertEqual(self.planned(stage)["slots"]["A"], "HOLD")

    def test_receipt_cannot_supply_its_own_expected_pins(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            self.populate(stage, "A")
            self.assertEqual(inspect(stage)["slots"]["A"], "HOLD")
            self.assertEqual(inspect(stage)["slots"]["B"], "MISSING")

    def test_wrong_independent_revision_or_runtime_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            self.populate(stage, "A")
            wrong_revision = self.planned(
                stage, revisions={"A": "b" * 40, "B": "a" * 40})
            self.assertEqual(wrong_revision["slots"]["A"], "HOLD")
            wrong_runtime = self.planned(
                stage, transformers_versions={"A": "4.57.0", "B": "4.57.1"})
            self.assertEqual(wrong_runtime["slots"]["A"], "HOLD")

    def test_tampered_context_length_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            stage = self.make_stage(td)
            receipt = self.populate(stage, "A")
            raw = json.loads(receipt.read_text())
            raw["max_model_len"] = 32769
            receipt.write_text(json.dumps(raw))
            self.assertEqual(self.planned(stage)["slots"]["A"], "HOLD")



if __name__ == "__main__":
    unittest.main()
