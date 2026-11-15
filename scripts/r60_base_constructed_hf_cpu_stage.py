"""Create-only SHA stage for three synthetic Base constructed-System HF CPU cases.

No private story data. Uses existing shared dependency resolver and HF
orchestrator; does not itself submit jobs or contact HF.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import r60_common2_wrapped_hf_stage as shared

from storyforge_dataset.hf_runtime import InputManager

SCHEMA = "storyforge_r60_base_constructed_hf_cpu_stage_private_v1"
RUN_RE = re.compile(r"r60-constructcpu-\d{8}T\d{6}Z-[a-f0-9]{12}\Z")
ENTRY = [
    "scripts/r60_base_constructed_hf_cpu_worker.py",
    "scripts/r60_base_constructed_hf_cpu_worker.sh",
    "scripts/r60_base_constructed_hf_cpu_stage.py",
    "requirements/r60-common2-wrapped-cpu.in",
    "experiments/r58_quality/r60_base_constructed_sft_cpu_smoke.py",
    "experiments/r58_quality/r60_base_constructed_system_contract_v1.py",
    "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py",
]
EXTRA = ["src/storyforge_dataset/token_preflight.py"]


def dependencies() -> list[str]:
    return shared.local_dependencies(entries=ENTRY, extras=EXTRA)


def verify(stage: Path, key: str) -> dict:
    if (not RUN_RE.fullmatch(key) or stage.name != key or stage.is_symlink()
            or not stage.is_dir()):
        raise ValueError("STAGE_IDENTITY_HOLD")
    manifest = InputManager.validate_json(InputManager.open_verified(
        stage / "SHA256_MANIFEST_PRIVATE.json", max_bytes=32768).read_bytes())
    files = manifest.get("files")
    if (manifest.get("schema") != SCHEMA or
            manifest.get("run_key") != key or
            manifest.get("status") != "SYNTHETIC_STAGE_ONLY__NO_JOB" or
            manifest.get("synthetic_cases") != 3 or
            manifest.get("train_admitted") != 0 or type(files) is not dict):
        raise ValueError("STAGE_CONTRACT_HOLD")
    found = {p.relative_to(stage).as_posix()
             for p in stage.rglob("*") if p.is_file() or p.is_symlink()}
    if found != set(files) | {"SHA256_MANIFEST_PRIVATE.json"} or (
            not set(ENTRY).issubset(files)):
        raise ValueError("STAGE_FILESET_HOLD")
    for name, digest in files.items():
        if (type(name) is not str or name.startswith("/")
                or ".." in Path(name).parts
                or type(digest) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            raise ValueError("STAGE_DIGEST_HOLD")
        InputManager.open_verified(
            stage / name, max_bytes=8_000_000, expected_sha256=digest)
    return {
        "schema": "storyforge_r60_base_constructed_hf_cpu_stage_safe_v1",
        "status": "BASE_CONSTRUCTED_HF_CPU_STAGE_VERIFIED__NO_JOB",
        "synthetic_cases": 3, "files_verified": len(files),
        "train_admitted": 0, "gpu_started": False,
        "hf_jobs_submitted": 0, "private_values_emitted": False,
    }


def prepare(stage: Path, key: str) -> dict:
    if (not RUN_RE.fullmatch(key) or stage.name != key or
            stage.exists() or stage.is_symlink()):
        raise ValueError("CREATE_ONLY_HOLD")
    paths = dependencies()
    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        hashes = {}
        for name in paths:
            src = ROOT / name
            if src.is_symlink() or not src.is_file():
                raise ValueError("SOURCE_PATH_HOLD")
            data = InputManager.open_verified(src, max_bytes=8_000_000).read_bytes()
            dst = stage / name
            dst.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            dst.write_bytes(data)
            dst.chmod(0o600)
            hashes[name] = hashlib.sha256(data).hexdigest()
        manifest = {
            "schema": SCHEMA, "run_key": key, "synthetic_cases": 3,
            "status": "SYNTHETIC_STAGE_ONLY__NO_JOB",
            "files": hashes, "private_story_data_in_stage": False,
            "model_weights_in_stage": False, "train_admitted": 0,
        }
        target = stage / "SHA256_MANIFEST_PRIVATE.json"
        target.write_text(json.dumps(manifest, sort_keys=True) + "\n")
        target.chmod(0o600)
        return verify(stage, key)
    except BaseException:
        shutil.rmtree(stage)
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare", "verify"))
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--run-key", required=True)
    args = p.parse_args()
    try:
        result = (prepare(args.stage, args.run_key) if args.action == "prepare"
                  else verify(args.stage, args.run_key))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - SAFE-only stage receipt
        print(json.dumps({
            "schema": "storyforge_r60_base_constructed_hf_cpu_stage_safe_v1",
            "status": "BASE_CONSTRUCTED_HF_CPU_STAGE_HOLD",
            "hf_jobs_submitted": 0, "gpu_started": False,
            "train_admitted": 0, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
