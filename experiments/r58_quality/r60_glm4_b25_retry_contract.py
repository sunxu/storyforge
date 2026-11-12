"""R60 GLM B25: strict read-only 25-case baseline -> 12-case retry view.

The source 25-case input remains pinned and unchanged. Retry positions 1..12
are *local retry indices*; the returned position map identifies their original
1..25 positions. The old 13 private checkpoints are never rewritten.
"""
from __future__ import annotations

import re
from pathlib import Path

from r60_review_isolation_core import (
    IsolationHold,
    emit,
    failure_name,
    validate_failure,
)

MODEL = "zai-org/GLM-4-32B-0414"
REVISION = "8dea913c41b543527c2860fb6f3c15c202f24aeb"
FAILED_POSITIONS = (1, 5, 6, 7, 9, 12, 15, 20, 22, 23, 24, 25)
VALID_POSITIONS = tuple(
    pos for pos in range(1, 26) if pos not in FAILED_POSITIONS
)
REASON = "MODEL_NONEXACT_QUOTE_HOLD"


def verify_baseline(worker: object, rows: list[dict], baseline: Path,
                    destination: Path) -> tuple[list[dict], tuple[int, ...]]:
    """Require every original record to be exactly as expected and verified."""
    if (len(rows) != 25 or baseline == destination
            or baseline.is_symlink() or not baseline.is_dir()
            or destination.is_symlink() or not destination.is_dir()
            or any(destination.iterdir())):
        raise IsolationHold("RETRY_PATH_OR_INPUT_HOLD")
    expected_names = {
        (worker.checkpoint_name(pos) if pos in VALID_POSITIONS
         else failure_name(pos)) for pos in range(1, 26)
    }
    objects = list(baseline.iterdir())
    if any(obj.is_symlink() or not obj.is_file()
           or not re.fullmatch(
               r"(review_[0-9]{4}\.private|technical_failure_[0-9]{4}\.safe)\.json",
               obj.name) for obj in objects):
        raise IsolationHold("RETRY_BASELINE_OBJECT_HOLD")
    if {obj.name for obj in objects} != expected_names:
        raise IsolationHold("RETRY_BASELINE_INVENTORY_HOLD")
    for pos in VALID_POSITIONS:
        checkpoint = worker.read_checkpoint(
            baseline / worker.checkpoint_name(pos),
            pos, rows[pos - 1], MODEL, REVISION)
        if checkpoint is None:
            raise IsolationHold("RETRY_BASELINE_CHECKPOINT_HOLD")
    for pos in FAILED_POSITIONS:
        reason = validate_failure(
            baseline / failure_name(pos), pos, worker, rows[pos - 1],
            MODEL, REVISION)
        if reason != REASON:
            raise IsolationHold("RETRY_BASELINE_REASON_HOLD")
    selected = [rows[pos - 1] for pos in FAILED_POSITIONS]
    if len({row["blind_id"] for row in selected}) != len(FAILED_POSITIONS):
        raise IsolationHold("RETRY_BLIND_ID_DUPLICATE_HOLD")
    emit("RETRY_BASELINE_VERIFIED", original_total=25,
         original_verified=13, original_technical_failures=12,
         retry_count=12, original_positions=list(FAILED_POSITIONS))
    return selected, FAILED_POSITIONS


def quote_shape_diagnostic(worker: object, emit_fn: object, *, repair: bool = False):
    """Build a wrapper for the exact frozen checkpoint_record global.

    Emit only field identity and TYPE/COUNT error, never quotes or a response.
    Optional conservative repair only converts an already exact source quote
    string to a one-item list or removes identical duplicate evidence quotes.
    The original frozen verifier still validates the resulting record.
    """
    original = worker.checkpoint_record

    def observed(position, row, response, model, revision):
        amended = response
        if isinstance(response, dict):
            for field, ident in (
                ("specific_source_quotes", "SOURCE"),
                ("specific_target_quotes", "TARGET"),
            ):
                value = response.get(field)
                if not isinstance(value, list):
                    emit_fn("QUOTE_SHAPE_DIAGNOSTIC", position=position,
                            field=ident, violation="NOT_LIST")
                elif len(value) > 12:
                    emit_fn("QUOTE_SHAPE_DIAGNOSTIC", position=position,
                            field=ident, violation="OVER_LIMIT")
                if not repair:
                    continue
                bodies = (
                    [x["content"] for x in row["visible_history"]]
                    if ident == "SOURCE" else [row["target_text"]]
                )
                normalized = None
                if (isinstance(value, str) and 0 < len(value) <= 300
                        and value.strip()
                        and any(value in body for body in bodies)):
                    normalized = [value]
                    operation = "EXACT_SINGLETON"
                elif isinstance(value, list) and len(value) > 12:
                    unique = list(dict.fromkeys(value)) if all(
                        isinstance(item, str) for item in value
                    ) else value
                    if (len(unique) <= 12 and all(
                            item and len(item) <= 300
                            and any(item in body for body in bodies)
                            for item in unique)):
                        normalized = unique
                        operation = "EXACT_DEDUPLICATE"
                if normalized is not None:
                    if amended is response:
                        amended = dict(response)
                    amended[field] = normalized
                    emit_fn("QUOTE_SHAPE_REPAIR", position=position,
                            field=ident, operation=operation,
                            substantive_text_changed=False)
        return original(position, row, amended, model, revision)

    return observed
