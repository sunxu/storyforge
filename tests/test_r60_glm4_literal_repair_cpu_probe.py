"""CPU fixtures: the GLM private-runner diagnostic must report bounded reasons."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1] / "experiments/r58_quality"
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location(
    "r60_glm4_literal_integration_test", BASE / "r60_glm4_literal_repair_cpu_probe.py")
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_synthetic_quote_is_real_exact_substring_and_distinct():
    body = "他推开房门，屋内空无一人。夜里风很冷，窗外还在下雨。"
    exact, broken = probe.synthetic_punctuation_case(body)
    assert exact in body
    assert broken not in body
    assert exact != broken
    assert exact[:-1] == broken[:-1]
    assert probe.reconcile_quote(broken, [body]) == exact


def test_missing_valid_quote_fails_with_bounded_reason():
    with pytest.raises(probe.ProbeHold,
                       match="SYNTHETIC_NO_UNIQUE_PUNCTUATION_CANDIDATE_HOLD"):
        probe.synthetic_punctuation_case("这一整行没有任何标点符号" * 20)


def _fake_frozen(tmp_path, monkeypatch):
    runner = tmp_path / "runner.py"
    source = tmp_path / "source.private.jsonl"
    row = {
        "visible_history": [{"content": "她站在房间中央，静静听着远处的雨声。"}],
        "target_text": "他推开房门，屋内空无一人。夜里风很冷，窗外还在下雨。",
    }
    source.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(probe, "INPUT_SHA", hashlib.sha256(source.read_bytes()).hexdigest())
    runner.write_text(
        "import hashlib, json\n"
        "class ReviewError(ValueError): pass\n"
        "def validate_input(row):\n"
        "    assert len(row['visible_history']) == 1\n"
        "def response_schema():\n"
        "    return {'properties': {'scores': {'properties': {'chinese_prose': {}}},"
        " 'severe_flags': {'properties': {'serious_player_agency': {}}}}}\n"
        "def validate_response(response, row):\n"
        "    for field, bodies in (('specific_source_quotes',"
        " [x['content'] for x in row['visible_history']]),"
        " ('specific_target_quotes', [row['target_text']])):\n"
        "        for quote in response[field]:\n"
        "            if not any(quote in body for body in bodies):\n"
        "                raise ReviewError('MODEL_NONEXACT_QUOTE_HOLD')\n"
        "    return response['decision']\n"
        "def checkpoint_record(position,row,response,model,revision):\n"
        "    validate_response(response,row)\n"
        "    return {'position': position, 'response': response}\n",
        encoding="utf-8")
    return runner, source


def test_frozen_runner_cpu_integration_passes_with_synthetic_input(tmp_path, monkeypatch):
    runner, source = _fake_frozen(tmp_path, monkeypatch)
    result = probe.inspect(runner, source)
    assert result["status"] == "GLM_LITERAL_FROZEN_CPU_INTEGRATION_PASS"
    assert result["punctuation_repair_revalidated"] is True
    assert result["original_response_modified"] is False
    assert result["gpu_started"] is False
    assert "雨声" not in str(result)


def test_fail_closed_on_wrong_sha(tmp_path, monkeypatch):
    runner, source = _fake_frozen(tmp_path, monkeypatch)
    monkeypatch.setattr(probe, "INPUT_SHA", "0" * 64)
    with pytest.raises(probe.ProbeHold, match="SOURCE_SHA_HOLD"):
        probe.inspect(runner, source)


def test_only_bounded_reason_names_are_advertised():
    assert "UNEXPECTED_PRIVATE_REDACTED_HOLD" not in probe.SAFE_REASONS
    assert all(reason.isupper() and " " not in reason
               for reason in probe.SAFE_REASONS)
