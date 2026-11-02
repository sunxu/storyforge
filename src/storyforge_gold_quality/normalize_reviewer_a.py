"""Normalize Reviewer A evidence without fabricating case-level reviews or scores."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

from .manifest import ManifestError
from .recover_reviewer_a import EXPECTED_REJECT_IDS, FILES, _load_pinned

FIELDS = {"chinese_prose", "character_consistency", "npc_initiative",
          "player_agency", "narrative_continuity", "rule_fidelity"}
B_SHA = "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"
COUNTS = {"case_level_scored_pass": 79, "reject_case_level_unscored": 3,
          "reject_group_only_unscored": 1, "pass_aggregate_only_pending": 109}


def normalize(sources: dict, expected_b_targets: set[str]) -> tuple[dict, dict]:
    initial, remaining = sources["initial"].get("cases"), sources["remaining"].get("cases")
    mappings = sources["mapping"].get("mapping")
    groups = sources["supplement"].get("reject_groups")
    aggregate = sources["safe"].get("ai_review_counts")
    if (not isinstance(initial, list) or len(initial) != 31
            or not isinstance(remaining, list) or len(remaining) != 51
            or not isinstance(mappings, list) or len(mappings) != 192
            or not isinstance(groups, list) or len(groups) != 4
            or aggregate != {"semantic_pass_only": 188, "hold": 0, "reject": 4,
                             "semantic_review_pending": 0}):
        raise ManifestError("REVIEWER_A_NORMALIZATION_SCOPE_INVALID")
    rejected = [cid for group in groups for cid in group.get("case_ids", [])]
    if len(rejected) != 4 or set(rejected) != EXPECTED_REJECT_IDS:
        raise ManifestError("REVIEWER_A_FINAL_REJECT_LIST_INVALID")
    case_rows = {}
    for record in initial + remaining:
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in case_rows:
            raise ManifestError("REVIEWER_A_CASE_LEVEL_DUPLICATE_OR_INVALID")
        case_rows[case_id] = record
    if len(case_rows) != 82:
        raise ManifestError("REVIEWER_A_CASE_LEVEL_COUNT_INVALID")
    mapping, targets = {}, set()
    for item in mappings:
        case_id, digest = item.get("original_case_id"), item.get("target_sha256")
        if (not isinstance(case_id, str) or not case_id or case_id in mapping
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or digest in targets):
            raise ManifestError("REVIEWER_A_CASE_TARGET_MAPPING_INVALID")
        mapping[case_id] = digest
        targets.add(digest)
    if (len(mapping) != 192 or targets != expected_b_targets
            or not set(case_rows).issubset(mapping)
            or not EXPECTED_REJECT_IDS.issubset(mapping)):
        raise ManifestError("REVIEWER_A_FROZEN_TARGET_SET_MISMATCH")
    first_ids = {row["case_id"] for row in initial}
    normalized, counts = [], Counter()
    for case_id, digest in sorted(mapping.items()):
        entry = case_rows.get(case_id)
        row = {
            "case_id": case_id, "target_sha256": digest, "reviewer": "A",
            "original_cohort": entry.get("cohort") if entry else None,
            "reported_final_decision": "REJECT" if case_id in EXPECTED_REJECT_IDS else "PASS_ONLY",
            "decision_for_strict_ab_pairing": None,
            "scores_1_to_5": None,
            "case_level_evidence_present": bool(entry),
            "score_state": "MISSING", "evidence_note": None,
            "case_level_evidence_source": None, "review_evidence_state": None,
            "v6_aggregate_complement_only": False, "quality_v1_admitted": False,
        }
        if entry is not None:
            row["evidence_note"] = entry.get("note")
            row["case_level_evidence_source"] = (
                "INITIAL_31" if case_id in first_ids else "REMAINING_51")
            if case_id in EXPECTED_REJECT_IDS:
                if (entry.get("decision") != "REJECT"
                        or entry.get("scores_1_to_5") is not None):
                    raise ManifestError("REVIEWER_A_REJECT_SCORES_OR_DECISION_INVALID")
                row["review_evidence_state"] = "REJECT_CASE_LEVEL_WITHOUT_SCORES"
                counts["reject_case_level_unscored"] += 1
            else:
                scores = entry.get("scores_1_to_5")
                if (entry.get("decision") != "AI_SEMANTIC_PASS_ONLY"
                        or not isinstance(scores, dict) or set(scores) != FIELDS
                        or any(type(v) is not int or not 1 <= v <= 5
                               for v in scores.values())):
                    raise ManifestError("REVIEWER_A_SCORED_PASS_INVALID")
                row.update({"scores_1_to_5": scores,
                            "decision_for_strict_ab_pairing": "PASS_ONLY",
                            "score_state": "COMPLETE",
                            "review_evidence_state": "CASE_LEVEL_SCORED_PASS"})
                counts["case_level_scored_pass"] += 1
        elif case_id in EXPECTED_REJECT_IDS:
            row.update({"review_evidence_state": "REJECT_FINAL_V6_GROUP_ONLY",
                        "case_level_evidence_source": "FINAL_SUPPLEMENT_V6_REJECT_GROUP"})
            counts["reject_group_only_unscored"] += 1
        else:
            row.update({
                "review_evidence_state":
                    "PASS_INFERRED_FROM_V6_AGGREGATE_PENDING_CASE_LEVEL_EVIDENCE",
                "v6_aggregate_complement_only": True,
            })
            counts["pass_aggregate_only_pending"] += 1
        normalized.append(row)
    if dict(counts) != COUNTS:
        raise ManifestError("REVIEWER_A_NORMALIZED_COUNTS_INVALID")
    return {
        "schema": "r58_gold192_reviewer_a_results_normalized_private_v1",
        "status": "NORMALIZED_192_IDENTITIES__CASE_LEVEL_GAPS_EXPLICIT",
        "reviewer": "A", "source_v6_counts": aggregate,
        "case_level_evidence_counts": dict(sorted(counts.items())),
        "training_authorized": False, "quality_v1_admitted": 0,
        "records": normalized,
    }, counts


def _private_write(path: Path, raw: bytes, repo_root: Path) -> None:
    target = path.absolute()
    if target.is_symlink() or target.exists():
        raise ManifestError("REVIEWER_A_OUTPUT_ALREADY_EXISTS")
    parent = target.parent
    repo = repo_root.resolve(strict=True)
    if not parent.is_dir() or parent.is_symlink() or any(
            p.is_symlink() for p in parent.parents):
        raise ManifestError("REVIEWER_A_OUTPUT_PARENT_INVALID")
    resolved = parent.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise ManifestError("REVIEWER_A_OUTPUT_INSIDE_REPOSITORY")
    if resolved.stat().st_mode & 0o077:
        raise ManifestError("REVIEWER_A_OUTPUT_PARENT_PERMISSIONS_TOO_OPEN")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


def build_reviewer_a_results(args) -> dict:
    if args.bundle_root.is_symlink():
        raise ManifestError("REVIEWER_A_BUNDLE_SYMLINK")
    root = args.bundle_root.resolve(strict=True)
    sources = {key: _load_pinned(root, *spec) for key, spec in FILES.items()}
    if args.reviewer_b.is_symlink() or not args.reviewer_b.is_file():
        raise ManifestError("REVIEWER_A_B_SOURCE_INVALID")
    b_bytes = args.reviewer_b.read_bytes()
    if hashlib.sha256(b_bytes).hexdigest() != B_SHA:
        raise ManifestError("REVIEWER_A_B_SOURCE_PIN_MISMATCH")
    b = json.loads(b_bytes)
    cases = b.get("cases")
    if not isinstance(cases, list) or len(cases) != 192:
        raise ManifestError("REVIEWER_A_B_SCOPE_INVALID")
    hashes = [record.get("target_sha256") for record in cases]
    if len(set(hashes)) != 192:
        raise ManifestError("REVIEWER_A_B_DUPLICATE_TARGET")
    report, _counts = normalize(sources, set(hashes))
    private_bytes = (json.dumps(report, ensure_ascii=False, indent=2,
                                sort_keys=True) + "\n").encode()
    safe = {
        "schema": "r58_gold192_reviewer_a_results_normalized_safe_v1",
        "status": "REVIEWER_A_192_IDENTITY_LEDGER_CREATED__EVIDENCE_GAPS_REMAIN",
        "reviewer_a_record_count": 192,
        "case_level_scored_pass": 79,
        "case_level_unscored_reject": 3,
        "group_only_unscored_reject": 1,
        "aggregate_only_pass_pending_case_evidence": 109,
        "strict_ab_pairing_eligible_from_a": 79,
        "private_report_sha256": hashlib.sha256(private_bytes).hexdigest(),
        "private_values_emitted": False, "quality_v1_admitted": 0,
        "training_authorized": False, "gpu_started": False, "r50_accessed": False,
    }
    if any(p.exists() or p.is_symlink() for p in (args.output, args.safe_output)):
        raise ManifestError("REVIEWER_A_OUTPUT_ALREADY_EXISTS")
    _private_write(args.output, private_bytes, args.repo_root)
    _private_write(args.safe_output, (json.dumps(safe, sort_keys=True, indent=2) +
                                    "\n").encode(), args.repo_root)
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize 192 pinned Reviewer A identities")
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--safe-output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build_reviewer_a_results(args), ensure_ascii=False,
                         sort_keys=True, indent=2))
        return 0
    except (ManifestError, OSError, ValueError, TypeError) as exc:
        code = str(exc) if isinstance(exc, ManifestError) else "REVIEWER_A_INPUT_OR_IO_ERROR"
        print(json.dumps({"schema": "r58_gold192_reviewer_a_results_normalized_safe_v1",
                          "status": "HOLD", "reason_code": code,
                          "quality_v1_admitted": 0, "training_authorized": False,
                          "r50_accessed": False, "private_values_emitted": False},
                         sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
