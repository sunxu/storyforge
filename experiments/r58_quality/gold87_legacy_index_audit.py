"""Read-only Gold87 frozen index audit. Index attestations are not reviewer evidence."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from legacy_gold_target_reuse import index_rows

EXPECTED = 87
BASE = Path("evaluations/v0.2/gold-quality-87/gold_87_index.csv")
COLUMNS = (
    "story_id", "sample_target_sha256", "sample_id", "review_A", "review_B",
    "review_C", "quality_decision", "training_admission", "split",
    "A_citation_status", "age_and_consent_status",
)
CITATIONS = {
    "ORIGINAL_EXACT_OR_VALID_COMPRESSED_QUOTE",
    "STRICT_CONTIGUOUS_PASS",
    "SEGMENT_MATCH_ONLY__REQUOTE_RECOMMENDED",
}
AGES = {
    "NOT_REVALIDATED_AT_QUALITY_SELECTION",
    "TARGET_TIME_AGE_NOT_VERIFIED",
}


def read_frozen_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        first = source.readline()
        if first == "<PARSED TEXT FOR SHEET: 1 / 1 TABS\n":
            if source.readline() != "TAB NAME: gold_87_index.csv>\n":
                raise ValueError("GOLD87_ENVELOPE_INVALID")
        else:
            source.seek(0)
        reader = csv.DictReader(source)
        if not set(COLUMNS).issubset(reader.fieldnames or []):
            raise ValueError("GOLD87_COLUMNS_INVALID")
        rows = list(reader)
    if len(rows) != EXPECTED or any(None in row for row in rows):
        raise ValueError("GOLD87_ROW_COUNT_OR_SHAPE_INVALID")
    return rows


def inspect(path):
    # Existing identity checker independently verifies 87 world+target identities,
    # digest format, and duplicate candidate IDs.
    identities = index_rows(path, EXPECTED)
    rows = read_frozen_rows(path)
    if len(identities) != EXPECTED:
        raise ValueError("GOLD87_IDENTITY_INVALID")
    if any(
        row["review_A"] != "ACCEPT"
        or row["review_B"] != "ACCEPT"
        or row["review_C"] not in {"ACCEPT", "NOT_REVIEWED"}
        or row["quality_decision"] != "GOLD_QUALITY_ACCEPTED_BY_OWNER"
        or row["training_admission"] != "PENDING_NOT_APPROVED"
        or row["split"] != "UNASSIGNED"
        or row["A_citation_status"] not in CITATIONS
        or row["age_and_consent_status"] not in AGES
        for row in rows
    ):
        raise ValueError("GOLD87_INDEX_STATUS_INVALID")
    cite = Counter(row["A_citation_status"] for row in rows)
    ages = Counter(row["age_and_consent_status"] for row in rows)
    reviews_c = Counter(row["review_C"] for row in rows)
    return {
        "schema": "r58_gold87_legacy_index_audit_safe_v1",
        "status": "GOLD87_INDEX_ATTESTATION_ONLY__REVIEW_EVIDENCE_UNBOUND",
        "frozen_rows_checked": EXPECTED,
        "target_world_identity_present": EXPECTED,
        "historical_review_a_accept_indexed": EXPECTED,
        "historical_review_b_accept_indexed": EXPECTED,
        "historical_review_c_accept_indexed": reviews_c["ACCEPT"],
        "historical_review_c_not_reviewed": reviews_c["NOT_REVIEWED"],
        "owner_quality_selected_indexed": EXPECTED,
        "citation_status_counts": dict(sorted(cite.items())),
        "age_consent_status_counts": dict(sorted(ages.items())),
        "historic_reviewer_text_and_scores_verified": False,
        "historic_reviewer_independence_proven": False,
        "historical_full_context_equivalence_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_read": False,
        "private_values_emitted": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    args = p.parse_args()
    try:
        root = args.repo_root.resolve()
        path = root / BASE
        if not path.is_file() or path.is_symlink() or path.resolve() != root / BASE:
            raise ValueError("GOLD87_PATH_INVALID")
        result = inspect(path)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, csv.Error) as error:
        allowed = {
            "GOLD87_ENVELOPE_INVALID", "GOLD87_COLUMNS_INVALID",
            "GOLD87_ROW_COUNT_OR_SHAPE_INVALID", "GOLD87_IDENTITY_INVALID",
            "GOLD87_INDEX_STATUS_INVALID", "GOLD87_PATH_INVALID",
        }
        reason = str(error) if isinstance(error, ValueError) and str(error) in allowed else "GOLD87_INDEX_INPUT_INVALID"
        print(json.dumps({
            "schema": "r58_gold87_legacy_index_audit_safe_v1",
            "status": "GOLD87_INDEX_AUDIT_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
