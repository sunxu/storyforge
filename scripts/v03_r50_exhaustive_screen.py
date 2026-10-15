"""Exhaustive all-offset long substring screening for R50 story sources.

Compare 120-Unicode-codepoint windows at EVERY normalized offset, rather than
the prior sampled stride. Output aggregate counts only; no narrative text or
window fingerprints leave the process. No fuzzy/paraphrase or R45 private pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from v03_r50_text_reuse_screen import (
    BLOCK, HIST, SOURCE, MIN_EXACT, digest, normalized, read_jsonl, strings_from_messages,
)


def all_windows(text: str):
    """Every fixed-width normalized codepoint window, including shifted starts."""
    for i in range(max(0, len(text) - BLOCK + 1)):
        yield digest(text[i : i + BLOCK])


def scan(repo: Path) -> dict:
    historical_exact: set[bytes] = set()
    historical_windows: set[bytes] = set()
    historic = 0
    for path, expected in HIST:
        for item in read_jsonl(repo / path, expected):
            historic += 1
            for text in strings_from_messages(item.get("messages")):
                if len(text) >= MIN_EXACT:
                    historical_exact.add(digest(text))
                historical_windows.update(all_windows(text))
    if historic != 215:
        raise ValueError("historical count unexpectedly changed")

    owner_by_exact: dict[bytes, set[int]] = defaultdict(set)
    owner_by_window: dict[bytes, set[int]] = defaultdict(set)
    worlds = []
    for folder in sorted((repo / SOURCE).iterdir()):
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError("bad source entry")
        rank = int(folder.name.split("-", 1)[0])
        path = folder / (folder.name + ".jsonl")
        item, = read_jsonl(path, 1)
        if item.get("rank") != rank:
            raise ValueError(f"source rank mismatch: {rank}")
        texts = strings_from_messages(item.get("messages"))
        exact_hits: set[bytes] = set()
        window_hits: set[bytes] = set()
        for text in texts:
            if len(text) >= MIN_EXACT:
                key = digest(text)
                owner_by_exact[key].add(rank)
                if key in historical_exact:
                    exact_hits.add(key)
            for key in all_windows(text):
                owner_by_window[key].add(rank)
                if key in historical_windows:
                    window_hits.add(key)
        worlds.append({
            "rank": rank,
            "nonempty_message_count": len(texts),
            "historic_exact_long_message_fingerprints": len(exact_hits),
            "historic_all_offset_120_codepoint_fingerprints": len(window_hits),
        })
    if {x["rank"] for x in worlds} != set(range(16, 21)):
        raise ValueError("invalid new worlds")

    def pair_groups(owner: dict[bytes, set[int]]) -> list[list[int]]:
        pairs = set()
        for r in owner.values():
            if len(r) > 1:
                a = sorted(r)
                for i, v in enumerate(a):
                    for z in a[i + 1 :]:
                        pairs.add((v, z))
        return [list(z) for z in sorted(pairs)]

    return {
        "schema": "storyforge-r50-exhaustive-codepoint-overlap-v1",
        "status": "ALL_OFFSET_120_CODEPOINT_SCREEN_DONE__SEMANTIC_REVIEW_PENDING",
        "method": "NFKC + casefold + whitespace collapse; all possible 120-codepoint start offsets",
        "window_length_codepoints": BLOCK,
        "window_step": 1,
        "digest": "BLAKE2b-128 as exact-text candidate fingerprint",
        "historic_records": historic,
        "worlds": worlds,
        "new_world_shared_message_pairs": pair_groups(owner_by_exact),
        "new_world_shared_120_codepoint_window_pairs": pair_groups(owner_by_window),
        "candidate_window_collision_verification": "not byte-by-byte verified",
        "semantic_near_duplicate_detection": "PENDING",
        "short_context_overlap": "NOT_COVERED",
        "private_r45_train_val": "PENDING",
        "model_quality_promoted": False,
        "heldout_test_cases": 0,
        "gpu_executed": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--output", type=Path)
    opts = p.parse_args()
    try:
        result = scan(opts.repo.resolve())
        body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if opts.output:
            with opts.output.open("x", encoding="utf-8") as stream:
                stream.write(body)
        else:
            sys.stdout.write(body)
    except (OSError, ValueError, TypeError, KeyError) as err:
        print(f"R50_EXHAUSTIVE_SCREEN_BLOCKED: {type(err).__name__}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
