"""CPU synthetic tests: frozen GLM quote error guards without source leakage."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_quote_raise_probe.py")
spec = importlib.util.spec_from_file_location("r60_quote_probe", SCRIPT)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_finds_membership_versus_structure(tmp_path):
    source = tmp_path / "runner.py"
    source.write_text(
        "def validate_response(result, row):\n"
        "  quotes = result['specific_source_quotes']\n"
        "  if not isinstance(quotes, list):\n"
        "    raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n"
        "  for quote in quotes:\n"
        "    if quote not in row['target_text']:\n"
        "      raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n")
    result = probe.inspect_runner(source)
    assert result["raise_site_count"] == 2
    assert result["direct_quote_error_possible"]
    assert set(result["guard_categories"]) == {
        "TYPE_CHECK", "MEMBERSHIP_OR_TEXT_MATCH"}


def test_does_not_emit_input_or_private_text(tmp_path):
    source = tmp_path / "runner.py"
    source.write_text(
        "def validate_response(result, row):\n"
        "  if '秘密小说文案' not in row['target_text']:\n"
        "    raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n")
    payload = probe.inspect_runner(source)
    assert "秘密小说文案" not in str(payload)
    assert payload["guard_categories"] == ["MEMBERSHIP_OR_TEXT_MATCH"]


def test_invalid_file_fails_closed(tmp_path):
    source = tmp_path / "runner.py"
    source.write_text("this is ???")
    with pytest.raises(probe.ProbeHold, match="RUNNER_PARSE_HOLD"):
        probe.inspect_runner(source)
