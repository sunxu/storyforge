"""Create-only SHA-pinned HF CPU stage for actual 293/43 exploratory data.

This stage is technical evidence, not a GPU release or train admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"),
                str(ROOT / "experiments/r58_quality")]

import r60_base336_exploratory_release_verify as release
import r60_common2_wrapped_hf_stage as shared

from storyforge_dataset.hf_runtime import InputManager

SCHEMA = "storyforge_r60_base336_final_cpu_stage_private_v1"
RUN_RE = re.compile(r"r60-base336-finalcpu-\d{8}T\d{6}Z-[a-f0-9]{12}\Z")
ENTRY = [
    "scripts/r60_base336_final_cpu_stage.py",
    "scripts/r60_base336_final_cpu_worker.py",
    "scripts/r60_base336_final_cpu_worker.sh",
    "requirements/r60-common2-wrapped-cpu.in",
    "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py",
]
EXTRA = ["src/storyforge_dataset/token_preflight.py"]
FILES = ("train.jsonl", "validation.jsonl", release.MANIFEST)


def dependencies() -> list[str]:
    return shared.local_dependencies(entries=ENTRY, extras=EXTRA)


def verify(stage: Path, key: str) -> dict:
    if not RUN_RE.fullmatch(key) or not stage.is_dir() or stage.is_symlink():
        raise ValueError("STAGE_ID_HOLD")
    doc = InputManager.validate_json(InputManager.open_verified(
        stage / "SHA256_MANIFEST_PRIVATE.json", max_bytes=32768).read_bytes())
    files = doc.get("files")
    if (doc.get("schema") != SCHEMA or doc.get("run_key") != key
            or doc.get("status") != "FINAL_COLLATOR_ONLY__NO_JOB"
            or doc.get("train_admitted") != 0 or type(files) is not dict
            or not set(ENTRY).issubset(files)
            or not {f"private/{x}" for x in FILES}.issubset(files)):
        raise ValueError("STAGE_CONTRACT_HOLD")
    actual = {p.relative_to(stage).as_posix() for p in stage.rglob("*")
              if p.is_file() or p.is_symlink()}
    if actual != set(files) | {"SHA256_MANIFEST_PRIVATE.json"}:
        raise ValueError("STAGE_FILESET_HOLD")
    for name, digest in files.items():
        if (type(name) is not str or name.startswith("/")
                or ".." in Path(name).parts or type(digest) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ValueError("STAGE_DIGEST_HOLD")
        InputManager.open_verified(stage / name, max_bytes=8_000_000,
                                   expected_sha256=digest)
    return {
        "schema": "storyforge_r60_base336_final_cpu_stage_safe_v1",
        "status": "BASE336_FINAL_CPU_STAGE_VERIFIED__NO_JOB",
        "files_verified": len(files), "train_rows": 293,
        "validation_rows": 43, "train_admitted": 0,
        "gpu_started": False, "hf_jobs_submitted": 0,
        "private_values_emitted": False,
    }


def prepare(source: Path, stage: Path, key: str) -> dict:
    if (not RUN_RE.fullmatch(key) or stage.name != key
            or stage.exists() or stage.is_symlink()):
        raise ValueError("CREATE_ONLY_HOLD")
    release.verify(source)
    payloads = {}
    for name in FILES:
        payloads[f"private/{name}"] = InputManager.open_verified(
            source / name, max_bytes=4_000_000).read_bytes()
    for name in dependencies():
        payloads[name] = InputManager.open_verified(
            ROOT / name, max_bytes=8_000_000).read_bytes()
    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    # Failure leaves partial stage intact; never overwrite or delete evidence.
    hashes = {}
    for name, raw in payloads.items():
        dest = stage / name
        dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with dest.open("xb") as output:
            output.write(raw)
        dest.chmod(0o600)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    manifest = {
        "schema": SCHEMA, "run_key": key, "files": hashes,
        "status": "FINAL_COLLATOR_ONLY__NO_JOB",
        "source_data_sha256": {
            key: hashes[f"private/{key}.jsonl"] for key in ("train", "validation")
        },
        "train_admitted": 0, "model_weights_in_stage": False,
    }
    target = stage / "SHA256_MANIFEST_PRIVATE.json"
    with target.open("x") as output:
        json.dump(manifest, output, sort_keys=True)
        output.write("\n")
    target.chmod(0o600)
    return verify(stage, key)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("prepare", "verify"))
    ap.add_argument("--source", type=Path)
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--run-key", required=True)
    a = ap.parse_args()
    try:
        value = (prepare(a.source, a.stage, a.run_key) if a.action == "prepare"
                 and a.source is not None else verify(a.stage, a.run_key)
                 if a.action == "verify" else None)
        if value is None:
            raise ValueError("ARGUMENT_HOLD")
        print(json.dumps(value, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no private paths or source
        print(json.dumps({
            "schema": "storyforge_r60_base336_final_cpu_stage_safe_v1",
            "status": "BASE336_FINAL_CPU_STAGE_HOLD",
            "train_admitted": 0, "gpu_started": False,
            "hf_jobs_submitted": 0, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
