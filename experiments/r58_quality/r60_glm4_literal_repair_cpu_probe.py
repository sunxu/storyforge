"""R60 GLM private-runner CPU integration preflight for opt-in literal repair.

Reads one pinned private source row without printing its contents. Synthesizes a
schema-valid HOLD response using genuine contiguous source/target excerpts.
Introduces one punctuation-only target error; confirms original frozen
checkpoint rejects it and the wrapper returns an independently valid record.
No model, vLLM or GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from r60_glm4_exact_quote_repair import make_reconciler, reconcile_quote

SCHEMA = "storyforge_r60_glm4_literal_repair_cpu_probe_safe_v1"
INPUT_SHA = "01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9"
MODEL = "zai-org/GLM-4-32B-0414"
REV = "8dea913c41b543527c2860fb6f3c15c202f24aeb"


class ProbeHold(ValueError):
    pass


SAFE_REASONS = frozenset({
    "FROZEN_SCOPE_HOLD", "SOURCE_SHA_HOLD", "SOURCE_PARSE_HOLD",
    "FROZEN_IMPORT_HOLD", "FROZEN_RUNNER_API_HOLD",
    "FROZEN_INPUT_VALIDATION_HOLD", "SYNTHETIC_BODY_TOO_SHORT_HOLD",
    "SYNTHETIC_NO_UNIQUE_PUNCTUATION_CANDIDATE_HOLD",
    "SYNTHETIC_ORIGINAL_REJECTED_OTHER_REASON_HOLD",
    "ORIGINAL_NONEXACT_NOT_DETECTED_HOLD",
    "PUNCTUATION_REPAIR_INTEGRATION_HOLD", "FROZEN_REVALIDATION_HOLD",
    "SYNTHETIC_SOURCE_EVIDENCE_HOLD",
})


def synthetic_punctuation_case(body: str) -> tuple[str, str]:
    """Choose an exact, punctuation-ending original slice with one changed
    terminal punctuation. Never invent candidates without validating that
    the same production reconciliation algorithm uniquely recovers the slice.
    """
    if len(body) < 12:
        raise ProbeHold("SYNTHETIC_BODY_TOO_SHORT_HOLD")
    # Prefer an excerpt ending on existing punctuation instead of appending
    # arbitrary punctuation to a fixed 24-character prefix.
    punctuation = "。，！？；,.!?"
    for length in range(12, min(len(body), 100) + 1):
        exact = body[:length]
        if exact[-1] not in punctuation:
            continue
        for altered in punctuation:
            if altered == exact[-1]:
                continue
            broken = exact[:-1] + altered
            if broken in body:
                continue
            if reconcile_quote(broken, [body]) == exact:
                return exact, broken
    raise ProbeHold("SYNTHETIC_NO_UNIQUE_PUNCTUATION_CANDIDATE_HOLD")


def inspect(runner: Path, source: Path) -> dict:
    if (runner.parent != source.parent
            or runner.is_symlink() or source.is_symlink()
            or not runner.is_file() or not source.is_file()
            or not 0 < runner.stat().st_size < 200000):
        raise ProbeHold("FROZEN_SCOPE_HOLD")
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != INPUT_SHA:
        raise ProbeHold("SOURCE_SHA_HOLD")
    try:
        first = next(line for line in raw.splitlines() if line.strip())
        row = json.loads(first)
    except (ValueError, StopIteration) as exc:
        raise ProbeHold("SOURCE_PARSE_HOLD") from exc
    spec = importlib.util.spec_from_file_location("r60_glm_literal_private_cpu", runner)
    if spec is None or spec.loader is None:
        raise ProbeHold("FROZEN_IMPORT_HOLD")
    sys.path.insert(0, str(runner.parent))
    try:
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
    finally:
        sys.path.pop(0)
    for name in ("validate_input", "response_schema", "checkpoint_record", "validate_response"):
        if not callable(getattr(worker, name, None)):
            raise ProbeHold("FROZEN_RUNNER_API_HOLD")
    try:
        worker.validate_input(row)
    except Exception as exc:
        raise ProbeHold("FROZEN_INPUT_VALIDATION_HOLD") from exc
    scores = {name: 4 for name in worker.response_schema()["properties"]["scores"]["properties"]}
    flags = {name: False for name in
             worker.response_schema()["properties"]["severe_flags"]["properties"]}
    source_body = row["visible_history"][0]["content"]
    target_body = row["target_text"]
    if len(source_body) < 12 or len(target_body) < 12:
        raise ProbeHold("SYNTHETIC_BODY_TOO_SHORT_HOLD")
    source_quote = source_body[:24]
    target_quote, broken_quote = synthetic_punctuation_case(target_body)
    response = {
        "decision": "HOLD",
        "scores": scores,
        "severe_flags": flags,
        "specific_source_quotes": [source_quote],
        "specific_target_quotes": [broken_quote],
        "literary_quality_notes": "合成CPU测试说明：仅检验逐字引用",
        "uncertainty": "这是合成诊断，不属于真实审核结果。",
    }
    original = worker.checkpoint_record
    try:
        original(1, row, response, MODEL, REV)
    except worker.ReviewError as exc:
        if str(exc) != "MODEL_NONEXACT_QUOTE_HOLD":
            raise ProbeHold("SYNTHETIC_ORIGINAL_REJECTED_OTHER_REASON_HOLD") from None
        original_failed = True
    else:
        original_failed = False
    if not original_failed:
        raise ProbeHold("ORIGINAL_NONEXACT_NOT_DETECTED_HOLD")
    events = []
    observed = make_reconciler(
        worker, lambda event, **fields: events.append((event, fields)))
    try:
        repaired = observed(1, row, response, MODEL, REV)
    except worker.ReviewError as exc:
        raise ProbeHold("PUNCTUATION_REPAIR_INTEGRATION_HOLD") from exc
    try:
        worker.validate_response(repaired["response"], row)
    except worker.ReviewError as exc:
        raise ProbeHold("FROZEN_REVALIDATION_HOLD") from exc
    if (repaired["response"]["decision"] != "HOLD"
            or repaired["response"]["specific_target_quotes"] != [target_quote]
            or response["specific_target_quotes"] != [broken_quote]
            or not any(event == "QUOTE_RECONCILIATION_CANDIDATE"
                       for event, _ in events)):
        raise ProbeHold("FROZEN_REVALIDATION_HOLD")
    # Do not return events (positions, strings or metadata) to the caller.
    return {"schema": SCHEMA,
            "status": "GLM_LITERAL_FROZEN_CPU_INTEGRATION_PASS",
            "frozen_runner_used": True,
            "gpu_started": False,
            "private_values_emitted": False,
            "original_rejected_inexact": True,
            "punctuation_repair_revalidated": True,
            "quality_decision_changed": False,
            "original_response_modified": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.runner, args.input), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never log arbitrary exception text
        # Only self-authored bounded reasons can reach stdout; frozen
        # ReviewError, private source and traceback strings are suppressed.
        reason = str(exc) if type(exc) is ProbeHold and str(exc) in SAFE_REASONS else "UNEXPECTED_PRIVATE_REDACTED_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "GLM_LITERAL_FROZEN_CPU_INTEGRATION_HOLD",
            "reason_code": reason,
            "private_values_emitted": False, "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
