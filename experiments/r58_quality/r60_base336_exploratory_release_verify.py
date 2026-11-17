"""Independent, read-only R60 336-only exploratory release verification.

No training admission, no GPU, no network or model weights. This checks actual
private JSONL bytes against the immutable release manifest, not source claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import r60_base336_exploratory_split as publisher
import r60_real_private_batch as private

SAFE = "storyforge_r60_base336_exploratory_release_verify_safe_v1"
MANIFEST = "R60_BASE336_EXPLORATORY_MANIFEST_PRIVATE.json"
ROWS = {"train": 293, "validation": 43}
STORIES = {"train": 146, "validation": 26}


class Hold(ValueError):
    pass


def _read_release_file(path: Path, maximum: int, *, staged: bool) -> bytes:
    if staged:
        from storyforge_dataset.hf_runtime import InputManager
        return InputManager.open_verified(path, max_bytes=maximum).read_bytes()
    return private.read_private(path, maximum)


def _verify(directory: Path, *, staged: bool) -> dict:
    if staged:
        import stat

        if (directory.is_symlink() or not directory.is_dir()
                or stat.S_IMODE(directory.stat().st_mode) != 0o700):
            raise Hold("STAGED_RELEASE_DIRECTORY_HOLD")
        for item in directory.iterdir():
            if (item.is_symlink() or not item.is_file()
                    or stat.S_IMODE(item.stat().st_mode) != 0o600):
                raise Hold("STAGED_RELEASE_FILE_MODE_HOLD")
    else:
        private.private_dir(directory, create=False)
    actual = {p.name for p in directory.iterdir()}
    if actual != {"train.jsonl", "validation.jsonl", MANIFEST}:
        raise Hold("RELEASE_FILESET_HOLD")
    manifest_raw = _read_release_file(
        directory / MANIFEST, private.MAX_CAPTURE_BYTES, staged=staged
    )
    doc = json.loads(manifest_raw)
    if (type(doc) is not dict
            or doc.get("schema") != publisher.SCHEMA
            or doc.get("status") !=
            "EXPLORATORY_TRAIN_VAL_ONLY__NOT_FORMALLY_ADMITTED"
            or doc.get("case_pool") != 336
            or doc.get("train_admitted") != 0
            or doc.get("gpu_started") is not False):
        raise Hold("MANIFEST_CONTRACT_HOLD")
    stats = doc.get("statistics")
    if (type(stats) is not dict or stats.get("rows") != ROWS
            or stats.get("stories") != STORIES
            or stats.get("known_world_group_count") != 8
            or stats.get("crossing_known_world_groups_after_split") != 0
            or stats.get("excluded_known5") != 3
            or stats.get("semantic_world_isolation_verified") is not False
            or stats.get("r50_semantic_isolation_verified") is not False
            or stats.get("reviewer_execution_independence_verified") is not False
            or stats.get("input_contract") != "THREE_PERSISTED_MESSAGES_NO_SYSTEM"):
        raise Hold("SPLIT_CONTRACT_HOLD")
    hashes = doc.get("data_sha256")
    if (type(hashes) is not dict or set(hashes) != set(ROWS)
            or any(type(value) is not str or len(value) != 64
                   for value in hashes.values())):
        raise Hold("DATA_DIGEST_CONTRACT_HOLD")
    for part, expected in ROWS.items():
        raw = _read_release_file(
            directory / f"{part}.jsonl", publisher.MAX_DATA_FILE, staged=staged
        )
        if hashlib.sha256(raw).hexdigest() != hashes[part]:
            raise Hold("DATA_DIGEST_MISMATCH_HOLD")
        lines = raw.splitlines()
        if len(lines) != expected:
            raise Hold("DATA_ROW_COUNT_HOLD")
        for line in lines:
            record = json.loads(line)
            if type(record) is not dict or set(record) != {"messages"}:
                raise Hold("DATA_ROW_SCHEMA_HOLD")
            msgs = record["messages"]
            if (type(msgs) is not list or len(msgs) != 4
                    or [m.get("role") for m in msgs] !=
                    ["user", "assistant", "user", "assistant"]
                    or any(type(m) is not dict
                           or set(m) != {"role", "content"}
                           or type(m["content"]) is not str
                           or not m["content"] for m in msgs)):
                raise Hold("DATA_MESSAGE_CONTRACT_HOLD")
    return {
        "schema": SAFE,
        "status": "BASE336_EXPLORATORY_RELEASE_BYTES_VERIFIED__GPU_HOLD",
        "train_rows": ROWS["train"],
        "validation_rows": ROWS["validation"],
        "manifest_verified": True,
        "sha256_verified": True,
        "final_collator_verified": False,
        "gpu_stage_prepared": False,
        "train_admitted": 0,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def verify(directory: Path) -> dict:
    """Verify the Owner Mac release under its existing private-root guard."""
    return _verify(directory, staged=False)


def verify_staged(directory: Path) -> dict:
    """Verify an exact read-only Stage copy without weakening the Mac private-root guard."""
    return _verify(directory, staged=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        print(json.dumps(verify(args.release_dir), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - never expose private values or paths
        print(json.dumps({
            "schema": SAFE, "status": "BASE336_EXPLORATORY_RELEASE_VERIFY_HOLD",
            "gpu_started": False, "train_admitted": 0,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
