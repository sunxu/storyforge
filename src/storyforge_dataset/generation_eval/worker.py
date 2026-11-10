"""Model-agnostic generation batch engine.

The engine accepts an injected backend and never loads model libraries itself.
Private generated text is written create-only with mode 0600; only metadata and
content hashes are returned in the SAFE receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from storyforge_dataset.hf_runtime.inputs import InputManager
from storyforge_dataset.hf_runtime.outputs import OutputManager, WriteReceipt

from .profiles import ProfileAssessment, assess_profile

SAMPLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
MESSAGE_ROLES = frozenset({"system", "developer", "user", "assistant"})


class WorkerError(ValueError):
    """A generation batch violates the strict worker contract."""


@dataclass(frozen=True)
class GenerationResult:
    text: str
    input_tokens: int
    output_tokens: int


class GenerationBackend(Protocol):
    """Backend contract implemented by a separately pinned model adapter."""

    @property
    def gpu_started(self) -> bool: ...

    def generate(
        self,
        *,
        model: str,
        revision: str,
        messages: Sequence[Mapping[str, str]],
        sampling: Mapping[str, Any],
        enable_thinking: bool | None,
        seed: int,
        max_input_tokens: int,
        max_new_tokens: int,
    ) -> GenerationResult: ...


@dataclass(frozen=True)
class WorkerReceipt:
    status: str
    model_role: str
    record_count: int
    output_size_bytes: int
    output_sha256: str
    output_mode: int
    private_values_emitted: bool = False
    inference_started: bool = True
    gpu_started: bool = False
    training_started: bool = False

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "schema": "storyforge_r60_generation_worker_receipt_safe_v1",
            "status": self.status,
            "model_role": self.model_role,
            "record_count": self.record_count,
            "output_size_bytes": self.output_size_bytes,
            "output_sha256": self.output_sha256,
            "output_mode": f"{self.output_mode:04o}",
            "private_values_emitted": False,
            "inference_started": self.inference_started,
            "gpu_started": self.gpu_started,
            "training_started": False,
        }


def _validate_records(records: list[dict[str, object]], expected_count: int) -> None:
    if len(records) != expected_count:
        raise WorkerError("INPUT_RECORD_COUNT_MISMATCH")
    seen: set[str] = set()
    for record in records:
        if set(record) != {"sample_id", "messages"}:
            raise WorkerError("INPUT_RECORD_SCHEMA_INVALID")
        sample_id = record["sample_id"]
        messages = record["messages"]
        if not isinstance(sample_id, str) or not SAMPLE_ID.fullmatch(sample_id):
            raise WorkerError("INPUT_SAMPLE_ID_INVALID")
        if sample_id in seen:
            raise WorkerError("INPUT_SAMPLE_ID_DUPLICATE")
        seen.add(sample_id)
        if not isinstance(messages, list) or not 1 <= len(messages) <= 64:
            raise WorkerError("INPUT_MESSAGES_INVALID")
        for message in messages:
            if not isinstance(message, dict) or set(message) != {"role", "content"}:
                raise WorkerError("INPUT_MESSAGE_SCHEMA_INVALID")
            if not isinstance(message["role"], str) or message["role"] not in MESSAGE_ROLES:
                raise WorkerError("INPUT_MESSAGE_ROLE_INVALID")
            if not isinstance(message["content"], str) or not message["content"].strip():
                raise WorkerError("INPUT_MESSAGE_CONTENT_INVALID")
        if messages[-1]["role"] != "user":
            raise WorkerError("INPUT_MUST_END_WITH_USER")


def run_generation_batch(
    *,
    profile: dict[str, Any],
    model_role: str,
    manifest: dict[str, Any],
    input_path: Path,
    output_path: Path,
    backend: GenerationBackend,
    max_input_file_bytes: int = 16 * 1024 * 1024,
) -> WorkerReceipt:
    """Run one authorized model batch and publish its private output atomically.

    This function is intentionally not exposed through an automatic CLI or Job
    submitter. A pinned backend and explicit profile authorization are required.
    """
    assessment: ProfileAssessment = assess_profile(profile)
    if not assessment.ready:
        raise WorkerError("GENERATION_PROFILE_NOT_READY")
    if model_role not in profile["model_profiles"]:
        raise WorkerError("MODEL_ROLE_INVALID")
    if not isinstance(manifest, dict) or manifest.get("schema") != "storyforge_r60_generation_input_manifest_v1":
        raise WorkerError("INPUT_MANIFEST_INVALID")

    expected_count = manifest.get("record_count")
    input_sha = manifest.get("sha256")
    max_input_tokens = manifest.get("max_input_tokens")
    max_new_tokens = manifest.get("max_new_tokens")
    seed = manifest.get("seed")
    for value, code in (
        (expected_count, "INPUT_RECORD_COUNT_INVALID"),
        (max_input_tokens, "MAX_INPUT_TOKENS_INVALID"),
        (max_new_tokens, "MAX_NEW_TOKENS_INVALID"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise WorkerError(code)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise WorkerError("SEED_INVALID")
    if not isinstance(input_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", input_sha):
        raise WorkerError("INPUT_SHA256_INVALID")
    if max_input_tokens > profile["input_budget_tokens"]:
        raise WorkerError("MAX_INPUT_TOKENS_EXCEEDS_PROFILE")
    if max_new_tokens > profile["generation_budget_tokens"]:
        raise WorkerError("MAX_NEW_TOKENS_EXCEEDS_PROFILE")
    if seed != profile["seed"]:
        raise WorkerError("SEED_MISMATCH")

    try:
        verified = InputManager.open_verified(
            input_path, max_bytes=max_input_file_bytes, expected_sha256=input_sha
        )
        records = InputManager.validate_jsonl(verified.read_bytes(), max_records=expected_count)
    except (OSError, ValueError) as exc:
        raise WorkerError("INPUT_VERIFICATION_FAILED") from exc
    _validate_records(records, expected_count)

    selected = profile["model_profiles"][model_role]
    private_outputs: list[dict[str, object]] = []
    for record in records:
        try:
            result = backend.generate(
                model=selected["model"],
                revision=selected["revision"],
                messages=record["messages"],
                sampling=selected["sampling"],
                enable_thinking=selected.get("enable_thinking"),
                seed=seed,
                max_input_tokens=max_input_tokens,
                max_new_tokens=max_new_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - do not leak backend errors or prompts
            raise WorkerError("GENERATION_BACKEND_FAILED") from exc
        if not isinstance(result, GenerationResult):
            raise WorkerError("GENERATION_RESULT_INVALID")
        if not isinstance(result.text, str) or len(result.text) > max_new_tokens * 64:
            raise WorkerError("GENERATION_RESULT_INVALID")
        if (not isinstance(result.input_tokens, int) or isinstance(result.input_tokens, bool)
                or not 1 <= result.input_tokens <= max_input_tokens):
            raise WorkerError("INPUT_TOKEN_BUDGET_EXCEEDED")
        if (not isinstance(result.output_tokens, int) or isinstance(result.output_tokens, bool)
                or not 0 <= result.output_tokens <= max_new_tokens):
            raise WorkerError("OUTPUT_TOKEN_BUDGET_EXCEEDED")
        private_outputs.append({
            "sample_id": record["sample_id"],
            "text": result.text,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        })

    payload = {
        "schema": "storyforge_r60_generation_outputs_private_v1",
        "model_role": model_role,
        "model": selected["model"],
        "revision": selected["revision"],
        "seed": seed,
        "record_count": len(private_outputs),
        "outputs": private_outputs,
    }
    try:
        write_receipt: WriteReceipt = OutputManager.write_safe(output_path, payload, mode=0o600)
    except (OSError, ValueError) as exc:
        raise WorkerError("OUTPUT_PUBLICATION_FAILED") from exc
    return WorkerReceipt(
        status="GENERATION_BATCH_PASS",
        model_role=model_role,
        record_count=len(private_outputs),
        output_size_bytes=write_receipt.size_bytes,
        output_sha256=write_receipt.sha256,
        output_mode=write_receipt.mode,
        gpu_started=backend.gpu_started is True,
    )
