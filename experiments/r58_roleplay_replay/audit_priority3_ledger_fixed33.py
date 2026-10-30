#!/usr/bin/env python3
"""R58 private-owner-only: fixed 33-message, read-only Ledger aggregate.
Uses sealed local source; prints only cohort counters. Never prints SQL,
private UUIDs, text, digests or DB error output. No source modification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from capture_priority3 import Hold, MAX_INPUT_BYTES
from preflight_priority3_history import derive_case
from verify_priority3_private import read_private_file, verify

COHORTS = {"AUTHOR", "CURRENT_PUBLIC", "OLD_PUBLIC"}
DB_HOSTS = {"aws-1-ap-southeast-1.pooler.supabase.com",
            "db.cckbpebhzmyasmttnfwp.supabase.co"}
DB_USERS = {"r58_export_reader", "r58_export_reader.cckbpebhzmyasmttnfwp"}


def fixed_rows(folder):
    if verify(folder)["case_fingerprints_verified"] != 12:
        raise Hold("source integrity HOLD")
    raw = read_private_file(folder / "source.private.jsonl", MAX_INPUT_BYTES)
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    selected = []
    for row in rows:
        if derive_case(row)["eleven_message_structure"] != "PASS":
            raise Hold("conditional window HOLD")
        case = row["case"]
        tail = row["history24"][-11:]
        if len(tail) != 11 or tail[0]["role"] != "user":
            raise Hold("history tail HOLD")
        for m in tail:
            try:
                msgid = str(uuid.UUID(m["id"]))
            except (ValueError, TypeError, KeyError, AttributeError):
                raise Hold("invalid source message ID")
            selected.append({
                "cohort": case["cohort"], "msgid": msgid,
                "story": case["story_id"], "session": case["session_id"],
                "target_at": case["target_created_at"], "role": m["role"],
                "revision": m["mutation_revision"],
                "digest": hashlib.sha256(m["content"].encode("utf-8")).hexdigest(),
            })
    if len(selected) != 33 or {r["cohort"] for r in selected} != COHORTS:
        raise Hold("fixed 33 message cohort HOLD")
    if len(set(r["msgid"] for r in selected)) != 33:
        raise Hold("duplicate physical message ID")
    return selected


def query_text(rows):
    # This JSON contains only IDs, time and digests, never narrative text.
    # It is sent to local psql through stdin, never through process argv.
    literal = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).replace("'", "''")
    return """BEGIN READ ONLY;
WITH fixed AS (
 SELECT * FROM jsonb_to_recordset('""" + literal + """'::jsonb)
 AS x(cohort text,msgid uuid,story text,session text,target_at timestamptz,
      role text,revision bigint,digest text)
), checked AS (
 SELECT f.cohort, f.role, f.revision,
        m.id IS NOT NULL AS exists_now,
        COALESCE(m.mutation_revision=f.revision,false) AS same_revision,
        COALESCE(encode(sha256(convert_to(m.content,'UTF8')),'hex')=f.digest,false)
          AS same_content,
        l.earlier, l.later, l.old_completed_different
 FROM fixed f
 LEFT JOIN public.v2_chat_messages m ON
   m.id=f.msgid AND m.story_id=f.story AND m.session_id=f.session
   AND m.role=f.role
 LEFT JOIN LATERAL (
   SELECT count(*) FILTER (WHERE e.recorded_at<=f.target_at) AS earlier,
          count(*) FILTER (WHERE e.recorded_at>f.target_at) AS later,
          count(*) FILTER (WHERE e.recorded_at<=f.target_at
             AND e.operation='update_before'
             AND e.row_data->>'status'='completed'
             AND e.row_data->>'content' IS DISTINCT FROM m.content)
             AS old_completed_different
   FROM public.v2_chat_message_ledger e
   WHERE e.message_id=f.msgid
     AND e.story_id=f.story AND e.session_id=f.session
 ) l ON true
), grouped AS (
 SELECT cohort, count(*) AS messages,
        count(*) FILTER (WHERE role='assistant') AS assistants,
        count(*) FILTER (WHERE role='user') AS users,
        count(*) FILTER (WHERE NOT exists_now) AS missing_current,
        count(*) FILTER (WHERE NOT same_revision) AS revision_drift,
        count(*) FILTER (WHERE NOT same_content) AS content_drift,
        sum(earlier) AS ledger_through_target,
        sum(later) AS ledger_after_target,
        sum(old_completed_different) AS prior_completed_text_variants
 FROM checked GROUP BY cohort
)
SELECT jsonb_build_object(
  'readonly',current_setting('transaction_read_only'),
  'reader',current_user='r58_export_reader',
  'cases', (SELECT jsonb_agg(to_jsonb(g) ORDER BY g.cohort) FROM grouped g)
)::text;
COMMIT;
"""


def aggregate(folder):
    rows = fixed_rows(folder)
    if os.getenv("PGHOST") not in DB_HOSTS or os.getenv("PGUSER") not in DB_USERS:
        raise Hold("unexpected DB host/reader role")
    if not os.getenv("PGPASSWORD"):
        raise Hold("missing private DB credential")
    env = os.environ.copy()
    env["PGOPTIONS"] = "-c default_transaction_read_only=on -c statement_timeout=90000"
    env["PGSSLMODE"] = "require"
    try:
        result = subprocess.run(
            ["psql", "-X", "-w", "-qAt", "-v", "ON_ERROR_STOP=1"],
            input=query_text(rows), text=True, capture_output=True,
            timeout=110, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Hold("DB query execution unavailable")
    if result.returncode or len(result.stdout.strip().splitlines()) != 1:
        raise Hold("DB aggregate failed")
    try:
        obj = json.loads(result.stdout.strip())
        cases = obj["cases"]
    except (ValueError, KeyError, TypeError):
        raise Hold("DB aggregate response malformed")
    if (obj.get("readonly") != "on" or obj.get("reader") is not True
            or not isinstance(cases, list) or len(cases) != 3
            or {c.get("cohort") for c in cases} != COHORTS):
        raise Hold("DB scope or read-only verification failed")
    fields = ("messages", "assistants", "users", "missing_current",
              "revision_drift", "content_drift", "ledger_through_target",
              "ledger_after_target", "prior_completed_text_variants")
    for c in cases:
        if any(type(c.get(k)) is not int or c[k] < 0 for k in fields):
            raise Hold("DB counts invalid")
        if (c["messages"], c["assistants"], c["users"]) != (11, 5, 6):
            raise Hold("DB fixed source count mismatch")
    return {
        "status": "R58_LEDGER_FIXED33_AGGREGATE_COMPLETED__ASOF_PROMPT_HOLD",
        "cases": sorted(cases, key=lambda c: c["cohort"]),
        "frozen_message_count": 33,
        "historical_request_time_text_parity": "HOLD",
        "provider_prompt_byte_exact": "HOLD",
        "training_admission": "HOLD",
    }


def main():
    ap = argparse.ArgumentParser(description="R58 private fixed-ID read-only aggregate")
    ap.add_argument("--private-dir", type=Path, required=True)
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()
    try:
        if args.plan_only:
            print(json.dumps({"status": "R58_LEDGER_FIXED33_PLAN_PASS",
                              "messages": len(fixed_rows(args.private_dir)),
                              "queried_db": False, "training_admission": "HOLD"}))
        else:
            print(json.dumps(aggregate(args.private_dir), sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError):
        print("R58_LEDGER_FIXED33: HOLD (scope, source or DB query)", file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
