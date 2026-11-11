"""Read-only GLM frozen validate_response call audit, CPU-testable.

The observer delegates without changing response, row, original validator,
schema, scores or exceptions. It logs ONLY approved categories/counts, never
quotes, messages, model output, identities, source paths or exception strings.
"""
from __future__ import annotations

from collections import Counter

FIELDS = (
    ("specific_source_quotes", "SOURCE"),
    ("specific_target_quotes", "TARGET"),
)
COUNT_CAP = 12


def _shape_and_match(value: object, bodies: list[str],
                     decision: object) -> dict:
    if not isinstance(value, list):
        return {"shape": "NOT_LIST", "missing": 0,
                "empty": 0, "non_string": 0, "too_long": 0,
                "not_in_body": 0, "over_limit": False}
    issues: Counter[str] = Counter()
    for quote in value:
        if not isinstance(quote, str):
            issues["non_string"] += 1
        elif not quote.strip():
            issues["empty"] += 1
        elif len(quote) > 300:
            issues["too_long"] += 1
        elif not any(quote in body for body in bodies):
            issues["not_in_body"] += 1
    if decision == "PASS" and not value:
        issues["missing"] += 1
    return {
        "shape": "LIST",
        "over_limit": len(value) > COUNT_CAP,
        **{name: min(issues[name], 13) for name in (
            "missing", "empty", "non_string", "too_long", "not_in_body"
        )},
    }


def make_observer(worker: object, rows: list[dict], emit: object):
    """Wrap exactly the frozen module's validate_response global.

    Rejected if the caller/row does not map to the expected private input
    digest. This hook is observational and never repairs any model assertion.
    """
    original = worker.validate_response
    digests = {worker.input_digest(row): i + 1
               for i, row in enumerate(rows)}
    if len(digests) != len(rows):
        raise ValueError("DUPLICATE_INPUT_IDENTITY_HOLD")

    def observed(result: object, row: dict):
        key = worker.input_digest(row)
        position = digests.get(key)
        if position is None:
            raise ValueError("UNEXPECTED_REVIEW_INPUT_HOLD")
        if not isinstance(result, dict):
            emit("VALIDATOR_ENTRY", position=position,
                 shape="NOT_OBJECT")
            return original(result, row)
        decision = result.get("decision")
        if decision not in ("PASS", "HOLD", "REJECT"):
            decision = "UNKNOWN"
        emit("VALIDATOR_ENTRY", position=position, shape="OBJECT")
        histories = [
            msg["content"] for msg in row["visible_history"]
            if isinstance(msg, dict) and isinstance(msg.get("content"), str)
        ]
        targets = [row["target_text"]] if isinstance(row.get("target_text"), str) else []
        for field, label in FIELDS:
            issues = _shape_and_match(
                result.get(field), histories if label == "SOURCE" else targets,
                decision)
            emit("VALIDATOR_QUOTE_DIAGNOSTIC", position=position,
                 field=label, **issues)
        return original(result, row)

    return observed
