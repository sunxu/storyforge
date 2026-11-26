"""R57 G3: pinned Gold195 metadata risk screen; NEVER selects or admits data.

Only four allowlisted Git JSONL files are opened. No R50, network, model,
training or private reviewer records. Output is fixed-schema count-only JSON.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import r57_source_index_export as frozen

SCHEMA = "storyforge-r57-g3-gold195-count-only-prescreen-v1"
SOURCES = ("GOLD87", "GOLD108", "V01_TRAIN", "V01_VALIDATION")
SOURCE_SHA_FIELDS = (
    "source_sha256", "source_archive_sha256", "source_jsonl_sha256", "source_zip_sha256"
)
FLAGS = {
    "independent_review": ("independent_gold_review", "independent_ab_review"),
    "qwen_length": ("qwen_token_length_check", "qwen_16384_token_check"),
    "final_mask": ("last_round_label_mask_check", "last_round_loss_mask_audit"),
    "target_time_card": ("story_card_status", "story_card_as_of_target"),
}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class PrescreenHold(ValueError):
    """Frozen input integrity or metadata schema was not verified."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _nonempty_string(value):
    return isinstance(value, str) and bool(value)


def _signal(metadata, keys):
    found = [metadata[k] for k in keys if k in metadata]
    if not found:
        return "absent"
    if len(found) != 1 or not isinstance(found[0], str):
        return "other_unverified"
    v = found[0]
    if v.startswith("NOT_RUN") or "UNVERIFIED" in v or "NOT_AVAILABLE" in v:
        return "explicit_pending"
    return "other_unverified"


def _rows(data, group):
    expected = frozen.SOURCE_PATHS[group][2]
    lines = data.splitlines()
    if len(lines) != expected or any(not line.strip() for line in lines):
        raise PrescreenHold("frozen sample count mismatch")
    result = []
    forms = {"sha256": 0, "utf8": 0, "legacy": 0}
    for line in lines:
        if len(line) > 3 * 1024 * 1024:
            raise PrescreenHold("source row exceeds limit")
        try:
            record = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise PrescreenHold("invalid source JSONL") from exc
        if not isinstance(record, dict):
            raise PrescreenHold("expected object row")
        messages = frozen._project_messages(record.get("messages"))
        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            raise PrescreenHold("original metadata missing")
        target = _sha(messages[-1]["content"].encode("utf-8"))
        if group.startswith("GOLD"):
            if metadata.get("training_admission") != "PENDING_NOT_APPROVED":
                raise PrescreenHold("Gold195 historical admission contract changed")
            keys = [key for key in frozen.TARGET_HASH_FIELDS if key in metadata]
            if len(keys) != 1 or metadata[keys[0]] != target:
                raise PrescreenHold("target SHA256 metadata differs from source")
            if group == "GOLD87":
                if keys != ["target_sha256_utf8"] or not _nonempty_string(
                    metadata.get("story_id")
                ):
                    raise PrescreenHold("Gold87 metadata contract drifted")
                world = metadata["story_id"]
            else:
                primary = metadata.get("story_id")
                alternate = metadata.get("source_story_id")
                if bool(primary) == bool(alternate):
                    raise PrescreenHold("ambiguous Gold108 source-world identity")
                if primary and keys == ["target_sha256"]:
                    forms["sha256"] += 1
                    world = primary
                elif primary and keys == ["target_sha256_utf8"]:
                    forms["utf8"] += 1
                    world = primary
                elif alternate and keys == ["target_content_sha256"]:
                    forms["legacy"] += 1
                    world = alternate
                else:
                    raise PrescreenHold("Gold108 SHA/world field pairing mismatch")
            if not _nonempty_string(world):
                raise PrescreenHold("Gold195 source-world identity missing")
        else:
            world = metadata.get("story_id")
            if not _nonempty_string(world):
                raise PrescreenHold("v0.1 source-world identity missing")
        result.append({
            "target": target,
            "world": world,
            "metadata": metadata,
            "full_input": frozen._projection_sha(messages),
            "history": frozen._projection_sha(messages[:-1]),
        })
    if group == "GOLD108" and forms != {"sha256": 90, "utf8": 15, "legacy": 3}:
        raise PrescreenHold("Gold108 frozen 90/15/3 distribution mismatch")
    if len({r["target"] for r in result}) != expected:
        raise PrescreenHold("source duplicate exact target")
    return result


def prescreen(payloads):
    """In-memory frozen input replay. Never return raw hashes or story identifiers."""
    if set(payloads) != set(SOURCES):
        raise PrescreenHold("four frozen sources required")
    sources = {name: _rows(payloads[name], name) for name in SOURCES}
    gold_rows = sources["GOLD87"] + sources["GOLD108"]
    old_targets = {
        "train": {r["target"] for r in sources["V01_TRAIN"]},
        "validation": {r["target"] for r in sources["V01_VALIDATION"]},
    }
    old_worlds = {
        "train": {r["world"] for r in sources["V01_TRAIN"]},
        "validation": {r["world"] for r in sources["V01_VALIDATION"]},
    }
    if len({r["target"] for r in gold_rows}) != 195:
        raise PrescreenHold("Gold195 unique-target proof failed")
    if old_targets["train"] & old_targets["validation"]:
        raise PrescreenHold("baseline v0.1 train/validation share exact targets")
    signal_counts = {
        name: {"explicit_pending": 0, "absent": 0, "other_unverified": 0}
        for name in FLAGS
    }
    supplied_source_pins = 0
    per_pool = {}
    for pool in ("GOLD87", "GOLD108"):
        group = sources[pool]
        pin_count = sum(
            any(isinstance(row["metadata"].get(key), str) and
                SHA_RE.fullmatch(row["metadata"][key]) for key in SOURCE_SHA_FIELDS)
            for row in group
        )
        supplied_source_pins += pin_count
        per_pool[pool] = {
            "rows": len(group),
            "world_uuid_count": len({r["world"] for r in group}),
            "source_sha_field_present": pin_count,
            "source_sha_field_absent": len(group) - pin_count,
            "same_uuid_as_v01_train_rows": sum(
                r["world"] in old_worlds["train"] for r in group
            ),
            "same_uuid_as_v01_validation_rows": sum(
                r["world"] in old_worlds["validation"] for r in group
            ),
        }
        for row in group:
            for name, keys in FLAGS.items():
                signal_counts[name][_signal(row["metadata"], keys)] += 1
    exact_prior = {
        k: sum(row["target"] in old_targets[k] for row in gold_rows)
        for k in ("train", "validation")
    }
    if exact_prior != {"train": 0, "validation": 0}:
        raise PrescreenHold("new exact v0.1 target exposure differs from freeze")
    return {
        "schema": SCHEMA,
        "status": "G3_GOLD195_SOURCE_METADATA_PRESCREEN_PASS__ALL_195_HOLD_FOR_ADMISSION",
        "source_rows": {name: len(sources[name]) for name in SOURCES},
        "gold195_distinct_exact_targets": 195,
        "gold195_distinct_world_uuids": len({r["world"] for r in gold_rows}),
        "gold195_source_sha_field_present": supplied_source_pins,
        "gold195_source_sha_field_absent": 195 - supplied_source_pins,
        "gold195_review_signals": signal_counts,
        "per_pool": per_pool,
        "gold_exact_target_seen_in_v01": exact_prior,
        "source_file_byte_pins_checked_by_cli": False,
        "source_sha_field_original_bytes_verified": False,
        "cross_uuid_world_alias_graph_certified": False,
        "r46_r54_actual_trainer_files_verified": False,
        "near_duplicate_semantic_review_done": False,
        "independent_quality_review_admission_done": False,
        "g3_private_review_queue_released": False,
        "v04_admitted_samples": 0,
        "protected_evaluation_content_accessed": False,
        "training_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--safe-out", type=Path)
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve(strict=True)
        values = {}
        for source in SOURCES:
            _, rel, _ = frozen.SOURCE_PATHS[source]
            raw = frozen._read(root, rel, frozen.MAX_SOURCE_BYTES)
            if frozen._git_blob(raw) != frozen.GIT_BLOBS[source]:
                raise PrescreenHold("frozen Git Blob source bytes mismatch")
            values[source] = raw
        result = prescreen(values)
        result["source_file_byte_pins_checked_by_cli"] = True
        output = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.safe_out:
            dest = args.safe_out.absolute()
            if root == dest or root in dest.parents:
                raise PrescreenHold("output path inside Git checkout disallowed")
            if args.safe_out.is_symlink() or args.safe_out.exists():
                raise PrescreenHold("safe output exists, overwrite prohibited")
            flags = os.O_WRONLY | os.O_EXCL | os.O_CREAT
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(args.safe_out, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as sink:
                sink.write(output)
        print(output, end="")
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        detail = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_G3_PRESCREEN_HOLD: {type(exc).__name__}: {detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
