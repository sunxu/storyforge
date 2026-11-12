"""Owner Mac: create a private, immutable R60 Common2 HF CPU-only stage.

Pure stdlib. Does NOT upload, install, run HF Jobs or disclose source text.
Recursively stage *only* Python modules imported from experiments/r58_quality,
plus the exact canonical label-mask audit. Never stage R50 assets.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = Path.home() / ".local/share/storyforge/r60/private"
DATA = "R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl"
MANIFEST = "R60_COMMON2_SFT_EXPERIMENTAL_MANIFEST_PRIVATE.json"
RUN_KEY = re.compile(r"r60-common2-cpu2-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}\Z")
START = [
    "experiments/r58_quality/r60_common2_sft_cpu_template_audit.py",
    "scripts/hf_label_mask_audit.py",
]
WORKER = "scripts/r60_common2_hf_cpu_worker.sh"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def code_paths() -> list[Path]:
    """Resolve only local named-module imports; fail if any local file disappears."""
    found: set[Path] = set()
    pending = [REPO / p for p in START]
    module_dir = REPO / "experiments/r58_quality"
    while pending:
        p = pending.pop()
        if p in found:
            continue
        if not p.is_file() or p.is_symlink():
            raise ValueError("CODE_SOURCE_UNSAFE")
        found.add(p)
        tree = ast.parse(p.read_bytes(), filename="<public-script>")
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                candidate = module_dir / f"{name}.py"
                if candidate.is_file():
                    pending.append(candidate)
    return sorted(found)


def validate_inputs(directory: Path) -> tuple[bytes, bytes]:
    if (directory.is_symlink() or
            not directory.is_dir() or
            stat.S_IMODE(directory.stat().st_mode) & 0o077):
        raise ValueError("PRIVATE_DIRECTORY_PERMISSIONS_HOLD")
    files = [directory / DATA, directory / MANIFEST]
    if any(not p.is_file() or p.is_symlink() or
           stat.S_IMODE(p.stat().st_mode) & 0o077 for p in files):
        raise ValueError("PRIVATE_FILES_PERMISSIONS_HOLD")
    raw, manifest_raw = (p.read_bytes() for p in files)
    if len(raw) > 8_000_000 or len(manifest_raw) > 65536:
        raise ValueError("PRIVATE_SIZE_HOLD")
    m = json.loads(manifest_raw)
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    if (m.get("schema") != "storyforge_r60_common2_sft_experimental_manifest_private_v1"
            or m.get("status") != "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED"
            or m.get("window") != 11 or m.get("examples") != 2
            or m.get("r50_complete_exclusion_verified") is not False
            or m.get("train_admitted") != 0 or m.get("data_sha256") != digest(raw)
            or len(rows) != 2):
        raise ValueError("EXPERIMENT_BINDING_HOLD")
    for row in rows:
        msgs = row.get("messages")
        if (row.get("schema") != "storyforge_r60_source_bound_experimental_sft_v1"
                or row.get("input_kind") != "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT"
                or row.get("supervision_scope") != "FINAL_ASSISTANT_ONLY"
                or row.get("system_prompt", 0) is not None
                or row.get("world_card", 0) is not None
                or row.get("train_admitted") is not False
                or not isinstance(msgs, list) or len(msgs) != 12
                or [v.get("role") for v in msgs] !=
                   ["user" if i % 2 == 0 else "assistant" for i in range(11)]
                   + ["assistant"]
                or any(set(v) != {"role", "content"} or
                       not isinstance(v["content"], str) or not v["content"]
                       for v in msgs)):
            raise ValueError("EXPERIMENT_ROW_HOLD")
    return raw, manifest_raw


def stage(input_dir: Path, output_dir: Path, run_key: str) -> dict:
    if not RUN_KEY.fullmatch(run_key):
        raise ValueError("RUN_KEY_HOLD")
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("OUTPUT_EXISTS_HOLD")
    raw, manifest_raw = validate_inputs(input_dir)
    sources = code_paths() + [REPO / WORKER]
    paths: dict[str, bytes] = {
        "private_stage/" + DATA: raw,
        "private_stage/" + MANIFEST: manifest_raw,
    }
    for src in sources:
        if not src.is_file() or src.is_symlink():
            raise ValueError("PUBLIC_CODE_SOURCE_HOLD")
        rel = "code/" + str(src.relative_to(REPO))
        paths[rel] = src.read_bytes()
    # Git blob of official mask audit, frozen by the R53 successful workflow.
    mask = paths["code/scripts/hf_label_mask_audit.py"]
    blob = hashlib.sha1(b"blob " + str(len(mask)).encode() + b"\x00" + mask).hexdigest()
    if blob != "15296f1d8438f40d727c84913ac658cf6de01cb4":
        raise ValueError("PINNED_LABEL_AUDITOR_HOLD")
    # Stage uses create-only writes, no symlink traversal, no overwrites.
    output_dir.mkdir(mode=0o700, parents=False)
    for name, data in sorted(paths.items()):
        dst = output_dir / name
        dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with os.fdopen(os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
            f.write(data)
    lines = [f"{digest(data)}  {name}\n" for name, data in sorted(paths.items())]
    with os.fdopen(os.open(output_dir / "SHA256SUMS.txt",
                           os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
        f.write("".join(lines).encode())
    return {
        "status": "R60_COMMON2_HF_CPU2_STAGE_READY__NO_JOB",
        "schema": "storyforge_r60_common2_hf_cpu_stage_safe_v1",
        "private_examples": 2, "files_staged": len(paths) + 1,
        "run_key": run_key, "model_inference_calls": 0,
        "gpu_started": False, "hf_jobs_submitted": 0,
        "private_values_emitted": False, "train_admitted": 0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--run-key", required=True)
    args = p.parse_args()
    try:
        result = stage(args.input_dir, args.output_dir, args.run_key)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - private contents must not leak in traceback
        print(json.dumps({
            "schema": "storyforge_r60_common2_hf_cpu_stage_safe_v1",
            "status": "R60_COMMON2_HF_CPU2_STAGE_HOLD", "train_admitted": 0,
            "hf_jobs_submitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
