"""Recover SHA-pinned Reviewer A evidence without inventing missing scores.

Owner-only inputs must stay outside the Git worktree. This command imports
79 case-level records with actual six-dimensional scores, plus four separate
unscored historical REJECT evidence events. No scores are synthesized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .cli import SCORES, now
from .manifest import ManifestError, append_events, load_events, make_event

FILES = {
    "initial": ("private/reviewer_a/INITIAL_31_CASES_OWNER_ONLY.json",
                "734ae5ccfc5ce06ff8c5fec3a98798273c1b75b2496289173bf212203de3deaf"),
    "remaining": ("private/reviewer_a/REMAINING_51_CASES_OWNER_ONLY.json",
                  "7e97790bb3d04c92441d10c6ffb7ceb67fe38a037242fb059e8085b1be0b1831"),
    "supplement": ("private/reviewer_a/FINAL_SUPPLEMENT_V6_OWNER_ONLY.json",
                   "30ceb8ec6de9df045da783780e50efa0d2688ab0ba447c20261e2aab50b5f543"),
    "mapping": ("private/reviewer_b/OWNER_ONLY_ID_MAP.json",
                "27bce4d9842768aa5cbb7febd963f5247540d6c5806466647802e9a9a2fc6a30"),
    "safe": ("evidence/R58_GOLD192_AI_REVIEW_SAFE_20261102_V6.json",
             "2b73a9514d8ae404371b8641de8da229d4688229038cb33b14f890ddee4a1975"),
}
EXPECTED_REJECT_IDS = {
    "xz-gold-t02108", "s06-gold-t03412",
    "s15-gold-r03-t02216", "s06-gold-t03930",
}
SOURCE_ID = "r58_reviewer_a_recovered_v6_20261102"


def _load_pinned(root: Path, relative: str, digest: str) -> dict:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ManifestError("REVIEWER_A_INPUT_MISSING_OR_SYMLINK")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ManifestError("REVIEWER_A_SOURCE_PIN_MISMATCH")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ManifestError("REVIEWER_A_SOURCE_INVALID")
    return value


def recover_reviewer_a(args) -> dict:
    root = args.bundle_root.resolve(strict=True)
    if root.is_symlink() or any(p.is_symlink() for p in (args.bundle_root, *args.bundle_root.parents)):
        raise ManifestError("REVIEWER_A_BUNDLE_PATH_SYMLINK")
    inputs = {key: _load_pinned(root, *pair) for key, pair in FILES.items()}
    first, remaining = inputs["initial"].get("cases"), inputs["remaining"].get("cases")
    mapping = inputs["mapping"].get("mapping")
    groups = inputs["supplement"].get("reject_groups")
    counts = inputs["safe"].get("ai_review_counts")
    if (not isinstance(first, list) or len(first) != 31 or
            not isinstance(remaining, list) or len(remaining) != 51 or
            not isinstance(mapping, list) or len(mapping) != 192 or
            not isinstance(groups, list) or
            counts != {"semantic_pass_only": 188, "hold": 0, "reject": 4,
                       "semantic_review_pending": 0}):
        raise ManifestError("REVIEWER_A_RECOVERY_SCOPE_INVALID")

    ids_to_sha = {}
    mapped_digests = set()
    for row in mapping:
        if not isinstance(row, dict):
            raise ManifestError("REVIEWER_A_MAPPING_INVALID")
        case, digest = row.get("original_case_id"), row.get("target_sha256")
        if (not isinstance(case, str) or not case or case in ids_to_sha or
                not isinstance(digest, str) or
                not re.fullmatch(r"[0-9a-f]{64}", digest) or digest in mapped_digests):
            raise ManifestError("REVIEWER_A_MAPPING_DUPLICATE_OR_INVALID")
        ids_to_sha[case] = digest
        mapped_digests.add(digest)
    group_rejects = [case for group in groups for case in group.get("case_ids", [])]
    if len(group_rejects) != 4 or set(group_rejects) != EXPECTED_REJECT_IDS:
        raise ManifestError("REVIEWER_A_REJECT_EVIDENCE_MISMATCH")

    # The B importer already established 192 canonical target digests. Require
    # a full exact mapping match before any A event can be appended.
    if not args.manifest.is_file() or args.manifest.is_symlink():
        raise ManifestError("REVIEWER_B_MANIFEST_REQUIRED")
    old = load_events(args.manifest)
    b_hashes = {
        e["payload"].get("target_sha256") for e in old
        if e["batch_id"] == "gold192" and e["event_type"] == "BLIND_REVIEW"
        and e["payload"].get("reviewer_role") == "REVIEWER_B"
        and e["payload"].get("reviewer_source_sha256") ==
        "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"
    }
    if len(b_hashes) != 192 or b_hashes != mapped_digests:
        raise ManifestError("REVIEWER_A_B_TARGET_SET_MISMATCH")

    seen = set()
    decision_counts = Counter()
    events = []
    missing_scores = set()
    for row in first + remaining:
        if not isinstance(row, dict):
            raise ManifestError("REVIEWER_A_ROW_INVALID")
        case = row.get("case_id")
        if not isinstance(case, str) or case not in ids_to_sha or case in seen:
            raise ManifestError("REVIEWER_A_CASE_ID_INVALID")
        seen.add(case)
        decision = row.get("decision")
        scores = row.get("scores_1_to_5")
        if decision == "AI_SEMANTIC_PASS_ONLY":
            if (not isinstance(scores, dict) or set(scores) != SCORES or
                    any(type(v) is not int or not 1 <= v <= 5 for v in scores.values())):
                raise ManifestError("REVIEWER_A_PASS_SCORES_INVALID")
            evidence = row.get("note")
            if not isinstance(evidence, str) or not evidence.strip():
                raise ManifestError("REVIEWER_A_EVIDENCE_INVALID")
            events.append(make_event("gold192", "INCREMENTAL_REVIEW", {
                "case_id": "reviewer-a:" + ids_to_sha[case],
                "target_sha256": ids_to_sha[case],
                "reviewer_role": "REVIEWER_A",
                "reviewer_source": SOURCE_ID,
                "decision": "PASS_ONLY",
                "scores": scores,
                "evidence_summary": evidence,
                "evidence_tier": "RECOVERED_SCORED_CASE_LEVEL_V6",
            }, now()))
            decision_counts["PASS_ONLY"] += 1
        elif decision == "REJECT" and scores is None:
            missing_scores.add(case)
            decision_counts["REJECT_UNSCORED_NOT_IMPORTED"] += 1
        else:
            raise ManifestError("REVIEWER_A_DECISION_OR_SCORE_INVALID")
    if (len(seen) != 82 or len(events) != 79 or
            len(missing_scores) != 3 or
            not missing_scores.issubset(EXPECTED_REJECT_IDS) or
            decision_counts != {"PASS_ONLY": 79, "REJECT_UNSCORED_NOT_IMPORTED": 3}):
        raise ManifestError("REVIEWER_A_RECOVERED_COUNTS_INVALID")

    reject_events = [make_event("gold192", "HISTORICAL_REJECT_EVIDENCE", {
        "case_id": "reviewer-a:" + ids_to_sha[case],
        "target_sha256": ids_to_sha[case],
        "reviewer_role": "REVIEWER_A",
        "reviewer_source": SOURCE_ID,
        "decision": "REJECT",
        "score_state": "UNAVAILABLE_NOT_SYNTHESIZED",
        "evidence_tier": ("RECOVERED_CASE_LEVEL_REJECT_UNSCORED_V6"
                          if case in missing_scores else
                          "FINAL_V6_REJECT_GROUP_ONLY"),
    }, now()) for case in sorted(EXPECTED_REJECT_IDS)]

    existing = [
        e for e in old if e["batch_id"] == "gold192"
        and e["event_type"] == "INCREMENTAL_REVIEW"
        and e["payload"].get("reviewer_role") == "REVIEWER_A"
    ]
    existing_rejects = [
        e for e in old if e["batch_id"] == "gold192"
        and e["event_type"] == "HISTORICAL_REJECT_EVIDENCE"
        and e["payload"].get("reviewer_role") == "REVIEWER_A"
    ]
    if existing:
        expected = {e["payload"]["target_sha256"] for e in events}
        actual = {e["payload"].get("target_sha256") for e in existing
                  if e["payload"].get("reviewer_source") == SOURCE_ID}
        if (len(existing) != 79 or actual != expected or len(actual) != 79 or
                any(e["payload"].get("reviewer_source") != SOURCE_ID
                    for e in existing)):
            raise ManifestError("REVIEWER_A_EXISTING_EVENTS_CONFLICT")
    if existing_rejects:
        expected_rejects = {ids_to_sha[case] for case in EXPECTED_REJECT_IDS}
        actual_rejects = {e["payload"].get("target_sha256") for e in existing_rejects}
        if (len(existing_rejects) != 4 or actual_rejects != expected_rejects or
                any(e["payload"].get("reviewer_source") != SOURCE_ID or
                    e["payload"].get("decision") != "REJECT" or
                    e["payload"].get("score_state") != "UNAVAILABLE_NOT_SYNTHESIZED" or
                    "scores" in e["payload"] for e in existing_rejects)):
            raise ManifestError("REVIEWER_A_EXISTING_REJECT_EVIDENCE_CONFLICT")
    pending = ([] if existing else events) + ([] if existing_rejects else reject_events)
    appended = append_events(args.manifest, pending, args.repo_root) if pending else 0
    status = ("RECOVERED_REVIEWER_A_ALREADY_IMPORTED" if not pending else
              "RECOVERED_REVIEWER_A_SCORED_AND_REJECT_EVIDENCE_IMPORTED")
    return {
        "schema": "storyforge_gold192_reviewer_a_recovery_safe_v1",
        "status": status,
        "case_level_records_recovered": 82,
        "scored_pass_cases_imported": 79,
        "historical_reject_evidence_imported": 4,
        "historical_rejects_without_scores": 4,
        "unscored_rejects_recovered_at_case_level": 3,
        "other_historical_reject_without_case_level_review": 1,
        "unrecovered_case_level_records": 110,
        "events_appended": appended,
        "reviewer_b_target_set_match": True,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Recover pinned private Reviewer A scored cases")
    p.add_argument("--bundle-root", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(recover_reviewer_a(args), indent=2, sort_keys=True))
        return 0
    except (ManifestError, OSError, ValueError, TypeError) as exc:
        code = str(exc) if isinstance(exc, ManifestError) else "RECOVERY_INPUT_ERROR"
        print(json.dumps({"schema": "storyforge_gold192_reviewer_a_recovery_safe_v1",
                          "status": "HOLD", "reason_code": code,
                          "private_values_emitted": False,
                          "quality_v1_admitted": 0,
                          "training_authorized": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
