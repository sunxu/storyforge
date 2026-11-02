"""Normalize Reviewer A from the three verified R58 V3 sources.

No synthetic Remaining51 file is accepted. The 109 PASS_ONLY entries are marked
aggregate-complement-only; the 31 six-dimension reviews and 52 explicit group
decisions retain their actual evidence granularity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

from .manifest import ManifestError

PINS = {
    "safe_v3": "e9009984fb5c223dd179b9f9920ff0fb083e26f7241bda4b2c3b0f16de6ae2ac",
    "cases31": "734ae5ccfc5ce06ff8c5fec3a98798273c1b75b2496289173bf212203de3deaf",
    "supplement_v3": "84ea6170aa13532093ebb611b3541c73d28f6add3271ab0c7c8ad22a0ee2af02",
    "packets": "ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e",
    "reviewer_b": "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _read_pinned(path: Path, key: str) -> tuple[bytes, dict | None]:
    if path.is_symlink() or not path.is_file():
        raise ManifestError("REVIEWER_A_V3_SOURCE_MISSING_OR_SYMLINK")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PINS[key]:
        raise ManifestError("REVIEWER_A_V3_SOURCE_PIN_MISMATCH_" + key.upper())
    if key == "packets":
        return raw, None
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ManifestError("REVIEWER_A_V3_SOURCE_SCHEMA_INVALID")
    return raw, value


def normalize_v3(safe_v3: dict, cases31: dict, supplement: dict,
                 packets_raw: bytes, reviewer_b: dict) -> tuple[dict, dict, dict]:
    counts = safe_v3.get("counts", {})
    if (safe_v3.get("schema") != "r58_gold192_ai_semantic_review_safe_v2"
            or counts.get("candidate_cases") != 192
            or counts.get("ai_semantic_pass_only") != 140
            or counts.get("hold") != 51 or counts.get("reject") != 1):
        raise ManifestError("REVIEWER_A_V3_SAFE_COUNTS_INVALID")
    if (cases31.get("schema") != "r58_gold192_ai_review_31_cases_private_v1"
            or len(cases31.get("cases", [])) != 31
            or cases31.get("counts", {}).get("ai_semantic_pass_only") != 31):
        raise ManifestError("REVIEWER_A_V3_CASES31_INVALID")
    if (supplement.get("schema") != "r58_gold192_ai_review_minimum_supplement_private_v2"
            or len(supplement.get("case_level_ai_reviews", [])) != 31):
        raise ManifestError("REVIEWER_A_V3_SUPPLEMENT_INVALID")
    cases31_rows = cases31["cases"]
    supplement_rows = supplement["case_level_ai_reviews"]
    if cases31_rows != supplement_rows:
        raise ManifestError("REVIEWER_A_V3_CASES31_SUPPLEMENT_MISMATCH")

    packets = []
    for line in packets_raw.decode("utf-8").splitlines():
        if line.strip():
            packets.append(json.loads(line))
    packet_cases = {}
    for packet in packets:
        for case in packet.get("cases", []):
            cid, digest = case.get("case_id"), case.get("target_sha256")
            if (not isinstance(cid, str) or not cid or cid in packet_cases
                    or not isinstance(digest, str) or not HEX64.fullmatch(digest)):
                raise ManifestError("REVIEWER_A_V3_PACKET_IDENTITY_INVALID")
            packet_cases[cid] = {
                "target_sha256": digest,
                "cohort": case.get("cohort"),
                "story_uuid": packet.get("story_uuid"),
            }
    if len(packet_cases) != 192 or len({x["target_sha256"] for x in packet_cases.values()}) != 192:
        raise ManifestError("REVIEWER_A_V3_PACKET_SCOPE_INVALID")

    if (reviewer_b.get("schema") != "r58_gold192_reviewer_b_results_v1"
            or len(reviewer_b.get("cases", [])) != 192
            or reviewer_b.get("counts") != {"PASS": 178, "HOLD": 12, "REJECT": 2}):
        raise ManifestError("REVIEWER_A_V3_REVIEWER_B_INVALID")
    b_by_sha = {}
    for row in reviewer_b["cases"]:
        digest = row.get("target_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest) or digest in b_by_sha:
            raise ManifestError("REVIEWER_A_V3_REVIEWER_B_TARGET_INVALID")
        b_by_sha[digest] = row
    if set(b_by_sha) != {x["target_sha256"] for x in packet_cases.values()}:
        raise ManifestError("REVIEWER_A_V3_REVIEWER_B_TARGET_SET_MISMATCH")

    scored = {}
    for row in cases31_rows:
        cid = row.get("case_id")
        scores = row.get("scores_1_to_5")
        if (cid in scored or cid not in packet_cases
                or row.get("decision") != "AI_SEMANTIC_PASS_ONLY"
                or not isinstance(scores, dict)
                or set(scores) != {"chinese_prose", "character_consistency", "npc_initiative",
                                   "player_agency", "narrative_continuity", "rule_fidelity"}
                or any(type(v) is not int or not 1 <= v <= 5 for v in scores.values())):
            raise ManifestError("REVIEWER_A_V3_SCORED_CASE_INVALID")
        scored[cid] = row

    hold_groups = {}
    for group in supplement.get("case_level_hold_groups", []):
        ids = group.get("case_ids")
        if not isinstance(ids, list):
            raise ManifestError("REVIEWER_A_V3_HOLD_GROUP_INVALID")
        for cid in ids:
            if cid in hold_groups or cid in scored or cid not in packet_cases:
                raise ManifestError("REVIEWER_A_V3_HOLD_ID_DUPLICATE_OR_UNKNOWN")
            hold_groups[cid] = group
    reject_groups = {}
    for group in supplement.get("reject_groups", []):
        ids = group.get("case_ids")
        if not isinstance(ids, list):
            raise ManifestError("REVIEWER_A_V3_REJECT_GROUP_INVALID")
        for cid in ids:
            if cid in reject_groups or cid in scored or cid in hold_groups or cid not in packet_cases:
                raise ManifestError("REVIEWER_A_V3_REJECT_ID_DUPLICATE_OR_UNKNOWN")
            reject_groups[cid] = group
    if len(scored) != 31 or len(hold_groups) != 51 or len(reject_groups) != 1:
        raise ManifestError("REVIEWER_A_V3_EXPLICIT_EVIDENCE_COUNTS_INVALID")

    aggregate_ids = set(packet_cases) - set(scored) - set(hold_groups) - set(reject_groups)
    if len(aggregate_ids) != 109 or len(scored) + len(hold_groups) + len(reject_groups) + len(aggregate_ids) != 192:
        raise ManifestError("REVIEWER_A_V3_AGGREGATE_COMPLEMENT_INVALID")

    records, cross = [], Counter()
    for cid, identity in sorted(packet_cases.items()):
        digest = identity["target_sha256"]
        b = b_by_sha[digest]
        if cid in scored:
            a_decision, state, granularity = "PASS_ONLY", "CASE_LEVEL_SCORED_PASS", "CASE_LEVEL_SCORED_REVIEW"
            score = scored[cid]["scores_1_to_5"]
            note = scored[cid].get("note")
            source = "R58_GOLD192_AI_REVIEW_31_CASES_PRIVATE_20261102.json"
            reason = story = None
        elif cid in hold_groups:
            group = hold_groups[cid]
            a_decision, state, granularity = "HOLD", "EXPLICIT_CASE_ID_IN_HOLD_GROUP__NO_INDIVIDUAL_SCORES", "CASE_ID_IN_EXPLICIT_HOLD_GROUP"
            score = note = None
            source = "R58_GOLD192_AI_REVIEW_SUPPLEMENT_PRIVATE_20261102_v3.json"
            reason, story = group.get("reason"), group.get("story")
        elif cid in reject_groups:
            group = reject_groups[cid]
            a_decision, state, granularity = "REJECT", "EXPLICIT_CASE_ID_IN_REJECT_GROUP__NO_INDIVIDUAL_SCORES", "CASE_ID_IN_EXPLICIT_REJECT_GROUP"
            score = note = None
            source = "R58_GOLD192_AI_REVIEW_SUPPLEMENT_PRIVATE_20261102_v3.json"
            reason, story = group.get("reason", "REJECT_GROUP"), group.get("story")
        else:
            a_decision, state, granularity = "PASS_ONLY", "PASS_INFERRED_FROM_V3_AGGREGATE_COMPLEMENT__PENDING_CASE_LEVEL_EVIDENCE", "AGGREGATE_COMPLEMENT_ONLY"
            score = note = reason = story = None
            source = "R58_GOLD192_AI_REVIEW_SAFE_20261102_v3.json"
        cross[(granularity, b["decision"])] += 1
        records.append({
            "case_id": cid, "target_sha256": digest, "cohort": identity["cohort"],
            "story_uuid": identity["story_uuid"], "reviewer": "A",
            "reported_final_decision": a_decision,
            "decision_for_strict_ab_decision_comparison": (
                None if granularity == "AGGREGATE_COMPLEMENT_ONLY" else a_decision),
            "scores_1_to_5": score, "review_evidence_state": state,
            "evidence_granularity": granularity,
            "case_level_scored_review_present": cid in scored,
            "case_id_in_explicit_group": cid in hold_groups or cid in reject_groups,
            "aggregate_complement_only": granularity == "AGGREGATE_COMPLEMENT_ONLY",
            "source_file": source, "group_reason": reason, "group_story": story,
            "review_note": note, "reviewer_b_decision": b["decision"],
            "reviewer_b_blind_case_id": b.get("blind_case_id"),
            "reviewer_b_scores_1_to_5": b.get("scores_1_to_5"),
            "reviewer_b_evidence_summary": b.get("evidence_summary"),
            "reviewer_b_severe_flags": b.get("severe_flags", []),
            "quality_v1_admitted": False,
        })

    priority = [r for r in records if r["evidence_granularity"] == "AGGREGATE_COMPLEMENT_ONLY"
                and r["reviewer_b_decision"] in {"HOLD", "REJECT"}]
    if len(priority) != 7 or Counter(r["reviewer_b_decision"] for r in priority) != {"HOLD": 6, "REJECT": 1}:
        raise ManifestError("REVIEWER_A_V3_PRIORITY7_COUNTS_INVALID")
    if Counter(r["reported_final_decision"] for r in records) != {"PASS_ONLY": 140, "HOLD": 51, "REJECT": 1}:
        raise ManifestError("REVIEWER_A_V3_FINAL_DECISION_COUNTS_INVALID")

    cross_rows = []
    for granularity in ("AGGREGATE_COMPLEMENT_ONLY", "CASE_LEVEL_SCORED_REVIEW",
                        "CASE_ID_IN_EXPLICIT_HOLD_GROUP", "CASE_ID_IN_EXPLICIT_REJECT_GROUP"):
        cross_rows.append({"a_evidence_granularity": granularity,
                           **{d: cross[(granularity, d)] for d in ("PASS", "HOLD", "REJECT")}})
    report = {
        "schema": "r58_gold192_reviewer_a_results_v3_reconciled_private_v1",
        "status": "V3_SOURCES_NORMALIZED__192_IDENTITIES_VERIFIED__EVIDENCE_GRANULARITY_EXPLICIT",
        "reviewer": "A", "source_pins": PINS,
        "decision_counts": {"PASS_ONLY": 140, "HOLD": 51, "REJECT": 1},
        "evidence_granularity_counts": {
            "case_level_scored_pass": 31, "explicit_hold_group_without_scores": 51,
            "explicit_reject_group_without_scores": 1, "aggregate_complement_pass_pending_case_evidence": 109,
        },
        "strict_ab_score_comparison_eligible": 31,
        "strict_ab_decision_comparison_eligible": 83,
        "records": records, "quality_v1_admitted": 0, "training_authorized": False,
    }
    report_raw = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    report_sha = hashlib.sha256(report_raw).hexdigest()
    safe = {
        "schema": "r58_gold192_reviewer_a_results_v3_reconciled_safe_v1",
        "status": "V3_REVIEWER_A_NORMALIZATION_PASS__QUALITY_ADMISSION_HOLD",
        "reviewer_a_records": 192,
        "reviewer_a_decision_counts": report["decision_counts"],
        "evidence_granularity_counts": report["evidence_granularity_counts"],
        "reviewer_b_decision_counts": {"PASS": 178, "HOLD": 12, "REJECT": 2},
        "cross_tab": cross_rows, "aggregate_only_b_nonpass_priority_count": 7,
        "aggregate_only_b_nonpass_priority_decisions": {"HOLD": 6, "REJECT": 1},
        "other_aggregate_only_b_pass": 102, "strict_ab_score_comparison_eligible": 31,
        "strict_ab_decision_comparison_eligible": 83, "private_report_sha256": report_sha,
        "source_pins": PINS, "private_values_emitted": False, "quality_v1_admitted": 0,
        "training_authorized": False, "gpu_started": False, "r50_accessed": False,
    }
    queue = {
        "schema": "r58_gold192_reviewer_a_v3_aggregate_only_b_nonpass_priority_private_v1",
        "status": "V3_AGGREGATE_ONLY_PASS_VS_B_NONPASS__PENDING_A_CASE_EVIDENCE",
        "source_report_sha256": report_sha, "case_count": 7,
        "cases": [{
            "case_id": r["case_id"], "target_sha256": r["target_sha256"],
            "reviewer_a_reported_final_decision": "PASS_ONLY",
            "reviewer_a_evidence_state": r["review_evidence_state"],
            "reviewer_a_actual_case_level_decision": None, "reviewer_a_scores_1_to_5": None,
            "reviewer_b_blind_case_id": r["reviewer_b_blind_case_id"],
            "reviewer_b_decision": r["reviewer_b_decision"],
            "reviewer_b_scores_1_to_5": r["reviewer_b_scores_1_to_5"],
            "reviewer_b_evidence_summary": r["reviewer_b_evidence_summary"],
            "reviewer_b_severe_flags": r["reviewer_b_severe_flags"],
            "priority": "P0" if r["reviewer_b_decision"] == "REJECT" else "P1",
            "task": "SEARCH_VERIFIED_EXISTING_REVIEWER_A_CASE_LEVEL_EVIDENCE",
            "status": "PENDING_A_EVIDENCE_RECOVERY", "quality_v1_admitted": False,
        } for r in priority],
    }
    return report, safe, queue


def _private_write(path: Path, raw: bytes, repo_root: Path) -> None:
    target = path.absolute()
    if target.is_symlink() or target.exists():
        raise ManifestError("REVIEWER_A_V3_OUTPUT_ALREADY_EXISTS")
    repo = repo_root.resolve(strict=True)
    parent = target.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ManifestError("REVIEWER_A_V3_OUTPUT_PARENT_INVALID")
    resolved = parent.resolve(strict=True)
    if resolved == repo or repo in resolved.parents or resolved.stat().st_mode & 0o077:
        raise ManifestError("REVIEWER_A_V3_OUTPUT_PARENT_PERMISSIONS_OR_LOCATION_INVALID")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def build(args) -> dict:
    loaded = {}
    for key, path in (
        ("safe_v3", args.safe_v3), ("cases31", args.cases31),
        ("supplement_v3", args.supplement_v3), ("packets", args.packets),
        ("reviewer_b", args.reviewer_b),
    ):
        _raw, value = _read_pinned(path, key)
        loaded[key] = value if value is not None else _raw
    report, safe, queue = normalize_v3(
        loaded["safe_v3"], loaded["cases31"], loaded["supplement_v3"],
        loaded["packets"], loaded["reviewer_b"])
    report_raw = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    safe_raw = (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    queue_raw = (json.dumps(queue, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    for path in (args.output, args.safe_output, args.priority_output):
        if path.exists() or path.is_symlink():
            raise ManifestError("REVIEWER_A_V3_OUTPUT_ALREADY_EXISTS")
    _private_write(args.output, report_raw, args.repo_root)
    _private_write(args.safe_output, safe_raw, args.repo_root)
    _private_write(args.priority_output, queue_raw, args.repo_root)
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Reviewer A from verified R58 V3 sources")
    for name in ("safe-v3", "cases31", "supplement-v3", "packets", "reviewer-b",
                 "output", "safe-output", "priority-output", "repo-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ManifestError, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, ManifestError) else "REVIEWER_A_V3_INPUT_OR_IO_ERROR"
        print(json.dumps({"schema": "r58_gold192_reviewer_a_results_v3_reconciled_safe_v1",
                          "status": "HOLD", "reason_code": reason, "quality_v1_admitted": 0,
                          "training_authorized": False, "gpu_started": False,
                          "r50_accessed": False, "private_values_emitted": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
