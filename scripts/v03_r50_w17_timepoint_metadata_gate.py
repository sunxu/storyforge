"""W17 timepoint metadata audit anchored to frozen full-message AI review.

No AI/GPU, no prompt leakage, no Git write. Checks W17 cited original
message times against Git-pinned W17 export-card metadata. Cannot certify
which character card or long-term rules were actually sent to the model.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import v03_r50_build_w17_semantic_kit as kit_builder
import v03_r50_full_original_world_inventory as inventory
import v03_r50_verify_w17_full_source_review as review

PINNED_FULL_REVIEW_SHA256 = "6482dd02b27d80f72763b23b848cf7c0b2765853f09ef0beb2ae4961d50b7ce3"
EXPECTED_TOTAL_DOSSIER_MESSAGES = 344
W17_RANK = 17


def require(ok: bool, marker: str) -> None:
    if not ok:
        raise ValueError(marker)


def parsed_time(value: object) -> datetime:
    require(isinstance(value, str) and bool(value.strip()),
            "SOURCE_TIME_FIELD_MISSING")
    timestamp = datetime.fromisoformat(value)
    require(timestamp.tzinfo is not None and timestamp.utcoffset() is not None,
            "SOURCE_TIMEZONE_REQUIRED")
    return timestamp


def audit_w17_timepoint(card: dict, transcript: dict, dossiers: list[dict],
                        decision: dict) -> dict:
    """Structural chronology check only. No world-link classification."""
    require(card.get("rank") == W17_RANK and
            transcript.get("rank") == W17_RANK and
            card.get("story_id") == inventory.identity(transcript),
            "W17_FROZEN_CARD_TRANSCRIPT_ID_MISMATCH")
    messages = transcript.get("messages")
    require(isinstance(messages, list) and messages, "W17_MESSAGES_MISSING")
    span = card.get("chat_window") or {}
    first = parsed_time(span.get("first_message_at"))
    last = parsed_time(span.get("last_message_at"))
    require(first <= last, "W17_CHAT_WINDOW_INVERTED")
    export = card.get("export_time_card") or {}
    author = card.get("current_author_card") or {}
    public = card.get("current_public_projection") or {}
    updated = parsed_time(export.get("updated_at"))
    created = parsed_time(export.get("created_at"))
    observed = parsed_time(export.get("observed_at"))
    author_updated = parsed_time(author.get("updated_at"))
    public_observed = parsed_time(public.get("observed_at"))
    require(created <= updated <= observed and
            author_updated <= public_observed,
            "W17_CARD_METADATA_TIME_INCONSISTENT")
    versions = card.get("content_versions")
    moderation = card.get("moderation_source_snapshots")
    require(isinstance(versions, list) and
            isinstance(moderation, list), "W17_VERSION_LISTS_INVALID")
    require(len(dossiers) == 7 and
            len(decision.get("gap_reviews", [])) == 7,
            "SEVEN_SCOPED_WORKPAPERS_REQUIRED")
    listed = 0
    reported_refs = 0
    w17_dossier_rows = 0
    w17_referenced = 0
    unique_refs: set[int] = set()
    citation_times = []
    missing_citation_timestamp = 0
    outside_window_citations = 0
    for packet, gap in zip(dossiers, decision["gap_reviews"], strict=True):
        require(packet.get("gap_index") == gap.get("gap_index"),
                "GAP_INDEX_MISMATCH")
        locators = {
            (r["source_rank"], r["original_source_message_index"]): r
            for r in packet["full_original_messages"]
        }
        listed += len(locators)
        w17_dossier_rows += sum(rank == W17_RANK for rank, _ in locators)
        refs = gap.get("source_refs")
        require(isinstance(refs, list), "FULL_REVIEW_REFERENCES_INVALID")
        reported_refs += len(refs)
        for r in locators.values():
            if r["source_rank"] != W17_RANK:
                continue
            index = r["original_source_message_index"]
            require(type(index) is int and 0 <= index < len(messages),
                    "W17_FULL_MESSAGE_INDEX_INVALID")
            source = messages[index]
            require(isinstance(source, dict) and
                    isinstance(source.get("content"), str) and
                    source["content"] == r.get("full_source_text") and
                    review.sha(source["content"].encode("utf8")) ==
                    r.get("original_message_sha256"),
                    "W17_DOSSIER_TEXT_NOT_EQUAL_TO_FROZEN_SOURCE")
        for r in refs:
            if r.get("source_rank") != W17_RANK:
                continue
            index = r.get("source_message_index")
            require(type(index) is int and 0 <= index < len(messages) and
                    (W17_RANK, index) in locators,
                    "W17_REVIEW_REF_NOT_IN_FROZEN_DOSSIER")
            w17_referenced += 1
            unique_refs.add(index)
            when_value = messages[index].get("created_at")
            if when_value is None:
                missing_citation_timestamp += 1
                continue
            date = parsed_time(when_value)
            citation_times.append(date)
            outside_window_citations += int(date < first or date > last)

    require(listed == EXPECTED_TOTAL_DOSSIER_MESSAGES,
            "PRIVATE_COMPLETE_MESSAGE_TOTAL_CHANGED")
    require(reported_refs == 75,
            "PRIVATE_SOURCE_CITATION_TOTAL_CHANGED")
    w17_before_export_update = sum(t < updated for t in citation_times)
    w17_before_public_observation = sum(t < public_observed for t in citation_times)
    return {
        "schema": "storyforge-r50-w17-full-message-temporal-metadata-v1",
        "source": "PRIVATE_FULL_AI_REVIEW_AND_GIT_PINNED_W17_CARD",
        "total_dossier_message_entries": listed,
        "full_review_source_citations": reported_refs,
        "w17_dossier_message_entries": w17_dossier_rows,
        "w17_citations_in_review": w17_referenced,
        "w17_distinct_cited_original_messages": len(unique_refs),
        "w17_citations_with_timestamp": len(citation_times),
        "w17_citations_without_timestamp": missing_citation_timestamp,
        "w17_citations_outside_reported_chat_window": outside_window_citations,
        "w17_citations_earlier_than_export_card_last_edit":
            w17_before_export_update,
        "w17_citations_earlier_than_public_card_observation":
            w17_before_public_observation,
        "export_card_last_edit_precedes_first_chat_message": updated < first,
        "export_card_creation_precedes_first_chat_message": created < first,
        "export_card_observed_after_last_chat_message": observed > last,
        "author_card_last_edit_precedes_first_chat_message": author_updated < first,
        "public_card_observed_after_last_chat_message": public_observed > last,
        "content_version_snapshot_count": len(versions),
        "moderation_source_snapshot_count": len(moderation),
        "export_card_last_edit_is_only_metadata_not_runtime_prompt_proof": True,
        "all_historical_card_fields_valid_at_actual_prompt_cutoff":
            "NOT_CERTIFIED",
        "full_chat_story_arc_and_transitive_alias_graph": "HOLD",
        "remaining_gap_assessments": "SEVEN_INSUFFICIENT_CONTEXT",
        "semantic_world_graph_gate": "HOLD",
        "heldout_final_seal": "NOT_PERFORMED",
        "no_private_story_text_emitted": True,
        "no_git_write": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--dossiers-dir", required=True, type=Path)
    ap.add_argument("--workpaper", required=True, type=Path)
    args = ap.parse_args()
    repo = args.repo.resolve()
    require((repo / ".git").exists(), "LOCAL_GIT_CHECKOUT_REQUIRED")
    dossier_dir = args.dossiers_dir.expanduser().absolute().resolve()
    require(repo != dossier_dir and repo not in dossier_dir.parents,
            "PRIVATE_DOSSIERS_INSIDE_REPO")
    dossiers, manifest_sha, _ = review.load_dossiers(dossier_dir)
    file = review.private_file(args.workpaper, repo)
    require(review.sha(file) == PINNED_FULL_REVIEW_SHA256,
            "PRIVATE_FULL_REVIEW_HASH_MISMATCH")
    decision = json.loads(file)
    review.summarize(dossiers, manifest_sha, decision, review.sha(file))
    card = kit_builder.frozen_w17_card(repo)
    receipt = json.loads((repo / inventory.RECEIPT).read_text(encoding="utf8"))
    world = next(w for w in receipt["worlds"] if w["number"] == 17)
    path = repo / inventory.ROOT / world["folder"] / (world["folder"] + ".jsonl")
    transcript = json.loads(path.read_text(encoding="utf8"))
    result = audit_w17_timepoint(card, transcript, dossiers, decision)
    print("R50_W17_FULL_SOURCE_TIMEPOINT_METADATA_CHECKED__CARD_CUTOFF_HOLD")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("NO_GIT_WRITE__NO_MODEL_INFERENCE__NO_FINAL_SEAL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError,
            UnicodeError, json.JSONDecodeError) as exc:
        print("R50_W17_TIMEPOINT_GATE_HOLD:", type(exc).__name__,
              str(exc)[:120], file=sys.stderr)
        sys.exit(2)
