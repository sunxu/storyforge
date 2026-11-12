"""CPU-only regression for Qwen reviewer-stage SAFE tracing."""
import importlib.util
import pathlib
import unittest
from types import SimpleNamespace

MODULE = pathlib.Path(__file__).resolve().parents[1] / "experiments" / "r58_quality" / "r60_qwen_guidance_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("r60_qwen_guidance_diagnostic", MODULE)
diagnostic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostic)


class QwenReviewerTraceTests(unittest.TestCase):
    def test_success_and_original_identity_restored(self):
        events = []
        worker = SimpleNamespace(
            validate_response=lambda secret: "ok",
            repair_generated_quotes=lambda secret: "fixed",
            write_checkpoint=lambda secret: "saved",
        )
        old = (worker.validate_response, worker.repair_generated_quotes,
               worker.write_checkpoint)
        with diagnostic.trace_reviewer_stages(
                worker, lambda event, **kw: events.append((event, kw))):
            self.assertEqual(worker.validate_response("private"), "ok")
            self.assertEqual(worker.repair_generated_quotes("private"), "fixed")
            self.assertEqual(worker.write_checkpoint("private"), "saved")
        self.assertEqual(
            [e[0] for e in events],
            ["VALIDATE_RESPONSE_START", "VALIDATE_RESPONSE_PASS",
             "QUOTE_REPAIR_START", "QUOTE_REPAIR_PASS",
             "CHECKPOINT_WRITE_START", "CHECKPOINT_WRITE_PASS"])
        self.assertTrue(all(not fields for _, fields in events))
        self.assertEqual(old, (worker.validate_response,
                               worker.repair_generated_quotes,
                               worker.write_checkpoint))

    def test_failure_is_rethrown_and_private_message_never_emitted(self):
        events = []
        class SecretFailure(ValueError):
            pass
        def fail(secret):
            raise SecretFailure("PRIVATE_TOKEN_DO_NOT_EMIT")
        worker = SimpleNamespace(validate_response=fail)
        with (self.assertRaisesRegex(SecretFailure, "PRIVATE_TOKEN"),
              diagnostic.trace_reviewer_stages(
                  worker, lambda event, **kw: events.append((event, kw)))):
            worker.validate_response("private")
        self.assertIs(worker.validate_response, fail)
        self.assertEqual(events, [
            ("VALIDATE_RESPONSE_START", {}),
            ("VALIDATE_RESPONSE_FAILURE",
             {"exception_class": "SecretFailure"}),
        ])
        self.assertNotIn("PRIVATE_TOKEN", str(events))

    def test_missing_optional_functions_are_unchanged(self):
        worker = SimpleNamespace()
        with diagnostic.trace_reviewer_stages(worker, lambda *a, **kw: None):
            pass
        self.assertEqual(vars(worker), {})


if __name__ == "__main__":
    unittest.main()
