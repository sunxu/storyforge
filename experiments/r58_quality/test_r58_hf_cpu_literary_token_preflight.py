import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from r58_hf_cpu_literary_token_preflight import (
    SCHEMA, MODE, HOLD, check_all, save_receipt, verify_reuse,
)
from r58_hf_gpu_literary_reviewer import MODELS, canon
from test_r58_hf_gpu_literary_reviewer import source_rows


class FakeTokenizer:
    chat_template = "PRIVATE_SYNTHETIC_TEMPLATE"
    def __init__(self, length=61):
        self.length = length

    def apply_chat_template(self, messages, **kwargs):
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "target_text" in messages[1]["content"]
        return {"input_ids": [[17] * self.length]}


class HFCPUReviewPreflightTests(unittest.TestCase):
    def stage(self, base):
        source = base / "source.private.jsonl"
        source.write_bytes(b"".join(canon(row) + b"\n" for row in source_rows()))
        source.chmod(0o600)
        output = base / "output"
        output.mkdir(mode=0o700)
        return source, output

    def args(self, source, output, slot="A", model=None, version="4.57.1",
             max_model_len=32768, max_output_tokens=2400):
        return SimpleNamespace(slot=slot, model=model or MODELS[slot],
                               revision="a"*40, input=source, output_dir=output,
                               transformers_version=version,
                               max_model_len=max_model_len,
                               max_output_tokens=max_output_tokens)

    def test_full13_no_gpu_and_safe_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = self.stage(Path(td))
            a = self.args(source, output)
            result = check_all(a, tokenizer_factory=lambda *x, **k: FakeTokenizer(),
                               package_version="4.57.1")
            self.assertEqual(result["schema"], SCHEMA)
            self.assertEqual(result["status"], MODE)
            self.assertEqual(result["cases_checked"], 13)
            self.assertEqual(result["pilot_cases_checked"], 2)
            self.assertEqual(result["remaining_cases_checked"], 11)
            self.assertEqual(result["prompt_tokens_max"], 61)
            self.assertEqual(result["max_total_tokens"], 2461)
            self.assertEqual(result["over_budget_count"], 0)
            self.assertFalse(result["model_weights_loaded"])
            self.assertFalse(result["paid_gpu_submitted"])
            self.assertFalse(result["training_authorized"])
            self.assertEqual(list(output.iterdir()), [])
            save_receipt(output, result)
            path = output / "r58_cpu_preflight_all13_safe.json"
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())["cases_checked"], 13)
            cached = verify_reuse(a)
            self.assertEqual(cached["status"], "R58_HF_CPU_TOKEN_PREFLIGHT_CACHED_PASS__NO_JOB")
            self.assertEqual(cached["cases_checked"], 13)
            self.assertNotIn("private_input_sha256", cached)
            forged = self.args(source, output, max_output_tokens=2500)
            with self.assertRaises(ValueError):
                verify_reuse(forged)
            tampered = json.loads(path.read_text())
            tampered["serialized_prompt_batch_sha256"] = "0" * 64
            path.write_text(json.dumps(tampered))
            with self.assertRaises(ValueError):
                verify_reuse(a)
            path.write_text(json.dumps(result))
            with self.assertRaises(FileExistsError):
                save_receipt(output, result)
            with self.assertRaises(ValueError):
                check_all(a, tokenizer_factory=lambda *x, **k: FakeTokenizer(),
                          package_version="4.57.1")

    def test_b_independent_and_over_budget_hold(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = self.stage(Path(td))
            b = self.args(source, output, slot="B", max_model_len=4096,
                          max_output_tokens=1200)
            result = check_all(b, tokenizer_factory=lambda *x, **k: FakeTokenizer(3000),
                               package_version="4.57.1")
            self.assertEqual(result["status"], HOLD)
            self.assertEqual(result["over_budget_count"], 13)
            self.assertEqual(result["max_total_tokens"], 4200)
            self.assertEqual(result["model"], MODELS["B"])
            self.assertFalse(result["private_text_emitted"])
            self.assertEqual(list(output.iterdir()), [])

    def test_bad_pin_and_version_and_template_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = self.stage(Path(td))
            args = self.args(source, output, slot="B", model=MODELS["A"])
            with self.assertRaises(ValueError):
                check_all(args, tokenizer_factory=lambda *x, **k: FakeTokenizer(),
                          package_version="4.57.1")
            args = self.args(source, output, version="4.57.1")
            with self.assertRaises(ValueError):
                check_all(args, tokenizer_factory=lambda *x, **k: FakeTokenizer(),
                          package_version="4.57.0")
            args = self.args(source, output)
            class BadTemplate(FakeTokenizer):
                chat_template = None
            with self.assertRaises(ValueError):
                check_all(args, tokenizer_factory=lambda *x, **k: BadTemplate(),
                          package_version="4.57.1")

    def test_private_input_failure_has_safe_stage_code(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = self.stage(Path(td))
            rows = source_rows()
            rows[0]["schema"] = "invalid-private-schema"
            source.write_bytes(b"".join(canon(row) + b"\n" for row in rows))
            args = self.args(source, output)
            with self.assertRaisesRegex(
                ValueError, "^PRIVATE_INPUT_SOURCE_UNREVIEWED_CONTRACT_INVALID$"
            ) as caught:
                check_all(args, tokenizer_factory=lambda *x, **k: FakeTokenizer(),
                          package_version="4.57.1")
            self.assertNotIn("invalid-private-schema", str(caught.exception))

    def test_tokenizer_load_failure_has_safe_stage_code(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = self.stage(Path(td))
            args = self.args(source, output)

            def fail_load(*args, **kwargs):
                raise RuntimeError("PRIVATE_TOKENIZER_DETAIL_MUST_NOT_ESCAPE")

            with self.assertRaisesRegex(ValueError, "^TOKENIZER_LOAD_FAILED$") as caught:
                check_all(args, tokenizer_factory=fail_load, package_version="4.57.1")
            self.assertNotIn("PRIVATE_TOKENIZER_DETAIL", str(caught.exception))

    def test_tokenization_failure_has_safe_stage_code(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = self.stage(Path(td))
            args = self.args(source, output)

            class BrokenTokenizer(FakeTokenizer):
                def apply_chat_template(self, messages, **kwargs):
                    raise RuntimeError("PRIVATE_PROMPT_DETAIL_MUST_NOT_ESCAPE")

            with self.assertRaisesRegex(ValueError, "^CHAT_TEMPLATE_RENDER_FAILED_RUNTIME_ERROR$") as caught:
                check_all(args, tokenizer_factory=lambda *x, **k: BrokenTokenizer(),
                          package_version="4.57.1")
            self.assertNotIn("PRIVATE_PROMPT_DETAIL", str(caught.exception))


    def test_template_exception_class_is_propagated_safely(self):
        with tempfile.TemporaryDirectory() as td:
            source, output = self.stage(Path(td))
            args = self.args(source, output)

            class TemplateError(Exception):
                pass

            class BrokenTokenizer(FakeTokenizer):
                def apply_chat_template(self, messages, **kwargs):
                    raise TemplateError("PRIVATE_TEMPLATE_DETAILS_MUST_NOT_ESCAPE")

            with self.assertRaisesRegex(
                ValueError, "^CHAT_TEMPLATE_RENDER_FAILED_CLASS_TEMPLATEERROR$"
            ) as caught:
                check_all(args, tokenizer_factory=lambda *x, **k: BrokenTokenizer(),
                          package_version="4.57.1")
            self.assertNotIn("PRIVATE_TEMPLATE_DETAILS", str(caught.exception))



if __name__ == "__main__":
    unittest.main()
