"""R50 private R45 49/15 historical-leakage guard. Runs only with owner-held files.

Report is aggregate and contains NO private texts, paths or source UUIDs.
On missing/altered inputs fail closed. Never runs a paid Job or modifies inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from v03_r50_exhaustive_screen import all_windows
from v03_r50_text_reuse_screen import (
    MIN_EXACT, SOURCE, digest, read_jsonl, strings_from_messages,
)

FROZEN = {
    "train": {
        "sha256": "e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742",
        "count": 49,
    },
    "validation": {
        "sha256": "5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963",
        "count": 15,
    },
}


def file_hash(path: Path) -> str:
    hashed = hashlib.sha256()
    with path.open("rb") as data:
        for buf in iter(lambda: data.read(1024 * 1024), b""):
            hashed.update(buf)
    return hashed.hexdigest()


def verify(repo: Path, train: Path, validation: Path, *,
           expected: dict | None = None) -> dict:
    checks = FROZEN if expected is None else expected
    paths = {"train": train, "validation": validation}
    historical_ids: set[str] = set()
    hist_exact: set[bytes] = set()
    hist_windows: set[bytes] = set()
    counts = {}
    for split, path in paths.items():
        spec = checks[split]
        if not path.is_file() or path.is_symlink() or file_hash(path) != spec["sha256"]:
            raise ValueError(f"R45 {split} frozen file SHA256 mismatch")
        actual_count = 0
        for row in read_jsonl(path, spec["count"]):
            actual_count += 1
            md = row.get("metadata")
            if not isinstance(md, dict) or not isinstance(md.get("source_story_id"), str):
                raise ValueError(f"R45 {split} source_story_id missing")
            if not md["source_story_id"].strip():
                raise ValueError("R45 empty source story id")
            historical_ids.add(md["source_story_id"])
            messages = strings_from_messages(row.get("messages"))
            for txt in messages:
                if len(txt) >= MIN_EXACT:
                    hist_exact.add(digest(txt))
                hist_windows.update(all_windows(txt))
        counts[split] = actual_count

    new_ids: set[str] = set()
    hits_exact = 0
    hits_windows = 0
    worlds = 0
    for directory in sorted((repo / SOURCE).iterdir()):
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("invalid new source directory")
        age = json.loads((directory / "age-review.json").read_text(encoding="utf-8"))
        story_id = age.get("story_id")
        if not isinstance(story_id, str) or not story_id:
            raise ValueError("invalid new source story id")
        new_ids.add(story_id)
        obj, = read_jsonl(directory / (directory.name + ".jsonl"), 1)
        worlds += 1
        for txt in strings_from_messages(obj.get("messages")):
            if len(txt) >= MIN_EXACT and digest(txt) in hist_exact:
                hits_exact += 1
            # Count matching normalized all-offset 120-codepoint windows.
            # This counts possible collisions, not semantically verified matches.
            for token in all_windows(txt):
                if token in hist_windows:
                    hits_windows += 1
    if worlds != 5 or len(new_ids) != 5:
        raise ValueError("expected five distinct source worlds")
    collisions = len(new_ids & historical_ids)
    if collisions or hits_exact or hits_windows:
        raise ValueError("R45 candidate world/text overlap detected; HOLD and manual review")
    return {
        "schema": "storyforge-r50-private-r45-isolation-v1",
        "status": "R45_FROZEN_49_15_EXACT_SCREEN_PASS__SEMANTIC_REVIEW_PENDING",
        "verified_r45_counts": counts,
        "r45_distinct_story_ids": len(historical_ids),
        "new_world_count": worlds,
        "exact_world_id_conflicts": collisions,
        "exact_long_message_hit_count": hits_exact,
        "all_offset_120_codepoint_window_hit_count": hits_windows,
        "short_or_paraphrased_context_review": "PENDING",
        "incomplete_or_hidden_world_aliases": "PENDING",
        "frozen_r45_hashes_verified": True,
        "raw_private_text_or_ids_emitted": False,
        "heldout_cases_sealed": 0,
        "gpu_executed": False,
        "model_promotion": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        output = args.output.resolve()
        if output == repo or repo in output.parents:
            raise ValueError("private report output must be OUTSIDE the Git repository")
        result = verify(repo, args.train, args.validation)
        raw = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as report:
            report.write(raw)
        print(result["status"])
        print("R50_PRIVACY_PRESERVING_PRIVATE_REPORT_WRITTEN")
    except (OSError, ValueError, TypeError, KeyError) as err:
        print(f"R50_PRIVATE_R45_HOLD: {type(err).__name__}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
