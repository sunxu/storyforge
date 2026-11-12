"""CPU-only P0 diagnosis: exact Guidance API + private-safe stage boundaries."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_qwen_guidance_diagnostic.py")
spec = importlib.util.spec_from_file_location("r60_guidance_diagnostic", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_cpu_probe_success_and_no_gpu(capsys):
    calls = []
    def guided(**kwargs):
        calls.append(("guided", kwargs["backend"]))
        return "guidance-config"
    def sampling(**kwargs):
        calls.append(("sampling", kwargs["guided_decoding"]))
        return object()
    worker = SimpleNamespace(response_schema=lambda: {"type": "object"})
    mod.cpu_guidance_probe(
        worker, SimpleNamespace(SamplingParams=sampling),
        SimpleNamespace(GuidedDecodingParams=guided), mod.emit_safe)
    assert calls == [("guided", "guidance"), ("sampling", "guidance-config")]
    assert "GUIDANCE_CPU_SAMPLING_PARAMS_PASS" in capsys.readouterr().out


def test_cpu_probe_valueerror_fails_before_gpu_without_private_text(capsys):
    def bad_sampling(**kwargs):
        raise ValueError("private source must not appear")
    worker = SimpleNamespace(response_schema=lambda: {"type": "object"})
    guided = SimpleNamespace(GuidedDecodingParams=lambda **kw: object())
    with pytest.raises(mod.DiagnosticHold, match="GUIDANCE_SAMPLING_PARAMS_API_HOLD"):
        mod.cpu_guidance_probe(
            worker, SimpleNamespace(SamplingParams=bad_sampling),
            guided, mod.emit_safe)
    log = capsys.readouterr().out
    assert "GUIDANCE_CPU_SAMPLING_PARAMS_HOLD" in log
    assert "private source must not appear" not in log


def test_runtime_traces_constructor_and_generate_stages_no_leaks(capsys):
    def guided(**kw):
        return object()
    def sampling(**kw):
        raise ValueError("secret from input")
    vl = SimpleNamespace(SamplingParams=sampling)
    sampling_module = SimpleNamespace(GuidedDecodingParams=guided)
    with mod.trace_generation_stages(vl, sampling_module, mod.emit_safe):
        sampling_module.GuidedDecodingParams(json={}, backend="guidance")
        with pytest.raises(ValueError):
            vl.SamplingParams(guided_decoding=object())
    assert vl.SamplingParams is sampling
    assert sampling_module.GuidedDecodingParams is guided
    log = capsys.readouterr().out
    assert "GUIDED_PARAMS_PASS" in log
    assert "SAMPLING_PARAMS_FAILURE" in log
    assert "secret from input" not in log


def test_generate_stage_separates_runtime_valueerror(capsys):
    class Engine:
        def generate(self, *args, **kwargs):
            raise ValueError("private generation body")
    instrumented = mod.TracedEngine(Engine(), mod.emit_safe)
    with pytest.raises(ValueError):
        instrumented.generate(["prompt"])
    log = capsys.readouterr().out
    assert "GENERATE_START" in log
    assert "GENERATE_FAILURE" in log
    assert "private generation body" not in log
