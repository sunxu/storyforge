"""Read-only Pilot5 v2 receipt/source integrity audit. No network or private output.

Usage: python r60_pilot5_v2_safe_audit.py --seed FILE --quality-dir DIR
Never logs private prose, case IDs, hashes, endpoint, model response or paths.
This is an evidence-integrity audit, NOT a quality adjudicator or trainer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

RECEIPT_TEMPLATE = "R60_QUALITY_CASE_{:04d}_PRIVATE.json"
EXPECTED_CASES = 5
FIELDS = ("case_key", "history_messages_sha256", "assistant_target_sha256")


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def audit(seed_file: Path, quality_dir: Path) -> dict:
    summary = {
        "schema": "storyforge_r60_pilot5_v2_safe_audit_v1",
        "status": "PILOT5_V2_EVIDENCE_HOLD",
        "cases_checked": 0,
        "all_source_binding_verified": False,
        "attempt_hold_counts": {},
        "reviewer_decisions": {"PASS": 0, "HOLD": 0, "REJECT": 0},
        "quality_decisions": {"PASS": 0, "HOLD": 0, "REJECT": 0},
        "database_modified": False,
        "gpu_started": False,
        "model_requests": 0,
        "train_admitted": 0,
        "private_values_emitted": False,
    }
    try:
        if seed_file.is_symlink() or quality_dir.is_symlink():
            raise ValueError("INPUT_SYMLINK_HOLD")
        if not seed_file.is_file() or not quality_dir.is_dir():
            raise ValueError("INPUT_MISSING_HOLD")
        with seed_file.open(encoding="utf-8") as stream:
            cases = [json.loads(line) for line in stream if line.strip()]
        if len(cases) != 6:
            raise ValueError("SEED_SIX_REQUIRED")
        holds = {}
        for index in range(1, EXPECTED_CASES + 1):
            case = cases[index - 1]
            receipt_file = quality_dir / RECEIPT_TEMPLATE.format(index)
            if receipt_file.is_symlink() or not receipt_file.is_file():
                raise ValueError("CASE_RECEIPT_MISSING_HOLD")
            receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            if (
                not isinstance(case, dict)
                or not isinstance(receipt, dict)
                or receipt.get("position") != index
                or any(receipt.get(key) != case.get(key) for key in FIELDS)
                or case.get("history_messages_sha256") != digest(case["history_messages"])
                or case.get("assistant_target_sha256") !=
                hashlib.sha256(case["target_text"].encode("utf-8")).hexdigest()
            ):
                raise ValueError("SOURCE_BINDING_HOLD")
            signed = {key: value for key, value in receipt.items()
                      if key != "receipt_sha256"}
            if digest(signed) != receipt.get("receipt_sha256"):
                raise ValueError("RECEIPT_DIGEST_HOLD")
            reviews = receipt.get("reviews")
            attempts = receipt.get("attempt_holds")
            if (
                not isinstance(reviews, list)
                or not isinstance(attempts, list)
                or len(reviews) + len(attempts) != 2
                or any(not isinstance(x, dict) for x in reviews)
                or any(not isinstance(x, str) for x in attempts)
                or receipt.get("quality_decision") not in summary["quality_decisions"]
            ):
                raise ValueError("RECEIPT_STRUCTURE_HOLD")
            summary["quality_decisions"][receipt["quality_decision"]] += 1
            for review in reviews:
                decision = review.get("decision")
                if decision not in summary["reviewer_decisions"]:
                    raise ValueError("REVIEWER_DECISION_HOLD")
                summary["reviewer_decisions"][decision] += 1
            for code in attempts:
                # Fail closed: no uncontrolled model or private text in stdout.
                if code not in (
                    "MODEL_JSON_INVALID", "QUALITY_FLOOR_DECISION_INCONSISTENT",
                    "MODEL_TRANSPORT_HOLD", "MODEL_PROTOCOL_HOLD",
                    "MODEL_REPLY_OVERSIZE", "SEVERE_FLAG_DECISION_INCONSISTENT"
                ) and not (
                    code.startswith("MODEL_HTTP_") and code.endswith("_HOLD")
                    and code[len("MODEL_HTTP_"):-len("_HOLD")].isdigit()
                ):
                    raise ValueError("UNKNOWN_ATTEMPT_CODE_HOLD")
                holds[code] = holds.get(code, 0) + 1
            summary["cases_checked"] += 1
        summary["attempt_hold_counts"] = dict(sorted(holds.items()))
        summary["all_source_binding_verified"] = True
        summary["status"] = "PILOT5_V2_EVIDENCE_INTEGRITY_PASS__NO_PROMOTION"
    except (OSError, ValueError, KeyError, TypeError, IndexError, UnicodeError):
        # Do not expose provider output or private file data in exception text.
        summary["status"] = "PILOT5_V2_EVIDENCE_HOLD"
        summary["all_source_binding_verified"] = False
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--quality-dir", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.seed, args.quality_dir)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["all_source_binding_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())
