"""Guard and optionally submit StoryForge CPU-only Hugging Face Jobs.

The guard is deliberately narrow: organization namespace adradar, CPU flavors,
read-only input mounts and one separate read-write output mount. It never
falls back to a personal namespace, retries a failed submission, or selects GPU.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass

BUCKET_PREFIX = "hf://buckets/adradar/storyforge-training/"
NAMESPACE = "adradar"
CPU_FLAVORS = frozenset({"cpu-basic", "cpu-upgrade"})


class PolicyError(ValueError):
    """A job specification violates the StoryForge HF execution policy."""


@dataclass(frozen=True)
class Volume:
    source: str
    destination: str
    mode: str


def parse_volume(value: str) -> Volume:
    """Parse HF bucket volume syntax without accepting ambiguous separators."""
    try:
        source, destination, mode = value.rsplit(":", 2)
    except ValueError as exc:
        raise PolicyError("VOLUME_SYNTAX_INVALID") from exc
    if not source.startswith(BUCKET_PREFIX):
        raise PolicyError("VOLUME_OUTSIDE_PROJECT_BUCKET")
    relative = source[len(BUCKET_PREFIX):]
    if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise PolicyError("VOLUME_SOURCE_PATH_INVALID")
    if not destination.startswith("/") or destination == "/":
        raise PolicyError("VOLUME_DESTINATION_INVALID")
    if mode not in {"ro", "rw"}:
        raise PolicyError("VOLUME_MODE_INVALID")
    return Volume(source, destination, mode)


def validate_spec(
    *,
    namespace: str,
    flavor: str,
    timeout_minutes: int,
    input_volumes: Sequence[str],
    output_volume: str,
    command: Sequence[str],
) -> tuple[list[Volume], Volume]:
    if namespace != NAMESPACE:
        raise PolicyError("NAMESPACE_MUST_BE_ADRADAR")
    if flavor not in CPU_FLAVORS:
        raise PolicyError("CPU_FLAVOR_REQUIRED_GPU_ESCALATION_FORBIDDEN")
    if not 1 <= timeout_minutes <= 120:
        raise PolicyError("CPU_TIMEOUT_OUT_OF_RANGE")
    if not input_volumes:
        raise PolicyError("READ_ONLY_INPUT_REQUIRED")
    if not command:
        raise PolicyError("JOB_COMMAND_REQUIRED")

    inputs = [parse_volume(item) for item in input_volumes]
    output = parse_volume(output_volume)

    if any(volume.mode != "ro" for volume in inputs):
        raise PolicyError("INPUT_MUST_BE_READ_ONLY")
    if any(
        not (
            volume.destination in {"/input", "/scripts"}
            or volume.destination.startswith("/input/")
            or volume.destination.startswith("/scripts/")
        )
        for volume in inputs
    ):
        raise PolicyError("INPUT_DESTINATION_MUST_BE_INPUT_OR_SCRIPTS")
    if len({volume.destination for volume in inputs}) != len(inputs):
        raise PolicyError("DUPLICATE_INPUT_DESTINATION")
    if output.mode != "rw" or output.destination != "/output":
        raise PolicyError("SEPARATE_READ_WRITE_OUTPUT_REQUIRED")
    for volume in inputs:
        input_source = volume.source.rstrip("/")
        output_source = output.source.rstrip("/")
        if (output_source == input_source
                or output_source.startswith(input_source + "/")
                or input_source.startswith(output_source + "/")):
            raise PolicyError("INPUT_OUTPUT_SOURCE_COLLISION")
    return inputs, output


def build_hf_argv(
    *,
    namespace: str,
    name: str,
    flavor: str,
    timeout_minutes: int,
    input_volumes: Sequence[str],
    output_volume: str,
    image: str,
    command: Sequence[str],
) -> list[str]:
    argv = [
        "hf", "jobs", "run",
        "--namespace", namespace,
        "--name", name,
        "--flavor", flavor,
        "--timeout", f"{timeout_minutes}m",
        "--attempts", "1",
    ]
    for volume in input_volumes:
        argv.extend(["-v", volume])
    argv.extend(["-v", output_volume, image, "--", *command])
    return argv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--flavor", required=True)
    parser.add_argument("--timeout-minutes", required=True, type=int)
    parser.add_argument("--input-volume", action="append", required=True)
    parser.add_argument("--output-volume", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--submit", action="store_true",
                        help="Actually submit. Without this flag, only validate.")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)

    try:
        inputs, output = validate_spec(
            namespace=args.namespace,
            flavor=args.flavor,
            timeout_minutes=args.timeout_minutes,
            input_volumes=args.input_volume,
            output_volume=args.output_volume,
            command=command,
        )
        report = {
            "schema": "storyforge-hf-cpu-job-guard-safe-v1",
            "status": "PREFLIGHT_PASS_NOT_SUBMITTED",
            "namespace": NAMESPACE,
            "flavor": args.flavor,
            "timeout_minutes": args.timeout_minutes,
            "input_mounts": len(inputs),
            "input_mount_mode": "ro",
            "output_mount_mode": output.mode,
            "attempts": 1,
            "gpu_allowed": False,
            "automatic_namespace_fallback": False,
            "automatic_retry": False,
            "private_values_emitted": False,
        }
        if not args.submit:
            print(json.dumps(report, sort_keys=True))
            return 0

        auth = subprocess.run(
            ["hf", "auth", "whoami"],
            capture_output=True,
            text=True,
            check=False,
        )
        if auth.returncode != 0:
            report.update(status="SUBMISSION_HOLD", reason_code="HF_AUTH_CHECK_FAILED")
            print(json.dumps(report, sort_keys=True))
            return 41

        argv = build_hf_argv(
            namespace=args.namespace,
            name=args.name,
            flavor=args.flavor,
            timeout_minutes=args.timeout_minutes,
            input_volumes=args.input_volume,
            output_volume=args.output_volume,
            image=args.image,
            command=command,
        )
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            error_text = (result.stderr + "\n" + result.stdout).lower()
            if "402" in error_text or "payment required" in error_text:
                reason = "ORGANIZATION_BILLING_OR_BALANCE"
            elif "403" in error_text or "forbidden" in error_text:
                reason = "ORGANIZATION_PERMISSION_OR_MOUNT_POLICY"
            else:
                reason = "HF_JOB_SUBMISSION_FAILED"
            report.update(status="SUBMISSION_REJECTED", reason_code=reason)
            print(json.dumps(report, sort_keys=True))
            return result.returncode or 42

        report.update(status="JOB_SUBMITTED")
        print(json.dumps(report, sort_keys=True))
        if result.stdout:
            print(result.stdout.rstrip())
        return 0
    except PolicyError as exc:
        print(json.dumps({
            "schema": "storyforge-hf-cpu-job-guard-safe-v1",
            "status": "PREFLIGHT_HOLD",
            "reason_code": str(exc),
            "private_values_emitted": False,
            "job_submitted": False,
        }, sort_keys=True))
        return 40


if __name__ == "__main__":
    sys.exit(main())
