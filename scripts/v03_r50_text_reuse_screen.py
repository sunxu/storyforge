"""R50 source transcript exact and long-fragment reuse screen.

This is an automated *candidate* screen, not proof of independence. Results
contain only story numbers and counts, never story text or fragment hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

SOURCE = Path("evaluations/v0.2/source-archives/16-20")
HIST = (
    (Path("evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl"), 87),
    (Path("evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl"), 108),
    (Path("evaluations/v0.1/test/prompts.jsonl"), 20),
)
MIN_EXACT = 80
BLOCK = 120
STEP = 80


def normalized(content: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", content).casefold()).strip()


def digest(text: str) -> bytes:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


def spans(content: str):
    if len(content) < BLOCK:
        return
    positions = list(range(0, len(content) - BLOCK + 1, STEP))
    if not positions or positions[-1] != len(content) - BLOCK:
        positions.append(len(content) - BLOCK)
    for pos in positions:
        yield digest(content[pos:pos + BLOCK])


def strings_from_messages(messages: object) -> list[str]:
    if not isinstance(messages, list):
        raise ValueError("source row lacks messages array")
    out = []
    for msg in messages:
        if not isinstance(msg, dict):
            raise ValueError("invalid message")
        value = msg.get("content")
        if isinstance(value, str) and value.strip():
            out.append(normalized(value))
    return out


def read_jsonl(path: Path, count: int | None = None):
    rows = 0
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if not line.strip():
                raise ValueError("unexpected blank JSONL line")
            rows += 1
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("unexpected non-object JSONL")
            yield obj
    if count is not None and rows != count:
        raise ValueError(f"unexpected count in {path.name}: {rows}, expected {count}")


def scan(repo: Path) -> dict:
    historic_exact = set()
    historic_blocks = set()
    old_rows = 0
    for path, expected in HIST:
        for obj in read_jsonl(repo / path, expected):
            old_rows += 1
            for text in strings_from_messages(obj.get("messages")):
                if len(text) >= MIN_EXACT:
                    historic_exact.add(digest(text))
                historic_blocks.update(spans(text))
    if old_rows != 215:
        raise ValueError("expected 215 historical records")

    seen_blocks: dict[bytes, set[int]] = defaultdict(set)
    seen_exact: dict[bytes, set[int]] = defaultdict(set)
    world_counts = []
    for directory in sorted((repo / SOURCE).iterdir()):
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("unexpected source directory")
        rank = int(directory.name.split("-", 1)[0])
        path = directory / (directory.name + ".jsonl")
        msg_count = 0
        exact_hits = set()
        block_hits = set()
        unique_message_sha = set()
        unique_blocks = set()
        rows = 0
        for obj in read_jsonl(path, 1):
            rows += 1
            if obj.get("rank") != rank:
                raise ValueError("source transcript rank mismatch")
            for content in strings_from_messages(obj.get("messages")):
                msg_count += 1
                if len(content) >= MIN_EXACT:
                    h = digest(content)
                    unique_message_sha.add(h)
                    seen_exact[h].add(rank)
                    if h in historic_exact:
                        exact_hits.add(h)
                for h in spans(content):
                    unique_blocks.add(h)
                    seen_blocks[h].add(rank)
                    if h in historic_blocks:
                        block_hits.add(h)
        if rows != 1:
            raise ValueError("expected one transcript record")
        world_counts.append({
            "rank": rank,
            "text_messages": msg_count,
            "unique_long_messages": len(unique_message_sha),
            "unique_long_blocks": len(unique_blocks),
            "historic_exact_message_hit_count": len(exact_hits),
            "historic_120char_block_hit_count": len(block_hits),
        })
    if {w["rank"] for w in world_counts} != set(range(16, 21)):
        raise ValueError("unexpected source set")
    inter_exact = set()
    inter_block = set()
    for ranks in seen_exact.values():
        if len(ranks) > 1:
            for a in ranks:
                for b in ranks:
                    if a < b:
                        inter_exact.add((a, b))
    for ranks in seen_blocks.values():
        if len(ranks) > 1:
            for a in ranks:
                for b in ranks:
                    if a < b:
                        inter_block.add((a, b))
    return {
        "schema": "storyforge-r50-source-text-reuse-screen-v1",
        "status": "LONG_TEXT_REUSE_SCREEN_COMPLETED__HUMAN_REVIEW_PENDING",
        "historic_records": old_rows,
        "min_exact_message_chars": MIN_EXACT,
        "fragment_chars": BLOCK,
        "fragment_step": STEP,
        "worlds": world_counts,
        "cross_world_exact_message_pairs": [list(v) for v in sorted(inter_exact)],
        "cross_world_shared_long_fragment_pairs": [list(v) for v in sorted(inter_block)],
        "no_raw_narrative_or_fragment_hashes_in_report": True,
        "fuzzy_paraphrase_and_short_message_detection": "NOT_COVERED",
        "private_r45_train_val": "NOT_COVERED",
        "semantic_alias_and_point_in_time": "MANUAL_REVIEW_PENDING",
        "fresh_heldout_cases": 0,
        "gpu_executed": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        report = scan(args.repo.resolve())
        raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as fh:
                fh.write(raw)
        else:
            sys.stdout.write(raw)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"R50_TEXT_REUSE_SCREEN_BLOCKED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
