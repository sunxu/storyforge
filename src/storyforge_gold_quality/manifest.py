from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import uuid
from collections import Counter, defaultdict

SCHEMA = "storyforge_gold_quality_manifest_event_v1"
EVENT_TYPES = {"SOURCE_FREEZE", "LEGACY_SELECTION_EVIDENCE", "LEGACY_REVIEW",
               "SOURCE_METADATA", "TRAINING_EXPOSURE_AGGREGATE", "TRAINING_EXPOSURE_ROW",
               "WORLD_IDENTITY_REVIEW", "INCREMENTAL_REVIEW", "BLIND_REVIEW",
               "ADJUDICATION", "AI_ARBITRATION", "HISTORICAL_REJECT_EVIDENCE", "STRUCTURE_VALIDATION", "TOKEN_PREFLIGHT", "FREEZE", "EXCLUSION", "REVIEW_RECONCILIATION", "GOLD72_OWNER_RESOLUTION"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def validate_event(event):
    required = {"schema", "event_id", "batch_id", "event_type", "recorded_at", "payload"}
    if not isinstance(event, dict) or not required.issubset(event):
        raise ManifestError("EVENT_SCHEMA_INVALID")
    if event["schema"] != SCHEMA or event["event_type"] not in EVENT_TYPES:
        raise ManifestError("EVENT_SCHEMA_INVALID")
    if not isinstance(event["payload"], dict):
        raise ManifestError("EVENT_PAYLOAD_INVALID")
    digest = event["payload"].get("target_sha256")
    if digest is not None and (not isinstance(digest, str) or not HEX64.fullmatch(digest)):
        raise ManifestError("TARGET_HASH_INVALID")
    if event["event_type"] == "REVIEW_RECONCILIATION":
        payload = event["payload"]
        source_pins = payload.get("source_pins")
        counts = (
            "candidate_count", "comparable_decision_cases", "decision_agreements",
            "decision_disagreements", "score_comparable_cases",
        )
        required_reconciliation_fields = {
            "reconciliation_type", "source_receipt_sha256", "source_pins",
            "candidate_count", "reviewer_a_evidence_granularity",
            "reviewer_b2_decisions", "a_b2_pair_counts",
            "comparable_decision_cases", "decision_agreements",
            "decision_disagreements", "score_comparable_cases",
            "score_comparison_by_dimension",
            "reviewer_a_two_independent_blinded_reviews_met",
            "reviewer_b2_execution_attestation_self_reported",
            "reviewer_b2_independence_verified", "cryptographic_independence_proven",
            "evidence_tier", "quality_v1_admitted", "training_authorized",
            "gpu_started", "r50_accessed",
        }
        source_pin_fields = {
            "staging_sha256", "source_context_sha256", "reviewer_a_v3_report_sha256",
            "reviewer_b2_blind_input_sha256", "reviewer_b2_instructions_sha256",
            "reviewer_b2_owner_map_sha256", "reviewer_b2_result_sha256",
            "reviewer_b2_execution_record_sha256",
        }
        a_counts = payload.get("reviewer_a_evidence_granularity")
        b_counts = payload.get("reviewer_b2_decisions")
        pair_counts = payload.get("a_b2_pair_counts")
        score_metrics = payload.get("score_comparison_by_dimension")
        if (event["batch_id"] != "gold72"
                or not required_reconciliation_fields.issubset(payload)
                or payload.get("reconciliation_type") != "REVIEWER_A_B2_CROSSWALK"
                or not isinstance(payload.get("source_receipt_sha256"), str)
                or not HEX64.fullmatch(payload["source_receipt_sha256"])
                or not isinstance(source_pins, dict) or set(source_pins) != source_pin_fields
                or any(not isinstance(value, str) or not HEX64.fullmatch(value)
                       for value in source_pins.values())
                or any(type(payload.get(key)) is not int or not 0 <= payload[key] <= 72
                       for key in counts)
                or payload.get("candidate_count") != 72
                or not isinstance(a_counts, dict) or sum(a_counts.values()) != 72
                or not isinstance(b_counts, dict) or sum(b_counts.values()) != 72
                or not isinstance(pair_counts, dict) or sum(pair_counts.values()) != 72
                or not isinstance(score_metrics, dict)
                or set(score_metrics) != {
                    "chinese_prose", "character_consistency", "npc_initiative",
                    "player_agency", "narrative_continuity", "rule_fidelity",
                }
                or payload.get("decision_agreements", 0)
                   + payload.get("decision_disagreements", 0)
                   != payload.get("comparable_decision_cases")
                or payload.get("reviewer_a_two_independent_blinded_reviews_met") is not False
                or payload.get("reviewer_b2_execution_attestation_self_reported") is not True
                or payload.get("reviewer_b2_independence_verified") is not False
                or payload.get("cryptographic_independence_proven") is not False
                or payload.get("evidence_tier") != "OWNER_RETURNED_SAFE_AGGREGATE"
                or payload.get("quality_v1_admitted") is not False
                or payload.get("training_authorized") is not False
                or payload.get("gpu_started") is not False
                or payload.get("r50_accessed") is not False):
            raise ManifestError("REVIEW_RECONCILIATION_EVENT_INVALID")
    elif event["event_type"] == "GOLD72_OWNER_RESOLUTION":
        payload = event["payload"]
        required = {
            "resolution_type", "source_receipt_sha256", "source_pins", "candidate_count",
            "a_b2_pair_counts", "reviewer_a_decisions", "reviewer_b2_decisions",
            "reviewer_c_decisions", "owner_decisions", "resolution_matrix",
            "owner_evidence_reference_count", "execution_record_available",
            "execution_metadata_sha256", "execution_attestation_complete",
            "reviewer_c_independence_verified", "cryptographic_independence_proven",
            "evidence_tier", "quality_v1_admitted", "training_authorized",
            "gpu_started", "r50_accessed",
        }
        pin_keys = {
            "package_safe_sha256", "receipt_template_sha256", "blind_input_sha256",
            "instructions_sha256", "owner_map_sha256", "result_sha256",
            "results_only_safe_sha256", "resolution_template_sha256",
            "owner_resolution_sha256",
        }
        expected_pairs = {
            "CASE_LEVEL_SCORED_PASS__B2_HOLD": 5,
            "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
            "EXPLICIT_HOLD__B2_PASS": 30,
            "EXPLICIT_HOLD__B2_REJECT": 3,
        }
        def valid_decisions(value):
            return (
                isinstance(value, dict)
                and set(value).issubset({"PASS", "HOLD", "REJECT"})
                and all(type(count) is int and count >= 0 for count in value.values())
                and sum(value.values()) == 40
            )
        matrix = payload.get("resolution_matrix")
        matrix_pattern = re.compile(
            r"A_(PASS|HOLD|REJECT)__B2_(PASS|HOLD|REJECT)__C_(PASS|HOLD|REJECT)__OWNER_(PASS|HOLD|REJECT)"
        )
        matrix_valid = (
            isinstance(matrix, dict) and bool(matrix)
            and all(isinstance(key, str) and matrix_pattern.fullmatch(key)
                    and type(count) is int and count > 0 for key, count in matrix.items())
            and sum(matrix.values()) == 40
        )
        maps_valid = all(valid_decisions(payload.get(key)) for key in (
            "reviewer_a_decisions", "reviewer_b2_decisions",
            "reviewer_c_decisions", "owner_decisions",
        ))
        marginals_valid = False
        if matrix_valid and maps_valid:
            a_counts, b_counts, c_counts, owner_counts = {}, {}, {}, {}
            for key, count in matrix.items():
                match = matrix_pattern.fullmatch(key)
                a, b, c, owner = match.groups()
                for target, decision in (
                    (a_counts, a), (b_counts, b), (c_counts, c), (owner_counts, owner)
                ):
                    target[decision] = target.get(decision, 0) + count
            marginals_valid = all(
                {key: value.get(key, 0) for key in ("PASS", "HOLD", "REJECT")}
                == {key: payload[target].get(key, 0) for key in ("PASS", "HOLD", "REJECT")}
                for value, target in (
                    (a_counts, "reviewer_a_decisions"),
                    (b_counts, "reviewer_b2_decisions"),
                    (c_counts, "reviewer_c_decisions"),
                    (owner_counts, "owner_decisions"),
                )
            )
        metadata_sha = payload.get("execution_metadata_sha256")
        if (
            event["batch_id"] != "gold72"
            or set(payload) != required
            or payload.get("resolution_type") != "GOLD72_REVIEWER_C_OWNER_RESOLUTION"
            or not isinstance(payload.get("source_receipt_sha256"), str)
            or not HEX64.fullmatch(payload["source_receipt_sha256"])
            or not isinstance(payload.get("source_pins"), dict)
            or set(payload["source_pins"]) != pin_keys
            or any(not isinstance(value, str) or not HEX64.fullmatch(value)
                   for value in payload["source_pins"].values())
            or payload.get("candidate_count") != 40
            or payload.get("a_b2_pair_counts") != expected_pairs
            or not maps_valid
            or payload.get("reviewer_c_decisions") != {"PASS": 38, "HOLD": 1, "REJECT": 1}
            or not matrix_valid or not marginals_valid
            or type(payload.get("owner_evidence_reference_count")) is not int
            or payload["owner_evidence_reference_count"] < 40
            or payload.get("execution_record_available") is not False
            or (metadata_sha is not None and
                (not isinstance(metadata_sha, str) or not HEX64.fullmatch(metadata_sha)))
            or payload.get("execution_attestation_complete") is not False
            or payload.get("reviewer_c_independence_verified") is not False
            or payload.get("cryptographic_independence_proven") is not False
            or payload.get("evidence_tier") != "OWNER_RETURNED_SAFE_AGGREGATE"
            or payload.get("quality_v1_admitted") is not False
            or payload.get("training_authorized") is not False
            or payload.get("gpu_started") is not False
            or payload.get("r50_accessed") is not False
        ):
            raise ManifestError("GOLD72_OWNER_RESOLUTION_EVENT_INVALID")
    return event


def load_events(path):
    if path.is_symlink() or not path.is_file():
        raise ManifestError("MANIFEST_NOT_REGULAR_FILE")
    events = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                raise ManifestError("MANIFEST_BLANK_LINE")
            events.append(validate_event(json.loads(line, object_pairs_hook=_pairs)))
    return events


def make_event(batch_id, event_type, payload, recorded_at):
    return {"schema": SCHEMA, "event_id": str(uuid.uuid4()), "batch_id": batch_id,
            "event_type": event_type, "recorded_at": recorded_at, "payload": payload}


def append_events(path, events, repo_root):
    if not events:
        raise ManifestError("NO_EVENTS_TO_APPEND")
    parent = path.parent.absolute()
    repo = repo_root.resolve(strict=True)
    try:
        parent.relative_to(repo)
    except ValueError:
        pass
    else:
        raise ManifestError("PRIVATE_MANIFEST_MUST_BE_OUTSIDE_REPOSITORY")
    parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if any(p.is_symlink() for p in (parent, *parent.parents)):
        raise ManifestError("PRIVATE_PATH_SYMLINK")
    if parent.resolve().stat().st_mode & 0o077:
        raise ManifestError("PRIVATE_PARENT_PERMISSIONS_TOO_OPEN")
    checked = [validate_event(x) for x in events]
    ids = [x["event_id"] for x in checked]
    if len(ids) != len(set(ids)):
        raise ManifestError("DUPLICATE_EVENT_ID")
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ManifestError("MANIFEST_NOT_REGULAR_FILE")
        os.fchmod(fd, 0o600)
        os.lseek(fd, 0, os.SEEK_SET)
        raw = b""
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            raw += chunk
        old = [validate_event(json.loads(line, object_pairs_hook=_pairs))
               for line in raw.decode("utf-8").splitlines() if line]
        old_ids = {x["event_id"] for x in old}
        if old_ids.intersection(ids):
            raise ManifestError("EVENT_ID_ALREADY_EXISTS")
        targets = {}
        for event in old + checked:
            payload = event["payload"]
            case = payload.get("case_id") or payload.get("case_ref")
            digest = payload.get("target_sha256")
            if case and digest:
                key = (event["batch_id"], case)
                prior = targets.setdefault(key, digest)
                if prior != digest:
                    raise ManifestError("CASE_TARGET_HASH_CHANGED")
        for event in checked:
            data = (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
            view = memoryview(data)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise ManifestError("MANIFEST_APPEND_FAILED")
                view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return len(checked)


PUBLIC_BATCHES = {"gold87", "gold108", "gold192", "gold195", "gold72"}
PUBLIC_DECISIONS = {"PASS", "PASS_ONLY", "HOLD", "REJECT", "ACCEPT", "UNKNOWN", "NOT_RUN"}
PUBLIC_TIERS = {"OWNER_RETURNED_SAFE_AGGREGATE", "OWNER_PRIVATE_SOURCE_IMPORT",
                "OWNER_LOCAL_FROZEN_BYTES__NOT_ALIAS_VERIFIED"}


def public_batch(value):
    return value if value in PUBLIC_BATCHES else "OTHER_PRIVATE_BATCHES"


def validate_manifest(events):
    ids = set()
    pins = {}
    by_batch, cases = defaultdict(Counter), defaultdict(set)
    for event in events:
        validate_event(event)
        if event["event_id"] in ids:
            raise ManifestError("DUPLICATE_EVENT_ID")
        ids.add(event["event_id"])
        batch = public_batch(event["batch_id"])
        by_batch[batch][event["event_type"]] += 1
        payload = event["payload"]
        case = payload.get("case_id") or payload.get("case_ref")
        digest = payload.get("target_sha256")
        if case:
            cases[batch].add((event["batch_id"], case))
            if digest:
                key = (event["batch_id"], case)
                if key in pins and pins[key] != digest:
                    raise ManifestError("CASE_TARGET_HASH_CHANGED")
                pins[key] = digest
    return {
        "valid": True,
        "event_count": len(events),
        "batch_count": len({event["batch_id"] for event in events}),
        "case_counts": {k: len(v) for k, v in sorted(cases.items())},
        "event_counts": {k: dict(sorted(v.items())) for k, v in sorted(by_batch.items())},
    }


def safe_report(events):
    summary = validate_manifest(events)
    decisions, tiers, ai_arbitrations = Counter(), Counter(), Counter()
    reconciliations = defaultdict(list)
    for event in events:
        if event["event_type"] == "REVIEW_RECONCILIATION":
            reconciliations[event["batch_id"]].append(event["payload"])
        payload = event["payload"]
        decision = payload.get("decision")
        if event["event_type"] == "AI_ARBITRATION":
            if decision is not None:
                ai_arbitrations[decision if decision in {"PASS", "HOLD"} else "OTHER"] += 1
        elif decision is not None:
            decisions[decision if decision in PUBLIC_DECISIONS else "OTHER"] += 1
        tier = payload.get("evidence_tier")
        if tier is not None:
            tiers[tier if tier in PUBLIC_TIERS else "OTHER"] += 1
    return {
        "schema": "storyforge_gold_quality_safe_aggregate_v1",
        "status": "MANIFEST_VALID__ADMISSION_NOT_IMPLIED",
        **summary,
        "decision_counts": dict(sorted(decisions.items())),
        "ai_arbitration_decision_counts": dict(sorted(ai_arbitrations.items())),
        "exposure_evidence_tiers": dict(sorted(tiers.items())),
        "review_reconciliation_summary": {
            batch: {
                "receipt_count": len(payloads),
                "candidate_count": sum(item["candidate_count"] for item in payloads),
                "comparable_decision_cases": sum(item["comparable_decision_cases"] for item in payloads),
                "decision_agreements": sum(item["decision_agreements"] for item in payloads),
                "decision_disagreements": sum(item["decision_disagreements"] for item in payloads),
                "score_comparable_cases": sum(item["score_comparable_cases"] for item in payloads),
                "reviewer_a_evidence_granularity": payloads[0]["reviewer_a_evidence_granularity"],
                "reviewer_b2_decisions": payloads[0]["reviewer_b2_decisions"],
                "a_b2_pair_counts": payloads[0]["a_b2_pair_counts"],
                "score_comparison_by_dimension": payloads[0]["score_comparison_by_dimension"],
                "reviewer_b2_independence_verified": all(
                    item["reviewer_b2_independence_verified"] for item in payloads
                ),
                "quality_v1_admitted": 0,
                "training_authorized": False,
            }
            for batch, payloads in sorted(reconciliations.items())
        },
        "gold72_owner_resolution_summary": {
            batch: {
                "receipt_count": len(payloads),
                "candidate_count": sum(item["candidate_count"] for item in payloads),
                "reviewer_a_decisions": payloads[-1]["reviewer_a_decisions"],
                "reviewer_b2_decisions": payloads[-1]["reviewer_b2_decisions"],
                "reviewer_c_decisions": payloads[-1]["reviewer_c_decisions"],
                "owner_decisions": payloads[-1]["owner_decisions"],
                "resolution_matrix": payloads[-1]["resolution_matrix"],
                "owner_evidence_reference_count": sum(
                    item["owner_evidence_reference_count"] for item in payloads
                ),
                "execution_record_available": False,
                "reviewer_c_independence_verified": False,
                "quality_v1_admitted": 0,
                "training_authorized": False,
            }
            for batch, payloads in sorted(
                {
                    batch: [event["payload"] for event in events
                            if event["batch_id"] == batch and event["event_type"] == "GOLD72_OWNER_RESOLUTION"]
                    for batch in {event["batch_id"] for event in events
                                  if event["event_type"] == "GOLD72_OWNER_RESOLUTION"}
                }.items()
            )
        },
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
