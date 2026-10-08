from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawBundle:
    records: list[dict[str, Any]]

    @classmethod
    def load(cls, root: Path) -> RawBundle:
        records: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*.jsonl")):
            with path.open("r", encoding="utf-8-sig") as fh:
                for line_no, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"invalid JSON: {path}:{line_no}: {exc}") from exc
                    records.append(record)
        if not records:
            raise ValueError(f"no JSONL records found under {root}")
        return cls(records=records)


def _stable_story_order(story_ids: Iterable[str]) -> list[str]:
    return sorted(set(story_ids), key=lambda s: hashlib.sha256(s.encode()).hexdigest())


def assign_story_splits(story_ids: Iterable[str]) -> dict[str, str]:
    ordered = _stable_story_order(story_ids)
    count = len(ordered)
    if count < 3:
        return {story_id: "train" for story_id in ordered}
    test_n = max(1, round(count * 0.10))
    val_n = max(1, round(count * 0.10))
    train_n = max(1, count - test_n - val_n)
    mapping: dict[str, str] = {}
    for story_id in ordered[:train_n]:
        mapping[story_id] = "train"
    for story_id in ordered[train_n : train_n + val_n]:
        mapping[story_id] = "validation"
    for story_id in ordered[train_n + val_n :]:
        mapping[story_id] = "test"
    return mapping


def _story_card_text(card: dict[str, Any]) -> str:
    payload = {
        "title": card.get("title"),
        "description": card.get("description"),
        "story": card.get("v2_data", {}),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _build_system_prompt(card: dict[str, Any] | None, opening: dict[str, Any] | None) -> str:
    parts = [
        "你是互动叙事模型。严格遵守作品设定和角色人格，保持角色自主性、时空连续性与既有关系；不要替用户角色擅自决定其主观意愿。",
        "仅根据当前输入中已经提供的事实继续剧情，不得利用未来消息或未来状态。",
    ]
    if card is not None:
        parts.append("\n[作品设定]\n" + _story_card_text(card))
    if opening is not None and opening.get("content"):
        parts.append("\n[开场背景]\n" + str(opening["content"]))
    return "\n".join(parts)


def compile_samples(
    bundle: RawBundle, history_messages: int = 12
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if history_messages < 1:
        raise ValueError("history_messages must be >= 1")

    metadata_by_story: dict[str, dict[str, Any]] = {}
    cards_by_story: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sessions: dict[str, dict[str, Any]] = {}
    openings: dict[str, dict[str, Any]] = {}
    messages: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in bundle.records:
        rtype = record.get("record_type")
        if rtype == "story_metadata":
            metadata_by_story[record["story_id"]] = record
        elif rtype == "story_card":
            cards_by_story[record["story_id"]].append(record)
        elif rtype == "session":
            sessions[record["transcript_id"]] = record
        elif rtype == "opening":
            openings[record["transcript_id"]] = record
        elif rtype == "message":
            messages[record["transcript_id"]].append(record)

    split_map = assign_story_splits(metadata_by_story)
    samples: list[dict[str, Any]] = []
    issues: list[str] = []

    for transcript_id, transcript_messages in messages.items():
        transcript_messages.sort(key=lambda m: (m.get("sequence", 0), m.get("turn_index", 0)))
        session = sessions.get(transcript_id)
        story_id = (session.get("session_info") or {}).get("story_id") if session else None
        if not story_id:
            issues.append(f"missing story_id for transcript {transcript_id}")
            continue

        cards = cards_by_story.get(story_id, [])
        cards_by_version = {card.get("version_id"): card for card in cards}
        opening = openings.get(transcript_id)

        for idx, target in enumerate(transcript_messages):
            if target.get("role") != "assistant" or not target.get("is_selected"):
                continue
            target_content = target.get("content") or ""
            if not target_content.strip():
                issues.append(f"empty selected assistant target {target.get('message_id')}")
                continue

            previous = transcript_messages[:idx]
            current_user_idx = None
            for j in range(len(previous) - 1, -1, -1):
                if previous[j].get("role") == "user" and (previous[j].get("content") or "").strip():
                    current_user_idx = j
                    break
            if current_user_idx is None:
                issues.append(f"no preceding user message for target {target.get('message_id')}")
                continue

            start = max(0, current_user_idx - history_messages + 1)
            dialogue = previous[start : current_user_idx + 1]
            dialogue = [
                m
                for m in dialogue
                if m.get("role") in {"user", "assistant"} and (m.get("content") or "").strip()
            ]

            wanted_version = target.get("story_card_version_id")
            card = cards_by_version.get(wanted_version)
            if card is None and session:
                for version in session.get("story_card_version_ids") or []:
                    if version in cards_by_version:
                        card = cards_by_version[version]
                        break
            if card is None and cards:
                card = max(cards, key=lambda c: c.get("source_updated_at") or "")

            messages_out: list[dict[str, str]] = [
                {"role": "system", "content": _build_system_prompt(card, opening)}
            ]
            for msg in dialogue:
                messages_out.append({"role": msg["role"], "content": str(msg["content"])})
            messages_out.append({"role": "assistant", "content": target_content})

            selection = target.get("selection") or {}
            sample_ids = selection.get("sample_ids") or selection.get("sample_id") or []
            if isinstance(sample_ids, int):
                sample_ids = [sample_ids]
            if not sample_ids:
                sample_ids = target.get("selected_sample_ids") or []

            samples.append(
                {
                    "id": f"sample-{len(samples) + 1:06d}",
                    "messages": messages_out,
                    "metadata": {
                        "story_id": story_id,
                        "story_title": (metadata_by_story.get(story_id) or {}).get("title"),
                        "transcript_id": transcript_id,
                        "session_id": target.get("session_id"),
                        "target_message_id": target.get("message_id"),
                        "target_sequence": target.get("sequence"),
                        "story_card_version_id": card.get("version_id") if card else None,
                        "story_card_version_status": target.get("story_card_version_status"),
                        "opening_status": (
                            opening.get("selection_status") if opening else "missing_or_unresolved"
                        ),
                        "context_message_count": len(dialogue),
                        "source_sample_ids": sample_ids,
                        "split": split_map.get(story_id, "train"),
                    },
                }
            )

    manifest = {
        "schema_version": "0.1",
        "sample_count": len(samples),
        "story_count": len({s["metadata"]["story_id"] for s in samples}),
        "split_story_counts": {
            split: len(
                {
                    s["metadata"]["story_id"]
                    for s in samples
                    if s["metadata"]["split"] == split
                }
            )
            for split in ("train", "validation", "test")
        },
        "split_sample_counts": {
            split: sum(1 for s in samples if s["metadata"]["split"] == split)
            for split in ("train", "validation", "test")
        },
        "history_messages": history_messages,
        "issues": issues,
    }
    return samples, manifest


def write_compiled(
    samples: list[dict[str, Any]], manifest: dict[str, Any], output: Path
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for split in ("train", "validation", "test"):
        with (output / f"{split}.jsonl").open("w", encoding="utf-8") as fh:
            for sample in samples:
                if sample["metadata"]["split"] == split:
                    fh.write(json.dumps(sample, ensure_ascii=False) + "\n")
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
