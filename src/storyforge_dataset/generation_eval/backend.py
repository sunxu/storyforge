"""Pinned Transformers backend adapter for Qwen3 / GLM4 generation.

Imports torch/transformers lazily and loads weights only when explicitly
constructed. This module is not called by profile checks, plan generation, or CI.
"""
from __future__ import annotations

import hashlib
import importlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.inputs import InputManager

from .worker import GenerationResult, WorkerError

SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SAMPLING_KEYS = frozenset({"do_sample", "temperature", "top_p", "top_k", "min_p"})


def verify_tokenizer_snapshot(
    snapshot_path: Path,
    expected_file_hashes: Mapping[str, str],
) -> None:
    """Verify every manifest-pinned tokenizer/config file before local-only loading."""
    if snapshot_path.is_symlink() or not snapshot_path.is_dir():
        raise WorkerError("TOKENIZER_SNAPSHOT_INVALID")
    if (
        not isinstance(expected_file_hashes, Mapping)
        or frozenset(expected_file_hashes) not in {frozenset(x) for x in (
            {"config.json", "generation_config.json", "merges.txt", "tokenizer.json",
             "tokenizer_config.json", "vocab.json"},
            {"chat_template.jinja", "config.json", "generation_config.json",
             "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"},
        )}
    ):
        raise WorkerError("TOKENIZER_FILE_MANIFEST_INVALID")
    for name, digest in expected_file_hashes.items():
        if (
            not isinstance(name, str) or Path(name).name != name
            or name in {".", ".."} or not isinstance(digest, str)
            or not SHA256.fullmatch(digest)
        ):
            raise WorkerError("TOKENIZER_FILE_MANIFEST_INVALID")
        try:
            verified = InputManager.open_verified(
                snapshot_path / name,
                max_bytes=64 * 1024 * 1024,
                expected_sha256=digest,
            )
            verified.read_bytes()
        except (OSError, ValueError) as exc:
            raise WorkerError("TOKENIZER_FILE_HASH_MISMATCH") from exc


def download_pinned_tokenizer_snapshot(
    *,
    model_id: str,
    revision: str,
    destination: Path,
    expected_file_hashes: Mapping[str, str],
) -> Path:
    """Download only the exact tokenizer/config file allowlist at one commit."""
    if not isinstance(revision, str) or not HEX40.fullmatch(revision):
        raise WorkerError("MODEL_REVISION_INVALID")
    if destination.exists() or destination.is_symlink():
        raise WorkerError("TOKENIZER_SNAPSHOT_DESTINATION_EXISTS")
    if not isinstance(expected_file_hashes, Mapping) or not expected_file_hashes:
        raise WorkerError("TOKENIZER_FILE_MANIFEST_INVALID")
    for name, digest in expected_file_hashes.items():
        if (
            not isinstance(name, str) or Path(name).name != name
            or name in {".", ".."} or not isinstance(digest, str)
            or not SHA256.fullmatch(digest)
        ):
            raise WorkerError("TOKENIZER_FILE_MANIFEST_INVALID")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        hub = importlib.import_module("huggingface_hub")
        downloaded = hub.snapshot_download(
            repo_id=model_id,
            revision=revision,
            local_dir=str(destination),
            allow_patterns=sorted(expected_file_hashes),
            token=False,
        )
        snapshot = Path(downloaded)
        verify_tokenizer_snapshot(snapshot, expected_file_hashes)
        return snapshot
    except WorkerError:
        raise
    except Exception as exc:
        raise WorkerError("TOKENIZER_SNAPSHOT_DOWNLOAD_FAILED") from exc


def classify_finish_reason(
    generated_token_ids: Sequence[int],
    *,
    eos_token_ids: Sequence[int],
    max_new_tokens: int,
) -> str:
    """Classify a single sequence from its actual generated token IDs."""
    if not generated_token_ids:
        return "unrecognized_stop"
    if generated_token_ids[-1] in eos_token_ids:
        return "eos"
    if len(generated_token_ids) >= max_new_tokens:
        return "length"
    return "unrecognized_stop"


class TransformersGenerationBackend:
    """One-model, one-device-map backend using pinned Hub revisions."""

    def __init__(
        self, *, tokenizer: Any, model: Any, torch_module: Any,
        model_id: str | None = None, revision: str | None = None,
    ) -> None:
        self.tokenizer = tokenizer
        self.model = model
        self.torch = torch_module
        self.model_id = model_id
        self.revision = revision
        self._gpu_started = self._verify_cuda_device_map(model)

    @staticmethod
    def _verify_cuda_device_map(model: Any) -> bool:
        device_map = getattr(model, "hf_device_map", None)
        if isinstance(device_map, dict) and device_map:
            values = tuple(device_map.values())
            if any(
                value == "cpu" or value == "disk"
                or isinstance(value, str) and not value.startswith("cuda")
                or isinstance(value, int) and value < 0
                for value in values
            ):
                raise WorkerError("MODEL_DEVICE_MAP_CPU_OFFLOAD_REJECTED")
            if not all(isinstance(value, int) or isinstance(value, str) and value.startswith("cuda")
                       for value in values):
                raise WorkerError("MODEL_DEVICE_MAP_UNKNOWN")
            return True
        device = getattr(model, "device", None)
        if getattr(device, "type", None) != "cuda":
            raise WorkerError("MODEL_NOT_RESIDENT_ON_CUDA")
        return True

    @property
    def gpu_started(self) -> bool:
        return self._gpu_started

    @classmethod
    def from_pretrained(
        cls,
        *,
        model_id: str,
        revision: str,
        template_source: str,
        expected_template_sha256: str,
        tokenizer_snapshot: Path,
        expected_tokenizer_file_hashes: Mapping[str, str],
        torch_module: Any | None = None,
        transformers_module: Any | None = None,
    ) -> TransformersGenerationBackend:
        if not HEX40.fullmatch(revision):
            raise WorkerError("MODEL_REVISION_INVALID")
        if not isinstance(expected_tokenizer_file_hashes, Mapping):
            raise WorkerError("TOKENIZER_FILE_MANIFEST_INVALID")
        if not SHA256.fullmatch(expected_template_sha256):
            raise WorkerError("CHAT_TEMPLATE_HASH_INVALID")
        file_set = frozenset(expected_tokenizer_file_hashes)
        if (
            template_source == "embedded_tokenizer_config"
            and file_set != frozenset({
                "config.json", "generation_config.json", "merges.txt", "tokenizer.json",
                "tokenizer_config.json", "vocab.json",
            })
        ) or (
            template_source == "standalone_chat_template.jinja"
            and file_set != frozenset({
                "chat_template.jinja", "config.json", "generation_config.json",
                "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
            })
        ):
            raise WorkerError("TOKENIZER_TEMPLATE_SOURCE_MANIFEST_MISMATCH")
        verify_tokenizer_snapshot(tokenizer_snapshot, expected_tokenizer_file_hashes)
        torch = torch_module or importlib.import_module("torch")
        transformers = transformers_module or importlib.import_module("transformers")
        if not torch.cuda.is_available():
            raise WorkerError("CUDA_NOT_AVAILABLE")
        if not torch.cuda.is_bf16_supported():
            raise WorkerError("CUDA_BFLOAT16_UNSUPPORTED")

        try:
            tokenizer = transformers.AutoTokenizer.from_pretrained(
                str(tokenizer_snapshot),
                local_files_only=True,
                trust_remote_code=False,
            )
            if template_source == "embedded_tokenizer_config":
                template = tokenizer.chat_template
                if not isinstance(template, str):
                    raise WorkerError("EMBEDDED_CHAT_TEMPLATE_MISSING")
                actual_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
            elif template_source == "standalone_chat_template.jinja":
                template_path = tokenizer_snapshot / "chat_template.jinja"
                try:
                    verified_template = InputManager.open_verified(
                        template_path,
                        max_bytes=1024 * 1024,
                        expected_sha256=expected_template_sha256,
                    )
                except ValueError as exc:
                    code = (
                        "CHAT_TEMPLATE_SHA256_MISMATCH"
                        if str(exc) == "INPUT_SHA256_MISMATCH"
                        else "STANDALONE_CHAT_TEMPLATE_INVALID"
                    )
                    raise WorkerError(code) from exc
                except OSError as exc:
                    raise WorkerError("STANDALONE_CHAT_TEMPLATE_INVALID") from exc
                template_bytes = verified_template.read_bytes()
                actual_hash = verified_template.sha256
                template = template_bytes.decode("utf-8")
                tokenizer.chat_template = template
            else:
                raise WorkerError("CHAT_TEMPLATE_SOURCE_INVALID")
            if actual_hash != expected_template_sha256:
                raise WorkerError("CHAT_TEMPLATE_SHA256_MISMATCH")

            model = transformers.AutoModelForCausalLM.from_pretrained(
                model_id,
                revision=revision,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=False,
                low_cpu_mem_usage=True,
            )
            model.eval()
            return cls(
                tokenizer=tokenizer, model=model, torch_module=torch,
                model_id=model_id, revision=revision,
            )
        except WorkerError:
            raise
        except Exception as exc:  # backend exceptions are converted to fixed codes
            raise WorkerError("MODEL_LOAD_FAILED") from exc

    def generate(
        self,
        *,
        model: str,
        revision: str,
        messages: list[dict[str, str]],
        sampling: dict[str, Any],
        enable_thinking: bool | None,
        seed: int,
        max_input_tokens: int,
        max_new_tokens: int,
        eos_token_ids: Sequence[int],
        pad_token_id: int,
    ) -> GenerationResult:
        if (not isinstance(eos_token_ids, (list, tuple)) or not eos_token_ids
                or any(not isinstance(value, int) or isinstance(value, bool) or value < 0
                       for value in eos_token_ids)
                or not isinstance(pad_token_id, int) or isinstance(pad_token_id, bool)
                or pad_token_id < 0):
            raise WorkerError("STOP_TOKEN_PROFILE_INVALID")
        if not isinstance(sampling, dict) or set(sampling) - SAMPLING_KEYS:
            raise WorkerError("SAMPLING_PROFILE_UNSUPPORTED")
        if not isinstance(sampling.get("do_sample"), bool):
            raise WorkerError("SAMPLING_PROFILE_INVALID")
        if self.model_id is not None and model != self.model_id:
            raise WorkerError("MODEL_ID_MISMATCH")
        if self.revision is not None and revision != self.revision:
            raise WorkerError("MODEL_REVISION_MISMATCH")
        kwargs: dict[str, Any] = {
            "tokenize": True,
            "add_generation_prompt": True,
            "return_tensors": "pt",
            "return_dict": True,
        }
        if enable_thinking is not None:
            kwargs["enable_thinking"] = enable_thinking
        try:
            inputs = self.tokenizer.apply_chat_template(messages, **kwargs)
            input_tokens = int(inputs["input_ids"].shape[-1])
            if not 1 <= input_tokens <= max_input_tokens:
                raise WorkerError("INPUT_TOKEN_BUDGET_EXCEEDED")
            inputs = inputs.to(self.model.device)
            self.torch.manual_seed(seed)
            self.torch.cuda.manual_seed_all(seed)
            generation_kwargs: dict[str, Any] = {
                "max_new_tokens": max_new_tokens,
                "do_sample": sampling["do_sample"],
                "use_cache": True,
                "eos_token_id": list(eos_token_ids),
                "pad_token_id": pad_token_id,
                "return_dict_in_generate": True,
            }
            if sampling["do_sample"]:
                for key in ("temperature", "top_p", "top_k", "min_p"):
                    if key in sampling:
                        generation_kwargs[key] = sampling[key]
            with self.torch.inference_mode():
                generated = self.model.generate(**inputs, **generation_kwargs)
            sequences = getattr(generated, "sequences", None)
            if sequences is None:
                raise WorkerError("GENERATION_OUTPUT_INVALID")
            new_tokens = sequences[0][input_tokens:]
            output_tokens = int(new_tokens.shape[-1])
            token_ids = new_tokens.tolist() if hasattr(new_tokens, "tolist") else None
            if not isinstance(token_ids, list) or any(
                not isinstance(value, int) or isinstance(value, bool) for value in token_ids
            ):
                raise WorkerError("GENERATION_OUTPUT_INVALID")
            finish_reason = classify_finish_reason(
                token_ids, eos_token_ids=eos_token_ids, max_new_tokens=max_new_tokens
            )
            text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            return GenerationResult(
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=finish_reason,
            )
        except WorkerError:
            raise
        except Exception as exc:
            raise WorkerError("MODEL_GENERATION_FAILED") from exc
