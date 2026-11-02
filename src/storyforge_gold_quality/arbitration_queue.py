"""Build an Owner-only Gold192 disagreement review queue from private Manifest.

The queue is a private artifact, never a verdict or a Quality-v1 admission.
Stdout is count-only SAFE. Never publish the queue or its raw identifiers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
from collections import Counter, defaultdict
from pathlib import Path

from .manifest import ManifestError, load_events
from .reconcile import CANONICAL_REVIEWER_B_SHA256, reconcile_gold192

PASS = {"PASS", "PASS_ONLY"}
REVIEW_EVENTS = {"INCREMENTAL_REVIEW", "BLIND_REVIEW"}
HISTORICAL_SOURCE = "r58_reviewer_a_recovered_v6_20261102"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def build_disagreements(events: list[dict]) -> tuple[dict, list[dict]]:
    summary = reconcile_gold192(events)
    if summary["nonexcluded_cases_observed"] != 192:
        raise ManifestError("ARBITRATION_SCOPE_NOT_192")
    rows = defaultdict(lambda: {"a": [], "b": [], "historical": []})
    for event in events:
        if event["batch_id"] != "gold192":
            continue
        kind, p = event["event_type"], event["payload"]
        if kind not in REVIEW_EVENTS | {"HISTORICAL_REJECT_EVIDENCE"}:
            continue
        digest = p.get("target_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise ManifestError("ARBITRATION_TARGET_INVALID")
        role = p.get("reviewer_role")
        if kind == "HISTORICAL_REJECT_EVIDENCE":
            if (role != "REVIEWER_A" or p.get("reviewer_source") != HISTORICAL_SOURCE
                    or p.get("decision") != "REJECT"
                    or p.get("score_state") != "UNAVAILABLE_NOT_SYNTHESIZED"
                    or "scores" in p):
                raise ManifestError("ARBITRATION_HISTORICAL_EVIDENCE_INVALID")
            rows[digest]["historical"].append(p)
        elif role == "REVIEWER_B":
            if p.get("reviewer_source_sha256") == CANONICAL_REVIEWER_B_SHA256:
                rows[digest]["b"].append(p)
        elif role == "REVIEWER_A":
            rows[digest]["a"].append(p)
    if len(rows) != 192:
        raise ManifestError("ARBITRATION_CASE_UNIVERSE_INVALID")
    queue = []
    types = Counter()
    for digest, state in sorted(rows.items()):
        a, b, hist = state["a"], state["b"], state["historical"]
        if len(b) != 1 or len(a) > 1 or len(hist) > 1 or (a and hist):
            raise ManifestError("ARBITRATION_REVIEW_ROUNDS_AMBIGUOUS")
        if hist:
            if b[0].get("decision") not in PASS:
                raise ManifestError("ARBITRATION_HISTORICAL_B_UNEXPECTED")
            reason = "A_HISTORICAL_REJECT_B_PASS"
            source = hist[0]
            a_decision = "REJECT"
            a_scores = None
            a_summary = None
            a_tier = source.get("evidence_tier")
        elif a:
            source = a[0]
            a_decision = source.get("decision")
            a_scores = source.get("scores")
            a_summary = source.get("evidence_summary")
            a_tier = source.get("evidence_tier")
            b_decision = b[0].get("decision")
            if a_decision in PASS and b_decision == "HOLD":
                reason = "A_PASS_B_HOLD"
            elif a_decision in PASS and b_decision == "REJECT":
                reason = "A_PASS_B_REJECT"
            elif a_decision == "REJECT" and b_decision in PASS:
                reason = "A_REJECT_B_PASS"
            elif a_decision == "HOLD" and b_decision in PASS:
                reason = "A_HOLD_B_PASS"
            else:
                continue
        else:
            continue
        types[reason] += 1
        queue.append({
            "target_sha256": digest,
            "original_case_id": None,  # no recovery of source ID by guess
            "reviewer_a": {"decision": a_decision, "scores": a_scores,
                           "evidence_summary": a_summary, "evidence_tier": a_tier,
                           "scores_missing": a_scores is None},
            "reviewer_b": {"blind_case_id": b[0].get("blind_case_id"),
                           "decision": b[0].get("decision"),
                           "scores": b[0].get("scores"),
                           "evidence_summary": b[0].get("evidence_summary"),
                           "severe_flags": b[0].get("severe_flags", [])},
            "disagreement_type": reason,
            "status": "PENDING_OWNER_ARBITRATION",
            "decision": None,
            "arbitration_note": None,
        })
    expected = {"A_HISTORICAL_REJECT_B_PASS": 4, "A_PASS_B_HOLD": 6,
                "A_PASS_B_REJECT": 1}
    if dict(types) != expected or len(queue) != 11:
        raise ManifestError("ARBITRATION_EXPECTED_DISAGREEMENTS_MISMATCH")
    safe = {
        "schema": "storyforge_gold192_arbitration_queue_safe_v1",
        "status": "PRIVATE_ARBITRATION_QUEUE_READY__NO_DECISIONS",
        "disagreement_count": len(queue),
        "disagreement_types": dict(sorted(types.items())),
        "pending_owner_arbitration": len(queue),
        "private_values_emitted": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
    }
    return safe, queue


def write_private_queue(path: Path, queue: list[dict], repo_root: Path) -> None:
    repo = repo_root.resolve(strict=True)
    target = path.absolute()
    if path.is_symlink():
        raise ManifestError("ARBITRATION_OUTPUT_SYMLINK")
    if any(p.is_symlink() for p in (target.parent, *target.parent.parents)):
        raise ManifestError("ARBITRATION_OUTPUT_PARENT_SYMLINK")
    resolved = target.parent.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise ManifestError("ARBITRATION_OUTPUT_INSIDE_REPOSITORY")
    if resolved.stat().st_mode & 0o077:
        raise ManifestError("ARBITRATION_OUTPUT_PARENT_PERMISSIONS_TOO_OPEN")
    data = {"schema": "storyforge_gold192_arbitration_queue_private_v1",
            "status": "PENDING_OWNER_ARBITRATION", "case_count": len(queue),
            "cases": queue}
    raw = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(target, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ManifestError("ARBITRATION_OUTPUT_NOT_REGULAR")
        with os.fdopen(fd, "wb") as out:
            fd = -1
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
    finally:
        if fd >= 0:
            os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create private Gold192 discrepancy queue")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        safe, cases = build_disagreements(load_events(args.manifest))
        write_private_queue(args.output, cases, args.repo_root)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ManifestError, OSError, ValueError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, ManifestError) else "ARBITRATION_IO_OR_INPUT_ERROR"
        print(json.dumps({"schema": "storyforge_gold192_arbitration_queue_safe_v1",
                          "status": "HOLD", "reason_code": reason,
                          "private_values_emitted": False, "quality_v1_admitted": 0,
                          "training_authorized": False, "r50_accessed": False},
                         sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
