"""R60 Qwen A25: CPU-only gate for a single, instrumented position-7 resume.

No vLLM/CUDA. Validates six frozen checkpoints against the original reviewer,
source row SHA/model/revision and no foreign files, without writing anything.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

SCHEMA = "storyforge_r60_qwen_resume7_cpu_gate_safe_v1"
SOURCE_SHA = "492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069"
MODEL = "Qwen/Qwen3-32B"
REV = "9216db5781bf21249d130ec9da846c4624c16137"
SIX = {f"review_{i:04d}.private.json" for i in range(1, 7)}


class GateHold(ValueError):
    pass


def check(runner: Path, source: Path, receipts: Path) -> dict:
    if (runner.is_symlink() or not runner.is_file()
            or source.is_symlink() or not source.is_file()
            or receipts.is_symlink() or not receipts.is_dir()
            or runner.parent != source.parent):
        raise GateHold("PATH_SCOPE_HOLD")
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise GateHold("SOURCE_SHA_HOLD")
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, TypeError) as exc:
        raise GateHold("SOURCE_PARSE_HOLD") from exc
    if len(rows) != 25:
        raise GateHold("SOURCE_COUNT_HOLD")
    objects = list(receipts.iterdir())
    if (any(x.is_symlink() or not x.is_file() for x in objects)
            or {x.name for x in objects} != SIX):
        raise GateHold("PREFIX_INVENTORY_HOLD")
    # Frozen runner is imported for validation only; its inference function
    # is never called and all GPU imports there are lazy.
    if runner.stat().st_size > 200_000:
        raise GateHold("RUNNER_SIZE_HOLD")
    spec = importlib.util.spec_from_file_location("r60_qwen_resume7_frozen", runner)
    if spec is None or spec.loader is None:
        raise GateHold("RUNNER_IMPORT_HOLD")
    sys.path.insert(0, str(runner.parent))
    try:
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
    finally:
        sys.path.pop(0)
    if not all(callable(getattr(worker, key, None))
               for key in ("validate_input", "read_checkpoint", "checkpoint_name")):
        raise GateHold("RUNNER_API_HOLD")
    for row in rows:
        worker.validate_input(row)
    if len({row["blind_id"] for row in rows}) != 25:
        raise GateHold("SOURCE_IDENTITY_HOLD")
    for position in range(1, 7):
        file = receipts / worker.checkpoint_name(position)
        try:
            record = worker.read_checkpoint(file, position, rows[position - 1], MODEL, REV)
        except Exception as exc:
            raise GateHold("PREFIX_VALIDATION_HOLD") from exc
        if record is None:
            raise GateHold("PREFIX_MISSING_HOLD")
    return {"schema": SCHEMA,
            "status": "QWEN_RESUME7_CPU_GATE_PASS",
            "private_values_emitted": False,
            "gpu_started": False,
            "checkpoint_prefix_verified": 6,
            "next_position": 7,
            "instrumented_scope_only_position_7": True,
            "output_modified": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--receipts", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = check(args.runner, args.input, args.receipts)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - redact any frozen private exception text
        print(json.dumps({"schema": SCHEMA,
                          "status": "QWEN_RESUME7_CPU_GATE_HOLD",
                          "private_values_emitted": False,
                          "gpu_started": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
