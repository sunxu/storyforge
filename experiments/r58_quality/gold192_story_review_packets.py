"""Build private per-world Gold192 semantic review packets; never train-ready."""
import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

from gold192_incremental_review_triage import inspect as inspect_triage
from legacy_gold_target_reuse import SCHEMA, canonical, private_file, safe_reason

OUT_SCHEMA = "r58_gold192_story_semantic_review_packet_private_v1"
CANDIDATE = "CANDIDATE_ONLY_QUALITY_HOLD"
EXCLUDED = "EXCLUDED_WORLD_UNRESOLVED"
GOLD108_REASON = "CONTEXT_EQUIVALENCE_UNVERIFIED"
GOLD87_REASON = "HISTORICAL_EVIDENCE_NOT_FULLY_BOUND"
CARD_SOURCE = "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST"


def load_jsonl(path, label):
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
                if len(rows) > 195:
                    raise ValueError(label + "_COUNT_INVALID")
    return rows


def build_packets(tasks_path, queue_path, scope_path):
    triage = inspect_triage(tasks_path, queue_path, scope_path)
    if triage["status"] != "GOLD192_INCREMENTAL_REVIEW_ROUTING_READY__SEMANTIC_HOLD":
        raise ValueError("TRIAGE_NOT_READY")
    queue_rows = load_jsonl(queue_path, "QUEUE")
    scope_rows = load_jsonl(scope_path, "SCOPE")
    task_rows = load_jsonl(tasks_path, "TASK")
    reasons = {r["case_id"]: r["reason_code"] for r in queue_rows}
    states = {r["case_id"]: r["scope_status"] for r in scope_rows}
    if len(reasons) != 195 or len(states) != 195 or len(task_rows) != 195:
        raise ValueError("PACKET_INPUT_COUNTS_INVALID")

    worlds = {}
    counts = Counter()
    seen = set()
    for task in task_rows:
        if not isinstance(task, dict) or task.get("schema") != SCHEMA:
            raise ValueError("PACKET_TASK_SCHEMA_INVALID")
        case_id = task.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("PACKET_CASE_ID_INVALID")
        seen.add(case_id)
        reason = reasons.get(case_id)
        state = states.get(case_id)
        if reason is None or state is None:
            raise ValueError("PACKET_SCOPE_BINDING_INVALID")
        if state == EXCLUDED:
            if reason != "WORLD_OR_TARGET_IDENTITY_HOLD":
                raise ValueError("PACKET_EXCLUSION_REASON_INVALID")
            counts["excluded_world_identity_unresolved"] += 1
            continue
        if state != CANDIDATE or reason not in {GOLD108_REASON, GOLD87_REASON}:
            raise ValueError("PACKET_CANDIDATE_STATE_INVALID")

        messages = task.get("messages")
        if (not isinstance(messages, list) or len(messages) < 2
                or messages[0].get("role") != "system"
                or messages[-1].get("role") != "user"
                or any(not isinstance(m, dict) or set(m) != {"role", "content"}
                       or m.get("role") not in {"system", "user", "assistant"}
                       or not isinstance(m.get("content"), str) or not m["content"].strip()
                       for m in messages)):
            raise ValueError("PACKET_MESSAGE_SHAPE_INVALID")
        if hashlib.sha256(canonical(messages)).hexdigest() != task.get("input_messages_sha256"):
            raise ValueError("PACKET_INPUT_HASH_INVALID")
        target = task.get("target_text")
        if (not isinstance(target, str) or not target.strip()
                or hashlib.sha256(target.encode("utf-8")).hexdigest() != task.get("target_sha256")):
            raise ValueError("PACKET_TARGET_HASH_INVALID")
        card_text = messages[0]["content"]
        try:
            card = json.loads(card_text)
        except (ValueError, TypeError, json.JSONDecodeError):
            raise ValueError("PACKET_CARD_JSON_INVALID") from None
        if not isinstance(card, dict) or not card:
            raise ValueError("PACKET_CARD_JSON_INVALID")
        card_bytes = json.dumps(card, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        card_hash = hashlib.sha256(card_bytes).hexdigest()
        if (card_bytes.decode("utf-8") != card_text
                or card_hash != task.get("card_snapshot_sha256")
                or task.get("card_source_kind") != CARD_SOURCE
                or task.get("input_design_status") != "PROPOSED_OFFLINE_CARD_NOT_APPROVED"
                or task.get("review_status") != "UNREVIEWED"
                or task.get("review_results") != []
                or task.get("quality_v1_admitted") is not False
                or task.get("training_authorized") is not False
                or task.get("split") is not None
                or task.get("world_component_id") is not None):
            raise ValueError("PACKET_CARD_OR_REVIEW_STATE_INVALID")
        story = task.get("story_uuid")
        if not isinstance(story, str) or not story:
            raise ValueError("PACKET_WORLD_ID_INVALID")
        history = messages[1:-1]
        if any(m["role"] == "system" for m in history):
            raise ValueError("PACKET_HISTORY_SYSTEM_INVALID")
        if any(history[i]["role"] == history[i - 1]["role"] for i in range(1, len(history))):
            raise ValueError("PACKET_HISTORY_ROLE_INVALID")
        assistant_first = bool(history and history[0]["role"] == "assistant")
        if task.get("source_history_starts_with_assistant") is not assistant_first:
            raise ValueError("PACKET_HISTORY_START_INVALID")
        cohort = "gold108" if reason == GOLD108_REASON else "gold87"
        instructions = task.get("review_instructions")
        expected_dimensions = {
            "chinese_prose", "character_consistency", "npc_initiative",
            "player_agency", "rule_fidelity", "narrative_continuity",
        }
        if (not isinstance(instructions, dict)
                or set(instructions.get("dimensions", {})) != expected_dimensions
                or set(instructions.get("dimension_floors", {})) != expected_dimensions
                or instructions.get("two_independent_blinded_reviews_required") is not True
                or instructions.get("source_world_card_is_unapproved") is not True):
            raise ValueError("PACKET_REVIEW_RUBRIC_INVALID")
        legacy_state = (
            "GOLD108_BASIC_HISTORICAL_EVIDENCE_BOUND__NEW_CONTEXT_REVIEW_REQUIRED"
            if cohort == "gold108"
            else "GOLD87_INDEX_DOUBLE_ACCEPT_ONLY__ORIGINAL_A_B_EVIDENCE_UNBOUND"
        )
        group = worlds.get(story)
        if group is None:
            group = {
                "schema": OUT_SCHEMA,
                "status": "PRIVATE_STORY_REVIEW_PACKET_NOT_REVIEWED",
                "story_uuid": story,
                "world_card": card,
                "world_card_sha256": card_hash,
                "world_card_source_kind": CARD_SOURCE,
                "world_card_approved_for_system": False,
                "world_card_review_status": "UNREVIEWED",
                "review_protocol": task.get("review_instructions"),
                "review_protocol_addendum": {
                    "card_is_export_snapshot_not_historical_request": True,
                    "do_not_assume_card_was_available_at_target_time": True,
                    "review_each_target_against_visible_history_and_card": True,
                    "preserve_leading_assistant_context_without_silent_deletion": True,
                    "world_card_approval_is_separate_from_sample_quality": True,
                },
                "cases": [],
            }
            worlds[story] = group
        elif group["world_card_sha256"] != card_hash:
            raise ValueError("PACKET_WORLD_CARD_CONFLICT")
        case = {
            "case_id": case_id,
            "cohort": cohort,
            "legacy_evidence_state": legacy_state,
            "priority": "P1_ASSISTANT_FIRST_CONTEXT" if assistant_first else "P2_USER_FIRST_CONTEXT",
            "history_starts_with_assistant": assistant_first,
            "history": history,
            "current_user_text": messages[-1]["content"],
            "target_assistant_text": target,
            "target_sha256": task["target_sha256"],
            "review_status": "UNREVIEWED",
            "review_focus": (
                [
                    "Determine whether the leading Assistant message has a grounded antecedent",
                    "Check whether the target relies on facts absent from the visible history or card",
                    "Check player agency and whether the response invents player intent",
                    "Do not delete, rewrite, or silently reclassify the leading Assistant message",
                ] if assistant_first else [
                    "Check target against current User input, visible history, and unapproved card",
                    "Check character relationships, hard rules, chronology, and player agency",
                ]
            ),
        }
        group["cases"].append(case)
        counts[cohort + "_cases"] += 1
        counts[cohort + ("_assistant_first" if assistant_first else "_user_first")] += 1
        counts["assistant_first_cases" if assistant_first else "user_first_cases"] += 1

    if len(seen) != 195 or counts["excluded_world_identity_unresolved"] != 3:
        raise ValueError("PACKET_FINAL_COUNTS_INVALID")
    if counts["gold108_cases"] != 105 or counts["gold87_cases"] != 87:
        raise ValueError("PACKET_COHORT_COUNTS_INVALID")
    if counts["assistant_first_cases"] != 132 or counts["user_first_cases"] != 60:
        raise ValueError("PACKET_HISTORY_COUNTS_INVALID")
    if len(worlds) != 13:
        raise ValueError("PACKET_WORLD_COUNTS_INVALID")
    packets = list(worlds.values())
    for packet in packets:
        packet["cases"].sort(key=lambda x: (x["priority"], x["cohort"], x["case_id"]))
        packet["case_count"] = len(packet["cases"])
        packet["assistant_first_case_count"] = sum(
            c["history_starts_with_assistant"] for c in packet["cases"]
        )
        packet["user_first_case_count"] = packet["case_count"] - packet["assistant_first_case_count"]
        packet["gold87_case_count"] = sum(c["cohort"] == "gold87" for c in packet["cases"])
        packet["gold108_case_count"] = sum(c["cohort"] == "gold108" for c in packet["cases"])
    receipt = {
        "schema": "r58_gold192_story_packet_build_safe_v1",
        "status": "GOLD192_STORY_PACKETS_READY__SEMANTIC_REVIEW_PENDING",
        "candidate_cases": 192,
        "excluded_world_identity_unresolved": 3,
        "story_packets": len(packets),
        "gold87_cases": counts["gold87_cases"],
        "gold108_cases": counts["gold108_cases"],
        "assistant_first_cases": counts["assistant_first_cases"],
        "user_first_cases": counts["user_first_cases"],
        "world_card_conflicts": 0,
        "world_card_approved_for_system": False,
        "semantic_reviews_completed": 0,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
        "private_packet_written": False,
    }
    return receipt, packets


def write_private(path, repo_root, packets):
    root = repo_root.resolve()
    parent = path.parent.resolve()
    if (not path.is_absolute() or path.exists() or path.is_symlink()
            or not path.parent.is_dir() or path.parent.is_symlink()
            or stat.S_IMODE(path.parent.stat().st_mode) & 0o077
            or root == parent or root in parent.parents):
        raise ValueError("PACKET_PRIVATE_OUTPUT_INVALID")
    payload = b"".join(canonical(packet) + b"\n" for packet in packets)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-tasks", type=Path, required=True)
    parser.add_argument("--private-queue", type=Path, required=True)
    parser.add_argument("--private-scope", type=Path, required=True)
    parser.add_argument("--private-output", type=Path)
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        files = [private_file(x, root) for x in (
            args.private_tasks, args.private_queue, args.private_scope
        )]
        if len({f.resolve() for f in files}) != 3:
            raise ValueError("PACKET_INPUT_FILES_NOT_DISTINCT")
        receipt, packets = build_packets(*files)
        if args.private_output:
            write_private(args.private_output, root, packets)
            receipt["private_packet_written"] = True
            receipt["status"] = "GOLD192_PRIVATE_STORY_PACKETS_WRITTEN__SEMANTIC_REVIEW_PENDING"
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        allowed = {
            "PACKET_INPUT_FILES_NOT_DISTINCT", "PACKET_INPUT_COUNTS_INVALID",
            "PACKET_TASK_SCHEMA_INVALID", "PACKET_CASE_ID_INVALID",
            "PACKET_SCOPE_BINDING_INVALID", "PACKET_EXCLUSION_REASON_INVALID",
            "PACKET_CANDIDATE_STATE_INVALID", "PACKET_MESSAGE_SHAPE_INVALID",
            "PACKET_INPUT_HASH_INVALID", "PACKET_TARGET_HASH_INVALID",
            "PACKET_CARD_JSON_INVALID", "PACKET_CARD_OR_REVIEW_STATE_INVALID", "PACKET_REVIEW_RUBRIC_INVALID",
            "PACKET_WORLD_ID_INVALID", "PACKET_HISTORY_SYSTEM_INVALID",
            "PACKET_HISTORY_ROLE_INVALID", "PACKET_HISTORY_START_INVALID",
            "PACKET_WORLD_CARD_CONFLICT", "PACKET_FINAL_COUNTS_INVALID",
            "PACKET_COHORT_COUNTS_INVALID", "PACKET_HISTORY_COUNTS_INVALID",
            "PACKET_WORLD_COUNTS_INVALID", "PACKET_PRIVATE_OUTPUT_INVALID",
            "TRIAGE_NOT_READY",
        }
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) in allowed else safe_reason(exc)
        receipt = {
            "schema": "r58_gold192_story_packet_build_safe_v1",
            "status": "GOLD192_STORY_PACKET_BUILD_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "private_values_emitted": False,
            "private_packet_written": False,
        }
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 42
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
