"""R50 privacy-preserving point-in-time character-card and message chronology screen.

Counts metadata only; it never prints story text, character names or messages.
Flags later card edits without inventing historically available card versions.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SOURCE = Path("evaluations/v0.2/source-archives/16-20")


def when(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timezone-naive timestamp")
    return stamp


def run(repo: Path) -> dict:
    rows = []
    root = repo / SOURCE
    if not root.is_dir():
        raise ValueError("source directory missing")
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("unexpected source entry")
        with (folder / "story-cards.json").open(encoding="utf-8") as file:
            card = json.load(file)
        with (folder / "runtime-context.json").open(encoding="utf-8") as file:
            runtime = json.load(file)
        with (folder / (folder.name + ".jsonl")).open(encoding="utf-8-sig") as file:
            lines = [line for line in file if line.strip()]
        if len(lines) != 1:
            raise ValueError("expected exactly one JSONL transcript object per world")
        transcript = json.loads(lines[0])
        rank = card["rank"]
        if rank != runtime["rank"] or rank != transcript["rank"]:
            raise ValueError("source rank mismatch")
        if card["story_id"] != runtime["story_id"]:
            raise ValueError("story id mismatch")
        if card["session_id"] != runtime["session_id"]:
            raise ValueError("session id mismatch")
        msgs = transcript["messages"]
        if not isinstance(msgs, list):
            raise ValueError("messages must be an array")
        span = card["chat_window"]
        first = when(span["first_message_at"])
        last = when(span["last_message_at"])
        if last < first:
            raise ValueError("invalid chat window")
        export = card["export_time_card"]
        card_created = when(export["created_at"])
        card_updated = when(export["updated_at"])
        if card_created > card_updated:
            raise ValueError("card updated before creation")
        valid_times = []
        missing_message_times = 0
        earlier_than_first = 0
        later_than_last = 0
        before_card_creation = 0
        before_card_update = 0
        for msg in msgs:
            if not isinstance(msg, dict):
                raise ValueError("non-object message")
            created = msg.get("created_at")
            if not created:
                missing_message_times += 1
                continue
            timestamp = when(created)
            valid_times.append(timestamp)
            earlier_than_first += int(timestamp < first)
            later_than_last += int(timestamp > last)
            before_card_creation += int(timestamp < card_created)
            before_card_update += int(timestamp < card_updated)
        backward_time_transitions = sum(
            b < a for a, b in zip(valid_times, valid_times[1:], strict=False)
        )
        versions = card.get("content_versions") or []
        moderation = card.get("moderation_source_snapshots") or []
        if not isinstance(versions, list) or not isinstance(moderation, list):
            raise ValueError("invalid card snapshot data")
        rows.append({
            "story_number": rank,
            "message_records": len(msgs),
            "messages_with_valid_timestamp": len(valid_times),
            "messages_missing_timestamp": missing_message_times,
            "messages_outside_reported_first_bound": earlier_than_first,
            "messages_outside_reported_last_bound": later_than_last,
            "messages_before_card_creation": before_card_creation,
            "messages_before_export_card_update": before_card_update,
            "timestamp_order_reversals": backward_time_transitions,
            "export_card_last_edited_after_chat_start": card_updated > first,
            "export_card_last_edited_after_chat_end": card_updated > last,
            "content_version_records": len(versions),
            "moderation_snapshot_records": len(moderation),
            "per_test_cutoff_reconstruction": "REQUIRED",
        })
    if {row["story_number"] for row in rows} != set(range(16, 21)):
        raise ValueError("expected stories 16-20 exactly")
    return {
        "schema": "storyforge-r50-point-in-time-source-screen-v1",
        "status": "CHRONOLOGY_METADATA_CHECKED__POINT_IN_TIME_MANUAL_REVIEW_PENDING",
        "stories": rows,
        "total_message_records": sum(x["message_records"] for x in rows),
        "limitations": [
            "An edit timestamp cannot prove which card fields were present at an earlier time.",
            "Saved relationship checkpoints are not exact model-request snapshots.",
            "Each future Held-out case needs a source cutoff and separately grounded card facts.",
        ],
        "fresh_heldout_cases": 0,
        "paid_gpu_executed": False,
        "model_promotion": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = run(args.repo.resolve())
        body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as f:
                f.write(body)
        else:
            sys.stdout.write(body)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"R50_CHRONOLOGY_BLOCKED: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
