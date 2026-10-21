#!/usr/bin/env python3
"""HF Bucket R54 run prefix guard: enumeration, never list-command exit status."""
from __future__ import annotations
import argparse
import re
import sys

BUCKET = "adradar/storyforge-training"
PREFIX = "preflight/v03-r54/gpu/runs"
EXPERIMENTS = "experiments/v03-r54"
SUBMISSIONS = "preflight/v03-r54/gpu/submissions"
FILES = frozenset({
    "SHA256SUMS.txt",
    "config/r54.yaml",
    "private/release/train.jsonl",
    "private/release/validation.jsonl",
    "private/release/R53_RELEASE_RECEIPT.json",
    "private/R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json",
    "private/R53_CPU40_OWNER_INTAKE_VERIFIED.json",
    "code/v03_r54_gpu_runner.py",
    "code/v03_r54_gpu_worker.sh",
    "code/v03_r54_gpu_readiness_v2.py",
    "code/v03_r54_last_step_checkpoint_gate.py",
    "code/hf_label_mask_audit.py",
    "code/hf_smoke_guard.py",
    "code/hf_job_runner.py",
})
RUN_KEY = re.compile(r"r54-v2-[0-9]{8}T[0-9]{6}Z-[0-9]{6}\Z")

def collect(api, prefix: str) -> set[str]:
    paths=set()
    for entry in api.list_bucket_tree(BUCKET,prefix=prefix,recursive=True):
        p=getattr(entry,"path",None)
        kind=getattr(entry,"type",None)
        if not isinstance(p,str) or not p.startswith(prefix):
            raise ValueError("R54_REMOTE_INVALID_LIST_ENTRY")
        if kind=="directory":
            # An already-created empty directory is still considered occupied.
            raise ValueError("R54_REMOTE_PREFIX_HAS_DIRECTORY")
        rel=p[len(prefix):]
        if not rel or rel in paths:
            raise ValueError("R54_REMOTE_DUPLICATE_OR_EMPTY")
        paths.add(rel)
    return paths

def check(mode: str,key: str,api) -> str:
    if not RUN_KEY.fullmatch(key):
        raise ValueError("R54_INVALID_RUN_KEY")
    staged=collect(api,f"{PREFIX}/{key}/")
    if collect(api,f"{SUBMISSIONS}/{key}/"):
        raise ValueError("R54_RUN_KEY_ALREADY_SUBMITTED__NO_AUTOMATIC_RETRY")
    if mode=="empty":
        if staged: raise ValueError("R54_REMOTE_STAGE_ALREADY_EXISTS")
        # Never reuse a run whose experiment directory already has artifacts.
        if collect(api,f"{EXPERIMENTS}/{key}/"):
            raise ValueError("R54_REMOTE_EXPERIMENT_ALREADY_EXISTS")
        return "R54_REMOTE_UNIQUE_RUN_PREFIX_AVAILABLE"
    if mode=="ready":
        if staged!=FILES:
            raise ValueError(f"R54_STAGE_INCOMPLETE missing={sorted(FILES-staged)} extra={sorted(staged-FILES)}")
        if collect(api,f"{EXPERIMENTS}/{key}/"):
            raise ValueError("R54_EXPERIMENT_PREFIX_ALREADY_EXISTS")
        return "R54_REMOTE_STAGE_COMPLETE__NO_GPU_JOB"
    raise ValueError("R54_INVALID_GUARD_MODE")

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["empty","ready"])
    p.add_argument("run_key")
    a=p.parse_args()
    try:
        from huggingface_hub import HfApi
        print(check(a.mode,a.run_key,HfApi()),flush=True)
        return 0
    except Exception as exc:
        print("R54_REMOTE_GUARD_BLOCKED:",str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
