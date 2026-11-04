"""Aggregate-only preflight for private R59 Owner Evidence; NO admission.

Reports missing Owner evidence dimensions without emitting IDs, source text,
paths, reviewer values, or hashes. The authoritative Review Bind remains the
only stage that associates A/B evidence and constructs reviewed candidates.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from gold_source_context_stage import _private_file, _read_rows
from quality_v1 import EVIDENCE, SEVERE, sha
from r59_staging_receipt import valid_staging_receipt

SCHEMA = "storyforge-r59-owner-evidence-preflight-safe-v1"
HEX = re.compile(r"^[0-9a-f]{64}$")
NEGATIVE = (
    "known_protected_overlap",
    "final_heldout_overlap",
    "protected_test_body_accessed",
)
READY_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
READY_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"


class PreflightHold(ValueError):
    pass


def _valid_ref(value):
    return isinstance(value, str) and bool(value.strip())


def preflight(staged, owner_rows, staged_sha, source_context_sha):
    if not isinstance(staged, list) or not isinstance(owner_rows, list):
        raise PreflightHold("INPUT_ROWS_INVALID")
    if not isinstance(staged_sha, str) or HEX.fullmatch(staged_sha) is None:
        raise PreflightHold("STAGED_PIN_INVALID")
    if not isinstance(source_context_sha, str) or HEX.fullmatch(source_context_sha) is None:
        raise PreflightHold("SOURCE_CONTEXT_PIN_INVALID")

    owners = {}
    for row in owner_rows:
        if not isinstance(row, dict):
            raise PreflightHold("OWNER_ROW_INVALID")
        cid = row.get("case_id")
        if not isinstance(cid, str) or not cid or cid in owners:
            raise PreflightHold("OWNER_IDENTITY_DUPLICATE_OR_INVALID")
        owners[cid] = row

    ready = [
        row for row in staged
        if isinstance(row, dict)
        and row.get("schema") == READY_SCHEMA
        and row.get("status") == READY_STATUS
    ]
    if len({row.get("case_id") for row in ready}) != len(ready):
        raise PreflightHold("STAGE_IDENTITY_DUPLICATE")

    matched = 0
    identity_mismatch = 0
    complete_rows = 0
    checks = Counter()
    for stage in ready:
        owner = owners.get(stage.get("case_id"))
        if not isinstance(owner, dict):
            identity_mismatch += 1
            continue
        if any(owner.get(k) != stage.get(k) for k in (
            "case_id", "target_sha256", "story_id", "session_id"
        )):
            identity_mismatch += 1
            continue
        matched += 1
        checks_before_row = checks.copy()

        flags = owner.get("owner_supplemental_severe_flags")
        flags_ok = (
            isinstance(flags, dict) and set(flags) == set(SEVERE)
            and all(type(flags[k]) is bool for k in SEVERE)
        )
        checks["supplemental_severe_flags_complete"] += int(flags_ok)
        checks["supplemental_severe_evidence_ref_present"] += int(
            _valid_ref(owner.get("owner_supplemental_severe_evidence_ref"))
        )

        evidence = owner.get("evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        for key in EVIDENCE:
            checks[f"evidence_true:{key}"] += int(evidence.get(key) is True)
        for key in NEGATIVE:
            checks[f"negative_evidence_false:{key}"] += int(evidence.get(key) is False)

        checks["source_version_sha256_valid"] += int(
            isinstance(owner.get("source_version_sha256"), str)
            and HEX.fullmatch(owner["source_version_sha256"]) is not None
        )
        checks["world_graph_sha256_valid"] += int(
            isinstance(owner.get("world_graph_sha256"), str)
            and HEX.fullmatch(owner["world_graph_sha256"]) is not None
        )
        checks["world_component_id_present"] += int(_valid_ref(owner.get("world_component_id")))
        checks["split_valid"] += int(owner.get("split") in ("train", "validation"))
        checks["reviewer_a_evidence_ref_present"] += int(_valid_ref(owner.get("reviewer_a_evidence_ref")))
        checks["reviewer_b_evidence_ref_present"] += int(_valid_ref(owner.get("reviewer_b_evidence_ref")))
        checks["staged_file_pin_matches"] += int(owner.get("staged_file_sha256") == staged_sha)
        checks["source_context_pin_matches"] += int(owner.get("source_context_file_sha256") == source_context_sha)

        # A row is field-complete only when every required presence/value check
        # passes for this exact matched candidate. This is not evidence
        # authenticity, independent reviewer proof, or Quality-v1 admission.
        if all(checks[key] - checks_before_row[key] == 1 for key in checks):
            complete_rows += 1

    incomplete_rows = matched - complete_rows
    missing = {
        key: matched - value
        for key, value in sorted(checks.items())
        if matched and value < matched
    }
    complete = (
        matched == len(ready) and identity_mismatch == 0 and matched > 0
        and not missing
    )
    partial = complete_rows > 0 and not complete
    return {
        "schema": SCHEMA,
        "status": (
            "OWNER_EVIDENCE_FIELDS_COMPLETE__BINDER_AND_OWNER_ATTESTATION_STILL_REQUIRED"
            if complete else
            "OWNER_EVIDENCE_PARTIAL_FIELDS_PRESENT__BINDER_REVIEW_REQUIRED"
            if partial else "OWNER_EVIDENCE_PREFLIGHT_HOLD"
        ),
        "staged_ready": len(ready),
        "owner_rows": len(owner_rows),
        "identity_matched": matched,
        "identity_missing_or_mismatched": identity_mismatch,
        "rows_with_all_required_fields_present": complete_rows,
        "rows_missing_one_or_more_required_fields": incomplete_rows,
        "field_checks_passed": dict(sorted(checks.items())),
        "field_checks_missing": missing,
        "reviewer_independence_independently_proven": False,
        "protected_set_completeness_independently_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def run(staged_path: Path, receipt_path: Path, owner_path: Path):
    staged_raw = _private_file(staged_path, 160 * 1024 * 1024)
    receipt_raw = _private_file(receipt_path, 1024 * 1024)
    owner_raw = _private_file(owner_path, 40 * 1024 * 1024)
    try:
        receipt = json.loads(receipt_raw)
    except (ValueError, UnicodeError):
        raise PreflightHold("STAGING_RECEIPT_INVALID") from None
    if not valid_staging_receipt(receipt, sha(staged_raw)):
        raise PreflightHold("STAGING_RECEIPT_MISMATCH")
    upstream = receipt.get("source_context_file_sha256")
    if not isinstance(upstream, str) or HEX.fullmatch(upstream) is None:
        raise PreflightHold("SOURCE_CONTEXT_PIN_INVALID")
    return preflight(
        _read_rows(staged_raw), _read_rows(owner_raw), sha(staged_raw), upstream
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-jsonl", type=Path, required=True)
    parser.add_argument("--staging-safe", type=Path, required=True)
    parser.add_argument("--owner-evidence-jsonl", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.staged_jsonl, args.staging_safe, args.owner_evidence_jsonl)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PreflightHold, OSError):
        reason = "OWNER_EVIDENCE_PREFLIGHT_INPUT_HOLD"
    except Exception:  # noqa: BLE001 - never expose private exception values
        reason = "OWNER_EVIDENCE_PREFLIGHT_INTERNAL_HOLD"
    print(json.dumps({
        "schema": SCHEMA, "status": "OWNER_EVIDENCE_PREFLIGHT_HOLD",
        "reason_code": reason, "quality_v1_admitted": 0,
        "training_authorized": False, "gpu_started": False,
        "r50_accessed": False, "private_values_emitted": False,
    }, sort_keys=True))
    return 42


if __name__ == "__main__":
    raise SystemExit(main())
