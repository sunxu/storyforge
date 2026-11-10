"""CPU-only tests for HF pilot diagnostic launcher (never import vLLM)."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "experiments/r58_quality/r60_pilot_diagnostic_launcher.py"


def test_diagnostics_keep_original_runner_and_emit_safe_checkpoints(tmp_path):
    source = tmp_path / "runner.py"
    source.write_text(
        "def read_input(path):\n"
        "    return [1, 2]\n"
        "def write_checkpoint(path, record):\n"
        "    return None\n"
        "def inference(rows):\n"
        "    write_checkpoint('PRIVATE_PATH', {'secret':'PRIVATE_CONTENT'})\n"
        "    return {'cases_total':2,'cases_completed':1}\n"
        "def main():\n"
        "    rows=read_input('PRIVATE_PATH')\n"
        "    inference(rows)\n"
        "    return 0\n"
    )
    wrapper = tmp_path / LAUNCHER.name
    wrapper.write_bytes(LAUNCHER.read_bytes())
    baseline = source.read_bytes()
    proc = subprocess.run([sys.executable, "-u", str(wrapper)],
                          capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0
    assert '"event":"BOOT"' in proc.stdout
    assert '"event":"INPUT_VERIFIED"' in proc.stdout
    assert '"event":"INFERENCE_ENTER"' in proc.stdout
    assert '"event":"CHECKPOINT_WRITTEN"' in proc.stdout
    assert '"event":"INFERENCE_SUMMARY"' in proc.stdout
    assert '"event":"RUNNER_EXIT"' in proc.stdout
    assert "PRIVATE_PATH" not in proc.stdout
    assert "PRIVATE_CONTENT" not in proc.stdout
    assert source.read_bytes() == baseline


def test_missing_runner_returns_safe_hold(tmp_path):
    wrapper = tmp_path / LAUNCHER.name
    wrapper.write_bytes(LAUNCHER.read_bytes())
    proc = subprocess.run([sys.executable, str(wrapper)],
                          capture_output=True, text=True, timeout=15)
    assert proc.returncode == 42
    assert "RUNNER_NOT_REGULAR" in proc.stdout


def test_exception_content_not_leaked(tmp_path):
    wrapper = tmp_path / LAUNCHER.name
    wrapper.write_bytes(LAUNCHER.read_bytes())
    (tmp_path / "runner.py").write_text("raise RuntimeError('PRIVATE_CONTENT')\n")
    proc = subprocess.run([sys.executable, str(wrapper)],
                          capture_output=True, text=True, timeout=15)
    assert proc.returncode == 42
    assert "PRIVATE_CONTENT" not in proc.stdout
    assert "RUNTIME_EXCEPTION_REDACTED" in proc.stdout


def test_trace_markers_are_allowlisted_and_callback_present(tmp_path):
    """Synthetic traced runner exposes only stage labels, not private args."""
    source = tmp_path / "runner.py"
    source.write_text(
        "def read_input(path):\n"
        "    return [1]\n"
        "def write_checkpoint(path, record):\n"
        "    return None\n"
        "def inference(rows):\n"
        "    _r60_diag_event('TOKENIZER_LOAD_START')\n"
        "    _r60_diag_event('TOKENIZER_LOADED')\n"
        "    _r60_diag_event('ENGINE_INIT_START')\n"
        "    _r60_diag_event('ENGINE_READY')\n"
        "    _r60_diag_event('GENERATE_START')\n"
        "    _r60_diag_event('GENERATE_DONE')\n"
        "    write_checkpoint('private', {'value': 'PRIVATE_SECRET'})\n"
        "    return {'cases_total':1,'cases_completed':1}\n"
        "def main():\n"
        "    inference(read_input('private'))\n"
        "    return 0\n"
    )
    wrapper = tmp_path / LAUNCHER.name
    wrapper.write_bytes(LAUNCHER.read_bytes())
    proc = subprocess.run([sys.executable, "-u", str(wrapper)],
                          capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0
    for stage in ("TOKENIZER_LOAD_START", "TOKENIZER_LOADED",
                  "ENGINE_INIT_START", "ENGINE_READY", "GENERATE_START",
                  "GENERATE_DONE"):
        assert f'"stage":"{stage}"' in proc.stdout
    assert "PRIVATE_SECRET" not in proc.stdout
