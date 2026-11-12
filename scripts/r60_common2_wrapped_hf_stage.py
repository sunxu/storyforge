"""Create/verify a private, immutable R60 Common2 wrapped-System HF CPU stage.

Uses the shared hf_runtime InputManager. Copies only Python import dependencies
needed by the existing business auditor; never duplicates tokenizer algorithms.
Mac-side actions are create-only and do not submit, tokenize or access HF.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from storyforge_dataset.hf_runtime import InputManager

RUN_RE = re.compile(r"r60-common2-wrapcpu-\d{8}T\d{6}Z-[a-f0-9]{12}\Z")
SCHEMA = "storyforge_r60_common2_wrapped_hf_stage_private_v1"
DATA = "R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl"
MANIFEST = "R60_COMMON2_SFT_EXPERIMENTAL_MANIFEST_PRIVATE.json"
ENTRY = [
    "scripts/r60_common2_wrapped_hf_worker.sh",
    "scripts/r60_common2_wrapped_hf_worker.py",
    "scripts/r60_common2_wrapped_system_cpu_audit.py",
    "requirements/r60-common2-wrapped-cpu.in",
]
EXTRA = [
    "src/storyforge_dataset/token_preflight.py",
]
ROOTS = ("scripts", "experiments/r58_quality")
MAX_CODE_FILES = 70


def local_dependencies() -> list[str]:
    names = {}
    for root in ROOTS:
        for path in (ROOT / root).glob("*.py"):
            names[path.stem] = path.relative_to(ROOT).as_posix()
    seen = set()
    pending = list(ENTRY) + EXTRA
    while pending:
        relative = pending.pop()
        if relative in seen:
            continue
        p = ROOT / relative
        if not p.is_file() or p.is_symlink():
            raise ValueError("LOCAL_CODE_MISSING_HOLD")
        seen.add(relative)
        if len(seen) > MAX_CODE_FILES:
            raise ValueError("DEPENDENCY_BOUND_HOLD")
        if p.suffix != ".py":
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module.split(".")[0]] if node.module else []
            else:
                continue
            pending.extend(names[m] for m in modules if m in names)
    # The imported shared HF Runtime is bundled whole, never forked or edited.
    seen.update(p.relative_to(ROOT).as_posix() for p in
                (ROOT / "src/storyforge_dataset/hf_runtime").glob("*.py"))
    seen.add("src/storyforge_dataset/__init__.py")
    return sorted(seen)


def input_bytes(path: Path, maximum: int) -> bytes:
    return InputManager.open_verified(path, max_bytes=maximum).read_bytes()


def verify(stage: Path, run_key: str) -> dict:
    if not RUN_RE.fullmatch(run_key):
        raise ValueError("RUN_KEY_HOLD")
    if stage.is_symlink() or not stage.is_dir():
        raise ValueError("STAGE_DIR_HOLD")
    frozen = InputManager.validate_json(input_bytes(stage / "SHA256_MANIFEST_PRIVATE.json", 32768))
    if (type(frozen) is not dict or frozen.get("schema") != SCHEMA
            or frozen.get("run_key") != run_key
            or frozen.get("status") != "STAGED_NOT_SUBMITTED"
            or frozen.get("train_admitted") != 0
            or frozen.get("private_data_contains_r50") is not False
            or type(frozen.get("files")) is not dict):
        raise ValueError("STAGE_MANIFEST_HOLD")
    expected = set(frozen["files"])
    actual = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    if actual != expected | {"SHA256_MANIFEST_PRIVATE.json"}:
        raise ValueError("STAGE_FILES_HOLD")
    if any(not re.fullmatch(r"[a-f0-9]{64}", v) for v in frozen["files"].values()):
        raise ValueError("STAGE_HASH_SCHEMA_HOLD")
    for name, digest in frozen["files"].items():
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("STAGE_PATH_HOLD")
        InputManager.open_verified(stage / name, max_bytes=8_000_000, expected_sha256=digest)
    # Detect accidental alteration or omission of the expected business adapter.
    if not set(ENTRY).issubset(expected) or not {
            "private/" + DATA, "private/" + MANIFEST,
            "src/storyforge_dataset/token_preflight.py",
        }.issubset(expected):
        raise ValueError("STAGE_CONTRACT_HOLD")
    return {"schema": "storyforge_r60_common2_wrapped_hf_stage_safe_v1",
            "status": "WRAPPED_CPU_STAGE_VERIFIED__NO_JOB",
            "files_verified": len(expected),
            "private_input_files_verified": 2,
            "run_key": run_key,
            "model_weights_in_stage": False, "gpu_started": False,
            "hf_jobs_submitted": 0, "train_admitted": 0,
            "private_values_emitted": False}


def prepare(input_dir: Path, stage: Path, run_key: str) -> dict:
    if not RUN_RE.fullmatch(run_key):
        raise ValueError("RUN_KEY_HOLD")
    if input_dir.is_symlink() or not input_dir.is_dir():
        raise ValueError("INPUT_DIR_HOLD")
    if stage.exists() or stage.is_symlink():
        raise ValueError("STAGE_ALREADY_EXISTS_HOLD")
    # Must verify frozen source contract and exact generic System before any copy.
    sys.path.insert(0, str(ROOT / "scripts"))
    import r60_common2_generic_system_wrapper_preview_cpu as preview
    readout = preview.preview(input_dir)
    if readout["status"] != "COMMON2_GENERIC_SYSTEM_IN_MEMORY_WRAPPER_PREVIEW_PASS__TRAIN_HOLD":
        raise ValueError("SOURCE_WRAPPER_HOLD")
    paths = local_dependencies()
    stage.mkdir(mode=0o700, parents=False, exist_ok=False)
    files = {}
    try:
        for name in paths:
            dst = stage / name
            dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            raw = input_bytes(ROOT / name, 8_000_000)
            dst.write_bytes(raw)
            dst.chmod(0o600)
            files[name] = hashlib.sha256(raw).hexdigest()
        for name in (DATA, MANIFEST):
            relative = "private/" + name
            dst = stage / relative
            dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            raw = input_bytes(input_dir / name, 8_000_000)
            dst.write_bytes(raw)
            dst.chmod(0o600)
            files[relative] = hashlib.sha256(raw).hexdigest()
        stage_doc = {
            "schema": SCHEMA, "status": "STAGED_NOT_SUBMITTED",
            "run_key": run_key, "files": files,
            "system_origin": "R27_R52_FROZEN_SYNTHETIC_NOT_HISTORICAL_SENT",
            "system_sha256": preview.SYSTEM_SHA256,
            "model": "Qwen/Qwen3.8-27B",
            "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
            "private_data_contains_r50": False, "train_admitted": 0,
        }
        manifest_path = stage / "SHA256_MANIFEST_PRIVATE.json"
        manifest_path.write_text(json.dumps(stage_doc, sort_keys=True) + "\n")
        manifest_path.chmod(0o600)
        return verify(stage, run_key)
    except BaseException:
        shutil.rmtree(stage)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["prepare", "verify"])
    ap.add_argument("--input-dir", type=Path)
    ap.add_argument("--stage", required=True, type=Path)
    ap.add_argument("--run-key", required=True)
    args = ap.parse_args()
    try:
        result = (prepare(args.input_dir, args.stage, args.run_key)
                  if args.action == "prepare" and args.input_dir is not None
                  else verify(args.stage, args.run_key) if args.action == "verify"
                  else (_ for _ in ()).throw(ValueError("ARGUMENTS_HOLD")))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - fail closed; SAFE only
        print(json.dumps({"schema": "storyforge_r60_common2_wrapped_hf_stage_safe_v1",
                          "status": "WRAPPED_CPU_STAGE_HOLD",
                          "reason_code": "INPUT_STAGE_OR_RUNTIME_HOLD",
                          "train_admitted": 0, "hf_jobs_submitted": 0,
                          "gpu_started": False, "private_values_emitted": False},
                         sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
