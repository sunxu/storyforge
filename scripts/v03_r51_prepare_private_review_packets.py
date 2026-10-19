"""R51 private Gold108 *content* review packets from certified original source.

Reuses v4 authenticated message offsets and the immutable Gold108 selection.
This is a bounded source-context review interface, NOT training examples or
a content-only admission. Never commit or print the private packet.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys
from collections import Counter, defaultdict
from pathlib import Path

import v03_r51_gold195_private_triage as triage
import v03_r51_gold195_readiness as base
import v03_r51_gold195_source_replay as replay

PACKET_SCHEMA = "storyforge-r51-private-gold108-context-review-packet-v1"
PREVIEW_LIMIT = 4


def require(value: bool, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def read_private_v4(path: Path, repo: Path) -> list[dict]:
    source = path.expanduser().absolute()
    require(source.is_file() and not source.is_symlink(),
            "V4_WORKPAPER_MISSING_OR_SYMLINK")
    require(source != repo and repo not in source.parents,
            "V4_MUST_BE_OUTSIDE_REPOSITORY")
    require(stat.S_IMODE(source.stat().st_mode) == 0o600 and
            stat.S_IMODE(source.parent.stat().st_mode) & 0o077 == 0,
            "V4_PRIVATE_MODE_UNSAFE")
    for ancestor in (source.parent, *source.parent.parents):
        require(not ancestor.is_symlink(), "V4_PARENT_SYMLINK_FORBIDDEN")
    with source.open(encoding="utf8") as stream:
        rows = [json.loads(line) for line in stream]
    a = base.read_pinned_rows(repo, base.GOLD87, 87,
                              blob_sha1=base.EXPECTED_GIT_SHA1_87)
    b = base.read_pinned_rows(repo, base.GOLD108, 108,
                              sha256_digest=base.EXPECTED_SHA256_108)
    index = base.read_gold108_index(repo)
    original, _ = triage.make_rows(a, b, index)
    require(len(rows) == len(original) == 195, "V4_ROW_COUNT_CHANGED")
    pinned = ("candidate_id", "cohort", "source_rank", "source_story_id",
              "original_target_message_id", "original_target_sha256",
              "history_fingerprints", "source_reference", "metadata_risks")
    for row, frozen in zip(rows, original, strict=True):
        require(all(row.get(k) == frozen[k] for k in pinned),
                "V4_FROZEN_SOURCE_ID_OR_HASH_CHANGED")
        require(row.get("schema") == "storyforge-r51-private-gold195-triage-v4"
                and row.get("training_admission") == triage.HOLD
                and row.get("split") is None,
                "V4_SCHEMA_OR_TRAINING_STATUS_INVALID")
        require(row.get("owner_attestation", {}).get("scope") ==
                "AGE_CONSENT_AND_CONTENT_BOUNDARIES",
                "V4_OWNER_ATTESTATION_MISSING")
        if row["cohort"] == 108:
            review = row["source_review"]
            proof = review.get("raw_source_receipt") or {}
            require(row.get("source_archive_replay") ==
                    "ORIGINAL_ROOT_MESSAGE_ID_SHA_ROLE_PASS"
                    and review.get("raw_history_contiguous_before_target")
                    == "PASS_ROLE_SHA" and
                    review.get("raw_history_in_order") == "PASS_ROLE_SHA"
                    and review.get("source_pointer_verified") ==
                    "ROOT_MESSAGES_INDEX_ID_SHA_ROLE_VERIFIED"
                    and isinstance(
                        proof.get("original_root_messages_array_index"), int),
                    "V4_SOURCE_AND_WINDOW_NOT_FULLY_VERIFIED")
    return rows


def verified_review_packet(
    row: dict, frozen_gold: dict, source_messages: list[dict],
    raw_sha: str, raw_zip_sha: str,
) -> dict:
    """No story title or invented card; original bytes, ordered by source index."""
    original_index = row["source_review"]["raw_source_receipt"][
        "original_root_messages_array_index"]
    require(isinstance(original_index, int) and
            0 <= original_index < len(source_messages),
            "TARGET_SOURCE_INDEX_OUT_OF_RANGE")
    target = source_messages[original_index]
    require(target.get("id") == row["original_target_message_id"] and
            replay.normalize_role(target.get("role")) == "assistant" and
            isinstance(target.get("content"), str) and
            triage.digest(target["content"]) == row["original_target_sha256"],
            "VERIFIED_TARGET_ID_SHA_ROLE_NOT_REPRODUCED")
    require(row["source_review"]["raw_source_receipt"].get(
        "source_jsonl_sha256") == raw_sha and
        row["source_review"]["raw_source_receipt"].get(
            "raw_zip_sha256") == raw_zip_sha,
        "V4_SOURCE_ARCHIVE_PROOF_MISMATCH")
    history = frozen_gold["messages"][:-1]
    history_count = len(history)
    start = original_index - history_count
    require(start >= 0, "ORIGINAL_VISIBLE_WINDOW_BEFORE_FIRST_MESSAGE")
    source_history = source_messages[start:original_index]
    for observed, selected in zip(source_history, history, strict=True):
        require(isinstance(observed, dict) and
                isinstance(observed.get("content"), str) and
                replay.normalize_role(observed.get("role")) ==
                replay.normalize_role(selected.get("role")) and
                triage.digest(observed["content"]) == triage.digest(selected["content"]),
                "VISIBLE_HISTORY_ROLE_OR_BODY_MISMATCH")
    require(triage.digest(frozen_gold["messages"][-1]["content"]) ==
            row["original_target_sha256"], "FROZEN_TARGET_DIFFERENT")

    preview_start = max(0, start - PREVIEW_LIMIT)
    prior = source_messages[preview_start:start]
    def display_message(raw: dict, source_index: int) -> dict:
        require(isinstance(raw, dict) and
                isinstance(raw.get("id"), str) and
                isinstance(raw.get("content"), str),
                "REVIEW_PREVIEW_MESSAGE_UNSUPPORTED")
        return {
            "role": replay.normalize_role(raw.get("role")),
            "content": raw["content"],
            "original_source_message_id": raw["id"],
            "original_source_array_index": source_index,
            "source_body_sha256": triage.digest(raw["content"]),
        }

    visible = [
        display_message(m, start + i)
        for i, m in enumerate(source_history)
    ]
    prior_preview = [
        display_message(m, preview_start + i)
        for i, m in enumerate(prior)
    ]
    return {
        "schema": PACKET_SCHEMA,
        "private_do_not_commit": True,
        "candidate_id": row["candidate_id"],
        "story_rank": row["source_rank"],
        "source_story_id": row["source_story_id"],
        "target_message_id": row["original_target_message_id"],
        "target_sha256": row["original_target_sha256"],
        "source_original_raw_jsonl_sha256": raw_sha,
        "source_original_raw_zip_sha256": raw_zip_sha,
        "target_original_array_index": original_index,
        "target_original_turn_index": target.get("turn_index"),
        "target_content_for_review_only": target["content"],
        "frozen_visible_history": visible,
        "preceding_source_preview_NOT_PART_OF_FROZEN_INPUT": prior_preview,
        "preview_is_not_complete_world_history": True,
        "frozen_visible_first_role": visible[0]["role"] if visible else None,
        "source_window_start_index": start,
        "historical_card_version_verified": False,
        "owner_age_consent_content_attested": True,
        "rights_or_license_certified": False,
        "context_only_route": "UNDECIDED__SOURCE_REVIEW_REQUIRED",
        "card_or_long_range_dependency": "UNDECIDED__SOURCE_REVIEW_REQUIRED",
        "facts_present_only_in_unseen_prior_history": "UNDECIDED",
        "player_agency_and_forbidden_rule_compliance": "UNDECIDED",
        "historical_world_rule_conflicts": "UNDECIDED",
        "source_review_scope": (
            "FROZEN_VISIBLE_CONTEXT_PLUS_UP_TO_4_PRECEDING_SOURCE_MESSAGES_"
            "NOT_A_FULL_STORY_REVIEW"),
        "reviewer_1": {"decision": "PENDING", "source_citations": [],
                       "context_dependency_rationale": None},
        "reviewer_2": {"decision": "PENDING", "source_citations": [],
                       "context_dependency_rationale": None},
        "training_admission": "PENDING_NOT_APPROVED",
        "split": None,
    }


def prepare(repo: Path, v4_rows: list[dict],
            original_raw_zip_by_rank: dict[int, bytes]) -> tuple[list[dict], dict]:
    pinned_gold = base.read_pinned_rows(
        repo, base.GOLD108, 108, sha256_digest=base.EXPECTED_SHA256_108)
    indexed = {r["id"]: r for r in pinned_gold}
    require(len(indexed) == 108, "ORIGINAL_GOLD108_DUPLICATE_ID")
    groups: dict[int, list[dict]] = defaultdict(list)
    for row in v4_rows:
        if row["cohort"] == 108:
            groups[row["source_rank"]].append(row)
    require(sum(map(len, groups.values())) == 108,
            "V4_GOLD108_ROW_COUNT_CHANGED")
    packets = []
    stats = Counter()
    by_rank = {}
    for rank, group in sorted(groups.items()):
        hashes = {r["source_reference"]["source_jsonl_sha256"]
                  for r in group
                  if r["source_reference"].get("source_jsonl_sha256")}
        payload = replay.choose_source_jsonl(
            original_raw_zip_by_rank[rank], hashes)
        roots = [json.loads(line) for line in
                 payload.decode("utf-8-sig").splitlines() if line.strip()]
        require(len(roots) == 1 and isinstance(roots[0].get("messages"), list),
                "RAW_SOURCE_ROOT_INVALID")
        messages = roots[0]["messages"]
        raw_sha = replay.sha256(payload)
        raw_zip_sha = replay.sha256(original_raw_zip_by_rank[rank])
        seen = set()
        local = Counter()
        for row in group:
            require(row["candidate_id"] not in seen,
                    "DUPLICATE_PRIVATE_CANDIDATE")
            seen.add(row["candidate_id"])
            pkt = verified_review_packet(
                row, indexed[row["candidate_id"]], messages, raw_sha, raw_zip_sha)
            packets.append(pkt)
            local["packets"] += 1
            local["starts_with_assistant"] += int(
                pkt["frozen_visible_first_role"] == "assistant")
            local["starts_with_user"] += int(
                pkt["frozen_visible_first_role"] == "user")
            local["has_prior_original_preview"] += int(bool(
                pkt["preceding_source_preview_NOT_PART_OF_FROZEN_INPUT"]))
            local["recovered_pointer_gap"] += int(
                "SOURCE_POINTER_RECONCILIATION_HOLD" in row["holds"])
        stats.update(local)
        by_rank[str(rank)] = dict(local)
    require(len(packets) == 108, "PRIVATE_REVIEW_PACKET_COUNT_CHANGED")
    return packets, {
        "schema": "storyforge-r51-gold108-private-review-packet-counts-v1",
        "status": "108_PRIVATE_SOURCE_REVIEW_PACKETS_PREPARED__NO_ADMISSION",
        "packets_created": stats["packets"],
        "starts_with_assistant": stats["starts_with_assistant"],
        "starts_with_user": stats["starts_with_user"],
        "has_prior_original_preview": stats["has_prior_original_preview"],
        "recovered_pointer_gaps_in_scope": stats["recovered_pointer_gap"],
        "by_story_rank": by_rank,
        "content_or_candidate_ids_in_stdout": False,
        "source_replay_source_text_committed": False,
        "reviewer_source_content_review_performed": 0,
        "train_admitted": 0,
        "validation_admitted": 0,
        "world_split_assigned": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--private-v4", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        repo = args.repo.resolve(strict=True)
        rows = read_private_v4(args.private_v4, repo)
        asset, archive_index = replay.pinned_archive(repo)
        original_raw_zip_by_rank = replay.discover_raw_zips(
            asset, archive_index)
        packets, stats = prepare(repo, rows, original_raw_zip_by_rank)
        triage.write_private(args.output, packets, repo)
    except (OSError, ValueError, AssertionError, KeyError, TypeError,
            json.JSONDecodeError, UnicodeError, RuntimeError) as exc:
        print("R51_PRIVATE_CONTEXT_REVIEW_PREPARATION_HOLD__" +
              type(exc).__name__, file=sys.stderr)
        return 2
    print("R51_GOLD108_PRIVATE_SOURCE_CONTEXT_REVIEW_PACKETS_CREATED__NO_ADMISSION")
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
