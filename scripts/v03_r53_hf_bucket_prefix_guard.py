#!/usr/bin/env python3
"""Read-only, fail-closed check of exact HF Bucket run paths.

Do NOT infer object existence from `hf buckets ls` exit status: empty prefixes
may yield a successful listing with no objects. Uses list_bucket_tree; never
writes/deletes objects or launches an HF Job.
"""
from __future__ import annotations

import argparse
import re
import sys

BUCKET = "adradar/storyforge-training"
BASE = "preflight/v03-r53/cpu40/runs"
RUN_KEY = re.compile(r"r53-cpu40-[0-9]{8}T[0-9]{6}Z-[0-9]{6}\Z")
EXPECTED = frozenset({
    "SHA256SUMS.txt",
    "code/v03_r53_hf_cpu40_audit.py",
    "code/v03_r53_hf_cpu40_worker.sh",
    "code/hf_label_mask_audit.py",
    "private_stage/STAGED_TRAIN_NOT_ADMITTED.jsonl",
    "private_stage/STAGED_VALIDATION_NOT_ADMITTED.jsonl",
    "private_stage/STAGED_31_9_SOURCE_HASH_MANIFEST_PRIVATE.json",
})


def check(mode: str, run_key: str, api) -> str:
    if not RUN_KEY.fullmatch(run_key):
        raise ValueError("R53_INVALID_RUN_KEY")
    prefix = f"{BASE}/{run_key}/"
    # Do not swallow authentication failures, access denials or API errors.
    entries = list(api.list_bucket_tree(BUCKET, prefix=prefix, recursive=True))
    names: set[str] = set()
    for entry in entries:
        path = getattr(entry, "path", None)
        kind = getattr(entry, "type", None)
        if not isinstance(path, str) or not path.startswith(prefix):
            raise ValueError("R53_REMOTE_LIST_INVALID_ENTRY")
        if kind == "directory":
            if mode == "empty":
                raise ValueError("R53_REMOTE_RUN_PREFIX_ALREADY_EXISTS")
            continue
        name = path[len(prefix):]
        if not name or name in names:
            raise ValueError("R53_REMOTE_LIST_DUPLICATE_OR_EMPTY_ENTRY")
        names.add(name)
    if mode == "empty":
        if names:
            raise ValueError("R53_REMOTE_RUN_PREFIX_ALREADY_EXISTS")
        return "R53_REMOTE_RUN_PREFIX_AVAILABLE"
    if mode == "ready":
        if names != EXPECTED:
            missing = sorted(EXPECTED - names)
            extra = sorted(names - EXPECTED)
            raise ValueError(f"R53_REMOTE_STAGE_NOT_READY missing={missing} extra={extra}")
        return "R53_REMOTE_STAGE_FILES_PRESENT"
    raise ValueError("R53_INVALID_PREFIX_GUARD_MODE")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["empty", "ready"])
    parser.add_argument("run_key")
    args = parser.parse_args()
    try:
        from huggingface_hub import HfApi
        print(check(args.mode, args.run_key, HfApi()), flush=True)
        return 0
    except Exception as exc:
        print(f"R53_REMOTE_PREFIX_CHECK_BLOCKED: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
