"""Build a fresh blind Reviewer C packet for the 40 Gold72 A/B2 disagreements.

This is an Owner-local evidence-preparation tool. It does not adjudicate, mutate
source reviews, write the Quality Manifest, or admit training data.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import stat
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from . import r60_reviewer_ab2_gold72_crosswalk as crosswalk
from . import r60_reviewer_ab_canonical_crosswalk as canonical

SAFE_SCHEMA = "r60_gold72_reviewer_c_disagreement_package_safe_v1"
SAFE_STATUS = "REVIEWER_C_DISAGREEMENT_PACKAGE_BUILT__AWAITING_INDEPENDENT_REVIEW"
BLIND_SCHEMA = "r60_gold72_reviewer_c_blind_story_packet_v1"
MAP_SCHEMA = "r60_gold72_reviewer_c_private_id_map_v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
EXPECTED_PAIRS = {
    "CASE_LEVEL_SCORED_PASS__B2_HOLD": 5,
    "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
    "EXPLICIT_HOLD__B2_PASS": 30,
    "EXPLICIT_HOLD__B2_REJECT": 3,
}
SOURCE_FLAGS = (
    "staged-jsonl", "staging-safe", "owner-evidence-jsonl",
    "reviewer-a-v3-json", "b2-blind-jsonl", "b2-instructions",
    "b2-owner-map-json", "b2-results-json", "b2-execution-receipt",
    "b2-execution-record", "b2-audit-safe",
)
MAX_INPUT = 160 * 1024 * 1024


class PackageHold(ValueError):
    """Fixed, non-sensitive failure reason."""


def _read_private(path: Path, limit: int = MAX_INPUT) -> bytes:
    if path.is_symlink() or not path.is_file() or path.parent.is_symlink():
        raise PackageHold("PRIVATE_INPUT_NOT_REGULAR")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1 or not 0 < info.st_size <= limit
            or stat.S_IMODE(path.parent.stat().st_mode) != 0o700):
        raise PackageHold("PRIVATE_INPUT_PERMISSION_OR_SIZE_INVALID")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        raise PackageHold("PRIVATE_INPUT_OPEN_FAILED") from None
    try:
        opened = os.fstat(fd)
        if (opened.st_ino, opened.st_dev) != (info.st_ino, info.st_dev):
            raise PackageHold("PRIVATE_INPUT_CHANGED_DURING_OPEN")
        raw = bytearray()
        while True:
            chunk = os.read(fd, min(1024 * 1024, limit + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > limit:
                raise PackageHold("PRIVATE_INPUT_SIZE_INVALID")
    finally:
        os.close(fd)
    if len(raw) != info.st_size:
        raise PackageHold("PRIVATE_INPUT_CHANGED_DURING_READ")
    return bytes(raw)


def _read_instructions(path: Path, repo_root: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise PackageHold("C_INSTRUCTIONS_NOT_REGULAR")
    resolved = path.resolve(strict=True)
    root = repo_root.resolve(strict=True)
    if resolved == root or root not in resolved.parents:
        raise PackageHold("C_INSTRUCTIONS_OUTSIDE_REPO")
    raw = path.read_bytes()
    if not 100 <= len(raw) <= 128 * 1024:
        raise PackageHold("C_INSTRUCTIONS_SIZE_INVALID")
    return raw


def _json(raw: bytes, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise PackageHold(reason) from None
    if not isinstance(value, dict):
        raise PackageHold(reason)
    return value


def _jsonl(raw: bytes, reason: str) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise PackageHold(reason) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise PackageHold(reason)
    return rows


def _unique(rows: list[dict[str, Any]], key: str, reason: str) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise PackageHold(reason)
        result[value] = row
    return result


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def validate_crosswalk_safe(crosswalk_safe: dict[str, Any], fresh: dict[str, Any]) -> None:
    comparable = (
        "candidate_count", "staging_sha256", "source_context_sha256",
        "reviewer_a_v3_report_sha256", "reviewer_b2_blind_input_sha256",
        "reviewer_b2_instructions_sha256", "reviewer_b2_owner_map_sha256",
        "reviewer_b2_result_sha256", "reviewer_b2_execution_record_sha256",
        "reviewer_a_evidence_granularity", "reviewer_b2_decisions",
        "a_b2_pair_counts", "a_b2_comparable_decision_cases",
        "a_b2_semantic_decision_disagreements",
        "a_b2_semantic_decision_agreements",
    )
    if (crosswalk_safe.get("schema") != crosswalk.SAFE_SCHEMA
            or crosswalk_safe.get("status") != crosswalk.SAFE_STATUS
            or any(crosswalk_safe.get(key) != fresh.get(key) for key in comparable)
            or fresh.get("a_b2_semantic_decision_disagreements") != 40
            or fresh.get("a_b2_semantic_decision_agreements") != 32):
        raise PackageHold("CROSSWALK_SAFE_STALE_OR_MISMATCH")


def build(
    staged_rows: list[dict[str, Any]],
    a_report: dict[str, Any],
    blind_packets: list[dict[str, Any]],
    owner_map: dict[str, Any],
    b2_result: dict[str, Any],
    *,
    token_factory: Callable[[], str] | None = None,
    shuffle: Callable[[list[Any]], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Build new C IDs and a private map from already validated source records."""
    if len(staged_rows) != 72:
        raise PackageHold("STAGED_CASE_COUNT_INVALID")
    a_records = a_report.get("records")
    if not isinstance(a_records, list) or len(a_records) != 192:
        raise PackageHold("A_REPORT_CASE_COUNT_INVALID")
    a_idx = _unique(a_records, "target_sha256", "A_TARGET_IDENTITY_INVALID")
    staged_idx = _unique(staged_rows, "target_sha256", "STAGED_TARGET_IDENTITY_INVALID")
    if len(staged_idx) != 72:
        raise PackageHold("STAGED_TARGET_COUNT_INVALID")

    blind_rows = []
    for packet in blind_packets:
        if packet.get("schema") != "r60_gold72_reviewer_b2_blind_story_packet_v1" or packet.get("reviewer") != "B2":
            raise PackageHold("B2_BLIND_PACKET_SCHEMA_INVALID")
        cases = packet.get("cases")
        if not isinstance(cases, list):
            raise PackageHold("B2_BLIND_PACKET_CASES_INVALID")
        blind_rows.extend(cases)
    result_rows = b2_result.get("cases")
    mapping = owner_map.get("mapping")
    if not isinstance(result_rows, list) or len(result_rows) != 72:
        raise PackageHold("B2_RESULT_CASE_COUNT_INVALID")
    if not isinstance(mapping, list) or len(mapping) != 72:
        raise PackageHold("B2_OWNER_MAP_COUNT_INVALID")
    blind_idx = _unique(blind_rows, "target_sha256", "B2_BLIND_TARGET_IDENTITY_INVALID")
    result_idx = _unique(result_rows, "target_sha256", "B2_RESULT_TARGET_IDENTITY_INVALID")
    owner_idx = _unique(mapping, "target_sha256", "B2_OWNER_TARGET_IDENTITY_INVALID")
    if any(len(x) != 72 for x in (blind_idx, result_idx, owner_idx)):
        raise PackageHold("B2_TARGET_SET_COUNT_INVALID")
    if set(blind_idx) != set(result_idx) or set(result_idx) != set(owner_idx) or set(owner_idx) != set(staged_idx):
        raise PackageHold("B2_GOLD72_TARGET_SET_MISMATCH")

    token_factory = token_factory or (lambda: secrets.token_urlsafe(18))
    shuffle = shuffle or secrets.SystemRandom().shuffle
    used_ids: set[str] = set()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    private_rows = []
    pair_counts: Counter[str] = Counter()

    for digest, staged in staged_idx.items():
        a_row = a_idx.get(digest)
        b_row = result_idx.get(digest)
        blind_row = blind_idx.get(digest)
        owner_row = owner_idx.get(digest)
        if any(row is None for row in (a_row, b_row, blind_row, owner_row)):
            raise PackageHold("CASE_SOURCE_JOIN_MISSING")
        if (a_row.get("case_id") != staged.get("case_id")
                or owner_row.get("original_case_id") != staged.get("case_id")
                or owner_row.get("target_sha256") != digest
                or blind_row.get("target_sha256") != digest
                or b_row.get("target_sha256") != digest
                or owner_row.get("blind_case_id") != blind_row.get("blind_case_id")
                or b_row.get("blind_case_id") != blind_row.get("blind_case_id")):
            raise PackageHold("CASE_SOURCE_JOIN_MISMATCH")
        story_uuid = owner_row.get("original_story_uuid")
        if not isinstance(story_uuid, str) or not story_uuid:
            raise PackageHold("OWNER_STORY_BINDING_INVALID")

        a_decision = crosswalk._a_decision(a_row)
        b_decision = b_row.get("decision")
        if b_decision not in {"PASS", "HOLD", "REJECT"}:
            raise PackageHold("B2_DECISION_INVALID")
        if a_decision is None or a_decision == b_decision:
            continue

        a_class = canonical._a_class(a_row)
        pair = f"{a_class}__B2_{b_decision}"
        pair_counts[pair] += 1
        required_case_fields = (
            "priority", "history_starts_with_assistant", "review_focus",
            "history", "current_user_text", "target_assistant_text",
        )
        if any(field not in blind_row for field in required_case_fields):
            raise PackageHold("BLIND_CASE_CONTEXT_FIELD_MISSING")
        if (not isinstance(blind_row.get("history"), list)
                or not isinstance(blind_row.get("review_focus"), list)
                or not blind_row.get("review_focus")
                or not isinstance(blind_row.get("current_user_text"), str)
                or not isinstance(blind_row.get("target_assistant_text"), str)
                or not isinstance(blind_row.get("history_starts_with_assistant"), bool)):
            raise PackageHold("BLIND_CASE_CONTEXT_INVALID")

        token = token_factory()
        if not isinstance(token, str) or not TOKEN.fullmatch(token):
            raise PackageHold("C_BLIND_TOKEN_INVALID")
        blind_id = "C-" + token
        if blind_id in used_ids or blind_id == blind_row.get("blind_case_id"):
            raise PackageHold("C_BLIND_ID_COLLISION")
        used_ids.add(blind_id)
        grouped[story_uuid].append({
            "blind_case_id": blind_id,
            "priority": blind_row["priority"],
            "history_starts_with_assistant": blind_row["history_starts_with_assistant"],
            "review_focus": blind_row["review_focus"],
            "history": blind_row["history"],
            "current_user_text": blind_row["current_user_text"],
            "target_assistant_text": blind_row["target_assistant_text"],
            "target_sha256": digest,
        })
        private_rows.append({
            "blind_case_id": blind_id,
            "original_case_id": staged["case_id"],
            "original_story_uuid": story_uuid,
            "target_sha256": digest,
            "reviewer_a_decision": a_decision,
            "reviewer_b2_decision": b_decision,
            "reviewer_a_evidence_class": a_class,
            "disagreement_type": pair,
            "prior_b2_blind_case_id": blind_row["blind_case_id"],
        })

    if dict(sorted(pair_counts.items())) != dict(sorted(EXPECTED_PAIRS.items())):
        raise PackageHold("GOLD72_DISAGREEMENT_PAIR_COUNTS_MISMATCH")
    if len(private_rows) != 40 or len(used_ids) != 40:
        raise PackageHold("GOLD72_DISAGREEMENT_CASE_COUNT_INVALID")

    packets = []
    for story_uuid, cases in grouped.items():
        shuffle(cases)
        story_token = token_factory()
        if not isinstance(story_token, str) or not TOKEN.fullmatch(story_token):
            raise PackageHold("C_STORY_TOKEN_INVALID")
        packets.append({
            "schema": BLIND_SCHEMA,
            "reviewer": "C",
            "blind_story_packet_id": "C-STORY-" + story_token,
            "do_not_use_owner_identity_mapping": True,
            "do_not_infer_why_this_case_was_selected": True,
            "case_count": len(cases),
            "cases": cases,
        })
    if len({p["blind_story_packet_id"] for p in packets}) != len(packets):
        raise PackageHold("C_STORY_ID_COLLISION")
    shuffle(packets)

    forbidden = {
        "case_id", "original_case_id", "original_story_uuid", "story_uuid",
        "cohort", "reviewer_a", "reviewer_b", "reviewer_a_decision",
        "reviewer_b2_decision", "disagreement_type", "prior_b2_blind_case_id",
    }
    if forbidden & set(_walk_keys(packets)):
        raise PackageHold("C_BLIND_PACKET_PRIOR_REVIEW_LEAK")

    private_map = {
        "schema": MAP_SCHEMA,
        "status": "OWNER_ONLY_PRIVATE_MAPPING",
        "reviewer": "C",
        "candidate_count": 40,
        "mapping": private_rows,
    }
    safe = {
        "schema": SAFE_SCHEMA,
        "status": SAFE_STATUS,
        "candidate_count": 40,
        "pair_counts": dict(sorted(pair_counts.items())),
        "prior_a_b2_decisions_embedded_in_blind_packet": False,
        "owner_mapping_separate": True,
        "reviewer_c_materials_read": False,
        "reviewer_c_execution_started": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return packets, private_map, safe


def _write_exclusive(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def _create_package(
    output_dir: Path,
    packets: list[dict[str, Any]],
    private_map: dict[str, Any],
    safe: dict[str, Any],
    instructions_raw: bytes,
) -> None:
    if not output_dir.is_absolute() or output_dir.exists() or output_dir.is_symlink():
        raise PackageHold("OUTPUT_DIR_INVALID_OR_EXISTS")
    parent = output_dir.parent
    if not parent.is_dir() or parent.is_symlink() or stat.S_IMODE(parent.stat().st_mode) != 0o700:
        raise PackageHold("OUTPUT_PARENT_NOT_PRIVATE")
    output_dir.mkdir(mode=0o700)
    output_dir.chmod(0o700)
    packet_raw = b"".join(
        json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        for packet in packets
    )
    map_raw = (json.dumps(private_map, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    safe_raw = (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _write_exclusive(output_dir / "R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl", packet_raw)
    _write_exclusive(output_dir / "R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json", map_raw)
    _write_exclusive(output_dir / "R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md", instructions_raw)
    _write_exclusive(output_dir / "R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json", safe_raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a fresh blind Reviewer C package for Gold72 disagreements")
    for flag in SOURCE_FLAGS:
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--crosswalk-safe", required=True, type=Path)
    parser.add_argument("--reviewer-c-instructions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = {flag: _read_private(getattr(args, flag.replace("-", "_"))) for flag in SOURCE_FLAGS}
        fresh = crosswalk.audit(
            raw["staged-jsonl"], raw["staging-safe"], raw["owner-evidence-jsonl"],
            raw["reviewer-a-v3-json"], raw["b2-blind-jsonl"], raw["b2-instructions"],
            raw["b2-owner-map-json"], raw["b2-results-json"], raw["b2-execution-receipt"],
            raw["b2-execution-record"], raw["b2-audit-safe"],
        )
        crosswalk_safe = _json(_read_private(args.crosswalk_safe, 2 * 1024 * 1024), "CROSSWALK_SAFE_INVALID")
        validate_crosswalk_safe(crosswalk_safe, fresh)
        staged_rows = _jsonl(raw["staged-jsonl"], "STAGED_JSONL_INVALID")
        a_report = _json(raw["reviewer-a-v3-json"], "A_REPORT_INVALID")
        blind_packets = _jsonl(raw["b2-blind-jsonl"], "B2_BLIND_INPUT_INVALID")
        owner_map = _json(raw["b2-owner-map-json"], "B2_OWNER_MAP_INVALID")
        b2_result = _json(raw["b2-results-json"], "B2_RESULT_INVALID")
        packets, private_map, safe = build(
            staged_rows, a_report, blind_packets, owner_map, b2_result
        )
        instructions_raw = _read_instructions(args.reviewer_c_instructions, args.repo_root)
        _create_package(args.output_dir, packets, private_map, safe, instructions_raw)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (PackageHold, crosswalk.CrosswalkHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, (PackageHold, crosswalk.CrosswalkHold)) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "HOLD", "reason_code": reason,
            "candidate_count": 0, "quality_v1_admitted": 0,
            "training_authorized": False, "gpu_started": False,
            "r50_accessed": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
