"""Seed Gold192 model-input evidence slots without claiming any Case is proven."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

EXPECTED_TOTAL = 192
SAFE_SCHEMA = "r60_model_input_evidence_seed_safe_v1"


def _read_private(path: Path) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("PRIVATE_INPUT_PATH_INVALID")
    if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise ValueError("PRIVATE_INPUT_PARENT_MODE_INVALID")
    st = path.stat()
    if stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or st.st_size > 32_000_000:
        raise ValueError("PRIVATE_INPUT_FILE_MODE_INVALID")
    return path.read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seed(locator_raw: bytes, source_safe_raw: bytes) -> tuple[bytes, dict]:
    try:
        safe = json.loads(source_safe_raw)
        locators = [json.loads(line) for line in locator_raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise ValueError("INPUT_PARSE_INVALID") from None
    artifact = safe.get("artifacts", {}).get("R60_SOURCE_LOCATORS_192.jsonl", {})
    if (
        safe.get("schema") != "r60_gold192_supabase_extract_v3_safe_v1"
        or safe.get("status") != "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED"
        or safe.get("gold192") != EXPECTED_TOTAL
        or safe.get("quality_v1_admitted") != 0
        or safe.get("training_authorized") is not False
        or safe.get("gpu_started") is not False
        or safe.get("database_modified") is not False
        or safe.get("private_values_emitted") is not False
        or artifact.get("records") != EXPECTED_TOTAL
        or artifact.get("sha256") != _sha(locator_raw)
        or len(locators) != EXPECTED_TOTAL
    ):
        raise ValueError("SOURCE_PIN_OR_COUNT_INVALID")
    cases = []
    for locator in locators:
        case_id = locator.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("CASE_ID_INVALID")
        cases.append(case_id)
    if len(set(cases)) != EXPECTED_TOTAL:
        raise ValueError("CASE_IDS_NOT_UNIQUE")
    rows = [
        {
            "case_id": row["case_id"],
            "source_status": row.get("source_status"),
            "input_evidence_class": "UNKNOWN_NOT_REVIEWED",
            "actual_sent_request_verified": False,
            "provider_response_link_verified": False,
            "request_attempt_link_verified": False,
            "reconstruction_verified": False,
            "target_provenance_verified": False,
            "evidence_source_refs": [],
            "reason_codes": ["EVIDENCE_REVIEW_NOT_STARTED"],
        }
        for row in locators
    ]
    private_jsonl = ("\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                                 for x in rows) + "\n").encode()
    source_counts = Counter(str(x.get("source_status")) for x in locators)
    public = {
        "schema": SAFE_SCHEMA,
        "status": "EVIDENCE_SLOTS_SEEDED_NOT_REVIEWED",
        "gold192_total": EXPECTED_TOTAL,
        "input_evidence_class_counts": {"A": None, "B": None, "C": None, "D": None,
                                        "UNKNOWN_NOT_REVIEWED": EXPECTED_TOTAL},
        "source_status_counts": dict(sorted(source_counts.items())),
        "source_locator_sha256": _sha(locator_raw),
        "private_slots_sha256": _sha(private_jsonl),
        "request_attempt_linkage_verified_count": 0,
        "exact_sent_payload_verified_count": 0,
        "evidence_review_started": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return private_jsonl, public


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-locators", type=Path, required=True)
    p.add_argument("--source-safe", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.source_locators.parent != args.source_safe.parent:
            raise ValueError("SOURCE_RUN_DIR_MISMATCH")
        if not args.output_dir.is_absolute() or args.output_dir.exists():
            raise ValueError("OUTPUT_DIR_INVALID")
        if stat.S_IMODE(args.output_dir.parent.stat().st_mode) != 0o700:
            raise ValueError("OUTPUT_PARENT_MODE_INVALID")
        private, public = seed(_read_private(args.source_locators),
                               _read_private(args.source_safe))
        args.output_dir.mkdir(mode=0o700)
        target = args.output_dir / "R60_MODEL_INPUT_EVIDENCE_SLOTS_PRIVATE.jsonl"
        receipt = args.output_dir / "R60_MODEL_INPUT_EVIDENCE_SLOTS_SAFE.json"
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(private)
        fd = os.open(receipt, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write((json.dumps(public, sort_keys=True, indent=2) + "\n").encode())
        print(json.dumps(public, ensure_ascii=False, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(f"MODEL_INPUT_EVIDENCE_SEED_HOLD: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
