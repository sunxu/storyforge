"""Synthetic tests for static, no-import reject predicate probe."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "experiments/r58_quality/r60_glm_reject_gate_ast_probe.py"
spec = importlib.util.spec_from_file_location("r60_glm_reject_ast", FILE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_reject_scan_static_and_no_execute(tmp_path):
    runner = tmp_path / "runner.py"
    runner.write_text(
        "raise AssertionError('must never import')\n"
        "def validate_response(row):\n"
        "    if row.get('flag') == 'REJECT':\n"
        "        return 'REJECT'\n"
        "    return 'PASS'\n"
        "def checkpoint_record():\n"
        "    return 'REJECT'\n",
        encoding="utf-8")
    result = mod.check(runner)
    assert result["status"] == "GLM_REJECT_GATE_AST_PASS"
    assert result["runner_imported"] is False
    assert result["gpu_started"] is False
    assert result["private_values_emitted"] is False
    assert len(result["functions"]) == 2
    assert result["functions"][0]["reject_literal_sites"] == 2
    assert result["functions"][0]["reject_scope_predicates"][0]["comparators"] == ["EQ"]


def test_missing_runner_fail_closed(tmp_path):
    try:
        mod.check(tmp_path / "nonexistent.py")
    except ValueError as exc:
        assert str(exc) == "RUNNER_SCOPE_HOLD"
    else:
        raise AssertionError("expected HOLD")
