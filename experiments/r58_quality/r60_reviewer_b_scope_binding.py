"""Owner-only source binding audit for canonical Gold192 Reviewer B evidence.

This proves the blind input, owner-only ID map, canonical Gold192 source bundle,
and selected Reviewer B result refer to the same 192 target cases. It does NOT
prove the B review ran in a separate AI session or that A evidence was unseen.
Only aggregate SAFE output is emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

B_BLIND_INPUT_SHA256 = "39faf3c5980616b1235b511fec54921fa4f87d0bf3ca7b5b7258c13f969efdb5"
B_ID_MAP_SHA256 = "27bce4d9842768aa5cbb7febd963f5247540d6c5806466647802e9a9a2fc6a30"
B_INSTRUCTIONS_SHA256 = "9ba2a6fa9ef08c50f65a8dca2a90277521c65f110fd4ab339309e44c29330254"
B_RESULTS_SHA256 = "bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8"
GOLD192_SOURCE_SHA256 = "ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e"

BLIND_PACKET_SCHEMA = "r58_gold192_reviewer_b_blind_story_packet_v1"
ID_MAP_SCHEMA = "r58_gold192_reviewer_b_private_id_map_v1"
SOURCE_PACKET_SCHEMA = "r58_gold192_story_semantic_review_packet_private_v1"
RESULT_SCHEMA = "r58_gold192_reviewer_b_results_v1"
SCORE_FIELDS = {
    "chinese_prose", "character_consistency", "npc_initiative",
    "player_agency", "narrative_continuity", "rule_fidelity",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class AuditHold(ValueError):
    """Fail-closed source or identity mismatch."""


def _read(path: Path, limit: int = 160 * 1024 * 1024) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AuditHold("INPUT_MISSING_OR_SYMLINK")
    raw = path.read_bytes()
    if len(raw) > limit:
        raise AuditHold("INPUT_SIZE_LIMIT")
    return raw


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise AuditHold("JSON_OBJECT_REQUIRED")
    return value


def _jsonl(raw: bytes) -> list[dict[str, Any]]:
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise AuditHold("JSONL_OBJECT_REQUIRED")
        rows.append(value)
    return rows


def _flatten_packets(packets: list[dict[str, Any]], schema: str, reviewer: str | None = None):
    if len(packets) != 13:
        raise AuditHold("STORY_PACKET_COUNT_INVALID")
    story_ids: set[str] = set()
    cases: list[tuple[str, dict[str, Any]]] = []
    for packet in packets:
        if packet.get("schema") != schema:
            raise AuditHold("STORY_PACKET_SCHEMA_INVALID")
        if reviewer is not None and packet.get("reviewer") != reviewer:
            raise AuditHold("REVIEWER_LABEL_INVALID")
        story_uuid = packet.get("story_uuid")
        if schema == SOURCE_PACKET_SCHEMA:
            if not isinstance(story_uuid, str) or not story_uuid or story_uuid in story_ids:
                raise AuditHold("SOURCE_STORY_ID_INVALID")
            story_ids.add(story_uuid)
        else:
            packet_id = packet.get("blind_story_packet_id")
            if not isinstance(packet_id, str) or not packet_id or packet_id in story_ids:
                raise AuditHold("BLIND_STORY_PACKET_ID_INVALID")
            story_ids.add(packet_id)
        packet_cases = packet.get("cases")
        if not isinstance(packet_cases, list):
            raise AuditHold("PACKET_CASES_INVALID")
        for case in packet_cases:
            if not isinstance(case, dict):
                raise AuditHold("PACKET_CASE_INVALID")
            cases.append((story_uuid if schema == SOURCE_PACKET_SCHEMA else packet_id, case))
    if len(cases) != 192:
        raise AuditHold("PACKET_CASE_COUNT_INVALID")
    return cases


def _key_names(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _key_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from _key_names(child)


def _unique(rows: list[dict[str, Any]], field: str, reason: str):
    result = {}
    for row in rows:
        value = row.get(field)
        if not isinstance(value, str) or not value or value in result:
            raise AuditHold(reason)
        result[value] = row
    return result


def _valid_scores(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == SCORE_FIELDS
        and all(type(score) is int and 1 <= score <= 5 for score in value.values())
    )


def audit(blind_raw: bytes, map_raw: bytes, instructions_raw: bytes,
          source_raw: bytes, result_raw: bytes) -> dict[str, Any]:
    pins = {
        "reviewer_b_blind_input_sha256": (blind_raw, B_BLIND_INPUT_SHA256),
        "reviewer_b_id_map_sha256": (map_raw, B_ID_MAP_SHA256),
        "reviewer_b_instructions_sha256": (instructions_raw, B_INSTRUCTIONS_SHA256),
        "reviewer_b_results_sha256": (result_raw, B_RESULTS_SHA256),
        "gold192_source_bundle_sha256": (source_raw, GOLD192_SOURCE_SHA256),
    }
    for reason_field, (raw, expected) in pins.items():
        if _sha(raw) != expected:
            raise AuditHold(reason_field.upper() + "_PIN_MISMATCH")

    blind_packets = _jsonl(blind_raw)
    source_packets = _jsonl(source_raw)
    blind_cases = _flatten_packets(blind_packets, BLIND_PACKET_SCHEMA, "B")
    source_cases = _flatten_packets(source_packets, SOURCE_PACKET_SCHEMA)

    forbidden = {
        "original_case_id", "case_id", "cohort", "reviewer_a",
        "reviewer_a_decision", "reviewer_a_scores", "gold87", "gold108",
    }
    blind_keys = set(_key_names(blind_packets))
    if blind_keys & forbidden:
        raise AuditHold("BLIND_INPUT_OWNER_OR_REVIEWER_A_DATA_LEAK")

    blind_rows = [case for _, case in blind_cases]
    source_rows = [case for _, case in source_cases]
    blind_idx = _unique(blind_rows, "blind_case_id", "BLIND_ID_MISSING_OR_DUPLICATE")
    blind_sha_idx = _unique(blind_rows, "target_sha256", "BLIND_TARGET_SHA_MISSING_OR_DUPLICATE")
    source_id_idx = _unique(source_rows, "case_id", "SOURCE_CASE_ID_MISSING_OR_DUPLICATE")
    _unique(source_rows, "target_sha256", "SOURCE_TARGET_SHA_MISSING_OR_DUPLICATE")

    id_map = _json(map_raw)
    if id_map.get("schema") != ID_MAP_SCHEMA or id_map.get("reviewer") != "B":
        raise AuditHold("OWNER_ID_MAP_SCHEMA_INVALID")
    map_rows = id_map.get("mapping")
    if not isinstance(map_rows, list) or len(map_rows) != 192:
        raise AuditHold("OWNER_ID_MAP_COUNT_INVALID")
    map_blind_idx = _unique(map_rows, "blind_case_id", "OWNER_MAP_BLIND_ID_INVALID")
    map_sha_idx = _unique(map_rows, "target_sha256", "OWNER_MAP_TARGET_SHA_INVALID")

    if set(blind_idx) != set(map_blind_idx) or set(blind_sha_idx) != set(map_sha_idx):
        raise AuditHold("BLIND_INPUT_OWNER_MAP_SET_MISMATCH")

    input_map_matches = 0
    map_source_matches = 0
    for blind_id, mapping in map_blind_idx.items():
        blind = blind_idx[blind_id]
        digest = mapping.get("target_sha256")
        if blind.get("target_sha256") != digest:
            raise AuditHold("BLIND_INPUT_OWNER_MAP_TARGET_MISMATCH")
        input_map_matches += 1

        original_id = mapping.get("original_case_id")
        original_story_uuid = mapping.get("original_story_uuid")
        source = source_id_idx.get(original_id)
        if source is None:
            raise AuditHold("OWNER_MAP_SOURCE_CASE_ID_MISSING")
        source_packet_story_uuid = next(
            story_uuid for story_uuid, case in source_cases if case is source
        )
        if (source.get("target_sha256") != digest
                or source_packet_story_uuid != original_story_uuid):
            raise AuditHold("OWNER_MAP_SOURCE_BINDING_MISMATCH")
        map_source_matches += 1

    result = _json(result_raw)
    if (result.get("schema") != RESULT_SCHEMA or result.get("reviewer") != "B"
            or result.get("status") != "REVIEW_COMPLETE"):
        raise AuditHold("CANONICAL_B_RESULT_SCHEMA_INVALID")
    result_rows = result.get("cases")
    if not isinstance(result_rows, list) or len(result_rows) != 192:
        raise AuditHold("B_RESULT_COUNT_INVALID")
    result_id_idx = _unique(result_rows, "blind_case_id", "B_RESULT_BLIND_ID_INVALID")
    result_sha_idx = _unique(result_rows, "target_sha256", "B_RESULT_TARGET_SHA_INVALID")
    if set(result_id_idx) != set(map_blind_idx) or set(result_sha_idx) != set(map_sha_idx):
        raise AuditHold("B_RESULT_OWNER_MAP_SET_MISMATCH")

    result_map_matches = 0
    for blind_id, mapping in map_blind_idx.items():
        case = result_id_idx[blind_id]
        if case.get("target_sha256") != mapping.get("target_sha256"):
            raise AuditHold("B_RESULT_OWNER_MAP_TARGET_MISMATCH")
        if (not _valid_scores(case.get("scores_1_to_5"))
                or not isinstance(case.get("severe_flags"), list)
                or not isinstance(case.get("evidence_summary"), str)
                or not case.get("evidence_summary")):
            raise AuditHold("B_RESULT_CASE_EVIDENCE_INCOMPLETE")
        result_map_matches += 1

    actual_counts = dict(sorted(Counter(row.get("decision") for row in result_rows).items()))
    expected_counts = {"HOLD": 12, "PASS": 178, "REJECT": 2}
    if actual_counts != expected_counts or result.get("counts") != {
        "PASS": 178, "HOLD": 12, "REJECT": 2
    }:
        raise AuditHold("B_RESULT_DECISION_COUNTS_INVALID")

    return {
        "schema": "storyforge-r60-reviewer-b-scope-binding-safe-v1",
        "status": "REVIEWER_B_SCOPE_BINDING_VERIFIED__INDEPENDENCE_PROVENANCE_HOLD",
        "reviewer_b_blind_story_packets": len(blind_packets),
        "gold192_source_story_packets": len(source_packets),
        "reviewer_b_input_cases": len(blind_idx),
        "owner_id_map_cases": len(map_blind_idx),
        "reviewer_b_result_cases": len(result_id_idx),
        "reviewer_b_input_to_owner_map_matches": input_map_matches,
        "owner_id_map_to_gold192_source_matches": map_source_matches,
        "reviewer_b_result_to_owner_map_matches": result_map_matches,
        "reviewer_b_blind_input_contains_no_owner_case_ids": True,
        "reviewer_b_blind_input_contains_no_reviewer_a_or_cohort_labels": True,
        "reviewer_b_result_decisions": actual_counts,
        "reviewer_b_result_scores_complete": 192,
        "reviewer_b_source_binding_verified": (
            input_map_matches == map_source_matches == result_map_matches == 192
        ),
        "reviewer_b_separate_session_execution_provenance_verified": False,
        "reviewer_b_independence_verified": False,
        "reviewer_b_independence_reason": (
            "NO_SEPARATE_SESSION_TASK_MODEL_OR_TRANSCRIPT_EVIDENCE"
        ),
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit canonical Reviewer B source binding")
    parser.add_argument("--reviewer-b-blind-jsonl", required=True, type=Path)
    parser.add_argument("--reviewer-b-id-map-json", required=True, type=Path)
    parser.add_argument("--reviewer-b-instructions", required=True, type=Path)
    parser.add_argument("--gold192-source-jsonl", required=True, type=Path)
    parser.add_argument("--reviewer-b-results-json", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(
            _read(args.reviewer_b_blind_jsonl),
            _read(args.reviewer_b_id_map_json),
            _read(args.reviewer_b_instructions, 2 * 1024 * 1024),
            _read(args.gold192_source_jsonl),
            _read(args.reviewer_b_results_json, 16 * 1024 * 1024),
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (AuditHold, OSError, ValueError, TypeError, KeyError, StopIteration) as exc:
        reason = str(exc) if isinstance(exc, AuditHold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": "storyforge-r60-reviewer-b-scope-binding-safe-v1",
            "status": "REVIEWER_B_SCOPE_BINDING_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
