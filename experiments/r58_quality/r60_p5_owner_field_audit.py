"""R60 P5: bounded, offline Owner field audit for P4's three cases.

This checks metadata consistency only. Neither a matching owner locator nor a
True boolean independently attests source, privacy, world isolation, or request.
Never reads R50, databases, diagnostic archives or model input bodies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

from experiments.r58_quality import r60_p3_stage_pair_probe as p3
from experiments.r58_quality import r60_p4_owner_locator_probe as p4

SCHEMA = "storyforge_r60_p5_owner_field_audit_safe_v1"
REQUIRED_TRUE = (
    "rights_attested", "source_version_verified", "context_is_coherent",
    "context_no_future_leakage_reviewed", "privacy_checked",
    "world_component_reviewed", "known_protected_metadata_checked",
    "other_known_reserved_metadata_checked", "final_heldout_metadata_checked",
    "reviewers_blinded_and_independent_attested", "owner_quality_approved",
)
REQUIRED_FALSE = (
    "known_protected_overlap", "final_heldout_overlap",
    "protected_test_body_accessed",
)
REQ_FIELD_NAMES = (
    "source_version_sha256", "world_graph_sha256", "world_component_id",
    "split", "reviewer_a_evidence_ref", "reviewer_b_evidence_ref",
    "owner_supplemental_severe_evidence_ref",
)
SENT_FIELDS = (
    "request_attempt_id", "request_id", "relay_request_id",
    "provider_request_id", "sent_payload_sha256", "exact_sent_payload_sha256",
)
SEVERE_FIELDS = (
    "serious_player_agency", "hard_fact_or_ban", "safety_exclusion",
)


def inspect(p4_rows: list[dict], loader) -> tuple[list[dict], dict]:
    if len(p4_rows) != 3 or len({r.get("case_id") for r in p4_rows}) != 3:
        raise p3.Hold("P4_THREE_UNIQUE_CASES_REQUIRED")
    missing = Counter()
    details = []
    unique_refs = set()
    for item in p4_rows:
        cid = item.get("case_id")
        target = item.get("target_sha256")
        refs = item.get("owner_locator_matches")
        if not isinstance(cid, str) or not isinstance(target, str) or not isinstance(refs, list):
            raise p3.Hold("P4_ITEM_INVALID")
        if not refs:
            raise p3.Hold("P4_OWNER_LOCATOR_ABSENT")
        observations = []
        distinct_file_hashes = set()
        deduped = set()
        for ref in refs:
            path = Path(ref["private_owner_file_path"])
            if not p3.contained(path, p3.ALLOWED_BASE):
                raise p3.Hold("P4_OWNER_PATH_SCOPE")
            if not any(path.is_relative_to(p3.ALLOWED_BASE / sub)
                       for sub in ("r58/private/quality-v1", "r59/private/quality-v1")):
                raise p3.Hold("P4_OWNER_OUTSIDE_INVENTORY_ROOTS")
            raw = loader(path, p4.MAX_OWNER_BYTES)
            fingerprint = hashlib.sha256(raw).hexdigest()
            if fingerprint != ref.get("owner_file_sha256"):
                raise p3.Hold("P4_OWNER_PIN_CHANGED")
            unique_refs.add(fingerprint)
            distinct_file_hashes.add(fingerprint)
            if fingerprint in deduped:
                continue
            deduped.add(fingerprint)
            rows = p4.parse_owner(raw)
            if not rows:
                raise p3.Hold("P4_OWNER_ROWS_NO_LONGER_PARSEABLE")
            for row in rows:
                if row.get("case_id") != cid or row.get("target_sha256") != target:
                    continue
                evidence = row.get("evidence")
                evidence = evidence if isinstance(evidence, dict) else {}
                true_fields = [k for k in REQUIRED_TRUE if evidence.get(k) is True]
                false_fields = [k for k in REQUIRED_FALSE if evidence.get(k) is False]
                attrs = [k for k in REQ_FIELD_NAMES
                         if isinstance(row.get(k), str) and bool(row[k].strip())]
                request_hints = [k for k in SENT_FIELDS
                                 if isinstance(row.get(k), str) and bool(row[k].strip())]
                flags = row.get("owner_supplemental_severe_flags")
                flags_valid = (isinstance(flags, dict)
                               and set(flags) == set(SEVERE_FIELDS)
                               and all(type(flags[k]) is bool for k in SEVERE_FIELDS))
                observations.append({
                    "owner_snapshot_sha256": fingerprint,
                    "true_declarations_present": true_fields,
                    "false_declarations_present": false_fields,
                    "metadata_fields_present": attrs,
                    "request_hint_field_names_present": request_hints,
                    "severe_flags_structurally_valid": flags_valid,
                    "severe_flag_any_true": any(flags.values()) if flags_valid else None,
                    "source_independently_verified": False,
                    "owner_approval_independently_verified": False,
                    "request_payload_independently_verified": False,
                })
        if not observations:
            raise p3.Hold("OWNER_ROWS_CHANGED_SINCE_P4")
        for key in REQUIRED_TRUE:
            if not any(key in x["true_declarations_present"] for x in observations):
                missing["OWNER_DECLARATION_MISSING_" + key.upper()] += 1
        for key in REQUIRED_FALSE:
            if not any(key in x["false_declarations_present"] for x in observations):
                missing["OWNER_NEGATIVE_DECLARATION_MISSING_" + key.upper()] += 1
        for key in REQ_FIELD_NAMES:
            if not any(key in x["metadata_fields_present"] for x in observations):
                missing["OWNER_METADATA_MISSING_" + key.upper()] += 1
        if not any(x["severe_flags_structurally_valid"] for x in observations):
            missing["OWNER_SEVERE_FLAGS_NOT_PRESENT"] += 1
        if not any(x["request_hint_field_names_present"] for x in observations):
            missing["NO_REQUEST_HINT_FIELDS"] += 1
        if any(x["severe_flag_any_true"] is True for x in observations):
            missing["SEVERE_FLAG_TRUE_REVIEW_REQUIRED"] += 1
        details.append({
            "case_id": cid,
            "target_sha256": target,
            "distinct_owner_file_hashes": sorted(distinct_file_hashes),
            "observations": observations,
            "owner_attestation_independently_verified": False,
            "sent_model_input_independently_verified": False,
            "protected_world_exposure_independently_verified": False,
            "quality_v1_admitted": False,
        })
    safe = {
        "schema": SCHEMA,
        "status": "P5_OWNER_FIELDS_AUDITED__EVIDENCE_AUTHENTICITY_HOLD",
        "candidate_cases_checked": len(details),
        "unique_owner_file_content_hashes_across_cases": len(unique_refs),
        "snapshot_observations": sum(len(r["observations"]) for r in details),
        "cases_with_any_request_hint": sum(
            any(o["request_hint_field_names_present"] for o in r["observations"])
            for r in details
        ),
        "missing_declaration_or_metadata_counts": dict(sorted(missing.items())),
        "owner_complete_independently_verified": 0,
        "exact_sent_payload_verified_count": 0,
        "request_attempt_linkage_verified_count": 0,
        "protected_world_exposure_verified_count": 0,
        "input_evidence_class_counts": {"A": None, "B": None, "C": None,
                                        "D": None, "UNKNOWN_NOT_REVIEWED": 192},
        "binder_bound": 0, "quality_v1_admitted": 0,
        "dataset_frozen": False, "cpu_tokenizer_collator_pass": False,
        "training_authorized": False, "gpu_started": False,
        "database_modified": False, "r50_accessed": False,
        "private_values_emitted": False,
    }
    return details, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p4-owner-locators", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        p4_rows = p3.parse_lines(p3.private_bytes(args.p4_owner_locators, 5_000_000), 3)
        out = args.output_dir
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()
                or stat.S_IMODE(out.parent.stat().st_mode) != 0o700
                or not out.is_relative_to(p3.ALLOWED_BASE / "r59/private")):
            raise p3.Hold("PRIVATE_OUTPUT_DIR_INVALID")
        private, safe = inspect(p4_rows, p3.private_bytes)
        out.mkdir(mode=0o700)
        for name, payload, lines in (
            ("R60_P5_OWNER_FIELD_AUDIT_PRIVATE.jsonl", private, True),
            ("R60_P5_SAFE.json", safe, False),
        ):
            fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                if lines:
                    for value in payload:
                        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
                else:
                    json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
                    stream.write("\n")
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (p3.Hold, OSError, ValueError, TypeError, KeyError, UnicodeError):
        print(json.dumps({
            "schema": SCHEMA, "status": "P5_HOLD",
            "reason_code": "PRIVATE_INPUT_OR_VALIDATION_FAILED",
            "quality_v1_admitted": 0, "gpu_started": False,
            "r50_accessed": False, "database_modified": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
