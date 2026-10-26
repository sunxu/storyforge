"""R57 G2 Owner-local world/alias evidence roster; NOT an automatic world map.

Read 8 fixed pinned JSONL sources; target-join historical metadata-free Trainer
rows to original Gold target SHA. Produce a private review roster with *unset*
owner alias decisions. SAFE stdout contains only counts. No R50/network/GPU.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact
import r57_g2_target_anchored_world_audit as anchored

SCHEMA = "storyforge-r57-g2-owner-private-world-alias-review-roster-v1"
SAFE_SCHEMA = "storyforge-r57-g2-world-alias-review-roster-count-only-v1"
PRIVATE_NAME = re.compile(
    r"^R57_G2_WORLD_ALIAS_REVIEW_[0-9]{8}_[0-9]{6}_PRIVATE\.json$"
)
TRAIN = ("V01_TRAIN", "R46_TRAIN", "R54_TRAIN")
VAL = ("V01_VALIDATION", "R46_VALIDATION", "R54_VALIDATION")
GROUPS = tuple(exact.SOURCE_IDS)


class WorldRosterHold(ValueError):
    """Source provenance incomplete or roster path unsafe."""


def _rows(payload):
    try:
        return [json.loads(line) for line in payload.splitlines()]
    except (UnicodeError, ValueError) as exc:
        raise WorldRosterHold("invalid frozen source JSONL") from exc


def build_roster(payloads):
    """Return private world roster and safe aggregates; caller must verify pins."""
    # Exhaustive historical overlap, five exact histories and UUID mapping
    # must already be satisfied before emitting even a private draft.
    verified = anchored.audit(payloads)
    original = {name: _rows(payloads[name]) for name in GROUPS}
    hashes = {name: exact._shape(payloads[name], name)[0] for name in GROUPS}
    origin = {}
    for name in ("GOLD87", "GOLD108"):
        for item, projected in zip(original[name], hashes[name], strict=True):
            key = projected["target"]
            if key in origin:
                raise WorldRosterHold("ambiguous Gold target-to-world mapping")
            origin[key] = anchored._source_world(item, name)
    if len(origin) != 195:
        raise WorldRosterHold("Gold target-to-world lookup incomplete")
    world_source_rows = {}
    gold_not_exact = {}
    previous_targets = set().union(*(
        {row["target"] for row in hashes[name]} for name in (*TRAIN, *VAL)
    ))
    for name in GROUPS:
        for item, target in zip(original[name], hashes[name], strict=True):
            if name.startswith("R46_") or name.startswith("R54_"):
                uuid = origin.get(target["target"])
                if uuid is None:
                    raise WorldRosterHold("compiled Trainer target lacks unique Gold source")
            else:
                uuid = anchored._source_world(item, name)
            counts = world_source_rows.setdefault(uuid, dict.fromkeys(GROUPS, 0))
            counts[name] += 1
            if name in ("GOLD87", "GOLD108") and target["target"] not in previous_targets:
                gold_not_exact[uuid] = gold_not_exact.get(uuid, 0) + 1
    historical_uuids = {
        uuid for uuid, counts in world_source_rows.items()
        if any(counts[name] for name in (*TRAIN, *VAL))
    }
    records = []
    for uuid in sorted(world_source_rows):
        counts = world_source_rows[uuid]
        records.append({
            "source_story_uuid_PRIVATE": uuid,
            "source_row_counts": counts,
            "gold_final_targets_without_previous_exact_match": gold_not_exact.get(uuid, 0),
            "same_exact_uuid_seen_in_previous_sft": uuid in historical_uuids,
            "owner_declared_component_token_PRIVATE": None,
            "owner_alias_evidence_references_PRIVATE": [],
            "owner_alias_semantic_review_status": "PENDING_NOT_VERIFIED",
            "owner_signoff_status": "NOT_SIGNED",
            "dataset_v04_decision": "HOLD_NOT_REVIEWED",
        })
    unmatched = [
        record for record in records if not record["same_exact_uuid_seen_in_previous_sft"]
        and record["gold_final_targets_without_previous_exact_match"]
    ]
    count = sum(r["gold_final_targets_without_previous_exact_match"] for r in unmatched)
    if count != 32:
        raise WorldRosterHold("unexposed exact-world Gold32 count differs from Owner report")
    if len(records) != 29:
        raise WorldRosterHold("distinct eight-source story UUID roster size differs")
    if len(unmatched) != 2:
        raise WorldRosterHold("number of not-previously-used Gold story UUIDs differs")
    private = {
        "schema": SCHEMA,
        "purpose": "OWNER_MANUAL_SEMANTIC_ALIAS_AND_WORLD_COMPONENT_EVIDENCE_REVIEW_ONLY",
        "sources_frozen_byte_identity_checked_by_cli": False,
        "independent_semantic_world_link_certified": False,
        "training_authorized": False,
        "v04_admitted_rows": 0,
        "worlds": records,
    }
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "R57_G2_WORLD_UUID_ROSTER_PREPARED__OWNER_ALIAS_REVIEW_REQUIRED__NO_ADMISSION",
        "world_uuid_count": len(records),
        "gold_world_uuids": len({
            uuid for uuid, cnt in world_source_rows.items()
            if cnt["GOLD87"] or cnt["GOLD108"]
        }),
        "historical_sft_world_uuid_count": len(historical_uuids),
        "gold_world_uuids_without_historical_sft_uuid": len(unmatched),
        "gold_rows_without_target_and_world_uuid_exact_match": count,
        "gold_rows_without_target_exact_match": 114,
        "compiled_rows_uniquely_matched_to_gold": sum(
            verified["compiled_trainer_rows_uniquely_mapped_to_gold195"].values()
        ),
        "source_frozen_byte_pins_verified_by_cli": False,
        "owner_semantic_alias_evidence_review_completed": False,
        "owner_alias_signoff_completed": False,
        "world_component_isolation_certified": False,
        "independent_quality_rights_age_consent_admission_complete": False,
        "v04_admitted": 0,
        "r50_content_accessed": False,
        "training_authorized": False,
    }
    return private, safe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", required=True, type=Path)
    p.add_argument("--private-root", required=True, type=Path)
    p.add_argument("--private-roster-name")
    args = p.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        priv = args.private_root.resolve(strict=True)
        if repo == priv or priv in repo.parents or repo in priv.parents:
            raise WorldRosterHold("private evidence and Git checkout cannot overlap")
        if args.private_roster_name is not None and not PRIVATE_NAME.fullmatch(
            args.private_roster_name
        ):
            raise WorldRosterHold("private roster filename must be fixed-format basename")
        payloads = {}
        for name in GROUPS:
            tag, rel, _ = frozen.SOURCE_PATHS[name]
            raw = frozen._read(repo if tag == "REPO" else priv, rel, frozen.MAX_SOURCE_BYTES)
            exact.verify_source_pin(name, raw)
            payloads[name] = raw
        private, safe = build_roster(payloads)
        safe["source_frozen_byte_pins_verified_by_cli"] = True
        if args.private_roster_name is not None:
            target = frozen._guard_path(priv, args.private_roster_name)
            if target.exists() or target.is_symlink():
                raise WorldRosterHold("private roster already exists")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(target, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as sink:
                private["sources_frozen_byte_identity_checked_by_cli"] = True
                json.dump(private, sink, ensure_ascii=False, sort_keys=True, indent=2)
                sink.write("\n")
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        message = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print("R57_G2_WORLD_ROSTER_HOLD: " + type(exc).__name__ + ": " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
