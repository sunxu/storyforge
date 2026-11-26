"""R57 G2: private source pointers for the two UUID-unmatched Gold87 worlds.

No narrative or source files are opened via source_file references: only
metadata from the frozen, byte-pinned Gold87 JSONL is copied to Owner-local
0600 output. CLI prints fixed count-only evidence. No R50/HF/GPU/model.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import r57_g2_owner_world_review_roster as roster
import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact

SCHEMA = "storyforge-r57-g2-owner-private-candidate-origin-locator-v1"
SAFE_SCHEMA = "storyforge-r57-g2-source-locator-safe-counts-v1"
PRIVATE_NAME = re.compile(r"^R57_G2_CANDIDATE_SOURCE_LOCATOR_[0-9]{8}_[0-9]{6}_PRIVATE\.json$")


class LocatorHold(ValueError):
    """Missing, ambiguous or unsafe original-case provenance."""


def prepare_locator(payloads):
    """Return private locator and safe counts. CLI independently verifies pins."""
    private_roster, _ = roster.build_roster(payloads)
    candidates = {
        row["source_story_uuid_PRIVATE"]: row["gold_final_targets_without_previous_exact_match"]
        for row in private_roster["worlds"]
        if not row["same_exact_uuid_seen_in_previous_sft"]
        and row["gold_final_targets_without_previous_exact_match"]
    }
    if len(candidates) != 2 or sorted(candidates.values()) != [14, 18]:
        raise LocatorHold("frozen unseen world distribution changed")
    found = {key: [] for key in candidates}
    for ordinal, line in enumerate(payloads["GOLD87"].splitlines(), 1):
        try:
            source = json.loads(line)
        except (UnicodeError, ValueError) as exc:
            raise LocatorHold("Gold87 source JSONL is not valid") from exc
        if not isinstance(source, dict) or not isinstance(source.get("metadata"), dict):
            raise LocatorHold("Gold87 missing row provenance")
        metadata = source["metadata"]
        uuid = metadata.get("story_id")
        if uuid not in candidates:
            continue
        for key in (
            "source_file", "source_json_pointer", "selection_title_zh",
            "source_sha256",
        ):
            if not isinstance(metadata.get(key), str) or not metadata[key].strip():
                raise LocatorHold("Gold candidate missing source locator field")
        found[uuid].append({
            "gold87_source_row_ordinal_1_based_PRIVATE": ordinal,
            "source_file_reference_PRIVATE": metadata["source_file"],
            "source_json_pointer_PRIVATE": metadata["source_json_pointer"],
            "case_selection_label_zh_PRIVATE": metadata["selection_title_zh"],
            "source_sha256_from_original_gold_metadata_PRIVATE": metadata["source_sha256"],
        })
    if {k: len(v) for k, v in found.items()} != candidates:
        raise LocatorHold("Gold87 candidate row count does not match frozen roster")
    # Preserve audit-only locators. This file does not contain dialogue text.
    records = [
        {
            "source_story_uuid_PRIVATE": uuid,
            "gold87_rows": len(found[uuid]),
            "owner_semantic_alias_review_status": "PENDING_NOT_VERIFIED",
            "owner_evidence_reviewed": False,
            "dataset_v04_decision": "HOLD_NOT_REVIEWED",
            "source_locations_PRIVATE": found[uuid],
        }
        for uuid in sorted(candidates)
    ]
    private = {
        "schema": SCHEMA,
        "source_byte_pins_verified_by_cli": False,
        "source_files_opened_from_original_metadata": False,
        "world_alias_verification_completed": False,
        "training_authorized": False,
        "v04_admitted": 0,
        "candidate_worlds_PRIVATE": records,
    }
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "R57_G2_GOLD32_SOURCE_POINTERS_PREPARED__MANUAL_WORLD_REVIEW_HOLD",
        "candidate_unseen_exact_uuid_worlds": len(records),
        "candidate_gold87_rows": sum(row["gold87_rows"] for row in records),
        "per_world_gold_row_counts_sorted": sorted(row["gold87_rows"] for row in records),
        "source_file_metadata_present_count": sum(len(row["source_locations_PRIVATE"]) for row in records),
        "source_json_pointer_metadata_present_count": sum(len(row["source_locations_PRIVATE"]) for row in records),
        "selection_label_metadata_present_count": sum(len(row["source_locations_PRIVATE"]) for row in records),
        "source_sha_metadata_present_not_independently_rehashed_count": sum(
            len(row["source_locations_PRIVATE"]) for row in records
        ),
        "source_byte_pins_reverified_by_cli": False,
        "original_story_files_opened": False,
        "semantic_alias_review_complete": False,
        "owner_signoff_complete": False,
        "world_isolation_certified": False,
        "v04_admitted": 0,
        "r50_content_accessed": False,
        "training_authorized": False,
    }
    return private, safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--private-locator-name", type=str)
    args = parser.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        root = args.private_root.resolve(strict=True)
        if repo == root or repo in root.parents or root in repo.parents:
            raise LocatorHold("Owner-private root must be outside Git checkout")
        if args.private_locator_name and not PRIVATE_NAME.fullmatch(args.private_locator_name):
            raise LocatorHold("private locator filename format rejected")
        data = {}
        for name in exact.SOURCE_IDS:
            flag, relative, _ = frozen.SOURCE_PATHS[name]
            original = frozen._read(
                repo if flag == "REPO" else root, relative, frozen.MAX_SOURCE_BYTES
            )
            exact.verify_source_pin(name, original)
            data[name] = original
        private, safe = prepare_locator(data)
        safe["source_byte_pins_reverified_by_cli"] = True
        if args.private_locator_name:
            target = frozen._guard_path(root, args.private_locator_name)
            if target.exists() or target.is_symlink():
                raise LocatorHold("private locator already exists")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(target, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                private["source_byte_pins_verified_by_cli"] = True
                json.dump(private, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        err = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_G2_SOURCE_LOCATOR_HOLD: {type(exc).__name__}: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
