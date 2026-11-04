"""Build a private exact-association index from frozen R59 Gold Story Packets.

This inventories packet structure and exact candidate membership only. It does
not approve world cards, establish historical card availability, prove rights,
reviewer independence, protected-set completeness, or Quality-v1 admission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "storyforge-r59-packet-evidence-inventory-safe-v1"
STAGED_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGED_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
HEX = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 160 * 1024 * 1024
CASE_FIELDS = ("case_id", "target_sha256", "history",
               "current_user_text", "target_assistant_text")
PROTOCOL_FLAGS = (
    "two_independent_blinded_reviews_required",
    "source_world_card_is_unapproved",
    "do_not_infer_missing_world_facts",
    "check_card_gold_contradictions",
)
ADDENDUM_FLAGS = (
    "card_is_export_snapshot_not_historical_request",
    "do_not_assume_card_was_available_at_target_time",
    "preserve_leading_assistant_context_without_silent_deletion",
    "review_each_target_against_visible_history_and_card",
    "world_card_approval_is_separate_from_sample_quality",
)


class PacketInventoryHold(ValueError):
    pass


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_private(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise PacketInventoryHold("INPUT_NOT_REGULAR_FILE")
    info = path.stat()
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise PacketInventoryHold("INPUT_PERMISSION_INVALID")
    if info.st_size <= 0 or info.st_size > MAX_BYTES:
        raise PacketInventoryHold("INPUT_SIZE_INVALID")
    return path.read_bytes()


def _jsonl(raw: bytes, reason: str) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise PacketInventoryHold(reason) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise PacketInventoryHold(reason)
    return rows


def _valid_case(case: Any) -> bool:
    if not isinstance(case, dict):
        return False
    if not isinstance(case.get("case_id"), str) or not case["case_id"]:
        return False
    if (not isinstance(case.get("current_user_text"), str)
            or not isinstance(case.get("target_assistant_text"), str)
            or not case["target_assistant_text"]):
        return False
    target = case.get("target_sha256")
    if HEX.fullmatch(target if isinstance(target, str) else "") is None:
        return False
    history = case.get("history")
    if not isinstance(history, list):
        return False
    return all(
        isinstance(message, dict)
        and message.get("role") in ("user", "assistant")
        and isinstance(message.get("content"), str)
        for message in history
    )


def build_inventory(packet_rows, staged_rows, packet_sha: str, staged_sha: str):
    if HEX.fullmatch(packet_sha or "") is None or HEX.fullmatch(staged_sha or "") is None:
        raise PacketInventoryHold("INPUT_PIN_INVALID")

    packet_schema = {row.get("schema") for row in packet_rows}
    if len(packet_schema) != 1 or not all(isinstance(x, str) and x for x in packet_schema):
        raise PacketInventoryHold("PACKET_SCHEMA_INCONSISTENT")

    packet_index: dict[tuple[str, str], tuple[int, int]] = {}
    packet_case_count = 0
    duplicate_packet_pairs = 0
    invalid_cases = 0
    matched_packets: set[int] = set()
    card_approval = Counter()
    card_review = Counter()
    card_source = Counter()
    protocol_counts = Counter()
    addendum_counts = Counter()
    leading_assistant = 0
    empty_history = 0
    history_messages = 0

    for packet_number, packet in enumerate(packet_rows, start=1):
        cases = packet.get("cases")
        if not isinstance(cases, list):
            raise PacketInventoryHold("PACKET_CASES_NOT_LIST")
        card = packet.get("world_card")
        if not isinstance(card, dict):
            raise PacketInventoryHold("PACKET_WORLD_CARD_INVALID")

        approval = packet.get("world_card_approved_for_system")
        card_approval[str(approval).lower() if type(approval) is bool else "unknown"] += 1
        review = packet.get("world_card_review_status")
        card_review[review if isinstance(review, str) else "unknown"] += 1
        source = packet.get("world_card_source_kind")
        card_source[source if isinstance(source, str) else "unknown"] += 1

        protocol = packet.get("review_protocol")
        if isinstance(protocol, dict):
            for flag in PROTOCOL_FLAGS:
                protocol_counts[flag + ":" + str(protocol.get(flag)).lower()
                                if type(protocol.get(flag)) is bool else flag + ":unknown"] += 1
        addendum = packet.get("review_protocol_addendum")
        if isinstance(addendum, dict):
            for flag in ADDENDUM_FLAGS:
                addendum_counts[flag + ":" + str(addendum.get(flag)).lower()
                                if type(addendum.get(flag)) is bool else flag + ":unknown"] += 1

        card_sha = packet.get("world_card_sha256")
        if card_sha is not None and HEX.fullmatch(card_sha if isinstance(card_sha, str) else "") is None:
            raise PacketInventoryHold("WORLD_CARD_PIN_INVALID")

        for case_number, case in enumerate(cases):
            packet_case_count += 1
            if not _valid_case(case):
                invalid_cases += 1
                continue
            history = case["history"]
            history_messages += len(history)
            if not history:
                empty_history += 1
            elif history[0].get("role") == "assistant":
                leading_assistant += 1
            pair = (case["case_id"], case["target_sha256"])
            if pair in packet_index:
                duplicate_packet_pairs += 1
            else:
                packet_index[pair] = (packet_number, case_number)

    if invalid_cases:
        raise PacketInventoryHold("PACKET_CASE_STRUCTURE_INVALID")
    if duplicate_packet_pairs:
        raise PacketInventoryHold("PACKET_CASE_IDENTITY_DUPLICATE")

    ready = [
        row for row in staged_rows
        if isinstance(row, dict)
        and row.get("schema") == STAGED_SCHEMA
        and row.get("status") == STAGED_STATUS
    ]
    if not ready:
        raise PacketInventoryHold("NO_STAGED_CANDIDATES")
    seen_stage = set()
    associations = []
    unmatched = 0
    for row in ready:
        case_id, target = row.get("case_id"), row.get("target_sha256")
        if not isinstance(case_id, str) or not case_id or HEX.fullmatch(target or "") is None:
            raise PacketInventoryHold("STAGED_IDENTITY_INVALID")
        pair = (case_id, target)
        if pair in seen_stage:
            raise PacketInventoryHold("STAGED_IDENTITY_DUPLICATE")
        seen_stage.add(pair)
        location = packet_index.get(pair)
        if location is None:
            unmatched += 1
            continue
        packet_number, case_number = location
        matched_packets.add(packet_number)
        packet = packet_rows[packet_number - 1]
        associations.append({
            "case_id": case_id,
            "target_sha256": target,
            "packet_row_1based": packet_number,
            "case_index_0based": case_number,
            "packet_world_card_sha256": packet.get("world_card_sha256"),
            "packet_world_card_source_kind": packet.get("world_card_source_kind"),
            "packet_world_card_review_status": packet.get("world_card_review_status"),
            "packet_world_card_approved_for_system": packet.get("world_card_approved_for_system"),
            "source_packet_locator": f"GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl:row={packet_number}:cases[{case_number}]",
            "world_card_snapshot_locator": f"GOLD192_STORY_REVIEW_PACKETS_PRIVATE.jsonl:row={packet_number}:world_card",
        })

    complete = len(associations) == len(ready) and unmatched == 0
    safe = {
        "schema": SCHEMA,
        "status": "PACKET_EVIDENCE_ASSOCIATION_COMPLETE__NO_ATTESTATION_OR_ADMISSION"
                  if complete else "PACKET_EVIDENCE_ASSOCIATION_HOLD",
        "packet_rows": len(packet_rows),
        "packet_case_objects": packet_case_count,
        "invalid_case_objects": invalid_cases,
        "staged_ready": len(ready),
        "candidate_exact_matches": len(associations),
        "candidate_unmatched": unmatched,
        "packets_with_candidate_matches": len(matched_packets),
        "world_card_approval_counts": dict(sorted(card_approval.items())),
        "world_card_review_status_counts": dict(sorted(card_review.items())),
        "world_card_source_kind_counts": dict(sorted(card_source.items())),
        "review_protocol_flag_counts": dict(sorted(protocol_counts.items())),
        "review_protocol_addendum_flag_counts": dict(sorted(addendum_counts.items())),
        "histories_start_with_assistant": leading_assistant,
        "histories_empty": empty_history,
        "history_messages_total": history_messages,
        "source_version_verified": False,
        "historical_snapshot_temporality_proven": False,
        "world_component_isolation_proven": False,
        "reviewer_independence_proven": False,
        "protected_set_completeness_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    private = {
        "schema": "storyforge-r59-packet-evidence-associations-private-v1",
        "packet_file_sha256": packet_sha,
        "staged_file_sha256": staged_sha,
        "associations": associations,
    }
    return safe, private


def _create_only(path: Path, payload: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def run(packet_path: Path, staged_path: Path, output_dir: Path):
    packet_raw = _read_private(packet_path)
    staged_raw = _read_private(staged_path)
    packet_rows = _jsonl(packet_raw, "PACKET_JSONL_INVALID")
    staged_rows = _jsonl(staged_raw, "STAGED_JSONL_INVALID")
    safe, private = build_inventory(
        packet_rows, staged_rows, _digest(packet_raw), _digest(staged_raw)
    )
    if output_dir.exists() or output_dir.is_symlink():
        raise PacketInventoryHold("OUTPUT_EXISTS")
    if output_dir.resolve().is_relative_to(Path.cwd().resolve()):
        raise PacketInventoryHold("OUTPUT_INSIDE_REPO")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise PacketInventoryHold("OUTPUT_PARENT_INVALID")
    output_dir.mkdir(mode=0o700)
    try:
        _create_only(
            output_dir / "R59_PACKET_EVIDENCE_ASSOCIATIONS_PRIVATE.json",
            json.dumps(private, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n",
        )
        _create_only(
            output_dir / "R59_PACKET_EVIDENCE_INVENTORY_SAFE.json",
            json.dumps(safe, sort_keys=True, indent=2).encode() + b"\n",
        )
    except BaseException:
        for item in output_dir.iterdir():
            item.unlink()
        output_dir.rmdir()
        raise
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-jsonl", type=Path, required=True)
    parser.add_argument("--staged-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.packet_jsonl, args.staged_jsonl, args.output_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PacketInventoryHold, OSError):
        reason = "PACKET_EVIDENCE_INVENTORY_INPUT_OR_OUTPUT_HOLD"
    except Exception:  # noqa: BLE001 - never expose private values or paths
        reason = "PACKET_EVIDENCE_INVENTORY_INTERNAL_HOLD"
    print(json.dumps({
        "schema": SCHEMA, "status": "PACKET_EVIDENCE_ASSOCIATION_HOLD",
        "reason_code": reason, "quality_v1_admitted": 0,
        "training_authorized": False, "gpu_started": False,
        "r50_accessed": False, "private_values_emitted": False,
    }, sort_keys=True))
    return 42


if __name__ == "__main__":
    raise SystemExit(main())
