"""Model-agnostic generation batch engine.

The engine accepts an injected backend and never loads model libraries itself.
Private generated text is written create-only with mode 0600; only metadata and
content hashes are returned in the SAFE receipt.
"""
from __future__ import annotations

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
    finish_reason: str = "unrecognized_stop"


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
        generation_prefix: str | None = None,
        seed: int,
        max_input_tokens: int,
        max_new_tokens: int,
        eos_token_ids: Sequence[int],
        pad_token_id: int,
    ) -> GenerationResult: ...


@dataclass(frozen=True)
class WorkerReceipt:
    status: str
    model_role: str
    record_count: int
    output_size_bytes: int
    output_sha256: str
    output_mode: int
    finish_reason_counts: dict[str, int]
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
            "finish_reason_counts": dict(self.finish_reason_counts),
            "truncated_count": self.finish_reason_counts.get("length", 0),
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
    except (OSError, TypeError, ValueError) as exc:
        raise WorkerError("INPUT_VERIFICATION_FAILED") from exc
    _validate_records(records, expected_count)

    selected = profile["model_profiles"][model_role]
    private_outputs: list[dict[str, object]] = []
    finish_reason_counts = {"eos": 0, "length": 0, "unrecognized_stop": 0}
    for index, record in enumerate(records):
        effective_seed = seed + index
        try:
            result = backend.generate(
                model=selected["model"],
                revision=selected["revision"],
                messages=record["messages"],
                sampling=selected["sampling"],
                enable_thinking=selected.get("enable_thinking"),
                generation_prefix=selected.get("generation_prefix"),
                seed=effective_seed,
                max_input_tokens=max_input_tokens,
                max_new_tokens=max_new_tokens,
                eos_token_ids=profile["eos_token_ids"][model_role],
                pad_token_id=profile["pad_token_ids"][model_role],
            )
        except Exception as exc:
            raise WorkerError("GENERATION_BACKEND_FAILED") from exc
        if not isinstance(result, GenerationResult):
            raise WorkerError("GENERATION_RESULT_INVALID")
        if not isinstance(result.text, str) or len(result.text) > max_new_tokens * 64:
            raise WorkerError("GENERATION_RESULT_INVALID")
        if result.finish_reason not in finish_reason_counts:
            raise WorkerError("GENERATION_FINISH_REASON_INVALID")
        finish_reason_counts[result.finish_reason] += 1
        if (not isinstance(result.input_tokens, int) or isinstance(result.input_tokens, bool)
                or not 1 <= result.input_tokens <= max_input_tokens):
            raise WorkerError("INPUT_TOKEN_BUDGET_EXCEEDED")
        if (not isinstance(result.output_tokens, int) or isinstance(result.output_tokens, bool)
                or not 0 <= result.output_tokens <= max_new_tokens):
            raise WorkerError("OUTPUT_TOKEN_BUDGET_EXCEEDED")
        private_outputs.append({
            "sample_id": record["sample_id"],
            "effective_seed": effective_seed,
            "text": result.text,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "finish_reason": result.finish_reason,
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
    if finish_reason_counts["unrecognized_stop"]:
        status = "GENERATION_BATCH_HOLD_UNRECOGNIZED_STOP"
    elif finish_reason_counts["length"]:
        status = "GENERATION_BATCH_PASS_WITH_LENGTH_STOPS"
    else:
        status = "GENERATION_BATCH_PASS"
    return WorkerReceipt(
        status=status,
        model_role=model_role,
        record_count=len(private_outputs),
        output_size_bytes=write_receipt.size_bytes,
        output_sha256=write_receipt.sha256,
        output_mode=write_receipt.mode,
        finish_reason_counts=finish_reason_counts,
        gpu_started=backend.gpu_started is True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one explicitly authorized, single-model generation batch.

    This entry point is intentionally fail-closed: the production profile must
    already carry Owner freeze/inference/GPU authorization. It writes private
    generations only beneath a fresh output directory and prints SAFE metadata.
    """
    import argparse
    import hashlib
    import json
    import os
    import sys
    import tempfile

    from .backend import TransformersGenerationBackend, download_pinned_tokenizer_snapshot
    from .profiles import assess_profile, load_profile

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-role", required=True, choices=("A", "B", "challenger"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        profile = load_profile(args.profile)
        assessment = assess_profile(profile)
        if not assessment.ready:
            raise WorkerError("GENERATION_PROFILE_NOT_AUTHORIZED")
        if profile.get("training_authorized") is True:
            raise WorkerError("TRAINING_AUTHORIZATION_MUST_REMAIN_DISABLED")

        repo_root = args.repo_root.resolve(strict=True)
        lock_relative = Path(profile["dependency_lock_path"])
        if lock_relative.is_absolute() or any(part in {"", ".", ".."} for part in lock_relative.parts):
            raise WorkerError("DEPENDENCY_LOCK_PATH_INVALID")
        lock_path = (repo_root / lock_relative).resolve(strict=True)
        if not lock_path.is_relative_to(repo_root):
            raise WorkerError("DEPENDENCY_LOCK_PATH_INVALID")
        lock_bytes = InputManager.open_verified(
            lock_path, max_bytes=8 * 1024 * 1024
        ).read_bytes()
        lock_sha = hashlib.sha256(lock_bytes).hexdigest()
        if lock_sha != profile.get("dependency_lock_sha256"):
            raise WorkerError("DEPENDENCY_LOCK_SHA256_MISMATCH")
        runtime_digest = profile.get("runtime_digest")
        if os.environ.get("STORYFORGE_RUNTIME_IMAGE_DIGEST") != runtime_digest:
            raise WorkerError("RUNTIME_IMAGE_DIGEST_MISMATCH")
        if sys.version_info[:2] != (3, 11):
            raise WorkerError("PYTHON_RUNTIME_MISMATCH")

        manifest_bytes = InputManager.open_verified(
            args.manifest, max_bytes=1024 * 1024
        ).read_bytes()
        try:
            manifest = json.loads(manifest_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkerError("INPUT_MANIFEST_INVALID") from exc
        if not isinstance(manifest, dict) or set(manifest) != {
            "schema", "record_count", "sha256", "max_input_tokens",
            "max_new_tokens", "seed",
        }:
            raise WorkerError("INPUT_MANIFEST_INVALID")

        output_dir = args.output_dir
        if (
            output_dir.parent != Path("/output")
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", output_dir.name)
        ):
            raise WorkerError("OUTPUT_DIRECTORY_INVALID")
        if output_dir.is_symlink() or output_dir.exists():
            raise WorkerError("OUTPUT_DIRECTORY_MUST_BE_NEW")
        parent = output_dir.parent
        OutputManager._check_root(parent)
        output_dir.mkdir(mode=0o700)
        os.chmod(output_dir, 0o700)
        OutputManager.probe(output_dir)

        selected = profile["model_profiles"][args.model_role]
        expected_files = profile["tokenizer_file_hashes"][args.model_role]
        model_id = selected["model"]
        revision = selected["revision"]
        output_path = output_dir / f"{args.model_role.lower()}-outputs.private.json"

        import torch
        import transformers

        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise WorkerError("CUDA_BF16_RUNTIME_REQUIRED")

        with tempfile.TemporaryDirectory(prefix=f"r60-p4-{args.model_role}-") as tmp:
            snapshot = download_pinned_tokenizer_snapshot(
                model_id=model_id,
                revision=revision,
                destination=Path(tmp) / "tokenizer",
                expected_file_hashes=expected_files,
            )
            backend = TransformersGenerationBackend.from_pretrained(
                model_id=model_id,
                revision=revision,
                template_source=selected["chat_template_source"],
                expected_template_sha256=selected["chat_template_sha256"],
                tokenizer_snapshot=snapshot,
                expected_tokenizer_file_hashes=expected_files,
                torch_module=torch,
                transformers_module=transformers,
            )
            if backend.gpu_started is not True:
                raise WorkerError("MODEL_NOT_RESIDENT_ON_CUDA")
            receipt = run_generation_batch(
                profile=profile,
                model_role=args.model_role,
                manifest=manifest,
                input_path=args.input,
                output_path=output_path,
                backend=backend,
            )
            safe = receipt.to_safe_dict()
            safe.update({
                "dependency_lock_sha256": lock_sha,
                "runtime_digest": runtime_digest,
                "model_revision": revision,
                "private_output_path": output_path.name,
            })
            print(json.dumps(safe, sort_keys=True))
            return 0 if receipt.status != "GENERATION_BATCH_HOLD_UNRECOGNIZED_STOP" else 3
    except (OSError, RuntimeError, TypeError, ValueError, KeyError, ImportError) as exc:
        code = str(exc) if isinstance(exc, WorkerError) else "WORKER_RUNTIME_VALIDATION_FAILED"
        print(json.dumps({
            "schema": "storyforge_r60_generation_worker_receipt_safe_v1",
            "status": "GENERATION_WORKER_HOLD",
            "reason_code": code,
            "private_values_emitted": False,
            "inference_started": False,
            "gpu_started": False,
            "training_started": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
