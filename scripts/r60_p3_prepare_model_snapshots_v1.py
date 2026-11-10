"""Download only pinned R60 P3 tokenizer/config/template files; never model weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MODEL_PINS = {
    "A": ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"),
    "B": ("zai-org/GLM-4-32B-0414", "8dea913c41b543527c2860fb6f3c15c202f24aeb"),
    "challenger": (
        "zai-org/GLM-Z1-32B-0414",
        "8eb2858992c1f749e2a6d4075455decc2484722d",
    ),
}
ALLOWLIST = {
    "A": (
        "config.json", "generation_config.json", "merges.txt",
        "tokenizer.json", "tokenizer_config.json", "vocab.json",
    ),
    "B": (
        "chat_template.jinja", "config.json", "generation_config.json",
        "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
    ),
    "challenger": (
        "chat_template.jinja", "config.json", "generation_config.json",
        "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
    ),
}
REQUIRED = {
    role: set(names) for role, names in ALLOWLIST.items()
}
WEIGHT_SUFFIXES = {
    ".safetensors", ".bin", ".pt", ".pth", ".gguf", ".onnx", ".h5",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_snapshots(output_root: Path, downloader=None) -> dict:
    if not output_root.is_absolute() or output_root.exists() or output_root.is_symlink():
        raise ValueError("P3_OUTPUT_ROOT_MUST_BE_ABSENT_ABSOLUTE")
    if not output_root.parent.is_dir() or output_root.parent.is_symlink():
        raise ValueError("P3_OUTPUT_PARENT_INVALID")
    if downloader is None:
        from huggingface_hub import snapshot_download
        downloader = snapshot_download

    output_root.mkdir(mode=0o700)
    models = {}
    for role, (repo_id, revision) in MODEL_PINS.items():
        folder = output_root / role / revision
        folder.parent.mkdir(mode=0o700)
        downloader(
            repo_id=repo_id,
            repo_type="model",
            revision=revision,
            local_dir=str(folder),
            allow_patterns=list(ALLOWLIST[role]),
            token=False,
        )
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("P3_SNAPSHOT_DIRECTORY_INVALID")
        files = {}
        for name in ALLOWLIST[role]:
            path = folder / name
            if not path.is_file() or path.is_symlink():
                raise ValueError("P3_REQUIRED_FILE_MISSING")
            files[name] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in WEIGHT_SUFFIXES:
                raise ValueError("P3_MODEL_WEIGHT_DETECTED")
        models[role] = {
            "model": repo_id,
            "revision": revision,
            "files": files,
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files.values()),
            "model_weights_downloaded": False,
        }
    return {
        "schema": "storyforge_r60_p3_model_files_safe_v1",
        "status": "P3_PINNED_TOKENIZER_FILES_READY__NO_WEIGHTS",
        "model_count": len(models),
        "models": models,
        "model_weights_downloaded": False,
        "inference_calls": 0,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "training_authorized": False,
        "private_values_emitted": False,
    }


def serialize_safe(safe: dict) -> str:
    """Serialize valid JSON with a real trailing newline."""
    return json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--safe-output", type=Path)
    args = parser.parse_args()
    try:
        safe = prepare_snapshots(args.output_root)
        encoded = serialize_safe(safe)
        if args.safe_output:
            if not args.safe_output.is_absolute() or args.safe_output.exists():
                raise ValueError("P3_SAFE_OUTPUT_MUST_BE_ABSENT_ABSOLUTE")
            args.safe_output.write_text(encoded, encoding="utf-8")
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, OSError, ImportError, RuntimeError, TypeError) as exc:
        reason = str(exc) if re.fullmatch(r"P3_[A-Z0-9_]+", str(exc)) else "P3_DOWNLOAD_FAILED"
        print(json.dumps({
            "schema": "storyforge_r60_p3_model_files_safe_v1",
            "status": "P3_MODEL_FILES_HOLD",
            "reason_code": reason,
            "model_weights_downloaded": False,
            "inference_calls": 0,
            "hf_jobs_submitted": 0,
            "gpu_started": False,
            "training_authorized": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
