"""R51: reconcile 108 original Gold records with frozen independent review index.

Sidecar crosswalk: preserve original bytes, no admission, no story text printed.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import hashlib
from pathlib import Path
import subprocess
import sys

import v03_r51_gold195_source_inventory as inventory

INDEX_PATH = Path("evaluations/v0.2/gold-quality-108/gold_108_index.csv")
PINNED_INDEX_BLOB = "38e350a9694cc35e4b1e0e8cb4858bd85b5d6ef3"
EXPECTED_BY_STORY = {"06":7,"08":4,"09":25,"10":19,"12":4,"13":17,"14":12,"15":20}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def load_index(repo: Path) -> list[dict]:
    path = repo / INDEX_PATH
    require(path.is_file() and not path.is_symlink(), "R51_INDEX_MISSING_OR_SYMLINK")
    blob = subprocess.run(
        ["git", "hash-object", "--", str(path)], cwd=repo,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    require(blob == PINNED_INDEX_BLOB, "R51_INDEX_BLOB_SHA_MISMATCH")
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    require(len(rows) == 108, "R51_INDEX_ROW_COUNT_MISMATCH")
    return rows


def reconcile(rows: list[dict], index: list[dict]) -> dict:
    require(len(rows) == 108 and len(index) == 108,
            "R51_108_SOURCE_OR_INDEX_ROWS_CHANGED")
    dictionary = {}
    for item in index:
        name = item.get("candidate_id")
        require(isinstance(name,str) and name.strip() and name not in dictionary,
                "R51_INDEX_CANDIDATE_ID_MISSING_OR_DUPLICATED")
        dictionary[name] = item
    counts = Counter()
    by_story = Counter()
    for source in rows:
        require(isinstance(source,dict) and isinstance(source.get("id"),str) and
                isinstance(source.get("metadata"),dict) and
                isinstance(source.get("messages"),list) and
                bool(source["messages"]), "R51_GOLD108_ORIGINAL_SCHEMA_INVALID")
        key = source["id"]
        require(key in dictionary, "R51_ORIGINAL_RECORD_NOT_IN_FROZEN_INDEX")
        row = dictionary.pop(key)
        meta = source["metadata"]
        require(source["messages"][-1].get("role") == "assistant" and
                isinstance(source["messages"][-1].get("content"),str),
                "R51_TARGET_NOT_ASSISTANT")
        target_hash = hashlib.sha256(
            source["messages"][-1]["content"].encode("utf8")
        ).hexdigest()
        require(row.get("target_sha256") == target_hash,
                "R51_REVIEW_INDEX_TARGET_SHA_MISMATCH")
        counts["target_sha_crosschecked_against_index"] += 1
        val = meta.get("target_sha256_utf8") or meta.get("target_sha256")
        if val:
            require(val == target_hash, "R51_ORIGINAL_METADATA_TARGET_SHA_CONFLICT")
        else:
            counts["original_target_hash_missing_recovered_by_index"] += 1
        source_story = row.get("story_id")
        require(isinstance(source_story,str) and bool(source_story.strip()),
                "R51_REVIEW_INDEX_STORY_ID_MISSING")
        if meta.get("story_id"):
            require(meta["story_id"] == source_story, "R51_STORY_ID_INDEX_CONFLICT")
        else:
            counts["original_story_id_missing_recovered_by_index"] += 1
        source_target = row.get("target_message_id")
        require(isinstance(source_target,str) and bool(source_target.strip()) and
                source_target == meta.get("target_message_id"),
                "R51_REVIEW_INDEX_TARGET_ID_CONFLICT")
        raw_number = row.get("story_number")
        require(isinstance(raw_number,str) and raw_number.isdigit() and
                1 <= int(raw_number) <= 15,
                "R51_REVIEW_INDEX_STORY_NUMBER_INVALID")
        number = f"{int(raw_number):02d}"
        by_story[number] += 1
        old_number = meta.get("story_number")
        if isinstance(old_number,int):
            require(old_number == int(raw_number),
                    "R51_STORY_NUMBER_INDEX_CONFLICT")
        elif isinstance(old_number,str) and old_number.strip().isdigit():
            require(int(old_number) == int(raw_number),
                    "R51_STORY_NUMBER_INDEX_CONFLICT")
        else:
            from_file = meta.get("source_file") or meta.get("source_jsonl_member")
            from_file = Path(from_file).name if isinstance(from_file,str) else ""
            if not from_file.startswith(number+"-"):
                counts["original_story_number_missing_recovered_by_index"] += 1
        require(row.get("reviewer1_decision") == "ACCEPT" and
                row.get("reviewer2_decision") == "ACCEPT",
                "R51_NOT_DOUBLE_ACCEPTED_IN_FROZEN_REVIEW_INDEX")
        require(row.get("training_admission") in ("PENDING_NOT_APPROVED","") and
                meta.get("training_admission") in ("PENDING_NOT_APPROVED",None),
                "R51_UNAUTHORIZED_TRAINING_APPROVAL_IN_SOURCE")
        require(row.get("split") in ("",None) and meta.get("split") is None,
                "R51_UNAUTHORIZED_TRAIN_VAL_SPLIT")
        counts["double_accepted_source_index_rows"] += 1
    require(not dictionary, "R51_INDEX_UNMATCHED_CANDIDATES")
    require(dict(by_story) == EXPECTED_BY_STORY,
            "R51_SELECTED_GOLD108_STORY_COUNTS_CHANGED")
    return {
        "schema": "storyforge-r51-gold108-original-index-reconciliation-v1",
        "status": "GOLD108_FROZEN_INDEX_RECONCILED__TRAINING_ADMISSION_HOLD",
        "frozen_original_blob_sha1": inventory.COHORTS["108"]["git_blob_sha1"],
        "frozen_index_blob_sha1": PINNED_INDEX_BLOB,
        "record_count": 108,
        "double_accepted_source_index_rows": counts["double_accepted_source_index_rows"],
        "verified_target_hash_against_original_reply": counts["target_sha_crosschecked_against_index"],
        "metadata_target_hash_gaps_resolved_by_frozen_index":
            counts["original_target_hash_missing_recovered_by_index"],
        "metadata_story_id_gaps_resolved_by_frozen_index":
            counts["original_story_id_missing_recovered_by_index"],
        "metadata_story_number_gaps_resolved_by_frozen_index":
            counts["original_story_number_missing_recovered_by_index"],
        "per_story": dict(sorted(by_story.items())),
        "training_admitted_by_reconciliation": 0,
        "data_split_assigned_by_reconciliation": 0,
        "source_card_at_target_validated": False,
        "rights_age_player_agency_validated": False,
        "full_world_component_alias_graph_validated": False,
        "actual_training_mask_verified": False,
        "original_gold_rows_rewritten": False,
        "no_gpu_or_model_inference": True,
        "no_git_write": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    args = ap.parse_args()
    repo = args.repo.resolve()
    require((repo / ".git").exists(), "R51_GIT_CHECKOUT_REQUIRED")
    rows = inventory.read_exact(repo,"108")
    index = load_index(repo)
    report = reconcile(rows,index)
    import json
    print("R51_GOLD108_FROZEN_REVIEW_INDEX_RECONCILIATION_PASS__ADMISSION_HOLD")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print("NO_DATA_REWRITE__NO_TRAINING_SPLIT__NO_GPU")


if __name__ == "__main__":
    try:
        main()
    except (ValueError,OSError,KeyError,TypeError,subprocess.CalledProcessError) as exc:
        print("R51_GOLD108_RECONCILIATION_HOLD:",
              type(exc).__name__,str(exc) if isinstance(exc,ValueError)
              else "SOURCE_UNAVAILABLE",file=sys.stderr)
        sys.exit(2)
