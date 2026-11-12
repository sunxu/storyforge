"""CPU static tracing proves which frozen runner calls the quote hook."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_runner_route_probe.py")
spec = importlib.util.spec_from_file_location("r60_route_probe", MODULE)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_checkpoint_hook_reachable(tmp_path):
    runner = tmp_path / "runner.py"
    runner.write_text(
        "class QuoteValidationError(Exception): pass\n"
        "def validate_response(response, row): pass\n"
        "def checkpoint_record(*args): return validate_response({}, {})\n"
        "def repair_generated_quotes(*args): pass\n"
        "def inference(*args):\n"
        "    try: checkpoint_record(*args)\n"
        "    except QuoteValidationError: repair_generated_quotes(*args)\n"
    )
    result = probe.inspect_runner(runner)
    assert result["old_checkpoint_record_hook_reachable"] is True
    assert result["checks"]["inference_calls_repair_generated_quotes"]
    assert result["checks"]["has_quote_validation_error_class"]


def test_checkpoint_hook_not_reachable(tmp_path):
    runner = tmp_path / "runner.py"
    runner.write_text(
        "def validate_response(result, row): pass\n"
        "def inference(*args): validate_response({}, {})\n"
    )
    result = probe.inspect_runner(runner)
    assert result["old_checkpoint_record_hook_reachable"] is False
    assert result["checks"]["inference_calls_validate_response"]
    assert result["recommended_next_step"] == (
        "OLD_CHECKPOINT_RECORD_HOOK_CANNOT_OBSERVE_INFERENCE")


def test_broken_runner_rejected_without_source_leak(tmp_path):
    runner = tmp_path / "runner.py"
    runner.write_text("secret payload")
    with pytest.raises(probe.ProbeHold, match="RUNNER_PARSE_HOLD"):
        probe.inspect_runner(runner)
