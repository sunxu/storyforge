"""Pinned Transformers backend adapter for Qwen3 / GLM4 generation.

Imports torch/transformers lazily and loads weights only when explicitly
constructed. This module is not called by profile checks, plan generation, or CI.
"""
from __future__ import annotations

import hashlib
import importlib
import re
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.inputs import InputManager

from .worker import GenerationResult, WorkerError

SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAMPLING_KEYS = frozenset({"do_sample", "temperature", "top_p", "top_k", "min_p"})


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
        self._generation_index = 0
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
        template_path: Path | None = None,
        torch_module: Any | None = None,
        transformers_module: Any | None = None,
    ) -> TransformersGenerationBackend:
        if not SHA256.fullmatch(expected_template_sha256):
            raise WorkerError("CHAT_TEMPLATE_HASH_INVALID")
        torch = torch_module or importlib.import_module("torch")
        transformers = transformers_module or importlib.import_module("transformers")
        if not torch.cuda.is_available():
            raise WorkerError("CUDA_NOT_AVAILABLE")
        if not torch.cuda.is_bf16_supported():
            raise WorkerError("CUDA_BFLOAT16_UNSUPPORTED")

        try:
            tokenizer = transformers.AutoTokenizer.from_pretrained(
                model_id,
                revision=revision,
                trust_remote_code=False,
            )
            if template_source == "embedded_tokenizer_config":
                template = tokenizer.chat_template
                if not isinstance(template, str):
                    raise WorkerError("EMBEDDED_CHAT_TEMPLATE_MISSING")
                actual_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
            elif template_source == "standalone_chat_template.jinja":
                if template_path is None:
                    raise WorkerError("STANDALONE_CHAT_TEMPLATE_MISSING")
                try:
                    verified_template = InputManager.open_verified(
                        template_path,
                        max_bytes=1024 * 1024,
                        expected_sha256=expected_template_sha256,
                    )
                except (OSError, ValueError) as exc:
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
    ) -> GenerationResult:
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
            effective_seed = seed + self._generation_index
            self._generation_index += 1
            self.torch.manual_seed(effective_seed)
            self.torch.cuda.manual_seed_all(effective_seed)
            generation_kwargs: dict[str, Any] = {
                "max_new_tokens": max_new_tokens,
                "do_sample": sampling["do_sample"],
                "use_cache": True,
                "pad_token_id": self.tokenizer.pad_token_id,
            }
            if sampling["do_sample"]:
                for key in ("temperature", "top_p", "top_k", "min_p"):
                    if key in sampling:
                        generation_kwargs[key] = sampling[key]
            with self.torch.inference_mode():
                generated = self.model.generate(**inputs, **generation_kwargs)
            new_tokens = generated[0][input_tokens:]
            output_tokens = int(new_tokens.shape[-1])
            text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            return GenerationResult(
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except WorkerError:
            raise
        except Exception as exc:
            raise WorkerError("MODEL_GENERATION_FAILED") from exc
