"""Fail-closed Owner resolution and aggregate-only import for Gold72 A/B2/C disagreements.

Private case-level decisions stay in the Owner workspace. Only a pinned,
aggregate SAFE receipt may be appended to the shared Gold Quality manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .manifest import ManifestError, append_events, load_events, make_event

SAFE_SCHEMA = "r60_gold72_owner_resolution_safe_v1"
SAFE_STATUS = "GOLD72_OWNER_RESOLUTION_VALID__AGGREGATE_IMPORT_READY"
RESOLUTION_SCHEMA = "r60_gold72_owner_disagreement_resolution_private_v1"
RESOLUTION_TEMPLATE_SCHEMA = RESOLUTION_SCHEMA
RESULT_SCHEMA = "r60_gold72_reviewer_c_results_v1"
MAP_SCHEMA = "r60_gold72_reviewer_c_private_id_map_v1"
BLIND_SCHEMA = "r60_gold72_reviewer_c_blind_story_packet_v1"
PACKAGE_SCHEMA = "r60_gold72_reviewer_c_disagreement_package_safe_v1"
PACKAGE_STATUS = "REVIEWER_C_DISAGREEMENT_PACKAGE_BUILT__AWAITING_INDEPENDENT_REVIEW"
RECEIPT_SCHEMA = "r60_gold72_reviewer_c_execution_receipt_v1"
EVENT_TYPE = "GOLD72_OWNER_RESOLUTION"
RESOLUTION_TYPE = "GOLD72_REVIEWER_C_OWNER_RESOLUTION"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCORE_FLOORS = {
    "chinese_prose": 4,
    "character_consistency": 4,
    "npc_initiative": 3,
    "player_agency": 4,
    "narrative_continuity": 4,
    "rule_fidelity": 4,
}
DECISIONS = {"PASS", "HOLD", "REJECT"}
OWNER_BASES = {
    "A_EVIDENCE_CONTROLS",
    "B2_EVIDENCE_CONTROLS",
    "C_EVIDENCE_CONTROLS",
    "CROSS_REVIEWER_SYNTHESIS",
    "SOURCE_RECHECK",
    "INSUFFICIENT_EVIDENCE_HOLD",
}
EXPECTED_PAIRS = {
    "CASE_LEVEL_SCORED_PASS__B2_HOLD": 5,
    "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
    "EXPLICIT_HOLD__B2_PASS": 30,
    "EXPLICIT_HOLD__B2_REJECT": 3,
}
RESULT_ONLY_FIELDS = {
    "schema", "status", "candidate_count", "case_bindings_valid",
    "decision_counts", "package_pins_rechecked", "execution_metadata_sha256",
    "execution_record_available", "execution_attestation_complete",
    "reviewer_c_independence_verified", "cryptographic_independence_proven",
    "quality_v1_admitted", "training_authorized", "gpu_started", "r50_accessed",
    "private_values_emitted",
}
SOURCE_PIN_KEYS = {
    "package_safe_sha256", "receipt_template_sha256", "blind_input_sha256",
    "instructions_sha256", "owner_map_sha256", "result_sha256",
    "results_only_safe_sha256", "resolution_template_sha256",
}
SAFE_FIELDS = {
    "schema", "status", "resolution_type", "candidate_count", "source_pins",
    "a_b2_pair_counts", "reviewer_a_decisions", "reviewer_b2_decisions",
    "reviewer_c_decisions", "owner_decisions", "resolution_matrix",
    "owner_evidence_reference_count", "execution_record_available",
    "execution_metadata_sha256", "execution_attestation_complete",
    "reviewer_c_independence_verified", "cryptographic_independence_proven",
    "quality_v1_admitted", "training_authorized", "gpu_started", "r50_accessed",
    "private_values_emitted",
}


class OwnerResolutionHold(ManifestError):
    """A fixed, non-sensitive reason code."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise OwnerResolutionHold("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _json(raw: bytes, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise OwnerResolutionHold(reason) from None
    if not isinstance(value, dict):
        raise OwnerResolutionHold(reason)
    return value


def _jsonl(raw: bytes, reason: str) -> list[dict[str, Any]]:
    try:
        rows = [
            json.loads(line, object_pairs_hook=_pairs)
            for line in raw.decode("utf-8").splitlines() if line.strip()
        ]
    except (UnicodeError, json.JSONDecodeError):
        raise OwnerResolutionHold(reason) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise OwnerResolutionHold(reason)
    return rows


def _read(path: Path, repo: Path, limit: int, *, private: bool = True) -> bytes:
    if not path.is_absolute() or any(parent.is_symlink() for parent in (path, *path.parents)):
        raise OwnerResolutionHold("INPUT_PATH_INVALID")
    try:
        resolved = path.resolve(strict=True)
        info = path.lstat()
        if resolved == repo or repo in resolved.parents:
            if private:
                raise OwnerResolutionHold("PRIVATE_INPUT_INSIDE_REPOSITORY")
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            raise OwnerResolutionHold("INPUT_NOT_REGULAR_OR_SIZE_INVALID")
        if private:
            if stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
                raise OwnerResolutionHold("PRIVATE_INPUT_PERMISSIONS_INVALID")
            if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
                raise OwnerResolutionHold("PRIVATE_INPUT_PARENT_PERMISSIONS_INVALID")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise OwnerResolutionHold("INPUT_CHANGED_DURING_OPEN")
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
                raise OwnerResolutionHold("INPUT_NOT_REGULAR_OR_SIZE_INVALID")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        if (not 0 < len(raw) <= limit
                or (after.st_size, after.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns)):
            raise OwnerResolutionHold("INPUT_CHANGED_DURING_READ")
        return raw
    except FileNotFoundError:
        raise OwnerResolutionHold("INPUT_NOT_REGULAR_OR_SIZE_INVALID") from None


def _write_create_only(path: Path, raw: bytes, repo: Path) -> None:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise OwnerResolutionHold("OUTPUT_PATH_INVALID_OR_EXISTS")
    parent = path.parent
    if (not parent.is_dir() or parent.is_symlink()
            or stat.S_IMODE(parent.stat().st_mode) != 0o700):
        raise OwnerResolutionHold("OUTPUT_PARENT_NOT_PRIVATE")
    if any(p.is_symlink() for p in (parent, *parent.parents)):
        raise OwnerResolutionHold("OUTPUT_PATH_SYMLINK")
    resolved = parent.resolve(strict=True)
    if resolved == repo or repo in resolved.parents:
        raise OwnerResolutionHold("PRIVATE_OUTPUT_INSIDE_REPOSITORY")
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _counts(value: Any, reason: str) -> dict[str, int]:
    if (not isinstance(value, dict) or not value
            or set(value) - DECISIONS
            or any(type(v) is not int or v < 0 for v in value.values())):
        raise OwnerResolutionHold(reason)
    return {key: value.get(key, 0) for key in ("PASS", "HOLD", "REJECT")}


def _unique(rows: list[dict[str, Any]], key: str, reason: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise OwnerResolutionHold(reason)
        result[value] = row
    return result


def _load_inputs(args: Any) -> dict[str, Any]:
    repo = args.repo_root.resolve(strict=True)
    limits = {
        "package_safe": 256 * 1024,
        "receipt_template": 2 * 1024 * 1024,
        "blind_input": 160 * 1024 * 1024,
        "instructions": 128 * 1024,
        "owner_map": 8 * 1024 * 1024,
        "result": 16 * 1024 * 1024,
        "results_only_safe": 256 * 1024,
        "resolution_template": 8 * 1024 * 1024,
    }
    raw = {}
    for key, limit in limits.items():
        path = getattr(args, key)
        raw[key] = _read(path, repo, limit, private=(key != "instructions"))
    values = {
        key: _json(raw[key], key.upper() + "_JSON_INVALID")
        for key in (
            "package_safe", "receipt_template", "owner_map", "result",
            "results_only_safe", "resolution_template",
        )
    }
    values["blind_packets"] = _jsonl(raw["blind_input"], "BLIND_INPUT_JSONL_INVALID")
    values["raw"] = raw
    values["repo"] = repo
    return values


def _validate_sources(values: dict[str, Any]) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict], dict]:
    raw = values["raw"]
    package = values["package_safe"]
    template = values["receipt_template"]
    owner = values["owner_map"]
    result = values["result"]
    result_safe = values["results_only_safe"]
    resolution_template = values["resolution_template"]

    if (package.get("schema") != PACKAGE_SCHEMA or package.get("status") != PACKAGE_STATUS
            or package.get("candidate_count") != 40):
        raise OwnerResolutionHold("PACKAGE_SAFE_INVALID")
    pins = {
        "blind_input": "blind_input_sha256",
        "instructions": "instructions_sha256",
        "owner_map": "owner_map_sha256",
        "receipt_template": "execution_receipt_template_sha256",
        "resolution_template": "owner_resolution_template_sha256",
    }
    for key, field in pins.items():
        if package.get(field) != _sha(raw[key]):
            raise OwnerResolutionHold("PACKAGE_PIN_MISMATCH")

    if (template.get("schema") != RECEIPT_SCHEMA or template.get("reviewer") != "C"
            or template.get("status") != "PENDING_INDEPENDENT_REVIEW_EXECUTION"
            or template.get("blind_input_sha256") != _sha(raw["blind_input"])
            or template.get("instructions_sha256") != _sha(raw["instructions"])
            or not isinstance(template.get("attestations"), dict)
            or any(value is not None for value in template["attestations"].values())
            or not isinstance(template.get("owner_verification"), dict)
            or any(value is not False for value in template["owner_verification"].values())):
        raise OwnerResolutionHold("RECEIPT_TEMPLATE_INVALID")

    blind_rows = []
    for packet in values["blind_packets"]:
        if packet.get("schema") != BLIND_SCHEMA or packet.get("reviewer") != "C":
            raise OwnerResolutionHold("BLIND_PACKET_SCHEMA_INVALID")
        cases = packet.get("cases")
        if not isinstance(cases, list) or not cases or any(not isinstance(row, dict) for row in cases):
            raise OwnerResolutionHold("BLIND_PACKET_CASES_INVALID")
        blind_rows.extend(cases)
    if len(blind_rows) != 40:
        raise OwnerResolutionHold("BLIND_CASE_COUNT_INVALID")
    blind_idx = _unique(blind_rows, "blind_case_id", "BLIND_ID_DUPLICATE")
    blind_sha = _unique(blind_rows, "target_sha256", "BLIND_TARGET_SHA_DUPLICATE")

    if (owner.get("schema") != MAP_SCHEMA or owner.get("reviewer") != "C"
            or owner.get("status") != "OWNER_ONLY_PRIVATE_MAPPING"
            or owner.get("candidate_count") != 40):
        raise OwnerResolutionHold("OWNER_MAP_SCHEMA_INVALID")
    owner_rows = owner.get("mapping")
    if not isinstance(owner_rows, list) or len(owner_rows) != 40:
        raise OwnerResolutionHold("OWNER_MAP_COUNT_INVALID")
    owner_idx = _unique(owner_rows, "blind_case_id", "OWNER_MAP_BLIND_ID_DUPLICATE")
    owner_sha = _unique(owner_rows, "target_sha256", "OWNER_MAP_TARGET_SHA_DUPLICATE")
    if set(owner_idx) != set(blind_idx) or set(owner_sha) != set(blind_sha):
        raise OwnerResolutionHold("BLIND_OWNER_MAP_SET_MISMATCH")
    expected_map_fields = {
        "blind_case_id", "original_case_id", "original_story_uuid", "target_sha256",
        "reviewer_a_decision", "reviewer_b2_decision", "reviewer_a_evidence_class",
        "disagreement_type", "prior_b2_blind_case_id",
    }
    pair_counts: Counter[str] = Counter()
    for blind_id, row in owner_idx.items():
        a_class = row.get("reviewer_a_evidence_class")
        a_decision = row.get("reviewer_a_decision")
        b_decision = row.get("reviewer_b2_decision")
        expected_a = {
            "CASE_LEVEL_SCORED_PASS": "PASS",
            "EXPLICIT_HOLD": "HOLD",
        }.get(a_class)
        pair = f"{a_class}__B2_{b_decision}"
        if (set(row) != expected_map_fields
                or row.get("target_sha256") != blind_idx[blind_id].get("target_sha256")
                or not isinstance(row.get("original_case_id"), str) or not row["original_case_id"]
                or not isinstance(row.get("original_story_uuid"), str) or not row["original_story_uuid"]
                or a_decision not in DECISIONS or b_decision not in DECISIONS
                or expected_a != a_decision
                or row.get("disagreement_type") != pair
                or not isinstance(row.get("prior_b2_blind_case_id"), str)
                or not row["prior_b2_blind_case_id"]):
            raise OwnerResolutionHold("OWNER_MAP_CASE_BINDING_INVALID")
        pair_counts[pair] += 1
    if dict(sorted(pair_counts.items())) != dict(sorted(EXPECTED_PAIRS.items())):
        raise OwnerResolutionHold("OWNER_MAP_DISAGREEMENT_DISTRIBUTION_INVALID")

    if (result.get("schema") != RESULT_SCHEMA or result.get("reviewer") != "C"
            or result.get("status") != "REVIEW_COMPLETE"):
        raise OwnerResolutionHold("RESULT_SCHEMA_INVALID")
    result_rows = result.get("cases")
    if not isinstance(result_rows, list) or len(result_rows) != 40:
        raise OwnerResolutionHold("RESULT_CASE_COUNT_INVALID")
    result_idx = _unique(result_rows, "blind_case_id", "RESULT_BLIND_ID_DUPLICATE")
    result_sha = _unique(result_rows, "target_sha256", "RESULT_TARGET_SHA_DUPLICATE")
    if set(result_idx) != set(owner_idx) or set(result_sha) != set(owner_sha):
        raise OwnerResolutionHold("RESULT_OWNER_MAP_SET_MISMATCH")
    result_counts: Counter[str] = Counter()
    for blind_id, row in result_idx.items():
        if row.get("target_sha256") != owner_idx[blind_id].get("target_sha256"):
            raise OwnerResolutionHold("RESULT_TARGET_SHA_MISMATCH")
        decision = row.get("decision")
        scores = row.get("scores_1_to_5")
        flags, summary = row.get("severe_flags"), row.get("evidence_summary")
        if decision not in DECISIONS:
            raise OwnerResolutionHold("RESULT_DECISION_INVALID")
        if (not isinstance(scores, dict) or set(scores) != set(SCORE_FLOORS)
                or any(type(v) is not int or not 1 <= v <= 5 for v in scores.values())):
            raise OwnerResolutionHold("RESULT_SCORES_INVALID")
        if (not isinstance(flags, list) or any(not isinstance(v, str) for v in flags)
                or not isinstance(summary, str) or not summary.strip()):
            raise OwnerResolutionHold("RESULT_EVIDENCE_INVALID")
        if decision == "PASS" and (
            flags or any(scores[key] < floor for key, floor in SCORE_FLOORS.items())
        ):
            raise OwnerResolutionHold("RESULT_PASS_GATE_VIOLATION")
        result_counts[decision] += 1
    counts = {key: result_counts.get(key, 0) for key in ("PASS", "HOLD", "REJECT")}
    if result.get("counts") != counts or sum(counts.values()) != 40:
        raise OwnerResolutionHold("RESULT_COUNTS_INVALID")

    expected_safe_fields = RESULT_ONLY_FIELDS
    if (set(result_safe) != expected_safe_fields
            or result_safe.get("schema") != "r60_gold72_reviewer_c_results_only_safe_v1"
            or result_safe.get("status") != "C_RESULTS_BINDING_VALID__EXECUTION_RECORD_UNAVAILABLE"
            or result_safe.get("candidate_count") != 40
            or result_safe.get("case_bindings_valid") != 40
            or result_safe.get("decision_counts") != counts
            or result_safe.get("package_pins_rechecked") is not True
            or result_safe.get("execution_record_available") is not False
            or result_safe.get("execution_attestation_complete") is not False
            or result_safe.get("reviewer_c_independence_verified") is not False
            or result_safe.get("cryptographic_independence_proven") is not False
            or result_safe.get("quality_v1_admitted") != 0
            or result_safe.get("training_authorized") is not False
            or result_safe.get("gpu_started") is not False
            or result_safe.get("r50_accessed") is not False
            or result_safe.get("private_values_emitted") is not False):
        raise OwnerResolutionHold("RESULTS_ONLY_SAFE_INVALID")
    metadata_sha = result_safe.get("execution_metadata_sha256")
    if metadata_sha is not None and (
        not isinstance(metadata_sha, str) or not HEX64.fullmatch(metadata_sha)
    ):
        raise OwnerResolutionHold("EXECUTION_METADATA_SHA_INVALID")

    if (resolution_template.get("schema") != RESOLUTION_TEMPLATE_SCHEMA
            or resolution_template.get("status") != "PENDING_REVIEWER_C_AND_OWNER_DECISION"
            or resolution_template.get("case_count") != 40):
        raise OwnerResolutionHold("OWNER_RESOLUTION_TEMPLATE_INVALID")
    template_rows = resolution_template.get("cases")
    if not isinstance(template_rows, list) or len(template_rows) != 40:
        raise OwnerResolutionHold("OWNER_RESOLUTION_TEMPLATE_COUNT_INVALID")
    template_idx = _unique(template_rows, "blind_case_id", "OWNER_RESOLUTION_TEMPLATE_DUPLICATE")
    if set(template_idx) != set(owner_idx):
        raise OwnerResolutionHold("OWNER_RESOLUTION_TEMPLATE_BINDING_INVALID")
    for blind_id, owner_row in owner_idx.items():
        row = template_idx[blind_id]
        expected_template_fields = set(owner_row) | {
            "reviewer_c_decision", "reviewer_c_scores_1_to_5",
            "reviewer_c_severe_flags", "reviewer_c_evidence_summary",
            "owner_decision", "owner_rationale_cn", "owner_evidence_refs",
            "owner_decided_at_utc", "owner_signoff",
        }
        if set(row) != expected_template_fields:
            raise OwnerResolutionHold("OWNER_RESOLUTION_TEMPLATE_FIELDS_INVALID")
        for key, value in owner_row.items():
            if row.get(key) != value:
                raise OwnerResolutionHold("OWNER_RESOLUTION_TEMPLATE_MAP_MISMATCH")
        if (row.get("reviewer_c_decision") is not None
                or row.get("reviewer_c_scores_1_to_5") is not None
                or row.get("reviewer_c_severe_flags") is not None
                or row.get("reviewer_c_evidence_summary") is not None
                or row.get("owner_decision") is not None
                or row.get("owner_rationale_cn") is not None
                or row.get("owner_evidence_refs") != []
                or row.get("owner_decided_at_utc") is not None
                or row.get("owner_signoff") is not False):
            raise OwnerResolutionHold("OWNER_RESOLUTION_TEMPLATE_PREPOPULATED")
    return blind_idx, owner_idx, result_idx, counts


def _source_pins(values: dict[str, Any]) -> dict[str, str]:
    raw = values["raw"]
    return {
        "package_safe_sha256": _sha(raw["package_safe"]),
        "receipt_template_sha256": _sha(raw["receipt_template"]),
        "blind_input_sha256": _sha(raw["blind_input"]),
        "instructions_sha256": _sha(raw["instructions"]),
        "owner_map_sha256": _sha(raw["owner_map"]),
        "result_sha256": _sha(raw["result"]),
        "results_only_safe_sha256": _sha(raw["results_only_safe"]),
        "resolution_template_sha256": _sha(raw["resolution_template"]),
    }


def prepare_owner_resolution(args) -> dict[str, Any]:
    values = _load_inputs(args)
    blind_idx, owner_idx, result_idx, counts = _validate_sources(values)
    cases = []
    for blind_id, owner_row in sorted(owner_idx.items()):
        result = result_idx[blind_id]
        cases.append({
            **owner_row,
            "reviewer_c_decision": result["decision"],
            "reviewer_c_scores_1_to_5": result["scores_1_to_5"],
            "reviewer_c_severe_flags": result["severe_flags"],
            "reviewer_c_evidence_summary": result["evidence_summary"],
            "owner_decision": None,
            "owner_decision_basis": None,
            "owner_rationale_cn": None,
            "owner_evidence_refs": [],
            "owner_decided_at_utc": None,
            "owner_signoff": False,
        })
    resolution = {
        "schema": RESOLUTION_SCHEMA,
        "status": "PENDING_OWNER_DECISIONS",
        "candidate_count": 40,
        "source_pins": _source_pins(values),
        "execution_record_available": False,
        "execution_metadata_sha256": values["results_only_safe"].get("execution_metadata_sha256"),
        "reviewer_c_independence_verified": False,
        "cryptographic_independence_proven": False,
        "cases": cases,
    }
    raw = (json.dumps(resolution, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    _write_create_only(args.output, raw, values["repo"])
    return {
        "schema": "r60_gold72_owner_resolution_prepare_safe_v1",
        "status": "OWNER_RESOLUTION_WORKSHEET_CREATED__PENDING_40_OWNER_DECISIONS",
        "candidate_count": 40,
        "reviewer_c_decision_counts": counts,
        "owner_decisions_complete": False,
        "execution_record_available": False,
        "reviewer_c_independence_verified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def _aware(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _evidence_ref(value: Any) -> bool:
    if not isinstance(value, str) or not 3 <= len(value) <= 256:
        return False
    if value != value.strip() or any(ord(ch) < 32 for ch in value):
        return False
    if value.startswith(("/", "~")) or "://" in value or "\\" in value:
        return False
    if any(part == ".." for part in value.split("/")):
        return False
    return True


def validate_owner_resolution(args) -> dict[str, Any]:
    values = _load_inputs(args)
    _, owner_idx, result_idx, c_counts = _validate_sources(values)
    repo = values["repo"]
    resolution_raw = _read(args.owner_resolution, repo, 16 * 1024 * 1024, private=True)
    resolution = _json(resolution_raw, "OWNER_RESOLUTION_JSON_INVALID")
    expected_pins = _source_pins(values)
    if (resolution.get("schema") != RESOLUTION_SCHEMA
            or resolution.get("status") != "OWNER_DECISIONS_COMPLETE_PENDING_IMPORT"
            or resolution.get("candidate_count") != 40
            or resolution.get("source_pins") != expected_pins
            or resolution.get("execution_record_available") is not False
            or resolution.get("execution_metadata_sha256")
                != values["results_only_safe"].get("execution_metadata_sha256")
            or resolution.get("reviewer_c_independence_verified") is not False
            or resolution.get("cryptographic_independence_proven") is not False):
        raise OwnerResolutionHold("OWNER_RESOLUTION_HEADER_OR_SOURCE_PINS_INVALID")
    rows = resolution.get("cases")
    if not isinstance(rows, list) or len(rows) != 40:
        raise OwnerResolutionHold("OWNER_RESOLUTION_CASE_COUNT_INVALID")
    row_idx = _unique(rows, "blind_case_id", "OWNER_RESOLUTION_BLIND_ID_DUPLICATE")
    if set(row_idx) != set(owner_idx):
        raise OwnerResolutionHold("OWNER_RESOLUTION_OWNER_MAP_SET_MISMATCH")

    a_counts: Counter[str] = Counter()
    b_counts: Counter[str] = Counter()
    final_counts: Counter[str] = Counter()
    matrix: Counter[str] = Counter()
    evidence_ref_count = 0
    for blind_id, row in row_idx.items():
        owner = owner_idx[blind_id]
        c_result = result_idx[blind_id]
        for key in (
            "original_case_id", "original_story_uuid", "target_sha256",
            "reviewer_a_decision", "reviewer_b2_decision",
            "reviewer_a_evidence_class", "disagreement_type", "prior_b2_blind_case_id",
        ):
            if row.get(key) != owner.get(key):
                raise OwnerResolutionHold("OWNER_RESOLUTION_SOURCE_MAP_CHANGED")
        for key, value in (
            ("reviewer_c_decision", c_result["decision"]),
            ("reviewer_c_scores_1_to_5", c_result["scores_1_to_5"]),
            ("reviewer_c_severe_flags", c_result["severe_flags"]),
            ("reviewer_c_evidence_summary", c_result["evidence_summary"]),
        ):
            if row.get(key) != value:
                raise OwnerResolutionHold("OWNER_RESOLUTION_REVIEWER_C_VALUE_CHANGED")

        decision = row.get("owner_decision")
        basis = row.get("owner_decision_basis")
        rationale = row.get("owner_rationale_cn")
        refs = row.get("owner_evidence_refs")
        decided_at = row.get("owner_decided_at_utc")
        if decision not in DECISIONS:
            raise OwnerResolutionHold("OWNER_DECISION_MISSING_OR_INVALID")
        if basis not in OWNER_BASES:
            raise OwnerResolutionHold("OWNER_DECISION_BASIS_INVALID")
        if basis == "INSUFFICIENT_EVIDENCE_HOLD" and decision != "HOLD":
            raise OwnerResolutionHold("OWNER_INSUFFICIENT_EVIDENCE_MUST_HOLD")
        if not isinstance(rationale, str) or len(rationale.strip()) < 20:
            raise OwnerResolutionHold("OWNER_RATIONALE_TOO_SHORT")
        if (not isinstance(refs, list) or not refs
                or any(not _evidence_ref(ref) for ref in refs)
                or len(refs) != len(set(refs))):
            raise OwnerResolutionHold("OWNER_EVIDENCE_REFERENCES_INVALID")
        if not _aware(decided_at):
            raise OwnerResolutionHold("OWNER_DECISION_TIMESTAMP_INVALID")
        if row.get("owner_signoff") is not True:
            raise OwnerResolutionHold("OWNER_SIGNOFF_MISSING")
        a_decision = owner["reviewer_a_decision"]
        b_decision = owner["reviewer_b2_decision"]
        c_decision = c_result["decision"]
        a_counts[a_decision] += 1
        b_counts[b_decision] += 1
        final_counts[decision] += 1
        matrix[f"A_{a_decision}__B2_{b_decision}__C_{c_decision}__OWNER_{decision}"] += 1
        evidence_ref_count += len(refs)

    if (sum(a_counts.values()) != 40 or sum(b_counts.values()) != 40
            or sum(final_counts.values()) != 40 or sum(matrix.values()) != 40):
        raise OwnerResolutionHold("OWNER_RESOLUTION_AGGREGATE_TOTAL_INVALID")

    safe = {
        "schema": SAFE_SCHEMA,
        "status": SAFE_STATUS,
        "resolution_type": RESOLUTION_TYPE,
        "candidate_count": 40,
        "source_pins": {**expected_pins, "owner_resolution_sha256": _sha(resolution_raw)},
        "a_b2_pair_counts": dict(sorted(EXPECTED_PAIRS.items())),
        "reviewer_a_decisions": dict(sorted(a_counts.items())),
        "reviewer_b2_decisions": dict(sorted(b_counts.items())),
        "reviewer_c_decisions": dict(sorted(c_counts.items())),
        "owner_decisions": dict(sorted(final_counts.items())),
        "resolution_matrix": dict(sorted(matrix.items())),
        "owner_evidence_reference_count": evidence_ref_count,
        "execution_record_available": False,
        "execution_metadata_sha256": resolution.get("execution_metadata_sha256"),
        "execution_attestation_complete": False,
        "reviewer_c_independence_verified": False,
        "cryptographic_independence_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    if args.safe_output.exists() or args.safe_output.is_symlink():
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_ALREADY_EXISTS")
    raw = (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    _write_create_only(args.safe_output, raw, repo)
    return {
        "schema": "r60_gold72_owner_resolution_validation_safe_v1",
        "status": "OWNER_RESOLUTION_COMPLETE__AGGREGATE_SAFE_CREATED",
        "candidate_count": 40,
        "reviewer_c_decisions": dict(sorted(c_counts.items())),
        "owner_decisions": dict(sorted(final_counts.items())),
        "owner_evidence_reference_count": evidence_ref_count,
        "execution_record_available": False,
        "reviewer_c_independence_verified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def _validate_safe(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or set(data) != SAFE_FIELDS:
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_FIELDS_INVALID")
    if (data.get("schema") != SAFE_SCHEMA or data.get("status") != SAFE_STATUS
            or data.get("resolution_type") != RESOLUTION_TYPE
            or data.get("candidate_count") != 40):
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_SCHEMA_INVALID")
    pins = data.get("source_pins")
    if (not isinstance(pins, dict)
            or set(pins) != SOURCE_PIN_KEYS | {"owner_resolution_sha256"}
            or any(not isinstance(value, str) or not HEX64.fullmatch(value) for value in pins.values())):
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_SOURCE_PINS_INVALID")
    if data.get("a_b2_pair_counts") != EXPECTED_PAIRS:
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_PAIR_COUNTS_INVALID")
    maps = (
        ("reviewer_a_decisions", "OWNER_RESOLUTION_SAFE_A_COUNTS_INVALID"),
        ("reviewer_b2_decisions", "OWNER_RESOLUTION_SAFE_B2_COUNTS_INVALID"),
        ("reviewer_c_decisions", "OWNER_RESOLUTION_SAFE_C_COUNTS_INVALID"),
        ("owner_decisions", "OWNER_RESOLUTION_SAFE_OWNER_COUNTS_INVALID"),
    )
    normalized = {}
    for field, reason in maps:
        normalized[field] = _counts(data.get(field), reason)
        if sum(normalized[field].values()) != 40:
            raise OwnerResolutionHold(reason)
    if normalized["reviewer_c_decisions"] != {"PASS": 38, "HOLD": 1, "REJECT": 1}:
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_C_COUNTS_MISMATCH")
    matrix = data.get("resolution_matrix")
    if (not isinstance(matrix, dict) or not matrix
            or any(not isinstance(key, str) or not re.fullmatch(
                r"A_(PASS|HOLD|REJECT)__B2_(PASS|HOLD|REJECT)__C_(PASS|HOLD|REJECT)__OWNER_(PASS|HOLD|REJECT)",
                key
            ) or type(value) is not int or value <= 0 for key, value in matrix.items())
            or sum(matrix.values()) != 40):
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_MATRIX_INVALID")
    if type(data.get("owner_evidence_reference_count")) is not int or data["owner_evidence_reference_count"] < 40:
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_EVIDENCE_COUNT_INVALID")
    matrix_a: Counter[str] = Counter()
    matrix_b: Counter[str] = Counter()
    matrix_c: Counter[str] = Counter()
    matrix_owner: Counter[str] = Counter()
    matrix_pairs: Counter[str] = Counter()
    matrix_pattern = re.compile(
        r"A_(PASS|HOLD|REJECT)__B2_(PASS|HOLD|REJECT)__C_(PASS|HOLD|REJECT)__OWNER_(PASS|HOLD|REJECT)"
    )
    for key, count in matrix.items():
        match = matrix_pattern.fullmatch(key)
        a, b, c, owner = match.groups()
        matrix_a[a] += count
        matrix_b[b] += count
        matrix_c[c] += count
        matrix_owner[owner] += count
        a_class = {"PASS": "CASE_LEVEL_SCORED_PASS", "HOLD": "EXPLICIT_HOLD"}.get(a)
        if a_class is None:
            raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_MATRIX_A_CLASS_INVALID")
        matrix_pairs[f"{a_class}__B2_{b}"] += count
    def same_counts(left: Counter[str], right: dict[str, int]) -> bool:
        return all(left.get(key, 0) == right.get(key, 0) for key in ("PASS", "HOLD", "REJECT"))
    if (
        not same_counts(matrix_a, normalized["reviewer_a_decisions"])
        or not same_counts(matrix_b, normalized["reviewer_b2_decisions"])
        or not same_counts(matrix_c, normalized["reviewer_c_decisions"])
        or not same_counts(matrix_owner, normalized["owner_decisions"])
        or dict(sorted(matrix_pairs.items())) != EXPECTED_PAIRS
    ):
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_MATRIX_MARGINAL_MISMATCH")
    metadata_sha = data.get("execution_metadata_sha256")
    if metadata_sha is not None and (
        not isinstance(metadata_sha, str) or not HEX64.fullmatch(metadata_sha)
    ):
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_METADATA_SHA_INVALID")
    required_false = {
        "execution_record_available": False,
        "execution_attestation_complete": False,
        "reviewer_c_independence_verified": False,
        "cryptographic_independence_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    if any(data.get(key) is not value for key, value in required_false.items()):
        raise OwnerResolutionHold("OWNER_RESOLUTION_SAFE_NON_ADMISSION_FLAGS_INVALID")
    return data


def import_owner_resolution(args) -> dict[str, Any]:
    repo = args.repo_root.resolve(strict=True)
    raw = _read(args.input, repo, 512 * 1024, private=True)
    data = _validate_safe(_json(raw, "OWNER_RESOLUTION_SAFE_JSON_INVALID"))
    receipt_sha = _sha(raw)
    existing = load_events(args.manifest) if args.manifest.exists() else []
    prior = [
        event for event in existing
        if event["batch_id"] == "gold72" and event["event_type"] == EVENT_TYPE
    ]
    if len(prior) > 1:
        raise OwnerResolutionHold("OWNER_RESOLUTION_DUPLICATE_CANONICAL_EVENTS")
    if prior:
        if prior[0]["payload"].get("source_receipt_sha256") == receipt_sha:
            return {
                "schema": "storyforge_gold_quality_owner_resolution_import_safe_v1",
                "status": "GOLD72_OWNER_RESOLUTION_ALREADY_IMPORTED",
                "events_appended": 0,
                "candidate_count": 40,
                "quality_v1_admitted": 0,
                "training_authorized": False,
                "private_values_emitted": False,
            }
        raise OwnerResolutionHold("GOLD72_OWNER_RESOLUTION_ALREADY_PINNED")

    payload = {
        "resolution_type": RESOLUTION_TYPE,
        "source_receipt_sha256": receipt_sha,
        "source_pins": data["source_pins"],
        "candidate_count": 40,
        "a_b2_pair_counts": data["a_b2_pair_counts"],
        "reviewer_a_decisions": data["reviewer_a_decisions"],
        "reviewer_b2_decisions": data["reviewer_b2_decisions"],
        "reviewer_c_decisions": data["reviewer_c_decisions"],
        "owner_decisions": data["owner_decisions"],
        "resolution_matrix": data["resolution_matrix"],
        "owner_evidence_reference_count": data["owner_evidence_reference_count"],
        "execution_record_available": False,
        "execution_metadata_sha256": data["execution_metadata_sha256"],
        "execution_attestation_complete": False,
        "reviewer_c_independence_verified": False,
        "cryptographic_independence_proven": False,
        "evidence_tier": "OWNER_RETURNED_SAFE_AGGREGATE",
        "quality_v1_admitted": False,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
    }
    event = make_event("gold72", EVENT_TYPE, payload, datetime.now(UTC).isoformat(timespec="seconds"))
    count = append_events(args.manifest, [event], repo)
    return {
        "schema": "storyforge_gold_quality_owner_resolution_import_safe_v1",
        "status": "GOLD72_OWNER_RESOLUTION_APPENDED",
        "candidate_count": 40,
        "events_appended": count,
        "owner_decisions": data["owner_decisions"],
        "execution_record_available": False,
        "reviewer_c_independence_verified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }
