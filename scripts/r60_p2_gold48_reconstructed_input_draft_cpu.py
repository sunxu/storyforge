"""Prepare 48 strictly source-bound reconstructed input drafts, CPU-only.

Reuses existing candidate/source-component contracts, the previously authored
GENERIC_SYSTEM, and history_recovery's proven pre-target summary gate. This is
NOT historical actual-sent input, prompt freeze, or inference authorization.
Does not open the historical Original Reference file or call a model/database.
No silent truncation, no invented rules/memory, no sampling or token estimate.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
from collections import Counter
from datetime import datetime
from pathlib import Path

from r60_base_constructed_system_contract_v1 import CONTRACT_ID, GENERIC_SYSTEM
from r60_p2_gold48_source_component_bind_cpu import (
    FIELDS,
    Hold,
    canonical,
    check_private_root,
    create_new,
    private_json,
    require,
    sha,
)

SCHEMA = "storyforge_r60_gold48_reconstructed_inputs_draft_private_v1"
SAFE_SCHEMA = "storyforge_r60_p2_gold48_reconstructed_inputs_draft_safe_v1"
MAX_DRAFT_BYTES = 32 * 1024 * 1024
MAX_SINGLE_INPUT_BYTES = 256 * 1024
MEMORY_KEYS = ("memory_summary", "recent_summary", "rolling_outline")
PROVENANCE = "EVALUATION_TIME_SNAPSHOT"
SYSTEM_SOURCE = "R60_BASE_CONSTRUCTED_SYSTEM_V1.GENERIC_SYSTEM"
INPUT_CONTRACT = "RECONSTRUCTED_EVALUATION_INPUT"


def check_summaries(recovered, target_created_at):
    summaries = recovered.get("pretarget_summaries")
    summary_status = recovered.get("summary_status")
    require(isinstance(summaries, list) and len(summaries) <= 1,
            "PRETARGET_SUMMARY_SHAPE_HOLD")
    if not summaries:
        require(summary_status == "NO_VERIFIED_PRETARGET_SUMMARY",
                "PRETARGET_SUMMARY_STATUS_HOLD")
        return None, "NO_VERIFIED_PRETARGET_MEMORY"
    summary = summaries[0]
    require(summary_status == "PRETARGET_SUMMARY_AVAILABLE"
            and isinstance(summary, dict)
            and summary.get("status") == "PRETARGET_COVERAGE_VERIFIED"
            and summary.get("used") is True
            and isinstance(summary.get("fields"), dict)
            and bool(summary["fields"])
            and set(summary["fields"]) <= set(MEMORY_KEYS),
            "PRETARGET_SUMMARY_PROVENANCE_HOLD")
    try:
        reported = datetime.fromisoformat(summary["updated_at"])
        target_time = datetime.fromisoformat(target_created_at)
        require(reported.tzinfo is not None and target_time.tzinfo is not None
                and reported < target_time,
                "PRETARGET_SUMMARY_TIMESTAMP_HOLD")
    except (KeyError, AttributeError, TypeError, ValueError) as exc:
        if isinstance(exc, Hold):
            raise
        raise Hold("PRETARGET_SUMMARY_TIMESTAMP_HOLD") from None
    require(all(isinstance(v, str) and v.strip() for v in summary["fields"].values())
            and len(canonical(summary["fields"])) <= 64 * 1024,
            "PRETARGET_MEMORY_TEXT_HOLD")
    return {k: summary["fields"][k] for k in MEMORY_KEYS
            if k in summary["fields"]}, "VERIFIED_PRETARGET_SESSION_SUMMARY"


def check_card(raw_evidence, source_binding):
    cards = raw_evidence.get("p2_scope", {}).get("source_records_PRIVATE")
    require(isinstance(cards, list) and len(cards) == 8, "P2_PUBLIC_CARDS_COUNT_HOLD")
    result = {}
    for card in cards:
        story = card.get("story_id_PRIVATE")
        fields = card.get("source_fields_PRIVATE")
        require(isinstance(story, str) and story not in result
                and isinstance(fields, dict) and set(fields) == set(FIELDS),
                "P2_PUBLIC_CARD_FIELDS_HOLD")
        result[story] = card
    require(len(result) == 8 and len(source_binding) == 48,
            "P2_CARD_BINDING_COVERAGE_HOLD")
    return result


def assemble_system(fields, memory):
    # Serialize actual JSON source fields with exact deterministic JSON bytes.
    # Missing fields are explicitly omitted, never synthesized.
    pieces = [
        GENERIC_SYSTEM,
        "以下为评估时点公开卡的原始结构化设定，非历史 actual-sent 记录。",
    ]
    names = {
        "world": "公开卡世界与明示规则",
        "character": "公开卡单角色",
        "characters": "公开卡多角色",
        "opening": "公开卡开场",
    }
    for field in FIELDS:
        if fields[field] is not None:
            pieces.append(names[field] + "（JSON）:\n" +
                          canonical(fields[field]).decode("utf-8"))
    if memory is None:
        pieces.append("未找到已验证的目标回复之前会话摘要，不补造历史记忆。")
    else:
        pieces.append("经历史恢复验证的目标回复之前会话摘要（JSON）:\n"
                      + canonical(memory).decode("utf-8"))
    return "\n\n".join(pieces)


def draft(candidate_dir, source_bind_dir, evidence_path, manifest_path):
    loc, loc_raw = private_json(
        candidate_dir / "GOLD48_CANDIDATE_LOCATORS_PRIVATE.json", 5 * 1024 * 1024)
    pre, pre_raw = private_json(
        candidate_dir / "GOLD48_CANDIDATE_PREFIXES_PRIVATE.json", 32 * 1024 * 1024)
    binding, binding_raw = private_json(
        source_bind_dir / "GOLD48_SOURCE_COMPONENT_BINDINGS_PRIVATE.json", 10 * 1024 * 1024)
    safe, _ = private_json(
        source_bind_dir / "GOLD48_SOURCE_COMPONENT_BINDING_SAFE.json", 1024 * 1024)
    evidence, evidence_raw = private_json(evidence_path, 32 * 1024 * 1024)
    manifest, manifest_raw = private_json(manifest_path, 2 * 1024 * 1024)
    require(
        binding.get("schema") == "storyforge_r60_gold48_source_component_binding_private_v1"
        and binding.get("status") == "PUBLIC_CARD_COMPONENTS_BOUND__RECONSTRUCTED_INPUT_PENDING"
        and binding.get("eval_input_contract") == INPUT_CONTRACT
        and binding.get("gold48_locators_file_sha256_PRIVATE") == sha(loc_raw)
        and binding.get("gold48_prefixes_file_sha256_PRIVATE") == sha(pre_raw)
        and binding.get("source_evidence_file_sha256_PRIVATE") == sha(evidence_raw)
        and binding.get("source_manifest_file_sha256_PRIVATE") == sha(manifest_raw)
        and safe.get("status") == "GOLD48_PUBLIC_SOURCE_COMPONENTS_BOUND__INPUT_NOT_FROZEN"
        and safe.get("case_count") == 48
        and safe.get("owner_gold48_freeze") is False
        and evidence.get("schema") == "storyforge_r60_base336_p2_source_evidence_private_v1"
        and evidence.get("p2_scope", {}).get("manifest_sha256_PRIVATE") ==
        sha(manifest_raw)
        and manifest.get("schema") == "storyforge_r60_base336_p2_public_source_inventory_private_v2",
        "CANDIDATE_SOURCE_EVIDENCE_FILE_BINDING_HOLD",
    )
    locator_rows, prefix_rows, bound_rows = (
        doc.get("cases_PRIVATE") for doc in (loc, pre, binding)
    )
    require(all(isinstance(rows, list) and len(rows) == 48
                for rows in (locator_rows, prefix_rows, bound_rows)),
            "GOLD48_DRAFT_CASE_COUNT_HOLD")
    expected_ids = [f"G48-C{i:02d}" for i in range(1, 49)]
    for rows in (locator_rows, prefix_rows, bound_rows):
        require([x.get("candidate_case_id_PRIVATE") for x in rows] == expected_ids,
                "GOLD48_DRAFT_CASE_ORDER_HOLD")
    bound_by_case = {x["candidate_case_id_PRIVATE"]: x for x in bound_rows}
    card_by_story = check_card(evidence, bound_rows)

    result, memory_count, no_memory_count = [], 0, 0
    source_counts = Counter()
    for locator, prefix in zip(locator_rows, prefix_rows, strict=True):
        case_id = locator["candidate_case_id_PRIVATE"]
        bound = bound_by_case[case_id]
        story = locator.get("story_id_PRIVATE")
        card = card_by_story.get(story)
        require(card is not None
                and story == prefix.get("history_recovery_PRIVATE", {}).get("story_id")
                and story == bound.get("story_id_PRIVATE")
                and locator.get("source_key_PRIVATE") == bound.get("source_key_PRIVATE")
                and locator.get("source_public_revision_PRIVATE") ==
                bound.get("source_public_revision_PRIVATE")
                and locator.get("source_snapshot_sha256_PRIVATE") ==
                bound.get("source_snapshot_sha256_PRIVATE")
                and card.get("public_content_revision_PRIVATE") ==
                bound.get("source_public_revision_PRIVATE")
                and card.get("submission_snapshot_sha256_PRIVATE") ==
                bound.get("source_snapshot_sha256_PRIVATE")
                and bound.get("public_component_provenance") == PROVENANCE
                and bound.get("historical_asof_card_verified") is False
                and bound.get("original_reference_included") is False
                and bound.get("reconstructed_messages_frozen") is False,
                "GOLD48_COMPONENT_CASE_IDENTITY_HOLD")
        fields = card.get("source_fields_PRIVATE")
        require(isinstance(fields, dict) and set(fields) == set(FIELDS)
                and all(
                    bound.get("public_component_hashes_PRIVATE", {}).get(field) ==
                    (sha(canonical(fields[field])) if fields[field] is not None else None)
                    for field in FIELDS
                ), "GOLD48_PUBLIC_COMPONENT_DIGEST_HOLD")
        history = prefix.get("prefix_messages_PRIVATE")
        recovered = prefix.get("history_recovery_PRIVATE")
        require(isinstance(history, list) and 3 <= len(history) <= 40
                and isinstance(recovered, dict)
                and sha(canonical(history)) == bound.get("prefix_sha256_PRIVATE")
                and sha(canonical(history)) == locator.get("prefix_sha256_PRIVATE")
                and history[-1].get("role") == "user"
                and all(isinstance(msg, dict) and set(msg) == {"role", "content"}
                        and isinstance(msg["content"], str) and msg["content"].strip()
                        and msg["role"] in ("user", "assistant") for msg in history),
                "GOLD48_HISTORY_INTEGRITY_HOLD")
        memory, memory_status = check_summaries(
            recovered, locator.get("target_created_at_PRIVATE"))
        memory_count += int(memory is not None)
        no_memory_count += int(memory is None)
        messages = [{"role": "system",
                     "content": assemble_system(fields, memory)}, *history]
        require(len(messages) <= 64 and
                len(canonical(messages)) <= MAX_SINGLE_INPUT_BYTES,
                "GOLD48_NO_TRUNCATION_INPUT_SIZE_HOLD")
        source_counts[story] += 1
        result.append({
            "candidate_case_id_PRIVATE": case_id,
            "story_id_PRIVATE": story,
            "source_revision_PRIVATE": bound["source_public_revision_PRIVATE"],
            "source_snapshot_sha256_PRIVATE": bound["source_snapshot_sha256_PRIVATE"],
            "source_components_provenance": PROVENANCE,
            "system_provenance": "EVALUATION_CONSTRUCTED_GENERIC_SYSTEM",
            "system_contract_id": CONTRACT_ID,
            "rules_provenance": "ONLY_AS_EXPRESSED_IN_PUBLIC_CARD_WORLD",
            "memory_provenance": memory_status,
            "historical_actual_sent_verified": False,
            "history_prefix_sha256_PRIVATE": prefix["prefix_sha256_PRIVATE"],
            "reconstructed_messages_sha256_PRIVATE": sha(canonical(messages)),
            "reconstructed_messages_PRIVATE": messages,
        })
    require(len(source_counts) == 8 and set(source_counts.values()) == {6}
            and memory_count + no_memory_count == 48,
            "GOLD48_DRAFT_SOURCE_AND_MEMORY_COUNTS_HOLD")
    package = {
        "schema": SCHEMA,
        "status": "RECONSTRUCTED_48_INPUT_DRAFT__OWNER_FREEZE_PENDING",
        "input_contract": INPUT_CONTRACT,
        "system_template": SYSTEM_SOURCE,
        "system_template_sha256_PRIVATE": sha(GENERIC_SYSTEM.encode("utf-8")),
        "source_component_binding_sha256_PRIVATE": sha(binding_raw),
        "evaluation_time_snapshot": True,
        "historical_actual_sent_verified": False,
        "memory_absent_not_fabricated": True,
        "original_reference_not_read_or_included": True,
        "prompt_owner_freeze": False,
        "cases_PRIVATE": result,
    }
    require(len(canonical(package)) <= MAX_DRAFT_BYTES,
            "GOLD48_DRAFT_PACKAGE_TOO_LARGE_HOLD")
    receipt = {
        "schema": SAFE_SCHEMA,
        "status": "GOLD48_RECONSTRUCTED_INPUT_DRAFT_48_READY__NOT_FROZEN",
        "case_count": 48,
        "source_count": 8,
        "prefixes_unchanged": True,
        "evaluation_time_public_card_components_bound": 48,
        "memory_pretarget_verified_count": memory_count,
        "memory_unverified_omitted_count": no_memory_count,
        "per_case_reconstructed_messages_sha256_created": 48,
        "original_reference_read": False,
        "historical_actual_sent_verified": False,
        "owner_gold48_freeze": False,
        "database_accessed": False,
        "gpu_started": False,
        "model_calls": 0,
        "private_values_emitted": False,
    }
    return package, receipt


def run(args):
    base = Path.home() / ".local/share/storyforge/r60/private"
    check_private_root(base)
    require(args.candidate_dir.parent == base
            and args.binding_dir.parent == base
            and args.output_dir.parent == base
            and args.evidence.is_relative_to(base)
            and args.manifest.is_relative_to(base)
            and not args.output_dir.exists()
            and not args.output_dir.is_symlink(),
            "GOLD48_DRAFT_PATH_SCOPE_HOLD")
    doc, receipt = draft(
        args.candidate_dir, args.binding_dir, args.evidence, args.manifest)
    os.mkdir(args.output_dir, mode=0o700)
    require(stat.S_IMODE(args.output_dir.stat().st_mode) == 0o700,
            "GOLD48_DRAFT_OUTPUT_DIRECTORY_MODE_HOLD")
    create_new(args.output_dir / "GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json", doc)
    create_new(args.output_dir / "GOLD48_RECONSTRUCTED_INPUTS_DRAFT_SAFE.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--binding-dir", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
    except (Hold, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        reason = (str(exc) if isinstance(exc, Hold)
                  else "GOLD48_RECONSTRUCTED_DRAFT_RUNTIME_HOLD")
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "HOLD",
            "reason_code": reason,
            "database_accessed": False,
            "gpu_started": False,
            "model_calls": 0,
            "private_values_emitted": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
