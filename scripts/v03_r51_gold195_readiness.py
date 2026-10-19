#!/usr/bin/env python3
"""R51 read-only Gold195 quality-pool integrity and training-blocker inventory.

Does NOT admit training examples, assign a split, synthesize a card, open
private heldout test prompts, call AI/HF/GPU, or change any source files.
Output is counts, statuses and source-blob digests only, never story text,
candidate IDs, full message bodies, private review notes or prompts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

GOLD87 = Path("evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl")
GOLD108 = Path("evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl")
INDEX108 = Path("evaluations/v0.2/gold-quality-108/gold_108_index.csv")
EXPECTED_GIT_SHA1_87 = "a2038e18bee8ddef96b93bb6746270a462f9a6e4"
EXPECTED_SHA256_108 = "27d15b6f8baf7935ee2c48f85558adc3b5b25e3558e127485d0f17b620f80308"
COUNT_BY_STORY = {
    1: 21, 2: 24, 3: 14, 4: 10, 5: 18, 6: 7,
    8: 4, 9: 25, 10: 19, 12: 4, 13: 17, 14: 12, 15: 20,
}
EXPECTED_COHORTS = {87: 87, 108: 108}


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError(code)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def read_pinned_rows(repo: Path, relpath: Path, expected_count: int,
                     *, blob_sha1: str | None = None,
                     sha256_digest: str | None = None) -> list[dict]:
    path = repo / relpath
    require(path.is_file() and not path.is_symlink(),
            "GOLD_COHORT_SOURCE_FILE_MISSING_OR_SYMLINK")
    raw = path.read_bytes()
    if blob_sha1 is not None:
        require(git_blob_sha1(raw) == blob_sha1, "GOLD87_GIT_BLOB_SHA_MISMATCH")
    if sha256_digest is not None:
        require(sha256(raw) == sha256_digest, "GOLD108_SHA256_MISMATCH")
    lines = raw.splitlines()
    require(len(lines) == expected_count, "GOLD_COHORT_ROW_COUNT_MISMATCH")
    parsed = [json.loads(line) for line in lines]
    require(all(isinstance(x, dict) for x in parsed),
            "GOLD_COHORT_RECORD_NOT_OBJECT")
    return parsed


def read_gold108_index(repo: Path) -> list[dict]:
    path = repo / INDEX108
    require(path.is_file() and not path.is_symlink(),
            "GOLD108_REVIEW_INDEX_MISSING_OR_SYMLINK")
    with path.open(encoding="utf8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == 108, "GOLD108_REVIEW_INDEX_COUNT_MISMATCH")
    require(len({x["candidate_id"] for x in rows}) == 108,
            "GOLD108_INDEX_DUPLICATE_SOURCE_ID")
    for row in rows:
        require(row["reviewer1_decision"] == row["reviewer2_decision"] == "ACCEPT",
                "GOLD108_DOUBLE_ACCEPT_NOT_PROVEN")
        require(row["training_admission"] == "PENDING_NOT_APPROVED",
                "GOLD108_INDEX_TRAINING_ADMISSION_CHANGED")
        require(row["split"] in ("", "None", "null"),
                "GOLD108_INDEX_SPLIT_ALREADY_ASSIGNED")
        for field in ("reviewer1_scores", "reviewer2_scores"):
            scores = [int(value) for value in row[field].split(",")]
            require(len(scores) == 5 and all(4 <= score <= 5 for score in scores),
                    "GOLD108_REVIEW_SCORE_BELOW_THRESHOLD")
    return rows


def inspect_rows(cohort87: list[dict], cohort108: list[dict],
                 index108: list[dict]) -> dict:
    require(len(cohort87) == 87 and len(cohort108) == 108 and
            len(index108) == 108, "GOLD195_INPUT_COUNT_WRONG")
    by_story: Counter[int] = Counter()
    components: dict[int, set[str]] = defaultdict(set)
    by_cohort = {87: 0, 108: 0}
    ages_unspecified = 0
    historical_card_unverified = 0
    explicit_source_index_missing = 0
    target_text_modifications = 0
    history_text_modifications = 0
    active_supervision_labels = 0
    history_message_entries = 0
    messages_with_system_first = 0
    lengths: list[int] = []
    ids: set[str] = set()
    target_keys: set[tuple[str, str]] = set()
    source_rank_missing = 0

    for cohort, records in ((87, cohort87), (108, cohort108)):
        for position, row in enumerate(records):
            meta = row.get("metadata")
            messages = row.get("messages")
            require(isinstance(meta, dict) and isinstance(messages, list) and
                    len(messages) >= 2 and
                    all(isinstance(item, dict) and isinstance(item.get("role"), str)
                        and isinstance(item.get("content"), str) for item in messages),
                    "GOLD195_MESSAGES_OR_METADATA_INVALID")
            require(type(row.get("id")) is str and row["id"] not in ids,
                    "GOLD195_DUPLICATE_OR_INVALID_ID")
            ids.add(row["id"])
            require(meta.get("training_admission") == "PENDING_NOT_APPROVED" and
                    meta.get("split") is None,
                    "GOLD195_PREMATURE_TRAINING_ADMISSION_OR_SPLIT")
            require(messages[-1]["role"] == "assistant" and
                    any(msg["role"] == "user" for msg in messages[:-1]),
                    "GOLD195_ASSISTANT_TARGET_OR_PLAYER_INPUT_INVALID")
            require(not any(msg.get("loss") is True for msg in messages[:-1]),
                    "GOLD195_HISTORY_SUPERVISION_ALREADY_ENABLED")
            # Cohort108 preserves multiple original source schemas:
            # target_sha256 (90), target_sha256_utf8 (15), and
            # target_content_sha256 (3). Never silently normalize source.
            hash_fields = (
                ("target_sha256_utf8",) if cohort == 87 else
                ("target_sha256", "target_sha256_utf8", "target_content_sha256")
            )
            digests = [meta[key] for key in hash_fields
                       if isinstance(meta.get(key), str)]
            require(bool(digests) and len(set(digests)) == 1,
                    "GOLD195_TARGET_DIGEST_MISSING_OR_CONFLICTING")
            expected_target = digests[0]
            require(type(expected_target) is str and
                    sha256(messages[-1]["content"].encode("utf8")) == expected_target,
                    "GOLD195_TARGET_SHA256_MISMATCH")
            story_id = meta.get("story_id")
            target_id = meta.get("target_message_id")
            require(type(story_id) is str and story_id and
                    type(target_id) is str and target_id,
                    "GOLD195_SOURCE_TARGET_ID_MISSING")
            target = (story_id, target_id)
            require(target not in target_keys, "GOLD195_DUPLICATE_SOURCE_TARGET")
            target_keys.add(target)
            if cohort == 87:
                match = re.match(r"^(\d\d)-", str(meta.get("source_file", "")))
                require(match is not None, "GOLD87_SOURCE_RANK_MISSING")
                rank = int(match.group(1))
                require(1 <= rank <= 5, "GOLD87_SOURCE_RANK_INVALID")
                historical_card_unverified += int(
                    "UNVERIFIED" in str(meta.get("story_card_status", "")))
                explicit_source_index_missing += int(
                    meta.get("source_json_pointer") is None)
                ages_unspecified += int(meta.get("source_character_age") ==
                                        "UNSPECIFIED")
                target_text_modifications += int(
                    meta.get("target_text_modified") is True)
                history_text_modifications += int(
                    meta.get("history_text_modified") is True)
            else:
                idx = index108[position]
                require(row["id"] == idx["candidate_id"],
                        "GOLD108_RECORD_REVIEW_INDEX_ORDER_INVALID")
                require(expected_target == idx["target_sha256"],
                        "GOLD108_TARGET_AND_INDEX_DIGEST_MISMATCH")
                rank = int(idx["story_number"])
                require(6 <= rank <= 15, "GOLD108_SOURCE_RANK_INVALID")
                if meta.get("story_number") is not None:
                    require(int(meta["story_number"]) == rank,
                            "GOLD108_METADATA_STORY_RANK_CONFLICT")
                historical_card_unverified += int(
                    meta.get("story_card_as_of_target") ==
                    "NOT_AVAILABLE_NOT_INJECTED" or
                    "UNVERIFIED" in str(meta.get("story_card_status", "")) or
                    "UNVERIFIED" in str(meta.get("target_time_story_card", "")))
                explicit_source_index_missing += int(
                    meta.get("source_message_array_index") is None and
                    meta.get("source_json_pointer") is None)
                target_text_modifications += int(
                    meta.get("raw_assistant_text_edited") is True or
                    meta.get("target_text_modified") is True or
                    meta.get("target_modified") is True)
                history_text_modifications += int(
                    meta.get("raw_history_text_edited") is True or
                    meta.get("history_text_modified") is True)
            by_story[rank] += 1
            components[rank].add(story_id)
            by_cohort[cohort] += 1
            history_message_entries += len(messages) - 1
            lengths.append(len(messages) - 1)
            messages_with_system_first += int(messages[0]["role"] == "system")
            active_supervision_labels += sum(m.get("loss") is True
                                             for m in messages)

    require(dict(by_story) == COUNT_BY_STORY,
            "GOLD195_STORY_DISTRIBUTION_CHANGED")
    require(by_cohort == EXPECTED_COHORTS,
            "GOLD195_COHORT_COMPOSITION_CHANGED")
    require(len(ids) == 195 and len(target_keys) == 195,
            "GOLD195_GLOBAL_TARGET_UNIQUENESS_FAILED")
    require(target_text_modifications == history_text_modifications == 0,
            "GOLD195_CANONICAL_TEXT_WAS_EDITED")

    return {
        "schema": "storyforge-r51-gold195-git-candidate-integrity-v1",
        "source": "GIT_PINNED_GOLD_87_AND_GOLD_108_WITH_REVIEW_INDEX",
        "cohorts": {"gold87": 87, "gold108": 108},
        "candidate_count": 195,
        "source_story_ranks_with_selected_gold": len(by_story),
        "source_story_rank_counts": {f"{rank:02d}": by_story[rank]
                                     for rank in sorted(by_story)},
        "unique_source_story_ids": sum(len(x) for x in components.values()),
        "source_ranks_with_multiple_story_ids":
            [rank for rank in sorted(components) if len(components[rank]) > 1],
        "unique_candidate_ids": len(ids),
        "unique_original_target_story_message_pairs": len(target_keys),
        "original_assistant_final_targets": len(ids),
        "original_target_hashes_verified": len(ids),
        "original_target_texts_edited": target_text_modifications,
        "original_histories_edited": history_text_modifications,
        "original_history_message_entries": history_message_entries,
        "min_history_message_count": min(lengths),
        "max_history_message_count": max(lengths),
        "existing_explicit_loss_true_message_count": active_supervision_labels,
        "original_messages_beginning_with_system": messages_with_system_first,
        "source_rank_missing": source_rank_missing,
        "source_index_fields_absent_in_source_metadata":
            explicit_source_index_missing,
        "explicit_export_or_target_card_unverified_flags":
            historical_card_unverified,
        "source_character_age_unspecified_flags": ages_unspecified,
        "quality_selection_gate": "OWNER_SELECTED_GOLD195_ONLY",
        "source_replay_and_timepoint_card_semantics": "NOT_PERFORMED_BY_THIS_GATE",
        "content_age_rights_and_player_agency_per_row":
            "REQUIRES_INDEPENDENT_PRIVATE_REVIEW",
        "train_val_heldout_world_component_isolation":
            "NOT_PERFORMED_BY_THIS_GATE",
        "fresh_train_validation_split": "NOT_CREATED",
        "tokenizer_actual_collator_and_label_mask": "NOT_EXECUTED",
        "r45_18_held_rows": "UNCHANGED_NOT_REOPENED",
        "r50_frozen_46_heldout_prompts": "NOT_READ",
        "r51_admitted_train_records": 0,
        "r51_admitted_validation_records": 0,
        "r51_status": "GOLD195_ORIGINAL_INTEGRITY_PASS__TRAINING_ADMISSION_HOLD",
        "gpu_run": False,
        "model_generation": False,
        "git_write": False,
    }


def run(repo: Path) -> dict:
    require((repo / ".git").exists(), "LOCAL_GIT_REPO_REQUIRED")
    a = read_pinned_rows(repo, GOLD87, 87, blob_sha1=EXPECTED_GIT_SHA1_87)
    b = read_pinned_rows(repo, GOLD108, 108, sha256_digest=EXPECTED_SHA256_108)
    i = read_gold108_index(repo)
    return inspect_rows(a, b, i)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args.repo.resolve())
    except (OSError, ValueError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as exc:
        print("R51_GOLD195_SOURCE_INTEGRITY_HOLD:",
              type(exc).__name__, str(exc)[:100], file=sys.stderr)
        sys.exit(2)
    print("R51_GOLD195_SOURCE_INTEGRITY_PASS__TRAINING_ADMISSION_HOLD")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("NO_GIT_WRITE__NO_GPU__NO_MODEL_INFERENCE__NO_SPLIT")


if __name__ == "__main__":
    main()
