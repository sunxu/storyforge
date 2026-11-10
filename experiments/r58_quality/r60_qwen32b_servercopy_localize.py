"""Qwen3-32B: verify Hub server-copy bucket snapshot into H200 local SSD.

Read-only Bucket mount; local-only create. Gets pinned Hub file metadata for
independent weight LFS digests, then verifies streamed local copy. No GPU
allocation, model load, review prompts, or private output. This is intended
to run before r60_qwen32b_local_smoke.py in the SAME H200 Job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

MODEL = "Qwen/Qwen3-32B"
REV = "9216db5781bf21249d130ec9da846c4624c16137"
SCHEMA = "storyforge_r60_qwen32b_weight_stage_safe_v1"
MANIFEST = "r60_weights_verified_manifest.json"
CHUNK = 8 * 1024 * 1024
OVERHEAD = 20 * 1024**3
SMALL = {
    "config.json", "generation_config.json", "tokenizer.json",
    "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json",
    "vocab.json", "merges.txt", "tokenizer.model", "chat_template.jinja",
    "model.safetensors.index.json",
}
SHARD = re.compile(r"model-\d{5}-of-\d{5}\.safetensors\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


class Hold(ValueError):
    pass


def emit(event: str, **values: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **values},
                     sort_keys=True, separators=(",", ":")), flush=True)


def inventory(model_info: object) -> list[dict]:
    if getattr(model_info, "sha", None) != REV:
        raise Hold("UPSTREAM_REVISION_MISMATCH")
    found = {}
    for file in model_info.siblings:
        name = file.rfilename
        if name not in SMALL and not SHARD.fullmatch(name):
            continue
        size = getattr(file, "size", None)
        if type(size) is not int or size <= 0 or name in found:
            raise Hold("UPSTREAM_METADATA_INVALID")
        lfs = getattr(file, "lfs", None)
        digest = lfs.get("sha256") if isinstance(lfs, dict) else None
        if SHARD.fullmatch(name) and (not isinstance(digest, str)
                                     or not HASH.fullmatch(digest)):
            raise Hold("UPSTREAM_WEIGHT_SHA_MISSING")
        found[name] = {"name": name, "size": size, "upstream_sha": digest}
    shards = sorted(x for x in found if SHARD.fullmatch(x))
    if (len(shards) != 17 or set(shards) != {
            f"model-{i:05d}-of-00017.safetensors" for i in range(1, 18)}
            or not {"config.json", "model.safetensors.index.json",
                    "tokenizer.json"}.issubset(found)):
        raise Hold("UPSTREAM_INVENTORY_MISMATCH")
    return sorted(found.values(), key=lambda x: x["name"])


def copy_checked(source: Path, dest: Path, size: int,
                 upstream_sha: str | None,
                 *, verify_weight_sha: bool = True) -> str:
    if source.is_symlink() or not source.is_file():
        raise Hold("SOURCE_NOT_REGULAR")
    if source.stat().st_size != size:
        raise Hold("BUCKET_SIZE_MISMATCH")
    part = dest.with_name(dest.name + ".r60-partial")
    if part.exists() or part.is_symlink() or dest.exists() or dest.is_symlink():
        raise Hold("DEST_EXISTS_HOLD")
    h = hashlib.sha256()
    count = 0
    fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as inp:
            while piece := inp.read(CHUNK):
                count += len(piece)
                if count > size:
                    raise Hold("BUCKET_STREAM_TOO_LARGE")
                if verify_weight_sha or upstream_sha is None:
                    h.update(piece)
                output.write(piece)
            output.flush()
            os.fsync(output.fileno())
        digest = (h.hexdigest() if verify_weight_sha or upstream_sha is None
                  else upstream_sha)
        if count != size or (verify_weight_sha and upstream_sha is not None
                             and digest != upstream_sha):
            raise Hold("BUCKET_WEIGHT_INTEGRITY_HOLD")
        os.rename(part, dest)
        return digest
    finally:
        if part.exists():
            part.unlink()


def run(bucket: Path, local: Path, model_info: object,
        *, verify_weight_sha: bool = True) -> dict:
    if (not bucket.is_absolute() or bucket.is_symlink()
            or not bucket.is_dir()):
        raise Hold("BUCKET_DIR_HOLD")
    if (not local.is_absolute() or local.is_symlink()
            or local.exists() or not local.parent.is_dir()):
        raise Hold("LOCAL_DIR_HOLD")
    manifest_items = inventory(model_info)
    required = sum(item["size"] for item in manifest_items)
    free = shutil.disk_usage(local.parent).free
    emit("LOCAL_DISK_PREFLIGHT", needed_gib=round((required + OVERHEAD) / 1024**3, 2),
         free_gib=round(free / 1024**3, 2),
         files_expected=len(manifest_items))
    if free < required + OVERHEAD:
        raise Hold("LOCAL_DISK_INSUFFICIENT")
    local.mkdir(mode=0o700)
    verified = []
    for index, item in enumerate(manifest_items, 1):
        actual = copy_checked(bucket / item["name"], local / item["name"],
                              item["size"], item["upstream_sha"],
                              verify_weight_sha=verify_weight_sha)
        verified.append({"name": item["name"], "size": item["size"],
                         "sha256": actual})
        emit("LOCAL_FILE_VERIFIED", file_number=index,
             file_count=len(manifest_items))
    index_data = json.loads((local / "model.safetensors.index.json").read_text())
    refs = set(index_data["weight_map"].values())
    if refs != {item["name"] for item in verified if SHARD.fullmatch(item["name"])}:
        raise Hold("WEIGHT_INDEX_MISMATCH")
    manifest = {"schema": SCHEMA, "model": MODEL, "revision": REV,
                "integrity_mode": ("sha256-verified" if verify_weight_sha
                                   else "size-only-upstream-sha-declared"),
                "files": verified}
    target = local / MANIFEST
    with target.open("x") as fp:
        json.dump(manifest, fp, sort_keys=True)
        fp.flush()
        os.fsync(fp.fileno())
    emit("LOCAL_WEIGHTS_READY", files=len(verified),
         full_weight_sha_verified=verify_weight_sha,
         integrity_mode=manifest["integrity_mode"],
         total_gib=round(required / 1024**3, 2))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket-dir", type=Path, required=True)
    parser.add_argument("--local-dir", type=Path, required=True)
    parser.add_argument("--skip-weight-sha", action="store_true",
                        help="Check weight size and pinned upstream metadata only; "
                             "do not hash large copied shards")
    args = parser.parse_args()
    try:
        from huggingface_hub import HfApi

        info = HfApi().model_info(MODEL, revision=REV, files_metadata=True)
        run(args.bucket_dir, args.local_dir, info,
            verify_weight_sha=not args.skip_weight_sha)
        return 0
    except Exception as exc:  # noqa: BLE001 - redact bucket paths and tokens
        emit("LOCALIZE_HOLD", reason_code=(
            str(exc) if isinstance(exc, Hold)
            else "LOCALIZE_RUNTIME_OR_NETWORK_ERROR"))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
