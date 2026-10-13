#!/usr/bin/env python3
"""Read-only exact-SHA check for private pre-GPU StoryForge v0.2 Git LFS assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PREFIX = Path("evaluations/v0.2/training-readiness/20261013")


def hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(2 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify(root: Path) -> None:
    manifest = json.loads((root / PREFIX / "SOURCE_ARCHIVE_MANIFEST.json").read_text())
    required = manifest["required_files"]
    if len(required) != 4 or len({v["archive_name"] for v in required}) != 4:
        raise ValueError("manifest count or duplicate error")
    for item in required:
        p = root / PREFIX / "private" / item["archive_name"]
        if not p.is_file() or p.stat().st_size != item["size_bytes"]:
            raise ValueError(f"missing or wrong size (LFS pointer?): {p}")
        if hash_file(p) != item["sha256"]:
            raise ValueError(f"hash mismatch: {p.name}")
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                bad = z.testzip()
                if bad:
                    raise ValueError(f"ZIP CRC error: {bad}")
        else:
            r = json.loads(p.read_text())
            if not (r.get("checked") == r.get("consistent") == 40
                    and r.get("status") == "COLLATOR_INTERNAL_CONSISTENCY_ONLY"
                    and r.get("training_performed") is False):
                raise ValueError("R18 report does not match the audited no-training run")
        print("ARCHIVE_SHA256_PASS", item["archive_name"], item["sha256"])
    if manifest["train_admission"] != "PENDING_NOT_APPROVED":
        raise ValueError("unapproved train-state change")
    print("SOURCE_PRE_GPU_ARCHIVE_LOCAL_PASS_ONLY (not evidence of remote LFS)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    verify(args.root.resolve())
