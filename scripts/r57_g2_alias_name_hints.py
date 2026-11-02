"""Owner-local human-readable title/source hints for 55 unresolved R57 alias pairs.

Read exactly eight frozen Git/Trainer sources; emit only a PRIVATE 0600 evidence
index plus safe count-only stdout. Titles and source members are *unverified
hints*, not automatic alias or story-identity decisions. No story content,
R50, model, network, or training.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import r57_g2_alias_pair_review as review
import r57_g2_owner_world_review_roster as roster
import r57_g2_target_anchored_world_audit as anchored
import r57_source_index_export as frozen
import r57_trainer_exact_replay as exact

SCHEMA = "storyforge-r57-g2-private-29-world-title-hints-and-55-pairs-v1"
SAFE_SCHEMA = "storyforge-r57-g2-title-hints-count-only-v1"
PRIVATE_NAME = re.compile(r"^R57_G2_WORLD_NAME_HINTS_[0-9]{8}_[0-9]{6}_PRIVATE\.json$")
HINT_FIELDS = ("story_title", "source_file", "source_jsonl_member")
DIRECT = ("GOLD87", "GOLD108", "V01_TRAIN", "V01_VALIDATION")


class NameHintsHold(ValueError):
    """Incomplete, modified, or unsupported evidence fields."""


def build_index(payloads):
    """Private name hints + safe coverage counts; caller authenticates bytes."""
    private_roster, _ = roster.build_roster(payloads)
    blank_review = review.expected_questions(payloads)
    indexed = {
        r["source_story_uuid_PRIVATE"]: {
            "world_uuid_PRIVATE": r["source_story_uuid_PRIVATE"],
            "historical_sft_exact_uuid": r["same_exact_uuid_seen_in_previous_sft"],
            "candidate_unseen_exact_uuid_gold_rows":
                r["gold_final_targets_without_previous_exact_match"]
                if not r["same_exact_uuid_seen_in_previous_sft"] else 0,
            "suggested_story_titles_PRIVATE": [],
            "source_file_references_PRIVATE": [],
            "source_jsonl_member_references_PRIVATE": [],
            "owner_canonical_title_PRIVATE": None,
            "owner_world_alias_decision": "UNREVIEWED",
            "owner_title_evidence_ref_PRIVATE": "",
        }
        for r in private_roster["worlds"]
    }
    if len(indexed) != 29:
        raise NameHintsHold("unexpected count of frozen source worlds")
    observed = {u: {field: set() for field in HINT_FIELDS} for u in indexed}
    for source in DIRECT:
        for line in payloads[source].splitlines():
            try:
                row = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise NameHintsHold("invalid frozen source JSONL") from exc
            uuid = anchored._source_world(row, source)
            if uuid not in observed:
                raise NameHintsHold("unexpected source UUID outside frozen 29")
            metadata = row["metadata"]
            for field in HINT_FIELDS:
                value = metadata.get(field)
                if value is None:
                    continue
                if not isinstance(value, str):
                    raise NameHintsHold("source display hint has unexpected data type")
                if not value.strip():
                    continue
                if len(value) > 512 or any(ord(c) < 32 for c in value):
                    raise NameHintsHold("source display hint oversized or contains controls")
                observed[uuid][field].add(value)
    for uuid, hints in observed.items():
        entry = indexed[uuid]
        entry["suggested_story_titles_PRIVATE"] = sorted(hints["story_title"])
        entry["source_file_references_PRIVATE"] = sorted(hints["source_file"])
        entry["source_jsonl_member_references_PRIVATE"] = sorted(hints["source_jsonl_member"])
    pairs = []
    for position, row in enumerate(blank_review["questions_PRIVATE"], 1):
        a = row["candidate_world_uuid_PRIVATE"]
        b = row["compare_world_uuid_PRIVATE"]
        if a not in indexed or b not in indexed:
            raise NameHintsHold("pair UUID not present in source-name index")
        def display_hints(uuid):
            item = indexed[uuid]
            return {
                "world_uuid_PRIVATE": uuid,
                "story_title_hints_PRIVATE": item["suggested_story_titles_PRIVATE"],
                "source_file_hints_PRIVATE": item["source_file_references_PRIVATE"],
                "source_jsonl_member_hints_PRIVATE":
                    item["source_jsonl_member_references_PRIVATE"],
            }
        pairs.append({
            "pair_ordinal_1_based": position,
            "comparison_kind": row["comparison_kind"],
            "candidate_world_PRIVATE": display_hints(a),
            "comparison_world_PRIVATE": display_hints(b),
            "automatic_link_inference": False,
            "manual_alias_verdict": "UNREVIEWED",
        })
    if len(pairs) != 55:
        raise NameHintsHold("55 alias pairs not fully represented")
    private = {
        "schema": SCHEMA,
        "evidence_title_hints_are_not_authoritative_story_titles": True,
        "aliases_or_world_links_inferred": False,
        "v04_admitted": 0,
        "worlds_PRIVATE": [indexed[k] for k in sorted(indexed)],
        "pair_name_hints_PRIVATE": pairs,
    }
    eligible = [
        x for x in indexed.values()
        if not x["historical_sft_exact_uuid"] and x["candidate_unseen_exact_uuid_gold_rows"]
    ]
    if sorted(x["candidate_unseen_exact_uuid_gold_rows"] for x in eligible) != [14, 18]:
        raise NameHintsHold("two candidate world count changed")
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "R57_G2_29_WORLD_NAME_HINTS_AND_55_PAIR_LOOKUP_PREPARED__NO_ALIAS_VERDICT",
        "observed_world_uuids": len(indexed),
        "historical_sft_world_uuids": sum(x["historical_sft_exact_uuid"]
                                         for x in indexed.values()),
        "candidate_gold_world_uuids": len(eligible),
        "candidate_gold_row_counts_sorted": [14, 18],
        "worlds_with_explicit_story_title_hint": sum(
            bool(x["suggested_story_titles_PRIVATE"]) for x in indexed.values()
        ),
        "worlds_with_source_file_hint": sum(
            bool(x["source_file_references_PRIVATE"]) for x in indexed.values()
        ),
        "worlds_with_source_jsonl_member_hint": sum(
            bool(x["source_jsonl_member_references_PRIVATE"]) for x in indexed.values()
        ),
        "worlds_without_any_display_hint": sum(
            not (x["suggested_story_titles_PRIVATE"] or
                 x["source_file_references_PRIVATE"] or
                 x["source_jsonl_member_references_PRIVATE"])
            for x in indexed.values()
        ),
        "candidate_worlds_with_source_file_hints": sum(
            bool(x["source_file_references_PRIVATE"]) for x in eligible
        ),
        "candidate_worlds_with_explicit_story_titles": sum(
            bool(x["suggested_story_titles_PRIVATE"]) for x in eligible
        ),
        "pair_hints": len(pairs),
        "pairs_decided_automatically": 0,
        "source_pins_reverified_by_cli": False,
        "independent_semantic_alias_review_completed": False,
        "world_isolation_certified": False,
        "dataset_v04_admitted": 0,
        "r50_content_accessed": False,
        "training_authorized": False,
    }
    return private, safe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--create-private-name")
    args = p.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        private_root = args.private_root.resolve(strict=True)
        if repo == private_root or repo in private_root.parents or private_root in repo.parents:
            raise NameHintsHold("private root must be outside Git checkout")
        if args.create_private_name and not PRIVATE_NAME.fullmatch(args.create_private_name):
            raise NameHintsHold("source name hints basename is not approved")
        data = {}
        for source in exact.SOURCE_IDS:
            category, rel, _ = frozen.SOURCE_PATHS[source]
            payload = frozen._read(
                repo if category == "REPO" else private_root, rel, frozen.MAX_SOURCE_BYTES
            )
            exact.verify_source_pin(source, payload)
            data[source] = payload
        index, safe = build_index(data)
        safe["source_pins_reverified_by_cli"] = True
        if args.create_private_name:
            out = frozen._guard_path(private_root, args.create_private_name)
            if out.exists() or out.is_symlink():
                raise NameHintsHold("private evidence file already exists")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(out, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(index, handle, indent=2, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
        print(json.dumps(safe, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        msg = "filesystem IO failed" if isinstance(exc, OSError) else str(exc)
        print(f"R57_G2_NAME_HINTS_HOLD: {type(exc).__name__}: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
