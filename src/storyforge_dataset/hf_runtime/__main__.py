"""Read-only Runtime doctor command."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .context import RuntimeContext
from .diagnostics import DiagnosticReporter
from .outputs import OutputManager
from .resources import ResourceGuard


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m storyforge_dataset.hf_runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--profile", choices=("cpu",), required=True)
    doctor.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    reporter = DiagnosticReporter(profile=args.profile)
    try:
        reporter.start_phase("ENVIRONMENT")
        context = RuntimeContext.detect(profile=args.profile)
        reporter.environment = context.to_safe_dict()
        reporter.record_check("runtime_context", "PASS")

        reporter.start_phase("PREFLIGHT")
        resource = ResourceGuard.check_cpu_only()
        for name, status in resource.checks.items():
            reporter.record_check(name, status)
        if resource.status != "PASS":
            reporter.fail("CPU_PROFILE_GPU_VISIBLE", phase="PREFLIGHT")

        reporter.start_phase("OUTPUT_VALIDATION")
        # Doctor probes the system temporary directory only; it does not inspect
        # project/private mounts or create a persistent report.
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(prefix="storyforge-r60-doctor-") as tmp:
            OutputManager.probe(Path(tmp))
        reporter.record_check("temporary_output_probe", "PASS")
    except ValueError as exc:
        code = str(exc)
        if code not in __import__("storyforge_dataset.hf_runtime.diagnostics", fromlist=["ERROR_CODES"]).ERROR_CODES:
            code = "CLI_DOCTOR_FAILED"
        reporter.fail(code)

    result = asdict(reporter.to_safe_dict())
    if args.json_output:
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    else:
        sys.stderr.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if reporter.status == "PASS":
        return 0
    if any(value == "UNKNOWN" for value in reporter.checks.values()):
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
