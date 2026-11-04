#!/usr/bin/env python3
"""Owner-invoked, synthetic-only HF managed-volume CPU smoke adapter.

This adapter is deliberately outside the business-agnostic Runtime package.
It never submits jobs, contacts the Hub, downloads models, or starts training.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime import (
    InputManager,
    OutputManager,
    PathResolver,
    ResourceGuard,
    RuntimeContext,
)

SCHEMA = "storyforge-r60-hf-volume-smoke-v1"
INPUT_SCHEMA = "storyforge-r60-smoke-input-v1"
REPORT_NAME = "R60_CPU_VOLUME_SMOKE_SAFE.json"
CASE_ID = re.compile(r"^synthetic-[0-9]{3}$")
EXPECTED_KEYS = {"schema", "case"}
READONLY_ERRNOS = {errno.EROFS, errno.EACCES, errno.EPERM}


def _read_only_mount_check(root: Path) -> dict[str, str]:
    """Require both kernel read-only mount metadata and a denied create probe."""
    try:
        flags = os.statvfs(root).f_flag
    except OSError:
        return {"mount_readonly_flag": "UNKNOWN", "create_denied": "UNKNOWN"}
    readonly_bit = getattr(os, "ST_RDONLY", 1)
    mount_readonly = bool(flags & readonly_bit)
    token = secrets.token_hex(12)
    probe = root / f".storyforge-r60-ro-probe-{token}"
    if not hasattr(os, "O_NOFOLLOW"):
        return {
            "mount_readonly_flag": "PASS" if mount_readonly else "FAIL",
            "create_denied": "UNKNOWN",
        }
    fd = -1
    identity: tuple[int, int] | None = None
    try:
        fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        info = os.fstat(fd)
        identity = (info.st_dev, info.st_ino)
    except OSError as exc:
        denied = exc.errno in READONLY_ERRNOS
        return {
            "mount_readonly_flag": "PASS" if mount_readonly else "FAIL",
            "create_denied": "PASS" if denied else "FAIL",
        }
    finally:
        if fd >= 0:
            os.close(fd)
    # A writable mount is a hard failure. Remove only the exact probe inode
    # created above; never touch any pre-existing object or recurse.
    try:
        current = probe.lstat()
        if identity == (current.st_dev, current.st_ino):
            probe.unlink()
    except OSError:
        return {
            "mount_readonly_flag": "PASS" if mount_readonly else "FAIL",
            "create_denied": "FAIL",
        }
    return {
        "mount_readonly_flag": "PASS" if mount_readonly else "FAIL",
        "create_denied": "FAIL",
    }


def _validate_synthetic_records(records: list[dict[str, object]], expected: int) -> None:
    if len(records) != expected:
        raise ValueError("SMOKE_RECORD_COUNT_MISMATCH")
    for index, record in enumerate(records, start=1):
        if set(record) != EXPECTED_KEYS or record.get("schema") != INPUT_SCHEMA:
            raise ValueError("SMOKE_INPUT_SCHEMA_INVALID")
        case = record.get("case")
        if not isinstance(case, str) or not CASE_ID.fullmatch(case):
            raise ValueError("SMOKE_INPUT_NOT_SYNTHETIC")
        if case != f"synthetic-{index:03d}":
            raise ValueError("SMOKE_INPUT_ORDER_INVALID")


def _safe_report(
    *,
    status: str,
    checks: dict[str, str],
    input_sha256: str | None,
    input_size: int | None,
    record_count: int,
    runtime: RuntimeContext,
    error_code: str | None,
) -> dict[str, Any]:
    # No raw paths, source values, exception text, environment dumps or tokens.
    return {
        "schema": SCHEMA,
        "runtime_version": runtime.runtime_version,
        "profile": "cpu",
        "status": status,
        "error_code": error_code,
        "checks": checks,
        "input": {
            "sha256": input_sha256,
            "size_bytes": input_size,
            "records": record_count,
        },
        "environment": {
            "runtime": runtime.runtime,
            "python_version": runtime.python_version,
            "operating_system": runtime.operating_system,
            "platform_machine": runtime.platform_machine,
        },
        "private_values_emitted": False,
        "gpu_started": False,
        "training_performed": False,
    }


def run_smoke(
    *,
    input_root: Path,
    input_name: str,
    output_root: Path,
    expected_sha256: str,
    expected_records: int,
    max_input_bytes: int = 65536,
) -> dict[str, object]:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", input_name) or input_name in {".", ".."}:
        raise ValueError("SMOKE_INPUT_NAME_INVALID")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("SMOKE_EXPECTED_SHA256_INVALID")
    if expected_records < 1 or expected_records > 100:
        raise ValueError("SMOKE_RECORD_COUNT_INVALID")

    runtime = RuntimeContext.detect(profile="cpu")
    checks: dict[str, str] = {}
    resource = ResourceGuard.check_cpu_only()
    checks["cpu_profile"] = resource.status
    checks["gpu_not_started"] = "PASS" if resource.gpu_started is False else "FAIL"
    checks["training_not_performed"] = (
        "PASS" if resource.training_performed is False else "FAIL"
    )
    if resource.status != "PASS":
        report = _safe_report(
            status="FAIL", checks=checks, input_sha256=None, input_size=None,
            record_count=0, runtime=runtime, error_code=resource.error_code,
        )
        raise SmokeFailure(report, resource.error_code or "CPU_PROFILE_RESOURCE_UNKNOWN")

    try:
        input_root = PathResolver.validate_input_root(input_root)
        output_root = PathResolver.validate_output_root(output_root)
        checks["input_root"] = "PASS"
        checks["output_root"] = "PASS"
        ro_checks = _read_only_mount_check(input_root)
        checks.update(ro_checks)
        if any(value != "PASS" for value in ro_checks.values()):
            raise ValueError("SMOKE_INPUT_MOUNT_NOT_READ_ONLY")

        input_path = input_root / input_name
        verified = InputManager.open_verified(
            input_path, max_bytes=max_input_bytes, expected_sha256=expected_sha256
        )
        try:
            records = InputManager.validate_jsonl(verified.read_bytes(), max_records=expected_records)
        except TypeError:
            raise ValueError("SMOKE_INPUT_SCHEMA_INVALID") from None
        _validate_synthetic_records(records, expected_records)
        checks["input_sha256"] = "PASS"
        checks["input_jsonl"] = "PASS"
        checks["input_synthetic_only"] = "PASS"
        checks["input_record_count"] = "PASS"

        capability = OutputManager.probe(output_root)
        if not capability.writable or not capability.probe_cleaned:
            raise ValueError("SMOKE_OUTPUT_PROBE_FAILED")
        checks["output_rw_probe"] = "PASS"
        report = _safe_report(
            status="PASS", checks=checks, input_sha256=verified.sha256,
            input_size=verified.size_bytes, record_count=len(records),
            runtime=runtime, error_code=None,
        )
        destination = output_root / REPORT_NAME
        write_receipt = OutputManager.write_safe(destination, report)
        readback = InputManager.open_verified(
            destination, max_bytes=32768, expected_sha256=write_receipt.sha256
        )
        saved = json.loads(readback.read_bytes())
        if saved != report:
            raise ValueError("SMOKE_OUTPUT_READBACK_MISMATCH")
        checks["output_safe_receipt"] = "PASS"
        # Re-publish is forbidden: report is written once. The stdout summary
        # carries the final verification fact without mutating the receipt.
        return {
            "schema": SCHEMA,
            "status": "PASS",
            "checks": checks,
            "report_file": REPORT_NAME,
            "report_sha256": write_receipt.sha256,
            "report_size_bytes": write_receipt.size_bytes,
            "private_values_emitted": False,
            "gpu_started": False,
            "training_performed": False,
        }
    except SmokeFailure:
        raise
    except ValueError as exc:
        # Only stable allowlisted codes are exposed; never stringify arbitrary exceptions.
        code = str(exc)
        if not code.startswith("SMOKE_") and code not in {
            "INPUT_SIZE_LIMIT_EXCEEDED", "INPUT_SHA256_MISMATCH",
            "INPUT_JSONL_INVALID", "INPUT_OPEN_FAILED", "INPUT_NOT_REGULAR_FILE",
            "INPUT_SYMLINK_REJECTED", "PATH_NOT_FOUND", "PATH_SYMLINK_REJECTED",
            "PATH_TYPE_INVALID", "OUTPUT_PARENT_INVALID", "OUTPUT_PROBE_FAILED",
            "OUTPUT_ALREADY_EXISTS", "OUTPUT_CREATE_FAILED", "OUTPUT_WRITE_FAILED",
            "OUTPUT_FSYNC_FAILED", "OUTPUT_VERIFY_FAILED", "OUTPUT_CLEANUP_FAILED",
        }:
            code = "SMOKE_RUNTIME_FAILED"
        raise SmokeFailure(
            _safe_report(
                status="FAIL", checks=checks, input_sha256=None, input_size=None,
                record_count=0, runtime=runtime, error_code=code,
            ),
            code,
        ) from None


class SmokeFailure(Exception):
    def __init__(self, report: dict[str, Any], code: str) -> None:
        super().__init__(code)
        self.report = report
        self.code = code


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic-only R60 HF volume CPU smoke")
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--input-name", default="synthetic.jsonl")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-records", type=int, required=True)
    parser.add_argument("--max-input-bytes", type=int, default=65536)
    args = parser.parse_args()
    try:
        result = run_smoke(
            input_root=args.input_root,
            input_name=args.input_name,
            output_root=args.output_root,
            expected_sha256=args.expected_sha256,
            expected_records=args.expected_records,
            max_input_bytes=args.max_input_bytes,
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except SmokeFailure as exc:
        print(json.dumps(exc.report, sort_keys=True, separators=(",", ":")))
        return 2
    except (OSError, ValueError):
        print(json.dumps({
            "schema": SCHEMA, "status": "FAIL", "error_code": "SMOKE_ARGUMENT_OR_IO_FAILED",
            "private_values_emitted": False, "gpu_started": False, "training_performed": False,
        }, sort_keys=True, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
