"""Build a new private CPU2 RO/RW stage from the verified frozen stage.

No HF API, upload, run_job, model weights or mutation of the original 27 files.
Create-only destination; all source file bytes copied verbatim except replacing
the legacy worker with the reviewed standalone v2 CPU-only worker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

try:
    from scripts import r60_common2_hf_cpu_image_probe as probe
    from scripts import r60_common2_hf_cpu_image_retry as retry
    from scripts import r60_common2_hf_cpu_stage as stage_contract
except ModuleNotFoundError:
    import r60_common2_hf_cpu_image_probe as probe
    import r60_common2_hf_cpu_image_retry as retry
    import r60_common2_hf_cpu_stage as stage_contract

WORKER = Path(__file__).with_name("r60_common2_hf_cpu_worker_v2.sh")
OLD_WORKER = "code/scripts/r60_common2_hf_cpu_worker.sh"
NEW_WORKER = "code/scripts/r60_common2_hf_cpu_worker_v2.sh"


def build(old_stage: Path, destination: Path, new_key: str) -> dict:
    if old_stage.name != retry.RUN_KEY or old_stage.is_symlink():
        raise ValueError("FROZEN_STAGE_BINDING_HOLD")
    if not stage_contract.RUN_KEY.fullmatch(new_key) or new_key == retry.RUN_KEY:
        raise ValueError("NEW_RUN_KEY_HOLD")
    if destination.name != new_key or destination.exists() or destination.is_symlink():
        raise ValueError("CREATE_ONLY_DESTINATION_HOLD")
    if stat.S_IMODE(old_stage.stat().st_mode) & 0o077:
        raise ValueError("FROZEN_STAGE_MODE_HOLD")
    probe.check_local(old_stage, retry.RUN_KEY)
    if not WORKER.is_file() or WORKER.is_symlink():
        raise ValueError("WORKER_SOURCE_HOLD")
    worker = WORKER.read_bytes()
    if not worker.startswith(b"#!/usr/bin/env bash") or b"swift sft" in worker:
        raise ValueError("WORKER_POLICY_HOLD")

    source_lines = (old_stage / "SHA256SUMS.txt").read_text().splitlines()
    files = {}
    for line in source_lines:
        _, _, rel = line.partition("  ")
        if rel != OLD_WORKER:
            files[rel] = (old_stage / rel).read_bytes()
    files[NEW_WORKER] = worker
    if len(files) != len(source_lines):
        raise ValueError("WORKER_REPLACEMENT_HOLD")

    destination.mkdir(mode=0o700)
    for rel, data in sorted(files.items()):
        target = destination / rel
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
    manifest = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {rel}\n"
        for rel, data in sorted(files.items())
    ).encode()
    fd = os.open(destination / "SHA256SUMS.txt", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(manifest)
    probe.check_local(destination, new_key)
    return {
        "schema": "storyforge_r60_common2_cpu2_v2_stage_safe_v1",
        "status": "CPU2_V2_NEW_STAGE_READY__NO_SYNC_NO_JOB",
        "files_staged": len(files) + 1,
        "original_stage_untouched": True,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "train_admitted": 0,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--old-stage", type=Path, required=True)
    p.add_argument("--new-stage", type=Path, required=True)
    p.add_argument("--new-run-key", required=True)
    a = p.parse_args()
    try:
        result = build(a.old_stage, a.new_stage, a.new_run_key)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({
            "schema": "storyforge_r60_common2_cpu2_v2_stage_safe_v1",
            "status": "CPU2_V2_STAGE_HOLD",
            "hf_jobs_submitted": 0,
            "gpu_started": False,
            "train_admitted": 0,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
