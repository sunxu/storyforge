"""Deterministic CPU-only long-context synthetic input builder for R60 P4.

This prepares exactly one synthetic JSONL record and its manifest. It does not
authorize inference, start a GPU, access private cases, or submit HF Jobs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from .backend import download_pinned_tokenizer_snapshot
from .profiles import load_profile

FROZEN_SHA256 = "a58d02c757767f18deb8a4cb948a56be199c837c045d83648838868961e1037f"
ROLE_CHOICES = ("A", "B", "challenger")
SYNTHETIC_SENTENCE = (
    "合成负载校准段落：甲乙丙丁戊己庚辛壬癸；一二三四五六七八九十。"
    "这是公开构造的机械重复文字，不代表任何实际作品或私人对话。"
)


def _encode_count(tokenizer: Any, messages: list[dict[str, str]], role_config: dict[str, Any]) -> int:
    """Count tokens using the exact runtime chat-template options and prefix."""
    kwargs: dict[str, Any] = {
        "tokenize": True,
        "add_generation_prompt": True,
    }
    if role_config.get("enable_thinking") is not None:
        kwargs["enable_thinking"] = role_config["enable_thinking"]
    ids = tokenizer.apply_chat_template(messages, **kwargs)
    if not isinstance(ids, list) or any(not isinstance(i, int) for i in ids):
        raise ValueError("SYNTHETIC_CHAT_TEMPLATE_TOKENS_INVALID")
    prefix = role_config.get("generation_prefix")
    if prefix:
        prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
        if ids[-len(prefix_ids):] != prefix_ids:
            ids = ids + prefix_ids
    return len(ids)


def calibrate_synthetic_input(
    *,
    tokenizer: Any,
    role_config: dict[str, Any],
    target_tokens: int = 28600,
    ceiling_tokens: int = 28672,
    tolerance_tokens: int = 96,
) -> tuple[list[dict[str, str]], int]:
    """Binary-search repeated synthetic text; never return an over-budget input."""
    if not 1 <= target_tokens <= ceiling_tokens <= 32768:
        raise ValueError("SYNTHETIC_TOKEN_TARGET_INVALID")
    if not 0 <= tolerance_tokens <= 1024:
        raise ValueError("SYNTHETIC_TOLERANCE_INVALID")

    def measure(n: int) -> tuple[list[dict[str, str]], int]:
        content = (
            "请确认你正在处理一次人工生成的长上下文运行时测试，"
            "请简洁概括下文重复结构，不要猜测真实人物或故事。\n"
            + SYNTHETIC_SENTENCE * n
            + "\n结束。请输出一句简短中文确认。"
        )
        messages = [{"role": "user", "content": content}]
        return messages, _encode_count(tokenizer, messages, role_config)

    low, high = 0, 1
    while True:
        _, size = measure(high)
        if size >= target_tokens or high >= 65536:
            break
        high *= 2
    if size < target_tokens:
        raise ValueError("SYNTHETIC_TARGET_UNREACHABLE")
    best_messages, best_count = measure(0)
    while low <= high:
        mid = (low + high) // 2
        messages, count = measure(mid)
        if count <= target_tokens:
            if count >= best_count:
                best_messages, best_count = messages, count
            low = mid + 1
        else:
            high = mid - 1
    if not target_tokens - tolerance_tokens <= best_count <= ceiling_tokens:
        raise ValueError("SYNTHETIC_TOKEN_CALIBRATION_OUT_OF_TOLERANCE")
    return best_messages, best_count


def _verify_owner_authorization(doc: dict[str, Any], frozen_sha256: str) -> None:
    if (
        doc.get("schema") != "storyforge_r60_p4_staged_execution_authorization_v1"
        or doc.get("frozen_profile_sha256") != frozen_sha256
        or doc.get("stages", {}).get("synthetic_32k", {}).get("owner_authorized") is not True
        or doc.get("denied", {}).get("training_authorized") is not False
    ):
        raise ValueError("SYNTHETIC_STAGE_NOT_OWNER_AUTHORIZED")


def prepare(
    *,
    frozen_path: Path,
    authorization_path: Path,
    model_role: str,
    output_dir: Path,
    target_tokens: int = 28600,
) -> dict[str, Any]:
    """Prepare synthetic input; only tokenizer files are downloaded, never weights."""
    if model_role not in ROLE_CHOICES:
        raise ValueError("SYNTHETIC_MODEL_ROLE_INVALID")
    frozen_bytes = frozen_path.read_bytes()
    frozen_sha = hashlib.sha256(frozen_bytes).hexdigest()
    if frozen_sha != FROZEN_SHA256:
        raise ValueError("SYNTHETIC_FROZEN_SHA256_MISMATCH")
    profile = load_profile(frozen_path)
    if not (
        profile.get("profile_freeze_authorized") is True
        and profile.get("inference_authorized") is False
        and profile.get("gpu_authorized") is False
        and profile.get("training_authorized") is False
    ):
        raise ValueError("SYNTHETIC_FROZEN_AUTH_FLAGS_INVALID")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    _verify_owner_authorization(authorization, frozen_sha)

    role = profile["model_profiles"][model_role]
    from transformers import AutoTokenizer

    with tempfile.TemporaryDirectory(prefix="storyforge-synthetic-tokenizer-") as tmp:
        snapshot = download_pinned_tokenizer_snapshot(
            model_id=role["model"],
            revision=role["revision"],
            destination=Path(tmp) / "tokenizer",
            expected_file_hashes=profile["tokenizer_file_hashes"][model_role],
        )
        tokenizer = AutoTokenizer.from_pretrained(
            str(snapshot), local_files_only=True, trust_remote_code=False
        )
        if role["chat_template_source"] == "standalone_chat_template.jinja":
            tokenizer.chat_template = (snapshot / "chat_template.jinja").read_text(encoding="utf-8")
        messages, actual_tokens = calibrate_synthetic_input(
            tokenizer=tokenizer,
            role_config=role,
            target_tokens=target_tokens,
            ceiling_tokens=profile["input_budget_tokens"],
        )

    record = {"sample_id": "r60-synthetic-32k-" + model_role.lower(), "messages": messages}
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    if len(payload) > 16 * 1024 * 1024:
        raise ValueError("SYNTHETIC_INPUT_FILE_TOO_LARGE")
    manifest = {
        "schema": "storyforge_r60_generation_input_manifest_v1",
        "record_count": 1,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "max_input_tokens": profile["input_budget_tokens"],
        "max_new_tokens": profile["generation_budget_tokens"],
        "seed": profile["seed"],
    }
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("SYNTHETIC_OUTPUT_DIR_MUST_BE_NEW")
    output_dir.mkdir(mode=0o700, parents=False)
    (output_dir / "inputs.jsonl").write_bytes(payload)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    safe = {
        "schema": "storyforge_r60_synthetic_32k_input_safe_v1",
        "status": "SYNTHETIC_32K_INPUT_PREPARED__GPU_NOT_STARTED",
        "model_role": model_role,
        "input_tokens": actual_tokens,
        "target_tokens": target_tokens,
        "max_input_tokens": profile["input_budget_tokens"],
        "max_new_tokens": profile["generation_budget_tokens"],
        "input_sha256": manifest["sha256"],
        "frozen_profile_sha256": frozen_sha,
        "record_count": 1,
        "tokenizer_only": True,
        "gpu_started": False,
        "inference_started": False,
        "training_started": False,
        "hf_job_submitted": False,
        "private_values_emitted": False,
    }
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", required=True, type=Path)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--model-role", required=True, choices=ROLE_CHOICES)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--target-tokens", type=int, default=28600)
    args = parser.parse_args()
    try:
        safe = prepare(
            frozen_path=args.frozen,
            authorization_path=args.authorization,
            model_role=args.model_role,
            output_dir=args.output_dir,
            target_tokens=args.target_tokens,
        )
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        safe = {
            "schema": "storyforge_r60_synthetic_32k_input_safe_v1",
            "status": "SYNTHETIC_32K_INPUT_HOLD",
            "reason_code": str(exc) if isinstance(exc, ValueError) else "PREPARATION_FAILED",
            "gpu_started": False,
            "inference_started": False,
            "training_started": False,
            "hf_job_submitted": False,
            "private_values_emitted": False,
        }
        print(json.dumps(safe, sort_keys=True))
        return 2
    print(json.dumps(safe, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
