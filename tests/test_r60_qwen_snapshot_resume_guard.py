"""CPU-only guard: snapshot diagnosis must never regenerate positions 1–6."""
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1] / "experiments" / "r58_quality"
sys.path.insert(0, str(ROOT))
import r60_qwen_continuous_review as qwen


class ResumeGuardTests(unittest.TestCase):
    def test_empty_output_fails_before_model_initialization(self):
        self.run_invalid_prefix(0)

    def test_five_receipts_fail_before_model_initialization(self):
        self.run_invalid_prefix(5)

    def run_invalid_prefix(self, count):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory)
            for pos in range(1, count + 1):
                (output / f"review_{pos:04d}.private.json").write_text("{}")
            called = []
            worker = SimpleNamespace(
                checkpoint_name=lambda i: f"review_{i:04d}.private.json",
                read_checkpoint=lambda *args: {},
                inference=lambda *args: called.append("inference"),
                write_checkpoint=lambda *args: called.append("write"),
            )
            def refuse_model(*args, **kwargs):
                called.append("GPU")
                raise AssertionError("model must not be initialized")
            hf = SimpleNamespace(from_pretrained=refuse_model)
            vllm = SimpleNamespace(LLM=refuse_model)
            rows = [{} for _ in range(25)]
            with self.assertRaisesRegex(qwen.Hold, "QWEN_SNAPSHOT_RESUME_PREFIX6_HOLD"):
                qwen.run_batches(
                    worker, rows, output, pathlib.Path("/unloaded"),
                    limit=7, batch_size=1, max_model_len=32768,
                    max_output_tokens=2400, wall_seconds=5400,
                    resume=True, hf_tokenizer=hf, vllm=vllm,
                    diagnose_generation=True,
                    generation_snapshot_store=object())
            self.assertEqual(called, [])

if __name__ == "__main__":
    unittest.main()
