"""Conservative R50 story/character identity and temporal-card screen (no GPU).

This script produces counts and story numbers only, never the source names or dialogs.
It cannot prove semantic world independence or substitute for a human review.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SOURCE = Path("evaluations/v0.2/source-archives/16-20")
GOLD = (
    (Path("evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl"), 87),
    (Path("evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl"), 108),
)
OLD_TEST = (Path("evaluations/v0.1/test/prompts.jsonl"), 20)


def read_rows(path: Path, expected: int) -> list[dict]:
    with path.open(encoding="utf-8-sig") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if len(rows) != expected or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected {expected} JSONL rows in {path.name}")
    return rows


def iso(text: str) -> datetime:
    result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("source timestamp is not timezone-aware")
    return result


def normalize(name: str) -> str:
    return unicodedata.normalize("NFKC", name).casefold().strip()


def card_characters(card: dict) -> list[dict]:
    v = card.get("v2_data") or {}
    if not isinstance(v, dict):
        raise ValueError("invalid v2 card")
    raw = v.get("characters") or []
    if not isinstance(raw, list):
        raise ValueError("invalid v2 character list")
    person = v.get("character")
    if isinstance(person, dict):
        raw = [*raw, person]
    if not all(isinstance(x, dict) for x in raw):
        raise ValueError("invalid character entry")
    return raw


def scan(repo: Path) -> dict:
    source = repo / SOURCE
    if not source.is_dir():
        raise ValueError("missing source root")
    worlds = []
    alias_worlds: dict[str, set[int]] = defaultdict(set)
    identifier_worlds: dict[str, set[int]] = defaultdict(set)
    alias_by_world: dict[int, set[str]] = {}
    for folder in sorted(source.iterdir()):
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("unexpected source entry")
        card = json.loads((folder / "story-cards.json").read_text(encoding="utf-8"))
        runtime = json.loads((folder / "runtime-context.json").read_text(encoding="utf-8"))
        rank = card["rank"]
        if rank != runtime["rank"] or card["story_id"] != runtime["story_id"]:
            raise ValueError(f"story metadata mismatch at {folder.name}")
        if not folder.name.startswith(f"{rank}-"):
            raise ValueError("folder rank differs")
        dates = card["chat_window"]
        first = iso(dates["first_message_at"])
        last = iso(dates["last_message_at"])
        if first > last:
            raise ValueError("source chat window inverted")
        exported = card["export_time_card"]
        last_edit = iso(exported["updated_at"])
        first_creation = iso(exported["created_at"])
        if first_creation > last:
            raise ValueError("source card created after last message")
        candidate_cards = [exported]
        for field in ("current_author_card", "current_public_projection"):
            if isinstance(card.get(field), dict):
                candidate_cards.append(card[field])
        aliases: set[str] = set()
        ids: set[str] = set()
        for candidate in candidate_cards:
            for char in card_characters(candidate):
                name = char.get("name")
                cid = char.get("id")
                if isinstance(name, str) and name.strip():
                    aliases.add(normalize(name))
                if isinstance(cid, str) and cid.strip():
                    ids.add(cid.strip())
        if not ids:
            raise ValueError(f"no character IDs in world {rank}")
        for alias in aliases:
            if len(alias) >= 2:
                alias_worlds[alias].add(rank)
        for cid in ids:
            identifier_worlds[cid].add(rank)
        alias_by_world[rank] = aliases
        worlds.append({
            "rank": rank,
            "character_ids_count": len(ids),
            "character_names_count": len(aliases),
            "card_created_after_first_message": first_creation > first,
            "export_card_updated_after_first_message": last_edit > first,
            "source_export_card_updated_after_last_message": last_edit > last,
            "timepoint_card_provenance": "PER_CASE_REQUIRED",
        })
    if {x["rank"] for x in worlds} != set(range(16, 21)):
        raise ValueError("expected exactly source worlds 16-20")
    cross_ids = sorted({tuple(sorted(used)) for used in identifier_worlds.values() if len(used) > 1})
    cross_alias = sorted({tuple(sorted(used)) for used in alias_worlds.values() if len(used) > 1})

    # Names may be shared incidentally. Text mentions are warnings, NOT automatic proof
    # of world leakage. Never write text or names to the result.
    old_texts = []
    for path, n in (*GOLD, OLD_TEST):
        for row in read_rows(repo / path, n):
            msgs = row.get("messages")
            if not isinstance(msgs, list):
                raise ValueError(f"invalid historic messages in {path}")
            old_texts.append("\n".join(str(m.get("content", "")) for m in msgs))
    normalized_texts = [normalize(x) for x in old_texts]
    history_mention_counts = {}
    for w in worlds:
        # Two-character Chinese names and generic terms are too ambiguous for
        # simple substring searching; they must be checked manually.
        qualified = [a for a in alias_by_world[w["rank"]] if len(a) >= 3]
        history_mention_counts[str(w["rank"])] = sum(
            any(alias in text for alias in qualified) for text in normalized_texts
        )

    return {
        "schema": "storyforge-r50-world-alias-and-card-timeline-screen-v1",
        "status": "AUTOMATED_CANDIDATE_SCREEN_DONE__MANUAL_WORLD_ISOLATION_PENDING",
        "worlds": worlds,
        "same_character_id_world_groups": [list(x) for x in cross_ids],
        "same_name_world_groups": [list(x) for x in cross_alias],
        "historic_rows_scanned": len(normalized_texts),
        "historical_rows_with_name_mentions_by_world": history_mention_counts,
        "historic_mention_is_not_proof_of_shared_world": True,
        "short_name_and_hidden_alias_review": "PENDING",
        "full_dialog_near_duplicate_screen": "PENDING",
        "private_r45_train_val_comparison": "PENDING",
        "human_story_cutoff_review": "PENDING",
        "final_heldout_cases": 0,
        "gpu_executed": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = scan(args.repo.resolve())
        body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(body)
        else:
            sys.stdout.write(body)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"R50_WORLD_ALIAS_SCREEN_BLOCKED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
