"""R60 GLM B25 CPU-only replay of signed private generation snapshots.

No model loading, GPU, filesystem mutation of sources/receipts, or checkpoint
writing. Uses the exact frozen runner for strict validation and optional
original model-produced repair selection (slot 2). Deterministic literal
reconciliation is a separate experimental result, never an admission.
Output SAFE counts/statuses only; no private body, quote, answer, blind ID,
input digest, runner digest, traceback or untrusted exception message.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from r60_generation_snapshot import filename, read_snapshot, verify_directory
from r60_glm4_b25_retry_contract import FAILED_POSITIONS
from r60_glm4_exact_quote_repair import make_reconciler

SCHEMA = "storyforge_r60_glm4_cpu_snapshot_replay_safe_v1"
B25_SHA = "01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9"
MODEL = "zai-org/GLM-4-32B-0414"
REV = "8dea913c41b543527c2860fb6f3c15c202f24aeb"
NAME = re.compile(r"generation_(\d{4})_(\d{2})\.private\.json\Z")
FAILURE_KINDS = frozenset({"MODEL_NONEXACT_QUOTE_HOLD", "MODEL_JSON_HOLD",
                           "MODEL_GENERATION_INCOMPLETE_HOLD", "OTHER_REVIEW_HOLD"})


class ReplayHold(ValueError):
    pass


def frozen(path: Path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 200000:
        raise ReplayHold("RUNNER_FILE_HOLD")
    spec = importlib.util.spec_from_file_location("r60_glm_replay_frozen", path)
    if spec is None or spec.loader is None:
        raise ReplayHold("RUNNER_IMPORT_HOLD")
    sys.path.insert(0, str(path.parent))
    try:
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
    finally:
        sys.path.pop(0)
    for name in ("validate_input", "checkpoint_record", "validate_response",
                 "input_digest", "apply_repairs", "quote_candidates"):
        if not callable(getattr(worker, name, None)):
            raise ReplayHold("RUNNER_API_HOLD")
    return worker


def load_original_rows(path: Path, worker: object) -> list[dict]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ReplayHold("INPUT_FILE_HOLD")
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != B25_SHA:
        raise ReplayHold("INPUT_SHA_HOLD")
    try:
        rows = [json.loads(line) for line in source.splitlines() if line.strip()]
    except (ValueError, TypeError) as exc:
        raise ReplayHold("INPUT_PARSE_HOLD") from exc
    if len(rows) != 25:
        raise ReplayHold("INPUT_COUNT_HOLD")
    for row in rows:
        worker.validate_input(row)
    return [rows[pos - 1] for pos in FAILED_POSITIONS]


def validate_inventory(directory: Path) -> list[int]:
    verify_directory(directory, fresh=False)
    slots = {}
    for item in directory.iterdir():
        if item.is_symlink() or not item.is_file():
            raise ReplayHold("SNAPSHOT_FOREIGN_OBJECT_HOLD")
        match = NAME.fullmatch(item.name)
        if not match:
            raise ReplayHold("SNAPSHOT_NAME_HOLD")
        position, slot = (int(x) for x in match.groups())
        if not 1 <= position <= 12 or slot not in (1, 2):
            raise ReplayHold("SNAPSHOT_POSITION_HOLD")
        slots.setdefault(position, set()).add(slot)
    if not slots or set(slots) != set(range(1, max(slots) + 1)):
        raise ReplayHold("SNAPSHOT_NONCONTIGUOUS_HOLD")
    if any(1 not in present for present in slots.values()):
        raise ReplayHold("SNAPSHOT_PRIMARY_MISSING_HOLD")
    return sorted(slots)


def _safe_error(exc: Exception, worker: object) -> str:
    if isinstance(exc, worker.ReviewError):
        candidate = str(exc)
        if candidate == "MODEL_NONEXACT_QUOTE_HOLD":
            return candidate
    return "OTHER_REVIEW_HOLD"


def _strict(worker: object, position: int, row: dict,
            response: object, model: str, revision: str) -> dict:
    record = worker.checkpoint_record(position, row, response, model, revision)
    return {"technical_status": "REPLAY_VALIDATED", "quality_decision":
            record["response"]["decision"]}


def _evaluate(worker: object, position: int, row: dict,
              primary: dict, secondary: dict | None) -> tuple[dict, dict]:
    if primary["finish_reason"] != "stop":
        if secondary is not None:
            raise ReplayHold("SECONDARY_WITHOUT_VALID_PRIMARY_HOLD")
        error = {"technical_status": "REPLAY_FAILED",
                 "reason_code": "MODEL_GENERATION_INCOMPLETE_HOLD",
                 "quality_decision": None}
        return error, error.copy()
    try:
        response = json.loads(primary["text"])
    except (ValueError, TypeError):
        if secondary is not None:
            raise ReplayHold("SECONDARY_WITHOUT_VALID_PRIMARY_HOLD") from None
        error = {"technical_status": "REPLAY_FAILED",
                 "reason_code": "MODEL_JSON_HOLD", "quality_decision": None}
        return error, error.copy()
    try:
        strict = _strict(worker, position, row, response, MODEL, REV)
        if secondary is not None:
            raise ReplayHold("SECONDARY_WITHOUT_QUOTE_REPAIR_HOLD")
    except worker.ReviewError as exc:
        strict = {"technical_status": "REPLAY_FAILED",
                  "reason_code": _safe_error(exc, worker),
                  "quality_decision": None}
        if secondary is not None and not isinstance(exc, worker.QuoteValidationError):
            raise ReplayHold("SECONDARY_WITHOUT_QUOTE_REPAIR_HOLD") from None
        if (secondary is not None and secondary["finish_reason"] == "stop"
                and isinstance(exc, worker.QuoteValidationError)):
            try:
                selection = json.loads(secondary["text"])
                candidates = {field: worker.quote_candidates(row, field)
                              for field in exc.invalid_indices}
                repaired = worker.apply_repairs(
                    response, row, exc.invalid_indices, candidates, selection)
                strict = _strict(worker, position, row, repaired, MODEL, REV)
            except (worker.ReviewError, ValueError, TypeError, KeyError):
                pass
    # Independent CPU experiment: does punctuation-only source-anchored repair
    # rescue the original primary response? Never overwrite strict result.
    reconciler = make_reconciler(worker, lambda _event, **_data: None)
    try:
        record = reconciler(position, row, response, MODEL, REV)
        literal = {"technical_status": "REPLAY_VALIDATED",
                   "quality_decision": record["response"]["decision"]}
    except worker.ReviewError as exc:
        literal = {"technical_status": "REPLAY_FAILED",
                   "reason_code": _safe_error(exc, worker),
                   "quality_decision": None}
    return strict, literal


def summarize(args) -> dict:
    if (args.runner.parent != args.input.parent
            or args.output.is_symlink() or args.output.exists()
            or not args.output.parent.is_dir()
            or args.output.parent.is_symlink()):
        raise ReplayHold("PATH_SCOPE_HOLD")
    worker = frozen(args.runner)
    rows = load_original_rows(args.input, worker)
    positions = validate_inventory(args.snapshots)
    runner_sha256 = hashlib.sha256(args.runner.read_bytes()).hexdigest()
    cases = []
    counts = {"original_frozen": Counter(), "literal_experiment": Counter()}
    for position in positions:
        row = rows[position - 1]
        def load(slot, position=position, row=row):
            file = args.snapshots / filename(position, slot)
            if not file.exists() and not file.is_symlink():
                return None
            return read_snapshot(
                file, position=position, generation_index=slot,
                row_digest=worker.input_digest(row),
                runner_sha256=runner_sha256, model=MODEL,
                revision=REV, policy=worker.POLICY)
        primary = load(1)
        secondary = load(2)
        if primary is None:
            raise ReplayHold("PRIMARY_MISSING_HOLD")
        original, literal = _evaluate(worker, position, row, primary, secondary)
        counts["original_frozen"][original["technical_status"]] += 1
        counts["literal_experiment"][literal["technical_status"]] += 1
        cases.append({
            "retry_position": position,
            "original_position": FAILED_POSITIONS[position - 1],
            "saved_generations": 1 + int(secondary is not None),
            "original_frozen": original,
            "literal_experiment": literal,
        })
    return {
        "schema": SCHEMA, "status": "CPU_SNAPSHOT_REPLAY_COMPLETE__NO_ADMISSION",
        "private_values_emitted": False, "gpu_started": False,
        "replayed_cases": len(cases),
        "original_frozen": dict(sorted(counts["original_frozen"].items())),
        "literal_experiment": dict(sorted(counts["literal_experiment"].items())),
        "cases": cases,
        "source_receipts_modified": False, "quality_v1_admitted": 0,
        "training_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for arg in ("runner", "input", "snapshots", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = summarize(args)
        payload = json.dumps(result, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode() + b"\n"
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as dest:
            dest.write(payload)
            dest.flush()
            os.fsync(dest.fileno())
        print(json.dumps({
            "status": result["status"], "replayed_cases": result["replayed_cases"],
            "original_frozen": result["original_frozen"],
            "literal_experiment": result["literal_experiment"],
            "private_values_emitted": False, "gpu_started": False,
        }, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - redact any private exception text
        print(json.dumps({
            "schema": SCHEMA, "status": "CPU_SNAPSHOT_REPLAY_HOLD",
            "private_values_emitted": False, "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
