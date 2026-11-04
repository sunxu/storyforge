"""Strict validation for public Runtime diagnostic receipts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .diagnostics import ERROR_CODES, PHASES
from .inputs import InputManager

SCHEMA = "storyforge-hf-runtime-diagnostic-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
        if value["profile"] != "cpu" or value["status"] not in {"PASS", "HOLD", "FAIL"}:
            raise ValueError("RECEIPT_FIELD_INVALID")
        if value["phase"] not in PHASES:
            raise ValueError("RECEIPT_FIELD_INVALID")
        code = value["error_code"]
        if code is not None and code not in ERROR_CODES:
            raise ValueError("RECEIPT_FIELD_INVALID")
        if not isinstance(value["checks"], dict) or any(
            not isinstance(k, str) or v not in {"PASS", "FAIL", "UNKNOWN"}
            for k, v in value["checks"].items()
        ):
            raise ValueError("RECEIPT_FIELD_INVALID")
        if not isinstance(value["environment"], dict):
            raise ValueError("RECEIPT_FIELD_INVALID")
        if value["private_values_emitted"] is not False or value["gpu_started"] is not False:
            raise ValueError("RECEIPT_INVARIANT_FAILED")
        if value["training_performed"] is not False:
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
        try:
            verified = InputManager.open_verified(path, max_bytes=max_bytes)
            value = json.loads(verified.read_bytes())
        except ValueError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
            raise ValueError("RECEIPT_READ_FAILED") from exc
        if not isinstance(value, dict) or value.get("schema") != expected_schema:
            raise ValueError("RECEIPT_SCHEMA_UNKNOWN")
        return cls.validate_runtime_receipt(value)
