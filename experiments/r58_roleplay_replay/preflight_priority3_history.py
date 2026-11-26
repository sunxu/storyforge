#!/usr/bin/env python3
"""R58 private-source structural preflight.

Read the immutable Priority3 source bundle only. Do not access Supabase, R50,
model providers, or HF. No private text, IDs, hashes, or raw input are printed.
This is a conditional replay against a SOURCE PIN, not deployed-runtime proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from capture_priority3 import Hold, MAX_INPUT_BYTES
from verify_priority3_private import read_private_file, verify

ROLEPLAY_PIN = "e9fe29c42434caeb0bac5acc91845ab4741ecb2b"
EXPECTED_ROUTES = {"AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"}
PRUNE_MIN_KEEP_MESSAGES = 12
PRUNE_MAX_KEEP_MESSAGES = 12


def derive_case(row: dict) -> dict:
    case = row["case"]
    history = row["history24"]
    checkpoint = row["prior_checkpoint"]["snapshot"]
    target = row["target"]
    cohort = case["cohort"]

    if not isinstance(checkpoint, dict):
        raise Hold("checkpoint snapshot missing")
    # RolePlay source pin: route.ts pruneHistoryBySummary + summary-history-window.ts.
    # This is a *conditional* simulation: production request flags and previous
    # async memory/summary writes have not been recovered.
    summary_turn = checkpoint.get("last_summary_turn")
    if type(summary_turn) is not int or summary_turn < 0:
        raise Hold("historical summary cursor missing or invalid")
    recent = history[-24:]
    if len(recent) != 24:
        raise Hold("bounded source history must be 24")
    roles = [m["role"] for m in recent]
    if len(recent) <= PRUNE_MIN_KEEP_MESSAGES or summary_turn == 0:
        window = recent[:]
    else:
        covered = summary_turn * 2
        uncovered = max(0, len(recent) - covered)
        keep = min(max(uncovered, PRUNE_MIN_KEEP_MESSAGES),
                   PRUNE_MAX_KEEP_MESSAGES, len(recent))
        window = recent[-keep:]
        first_user = next((i for i, msg in enumerate(window)
                           if msg["role"] == "user"), None)
        window = window[first_user:] if first_user is not None else []

    last12 = recent[-12:]
    roles12 = [msg["role"] for msg in last12]
    strictly_alternating = all(roles12[i] != roles12[i-1]
                               for i in range(1, len(roles12)))
    structure_11 = (
        summary_turn > 0 and len(window) == 11
        and len(last12) == 12
        and all(msg["status"] == "completed" for msg in last12)
        and roles12[0] == "assistant" and roles12[1] == "user"
        and roles12[-1] == "user" and strictly_alternating
    )

    meta = target.get("metadata") or {}
    if not isinstance(meta, dict):
        raise Hold("target metadata malformed")
    preceding_assistants = [msg for msg in recent if msg["role"] == "assistant"]
    prev_meta = ((preceding_assistants[-1].get("metadata") or {})
                 if preceding_assistants else {})
    if not isinstance(prev_meta, dict):
        raise Hold("prior assistant metadata malformed")
    before = meta.get("v2EventRuntimeBefore")
    after = prev_meta.get("v2EventRuntimeAfter")
    if before is None:
        event_chain = "NOT_PRESENT"
    elif after is not None and before == after:
        event_chain = "JSONB_STRUCTURAL_EQUIVALENCE"
    else:
        event_chain = "HOLD_MISSING_OR_MISMATCH"

    metric = row.get("untrusted_nearby_metric") or {}
    if not isinstance(metric, dict):
        raise Hold("nearby metric malformed")
    nearby_count = metric.get("history_msg_count")
    near_count_11 = str(nearby_count) == "11"
    user_continue_count = sum(
        1 for msg in window
        if msg["role"] == "user"
        and isinstance(msg.get("metadata"), dict)
        and msg["metadata"].get("type") == "continue"
    )
    assistant_structured_maybe = sum(
        1 for msg in window
        if msg["role"] == "assistant" and "<" in msg["content"]
    )
    source_revision_count = sum(
        1 for msg in window
        if isinstance(msg.get("mutation_revision"), int)
        and msg["mutation_revision"] > 0
    )
    # Treat this as a diagnostic, not a byte-perfect LLM history.
    return {
        "cohort": cohort,
        "checkpoint_summary_present": summary_turn > 0,
        "source_last24_completed": all(m["status"] == "completed" for m in recent),
        "conditional_window_count": len(window),
        "eleven_message_structure": "PASS" if structure_11 else "HOLD",
        "nearby_metric_count_11": near_count_11,
        "event_previous_after_to_target_before": event_chain,
        "continue_row_in_conditional_window": user_continue_count > 0,
        "assistant_structured_scrub_may_apply": assistant_structured_maybe > 0,
        "mutated_rows_in_conditional_window": source_revision_count,
        "risk_remaining": [
            "HISTORICAL_DEPLOY_COMMIT_UNKNOWN",
            "REQUEST_RESUME_REGENERATE_CONTINUE_FLAGS_UNKNOWN",
            "DYNAMIC_SUMMARY_AND_RAG_AT_REQUEST_TIME_UNKNOWN",
            "POLICY_REPEAT_DEGENERATE_SCRUB_NOT_REPLAYED",
            "LOCALE_MODEL_AND_LAST_USER_INJECTION_UNKNOWN",
            "PROVIDER_REQUEST_BYTES_UNKNOWN",
            "NEARBY_LATENCY_METRIC_NOT_REQUEST_ID_JOINED",
        ],
    }


def preflight(folder: Path) -> dict:
    integrity = verify(folder)
    if integrity.get("case_fingerprints_verified") != 12:
        raise Hold("private source integrity precondition not met")
    raw = read_private_file(folder / "source.private.jsonl", MAX_INPUT_BYTES)
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError) as exc:
        raise Hold("malformed private JSONL") from exc
    cases = [derive_case(row) for row in rows]
    if {item["cohort"] for item in cases} != EXPECTED_ROUTES or len(cases) != 3:
        raise Hold("unexpected source routes")
    structure_ok = sum(x["eleven_message_structure"] == "PASS" for x in cases)
    metric_ok = sum(x["nearby_metric_count_11"] for x in cases)
    event_chain_ok = sum(x["event_previous_after_to_target_before"]
                         == "JSONB_STRUCTURAL_EQUIVALENCE" for x in cases)
    event_chain_missing = sum(x["event_previous_after_to_target_before"]
                              == "NOT_PRESENT" for x in cases)
    event_chain_hold = sum(x["event_previous_after_to_target_before"]
                           == "HOLD_MISSING_OR_MISMATCH" for x in cases)
    return {
        "status": (
            "R58_CONDITIONAL_HISTORY_WINDOW_STRUCTURE_PASS__RUNTIME_REPLAY_HOLD"
            if structure_ok == 3 and metric_ok == 3 and event_chain_hold == 0
            else "R58_HISTORY_STRUCTURE_OR_EVENT_CHAIN_HOLD"
        ),
        "source_pin_examined": ROLEPLAY_PIN,
        "source_file_and_case_fingerprints": "PASS",
        "cases": sorted(cases, key=lambda item: item["cohort"]),
        "source_11_message_structure_pass": structure_ok,
        "nearby_metric_count_11": metric_ok,
        "event_chain_direct_match": event_chain_ok,
        "event_chain_metadata_absent": event_chain_missing,
        "event_chain_holds": event_chain_hold,
        "actual_runtime_history_bytes_verified": False,
        "actual_runtime_prompt_bytes_verified": False,
        "private_source_was_modified": False,
        "training_admission": "HOLD",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="R58 source-only preflight, safe output.")
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(preflight(args.private_dir), ensure_ascii=False, sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError):
        print("R58_CONDITIONAL_HISTORY_PREFLIGHT: HOLD (private source or metadata issue)",
              file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
