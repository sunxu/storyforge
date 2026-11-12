"""R60 P1: strictly verified two-model review summary, CPU-only.

The two outputs must derive from the exact same 25 source rows in the same order.
Private checkpoints remain read-only. Output is SAFE: positions, statuses and
counts only; no blind IDs, quotes, prompts, notes, scores or raw errors.

Important distinctions:
  VERIFIED + PASS/HOLD/REJECT: frozen reviewer validated the checkpoint.
  TECHNICAL_FAILURE: signed failure receipt, quality=None.
  MISSING: no receipt, quality=None.
  BAD/foreign/mismatched receipts: fail closed; never normalize to MISSING.
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

from r60_review_isolation_core import canonical, failure_name, validate_failure

SCHEMA = "storyforge_r60_p1_dual_model_review_summary_safe_v1"
A_MODEL = "Qwen/Qwen3-32B"
A_REV = "9216db5781bf21249d130ec9da846c4624c16137"
A_INPUT_SHA = "492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069"
B_MODEL = "zai-org/GLM-4-32B-0414"
B_REV = "8dea913c41b543527c2860fb6f3c15c202f24aeb"
B_INPUT_SHA = "01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9"
N = 25
QUALITY = ("PASS", "HOLD", "REJECT")
TECH = ("VERIFIED", "TECHNICAL_FAILURE", "MISSING")
HEX = re.compile(r"[a-f0-9]{64}\Z")
CHECKPOINT = re.compile(r"review_(\d{4})\.private\.json\Z")
FAILURE = re.compile(r"technical_failure_(\d{4})\.safe\.json\Z")


class SummaryHold(ValueError):
    pass


def _file(path: Path, size: int) -> bytes:
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= size):
        raise SummaryHold("INPUT_FILE_HOLD")
    return path.read_bytes()


def _frozen_worker(path: Path, name: str):
    _file(path, 200_000)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SummaryHold("FROZEN_RUNNER_LOAD_HOLD")
    # Local helper imports used by frozen runner must resolve from its own
    # private input bundle, not via unrelated Python environment state.
    sys.path.insert(0, str(path.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    for fn in ("validate_input", "input_digest", "read_checkpoint",
               "checkpoint_name", "validate_response"):
        if not callable(getattr(module, fn, None)):
            raise SummaryHold("FROZEN_RUNNER_API_HOLD")
    if not isinstance(getattr(module, "POLICY", None), str):
        raise SummaryHold("FROZEN_RUNNER_POLICY_HOLD")
    return module


def _rows(path: Path, expected_sha: str, worker: object) -> list[dict]:
    raw = _file(path, 64 * 1024 * 1024)
    if not HEX.fullmatch(expected_sha) or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise SummaryHold("INPUT_SHA_HOLD")
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except ValueError as exc:
        raise SummaryHold("INPUT_JSON_HOLD") from exc
    if len(rows) != N:
        raise SummaryHold("INPUT_COUNT_HOLD")
    seen = set()
    for row in rows:
        worker.validate_input(row)
        digest = worker.input_digest(row)
        if (not isinstance(digest, str) or not HEX.fullmatch(digest)
                or digest in seen):
            raise SummaryHold("INPUT_IDENTITY_HOLD")
        seen.add(digest)
    return rows


def _inventory(directory: Path) -> dict[int, str]:
    if directory.is_symlink() or not directory.is_dir():
        raise SummaryHold("REVIEW_DIR_HOLD")
    slots = {}
    for item in directory.iterdir():
        if item.is_symlink() or not item.is_file():
            raise SummaryHold("REVIEW_FOREIGN_OBJECT_HOLD")
        match_cp = CHECKPOINT.fullmatch(item.name)
        match_fail = FAILURE.fullmatch(item.name)
        if (match_cp is None) == (match_fail is None):
            raise SummaryHold("REVIEW_FOREIGN_NAME_HOLD")
        position = int((match_cp or match_fail).group(1))
        if not 1 <= position <= N or position in slots:
            raise SummaryHold("REVIEW_DUPLICATE_OR_POSITION_HOLD")
        slots[position] = "VERIFIED" if match_cp else "TECHNICAL_FAILURE"
    return slots


def _one_model(rows: list[dict], worker: object, directory: Path,
               model: str, revision: str) -> list[dict]:
    inventory = _inventory(directory)
    results = []
    for position, row in enumerate(rows, 1):
        state = inventory.get(position, "MISSING")
        if state == "VERIFIED":
            expected_name = worker.checkpoint_name(position)
            if expected_name != f"review_{position:04d}.private.json":
                raise SummaryHold("CHECKPOINT_NAME_HOLD")
            record = worker.read_checkpoint(directory / expected_name,
                                            position, row, model, revision)
            if not isinstance(record, dict) or not isinstance(record.get("response"), dict):
                raise SummaryHold("CHECKPOINT_INVALID_HOLD")
            decision = record["response"].get("decision")
            if decision not in QUALITY:
                raise SummaryHold("CHECKPOINT_DECISION_HOLD")
            results.append({"technical_status": state, "quality_decision": decision})
        elif state == "TECHNICAL_FAILURE":
            reason = validate_failure(directory / failure_name(position),
                                      position, worker, row, model, revision)
            # Never treat a technical code as a literary quality decision.
            results.append({"technical_status": state, "quality_decision": None,
                            "technical_reason_code": reason})
        else:
            results.append({"technical_status": state, "quality_decision": None})
    return results


def _counts(items: list[dict]) -> dict:
    status = Counter(x["technical_status"] for x in items)
    quality = Counter(x["quality_decision"] for x in items
                      if x["technical_status"] == "VERIFIED")
    codes = Counter(x["technical_reason_code"] for x in items
                    if x["technical_status"] == "TECHNICAL_FAILURE")
    return {
        "technical": {kind: status[kind] for kind in TECH},
        "quality_from_verified_only": {kind: quality[kind] for kind in QUALITY},
        "technical_reason_codes": dict(sorted(codes.items())),
    }


def _source_key(row: dict) -> str:
    if not isinstance(row, dict) or not isinstance(row.get("blind_id"), str):
        raise SummaryHold("CROSS_MODEL_ROW_SCHEMA_HOLD")
    # The independent blind IDs may differ by model. Never join by blind ID
    # alone, by ordinal position alone, or by source/target excerpts.
    content = {key: val for key, val in row.items() if key != "blind_id"}
    return hashlib.sha256(canonical(content)).hexdigest()


def _align(a_rows: list[dict], b_rows: list[dict]) -> list[int]:
    if len(a_rows) != N or len(b_rows) != N:
        raise SummaryHold("CROSS_MODEL_COUNT_HOLD")
    a_keys = [_source_key(row) for row in a_rows]
    b_keys = [_source_key(row) for row in b_rows]
    if (len(set(a_keys)) != N or len(set(b_keys)) != N
            or set(a_keys) != set(b_keys)):
        raise SummaryHold("CROSS_MODEL_CONTENT_OR_UNIQUE_HOLD")
    b_positions = {key: i for i, key in enumerate(b_keys)}
    return [b_positions[key] for key in a_keys]


def summarize(a_rows: list[dict], b_rows: list[dict],
              a: list[dict], b: list[dict]) -> dict:
    if len(a_rows) != N or len(b_rows) != N or len(a) != N or len(b) != N:
        raise SummaryHold("SUMMARY_COUNT_HOLD")
    alignment = _align(a_rows, b_rows)
    cases = []
    pairs = Counter()
    for pos, (left, b_index) in enumerate(zip(a, alignment), 1):
        right = b[b_index]
        if (left["technical_status"] == "VERIFIED"
                and right["technical_status"] == "VERIFIED"):
            pairs[(left["quality_decision"], right["quality_decision"])] += 1
            comparison = ("AGREE" if left["quality_decision"] == right["quality_decision"]
                          else "DISAGREE")
        else:
            comparison = "NOT_COMPARABLE"
        cases.append({"position_A": pos, "position_B": b_index + 1,
                      "A": left, "B": right,
                      "quality_comparison": comparison})
    agree = sum(v for (x, y), v in pairs.items() if x == y)
    compared = sum(pairs.values())
    matrix = {
        x: {y: pairs[(x, y)] for y in QUALITY} for x in QUALITY
    }
    return {
        "schema": SCHEMA,
        "status": "P1_SAFE_SUMMARY_PASS__NO_TRAINING_ADMISSION",
        "private_values_emitted": False,
        "gpu_started": False,
        "cases_total": N,
        "cross_model_alignment": "EXACT_CONTENT_EXCLUDING_BLIND_ID",
        "model_A": {"model": A_MODEL, "revision": A_REV, **_counts(a)},
        "model_B": {"model": B_MODEL, "revision": B_REV, **_counts(b)},
        "both_verified": compared,
        "quality_agreement": agree,
        "quality_disagreement": compared - agree,
        "quality_not_comparable": N - compared,
        "quality_pair_matrix_A_rows_B_columns": matrix,
        "cases": cases,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }


def run(args) -> dict:
    if (args.output.is_symlink() or args.output.exists()
            or not args.output.parent.is_dir()
            or args.output.parent.is_symlink()):
        raise SummaryHold("OUTPUT_EXISTS_OR_DIR_HOLD")
    a_worker = _frozen_worker(args.runner_a, "r60_summary_frozen_A")
    b_worker = _frozen_worker(args.runner_b, "r60_summary_frozen_B")
    a_rows = _rows(args.input_a, A_INPUT_SHA, a_worker)
    b_rows = _rows(args.input_b, B_INPUT_SHA, b_worker)
    _align(a_rows, b_rows)
    a = _one_model(a_rows, a_worker, args.reviews_a, A_MODEL, A_REV)
    b = _one_model(b_rows, b_worker, args.reviews_b, B_MODEL, B_REV)
    report = summarize(a_rows, b_rows, a, b)
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="CPU-only R60 dual model SAFE review summary")
    for name in ("runner_a", "runner_b", "input_a", "input_b",
                 "reviews_a", "reviews_b", "output"):
        parser.add_argument("--" + name.replace("_", "-"), required=True,
                            type=Path)
    args = parser.parse_args()
    try:
        report = run(args)
    except Exception:  # noqa: BLE001 - no arbitrary private exception strings
        print(json.dumps({"schema": SCHEMA, "status": "P1_SUMMARY_HOLD",
                          "private_values_emitted": False,
                          "gpu_started": False}, sort_keys=True))
        return 42
    # Print only aggregate, never echo any case metadata or private values.
    print(json.dumps({
        "schema": SCHEMA, "status": report["status"],
        "cases_total": report["cases_total"],
        "A": report["model_A"]["technical"],
        "B": report["model_B"]["technical"],
        "both_verified": report["both_verified"],
        "quality_agreement": report["quality_agreement"],
        "quality_disagreement": report["quality_disagreement"],
        "private_values_emitted": False, "gpu_started": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
