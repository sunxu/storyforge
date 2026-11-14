"""Create-only SHA-bound Base CPU336 HF technical stage; no remote submissions.

Reuses Common2 dependency closure and shared hf_runtime InputManager.
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
from storyforge_dataset.hf_runtime import InputManager

import r60_common2_wrapped_hf_stage as shared_stage

RUN_RE = re.compile(r"r60-base-cpu336-\d{8}T\d{6}Z-[a-f0-9]{12}\Z")
SCHEMA = "storyforge_r60_base_cpu336_stage_private_v1"
DATA = "R60_BASE_CPU336_TECHNICAL_NOT_ADMITTED_PRIVATE.jsonl"
MANIFEST = "R60_BASE_CPU336_TECHNICAL_MANIFEST_PRIVATE.json"
ENTRY = [
    "scripts/r60_base_cpu336_hf_worker.sh",
    "scripts/r60_base_cpu336_hf_worker.py",
    "scripts/r60_base_cpu336_hf_stage.py",
    "requirements/r60-common2-wrapped-cpu.in",
    "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py",
]
EXTRA = ["src/storyforge_dataset/token_preflight.py"]


def dependencies() -> list[str]:
    return shared_stage.local_dependencies(entries=ENTRY, extras=EXTRA)


def verify(stage: Path, key: str) -> dict:
    if not RUN_RE.fullmatch(key) or stage.is_symlink():
        raise ValueError("STAGE_NAME_HOLD")
    doc = InputManager.validate_json(InputManager.open_verified(
        stage / "SHA256_MANIFEST_PRIVATE.json", max_bytes=32768).read_bytes())
    if (doc.get("schema") != SCHEMA or doc.get("run_key") != key
            or doc.get("status") != "TECHNICAL_STAGE_ONLY__NO_JOB"
            or doc.get("train_admitted") != 0 or doc.get("examples") != 336):
        raise ValueError("STAGE_MANIFEST_HOLD")
    files = doc.get("files")
    if not isinstance(files, dict):
        raise ValueError("STAGE_FILES_HOLD")
    actual = {p.relative_to(stage).as_posix()
              for p in stage.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != set(files) | {"SHA256_MANIFEST_PRIVATE.json"}:
        raise ValueError("STAGE_FILESET_HOLD")
    for name, digest in files.items():
        if (name.startswith("/") or ".." in Path(name).parts
                or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            raise ValueError("STAGE_FILE_HASH_HOLD")
        InputManager.open_verified(
            stage / name, max_bytes=8_000_000, expected_sha256=digest)
    if not set(ENTRY).issubset(files) or not {
            "private/" + DATA, "private/" + MANIFEST}.issubset(files):
        raise ValueError("STAGE_CONTRACT_HOLD")
    return {
        "schema": "storyforge_r60_base_cpu336_stage_safe_v1",
        "status": "BASE_CPU336_STAGE_VERIFIED__NO_JOB",
        "files_verified": len(files), "cases": 336,
        "train_admitted": 0, "hf_jobs_submitted": 0,
        "gpu_started": False, "private_values_emitted": False,
    }


def prepare(private_dir: Path, stage: Path, key: str) -> dict:
    if (not RUN_RE.fullmatch(key) or stage.name != key
            or stage.exists() or stage.is_symlink()
            or private_dir.is_symlink()):
        raise ValueError("STAGE_PATH_HOLD")
    technical = InputManager.validate_json(InputManager.open_verified(
        private_dir / MANIFEST, max_bytes=32768).read_bytes())
    if (technical.get("schema") !=
            "storyforge_r60_base_cpu336_hf_packet_private_v1"
            or technical.get("status") != "TECHNICAL_INPUT_ONLY__ALL_HELD"
            or technical.get("examples") != 336
            or technical.get("train_admitted") != 0
            or technical.get("training_dataset_created") is not False):
        raise ValueError("TECHNICAL_SOURCE_HOLD")
    data = InputManager.open_verified(
        private_dir / DATA, max_bytes=4_000_000,
        expected_sha256=technical["data_sha256"]).read_bytes()
    if len(data.splitlines()) != 336:
        raise ValueError("SOURCE_ROW_COUNT_HOLD")
    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    files = {}
    try:
        for name in dependencies():
            raw = InputManager.open_verified(
                ROOT / name, max_bytes=8_000_000).read_bytes()
            dst = stage / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(raw)
            dst.chmod(0o600)
            files[name] = hashlib.sha256(raw).hexdigest()
        for name, raw in ((DATA, data), (MANIFEST, json.dumps(
                technical, sort_keys=True, separators=(",", ":")).encode() + b"\n")):
            dst = stage / "private" / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(raw)
            dst.chmod(0o600)
            files["private/" + name] = hashlib.sha256(raw).hexdigest()
        doc = {
            "schema": SCHEMA, "status": "TECHNICAL_STAGE_ONLY__NO_JOB",
            "run_key": key, "examples": 336, "files": files,
            "source_sha256": technical["data_sha256"],
            "train_admitted": 0, "model_weights_in_stage": False,
        }
        target = stage / "SHA256_MANIFEST_PRIVATE.json"
        target.write_text(json.dumps(doc, sort_keys=True) + "\n")
        target.chmod(0o600)
        return verify(stage, key)
    except BaseException:
        shutil.rmtree(stage)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("prepare", "verify"))
    ap.add_argument("--private-dir", type=Path)
    ap.add_argument("--stage", required=True, type=Path)
    ap.add_argument("--run-key", required=True)
    a = ap.parse_args()
    try:
        if a.action == "prepare" and a.private_dir is not None:
            safe = prepare(a.private_dir, a.stage, a.run_key)
        elif a.action == "verify":
            safe = verify(a.stage, a.run_key)
        else:
            raise ValueError("STAGE_ARGS_HOLD")
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no private values
        print(json.dumps({
            "schema": "storyforge_r60_base_cpu336_stage_safe_v1",
            "status": "BASE_CPU336_STAGE_HOLD",
            "train_admitted": 0, "hf_jobs_submitted": 0,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
