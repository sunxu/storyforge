"""Allowlisted, privacy-safe phase and failure diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PHASES = (
    "PREFLIGHT", "ENVIRONMENT", "BOOTSTRAP", "INPUT_SYNC", "INPUT_READ",
    "INPUT_VALIDATION", "DEPENDENCY_IMPORT", "MODEL_DOWNLOAD", "MODEL_LOAD",
    "TOKENIZER_LOAD", "TOKENIZATION", "BUSINESS_LOGIC", "OUTPUT_WRITE",
    "OUTPUT_VALIDATION", "COMPLETION",
)

ERROR_CODES = frozenset({
    "RUNTIME_CONTEXT_UNSUPPORTED", "RUNTIME_PROFILE_INVALID", "RUNTIME_ENVIRONMENT_UNKNOWN",
    "PATH_NOT_ABSOLUTE", "PATH_TRAVERSAL_REJECTED", "PATH_SYMLINK_REJECTED",
    "PATH_ROOT_NOT_ALLOWED", "PATH_KIND_AMBIGUOUS", "PATH_NOT_FOUND", "PATH_TYPE_INVALID",
    "INPUT_OPEN_FAILED", "INPUT_NOT_REGULAR_FILE", "INPUT_SYMLINK_REJECTED",
    "INPUT_SIZE_LIMIT_EXCEEDED", "INPUT_READ_FAILED", "INPUT_SHA256_MISMATCH",
    "INPUT_DESCRIPTOR_CHANGED", "OUTPUT_PARENT_INVALID", "OUTPUT_PROBE_FAILED",
    "OUTPUT_ALREADY_EXISTS", "OUTPUT_SYMLINK_REJECTED", "OUTPUT_CREATE_FAILED",
    "OUTPUT_WRITE_FAILED", "OUTPUT_FSYNC_FAILED", "OUTPUT_VERIFY_FAILED",
    "OUTPUT_CLEANUP_FAILED", "CPU_PROFILE_GPU_VISIBLE", "CPU_PROFILE_CUDA_DEVICE_DETECTED",
    "CPU_PROFILE_RESOURCE_UNKNOWN", "RESOURCE_PROFILE_UNSUPPORTED", "RECEIPT_READ_FAILED",
    "RECEIPT_SCHEMA_UNKNOWN", "RECEIPT_SCHEMA_INVALID", "RECEIPT_FIELD_INVALID",
    "RECEIPT_DIGEST_INVALID", "RECEIPT_INVARIANT_FAILED", "RECEIPT_SIZE_LIMIT_EXCEEDED",
    "CLI_ARGUMENT_INVALID", "CLI_DOCTOR_FAILED", "RUNTIME_INTERNAL_ERROR",
})
ErrorCode = str


@dataclass(frozen=True)
class Diagnostic:
    schema: str
    runtime_version: str
    profile: str
    status: str
    phase: str
    error_code: str | None
    checks: dict[str, str]
    environment: dict[str, object]
    private_values_emitted: bool = False
    gpu_started: bool = False
    training_performed: bool = False


@dataclass
class DiagnosticReporter:
    profile: str = "cpu"
    runtime_version: str = "0.1.0"
    phase: str = "PREFLIGHT"
    status: str = "PASS"
    error_code: str | None = None
    checks: dict[str, str] = field(default_factory=dict)
    environment: dict[str, object] = field(default_factory=dict)

    def start_phase(self, name: str) -> None:
        if name not in PHASES:
            raise ValueError("RUNTIME_INTERNAL_ERROR")
        self.phase = name

    def record_check(self, name: str, status: str) -> None:
        if not name.replace("_", "").isalnum() or status not in {"PASS", "FAIL", "UNKNOWN"}:
            raise ValueError("RUNTIME_INTERNAL_ERROR")
        self.checks[name] = status

    def fail(self, code: ErrorCode, *, phase: str | None = None) -> Diagnostic:
        if code not in ERROR_CODES:
            code = "RUNTIME_INTERNAL_ERROR"
        if phase is not None:
            if phase not in PHASES:
                code = "RUNTIME_INTERNAL_ERROR"
            else:
                self.phase = phase
        self.status = "HOLD" if code.endswith("_UNKNOWN") else "FAIL"
        self.error_code = code
        return self.to_safe_dict()

    def to_safe_dict(self) -> Diagnostic:
        safe_environment = {
            key: value for key, value in self.environment.items()
            if key in {"runtime", "python_version", "operating_system", "platform_machine"}
            and isinstance(value, (str, int, float, bool, type(None)))
        }
        return Diagnostic(
            schema="storyforge-hf-runtime-diagnostic-v1",
            runtime_version=self.runtime_version,
            profile=self.profile,
            status=self.status,
            phase=self.phase,
            error_code=self.error_code,
            checks=dict(self.checks),
            environment=safe_environment,
        )

    def write_safe(self, path: "Path") -> "WriteReceipt":
        from .outputs import OutputManager
        from dataclasses import asdict

        return OutputManager.write_safe(path, asdict(self.to_safe_dict()))
