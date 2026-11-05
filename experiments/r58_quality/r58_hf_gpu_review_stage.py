#!/usr/bin/env python3
"""Stage sealed R58 GPU A/B inputs without a crosswalk or any GPU submission.

Creates isolated private work directories for the HF CLI local-volume sync.
Never includes the other reviewer's input or Owner mapping in a work directory.
"""
from __future__ import annotations
import argparse
import json
import hashlib
import os
from pathlib import Path
import stat

from r58_hf_gpu_literary_reviewer import read_source

REVIEWER = Path(__file__).with_name("r58_hf_gpu_literary_reviewer.py")
TOKEN_CORE = Path(__file__).resolve().parents[2] / "src/storyforge_dataset/token_preflight.py"
CPU_PREFLIGHT = Path(__file__).with_name("r58_hf_cpu_literary_token_preflight.py")
BUNDLED_CODE = {
    "runner.py": REVIEWER,
    "token_core.py": TOKEN_CORE,
    "token_preflight.py": CPU_PREFLIGHT,
}


def verify_code_sources():
    for path in BUNDLED_CODE.values():
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError("BUNDLED_CODE_UNAVAILABLE")


def checksum(path):
    return hashlib.sha256(path.read_bytes()).digest()


def ensure_private_stage(pilot: Path, stage_dir: Path, repo: Path):
    if (not pilot.is_absolute() or pilot.is_symlink() or not pilot.is_dir()
            or not stage_dir.is_absolute() or stage_dir.is_symlink()
            or not stage_dir.is_dir()
            or stat.S_IMODE(stage_dir.stat().st_mode) != 0o700
            or repo.resolve() == stage_dir.resolve()
            or repo.resolve() in stage_dir.resolve().parents):
        raise ValueError("EXISTING_STAGE_INVALID")
    owner = pilot / "owner_crosswalk.private.json"
    if (owner.is_symlink() or not owner.is_file()
            or stat.S_IMODE(owner.stat().st_mode) != 0o600):
        raise ValueError("OWNER_CROSSWALK_MISSING_OR_UNSAFE")
    for slot in ("A", "B"):
        original = pilot / f"reviewer_{slot}.private.jsonl"
        staged = stage_dir / f"input_{slot}" / "source.private.jsonl"
        inp, out = staged.parent, stage_dir / f"output_{slot}"
        if (not inp.is_dir() or inp.is_symlink() or
                not out.is_dir() or out.is_symlink()
                or stat.S_IMODE(inp.stat().st_mode) != 0o700
                or stat.S_IMODE(out.stat().st_mode) != 0o700):
            raise ValueError("STAGE_SLOT_INVALID")
        if (original.is_symlink() or not original.is_file()
                or staged.is_symlink() or not staged.is_file()
                or original.stat().st_nlink != 1 or staged.stat().st_nlink != 1
                or stat.S_IMODE(original.stat().st_mode) != 0o600
                or stat.S_IMODE(staged.stat().st_mode) != 0o600
                or checksum(original) != checksum(staged)):
            raise ValueError("PRIVATE_SOURCE_BYTES_CHANGED")
        read_source(staged)
        if list(out.glob("checkpoint_*.private.json")) or list(out.glob("reviewer_*.completed.private.jsonl")):
            raise ValueError("REVIEW_ALREADY_STARTED__REFRESH_FORBIDDEN")


def refresh_code(pilot: Path, stage_dir: Path, repo: Path):
    """Refresh only bundled code in existing private stage; never touch data/results."""
    ensure_private_stage(pilot, stage_dir, repo)
    verify_code_sources()
    # Two-phase validation: refuse unsafe existing paths before changing any.
    for slot in ("A", "B"):
        inp = stage_dir / f"input_{slot}"
        for filename in BUNDLED_CODE:
            target = inp / filename
            if (target.is_symlink() or (target.exists() and (
                not target.is_file() or target.stat().st_nlink != 1
                or stat.S_IMODE(target.stat().st_mode) != 0o600))):
                raise ValueError("STAGED_CODE_PATH_UNSAFE")
    changed = 0
    for slot in ("A", "B"):
        inp = stage_dir / f"input_{slot}"
        for filename, source in BUNDLED_CODE.items():
            target = inp / filename
            if target.exists() and checksum(target) == checksum(source):
                continue
            temp = inp / (filename + ".new")
            if temp.exists() or temp.is_symlink():
                raise ValueError("STAGED_TEMP_EXISTS")
            try:
                copy_private(source, temp)
                os.replace(temp, target)
            finally:
                if temp.exists():
                    temp.unlink()
            changed += 1
    return {
        "schema": "r58_hf_gpu_blind_staging_safe_v1",
        "status": "R58_A_B_PRIVATE_CODE_REFRESHED__SOURCES_UNCHANGED",
        "slots": 2, "code_files_updated": changed,
        "owner_crosswalk_uploaded": False,
        "paid_gpu_submitted": False, "private_text_emitted": False,
        "quality_v1_admitted": 0, "training_authorized": False,
    }



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
    verify_code_sources()
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
        for filename, code in BUNDLED_CODE.items():
            copy_private(code, inp / filename)
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
    p.add_argument("--refresh-code", action="store_true",
                   help="update code only in an existing PRIVATE stage; never overwrite blind data")
    a = p.parse_args()
    try:
        if a.refresh_code:
            receipt = refresh_code(a.pilot_dir, a.stage_dir, a.repo_root)
        else:
            receipt = stage(a.pilot_dir, a.stage_dir, a.repo_root)
        code = 0
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
