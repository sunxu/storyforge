"""R60 E0-E3 evidence bridge: reuse R59 Packet association for 3 previews.

No attestations are minted. Packet export snapshot is not the historical
Provider payload or proof that a world card existed at target time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

from r59_gold192_supabase_extract import PACKETS_SHA
from r59_packet_evidence_inventory import build_inventory
from r60_experimental_shape_adapter import GATES, NOT_ACTUAL_SENT
from r60_p3_stage_pair_probe import (
    ALLOWED_BASE, Hold, parse_lines, private_bytes,
)

SCHEMA = "storyforge_r60_experimental_e03_bridge_safe_v1"


def bridge(packet_raw: bytes, stage_raw: bytes, preview: list[dict],
           tasks: list[dict], frozen_sha: str):
    if (hashlib.sha256(packet_raw).hexdigest() != PACKETS_SHA
            or hashlib.sha256(stage_raw).hexdigest() != frozen_sha):
        raise Hold("PACKET_OR_STAGE_PIN_INVALID")
    packet_rows = parse_lines(packet_raw, 13)
    stage_rows = parse_lines(stage_raw, 192)
    # One authoritative R59 exact-association implementation, not duplicated.
    _, associations = build_inventory(
        packet_rows, stage_rows, PACKETS_SHA, frozen_sha
    )
    indexed = {x["case_id"]: x for x in associations["associations"]}
    if len(tasks) != 3 or len(preview) != 3:
        raise Hold("EXPERIMENTAL_THREE_ROW_INPUT_REQUIRED")
    ids = set()
    result = []
    counts = Counter()
    for item, row in zip(tasks, preview, strict=True):
        cid, target = item.get("case_id"), item.get("source_target_sha256")
        if (not isinstance(cid, str) or not cid or cid in ids
                or not isinstance(target, str) or len(target) != 64
                or item.get("context_provenance") != NOT_ACTUAL_SENT
                or item.get("stage_file_sha256") != frozen_sha
                or item.get("gates") != {gate: "HOLD_UNREVIEWED" for gate in GATES}):
            raise Hold("EXPERIMENTAL_TASK_IDENTITY_OR_GATE_DRIFT")
        ids.add(cid)
        assoc = indexed.get(cid)
        if not assoc or assoc["target_sha256"] != target:
            raise Hold("PACKET_EXACT_ASSOCIATION_MISSING")
        messages = row.get("messages")
        metadata = row.get("metadata")
        if (not isinstance(messages, list) or not messages
                or not isinstance(metadata, dict)
                or metadata.get("source_target_sha256") != target
                or hashlib.sha256(messages[-1]["content"].encode()).hexdigest() != target):
            raise Hold("PREVIEW_TARGET_PIN_MISMATCH")
        packet = packet_rows[assoc["packet_row_1based"] - 1]
        source = packet["cases"][assoc["case_index_0based"]]
        original_target_equal = source["target_assistant_text"] == messages[-1]["content"]
        staged_user_equal = source["current_user_text"] == messages[-2]["content"]
        if original_target_equal:
            counts["packet_target_exact_equal"] += 1
        else:
            counts["packet_target_not_equal"] += 1
        if staged_user_equal:
            counts["packet_user_exact_equal"] += 1
        else:
            counts["packet_user_not_equal"] += 1
        result.append({
            **item,
            "packet_source_sha256": PACKETS_SHA,
            "packet_case_locator": assoc["source_packet_locator"],
            "packet_snapshot_sha256": hashlib.sha256(json.dumps(
                source, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False,
            ).encode()).hexdigest(),
            "packet_world_card_snapshot_sha256": assoc["packet_world_card_sha256"],
            "packet_world_card_source_kind": assoc["packet_world_card_source_kind"],
            "packet_world_card_review_status": assoc["packet_world_card_review_status"],
            "packet_world_card_approved_for_system": assoc["packet_world_card_approved_for_system"],
            "packet_target_exact_equal": original_target_equal,
            "packet_current_user_exact_equal": staged_user_equal,
            "packet_world_card_is_historical_input_proven": False,
            "source_version_at_generation_proven": False,
            "request_payload_proven": False,
            "owner_evidence_independently_verified": False,
            "e0_e3_review_required": True,
            "gates": {gate: "HOLD_UNREVIEWED" for gate in GATES},
        })
    if len(result) != 3:
        raise Hold("EXPERIMENTAL_BRIDGE_COUNT_INVALID")
    safe = {
        "schema": SCHEMA,
        "status": "EXPERIMENTAL_PACKET_ASSOCIATIONS_3_CHECKED__E0_E3_HOLD",
        "candidate_cases_checked": 3,
        "packet_assoc_exact_cases": len(result),
        "packet_target_exact_equal": counts["packet_target_exact_equal"],
        "packet_target_not_equal": counts["packet_target_not_equal"],
        "packet_user_exact_equal": counts["packet_user_exact_equal"],
        "packet_user_not_equal": counts["packet_user_not_equal"],
        "packet_world_snapshot_is_historical_proof": False,
        "e0_e3_owner_review_complete": 0,
        "experimental_dataset_frozen": False,
        "actual_swift_collator_run": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return result, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("packet-jsonl", "stage-pairs", "experimental-preview",
                "experimental-tasks", "output-dir"):
        parser.add_argument("--" + arg, required=True, type=Path)
    args = parser.parse_args()
    try:
        packet_raw = private_bytes(args.packet_jsonl, 160_000_000)
        pairs = json.loads(private_bytes(args.stage_pairs, 2_000_000))
        if not isinstance(pairs, list) or len(pairs) != 1:
            raise Hold("STAGE_PAIRS_INVALID")
        pair = pairs[0]
        stage_path = Path(pair["stage_private_path"])
        stage_raw = private_bytes(stage_path, 160_000_000)
        preview = parse_lines(private_bytes(args.experimental_preview, 10_000_000), 3)
        tasks = parse_lines(private_bytes(args.experimental_tasks, 2_000_000), 3)
        out = args.output_dir
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()
                or stat.S_IMODE(out.parent.stat().st_mode) != 0o700
                or not out.is_relative_to(ALLOWED_BASE / "r59/private")):
            raise Hold("OUTPUT_DIR_INVALID")
        if not (
            hashlib.sha256(stage_raw).hexdigest() == pair["stage_sha256"]
            and len(pair["staged_case_ids_private"]) == pair["staged_status_total"]
        ):
            raise Hold("STAGE_PAIR_DRIFT")
        private, safe = bridge(packet_raw, stage_raw, preview, tasks, pair["stage_sha256"])
        out.mkdir(mode=0o700)
        for name, items, is_lines in (
            ("R60_E03_REVIEW_LOCATORS_PRIVATE.jsonl", private, True),
            ("R60_E03_SAFE.json", safe, False),
        ):
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(out / name, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                if is_lines:
                    for item in items:
                        stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
                else:
                    json.dump(items, stream, ensure_ascii=False, sort_keys=True, indent=2)
                    stream.write("\n")
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "EXPERIMENTAL_E03_BRIDGE_HOLD",
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
