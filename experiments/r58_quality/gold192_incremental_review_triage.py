"""Read-only Gold192 incremental review triage; no semantic judgments or training."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from gold192_scope_exclusion import inspect_scope
from legacy_gold_target_reuse import SCHEMA, canonical, private_file, safe_reason

TASKS_TOTAL = 195
SCOPED = 192
EXCLUDED = 3
STATUS_CANDIDATE = "CANDIDATE_ONLY_QUALITY_HOLD"
STATUS_EXCLUDED = "EXCLUDED_WORLD_ID_UNRESOLVED"
SCHEMA_OUT = "r58_gold192_incremental_review_triage_safe_v1"


def inspect(tasks_file, queue_file, scope_file):
    # Revalidate the already established 105 / 87 / 3 boundary on every run.
    preflight = inspect_scope(tasks_file, queue_file)
    if preflight["scoped_candidate_count"] != SCOPED:
        raise ValueError("TRIAGE_SCOPE_INVALID")
    with open(queue_file, encoding="utf-8") as stream:
        reasons = {}
        for line in stream:
            if line.strip():
                row = json.loads(line)
                case_id = row["case_id"]
                if case_id in reasons:
                    raise ValueError("TRIAGE_QUEUE_DUPLICATE")
                reasons[case_id] = row["reason_code"]
    with open(scope_file, encoding="utf-8") as stream:
        scope = {}
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            if (not isinstance(row, dict)
                    or set(row) != {"case_id", "scope_status", "quality_v1_admitted",
                                   "training_authorized"}
                    or row.get("quality_v1_admitted") is not False
                    or row.get("training_authorized") is not False
                    or row.get("scope_status") not in {STATUS_CANDIDATE, STATUS_EXCLUDED}
                    or not isinstance(row.get("case_id"), str)
                    or not row["case_id"] or row["case_id"] in scope):
                raise ValueError("TRIAGE_SCOPE_ROWS_INVALID")
            scope[row["case_id"]] = row["scope_status"]
    if len(scope) != TASKS_TOTAL or set(scope) != set(reasons):
        raise ValueError("TRIAGE_SCOPE_SET_MISMATCH")
    for key, reason in reasons.items():
        expected = STATUS_EXCLUDED if reason == "WORLD_OR_TARGET_IDENTITY_HOLD" else STATUS_CANDIDATE
        if scope[key] != expected:
            raise ValueError("TRIAGE_SCOPE_DECISION_MISMATCH")

    count = Counter()
    worlds = defaultdict(lambda: Counter())
    seen = set()
    with open(tasks_file, encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            cid = row["case_id"]
            if cid in seen or row.get("schema") != SCHEMA or cid not in scope:
                raise ValueError("TRIAGE_TASK_ID_INVALID")
            seen.add(cid)
            if scope[cid] == STATUS_EXCLUDED:
                count["excluded_world_identity_unresolved"] += 1
                continue
            if (row.get("quality_v1_admitted") is not False
                    or row.get("training_authorized") is not False
                    or row.get("review_status") != "UNREVIEWED"
                    or row.get("review_results") != []
                    or row.get("input_design_status") != "PROPOSED_OFFLINE_CARD_NOT_APPROVED"
                    or row.get("split") is not None
                    or row.get("world_component_id") is not None
                    or not isinstance(row.get("story_uuid"), str)
                    or not row["story_uuid"]
                    or not isinstance(row.get("target_text"), str)
                    or hashlib.sha256(row["target_text"].encode("utf-8")).hexdigest()
                    != row.get("target_sha256")
                    or not isinstance(row.get("messages"), list)
                    or hashlib.sha256(canonical(row["messages"])).hexdigest()
                    != row.get("input_messages_sha256")):
                raise ValueError("TRIAGE_TASK_CONTENT_INVALID")
            messages = row["messages"]
            if (len(messages) < 2
                    or messages[0].get("role") != "system"
                    or messages[-1].get("role") != "user"
                    or not all(
                        isinstance(item, dict)
                        and set(item) == {"role", "content"}
                        and item["role"] in {"system", "user", "assistant"}
                        and isinstance(item["content"], str)
                        and bool(item["content"].strip())
                        for item in messages
                    )):
                raise ValueError("TRIAGE_MESSAGE_SHAPE_INVALID")
            history = messages[1:-1]
            if any(item["role"] == "system" for item in history):
                raise ValueError("TRIAGE_HISTORY_SYSTEM_INVALID")
            if any(history[i]["role"] == history[i - 1]["role"] for i in range(1, len(history))):
                raise ValueError("TRIAGE_HISTORY_ROLE_INVALID")
            leading = bool(history and history[0]["role"] == "assistant")
            if row.get("source_history_starts_with_assistant") is not leading:
                raise ValueError("TRIAGE_LEADING_FLAG_INVALID")
            cohort = "gold108" if reasons[cid] == "CONTEXT_EQUIVALENCE_UNVERIFIED" else "gold87"
            count[cohort + "_candidates"] += 1
            count[cohort + ("_assistant_first" if leading else "_user_first")] += 1
            kind = row.get("card_source_kind")
            if not isinstance(kind, str) or not kind:
                raise ValueError("TRIAGE_CARD_SOURCE_INVALID")
            # Do not print arbitrary source kind from private task.
            count[cohort + "_card_source_recognized" if
                  kind == "EXPORT_TIME_SNAPSHOT_NOT_HISTORICAL_REQUEST"
                  else cohort + "_card_source_other_hold"] += 1
            worlds[row["story_uuid"]][cohort] += 1
            count["eligible_for_incremental_review_not_training"] += 1

    if len(seen) != TASKS_TOTAL or count["excluded_world_identity_unresolved"] != EXCLUDED:
        raise ValueError("TRIAGE_COUNT_INVALID")
    if count["gold108_candidates"] != 105 or count["gold87_candidates"] != 87:
        raise ValueError("TRIAGE_COHORT_COUNT_INVALID")
    cross_cohort = sum(bool(v["gold87"] and v["gold108"]) for v in worlds.values())
    return {
        "schema": SCHEMA_OUT,
        "status": "GOLD192_INCREMENTAL_REVIEW_ROUTING_READY__SEMANTIC_HOLD",
        "counts": dict(sorted(count.items())),
        "unique_story_uuids": len(worlds),
        "story_uuids_present_in_both_cohorts": cross_cohort,
        "history_context_equivalence_verified": False,
        "world_card_semantically_approved": False,
        "world_component_isolation_proven": False,
        "historical_exposure_decontaminated": False,
        "old_review_evidence_new_quality_v1": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-tasks", type=Path, required=True)
    p.add_argument("--private-queue", type=Path, required=True)
    p.add_argument("--private-scope", type=Path, required=True)
    args = p.parse_args()
    try:
        repo = args.repo_root.resolve()
        files = [private_file(x, repo) for x in (
            args.private_tasks, args.private_queue, args.private_scope
        )]
        if len({x.resolve() for x in files}) != 3:
            raise ValueError("TRIAGE_INPUT_FILES_NOT_DISTINCT")
        report = inspect(*files)
        status = 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        allowed = {
            "TRIAGE_SCOPE_INVALID", "TRIAGE_QUEUE_DUPLICATE",
            "TRIAGE_SCOPE_ROWS_INVALID", "TRIAGE_SCOPE_SET_MISMATCH",
            "TRIAGE_SCOPE_DECISION_MISMATCH", "TRIAGE_TASK_ID_INVALID",
            "TRIAGE_TASK_CONTENT_INVALID", "TRIAGE_MESSAGE_SHAPE_INVALID",
            "TRIAGE_HISTORY_SYSTEM_INVALID", "TRIAGE_HISTORY_ROLE_INVALID",
            "TRIAGE_LEADING_FLAG_INVALID", "TRIAGE_CARD_SOURCE_INVALID",
            "TRIAGE_COUNT_INVALID", "TRIAGE_COHORT_COUNT_INVALID",
            "TRIAGE_INPUT_FILES_NOT_DISTINCT",
        }
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) in allowed else safe_reason(exc)
        report = {
            "schema": SCHEMA_OUT, "status": "GOLD192_TRIAGE_INVALID__HOLD",
            "reason_code": reason, "quality_v1_admitted": 0,
            "training_authorized": False, "private_values_emitted": False,
        }
        status = 42
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
