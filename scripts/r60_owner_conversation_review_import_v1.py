#!/usr/bin/env python3
"""Import R60 Owner conversation confirmations into a separate private audit ledger.

This tool does NOT create official Owner semantic checks, attest reviewer identity,
change verdicts, or make training-admission decisions. It is deliberately a
create-only, fail-closed importer for the conversation handoff artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

SCHEMA = "storyforge_r60_p2a_owner_60_conversation_review_handoff_v1"
LEDGER_SCHEMA = "storyforge_r60_owner_conversation_review_ledger_v1"
SAFE_SCHEMA = "storyforge_r60_owner_conversation_review_import_safe_v1"
MANIFEST_SCHEMA = "storyforge_r60_owner_conversation_review_import_manifest_v1"
DIMENSIONS = {"player_agency", "hard_rule", "safety"}
DECISIONS = {"A", "B", "C"}
DECISION_COUNTS = {"A": 58, "B": 1, "C": 1}
MAX_INPUT_BYTES = 8 * 1024 * 1024


class ImportHold(Exception):
    """Safe, non-sensitive import rejection."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ImportHold(reason)


def validate_handoff(data: Any) -> list[dict[str, Any]]:
    """Validate all 60 explicit conversation decisions without inferring identity."""
    _require(isinstance(data, dict), "HANDOFF_NOT_OBJECT")
    _require(data.get("schema") == SCHEMA, "HANDOFF_SCHEMA_MISMATCH")
    _require(
        data.get("status")
        == "CONVERSATIONAL_OWNER_REVIEW_COMPLETE__FORMAL_RECEIPT_NOT_CREATED",
        "HANDOFF_STATUS_NOT_IMPORTABLE",
    )
    scope = data.get("review_scope")
    _require(isinstance(scope, dict), "REVIEW_SCOPE_MISSING")
    _require(scope.get("cases") == 20, "CASE_COUNT_MISMATCH")
    _require(scope.get("dimensions_per_case") == 3, "DIMENSION_COUNT_MISMATCH")
    _require(scope.get("total_items") == 60, "ITEM_COUNT_MISMATCH")
    _require(set(scope.get("dimensions", [])) == DIMENSIONS, "DIMENSION_SET_MISMATCH")

    owner = data.get("owner_review")
    _require(isinstance(owner, dict), "OWNER_REVIEW_MISSING")
    _require(
        owner.get("reviewer_type") == "OWNER_EXPLICIT_CONVERSATION_CONFIRMATIONS",
        "OWNER_REVIEWER_TYPE_MISMATCH",
    )
    _require(owner.get("formal_owner_identity_attested") is False,
             "FORMAL_IDENTITY_MUST_NOT_BE_ATTESTED")
    _require(owner.get("formal_owner_receipt_created") is False,
             "FORMAL_RECEIPT_ALREADY_CLAIMED")
    _require(
        owner.get("decision_counts") == {
            "A_SUPPORT_ORIGINAL": 58,
            "B_DO_NOT_SUPPORT_ORIGINAL": 1,
            "C_CONTEXT_INSUFFICIENT_REVIEW": 1,
        },
        "OWNER_DECISION_SUMMARY_MISMATCH",
    )

    cross = data.get("claude_cross_review")
    _require(isinstance(cross, dict), "CROSS_REVIEW_MISSING")
    _require(cross.get("reviewer_type") == "AI_CROSS_REVIEW_ADVISORY_NOT_OWNER",
             "CROSS_REVIEWER_TYPE_MISMATCH")
    _require(cross.get("model") == "claude-opus-5-5", "CROSS_REVIEW_MODEL_MISMATCH")
    _require(cross.get("validated_rows") == 60, "CROSS_REVIEW_COUNT_MISMATCH")

    safety = data.get("safety_and_scope")
    _require(isinstance(safety, dict), "SAFETY_SCOPE_MISSING")
    _require(safety.get("original_files_modified") is False,
             "ORIGINAL_MODIFICATION_CLAIM_HOLD")
    _require(safety.get("owner_formal_jsonl_created") is False,
             "FORMAL_OWNER_JSONL_CLAIM_HOLD")
    _require(safety.get("owner_identity_fabricated") is False,
             "OWNER_IDENTITY_CLAIM_HOLD")
    _require(safety.get("gpu_started") is False, "GPU_STATE_HOLD")
    _require(safety.get("training_authorized") is False, "TRAINING_STATE_HOLD")

    items = data.get("items")
    _require(isinstance(items, list) and len(items) == 60, "ITEM_CARDINALITY_HOLD")
    seen: set[tuple[str, str]] = set()
    counts = {"A": 0, "B": 0, "C": 0}
    by_case: dict[int, set[str]] = {}

    for expected_item, row in enumerate(items, 1):
        _require(isinstance(row, dict), "ITEM_ROW_SHAPE_HOLD")
        _require(row.get("item") == expected_item, "ITEM_ORDER_HOLD")
        case_number = row.get("case_number")
        _require(type(case_number) is int and 1 <= case_number <= 20,
                 "CASE_NUMBER_HOLD")
        _require(case_number == ((expected_item - 1) // 3) + 1,
                 "CASE_SEQUENCE_HOLD")
        blind_id = row.get("blind_id")
        _require(isinstance(blind_id, str) and 8 <= len(blind_id) <= 128,
                 "BLIND_ID_SHAPE_HOLD")
        dimension = row.get("dimension")
        _require(dimension in DIMENSIONS, "DIMENSION_VALUE_HOLD")
        pair = (blind_id, dimension)
        _require(pair not in seen, "DUPLICATE_BLIND_DIMENSION")
        seen.add(pair)
        by_case.setdefault(case_number, set()).add(dimension)

        decision = row.get("owner_conversation_decision")
        _require(decision in DECISIONS, "OWNER_DECISION_VALUE_HOLD")
        counts[decision] += 1
        _require(isinstance(row.get("original_owner_verdict"), str)
                 and row["original_owner_verdict"], "ORIGINAL_VERDICT_MISSING")
        _require(row.get("formal_owner_receipt") is False,
                 "ROW_FORMAL_RECEIPT_CLAIM_HOLD")
        _require(isinstance(row.get("owner_decision_interpretation"), str),
                 "OWNER_DECISION_INTERPRETATION_MISSING")
        note = row.get("owner_note")
        _require(note is None or isinstance(note, str), "OWNER_NOTE_SHAPE_HOLD")

        claude_conclusion = row.get("claude_conclusion")
        _require(
            claude_conclusion in (
                "SUPPORTS_VERDICT", "DOES_NOT_SUPPORT_VERDICT", "INSUFFICIENT_CONTEXT"
            ),
            "CLAUDE_CONCLUSION_VALUE_HOLD",
        )
        _require(isinstance(row.get("claude_reasoning_summary"), str)
                 and row["claude_reasoning_summary"],
                 "CLAUDE_REASONING_MISSING")
        unresolved = row.get("claude_unresolved_context", [])
        _require(isinstance(unresolved, (list, str)), "CLAUDE_UNRESOLVED_SHAPE_HOLD")

    _require(counts == DECISION_COUNTS, "OWNER_DECISION_COUNTS_HOLD")
    _require(len(by_case) == 20 and all(v == DIMENSIONS for v in by_case.values()),
             "CASE_DIMENSION_COVERAGE_HOLD")
    _require(len(seen) == 60, "PAIR_COVERAGE_HOLD")
    return items


def build_artifacts(data: dict[str, Any], source_sha256: str) -> dict[str, bytes]:
    items = validate_handoff(data)
    ledger_rows = []
    for row in items:
        # Keep the original values; do not manufacture official reviewer fields.
        ledger_rows.append({
            "schema": LEDGER_SCHEMA,
            "item": row["item"],
            "case_number": row["case_number"],
            "blind_id": row["blind_id"],
            "dimension": row["dimension"],
            "original_owner_verdict": row["original_owner_verdict"],
            "owner_conversation_decision": row["owner_conversation_decision"],
            "owner_decision_interpretation": row["owner_decision_interpretation"],
            "owner_note": row.get("owner_note"),
            "claude_model": data["claude_cross_review"]["model"],
            "claude_reviewer_type": data["claude_cross_review"]["reviewer_type"],
            "claude_conclusion": row["claude_conclusion"],
            "claude_reasoning_summary": row["claude_reasoning_summary"],
            "claude_unresolved_context": row.get("claude_unresolved_context", []),
            "record_type": "CONVERSATION_AUDIT_NOT_OFFICIAL_SEMANTIC_CHECK",
            "formal_owner_receipt": False,
        })
    ledger_raw = b"".join(_canonical(row) + b"\n" for row in ledger_rows)
    decision_counts = {
        decision: sum(r["owner_conversation_decision"] == decision for r in items)
        for decision in ("A", "B", "C")
    }
    dimension_counts = {
        dim: sum(r["dimension"] == dim for r in items)
        for dim in sorted(DIMENSIONS)
    }
    claude_counts: dict[str, int] = {}
    for row in items:
        value = row["claude_conclusion"]
        claude_counts[value] = claude_counts.get(value, 0) + 1

    safe = {
        "schema": SAFE_SCHEMA,
        "status": "OWNER_CONVERSATION_LEDGER_CREATED__NOT_FORMAL_OWNER_RECEIPT",
        "total_items": 60,
        "case_count": 20,
        "decision_counts": decision_counts,
        "dimension_counts": dimension_counts,
        "claude_conclusion_counts": claude_counts,
        "owner_identity_attested": False,
        "formal_owner_receipt_created": False,
        "official_semantic_checks_created": False,
        "original_files_modified": False,
        "private_values_emitted": False,
        "gpu_started": False,
        "training_authorized": False,
    }
    safe_raw = _canonical(safe) + b"\n"
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": safe["status"],
        "source_handoff_sha256": source_sha256,
        "ledger_sha256": _sha256(ledger_raw),
        "safe_sha256": _sha256(safe_raw),
        "ledger_rows": len(ledger_rows),
        "files": [
            "OWNER_CONVERSATION_REVIEW_LEDGER_PRIVATE.jsonl",
            "OWNER_CONVERSATION_REVIEW_IMPORT_SAFE.json",
        ],
        "identity_attestation": "NONE",
        "formal_semantic_check_conversion": False,
        "original_files_modified": False,
        "gpu_started": False,
        "training_authorized": False,
    }
    manifest_raw = _canonical(manifest) + b"\n"
    return {
        "OWNER_CONVERSATION_REVIEW_LEDGER_PRIVATE.jsonl": ledger_raw,
        "OWNER_CONVERSATION_REVIEW_IMPORT_SAFE.json": safe_raw,
        "OWNER_CONVERSATION_REVIEW_IMPORT_MANIFEST.json": manifest_raw,
    }


def _read_private_input(path: Path) -> bytes:
    _require(not path.is_symlink(), "INPUT_SYMLINK_HOLD")
    _require(path.is_file(), "INPUT_FILE_MISSING")
    info = path.lstat()
    _require(stat.S_IMODE(info.st_mode) == 0o600, "INPUT_MODE_MUST_BE_0600")
    _require(info.st_nlink == 1, "INPUT_HARDLINK_HOLD")
    _require(info.st_size <= MAX_INPUT_BYTES, "INPUT_SIZE_LIMIT_HOLD")
    raw = path.read_bytes()
    _require(len(raw) == info.st_size, "INPUT_READ_SIZE_MISMATCH")
    return raw


def import_handoff(input_path: Path, output_dir: Path) -> dict[str, Any]:
    raw = _read_private_input(input_path)
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ImportHold("HANDOFF_JSON_INVALID") from None
    source_sha = _sha256(raw)
    artifacts = build_artifacts(data, source_sha)

    _require(output_dir.is_absolute(), "OUTPUT_PATH_MUST_BE_ABSOLUTE")
    _require(not output_dir.exists() and not output_dir.is_symlink(),
             "OUTPUT_MUST_BE_NEW")
    parent = output_dir.parent
    _require(parent.is_dir() and not parent.is_symlink(), "OUTPUT_PARENT_INVALID")
    _require(stat.S_IMODE(parent.stat().st_mode) == 0o700,
             "OUTPUT_PARENT_MODE_MUST_BE_0700")

    output_dir.mkdir(mode=0o700)
    try:
        for name, content in artifacts.items():
            target = output_dir / name
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        safe = json.loads(artifacts["OWNER_CONVERSATION_REVIEW_IMPORT_SAFE.json"])
        return safe
    except Exception:
        # Never overwrite or silently leave a partial output as a successful run.
        for child in output_dir.iterdir():
            if child.is_file() and not child.is_symlink():
                child.unlink()
        output_dir.rmdir()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = import_handoff(args.input_json.expanduser(), args.output_dir.expanduser())
    except ImportHold as exc:
        print(json.dumps({
            "status": "OWNER_CONVERSATION_IMPORT_HOLD",
            "reason_code": str(exc),
            "private_values_emitted": False,
            "original_files_modified": False,
            "gpu_started": False,
            "training_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
