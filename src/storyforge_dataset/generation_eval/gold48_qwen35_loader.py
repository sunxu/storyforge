"""Thin Qwen3.8 conditional+LoRA loader for the frozen Gold48 four-arm profile.

Reuses the existing generation_eval.backend.TransformersGenerationBackend
tokenization, generation and finish-reason semantics. Imports GPU libraries only
when explicitly authorized; no code here uploads, submits Jobs or reads Gold
original replies. GPU smoke and runtime compatibility remain unverified.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from storyforge_dataset.hf_runtime.inputs import InputManager

from .backend import TransformersGenerationBackend
from .worker import WorkerError

MODEL = "Qwen/Qwen3.8-27B"
REVISION = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
EOS_IDS = (248046, 248044)
PAD_ID = 248044
ADAPTER_SIZE = 1_867_797_544
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BASE_PATH = re.compile(
    rf"(?:^|/)models--Qwen--Qwen3\.8-27B/snapshots/{REVISION}\Z"
)
TARGET_PREFIX = "^(model\\.language_model(?=\\.).*\\."
ALLOWED_TARGETS = {
    "o_proj", "gate_proj", "up_proj", "in_proj_b", "in_proj_z",
    "q_proj", "in_proj_qkv", "out_proj", "k_proj", "v_proj",
    "in_proj_a", "down_proj",
}
PUBLIC_CONFIG_NAMES = frozenset({
    "config.json", "generation_config.json", "chat_template.jinja",
    "merges.txt", "tokenizer.json", "tokenizer_config.json", "vocab.json",
})


def verify_adapter_config(config: Mapping[str, Any]) -> None:
    """CPU-only: require training-produced adapter geometry and target family."""
    source = config.get("base_model_name_or_path")
    target = config.get("target_modules")
    if not (
        isinstance(source, str) and BASE_PATH.search(source)
        and config.get("peft_type") == "LORA"
        and config.get("task_type") == "CAUSAL_LM"
        and type(config.get("r")) is int and config["r"] == 64
        and type(config.get("lora_alpha")) is int and config["lora_alpha"] == 128
        and config.get("inference_mode") is True
        and isinstance(target, str) and target.startswith(TARGET_PREFIX + "(")
        and target.endswith("))$")
    ):
        raise WorkerError("GOLD48_ADAPTER_IDENTITY_OR_GEOMETRY_HOLD")
    targets = target[len(TARGET_PREFIX) + 1:-3].split("|")
    if set(targets) != ALLOWED_TARGETS or len(targets) != len(ALLOWED_TARGETS):
        raise WorkerError("GOLD48_ADAPTER_TARGET_MODULES_HOLD")


def verify_base_snapshot_metadata(config: Mapping[str, Any],
                                  generation: Mapping[str, Any]) -> None:
    """CPU-only: lock architecture and stopping IDs to pinned Qwen revision."""
    if (config.get("model_type") != "qwen3_5"
            or config.get("architectures") != ["Qwen3_5ForConditionalGeneration"]
            or generation.get("eos_token_id") != list(EOS_IDS)
            or generation.get("pad_token_id") != PAD_ID):
        raise WorkerError("GOLD48_BASE_QWEN35_CONFIG_HOLD")


def _read_json(path: Path, max_bytes: int = 1024 * 1024) -> dict[str, Any]:
    try:
        obj = json.loads(InputManager.open_verified(path, max_bytes=max_bytes).read_bytes())
        if not isinstance(obj, dict):
            raise TypeError("NOT_JSON_OBJECT")
        return obj
    except (ValueError, TypeError, OSError) as exc:
        raise WorkerError("GOLD48_RUNTIME_METADATA_READ_HOLD") from exc


def _hash_adapter_weights(path: Path, expected_sha: str) -> None:
    """Memory-bounded SHA check: never read 1.8 GB adapter into RAM."""
    if not isinstance(expected_sha, str) or not SHA256.fullmatch(expected_sha):
        raise WorkerError("GOLD48_ADAPTER_EXPECTED_SHA_REQUIRED")
    if path.is_symlink() or not hasattr(os, "O_NOFOLLOW"):
        raise WorkerError("GOLD48_ADAPTER_PATH_HOLD")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size != ADAPTER_SIZE:
                raise WorkerError("GOLD48_ADAPTER_FILE_SIZE_HOLD")
            digest = hashlib.sha256()
            while True:
                data = os.read(fd, 8 * 1024 * 1024)
                if not data:
                    break
                digest.update(data)
            after = os.fstat(fd)
            if ((before.st_dev, before.st_ino, before.st_size,
                 before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns)):
                raise WorkerError("GOLD48_ADAPTER_CHANGED_HOLD")
            if digest.hexdigest() != expected_sha:
                raise WorkerError("GOLD48_ADAPTER_SHA_MISMATCH_HOLD")
        finally:
            os.close(fd)
    except OSError as exc:
        raise WorkerError("GOLD48_ADAPTER_READ_HOLD") from exc


def load_pinned_gold48_backend(
    *,
    adapter_dir: Path | None,
    expected_adapter_sha256: str | None,
    expected_template_sha256: str,
    runtime_authorized: bool = False,
    torch_module: Any | None = None,
    transformers_module: Any | None = None,
    peft_module: Any | None = None,
) -> TransformersGenerationBackend:
    """GPU-only explicit loader. Caller must independently enforce signed run auth.

    Passing runtime_authorized=True is necessary, never sufficient for a public
    Job or model generation authorization; no submitter calls this automatically.
    """
    if not runtime_authorized:
        raise WorkerError("GOLD48_RUNTIME_NOT_AUTHORIZED")
    if not isinstance(expected_template_sha256, str) or not SHA256.fullmatch(expected_template_sha256):
        raise WorkerError("GOLD48_TEMPLATE_SHA_REQUIRED")
    if (adapter_dir is None) != (expected_adapter_sha256 is None):
        raise WorkerError("GOLD48_ADAPTER_PIN_PAIR_REQUIRED")

    if adapter_dir is not None:
        if adapter_dir.is_symlink() or not adapter_dir.is_dir():
            raise WorkerError("GOLD48_ADAPTER_DIR_HOLD")
        adapter = _read_json(adapter_dir / "adapter_config.json")
        verify_adapter_config(adapter)
        _hash_adapter_weights(
            adapter_dir / "adapter_model.safetensors", expected_adapter_sha256
        )

    torch = torch_module or importlib.import_module("torch")
    transformers = transformers_module or importlib.import_module("transformers")
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise WorkerError("GOLD48_CUDA_BF16_REQUIRED_HOLD")
    model_class = getattr(transformers, "Qwen3_5ForConditionalGeneration", None)
    if model_class is None:
        raise WorkerError("GOLD48_QWEN35_CLASS_UNAVAILABLE_HOLD")
    try:
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            MODEL, revision=REVISION, trust_remote_code=False
        )
        template = tokenizer.chat_template
        if (not isinstance(template, str) or
                hashlib.sha256(template.encode("utf-8")).hexdigest() !=
                expected_template_sha256):
            raise WorkerError("GOLD48_CHAT_TEMPLATE_SHA_MISMATCH_HOLD")
        model = model_class.from_pretrained(
            MODEL, revision=REVISION, dtype=torch.bfloat16,
            device_map={"": 0}, trust_remote_code=False,
            low_cpu_mem_usage=True,
        )
        if adapter_dir is not None:
            peft = peft_module or importlib.import_module("peft")
            model = peft.PeftModel.from_pretrained(
                model, str(adapter_dir), is_trainable=False
            )
        model.eval()
        return TransformersGenerationBackend(
            tokenizer=tokenizer, model=model, torch_module=torch,
            model_id=MODEL, revision=REVISION
        )
    except WorkerError:
        raise
    except Exception as exc:
        raise WorkerError("GOLD48_QWEN35_LORA_LOAD_HOLD") from exc
