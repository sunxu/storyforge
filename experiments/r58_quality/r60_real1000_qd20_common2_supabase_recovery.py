"""Owner Mac only: read-only Supabase history recovery for two common-PASS cases.

The original R60 extraction kept exactly three preceding messages. This tool
uses the frozen two-candidate binding to recover preceding completed messages
from V2 DB, without treating current story fields as historical prompt facts.
Private output is create-only 0600. No API inference, training, or DB mutation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import r60_real1000_pilot20_local_review as pilot
import r60_real1000_qd20_common2_context_cpu as context
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_qd20_common2_supabase_recovery_safe_v1"
PRIVATE_SCHEMA = "storyforge_r60_qd20_common2_supabase_recovery_private_v1"
FILENAME = "R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json"
MAX_HISTORY = 500


class Hold(ValueError):
    pass


def select_sources(cases: list[dict], packets: list[dict],
                   blind: dict) -> list[dict]:
    if len(cases) != 1000 or len(packets) != 20 or len(blind["cases"]) != 2:
        raise Hold("FROZEN_SELECTION_HOLD")
    result = []
    for item in blind["cases"]:
        matches = [
            p for p in packets
            if (p["history_messages"] == item["history_messages"]
                and p["assistant_target"] == item["assistant_target"])
        ]
        if len(matches) != 1:
            raise Hold("PILOT_BINDING_HOLD")
        p = matches[0]
        i = p["sample100_position"]
        if type(i) is not int or not 1 <= i <= 1000:
            raise Hold("SOURCE_POSITION_HOLD")
        c = cases[i - 1]
        if (c.get("history_messages") != item["history_messages"]
                or c.get("target_text") != item["assistant_target"]):
            raise Hold("SOURCE_TEXT_BINDING_HOLD")
        src = c["source"]
        if not all(isinstance(src.get(key), str) and src[key] for key in (
                "story_id", "session_id", "assistant_message_id",
                "prior_user_message_id", "previous_assistant_message_id",
                "previous_user_message_id")):
            raise Hold("SOURCE_IDS_HOLD")
        result.append(c)
    if len({c["source"]["assistant_message_id"] for c in result}) != 2:
        raise Hold("DUPLICATE_TARGET_HOLD")
    return result


def validate_history(case: dict, rows: list[tuple]) -> dict:
    """DB history rows are DESC by turn, created_at, id; verify last 3 exactly."""
    if len(rows) > MAX_HISTORY:
        # Never silently call a capped transcript complete.
        raise Hold("HISTORY_OVER_LIMIT_HOLD")
    if not rows:
        raise Hold("HISTORY_MISSING_HOLD")
    src = case["source"]
    history = list(reversed(rows))
    seen = set()
    for id_, role, content, turn, created in history:
        if (not isinstance(id_, str) or id_ in seen
                or role not in ("user", "assistant")
                or not isinstance(content, str) or not content
                or type(turn) is not int):
            raise Hold("HISTORY_ROW_HOLD")
        seen.add(id_)
    expected_ids = [
        src["previous_user_message_id"],
        src["previous_assistant_message_id"],
        src["prior_user_message_id"],
    ]
    if (len(history) < 3
            or [x[0] for x in history[-3:]] != expected_ids
            or [x[1] for x in history[-3:]] !=
            ["user", "assistant", "user"]
            or [x[2] for x in history[-3:]] !=
            [m["content"] for m in case["history_messages"]]):
        raise Hold("HISTORICAL_THREE_MESSAGES_MISMATCH_HOLD")
    if any(history[i][3] > history[i + 1][3]
           for i in range(len(history) - 1)):
        raise Hold("HISTORY_TURN_ORDER_HOLD")
    return {
        "history_messages": [{
            "id": id_, "role": role, "content": content,
            "turn_index": turn, "created_at": str(created),
        } for id_, role, content, turn, created in history],
        "message_count_before_target": len(history),
        "last_three_exact_source_match": True,
        "history_scope": "ALL_PERSISTED_COMPLETED_PRE_TARGET_WITHIN_LIMIT",
        "actual_sent_prompt_verified": False,
    }


def read_one(cur, case: dict) -> dict:
    src = case["source"]
    story, session, target = (
        src["story_id"], src["session_id"], src["assistant_message_id"])
    cur.execute("""
        SELECT id::text, role, content, turn_index, created_at
        FROM public.v2_chat_messages
        WHERE id=%s::uuid AND story_id=%s AND session_id=%s
          AND role='assistant' AND status='completed'
    """, (target, story, session))
    row = cur.fetchone()
    if (row is None or row[2] != case["target_text"]
            or row[3] != src["assistant_turn_index"]):
        raise Hold("TARGET_DB_BINDING_HOLD")
    target_created = row[4]
    cur.execute("""
        SELECT id::text, role, content, turn_index, created_at
        FROM public.v2_chat_messages
        WHERE story_id=%s AND session_id=%s
          AND turn_index < %s AND status='completed'
          AND role IN ('user','assistant')
          AND created_at <= %s
        ORDER BY turn_index DESC, created_at DESC, id DESC
        LIMIT %s
    """, (story, session, row[3], target_created, MAX_HISTORY + 1))
    data = validate_history(case, cur.fetchall())
    # Current story settings may have changed since target response.
    cur.execute("""
        SELECT version, updated_at,
               NULLIF(BTRIM(initial_system_prompt),'') IS NOT NULL,
               NULLIF(BTRIM(world_setting),'') IS NOT NULL
        FROM public.user_stories WHERE id=%s
    """, (story,))
    story_row = cur.fetchone()
    cur.execute("""
        SELECT count(*) FROM public.v2_session_checkpoints
        WHERE story_id=%s AND session_id=%s AND turn_index <= %s
          AND created_at <= %s
    """, (story, session, row[3], target_created))
    checkpoints = cur.fetchone()[0]
    return {
        "story_id": story, "session_id": session,
        "assistant_message_id": target,
        "target_created_at": str(target_created),
        "target_turn_index": row[3],
        **data,
        "prior_checkpoint_count": checkpoints,
        "current_story_record_exists": story_row is not None,
        "current_story_version": story_row[0] if story_row else None,
        "current_story_updated_at": str(story_row[1]) if story_row else None,
        "current_story_has_system_field": bool(story_row[2]) if story_row else False,
        "current_story_has_world_field": bool(story_row[3]) if story_row else False,
        "historical_system_verified": False,
        "historical_world_components_verified": False,
        "r50_full_exclusion_verified": False,
    }


def recover(dsn: str, source_cases: list[dict]) -> list[dict]:
    import psycopg

    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as db:
        try:
            with db.cursor() as cur:
                cur.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("SET LOCAL statement_timeout='30000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("""
                    SELECT current_user,
                           current_setting('transaction_read_only'),
                           current_setting('row_security'),
                           r.rolbypassrls, r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                """)
                private.assert_guard(cur.fetchone())
                return [read_one(cur, c) for c in source_cases]
        finally:
            db.rollback()


def run(args: argparse.Namespace) -> dict:
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    # Validate local evidence BEFORE any DB access.
    baseline_args = argparse.Namespace(**vars(args))
    baseline_args.output_dir = args.blind_dir
    baseline = context.run(baseline_args)
    if baseline["candidate_count"] != 2 or baseline["strict_independent_pass"] != 2:
        raise Hold("BASELINE_CONTEXT_HOLD")
    pool, _ = quality.frozen_pool(args.expand_dir)
    _cfg, packets, _ = pilot.get_state(args.review_dir)
    private.private_dir(args.blind_dir, create=False)
    # read securely as already checked in context.run
    blind = json.loads(private.read_private(
        args.blind_dir / "R60_QD20_COMMON2_BLIND_PRIVATE.json", 200000))
    source_cases = select_sources(pool, packets["packets"], blind)
    dsn = os.getenv("R60_SUPABASE_READONLY_DSN", "")
    if not dsn:
        raise Hold("READONLY_DSN_MISSING_HOLD")
    recovered = recover(dsn, source_cases)
    if len(recovered) != 2:
        raise Hold("RECOVERY_COUNT_HOLD")
    manifest = {
        "schema": PRIVATE_SCHEMA,
        "status": "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT",
        "source": "SUPABASE_READ_ONLY_V2_PERSISTED_MESSAGES",
        "cases": recovered,
        "train_admitted": 0,
    }
    private.private_dir(args.output_dir, create=True)
    private.write_new(args.output_dir / FILENAME, pilot.canonical(manifest))
    return {
        "schema": SCHEMA,
        "status": "QD20_COMMON2_PERSISTED_HISTORY_RECOVERED__TRAIN_CONTEXT_HOLD",
        "candidate_count": 2,
        "history_message_count_by_case": sorted(
            x["message_count_before_target"] for x in recovered),
        "last_three_exact_match_count": 2,
        "current_story_system_present_count": sum(
            x["current_story_has_system_field"] for x in recovered),
        "current_story_world_present_count": sum(
            x["current_story_has_world_field"] for x in recovered),
        "prior_checkpoint_count_total": sum(
            x["prior_checkpoint_count"] for x in recovered),
        "actual_sent_system_verified_count": 0,
        "historical_world_components_verified_count": 0,
        "r50_complete_exclusion_verified": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "database_accessed": True,
        "database_modified": False,
        "model_inference_calls": 0,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expand-dir", type=Path, required=True)
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--review-dir", type=Path, required=True)
    p.add_argument("--s1-blind-dir", type=Path, required=True)
    p.add_argument("--owner-map-dir", type=Path, required=True)
    p.add_argument("--codex-result", type=Path, required=True)
    p.add_argument("--live-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--blind-dir", type=Path, required=True)
    p.add_argument("--decisions", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never output DB text/IDs/DSN
        reason = str(exc) if isinstance(exc, Hold) else "DB_HISTORY_RECOVERY_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA, "status": "QD20_COMMON2_DB_RECOVERY_HOLD",
            "reason_code": reason, "quality_v1_admitted": 0,
            "train_admitted": 0, "database_modified": False,
            "model_inference_calls": 0, "gpu_job_started": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
