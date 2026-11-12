"""CPU-only regression tests for frozen quote binding provenance."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_quote_binding_probe.py")
spec = importlib.util.spec_from_file_location("glm4_binding_probe", SOURCE)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def _write(tmp_path, content):
    path = tmp_path / "runner.py"
    path.write_text(content)
    return path


def test_history_alias_in_generator(tmp_path):
    path = _write(tmp_path, """
def validate_response(response, row):
    history = row["visible_history"]
    bodies = [entry["content"] for entry in history]
    for quote in response["specific_source_quotes"]:
        if not any(quote in text for text in bodies):
            raise ReviewError("MODEL_NONEXACT_QUOTE_HOLD")
""")
    result = probe.inspect_runner(path)
    assert result["status"] == "QUOTE_BINDING_CPU_PASS"
    assert result["membership"][0]["right_scope"] == "HISTORY_OR_MESSAGE"
    assert "VISIBLE_HISTORY" in result["membership"][0]["right_provenance"]
    assert result["uses_any"] and result["uses_negation"]


def test_target_alias_in_generator(tmp_path):
    path = _write(tmp_path, """
def validate_response(response, row):
    expected = row["target_text"]
    snippets = [expected]
    if not any(quote in candidate for quote in response["specific_target_quotes"] for candidate in snippets):
        raise ReviewError("MODEL_NONEXACT_QUOTE_HOLD")
""")
    result = probe.inspect_runner(path)
    assert result["membership"][0]["right_scope"] == "TARGET_TEXT"


def test_unknown_alias_not_invented(tmp_path):
    path = _write(tmp_path, """
def validate_response(response, row):
    if not any(quote in arbitrary_var for quote in response["specific_source_quotes"]):
        raise ReviewError("MODEL_NONEXACT_QUOTE_HOLD")
""")
    result = probe.inspect_runner(path)
    assert result["membership"][0]["right_scope"] == "UNKNOWN"


def test_never_echoes_private_literal(tmp_path):
    path = _write(tmp_path, """
def validate_response(response, row):
    expected = "PRIVATE_FICTION_TEXT"
    if not any(quote in expected for quote in response["specific_source_quotes"]):
        raise ReviewError("MODEL_NONEXACT_QUOTE_HOLD")
""")
    result = probe.inspect_runner(path)
    assert "PRIVATE_FICTION_TEXT" not in str(result)


def test_malformed_source_holds(tmp_path):
    path = _write(tmp_path, "this is ???")
    with pytest.raises(probe.ProbeHold, match="RUNNER_PARSE_HOLD"):
        probe.inspect_runner(path)
