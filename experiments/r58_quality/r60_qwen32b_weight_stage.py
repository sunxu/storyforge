"""R60 pinned Qwen3-32B weight staging: CPU download; GPU localize.

No prompts, inference, training or model loading. Never stream weights into
Python heap. All output paths are fixed under operator-provided mount roots.

stage:     Hugging Face Hub -> durable bucket, stream + LFS SHA256 + manifest
localize:  durable bucket -> H200 local disk, SHA256 verified again
Both modes fail closed on mismatched revision or pre-existing corruption.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import time
from pathlib import Path

MODEL = "Qwen/Qwen3-32B"
REV = "9216db5781bf21249d130ec9da846c4624c16137"
SCHEMA = "storyforge_r60_qwen32b_weight_stage_safe_v1"
MANIFEST = "r60_weights_verified_manifest.json"
MIN_FREE_OVERHEAD = 20 * 1024**3
CHUNK = 8 * 1024 * 1024
ALLOWED_SMALL = {
    "config.json", "generation_config.json", "tokenizer.json",
    "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json",
    "vocab.json", "merges.txt", "tokenizer.model", "chat_template.jinja",
    "model.safetensors.index.json",
}
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HEX40 = re.compile(r"^[a-f0-9]{40}$")


class Hold(ValueError):
    pass


def emit(event: str, **details: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **details},
                     sort_keys=True, separators=(",", ":")), flush=True)


def allowed(name: str) -> bool:
    return (
        name in ALLOWED_SMALL
        or bool(re.fullmatch(r"model(?:-\d{5}-of-\d{5})?\.safetensors", name))
    )


def sha_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while data := stream.read(CHUNK):
            digest.update(data)
            count += len(data)
    return digest.hexdigest(), count


def safe_root(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise Hold("ROOT_NOT_DIRECTORY")
    # Never write into a repo mount or arbitrary relative path.
    if not root.is_absolute():
        raise Hold("ROOT_NOT_ABSOLUTE")


def check_existing(path: Path, expected_size: int,
                   expected_sha: str) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_symlink() or not path.is_file():
        raise Hold("EXISTING_OBJECT_NOT_REGULAR")
    if path.stat().st_size != expected_size:
        raise Hold("EXISTING_SIZE_MISMATCH")
    actual, _ = sha_file(path)
    if actual != expected_sha:
        raise Hold("EXISTING_SHA_MISMATCH")
    return True


def atomic_stream_copy(stream: object, destination: Path,
                       expected_size: int, expected_sha: str) -> None:
    # Only staging-owned partial files are cleaned on a retry. Complete
    # files are immutable; corrupted complete files require human review.
    partial = destination.with_name(destination.name + ".r60-partial")
    if partial.is_symlink():
        raise Hold("PARTIAL_SYMLINK_HOLD")
    if partial.exists():
        partial.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    total = 0
    fd = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            for piece in stream:
                if not piece:
                    continue
                total += len(piece)
                if total > expected_size:
                    raise Hold("STREAM_TOO_LARGE")
                h.update(piece)
                output.write(piece)
            output.flush()
            os.fsync(output.fileno())
        if total != expected_size or h.hexdigest() != expected_sha:
            raise Hold("STREAM_SIZE_OR_SHA_MISMATCH")
        os.rename(partial, destination)
    finally:
        if partial.exists():
            partial.unlink()


def frozen_manifest(root: Path) -> dict:
    path = root / MANIFEST
    if not path.is_file() or path.is_symlink():
        raise Hold("MANIFEST_MISSING")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise Hold("MANIFEST_INVALID") from exc
    if (not isinstance(data, dict) or data.get("schema") != SCHEMA
            or data.get("model") != MODEL or data.get("revision") != REV
            or not isinstance(data.get("files"), list)
            or not data["files"]):
        raise Hold("MANIFEST_INVALID")
    names = set()
    for item in data["files"]:
        if (not isinstance(item, dict)
                or set(item) != {"name", "sha256", "size"}
                or not isinstance(item["name"], str)
                or not allowed(item["name"])
                or item["name"] in names
                or not isinstance(item["sha256"], str)
                or not HEX64.fullmatch(item["sha256"])
                or type(item["size"]) is not int or item["size"] <= 0):
            raise Hold("MANIFEST_INVALID")
        names.add(item["name"])
    if "config.json" not in names or "model.safetensors.index.json" not in names:
        raise Hold("MANIFEST_MISSING_ESSENTIALS")
    if not any(name.endswith(".safetensors") for name in names):
        raise Hold("MANIFEST_NO_WEIGHTS")
    index_path = root / "model.safetensors.index.json"
    try:
        index = json.loads(index_path.read_text())
        shards = set(index["weight_map"].values())
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise Hold("INDEX_INVALID") from None
    if not shards or not shards.issubset(names):
        raise Hold("INDEX_SHARDS_MISMATCH")
    return data


def stage(bucket_root: Path) -> int:
    safe_root(bucket_root)
    if not HEX40.fullmatch(REV):
        raise Hold("REVISION_NOT_PINNED")
    import requests
    from huggingface_hub import HfApi, hf_hub_url

    api = HfApi()
    model_info = api.model_info(MODEL, revision=REV, files_metadata=True)
    if model_info.sha != REV:
        raise Hold("UPSTREAM_REVISION_MISMATCH")
    candidates = []
    for sibling in model_info.siblings:
        name = sibling.rfilename
        if not allowed(name):
            continue
        if not isinstance(sibling.size, int) or sibling.size <= 0:
            raise Hold("UPSTREAM_SIZE_UNKNOWN")
        lfs = sibling.lfs
        expected_sha = lfs.get("sha256") if isinstance(lfs, dict) else None
        if expected_sha is not None and not HEX64.fullmatch(expected_sha):
            raise Hold("UPSTREAM_HASH_INVALID")
        candidates.append((name, sibling.size, expected_sha))
    names = {x[0] for x in candidates}
    if (not candidates or "model.safetensors.index.json" not in names
            or "config.json" not in names
            or not any(x.endswith(".safetensors") for x in names)
            or any(sha is None for name, _, sha in candidates
                   if name.endswith(".safetensors"))):
        raise Hold("UPSTREAM_METADATA_INCOMPLETE")

    manifest_path = bucket_root / MANIFEST
    if manifest_path.exists() or manifest_path.is_symlink():
        existing = frozen_manifest(bucket_root)
        for item in existing["files"]:
            if not check_existing(bucket_root / item["name"],
                                  item["size"], item["sha256"]):
                raise Hold("VERIFIED_FILE_MISSING")
        emit("STAGE_ALREADY_VERIFIED", files=len(existing["files"]))
        return 0

    emit("STAGE_START", file_count=len(candidates),
         total_gib=round(sum(x[1] for x in candidates) / 1024**3, 2))
    manifest_files = []
    for index, (name, size, expected_sha) in enumerate(sorted(candidates), 1):
        dest = bucket_root / name
        # For small files without LFS metadata, we must download to calculate
        # the digest, then record it; no hashes are assumed.
        if expected_sha is not None and check_existing(dest, size, expected_sha):
            observed_sha = expected_sha
            emit("SHARD_REUSED", file_number=index, file_count=len(candidates))
        else:
            if dest.exists() or dest.is_symlink():
                raise Hold("UNVERIFIED_EXISTING_FILE")
            url = hf_hub_url(MODEL, name, revision=REV)
            with requests.get(url, stream=True, timeout=(30, 120)) as response:
                response.raise_for_status()
                # Without LFS SHA (small config/tokenizer files), calculate
                # expected hash from the downloaded stream using a temp file.
                if expected_sha is None:
                    part = dest.with_name(dest.name + ".r60-partial")
                    if part.exists() or part.is_symlink():
                        part.unlink()
                    fd = os.open(part, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    h = hashlib.sha256()
                    count = 0
                    with os.fdopen(fd, "wb") as output:
                        for piece in response.iter_content(chunk_size=CHUNK):
                            if piece:
                                count += len(piece)
                                if count > size:
                                    raise Hold("STREAM_TOO_LARGE")
                                h.update(piece)
                                output.write(piece)
                        output.flush()
                        os.fsync(output.fileno())
                    if count != size:
                        raise Hold("STREAM_SIZE_MISMATCH")
                    os.rename(part, dest)
                    observed_sha = h.hexdigest()
                else:
                    atomic_stream_copy(response.iter_content(chunk_size=CHUNK),
                                       dest, size, expected_sha)
                    observed_sha = expected_sha
            emit("SHARD_VERIFIED", file_number=index, file_count=len(candidates),
                 size_mib=round(size / 1048576, 1))
        manifest_files.append({"name": name, "size": size,
                               "sha256": observed_sha})
    # Recheck cross-file manifest and safetensors weight index before the
    # final completion marker is written. This does not reread 65GiB.
    summary = {"schema": SCHEMA, "model": MODEL, "revision": REV,
               "files": manifest_files}
    temp = bucket_root / (MANIFEST + ".r60-partial")
    if temp.exists() or temp.is_symlink():
        raise Hold("EXISTING_MANIFEST_PARTIAL")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(summary, output, sort_keys=True)
        output.flush()
        os.fsync(output.fileno())
    os.rename(temp, manifest_path)
    frozen_manifest(bucket_root)
    emit("STAGE_COMPLETE", files=len(manifest_files))
    return 0


def localize(bucket_root: Path, local_root: Path) -> int:
    safe_root(bucket_root)
    if local_root.exists() or local_root.is_symlink():
        raise Hold("LOCAL_DEST_EXISTS")
    if not local_root.is_absolute():
        raise Hold("LOCAL_ROOT_NOT_ABSOLUTE")
    manifest = frozen_manifest(bucket_root)
    required = sum(item["size"] for item in manifest["files"])
    free = shutil.disk_usage(local_root.parent).free
    emit("DISK_PREFLIGHT", needed_gib=round((required + MIN_FREE_OVERHEAD) / 1024**3, 2),
         free_gib=round(free / 1024**3, 2))
    if free < required + MIN_FREE_OVERHEAD:
        raise Hold("LOCAL_DISK_INSUFFICIENT")
    local_root.mkdir(mode=0o700)
    for index, item in enumerate(manifest["files"], 1):
        source = bucket_root / item["name"]
        if not source.is_file() or source.is_symlink():
            raise Hold("BUCKET_FILE_MISSING")
        with source.open("rb") as inp:
            atomic_stream_copy(iter(lambda: inp.read(CHUNK), b""),
                               local_root / item["name"],
                               item["size"], item["sha256"])
        emit("LOCAL_FILE_VERIFIED", file_number=index,
             file_count=len(manifest["files"]))
    # Manifest copy only after all data is verified.
    (local_root / MANIFEST).write_text(json.dumps(manifest, sort_keys=True))
    frozen_manifest(local_root)
    emit("LOCAL_WEIGHTS_READY", files=len(manifest["files"]),
         total_gib=round(required / 1024**3, 2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("stage", "localize"), required=True)
    parser.add_argument("--bucket-dir", type=Path, required=True)
    parser.add_argument("--local-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "stage":
            if args.local_dir is not None:
                raise Hold("INVALID_MODE_ARGUMENTS")
            return stage(args.bucket_dir)
        if args.local_dir is None:
            raise Hold("LOCAL_DIR_REQUIRED")
        return localize(args.bucket_dir, args.local_dir)
    except Exception as exc:  # noqa: BLE001 - do not print paths or tokens
        code = str(exc) if isinstance(exc, Hold) else "STAGING_IO_OR_NETWORK_HOLD"
        emit("STAGE_HOLD", reason_code=code)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
