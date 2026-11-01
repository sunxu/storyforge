#!/usr/bin/env python3
"""Stage sealed R58 GPU A/B inputs without a crosswalk or any GPU submission.

Creates isolated private work directories for the HF CLI local-volume sync.
Never includes the other reviewer's input or Owner mapping in a work directory.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import stat

from r58_hf_gpu_literary_reviewer import read_source

REVIEWER = Path(__file__).with_name("r58_hf_gpu_literary_reviewer.py")


def copy_private(src: Path, dst: Path):
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        with src.open("rb") as stream:
            while True:
                block = stream.read(1024 * 1024)
                if not block:
                    break
                out.write(block)
        out.flush()
        os.fsync(out.fileno())


def stage(pilot: Path, stage_dir: Path, repo: Path):
    if not pilot.is_absolute() or pilot.is_symlink() or not pilot.is_dir():
        raise ValueError("PILOT_DIR_INVALID")
    if (not stage_dir.is_absolute() or stage_dir.exists()
            or stage_dir.is_symlink() or not stage_dir.parent.is_dir()
            or stage_dir.parent.is_symlink()
            or stat.S_IMODE(stage_dir.parent.stat().st_mode) & 0o077
            or repo.resolve() == stage_dir.resolve()
            or repo.resolve() in stage_dir.resolve().parents):
        raise ValueError("STAGE_DESTINATION_INVALID")
    if not REVIEWER.is_file() or REVIEWER.is_symlink():
        raise ValueError("REVIEWER_SCRIPT_UNAVAILABLE")
    sources = {}
    for slot in ("A", "B"):
        path = pilot / f"reviewer_{slot}.private.jsonl"
        if (path.is_symlink() or not path.is_file()
                or stat.S_IMODE(path.stat().st_mode) != 0o600
                or path.stat().st_nlink != 1):
            raise ValueError("PRIVATE_REVIEWER_SOURCE_INVALID")
        sources[slot] = read_source(path)
    a_ids = {x["blind_id"] for x in sources["A"]}
    b_ids = {x["blind_id"] for x in sources["B"]}
    if a_ids & b_ids:
        raise ValueError("BLIND_SOURCE_IDS_OVERLAP")
    # Validate mapping is present locally, but do NOT copy/read its content.
    owner = pilot / "owner_crosswalk.private.json"
    if (owner.is_symlink() or not owner.is_file()
            or stat.S_IMODE(owner.stat().st_mode) != 0o600):
        raise ValueError("OWNER_CROSSWALK_MISSING_OR_UNSAFE")
    stage_dir.mkdir(mode=0o700)
    for slot in ("A", "B"):
        inp, out = stage_dir / f"input_{slot}", stage_dir / f"output_{slot}"
        inp.mkdir(mode=0o700)
        out.mkdir(mode=0o700)
        copy_private(pilot / f"reviewer_{slot}.private.jsonl",
                     inp / "source.private.jsonl")
        copy_private(REVIEWER, inp / "runner.py")
        if read_source(inp / "source.private.jsonl") != sources[slot]:
            raise ValueError("STAGED_INPUT_NOT_IDENTICAL")
    return {
        "schema": "r58_hf_gpu_blind_staging_safe_v1",
        "status": "R58_A_B_PRIVATE_GPU_STAGING_READY__NOT_SUBMITTED",
        "slots": 2, "cases_per_slot": 13,
        "owner_crosswalk_uploaded": False,
        "other_reviewer_input_uploaded_to_each_slot": False,
        "paid_gpu_submitted": False,
        "training_authorized": False,
        "quality_v1_admitted": 0,
        "private_text_emitted": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pilot-dir", required=True, type=Path)
    p.add_argument("--stage-dir", required=True, type=Path)
    p.add_argument("--repo-root", required=True, type=Path)
    a = p.parse_args()
    try:
        receipt, code = stage(a.pilot_dir, a.stage_dir, a.repo_root), 0
    except Exception:
        receipt = {
            "schema": "r58_hf_gpu_blind_staging_safe_v1",
            "status": "R58_A_B_GPU_STAGING_HOLD",
            "paid_gpu_submitted": False,
            "quality_v1_admitted": 0,
            "private_text_emitted": False,
        }
        code = 42
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
