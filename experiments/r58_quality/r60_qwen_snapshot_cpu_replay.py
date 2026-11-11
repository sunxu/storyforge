"""Qwen R60: CPU-only signed generation snapshot replay, no training admission.

Replay original slot01 through frozen checkpoint_record only. A secondary
model-produced quote-repair generation is authenticated but not automatically
substituted into the strict result. Never print model text or identifiers.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

from r60_generation_snapshot import filename, read_snapshot, verify_directory

SCHEMA = "storyforge_r60_qwen_snapshot_cpu_replay_safe_v1"
SOURCE_SHA = "492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069"
MODEL = "Qwen/Qwen3-32B"
REV = "9216db5781bf21249d130ec9da846c4624c16137"


class ReplayHold(ValueError):
    pass


def inspect(runner: Path, source: Path, snapshots: Path, *, position: int = 7) -> dict:
    if (position != 7 or runner.parent != source.parent
            or runner.is_symlink() or source.is_symlink()
            or not runner.is_file() or not source.is_file()
            or runner.stat().st_size > 200_000):
        raise ReplayHold("FROZEN_SCOPE_HOLD")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ReplayHold("SOURCE_SHA_HOLD")
    spec = importlib.util.spec_from_file_location("qwen_snapshot_frozen", runner)
    if spec is None or spec.loader is None:
        raise ReplayHold("RUNNER_IMPORT_HOLD")
    sys.path.insert(0, str(runner.parent))
    try:
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
    finally:
        sys.path.pop(0)
    for key in ("validate_input", "input_digest", "checkpoint_record"):
        if not callable(getattr(worker, key, None)):
            raise ReplayHold("REVIEWER_API_HOLD")
    if not isinstance(getattr(worker, "POLICY", None), str):
        raise ReplayHold("REVIEWER_POLICY_HOLD")
    try:
        rows = [json.loads(x) for x in source.read_bytes().splitlines() if x.strip()]
    except (ValueError, TypeError):
        raise ReplayHold("SOURCE_PARSE_HOLD") from None
    if len(rows) != 25:
        raise ReplayHold("SOURCE_COUNT_HOLD")
    for row in rows:
        worker.validate_input(row)
    row = rows[position - 1]
    verify_directory(snapshots, fresh=False)
    allowed = {filename(position, 1), filename(position, 2)}
    objects = list(snapshots.iterdir())
    if (not objects or any(x.is_symlink() or not x.is_file() or x.name not in allowed
                           for x in objects)):
        raise ReplayHold("SNAPSHOT_INVENTORY_HOLD")
    runner_sha = hashlib.sha256(runner.read_bytes()).hexdigest()
    slots = {}
    for slot in (1, 2):
        path = snapshots / filename(position, slot)
        if path.exists() or path.is_symlink():
            slots[slot] = read_snapshot(
                path, position=position, generation_index=slot,
                row_digest=worker.input_digest(row),
                runner_sha256=runner_sha, model=MODEL, revision=REV,
                policy=worker.POLICY)
    if 1 not in slots:
        raise ReplayHold("SNAPSHOT_PRIMARY_MISSING_HOLD")

    result = {"schema": SCHEMA,
              "status": "QWEN_SNAPSHOT_CPU_REPLAY_COMPLETE_NO_ADMISSION",
              "scope": "POSITION_7", "position": position,
              "authenticated_snapshots": len(slots),
              "secondary_repair_replayed": False,
              "gpu_started": False, "model_inference_calls": 0,
              "source_receipts_modified": False,
              "private_values_emitted": False,
              "quality_v1_admitted": 0, "training_authorized": False,
              "technical_status": "REPLAY_FAILED",
              "reason_code": "STRICT_REVIEW_EXCEPTION_REDACTED",
              "quality_decision": None}
    primary = slots[1]
    if primary["finish_reason"] != "stop":
        result["reason_code"] = "MODEL_GENERATION_INCOMPLETE_HOLD"
        return result
    try:
        response = json.loads(primary["text"])
    except (ValueError, TypeError):
        result["reason_code"] = "MODEL_JSON_HOLD"
        return result
    try:
        checkpoint = worker.checkpoint_record(position, row, response, MODEL, REV)
        decision = checkpoint["response"]["decision"]
        if decision not in ("PASS", "HOLD", "REJECT"):
            raise ReplayHold("QUALITY_DECISION_HOLD")
    except Exception:
        # Never leak original reviewer errors or private text to stdout/report.
        return result
    result["technical_status"] = "REPLAY_VALIDATED"
    result["reason_code"] = None
    result["quality_decision"] = decision
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("runner", "input", "snapshots", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        if (args.output.exists() or args.output.is_symlink()
                or not args.output.parent.is_dir()
                or args.output.parent.is_symlink()):
            raise ReplayHold("OUTPUT_PATH_HOLD")
        report = inspect(args.runner, args.input, args.snapshots)
        data = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")) + "\n").encode()
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({"schema": SCHEMA, "status": "QWEN_SNAPSHOT_CPU_REPLAY_HOLD",
                          "gpu_started": False, "private_values_emitted": False},
                         sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
