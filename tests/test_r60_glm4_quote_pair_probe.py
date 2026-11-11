"""CPU tests: only literal field-body pairs, never inferred cross-field mixture."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_quote_pair_probe.py")
spec = importlib.util.spec_from_file_location("r60_glm_quote_pair", SOURCE)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_separate_paired_scopes(tmp_path):
    path = tmp_path / "runner.py"
    path.write_text(
        "def validate_response(response,row):\n"
        " history=row['visible_history']\n"
        " bodies=[x['content'] for x in history]\n"
        " goal=row['target_text']\n"
        " for field,corpus in (('specific_source_quotes',bodies),"
        "('specific_target_quotes',[goal])):\n"
        "  if not any(quote in text for text in corpus):\n"
        "   raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n")
    result = probe.inspect_runner(path)
    assert result["pair_count"] == 2
    assert result["pairings"][0]["candidate_body_scope"] == "HISTORY"
    assert result["pairings"][1]["candidate_body_scope"] == "TARGET_TEXT"
    assert result["status"] == "QUOTE_PAIR_CPU_PASS"


def test_no_literal_pair_is_unknown(tmp_path):
    path = tmp_path / "runner.py"
    path.write_text(
        "def validate_response(response,row):\n"
        " if not any(q in content for q in response['specific_source_quotes']):\n"
        "  raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n")
    result = probe.inspect_runner(path)
    assert result["pairings"] == []
    assert not result["source_pair_found"]


def test_never_exposes_private_values(tmp_path):
    path = tmp_path / "runner.py"
    path.write_text(
        "def validate_response(response,row):\n"
        " secret='PRIVATE_STORY_BODY'\n"
        " for a,b in [('specific_source_quotes',[secret])]:\n"
        "  raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n")
    result = probe.inspect_runner(path)
    assert "PRIVATE_STORY_BODY" not in str(result)


def test_invalid_input_is_fail_closed(tmp_path):
    path = tmp_path / "runner.py"
    path.write_text("this is ???")
    with pytest.raises(probe.ProbeHold, match="RUNNER_PARSE_HOLD"):
        probe.inspect_runner(path)
