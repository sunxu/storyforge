#!/usr/bin/env python3
"""R58 owner-local private request timeline correlation (aggregate only).

Read the frozen three targets, query only a bounded terminal-event window and
join request events to latency metrics by exact request_id in PostgreSQL.
Never print private IDs, SQL, timestamps, model, story content or credentials.
NO exact target->request foreign key exists in the extracted evidence.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from capture_priority3 import Hold, MAX_INPUT_BYTES, read_time
from verify_priority3_private import read_private_file, verify

COHORTS = {"AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"}
HOST = "aws-1-ap-southeast-1.pooler.supabase.com"
USER = "r58_export_reader.cckbpebhzmyasmttnfwp"
FIELDS = (
    "target_found", "target_created_matches",
    "terminal_events_in_window", "events_with_matching_metric",
    "events_with_one_metric", "timing_compatible_joined_events",
    "missing_duration_events", "excess_candidates",
    "events_with_history11_metric", "events_near_target_ledger_update",
    "events_with_both_soft_signals",
)


def fixed_targets(folder: Path) -> list[dict]:
    if verify(folder)["case_fingerprints_verified"] != 12:
        raise Hold("private manifest integrity HOLD")
    raw = read_private_file(folder / "source.private.jsonl", MAX_INPUT_BYTES)
    source = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(source) != 3:
        raise Hold("expected three frozen targets")
    targets = []
    for row in source:
        case = row["case"]
        try:
            target_id = str(uuid.UUID(case["target_message_id"]))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise Hold("invalid target UUID") from exc
        read_time(case["target_created_at"], "target")
        targets.append({
            "cohort": case["cohort"],
            "target_id": target_id,
            "story": case["story_id"],
            "session": case["session_id"],
            "target_time": case["target_created_at"],
        })
    if len({t["target_id"] for t in targets}) != 3:
        raise Hold("target ID uniqueness violation")
    if {t["cohort"] for t in targets} != COHORTS:
        raise Hold("unexpected frozen cohorts")
    return targets


def query_sql(targets: list[dict]) -> str:
    # Private target identifiers travel only through local psql stdin.
    blob = json.dumps(targets, separators=(",", ":"), ensure_ascii=True)
    blob = blob.replace("'", "''")
    return """BEGIN READ ONLY;
WITH sealed AS (
 SELECT * FROM jsonb_to_recordset('""" + blob + """'::jsonb)
 AS x(cohort text,target_id uuid,story text,session text,target_time timestamptz)
), anchored AS (
 SELECT s.*, m.user_id,
        (m.id IS NOT NULL) AS target_found,
        COALESCE(m.created_at=s.target_time,false) AS time_matches
 FROM sealed s
 LEFT JOIN public.v2_chat_messages m
   ON m.id=s.target_id AND m.story_id=s.story
   AND m.session_id=s.session AND m.role='assistant'
), per_target AS (
 SELECT a.cohort,a.target_found,a.time_matches,
        q.candidate_count,q.metric_matched,q.one_metric,
        q.time_compatible,q.missing_duration,q.excess_candidates,
        q.history11_count,q.near_update_count,q.both_count
 FROM anchored a
 LEFT JOIN LATERAL (
   SELECT count(*)::int AS candidate_count,
          count(*) FILTER (WHERE c.metric_count>0)::int AS metric_matched,
          count(*) FILTER (WHERE c.metric_count=1)::int AS one_metric,
          count(*) FILTER (
            WHERE c.metric_count=1 AND c.duration_ms BETWEEN 0 AND 1200000
             AND a.target_time >= c.occurred_at
                  - (c.duration_ms * INTERVAL '1 millisecond') - INTERVAL '2 minutes'
             AND a.target_time <= c.occurred_at + INTERVAL '2 minutes'
          )::int AS time_compatible,
          count(*) FILTER (WHERE c.duration_ms IS NULL)::int AS missing_duration,
          count(*) FILTER (WHERE c.metric_count=1
                             AND c.metric_history11_count=1)::int AS history11_count,
          count(*) FILTER (WHERE c.metric_count=1
                             AND c.near_target_update)::int AS near_update_count,
          count(*) FILTER (WHERE c.metric_count=1
                             AND c.metric_history11_count=1
                             AND c.near_target_update
                             AND c.duration_ms BETWEEN 0 AND 1200000
                             AND a.target_time >= c.occurred_at
                               - (c.duration_ms * INTERVAL '1 millisecond')
                               - INTERVAL '2 minutes'
                             AND a.target_time <= c.occurred_at
                               + INTERVAL '2 minutes')::int AS both_count,
          (count(*)>100)::boolean AS excess_candidates
   FROM (
     SELECT ev.request_id,ev.occurred_at,ev.duration_ms,
            EXISTS (
              SELECT 1 FROM public.v2_chat_message_ledger led
              WHERE led.message_id=a.target_id AND led.story_id=a.story
                AND led.session_id=a.session
                AND led.operation='update_after'
                AND led.recorded_at BETWEEN ev.occurred_at - INTERVAL '2 minutes'
                                        AND ev.occurred_at + INTERVAL '2 minutes'
            ) AS near_target_update,
            (SELECT count(*)::int FROM public.chat_latency_metrics lm
              WHERE lm.request_id=ev.request_id AND lm.user_id=a.user_id
                AND lm.story_id=a.story AND lm.session_id=a.session
                AND lm.scene='v2-chat' AND lm.status=200
                AND lm.token_breakdown->>'historyMsgCount'='11'
            ) AS metric_history11_count,
            (SELECT count(*)::int FROM public.chat_latency_metrics lm
              WHERE lm.request_id=ev.request_id AND lm.user_id=a.user_id
                AND lm.story_id=a.story AND lm.session_id=a.session
                AND lm.scene='v2-chat' AND lm.status=200
            ) AS metric_count
     FROM public.v2_chat_request_events ev
     WHERE a.target_found AND ev.user_id=a.user_id
       AND ev.story_id=a.story AND ev.session_id=a.session
       AND ev.status=200
       AND ev.occurred_at BETWEEN
           a.target_time - INTERVAL '2 minutes'
           AND a.target_time + INTERVAL '20 minutes'
     ORDER BY ev.occurred_at, ev.request_id
     LIMIT 101
   ) c
 ) q ON true
)
SELECT jsonb_build_object(
 'role_correct',current_user='r58_export_reader',
 'transaction_read_only',current_setting('transaction_read_only'),
 'cases',(SELECT jsonb_agg(jsonb_build_object(
   'cohort',cohort,
   'target_found',target_found,
   'target_created_matches',time_matches,
   'terminal_events_in_window',candidate_count,
   'events_with_matching_metric',metric_matched,
   'events_with_one_metric',one_metric,
   'timing_compatible_joined_events',time_compatible,
   'missing_duration_events',missing_duration,
   'excess_candidates',excess_candidates,
   'events_with_history11_metric',history11_count,
   'events_near_target_ledger_update',near_update_count,
   'events_with_both_soft_signals',both_count
 ) ORDER BY cohort) FROM per_target)
)::text;
COMMIT;
"""


def project(response: object) -> dict:
    if not isinstance(response, dict) or response.get("role_correct") is not True:
        raise Hold("reader identity HOLD")
    if response.get("transaction_read_only") != "on":
        raise Hold("transaction isolation HOLD")
    cases = response.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        raise Hold("unexpected request timeline results")
    projected = []
    for case in cases:
        if not isinstance(case, dict) or case.get("cohort") not in COHORTS:
            raise Hold("unexpected case group")
        rec = {"cohort": case["cohort"]}
        for name in FIELDS:
            value = case.get(name)
            if name in ("target_found", "target_created_matches", "excess_candidates"):
                if type(value) is not bool:
                    raise Hold("invalid boolean aggregate")
            elif type(value) is not int or value < 0 or value > 101:
                raise Hold("invalid count aggregate")
            rec[name] = value
        if not (rec["timing_compatible_joined_events"]
                <= rec["events_with_one_metric"]
                <= rec["events_with_matching_metric"]
                <= rec["terminal_events_in_window"]):
            raise Hold("nonmonotonic request aggregate")
        if not (
            rec["events_with_both_soft_signals"]
            <= rec["timing_compatible_joined_events"]
            and rec["events_with_both_soft_signals"]
            <= rec["events_with_history11_metric"]
            <= rec["events_with_one_metric"]
            and rec["events_with_both_soft_signals"]
            <= rec["events_near_target_ledger_update"]
            <= rec["events_with_one_metric"]
        ):
            raise Hold("soft signal count inconsistency")
        projected.append(rec)
    if {c["cohort"] for c in projected} != COHORTS:
        raise Hold("cohort duplicate or missing")
    unique = all(
        c["target_found"] and c["target_created_matches"]
        and not c["excess_candidates"]
        and c["events_with_both_soft_signals"] == 1
        for c in projected
    )
    return {
        "status": ("R58_REQUEST_TIMELINE_SOFT_NARROWED_3_OF_3"
                   "__TARGET_REQUEST_LINK_HOLD"
                   if unique else "R58_REQUEST_TIMELINE_CORRELATION_HOLD"),
        "cases": sorted(projected, key=lambda x: x["cohort"]),
        "exact_request_id_join_between_logs": True,
        "exact_target_message_to_request_join": False,
        "history11_and_ledger_proximity": "SOFT_SIGNALS_ONLY_NOT_CAUSAL_PROOF",
        "request_start_time_certified": False,
        "provider_request_byte_exact": "HOLD",
        "training_admission": "HOLD",
    }


def audit(folder: Path) -> dict:
    targets = fixed_targets(folder)
    if os.getenv("PGHOST") != HOST or os.getenv("PGUSER") != USER:
        raise Hold("unexpected reader connection")
    if not os.getenv("PGPASSWORD"):
        raise Hold("missing private DB credential")
    env = os.environ.copy()
    env["PGOPTIONS"] = ("-c default_transaction_read_only=on"
                        " -c statement_timeout=90000 -c lock_timeout=1000")
    env["PGSSLMODE"] = "require"
    try:
        task = subprocess.run(
            ["psql", "-X", "-w", "-qAt", "-v", "ON_ERROR_STOP=1"],
            input=query_sql(targets), text=True, capture_output=True,
            timeout=115, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Hold("database read unavailable") from exc
    if task.returncode != 0:
        raise Hold("request timeline SELECT failed")
    lines = [line for line in task.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise Hold("unexpected query output")
    try:
        return project(json.loads(lines[0]))
    except (TypeError, ValueError) as exc:
        raise Hold("request timeline JSON invalid") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="R58 fixed-target request timeline probe")
    parser.add_argument("--private-dir", required=True, type=Path)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.plan_only:
            print(json.dumps({
                "status": "R58_REQUEST_TIMELINE_FIXED3_PLAN_PASS",
                "fixed_targets": len(fixed_targets(args.private_dir)),
                "db_queried": False, "training_admission": "HOLD",
            }, sort_keys=True))
        else:
            print(json.dumps(audit(args.private_dir), sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError):
        # Never log psql stderr, query payload, IDs, text or digests.
        print("R58_REQUEST_TIMELINE: HOLD (source, role or query guard)",
              file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
