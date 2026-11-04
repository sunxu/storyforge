"""Strict validation for public Runtime diagnostic receipts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .diagnostics import ERROR_CODES, PHASES
from .inputs import InputManager

SCHEMA = "storyforge-hf-runtime-diagnostic-v1"
ENVIRONMENT_FIELDS = {"runtime", "python_version", "operating_system", "platform_machine"}


@dataclass(frozen=True)
class RuntimeReceipt:
    value: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return dict(self.value)


class ReceiptValidator:
    REQUIRED = {
        "schema", "runtime_version", "profile", "status", "phase", "error_code",
        "checks", "environment", "private_values_emitted", "gpu_started",
        "training_performed",
    }

    @classmethod
    def validate_runtime_receipt(cls, value: object) -> RuntimeReceipt:
        if not isinstance(value, dict) or set(value) != cls.REQUIRED:
            raise ValueError("RECEIPT_SCHEMA_INVALID")
        if value["schema"] != SCHEMA:
            raise ValueError("RECEIPT_SCHEMA_UNKNOWN")
        if not isinstance(value["runtime_version"], str) or not isinstance(value["profile"], str):
            raise ValueError("RECEIPT_FIELD_INVALID")
        if value["profile"] != "cpu" or not isinstance(value["status"], str) or value["status"] not in {"PASS", "HOLD", "FAIL"}:
            raise ValueError("RECEIPT_FIELD_INVALID")
        if not isinstance(value["phase"], str) or value["phase"] not in PHASES:
            raise ValueError("RECEIPT_FIELD_INVALID")
        code = value["error_code"]
        if code is not None and (not isinstance(code, str) or code not in ERROR_CODES):
            raise ValueError("RECEIPT_FIELD_INVALID")
        checks = value["checks"]
        if not isinstance(checks, dict) or any(
            not isinstance(key, str) or not isinstance(status, str)
            or status not in {"PASS", "FAIL", "UNKNOWN"}
            for key, status in checks.items()
        ):
            raise ValueError("RECEIPT_FIELD_INVALID")
        environment = value["environment"]
        if not isinstance(environment, dict) or not set(environment).issubset(ENVIRONMENT_FIELDS):
            raise ValueError("RECEIPT_FIELD_INVALID")
        if any(
            not isinstance(item, (str, int, float, bool)) and item is not None
            for item in environment.values()
        ):
            raise ValueError("RECEIPT_FIELD_INVALID")
        for field in ("private_values_emitted", "gpu_started", "training_performed"):
            if type(value[field]) is not bool or value[field] is not False:
                raise ValueError("RECEIPT_INVARIANT_FAILED")
        if value["status"] == "PASS" and code is not None:
            raise ValueError("RECEIPT_INVARIANT_FAILED")
        if value["status"] != "PASS" and code is None:
            raise ValueError("RECEIPT_INVARIANT_FAILED")
        return RuntimeReceipt(dict(value))

    @classmethod
    def verify_file(
        cls,
        path: Path,
        *,
        expected_schema: str,
        max_bytes: int = 32768,
    ) -> RuntimeReceipt:
        if expected_schema != SCHEMA:
            raise ValueError("RECEIPT_SCHEMA_UNKNOWN")
        try:
            verified = InputManager.open_verified(path, max_bytes=max_bytes)
            value = json.loads(verified.read_bytes())
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("RECEIPT_SCHEMA_INVALID") from exc
        except ValueError as exc:
            if str(exc) == "INPUT_SIZE_LIMIT_EXCEEDED":
                raise ValueError("RECEIPT_SIZE_LIMIT_EXCEEDED") from exc
            raise
        except OSError as exc:
            raise ValueError("RECEIPT_READ_FAILED") from exc
        return cls.validate_runtime_receipt(value)
