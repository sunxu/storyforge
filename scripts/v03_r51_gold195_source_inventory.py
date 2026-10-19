"""R51: read-only structural inventory of the original Gold195 candidates.

Training admission is NEVER authorized by a successful inventory.
No AI/GPU, raw narrative logs, split, rewriting, or Git mutations.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

COHORTS = {
    "87": {
        "path": "evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl",
        "git_blob_sha1": "a2038e18bee8ddef96b93bb6746270a462f9a6e4",
        "expected_rows": 87,
    },
    "108": {
        "path": "evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl",
        "git_blob_sha1": "eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90",
        "expected_rows": 108,
    },
}
SCHEMA = "storyforge-r51-original-gold195-structural-preflight-v1"


def guard(test: bool, code: str) -> None:
    if not test:
        raise ValueError(code)


def read_exact(repo: Path, cohort: str) -> list[dict]:
    spec = COHORTS[cohort]
    file = repo / spec["path"]
    guard(file.is_file() and not file.is_symlink(), "MISSING_OR_SYMLINKED_FROZEN_GOLD")
    actual = subprocess.run(
        ["git", "hash-object", "--", str(file)],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.strip()
    guard(actual == spec["git_blob_sha1"], "GOLD_SOURCE_GIT_BLOB_HASH_MISMATCH")
    blob = file.read_bytes()
    guard(blob.endswith(b"\n"), "GOLD_JSONL_MISSING_TERMINATING_NEWLINE")
    raw = blob.splitlines()
    guard(len(raw) == spec["expected_rows"], "GOLD_FROZEN_COHORT_ROW_COUNT_MISMATCH")
    rows = []
    for b in raw:
        guard(bool(b.strip()), "GOLD_BLANK_RECORD")
        rows.append(json.loads(b.decode("utf8")))
    return rows


def _state(value: object) -> str:
    if value is None:
        return "MISSING"
    if value == "NOT_RUN":
        return "NOT_RUN"
    if value == "PENDING_NOT_APPROVED":
        return "PENDING_NOT_APPROVED"
    if value in ("UNVERIFIED", "UNKNOWN", "PENDING"):
        return "UNVERIFIED"
    if value in ("PASS", "VERIFIED"):
        return "REPORTED_PASS_NOT_INDEPENDENTLY_CONFIRMED"
    return "OTHER_OR_NOT_SCOPED"


def inspect(cohorts: dict[str, list[dict]]) -> dict:
    guard(set(cohorts) == {"87", "108"}, "GOLD_COHORT_SCOPE_CHANGED")
    seen_ids = set()
    seen_target_source = set()
    target_hashes: Counter[str] = Counter()
    per_cohort = {}
    unique_story_ids: set[str] = set()
    global_summary = Counter()
    by_story: Counter[str] = Counter()
    for cohort in ("87", "108"):
        data = cohorts[cohort]
        guard(len(data) == COHORTS[cohort]["expected_rows"],
              "GOLD_COHORT_ROW_COUNT_MISMATCH")
        counts = Counter()
        for entry in data:
            guard(isinstance(entry, dict) and
                  isinstance(entry.get("id"), str) and entry["id"].strip(),
                  "GOLD_RECORD_ID_MISSING")
            rid = entry["id"]
            guard(rid not in seen_ids, "GOLD_ID_COLLISION_ACROSS_COHORTS")
            seen_ids.add(rid)
            messages = entry.get("messages")
            m = entry.get("metadata")
            guard(isinstance(messages, list) and len(messages) >= 2 and
                  isinstance(m, dict), "GOLD_MESSAGES_OR_METADATA_MALFORMED")
            for row in messages:
                guard(isinstance(row, dict) and
                      row.get("role") in ("system", "user", "assistant") and
                      isinstance(row.get("content"), str),
                      "GOLD_MALFORMED_ROLE_OR_MESSAGE")
            target = messages[-1]
            guard(target["role"] == "assistant" and
                  bool(target["content"].strip()),
                  "GOLD_FINAL_SUPERVISION_TARGET_NOT_ASSISTANT")
            story_id = m.get("story_id")
            if isinstance(story_id, str) and story_id.strip():
                unique_story_ids.add(story_id)
                source_identity = story_id
                counts["source_story_id_present"] += 1
            else:
                # Some frozen records omit it. This is an evidence gap,
                # NOT an excuse to invent a verified source UUID.
                counts["source_story_id_missing"] += 1
                source_identity = None
            source_number = m.get("story_number")
            source_file = m.get("source_file") or m.get("source_jsonl_member")
            found = re.match(r"^(\d{2})-", Path(source_file).name) if isinstance(source_file,str) else None
            if type(source_number) is int and 1 <= source_number <= 15:
                by_story[f"{source_number:02d}"] += 1
                source_number_label = f"{source_number:02d}"
            elif found:
                by_story[found.group(1)] += 1
                source_number_label = found.group(1)
            else:
                counts["source_story_number_unmapped"] += 1
                source_number_label = None
            target_sha = hashlib.sha256(target["content"].encode("utf8")).hexdigest()
            expected_sha = m.get("target_sha256_utf8", m.get("target_sha256"))
            if expected_sha is not None:
                guard(isinstance(expected_sha, str) and
                      expected_sha == target_sha,
                      "GOLD_TARGET_SHA256_MISMATCH")
                counts["target_source_hash_verified"] += 1
            else:
                counts["target_source_hash_missing"] += 1
            target_hashes[target_sha] += 1
            source_target_id = m.get("target_message_id")
            if isinstance(source_target_id, str) and source_target_id:
                scope_identity = source_identity or (
                    f"UNVERIFIED_NUMERIC_SOURCE_{cohort}_{source_number_label}"
                    if source_number_label is not None else
                    f"UNVERIFIED_RECORD_SCOPE_{cohort}_{rid}"
                )
                key = (scope_identity, source_target_id)
                guard(key not in seen_target_source,
                      "GOLD_DUPLICATE_TARGET_SOURCE_MESSAGE")
                seen_target_source.add(key)
                counts["target_source_id_present"] += 1
            else:
                counts["target_source_id_missing"] += 1
            raw_ids = m.get("source_message_ids")
            history_ids = m.get("history_source_message_ids")
            if isinstance(raw_ids, list) and raw_ids:
                guard(len(raw_ids) == len(messages),
                      "GOLD_SOURCE_MESSAGE_ID_COUNT_MISMATCH")
                if source_target_id:
                    guard(raw_ids[-1] == source_target_id,
                          "GOLD_FINAL_TARGET_SOURCE_ID_MISMATCH")
                counts["source_message_ids_present"] += 1
            elif isinstance(history_ids, list) and history_ids:
                # Cohort108 names the historical IDs separately from target.
                guard(len(history_ids) == len(messages)-1,
                      "GOLD_HISTORY_SOURCE_ID_COUNT_MISMATCH")
                counts["history_source_message_ids_present"] += 1
            else:
                counts["source_message_ids_missing"] += 1
            contract = m.get("supervision_contract")
            if isinstance(contract, dict):
                idx = contract.get("supervised_message_index")
                if idx is not None:
                    guard(type(idx) is int and idx == len(messages)-1,
                          "GOLD_LAST_ASSISTANT_LABEL_CONTRACT_MISMATCH")
                if contract.get("only_final_assistant_supervised") is True:
                    counts["declared_final_assistant_only"] += 1
            elif contract is not None:
                counts["supervision_contract_unstructured"] += 1
            counts["actual_loss_label_mask_verified"] += 0  # never assume a runtime label test
            for k, aliases in (
                ("target_text_modified", ("target_text_modified","raw_assistant_text_edited")),
                ("history_text_modified", ("history_text_modified","raw_history_text_edited")),
                ("system_prompt_added", ("system_prompt_added",)),
            ):
                known = [m[a] for a in aliases if a in m]
                if any(v is True for v in known):
                    raise ValueError("GOLD_ORIGINAL_SOURCE_MODIFIED_OR_SYSTEM_ADDED")
                if not known:
                    counts[k+"_not_attested"] += 1
            guard(m.get("training_admission") in (None, "PENDING_NOT_APPROVED"),
                  "GOLD_UNAUTHORIZED_TRAINING_ADMISSION_STATUS")
            counts["training_admission_pending_or_unstated"] += 1
            guard(m.get("split") is None, "GOLD_UNAUTHORIZED_TRAIN_VALIDATION_SPLIT")
            counts["split_not_assigned"] += 1
            counts["version_id_present"] += int(bool(m.get("story_card_version_id")))
            counts["version_id_absent"] += int(not bool(m.get("story_card_version_id")))
            for k, keys in (
                ("qwen_token_check", ("qwen_token_length_check","qwen_16384_token_check")),
                ("loss_mask_check", ("last_round_label_mask_check","last_round_loss_mask_audit")),
                ("independent_review", ("independent_gold_review","independent_ab_review")),
                ("prior_v01_split_overlap", ("prior_v01_split_overlap",)),
                ("target_time_card", ("story_card_version_id","story_card_as_of_target")),
            ):
                value = next((m[z] for z in keys if z in m), None)
                counts[k+":"+_state(value)] += 1
            counts["source_message_records"] += len(messages)
            counts["target_characters"] += len(target["content"])
            counts["historical_assistant_messages_to_mask"] += sum(
                row["role"] == "assistant" for row in messages[:-1])
            counts["rows"] += 1
        per_cohort[cohort] = {
            "rows": counts["rows"],
            "source_message_records": counts["source_message_records"],
            "last_assistant_target_rows": counts["rows"],
            "target_source_hash_verified": counts["target_source_hash_verified"],
            "target_source_hash_missing": counts["target_source_hash_missing"],
            "source_story_id_present": counts["source_story_id_present"],
            "source_story_id_missing": counts["source_story_id_missing"],
            "source_target_id_present": counts["target_source_id_present"],
            "source_target_id_missing": counts["target_source_id_missing"],
            "source_message_ids_present": counts["source_message_ids_present"],
            "history_source_message_ids_present":
                counts["history_source_message_ids_present"],
            "source_message_ids_missing": counts["source_message_ids_missing"],
            "declared_final_assistant_only": counts["declared_final_assistant_only"],
            "supervision_contract_unstructured": counts["supervision_contract_unstructured"],
            "historical_assistant_messages_to_mask":
                counts["historical_assistant_messages_to_mask"],
            "story_card_version_id_missing": counts["version_id_absent"],
            "story_card_version_id_present": counts["version_id_present"],
            "training_admission_pending_or_unstated":
                counts["training_admission_pending_or_unstated"],
            "split_not_assigned": counts["split_not_assigned"],
            "source_story_number_unmapped": counts["source_story_number_unmapped"],
            "qwen_status": {
                key.split(":",1)[1]: value for key,value in sorted(counts.items())
                if key.startswith("qwen_token_check:")
            },
            "actual_loss_mask_status": {
                key.split(":",1)[1]: value for key,value in sorted(counts.items())
                if key.startswith("loss_mask_check:")
            },
            "independent_review_status": {
                key.split(":",1)[1]: value for key,value in sorted(counts.items())
                if key.startswith("independent_review:")
            },
            "card_time_evidence_status": {
                key.split(":",1)[1]: value for key,value in sorted(counts.items())
                if key.startswith("target_time_card:")
            },
            "original_modification_attestation_missing": sum(
                counts[k+"_not_attested"] for k in
                ("target_text_modified","history_text_modified","system_prompt_added")
            ),
        }
        global_summary.update(counts)
    return {
        "schema": SCHEMA,
        "status": "GOLD195_FROZEN_SOURCE_PREFLIGHT_ONLY__TRAINING_ADMISSION_HOLD",
        "expected_gold_cohorts": {"87": 87, "108": 108},
        "frozen_git_blob_sha1": {key: COHORTS[key]["git_blob_sha1"] for key in ("87","108")},
        "total_original_candidates": global_summary["rows"],
        "distinct_record_ids": len(seen_ids),
        "distinct_source_story_ids": len(unique_story_ids),
        "record_counts_by_source_story_number": dict(sorted(by_story.items())),
        "target_sha256_duplicate_record_count":
            sum(n - 1 for n in target_hashes.values() if n > 1),
        "per_cohort": per_cohort,
        "training_admitted_rows": 0,
        "train_rows_assigned": 0,
        "validation_rows_assigned": 0,
        "old_r45_18_hold_released_by_this_audit": 0,
        "world_component_alias_graph_certified": False,
        "target_time_card_provenance_certified": False,
        "content_rights_age_and_player_agency_review_certified": False,
        "actual_ms_swift_collator_label_mask_certified": False,
        "fresh_heldout_isolation_certified": False,
        "target_trainable_120_to_160_not_a_quota": True,
        "gold_originals_modified": False,
        "no_model_inference": True,
        "no_gpu": True,
        "no_git_mutation": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, type=Path)
    args = ap.parse_args()
    repo = args.repo.resolve()
    guard((repo / ".git").exists(), "R51_GIT_CHECKOUT_REQUIRED")
    cohorts = {k: read_exact(repo, k) for k in ("87", "108")}
    report = inspect(cohorts)
    print("R51_GOLD195_FROZEN_SOURCE_STRUCTURAL_INVENTORY_PASS__ADMISSION_HOLD")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("NO_TRAINING_SPLIT__NO_GIT_WRITE__NO_MODEL_INFERENCE__NO_GPU")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, TypeError, KeyError,
            json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        # Never echo source records or path to CI output.
        print("R51_GOLD195_STRUCTURAL_PREFLIGHT_HOLD:",
              type(exc).__name__,
              str(exc) if isinstance(exc, ValueError) else "SOURCE_UNAVAILABLE",
              file=sys.stderr)
        sys.exit(2)
