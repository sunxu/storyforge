"""R57 G2: offline count-only overlap audit of OWNER-PREPARED private SHA indexes.

Read-only on inputs; never opens original story files, protected evaluation,
GitHub, Hugging Face, or GPUs. No actual sample is accepted by this tool.
"""
import argparse
import itertools
import json
import os
import re
import stat
import sys
from pathlib import Path

FORMAT = "storyforge-r57-training-lineage-private-index-v1"
RESULT = "storyforge-r57-training-lineage-count-only-v1"
HEX = re.compile(r"^[0-9a-f]{64}$")
EXPECTED = {
    "GOLD87": 87,
    "GOLD108": 108,
    "V01_TRAIN": 65,
    "V01_VALIDATION": 15,
    "R46_TRAIN": 49,
    "R46_VALIDATION": 15,
    "R54_TRAIN": 31,
    "R54_VALIDATION": 9,
}
FIELDS = {"target_sha256", "input_sha256", "history_sha256", "world_component_token"}


class AuditHold(ValueError):
    """Metadata is inconsistent or cannot support the requested audit."""


def sha(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def expect_fields(obj, fields):
    if not isinstance(obj, dict) or set(obj) != fields:
        raise AuditHold("unexpected or missing metadata keys")


def audit(packet, *, full=False):
    """Return only safe aggregate counts, never IDs, tokens or individual SHA values."""
    expect_fields(packet, {"schema", "no_protected_evaluation_accessed", "training_authorized", "sources"})
    if packet["schema"] != FORMAT:
        raise AuditHold("unsupported source index schema")
    if packet["no_protected_evaluation_accessed"] is not True:
        raise AuditHold("protected evaluation access boundary is not clear")
    if packet["training_authorized"] is not False:
        raise AuditHold("training flag is prohibited")
    sources = packet["sources"]
    if not isinstance(sources, list) or len(sources) > len(EXPECTED):
        raise AuditHold("invalid source index collections")
    grouped = {}
    for source in sources:
        expect_fields(source, {"id", "source_file_sha256", "rows"})
        name = source["id"]
        if not isinstance(name, str) or name not in EXPECTED or name in grouped:
            raise AuditHold("unknown or repeated source collection")
        if not sha(source["source_file_sha256"]):
            raise AuditHold("invalid source file SHA256")
        records = source["rows"]
        if not isinstance(records, list) or len(records) > 10000:
            raise AuditHold("invalid source rows")
        checked = []
        for row in records:
            expect_fields(row, FIELDS)
            if any(not sha(row[key]) for key in ("target_sha256", "input_sha256", "history_sha256")):
                raise AuditHold("invalid row SHA256")
            world = row["world_component_token"]
            if not isinstance(world, str) or not 3 <= len(world) <= 128:
                raise AuditHold("invalid opaque world component token")
            checked.append(row)
        grouped[name] = checked

    if full and (set(grouped) != set(EXPECTED) or
                 any(len(grouped[name]) != required for name, required in EXPECTED.items())):
        raise AuditHold("full-source inventory incomplete or counts differ from frozen receipt")

    def values(source_name, key):
        return {row[key] for row in grouped.get(source_name, [])}

    counts = {name: len(grouped[name]) for name in sorted(grouped)}
    duplicate_target_rows = {
        name: len(grouped[name]) - len(values(name, "target_sha256"))
        for name in sorted(grouped)
    }
    pairwise = []
    for left, right in itertools.combinations(sorted(grouped), 2):
        pairwise.append({
            "left": left,
            "right": right,
            "exact_target_matches": len(values(left, "target_sha256") & values(right, "target_sha256")),
            "exact_input_matches": len(values(left, "input_sha256") & values(right, "input_sha256")),
            "exact_history_matches": len(values(left, "history_sha256") & values(right, "history_sha256")),
            "declared_world_component_overlap": len(
                values(left, "world_component_token") & values(right, "world_component_token")
            ),
        })

    gold = values("GOLD87", "target_sha256") | values("GOLD108", "target_sha256")
    historical_train = (
        values("V01_TRAIN", "target_sha256") |
        values("R46_TRAIN", "target_sha256") |
        values("R54_TRAIN", "target_sha256")
    )
    historical_validation = (
        values("V01_VALIDATION", "target_sha256") |
        values("R46_VALIDATION", "target_sha256") |
        values("R54_VALIDATION", "target_sha256")
    )
    known_overlap = None
    if {"R54_TRAIN", "R46_TRAIN", "R46_VALIDATION"}.issubset(grouped):
        r54 = values("R54_TRAIN", "target_sha256")
        r46t = values("R46_TRAIN", "target_sha256")
        r46v = values("R46_VALIDATION", "target_sha256")
        known_overlap = {
            "r54_train_in_r46_train": len(r54 & r46t),
            "r54_train_in_r46_validation": len(r54 & r46v),
            "r54_train_not_in_r46_splits": len(r54 - r46t - r46v),
            "historical_receipt_14_9_8_agrees": (
                len(r54 & r46t) == 14 and
                len(r54 & r46v) == 9 and
                len(r54 - r46t - r46v) == 8
            ),
        }
        if full and not known_overlap["historical_receipt_14_9_8_agrees"]:
            raise AuditHold("historical R46/R54 overlap does not replay to frozen receipt")

    if full:
        if len(gold) != 195:
            raise AuditHold("Gold195 exact-target uniqueness does not replay")
        if any(duplicate_target_rows.values()):
            raise AuditHold("a historical source contains repeated target SHA values")

    return {
        "schema": RESULT,
        "status": (
            "R57_G2_PRIVATE_INDEX_REPLAY_COUNTS_PASS__NOT_SOURCE_BYTES_OR_WORLD_CERTIFIED"
            if full else "R57_G2_PARTIAL_METADATA_DRAFT__NOT_AUDITED"
        ),
        "collections_seen": len(grouped),
        "source_row_counts": counts,
        "duplicate_exact_target_rows_within_source": duplicate_target_rows,
        "source_pairs": pairwise,
        "distinct_gold_target_hashes_seen": len(gold),
        "gold_exact_targets_seen_in_prior_train": len(gold & historical_train),
        "gold_exact_targets_seen_in_prior_validation": len(gold & historical_validation),
        "historical_r46_r54_receipt_replay": known_overlap,
        "no_protected_evaluation_accessed": True,
        "source_bytes_independently_rehashed": False,
        "alias_graph_semantically_certified": False,
        "near_duplicates_audited": False,
        "training_authorized": False,
        "v04_samples_admitted": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-index", required=True, type=Path)
    parser.add_argument("--mode", choices=("draft", "full"), default="draft")
    parser.add_argument("--safe-out", type=Path)
    args = parser.parse_args()
    try:
        # Never resolve or read protected evaluation paths, even if supplied by mistake.
        if any("r50" in part.lower() for part in args.private_index.parts):
            raise AuditHold("protected data path is not a permitted source index")
        if args.private_index.is_symlink():
            raise AuditHold("source index symlink forbidden")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(args.private_index, flags)
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            st = os.fstat(handle.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_size > 64 * 1024 * 1024:
                raise AuditHold("metadata index must be regular and at most 64 MiB")
            packet = json.load(handle)
        result = audit(packet, full=args.mode == "full")
        output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.safe_out:
            if args.private_index.resolve() == args.safe_out.resolve():
                raise AuditHold("receipt cannot overwrite input")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(args.safe_out, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(output)
        print(output, end="")
        return 0
    except (ValueError, TypeError, OSError) as exc:
        msg = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_G2_SOURCE_AUDIT_HOLD: {type(exc).__name__}: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
