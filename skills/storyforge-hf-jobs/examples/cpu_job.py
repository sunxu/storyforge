"""示例业务 Runner：仅展示 Runtime 调用，不提交 HF Job、不加载模型。"""
from pathlib import Path

from storyforge_dataset.hf_runtime import (
    DiagnosticReporter,
    InputManager,
    OutputManager,
    ResourceGuard,
    RuntimeContext,
)

def main() -> int:
    runtime = RuntimeContext.detect(profile="cpu")
    reporter = DiagnosticReporter(profile="cpu")
    reporter.start_phase("PREFLIGHT")
    resource = ResourceGuard.check_cpu_only()
    if resource.status != "PASS":
        reporter.fail(resource.error_code or "CPU_PROFILE_RESOURCE_UNKNOWN")
        return 2

    reporter.start_phase("INPUT_READ")
    source = InputManager.open_verified(
        Path("/job/synthetic.jsonl"),
        max_bytes=64 * 1024,
        expected_sha256="0" * 64,  # Replace only with a separately verified synthetic-input digest.
    )
    reporter.record_check("input_verified", "PASS")
    reporter.start_phase("OUTPUT_WRITE")
    OutputManager.probe(Path("/results"))
    OutputManager.write_safe(
        Path("/results/EXAMPLE_SAFE.json"),
        {"schema": "example-safe-v1", "input_sha256": source.sha256,
         "runtime": runtime.to_safe_dict()["runtime"]},
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
