"""Read-only private priority queue for Reviewer A case-level evidence gaps.

Only B HOLD/REJECT intersected with A aggregate-only PASS are selected.
No inferred Reviewer A verdict is represented as an actual case-level review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .arbitration_queue import write_private_queue
from .manifest import ManifestError, load_events, validate_manifest
from .reconcile import CANONICAL_REVIEWER_B_SHA256

HEX64 = re.compile(r"^[0-9a-f]{64}$")
A_STATE = "PASS_INFERRED_FROM_V6_AGGREGATE_PENDING_CASE_LEVEL_EVIDENCE"
EXPECTED_B = {"HOLD": 6, "REJECT": 1}


def _read_private(path: Path) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file():
        raise ManifestError("A_GAP_INPUT_MISSING_OR_SYMLINK")
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ManifestError("A_GAP_INPUT_INVALID")
    return data, hashlib.sha256(raw).hexdigest()


def build_a_gap_priority(normalized: dict, events: list[dict]) -> tuple[dict, list[dict]]:
    validate_manifest(events)
    if (normalized.get("schema") != "r58_gold192_reviewer_a_results_normalized_private_v1"
            or normalized.get("status") != "NORMALIZED_192_IDENTITIES__CASE_LEVEL_GAPS_EXPLICIT"
            or normalized.get("reviewer") != "A"
            or normalized.get("quality_v1_admitted") != 0
            or normalized.get("case_level_evidence_counts") != {
                "case_level_scored_pass": 79, "pass_aggregate_only_pending": 109,
                "reject_case_level_unscored": 3, "reject_group_only_unscored": 1,
            }):
        raise ManifestError("A_GAP_NORMALIZED_SOURCE_INVALID")
    records = normalized.get("records")
    if not isinstance(records, list) or len(records) != 192:
        raise ManifestError("A_GAP_192_SCOPE_INVALID")
    by_sha: dict[str, dict] = {}
    aggregate_count = 0
    for r in records:
        if not isinstance(r, dict):
            raise ManifestError("A_GAP_ROW_INVALID")
        digest, case_id = r.get("target_sha256"), r.get("case_id")
        if (not isinstance(digest, str) or not HEX64.fullmatch(digest)
                or digest in by_sha or not isinstance(case_id, str) or not case_id):
            raise ManifestError("A_GAP_IDENTITY_DUPLICATE_OR_INVALID")
        by_sha[digest] = r
        if r.get("review_evidence_state") == A_STATE:
            if (r.get("v6_aggregate_complement_only") is not True
                    or r.get("case_level_evidence_present") is not False
                    or r.get("scores_1_to_5") is not None
                    or r.get("decision_for_strict_ab_pairing") is not None
                    or r.get("reported_final_decision") != "PASS_ONLY"):
                raise ManifestError("A_GAP_AGGREGATE_ONLY_STATE_INVALID")
            aggregate_count += 1
    if aggregate_count != 109:
        raise ManifestError("A_GAP_AGGREGATE_COUNT_INVALID")
    canonical_b: dict[str, dict] = {}
    existing_a, historical_rejects, existing_ai = set(), set(), set()
    for ev in events:
        if ev.get("batch_id") != "gold192":
            continue
        p = ev["payload"]
        digest = p.get("target_sha256")
        kind = ev["event_type"]
        if (kind == "BLIND_REVIEW" and p.get("reviewer_role") == "REVIEWER_B"
                and p.get("reviewer_source_sha256") == CANONICAL_REVIEWER_B_SHA256):
            if digest in canonical_b:
                raise ManifestError("A_GAP_DUPLICATE_CANONICAL_B")
            canonical_b[digest] = p
        elif kind in {"INCREMENTAL_REVIEW", "BLIND_REVIEW"} and (
                p.get("reviewer_role") == "REVIEWER_A"):
            existing_a.add(digest)
        elif kind == "HISTORICAL_REJECT_EVIDENCE":
            historical_rejects.add(digest)
        elif kind == "AI_ARBITRATION":
            existing_ai.add(digest)
    if len(canonical_b) != 192 or set(canonical_b) != set(by_sha):
        raise ManifestError("A_GAP_CANONICAL_B_SET_MISMATCH")
    queue, counts = [], Counter()
    for digest, b in sorted(canonical_b.items()):
        a = by_sha[digest]
        if a["review_evidence_state"] != A_STATE:
            continue
        decision = b.get("decision")
        if decision not in {"PASS", "HOLD", "REJECT"}:
            raise ManifestError("A_GAP_CANONICAL_B_DECISION_INVALID")
        if decision == "PASS":
            continue
        if digest in existing_a or digest in historical_rejects or digest in existing_ai:
            raise ManifestError("A_GAP_CONFLICTING_PREEXISTING_EVIDENCE")
        if not isinstance(b.get("evidence_summary"), str) or not b["evidence_summary"]:
            raise ManifestError("A_GAP_B_REASON_MISSING")
        counts[decision] += 1
        queue.append({
            "case_id": a["case_id"], "target_sha256": digest,
            "reviewer_a_reported_final_decision": "PASS_ONLY",
            "reviewer_a_evidence_status": A_STATE,
            "reviewer_a_actual_case_level_decision": None,
            "reviewer_a_scores_1_to_5": None,
            "reviewer_b_blind_case_id": b.get("blind_case_id"),
            "reviewer_b_decision": decision,
            "reviewer_b_scores": b.get("scores"),
            "reviewer_b_evidence_summary": b["evidence_summary"],
            "reviewer_b_severe_flags": b.get("severe_flags", []),
            "priority": "P0" if decision == "REJECT" else "P1",
            "task": "LOCATE_EXISTING_A_CASE_LEVEL_EVIDENCE_BEFORE_ANY_NEW_REVIEW",
            "status": "PENDING_A_EVIDENCE_RECOVERY",
            "quality_v1_admitted": False,
        })
    if len(queue) != 7 or dict(counts) != EXPECTED_B:
        raise ManifestError("A_GAP_PRIORITY_COUNTS_INVALID")
    safe = {
        "schema": "r58_gold192_reviewer_a_gap_priority_safe_v1",
        "status": "A_GAP_PRIORITY_7_PRIVATE_QUEUE_READY__NO_REVIEW",
        "reviewer_a_aggregate_only_total": 109,
        "priority_case_count": 7,
        "priority_reviewer_b_decisions": dict(sorted(counts.items())),
        "other_aggregate_only_b_pass": 102,
        "existing_a_case_level_reviews_created": 0,
        "case_identity_scope_verified": False,
        "quality_v1_admitted": 0, "training_authorized": False,
        "gpu_started": False, "r50_accessed": False, "private_values_emitted": False,
    }
    return safe, queue


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare 7 private Reviewer A evidence gaps")
    parser.add_argument("--reviewer-a", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        source, source_sha = _read_private(args.reviewer_a)
        safe, cases = build_a_gap_priority(source, load_events(args.manifest))
        for row in cases:
            row["reviewer_a_source_sha256"] = source_sha
        write_private_queue(args.output, cases, args.repo_root)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ManifestError, OSError, ValueError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, ManifestError) else "A_GAP_INPUT_OR_IO_ERROR"
        print(json.dumps({"schema": "r58_gold192_reviewer_a_gap_priority_safe_v1",
                          "status": "HOLD", "reason_code": reason,
                          "quality_v1_admitted": 0, "training_authorized": False,
                          "r50_accessed": False, "private_values_emitted": False},
                         sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
