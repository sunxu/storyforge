"""R60 CPU-only readiness comparison for recovered persisted history windows.

No System, target text, candidate ID or private history is emitted. This is not
Qwen tokenizer preflight, not an actual-sent request reconstruction, and not SFT
admission. Uses an existing create-only Owner private recovery manifest.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import r60_real_private_batch as private

SCHEMA = "storyforge_r60_history_window_safe_v1"
INPUT_SCHEMA = "storyforge_r60_qd20_common2_supabase_recovery_private_v1"
INPUT_STATUS = "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT"
FILENAME = "R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json"
WINDOWS = (6, 12, 24, 48)
MAX_BYTES = 8_000_000


class Hold(ValueError):
    pass


def assess(data: dict) -> dict:
    if (
        not isinstance(data, dict)
        or data.get("schema") != INPUT_SCHEMA
        or data.get("status") != INPUT_STATUS
        or data.get("train_admitted") != 0
        or not isinstance(data.get("cases"), list)
        or len(data["cases"]) != 2
    ):
        raise Hold("RECOVERY_MANIFEST_HOLD")
    counts: list[int] = []
    summaries: dict[str, dict] = {}
    for size in WINDOWS:
        summaries[str(size)] = {
            "window_size": size, "last_three_preserved_count": 0,
            "window_starts_with_user_count": 0,
            "message_counts": [], "content_chars": [],
        }
    for case in data["cases"]:
        if not isinstance(case, dict):
            raise Hold("CASE_FORMAT_HOLD")
        if (
            case.get("last_three_exact_source_match") is not True
            or case.get("actual_sent_prompt_verified") is not False
            or case.get("historical_system_verified") is not False
            or case.get("historical_world_components_verified") is not False
            or case.get("r50_full_exclusion_verified") is not False
        ):
            raise Hold("EVIDENCE_FLAGS_HOLD")
        messages = case.get("history_messages")
        n = case.get("message_count_before_target")
        if (type(n) is not int or n < 3 or n > 500
                or not isinstance(messages, list) or len(messages) != n):
            raise Hold("HISTORY_COUNT_HOLD")
        ids = set()
        prev_turn = None
        for m in messages:
            if not isinstance(m, dict):
                raise Hold("MESSAGE_SHAPE_HOLD")
            if (not isinstance(m.get("id"), str) or not m["id"]
                    or m["id"] in ids or m.get("role") not in ("user", "assistant")
                    or not isinstance(m.get("content"), str) or not m["content"]
                    or type(m.get("turn_index")) is not int):
                raise Hold("MESSAGE_SOURCE_HOLD")
            ids.add(m["id"])
            turn = m["turn_index"]
            if prev_turn is not None and turn <= prev_turn:
                raise Hold("MESSAGE_TURN_ORDER_HOLD")
            prev_turn = turn
        if [m["role"] for m in messages[-3:]] != ["user", "assistant", "user"]:
            raise Hold("LAST_THREE_ROLE_HOLD")
        counts.append(n)
        for size in WINDOWS:
            chosen = messages[-size:]
            result = summaries[str(size)]
            result["last_three_preserved_count"] += (
                [m["id"] for m in chosen[-3:]] ==
                [m["id"] for m in messages[-3:]]
            )
            result["window_starts_with_user_count"] += chosen[0]["role"] == "user"
            result["message_counts"].append(len(chosen))
            result["content_chars"].append(sum(len(m["content"]) for m in chosen))
    for result in summaries.values():
        for key in ("message_counts", "content_chars"):
            values = result.pop(key)
            result[f"{key}_min"] = min(values)
            result[f"{key}_max"] = max(values)
    return {
        "schema": SCHEMA,
        "status": "SOURCE_BOUND_PERSISTED_HISTORY_WINDOWS_ASSESSED__TRAIN_HOLD",
        "candidate_count": 2,
        "full_history_message_counts": sorted(counts),
        "windows": summaries,
        "source_context_kind": "PERSISTED_HISTORY_NOT_ACTUALLY_SENT",
        "actual_sent_prompt_verified": False,
        "historical_system_verified": False,
        "historical_world_components_verified": False,
        "r50_complete_exclusion_verified": False,
        "tokenizer_verified": False,
        "quality_v1_admitted": 0, "train_admitted": 0,
        "database_accessed": False, "database_modified": False,
        "model_inference_calls": 0, "gpu_job_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        private.private_dir(args.recovery_dir, create=False)
        raw = private.read_private(args.recovery_dir / FILENAME, MAX_BYTES)
        result = assess(json.loads(raw))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never output private content or source IDs
        reason = str(exc) if isinstance(exc, Hold) else "WINDOW_PREFLIGHT_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "SOURCE_BOUND_HISTORY_WINDOWS_HOLD",
            "reason_code": reason, "train_admitted": 0, "quality_v1_admitted": 0,
            "database_accessed": False, "model_inference_calls": 0,
            "gpu_job_started": False, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
