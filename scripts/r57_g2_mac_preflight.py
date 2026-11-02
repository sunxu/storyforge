"""Owner Mac G2 zero-write preflight of eight immutable source byte pins.

Only fixed allowlisted Gold/v0.1 files and R46/R54 private compiled Trainer
paths are read; no automatic filesystem search, remote call, or R50 access.
Result contains fixed source names/statuses only; never paths, hashes or prose.
"""

import argparse
import json
import sys
from pathlib import Path

import r57_source_index_export as frozen

SCHEMA = "storyforge-r57-g2-mac-eight-source-preflight-safe-v1"
PUBLIC = tuple(frozen.GIT_BLOBS)
PRIVATE = tuple(frozen.HISTORICAL_TRAINER_SHA256)


def preflight(repo_root, private_root=None, *, only_public=False, reader=None):
    """Return summary and success flag without writing or disclosing source bytes."""
    reader = frozen._read if reader is None else reader
    repo = Path(repo_root).resolve(strict=False)
    private = Path(private_root).resolve(strict=False) if private_root is not None else None
    sources = {}
    if not only_public and private is not None and (
        repo == private or repo in private.parents or private in repo.parents
    ):
        return {
            "schema": SCHEMA,
            "status": "HOLD_PRIVATE_DIRECTORY_NOT_SEPARATE",
            "source_status": {},
            "all_pins_verified": False,
            "protected_evaluation_accessed": False,
            "training_authorized": False,
        }, False
    for name in (*PUBLIC, *((PRIVATE) if not only_public else ())):
        group, relative, _ = frozen.SOURCE_PATHS[name]
        if group == "PRIVATE" and private is None:
            status = "MISSING_PRIVATE_ROOT"
        else:
            root = repo if group == "REPO" else private
            try:
                payload = reader(root, relative, frozen.MAX_SOURCE_BYTES)
                if name in frozen.GIT_BLOBS:
                    good = frozen._git_blob(payload) == frozen.GIT_BLOBS[name]
                else:
                    good = frozen._digest(payload) == frozen.HISTORICAL_TRAINER_SHA256[name]
                status = "BYTE_PIN_PASS" if good else "BYTE_PIN_MISMATCH"
            except FileNotFoundError:
                status = "MISSING"
            except (OSError, ValueError, TypeError):
                status = "UNSAFE_OR_UNREADABLE"
        sources[name] = status
    ready = all(value == "BYTE_PIN_PASS" for value in sources.values())
    return {
        "schema": SCHEMA,
        "status": (
            "FOUR_PUBLIC_GIT_BLOB_BYTE_PINS_PASS__NOT_FULL_G2"
            if ready and only_public else
            "EIGHT_SOURCE_BYTE_PINS_PASS__EXACT_OVERLAP_AND_WORLD_STILL_PENDING"
            if ready else "G2_SOURCE_BYTE_PREFLIGHT_HOLD"
        ),
        "source_status": sources,
        "checked_collection_count": len(sources),
        "byte_pin_pass_count": sum(v == "BYTE_PIN_PASS" for v in sources.values()),
        "all_pins_verified": ready,
        "exact_target_lineage_replayed": False,
        "world_alias_graph_certified": False,
        "r50_content_accessed": False,
        "protected_evaluation_accessed": False,
        "training_authorized": False,
        "v04_admitted": 0,
    }, ready


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--private-root", type=Path)
    ap.add_argument("--only-public", action="store_true")
    args = ap.parse_args()
    result, ok = preflight(args.repo_root, args.private_root, only_public=args.only_public)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
