"""Qwen A25 Guidance failure-stage tracing without private outputs.

CPU preflight validates the EXACT two-argument construction used by the
frozen Guidance reviewer. Runtime tracing is opt-in and records only fixed
stage/status codes and exception class names, never exception messages,
tokens, prompts, text, JSON payloads or private source paths.
"""
from __future__ import annotations

import contextlib
import importlib.util
import json
from pathlib import Path


class DiagnosticHold(ValueError):
    pass


def cpu_guidance_probe(worker: object, vllm: object,
                       sampling_module: object, emit: object) -> None:
    """Replicate the frozen runner's Guidance + SamplingParams call, no GPU."""
    emit("GUIDANCE_CPU_SCHEMA_READY")
    schema = worker.response_schema()
    emit("GUIDANCE_CPU_GUIDED_PARAMS_START")
    try:
        guided = sampling_module.GuidedDecodingParams(
            json=schema, backend="guidance")
    except Exception as exc:  # noqa: BLE001 - redact arbitrary vLLM error messages
        emit("GUIDANCE_CPU_GUIDED_PARAMS_HOLD",
             exception_class=type(exc).__name__)
        raise DiagnosticHold("GUIDANCE_GUIDED_PARAMS_API_HOLD") from None
    emit("GUIDANCE_CPU_GUIDED_PARAMS_PASS")
    emit("GUIDANCE_CPU_SAMPLING_PARAMS_START")
    try:
        vllm.SamplingParams(
            temperature=0, max_tokens=2400, guided_decoding=guided)
    except Exception as exc:  # noqa: BLE001 - redact arbitrary vLLM error messages
        emit("GUIDANCE_CPU_SAMPLING_PARAMS_HOLD",
             exception_class=type(exc).__name__)
        raise DiagnosticHold("GUIDANCE_SAMPLING_PARAMS_API_HOLD") from None
    emit("GUIDANCE_CPU_SAMPLING_PARAMS_PASS")


def safe_exception_stage(exc: Exception) -> str:
    # Never use str(exc), repr(exc), args or traceback here.
    return type(exc).__name__[:64]


@contextlib.contextmanager
def trace_generation_stages(vllm: object, sampling_module: object,
                            emit: object):
    """Temporarily wrap public constructors with output-free trace stages."""
    original_sampling = vllm.SamplingParams
    original_guided = sampling_module.GuidedDecodingParams

    def guided_factory(*args, **kwargs):
        emit("GUIDED_PARAMS_START")
        try:
            result = original_guided(*args, **kwargs)
        except Exception as exc:
            emit("GUIDED_PARAMS_FAILURE",
                 exception_class=safe_exception_stage(exc))
            raise
        emit("GUIDED_PARAMS_PASS")
        return result

    def sampling_factory(*args, **kwargs):
        emit("SAMPLING_PARAMS_START")
        try:
            result = original_sampling(*args, **kwargs)
        except Exception as exc:
            emit("SAMPLING_PARAMS_FAILURE",
                 exception_class=safe_exception_stage(exc))
            raise
        emit("SAMPLING_PARAMS_PASS")
        return result

    vllm.SamplingParams = sampling_factory
    sampling_module.GuidedDecodingParams = guided_factory
    try:
        yield
    finally:
        vllm.SamplingParams = original_sampling
        sampling_module.GuidedDecodingParams = original_guided


class TracedEngine:
    """Delegates all engine API other than generate without modifying model."""

    def __init__(self, engine: object, emit: object) -> None:
        self._engine = engine
        self._emit = emit

    def __getattr__(self, key: str) -> object:
        return getattr(self._engine, key)

    def generate(self, *args, **kwargs):
        self._emit("GENERATE_START")
        try:
            result = self._engine.generate(*args, **kwargs)
        except Exception as exc:
            self._emit("GENERATE_FAILURE",
                       exception_class=safe_exception_stage(exc))
            raise
        self._emit("GENERATE_PASS")
        return result


def probe_runner_from_local_file(
    path: Path, *, vllm: object, sampling_module: object,
    emit: object,
) -> None:
    if path.is_symlink() or not path.is_file():
        raise DiagnosticHold("GUIDANCE_RUNNER_FILE_HOLD")
    source = path.read_text(encoding="utf-8")
    if ("GuidedDecodingParams(json=response_schema(), backend=\"guidance\")"
            not in source
            or source.count("GuidedDecodingParams(json=response_schema(), backend=\"guidance\")") != 1):
        raise DiagnosticHold("GUIDANCE_RUNNER_NOT_PINNED_HOLD")
    spec = importlib.util.spec_from_file_location("r60_guidance_cpu_probe", path)
    if spec is None or spec.loader is None:
        raise DiagnosticHold("GUIDANCE_RUNNER_IMPORT_HOLD")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cpu_guidance_probe(module, vllm, sampling_module, emit)


def emit_safe(event: str, **fields: object) -> None:
    print(json.dumps({"schema": "storyforge_r60_guidance_diagnostic_safe_v1",
                      "event": event, "private_values_emitted": False,
                      **fields}, sort_keys=True, separators=(",", ":")),
          flush=True)

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    args = parser.parse_args()
    try:
        import vllm
        import vllm.sampling_params as sampling_module
        probe_runner_from_local_file(
            args.runner, vllm=vllm, sampling_module=sampling_module,
            emit=emit_safe)
        emit_safe("GUIDANCE_CPU_PREFLIGHT_PASS")
        return 0
    except DiagnosticHold as exc:
        emit_safe("GUIDANCE_CPU_PREFLIGHT_HOLD", reason_code=str(exc))
        return 42
    except Exception as exc:  # noqa: BLE001 - SAFE metadata only
        emit_safe("GUIDANCE_CPU_PREFLIGHT_HOLD",
                  reason_code="GUIDANCE_CPU_UNEXPECTED_HOLD",
                  exception_class=safe_exception_stage(exc))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
