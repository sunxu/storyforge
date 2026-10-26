"""R57 G2: offline byte-pinned exact overlap replay without story-metadata dependency.

The four Git files can be verified directly from a checkout. Four historical
compiled Trainer files are strictly private and must be supplied by the Owner.
No model/HF/network/R50 access; emits only aggregate counts.
"""

import argparse
import hashlib
import itertools
import json
import os
import re
import sys
from pathlib import Path

import r57_source_index_export as frozen

SOURCE_IDS = tuple(frozen.SOURCE_PATHS)
GIT_SOURCES = tuple(name for name in SOURCE_IDS if name in frozen.GIT_BLOBS)
HISTORICAL_SOURCES = tuple(name for name in SOURCE_IDS if name in frozen.HISTORICAL_TRAINER_SHA256)
SCHEMA = "storyforge-r57-g2-byte-pinned-exact-replay-safe-v1"
MAX_LINE_BYTES = 3 * 1024 * 1024
SHA = re.compile(r"^[0-9a-f]{64}$")


class ExactReplayHold(ValueError):
    """Input, digest, or expected historical metadata failed closed."""


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _shape(raw, source_name):
    """Return private in-memory projections only. Never serialize them to report."""
    expected = frozen.SOURCE_PATHS[source_name][2]
    lines = raw.splitlines()
    if len(lines) != expected or any(not item.strip() for item in lines):
        raise ExactReplayHold("historical collection row count mismatch")
    parsed = []
    counters = {"rows_with_metadata": 0, "rows_without_metadata": 0,
                "declared_target_hashes_verified": 0,
                "rows_without_declared_target_hash": 0}
    mixed = {"gold108_standard": 0, "gold108_legacy": 0}
    for line in lines:
        if len(line) > MAX_LINE_BYTES:
            raise ExactReplayHold("oversized JSONL row")
        try:
            record = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise ExactReplayHold("malformed JSONL row") from exc
        if not isinstance(record, dict):
            raise ExactReplayHold("expected JSON object row")
        messages = frozen._project_messages(record.get("messages"))
        md = record.get("metadata")
        if md is None:
            counters["rows_without_metadata"] += 1
            md = {}
        elif isinstance(md, dict):
            counters["rows_with_metadata"] += 1
        else:
            raise ExactReplayHold("unsupported metadata type")
        target_digest = _hash(messages[-1]["content"].encode("utf-8"))
        declared = [name for name in frozen.TARGET_HASH_FIELDS if name in md]
        if source_name == "GOLD87":
            if declared != ["target_sha256_utf8"] or not md.get("story_id"):
                raise ExactReplayHold("Gold87 source metadata signature mismatch")
        elif source_name == "GOLD108":
            primary = md.get("story_id")
            legacy = md.get("source_story_id")
            if (bool(primary) == bool(legacy)) or len(declared) != 1:
                raise ExactReplayHold("ambiguous Gold108 metadata schema")
            if primary and declared == ["target_sha256"]:
                mixed["gold108_standard"] += 1
            elif legacy and declared == ["target_content_sha256"]:
                mixed["gold108_legacy"] += 1
            else:
                raise ExactReplayHold("unknown Gold108 schema combination")
        if declared:
            if len(declared) != 1 or not isinstance(md[declared[0]], str):
                raise ExactReplayHold("ambiguous or malformed metadata target SHA")
            if not SHA.fullmatch(md[declared[0]]) or md[declared[0]] != target_digest:
                raise ExactReplayHold("target SHA mismatch with source metadata")
            counters["declared_target_hashes_verified"] += 1
        else:
            counters["rows_without_declared_target_hash"] += 1
        # Full role/content projection deliberately includes final target. It is not
        # the original byte-wise ms-swift train.jsonl, template or masked token input.
        parsed.append({
            "target": target_digest,
            "input": frozen._projection_sha(messages),
            "history": frozen._projection_sha(messages[:-1]),
        })
    if source_name == "GOLD108" and mixed != {"gold108_standard": 105, "gold108_legacy": 3}:
        raise ExactReplayHold("Gold108 frozen schema distribution changed")
    return parsed, counters


def replay_payloads(payloads, *, require_all=False):
    """Given already authenticated bytes, compare exact, metadata-free projections.

    This helper does NOT authenticate the file bytes; the command-line file reader
    calls verify_source_pin() before running this comparison.
    """
    if not isinstance(payloads, dict) or not payloads or not set(payloads) <= set(SOURCE_IDS):
        raise ExactReplayHold("unsupported source collection")
    if require_all and set(payloads) != set(SOURCE_IDS):
        raise ExactReplayHold("full replay requires all eight historical sources")
    rows, stats = {}, {}
    for name in SOURCE_IDS:
        if name in payloads:
            rows[name], stats[name] = _shape(payloads[name], name)
    keysets = {name: {key: {r[key] for r in values} for key in ("target", "input", "history")}
               for name, values in rows.items()}
    pairs = []
    for a, b in itertools.combinations(keysets, 2):
        pairs.append({
            "a": a, "b": b,
            "target_exact": len(keysets[a]["target"] & keysets[b]["target"]),
            "role_content_full_exact": len(keysets[a]["input"] & keysets[b]["input"]),
            "role_content_history_exact": len(keysets[a]["history"] & keysets[b]["history"]),
        })
    gold_targets = keysets.get("GOLD87", {}).get("target", set()) | keysets.get(
        "GOLD108", {}
    ).get("target", set())
    actual_train = set().union(*(keysets.get(name, {}).get("target", set())
                                 for name in ("V01_TRAIN", "R46_TRAIN", "R54_TRAIN")))
    actual_val = set().union(*(keysets.get(name, {}).get("target", set())
                               for name in ("V01_VALIDATION", "R46_VALIDATION", "R54_VALIDATION")))
    known = None
    if all(name in keysets for name in ("R46_TRAIN", "R46_VALIDATION", "R54_TRAIN")):
        r54 = keysets["R54_TRAIN"]["target"]
        r46t = keysets["R46_TRAIN"]["target"]
        r46v = keysets["R46_VALIDATION"]["target"]
        known = {
            "r54_train_in_r46_train": len(r54 & r46t),
            "r54_train_in_r46_validation": len(r54 & r46v),
            "r54_train_not_in_r46": len(r54 - r46t - r46v),
        }
        if require_all and known != {
            "r54_train_in_r46_train": 14,
            "r54_train_in_r46_validation": 9,
            "r54_train_not_in_r46": 8,
        }:
            raise ExactReplayHold("historical R46/R54 14/9/8 cannot be reproduced")
    for name, records in rows.items():
        if len(keysets[name]["target"]) != len(records):
            raise ExactReplayHold("within-source duplicate final target detected")
    if {"GOLD87", "GOLD108"}.issubset(rows) and len(gold_targets) != 195:
        raise ExactReplayHold("Gold195 unique targets mismatch")
    return {
        "schema": SCHEMA,
        "status": ("EIGHT_SOURCE_EXACT_TARGET_REPLAY_PASS__WORLD_ALIAS_HOLD"
                   if require_all else "PARTIAL_PINNED_EXACT_REPLAY__NOT_G2_FULL_PASS"),
        "sources_compared": list(rows),
        "source_row_counts": {name: len(values) for name, values in rows.items()},
        "source_metadata_coverage": stats,
        "exact_pairwise": pairs,
        "gold_distinct_target_count": len(gold_targets),
        "gold_exact_target_seen_in_previous_train": len(gold_targets & actual_train),
        "gold_exact_target_seen_in_previous_validation": len(gold_targets & actual_val),
        "historical_r46_r54": known,
        "original_file_byte_pins_checked_by_cli": False,
        "true_world_component_isolation_verified": False,
        "semantic_near_duplicate_reviewed": False,
        "ms_swift_original_input_bytes_replayed": False,
        "reviewer_admission_approved": False,
        "v04_admitted": 0,
        "training_authorized": False,
        "protected_evaluation_accessed": False,
    }


def verify_source_pin(name, payload):
    """Trust roots are frozen Git blob IDs or formal historical Trainer digests."""
    if name in frozen.GIT_BLOBS:
        if frozen._git_blob(payload) != frozen.GIT_BLOBS[name]:
            raise ExactReplayHold("frozen Git blob identity mismatch")
    elif name in frozen.HISTORICAL_TRAINER_SHA256:
        if _hash(payload) != frozen.HISTORICAL_TRAINER_SHA256[name]:
            raise ExactReplayHold("frozen compiled Trainer file SHA256 mismatch")
    else:
        raise ExactReplayHold("unrecognized source")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", required=True, type=Path)
    ap.add_argument("--private-root", type=Path)
    ap.add_argument("--mode", choices=("draft", "full"), default="draft")
    ap.add_argument("--source", choices=SOURCE_IDS, action="append", dest="sources")
    ap.add_argument("--safe-out", type=Path)
    args = ap.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        names = args.sources or list(GIT_SOURCES)
        if len(set(names)) != len(names):
            raise ExactReplayHold("duplicate selected source")
        if args.mode == "full" and set(names) != set(SOURCE_IDS):
            raise ExactReplayHold("full mode requires explicit selection of eight source IDs")
        if any(name in HISTORICAL_SOURCES for name in names):
            if args.private_root is None:
                raise ExactReplayHold("Owner-private historical file root required")
            private = args.private_root.resolve(strict=True)
            if repo == private or private in repo.parents or repo in private.parents:
                raise ExactReplayHold("private source directory must be outside repository")
        else:
            private = None
        data = {}
        for name in names:
            root_tag, relative, _ = frozen.SOURCE_PATHS[name]
            root = repo if root_tag == "REPO" else private
            payload = frozen._read(root, relative, frozen.MAX_SOURCE_BYTES)
            verify_source_pin(name, payload)
            data[name] = payload
        result = replay_payloads(data, require_all=args.mode == "full")
        result["original_file_byte_pins_checked_by_cli"] = True
        text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.safe_out is not None:
            if args.safe_out.exists() or args.safe_out.is_symlink():
                raise ExactReplayHold("receipt already exists")
            if any("r50" in part.lower() for part in args.safe_out.parts):
                raise ExactReplayHold("protected path forbidden")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(args.safe_out, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
        print(text, end="")
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        # Never print input paths or file content through OSError exception strings.
        msg = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_G2_EXACT_REPLAY_HOLD: {type(exc).__name__}: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
