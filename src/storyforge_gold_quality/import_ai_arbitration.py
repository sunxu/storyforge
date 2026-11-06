"""Import completed AI arbitration as a separate, non-owner evidence layer.

Requires the private arbitration report, its SAFE receipt, and the original
private queue. Does not alter A/B reviews, invent scores, or grant admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .manifest import ManifestError, append_events, load_events, make_event

PASS_HOLD = {"PASS", "HOLD"}
CANONICAL_B = "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"
A_SOURCE = "r58_reviewer_a_recovered_v6_20261102"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED = {"PASS": 6, "HOLD": 5}


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read_pinned(path: Path) -> tuple[dict, bytes]:
    if path.is_symlink() or not path.is_file():
        raise ManifestError("ARBITRATION_INPUT_NOT_REGULAR")
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ManifestError("ARBITRATION_INPUT_SCHEMA_INVALID")
    return data, raw


def _review_index(events: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for event in events:
        if event["batch_id"] != "gold192":
            continue
        kind, p = event["event_type"], event["payload"]
        digest = p.get("target_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            continue
        state = index.setdefault(digest, {"a": [], "b": [], "historical": []})
        if kind in {"INCREMENTAL_REVIEW", "BLIND_REVIEW"}:
            role = p.get("reviewer_role")
            if role == "REVIEWER_A":
                state["a"].append(p)
            elif (role == "REVIEWER_B" and
                  p.get("reviewer_source_sha256") == CANONICAL_B):
                state["b"].append(p)
        elif (kind == "HISTORICAL_REJECT_EVIDENCE"
              and p.get("reviewer_source") == A_SOURCE):
            state["historical"].append(p)
    return index


def import_ai_arbitration(args) -> dict:
    private, private_raw = _read_pinned(args.input)
    safe, _safe_raw = _read_pinned(args.safe_summary)
    queue, queue_raw = _read_pinned(args.queue)
    report_sha = hashlib.sha256(private_raw).hexdigest()
    queue_sha = hashlib.sha256(queue_raw).hexdigest()
    if (private.get("schema") != "storyforge_gold192_ai_disagreement_arbitration_private_v1"
            or private.get("status") != "AI_ARBITRATION_11_COMPLETED__OWNER_ADMISSION_HOLD"
            or safe.get("schema") != "storyforge_gold192_ai_disagreement_arbitration_safe_v1"
            or safe.get("private_report_sha256") != report_sha
            or queue.get("schema") != "storyforge_gold192_arbitration_queue_private_v1"
            or private.get("source_integrity", {}).get("arbitration_queue_sha256") != queue_sha):
        raise ManifestError("ARBITRATION_SOURCE_PIN_OR_SCHEMA_MISMATCH")
    if (private.get("source_integrity", {}).get("packet_case_count") != 192
            or private.get("source_integrity", {}).get("matched_disagreements") != 11
            or safe.get("disagreements_matched") != 11
            or safe.get("arbitration_decision_counts") != EXPECTED
            or safe.get("prior_a_b_decisions_preserved") is not True
            or safe.get("quality_v1_admitted") != 0
            or safe.get("training_authorized") is not False
            or safe.get("gpu_started") is not False
            or safe.get("r50_accessed") is not False
            or safe.get("private_values_emitted") is not False):
        raise ManifestError("ARBITRATION_SAFE_RECEIPT_INVALID")
    cases = private.get("cases")
    queued = queue.get("cases")
    if not isinstance(cases, list) or len(cases) != 11 or not isinstance(queued, list) or len(queued) != 11:
        raise ManifestError("ARBITRATION_CASE_COUNT_INVALID")
    queue_by_hash = {}
    for row in queued:
        digest = row.get("target_sha256")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest) or digest in queue_by_hash:
            raise ManifestError("ARBITRATION_QUEUE_IDENTITY_INVALID")
        if row.get("status") != "PENDING_OWNER_ARBITRATION" or row.get("decision") is not None:
            raise ManifestError("ARBITRATION_QUEUE_NOT_PENDING")
        queue_by_hash[digest] = row
    events = load_events(args.manifest)
    index = _review_index(events)
    new_events, seen, decisions = [], set(), Counter()
    for row in cases:
        digest = row.get("target_sha256")
        if (not isinstance(digest, str) or not HEX64.fullmatch(digest)
                or digest in seen or digest not in queue_by_hash):
            raise ManifestError("ARBITRATION_CASE_IDENTITY_INVALID")
        seen.add(digest)
        if row.get("quality_v1_admitted") is not False or row.get("human_owner_approval") is not False:
            raise ManifestError("ARBITRATION_OWNER_ADMISSION_FLAG_INVALID")
        decision = row.get("arbitration_decision")
        if decision not in PASS_HOLD:
            raise ManifestError("ARBITRATION_DECISION_INVALID")
        state = index.get(digest)
        queued_row = queue_by_hash[digest]
        if state is None or len(state["b"]) != 1 or len(state["a"]) + len(state["historical"]) != 1:
            raise ManifestError("ARBITRATION_REVIEW_EVIDENCE_NOT_UNIQUE")
        a = state["a"][0] if state["a"] else state["historical"][0]
        b = state["b"][0]
        a_decision = a.get("decision")
        b_decision = b.get("decision")
        if (row.get("reviewer_a_previous_decision") != a_decision
                or row.get("reviewer_b_previous_decision") != b_decision
                or row.get("reviewer_b_blind_case_id") != b.get("blind_case_id")
                or row.get("previous_disagreement_type") != queued_row.get("disagreement_type")
                or queued_row.get("reviewer_a", {}).get("decision") != a_decision
                or queued_row.get("reviewer_b", {}).get("decision") != b_decision):
            raise ManifestError("ARBITRATION_PRIOR_DECISION_MISMATCH")
        if not isinstance(row.get("case_id"), str) or not row["case_id"]:
            raise ManifestError("ARBITRATION_CASE_ID_MISSING")
        rationale = row.get("rationale_cn")
        scope = row.get("scope_limit_cn")
        basis = row.get("review_basis")
        if (not isinstance(rationale, str) or not rationale.strip()
                or not isinstance(scope, str) or not scope.strip()
                or not isinstance(basis, list) or not basis
                or any(not isinstance(x, str) for x in basis)):
            raise ManifestError("ARBITRATION_RATIONALE_INVALID")
        decisions[decision] += 1
        payload = {
            "case_id": "ai-arbitration:" + digest,
            "target_sha256": digest,
            "arbiter_type": "AI_ARBITER",
            "arbitration_source_sha256": report_sha,
            "arbitration_queue_sha256": queue_sha,
            "case_id_label": row["case_id"],
            "reviewer_b_blind_case_id": row["reviewer_b_blind_case_id"],
            "previous_disagreement_type": row["previous_disagreement_type"],
            "reviewer_a_previous_decision": a_decision,
            "reviewer_b_previous_decision": b_decision,
            "decision": decision,
            "rationale_cn": rationale,
            "scope_limit_cn": scope,
            "review_basis": basis,
            "human_owner_approval": False,
            "quality_v1_admitted": False,
        }
        new_events.append(make_event("gold192", "AI_ARBITRATION", payload, now()))
    if len(seen) != 11 or dict(decisions) != EXPECTED:
        raise ManifestError("ARBITRATION_DECISION_COUNTS_INVALID")
    existing = [e for e in events if e["batch_id"] == "gold192"
                and e["event_type"] == "AI_ARBITRATION"]
    if existing:
        prior = {e["payload"].get("target_sha256"): e["payload"]
                 for e in existing
                 if e["payload"].get("arbitration_source_sha256") == report_sha}
        if (len(existing) != 11 or len(prior) != 11
                or set(prior) != seen
                or any(prior[d].get("decision") != next(
                    x["payload"]["decision"] for x in new_events
                    if x["payload"]["target_sha256"] == d) for d in seen)):
            raise ManifestError("ARBITRATION_EXISTING_EVENTS_CONFLICT")
        status, appended = "AI_ARBITRATION_ALREADY_IMPORTED", 0
    else:
        appended = append_events(args.manifest, new_events, args.repo_root)
        status = "AI_ARBITRATION_IMPORTED__OWNER_ADMISSION_HOLD"
    return {
        "schema": "storyforge_gold192_ai_arbitration_import_safe_v1",
        "status": status,
        "arbitration_cases_verified": 11,
        "decision_counts": dict(sorted(decisions.items())),
        "events_appended": appended,
        "prior_a_b_decisions_preserved": True,
        "human_owner_approval": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import private AI arbitration as separate evidence")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--safe-summary", required=True, type=Path)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(import_ai_arbitration(args), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ManifestError, OSError, ValueError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, ManifestError) else "ARBITRATION_INPUT_OR_IO_ERROR"
        print(json.dumps({"schema": "storyforge_gold192_ai_arbitration_import_safe_v1",
                          "status": "HOLD", "reason_code": reason,
                          "private_values_emitted": False, "quality_v1_admitted": 0,
                          "training_authorized": False, "r50_accessed": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
