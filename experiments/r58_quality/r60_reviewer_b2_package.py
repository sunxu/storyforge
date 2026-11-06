"""Build a fresh, owner-only R60 Gold72 Reviewer B2 blind-review package.

The builder reads the frozen Gold192 semantic source packets and the exact
72-row R60 structural staging selection. It emits a reviewer-only blind input
and instructions separately from an Owner-only identity map and execution
receipt template. It never reads Reviewer A/B1 decisions or results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
from collections import Counter
from pathlib import Path
from typing import Any, Callable

GOLD192_SOURCE_SHA256 = "ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e"
SOURCE_PACKET_SCHEMA = "r58_gold192_story_semantic_review_packet_private_v1"
SOURCE_PACKET_STATUS = "PRIVATE_STORY_REVIEW_PACKET_NOT_REVIEWED"
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
STAGING_RECEIPT_SCHEMA = "storyforge-r59-contiguous-suffix-stage-safe-v1"
STAGING_RECEIPT_STATUS = "CONTIGUOUS_SUFFIX_SOURCE_STAGE_BUILT__NOT_QUALITY_ADMITTED"
BLIND_SCHEMA = "r60_gold72_reviewer_b2_blind_story_packet_v1"
MAP_SCHEMA = "r60_gold72_reviewer_b2_private_id_map_v1"
SAFE_SCHEMA = "r60_gold72_reviewer_b2_package_safe_v1"
EXECUTION_SCHEMA = "r60_gold72_reviewer_b2_execution_receipt_v1"
RESULT_SCHEMA = "r60_gold72_reviewer_b2_results_v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 160 * 1024 * 1024
EXPECTED_CASES = 72
EXPECTED_SOURCE_CASES = 192


class PackageHold(ValueError):
    """Fixed fail-closed reason code; never includes private input values."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _read_private(path: Path, limit: int = MAX_BYTES) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise PackageHold("INPUT_NOT_REGULAR_FILE")
    info = path.stat()
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
        or not 0 < info.st_size <= limit
    ):
        raise PackageHold("INPUT_PERMISSION_OR_SIZE_INVALID")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        after = os.fstat(stream.fileno())
        if (after.st_ino, after.st_dev) != (info.st_ino, info.st_dev):
            raise PackageHold("INPUT_CHANGED_DURING_OPEN")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise PackageHold("INPUT_SIZE_LIMIT")
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
        values = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise PackageHold(reason) from None
    if not values or any(not isinstance(value, dict) for value in values):
        raise PackageHold(reason)
    return values


def _unique_index(rows: list[dict[str, Any]], key: str, reason: str):
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise PackageHold(reason)
        result[value] = row
    return result


def _valid_history(history: Any) -> bool:
    if not isinstance(history, list) or not history:
        return False
    previous = None
    for message in history:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            return False
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"} or role == previous:
            return False
        if not isinstance(content, str) or not content.strip():
            return False
        previous = role
    # The current User turn is supplied separately from the prior history.
    return previous == "assistant"


def _validate_source_packets(rows: list[dict[str, Any]]):
    if len(rows) != 13:
        raise PackageHold("GOLD192_STORY_PACKET_COUNT_INVALID")
    story_ids = set()
    cases = []
    for packet in rows:
        if (
            packet.get("schema") != SOURCE_PACKET_SCHEMA
            or packet.get("status") != SOURCE_PACKET_STATUS
        ):
            raise PackageHold("GOLD192_PACKET_SCHEMA_OR_STATUS_INVALID")
        story_id = packet.get("story_uuid")
        if not isinstance(story_id, str) or not story_id or story_id in story_ids:
            raise PackageHold("GOLD192_STORY_ID_INVALID")
        story_ids.add(story_id)
        card = packet.get("world_card")
        if not isinstance(card, dict) or not card:
            raise PackageHold("GOLD192_WORLD_CARD_INVALID")
        card_bytes = json.dumps(
            card, ensure_ascii=False, sort_keys=True, indent=2
        ).encode("utf-8")
        if (
            packet.get("world_card_source_kind") != "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST"
            or _sha(card_bytes) != packet.get("world_card_sha256")
            or not isinstance(packet.get("review_protocol"), dict)
            or not isinstance(packet.get("review_protocol_addendum"), dict)
        ):
            raise PackageHold("GOLD192_WORLD_CARD_OR_PROTOCOL_INVALID")
        packet_cases = packet.get("cases")
        if not isinstance(packet_cases, list) or not packet_cases:
            raise PackageHold("GOLD192_CASE_LIST_INVALID")
        for case in packet_cases:
            if not isinstance(case, dict):
                raise PackageHold("GOLD192_CASE_INVALID")
            case_id = case.get("case_id")
            target = case.get("target_assistant_text")
            digest = case.get("target_sha256")
            current_user = case.get("current_user_text")
            history = case.get("history")
            if (
                not isinstance(case_id, str) or not case_id
                or not isinstance(target, str) or not target.strip()
                or not isinstance(digest, str) or not HEX64.fullmatch(digest)
                or _sha(target.encode("utf-8")) != digest
                or not isinstance(current_user, str) or not current_user.strip()
                or not _valid_history(history)
                or not isinstance(case.get("history_starts_with_assistant"), bool)
                or case["history_starts_with_assistant"] != (history[0]["role"] == "assistant")
                or not isinstance(case.get("priority"), str)
                or not isinstance(case.get("review_focus"), list)
                or not case["review_focus"]
                or any(not isinstance(item, str) or not item.strip() for item in case["review_focus"])
            ):
                raise PackageHold("GOLD192_CASE_SOURCE_INVALID")
            cases.append((packet, case))
    if len(cases) != EXPECTED_SOURCE_CASES:
        raise PackageHold("GOLD192_CASE_COUNT_INVALID")
    case_index = _unique_index([case for _, case in cases], "case_id", "GOLD192_CASE_ID_DUPLICATE")
    target_index = _unique_index([case for _, case in cases], "target_sha256", "GOLD192_TARGET_SHA_DUPLICATE")
    if len(case_index) != EXPECTED_SOURCE_CASES or len(target_index) != EXPECTED_SOURCE_CASES:
        raise PackageHold("GOLD192_CASE_IDENTITY_COUNT_INVALID")
    return cases, case_index, target_index


def build(
    source_packets: list[dict[str, Any]],
    staged_rows: list[dict[str, Any]],
    instructions: str,
    *,
    token_factory: Callable[[], str] | None = None,
    shuffle: Callable[[list[Any]], None] | None = None,
):
    if not isinstance(instructions, str) or len(instructions.strip()) < 100:
        raise PackageHold("B2_INSTRUCTIONS_INVALID")
    source_cases, source_by_id, source_by_sha = _validate_source_packets(source_packets)
    if len(staged_rows) != EXPECTED_CASES:
        raise PackageHold("GOLD72_STAGE_COUNT_INVALID")

    stage_ids = set()
    stage_hashes = set()
    selected = []
    for row in staged_rows:
        if (
            row.get("schema") != STAGE_SCHEMA
            or row.get("status") != STAGE_STATUS
            or not isinstance(row.get("case_id"), str)
            or not isinstance(row.get("target_sha256"), str)
            or not HEX64.fullmatch(row["target_sha256"])
        ):
            raise PackageHold("GOLD72_STAGE_ROW_INVALID")
        case_id, digest = row["case_id"], row["target_sha256"]
        if case_id in stage_ids or digest in stage_hashes:
            raise PackageHold("GOLD72_STAGE_IDENTITY_DUPLICATE")
        stage_ids.add(case_id)
        stage_hashes.add(digest)
        source_case = source_by_id.get(case_id)
        source_pair = source_by_sha.get(digest)
        if (
            source_case is None or source_pair is None
            or source_case.get("target_sha256") != digest
            or source_pair.get("case_id") != case_id
        ):
            raise PackageHold("GOLD72_STAGE_SOURCE_BINDING_MISMATCH")
        source_packet = next(packet for packet, case in source_cases if case is source_case)
        selected.append((source_packet, source_case))

    token_factory = token_factory or (lambda: secrets.token_hex(12))
    shuffle = shuffle or secrets.SystemRandom().shuffle
    blind_ids = set()
    story_ids = set()
    id_map = []
    per_story: dict[str, dict[str, Any]] = {}
    for packet, source_case in selected:
        blind_id = "B2-" + token_factory()
        if blind_id in blind_ids:
            raise PackageHold("B2_RANDOM_ID_COLLISION")
        blind_ids.add(blind_id)
        story_uuid = packet["story_uuid"]
        group = per_story.get(story_uuid)
        if group is None:
            group = {
                "schema": BLIND_SCHEMA,
                "status": "BLIND_REVIEW_PENDING",
                "blind_story_packet_id": None,
                "reviewer": "B2",
                "world_card_source_kind": packet["world_card_source_kind"],
                "world_card_sha256": packet["world_card_sha256"],
                "world_card": packet["world_card"],
                "review_protocol": packet["review_protocol"],
                "review_protocol_addendum": {
                    **packet["review_protocol_addendum"],
                    "independent_recheck_only": True,
                    "do_not_access_or_request_reviewer_a_or_b1_materials": True,
                    "do_not_use_prior_conversations_or_memory": True,
                    "do_not_use_owner_identity_mapping": True,
                    "do_not_infer_why_this_case_was_selected": True,
                },
                "case_count": 0,
                "cases": [],
            }
            per_story[story_uuid] = group
        group["cases"].append({
            "blind_case_id": blind_id,
            "priority": source_case["priority"],
            "history_starts_with_assistant": source_case["history_starts_with_assistant"],
            "review_focus": source_case["review_focus"],
            "history": source_case["history"],
            "current_user_text": source_case["current_user_text"],
            "target_assistant_text": source_case["target_assistant_text"],
            "target_sha256": source_case["target_sha256"],
        })
        id_map.append({
            "blind_case_id": blind_id,
            "original_case_id": source_case["case_id"],
            "original_story_uuid": story_uuid,
            "target_sha256": source_case["target_sha256"],
        })

    packets = list(per_story.values())
    for packet in packets:
        shuffle(packet["cases"])
        packet["case_count"] = len(packet["cases"])
        packet["blind_story_packet_id"] = "B2-STORY-" + token_factory()
        story_ids.add(packet["blind_story_packet_id"])
    if len(story_ids) != len(packets):
        raise PackageHold("B2_STORY_ID_COLLISION")
    shuffle(packets)

    # Fail closed if any owner identity, cohort, or prior-review field leaked.
    forbidden_keys = {
        "case_id", "story_uuid", "cohort", "legacy_evidence_state",
        "review_status", "reviewer_a", "reviewer_b", "gold87", "gold108",
    }
    def walk_keys(value: Any):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_keys(child)
    if set(walk_keys(packets)) & forbidden_keys:
        raise PackageHold("B2_BLIND_INPUT_OWNER_DATA_LEAK")

    return packets, id_map, {
        "candidate_count": len(id_map),
        "story_packet_count": len(packets),
        "blind_ids_unique": len(blind_ids) == EXPECTED_CASES,
        "all_targets_bound_to_frozen_gold192": len(id_map) == EXPECTED_CASES,
        "reviewer_a_materials_read": False,
        "reviewer_b1_materials_read": False,
        "owner_mapping_in_blind_input": False,
    }


def _create_only(path: Path, raw: bytes):
    fd = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return _sha(raw)


def run(
    source_path: Path,
    staged_path: Path,
    staging_safe_path: Path,
    instructions_path: Path,
    output_dir: Path,
    repo_root: Path,
):
    source_raw = _read_private(source_path)
    staged_raw = _read_private(staged_path)
    stage_safe_raw = _read_private(staging_safe_path, 256 * 1024)
    instructions_raw = _read_private(instructions_path, 128 * 1024)
    if _sha(source_raw) != GOLD192_SOURCE_SHA256:
        raise PackageHold("GOLD192_SOURCE_PIN_MISMATCH")
    stage_safe = _json(stage_safe_raw, "STAGING_SAFE_JSON_INVALID")
    if (
        stage_safe.get("schema") != STAGING_RECEIPT_SCHEMA
        or stage_safe.get("status") != STAGING_RECEIPT_STATUS
        or stage_safe.get("staged_file_sha256") != _sha(staged_raw)
        or stage_safe.get("source_rows") != EXPECTED_CASES
        or stage_safe.get("context_staged") != EXPECTED_CASES
        or stage_safe.get("context_structure_hold") != 0
        or stage_safe.get("source_histories_mutated") is not False
        or stage_safe.get("original_staging_mutated") is not False
        or stage_safe.get("quality_v1_admitted") != 0
        or stage_safe.get("training_authorized") is not False
        or stage_safe.get("gpu_started") is not False
        or stage_safe.get("r50_accessed") is not False
        or not isinstance(stage_safe.get("source_context_file_sha256"), str)
        or not HEX64.fullmatch(stage_safe["source_context_file_sha256"])
    ):
        raise PackageHold("GOLD72_STAGING_RECEIPT_INVALID")

    source_packets = _jsonl(source_raw, "GOLD192_SOURCE_JSONL_INVALID")
    staged_rows = _jsonl(staged_raw, "GOLD72_STAGE_JSONL_INVALID")
    instructions = instructions_raw.decode("utf-8")
    packets, mapping, counts = build(source_packets, staged_rows, instructions)

    root = repo_root.resolve()
    if (
        output_dir.exists() or output_dir.is_symlink()
        or not output_dir.is_absolute()
        or output_dir.resolve().is_relative_to(root)
        or not output_dir.parent.is_dir()
        or output_dir.parent.is_symlink()
        or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700
    ):
        raise PackageHold("B2_OUTPUT_LOCATION_INVALID")

    output_dir.mkdir(mode=0o700)
    created = []
    try:
        blind_raw = b"".join(_canonical(packet) + b"\n" for packet in packets)
        map_raw = json.dumps(
            {"schema": MAP_SCHEMA, "reviewer": "B2", "mapping": mapping},
            ensure_ascii=False, sort_keys=True, indent=2,
        ).encode("utf-8") + b"\n"
        receipt_template = {
            "schema": EXECUTION_SCHEMA,
            "status": "PENDING_INDEPENDENT_REVIEW_EXECUTION",
            "reviewer": "B2",
            "execution_mode": None,
            "provider": None,
            "model_id": None,
            "model_version": None,
            "session_or_request_id": None,
            "started_at_utc": None,
            "completed_at_utc": None,
            "blind_input_sha256": _sha(blind_raw),
            "instructions_sha256": _sha(instructions_raw),
            "result_sha256": None,
            "transcript_or_provider_record_sha256": None,
            "attestations": {
                "reviewer_a_materials_not_provided": None,
                "reviewer_b1_materials_not_provided": None,
                "owner_id_map_not_provided": None,
                "prior_conversations_or_memory_not_used": None,
                "tools_and_connectors_not_used": None,
                "all_72_cases_reviewed_independently": None,
            },
            "owner_verification": {
                "input_hashes_rechecked": False,
                "execution_record_inspected": False,
                "result_hash_rechecked": False,
                "case_binding_rechecked": False,
            },
            "limitations": [
                "Self-attestation is not cryptographic proof of a separate session.",
                "A temporary chat transcript alone cannot prove hidden memory state.",
                "Prefer a stateless one-shot API request with no conversation or prior_response_id.",
            ],
        }
        files = {
            "R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl": blind_raw,
            "R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md": instructions_raw,
            "R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json": map_raw,
            "R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json": (
                json.dumps(receipt_template, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
            ),
        }
        hashes = {}
        for name, raw in files.items():
            hashes[name] = _create_only(output_dir / name, raw)
            created.append(output_dir / name)
        safe = {
            "schema": SAFE_SCHEMA,
            "status": "REVIEWER_B2_PACKAGE_BUILT__AWAITING_INDEPENDENT_EXECUTION",
            **counts,
            "source_packet_sha256": _sha(source_raw),
            "staged_selection_sha256": _sha(staged_raw),
            "staging_receipt_sha256": _sha(stage_safe_raw),
            "blind_input_sha256": hashes["R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl"],
            "instructions_sha256": hashes["R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md"],
            "owner_map_sha256": hashes["R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json"],
            "execution_receipt_template_sha256": hashes[
                "R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json"
            ],
            "reviewer_a_or_b1_results_included": False,
            "owner_mapping_shared_with_reviewer": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }
        safe_raw = json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
        _create_only(output_dir / "R60_GOLD72_REVIEWER_B2_PACKAGE_SAFE.json", safe_raw)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        for path in output_dir.iterdir():
            path.unlink(missing_ok=True)
        output_dir.rmdir()
        raise
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold192-source-jsonl", required=True, type=Path)
    parser.add_argument("--gold72-staged-jsonl", required=True, type=Path)
    parser.add_argument("--gold72-staging-safe", required=True, type=Path)
    parser.add_argument("--instructions-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        safe = run(
            args.gold192_source_jsonl, args.gold72_staged_jsonl,
            args.gold72_staging_safe, args.instructions_file,
            args.output_dir, args.repo_root,
        )
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (PackageHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = str(exc) if isinstance(exc, PackageHold) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "REVIEWER_B2_PACKAGE_HOLD",
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
