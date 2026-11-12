"""CPU-only tests for literal-free frozen GLM quote semantics inspection."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_quote_semantics_probe.py")
spec = importlib.util.spec_from_file_location("quote_semantics", SOURCE)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_membership_guard_from_target_and_source(tmp_path):
    runner = tmp_path / "runner.py"
    runner.write_text(
        "def validate_response(result, row):\n"
        "    histories = [x['content'] for x in row['visible_history']]\n"
        "    for quote in result['specific_source_quotes']:\n"
        "        if not any(quote in body for body in histories):\n"
        "            raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n"
    )
    result = probe.inspect(runner)
    assert result["status"] == "QUOTE_SEMANTICS_CPU_PASS"
    assert result["site"]["guard_kind"] == "MEMBERSHIP"
    assert result["site"]["uses_any"]
    assert result["site"]["uses_not"]
    assert "visible_history" in result["validator_field_references"]
    assert "specific_source_quotes" in result["validator_field_references"]
    assert result["site"]["membership_predicates"][0]["left_role"] == "QUOTED_ITEM"


def test_private_literals_not_revealed(tmp_path):
    runner = tmp_path / "runner.py"
    runner.write_text(
        "def validate_response(result, row):\n"
        "    if '秘密作品内容' not in row['target_text']:\n"
        "        raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n"
    )
    result = probe.inspect(runner)
    assert "秘密作品内容" not in str(result)
    assert result["site"]["membership_predicates"][0]["operator"] == "NOT_IN"


def test_multiple_raise_sites_fail_closed(tmp_path):
    runner = tmp_path / "runner.py"
    runner.write_text(
        "def validate_response(result, row):\n"
        "    if not quote in target:\n"
        "        raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n"
        "    if not source in target:\n"
        "        raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n"
    )
    with pytest.raises(probe.ProbeHold, match="UNEXPECTED_QUOTE_RAISE_SITES_HOLD"):
        probe.inspect(runner)
