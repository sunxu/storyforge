"""Gold48 scoped one-time private candidate recovery. Never a Gold freeze or model run.

Thin adapter: reuse storyforge_gold_quality.history_recovery for immutable
history/ledger recovery. Only the fixed eight Owner-reviewed P2 stories are read.
All raw text, identity and hashes remain in local 0600 files, never stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from storyforge_gold_quality.history_recovery import HistoryRecoveryError, recover_case

CUTOFF = datetime.fromisoformat("2026-11-19T15:30:00+00:00")
MAX_PER_STORY = 160
ALLOWED_SCHEMAS = {
    "storyforge_r60_base336_p2_public_source_inventory_private_v2",
}
IDS_SCHEMA = "storyforge_r60_p2_gold48_source_ids_private_v1"
SAFE_SCHEMA = "storyforge_r60_p2_gold48_private_recovery_capture_safe_v1"


class Hold(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Hold(reason)


def timestamp(s):
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        raise Hold("SOURCE_TIMESTAMP_HOLD") from None
    require(d.tzinfo is not None, "SOURCE_TIMESTAMP_ZONE_HOLD")
    return d.astimezone(timezone.utc)


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()


def load_private(path, max_bytes):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode) and not path.is_symlink()
            and stat.S_IMODE(s.st_mode) == 0o600 and 0 < s.st_size <= max_bytes,
            "PRIVATE_INPUT_MODE_OR_SIZE_HOLD")
    return json.loads(path.read_bytes())


def validate_sources(ids_doc, manifest, binding):
    require(ids_doc.get("schema") == IDS_SCHEMA
            and ids_doc.get("status") == "GOLD48_COMPLETE_HISTORY_SOURCE_IDS__OWNER_FREEZE_PENDING",
            "SOURCE_ID_LIST_HOLD")
    require(manifest.get("schema") in ALLOWED_SCHEMAS
            and manifest.get("status") == "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING",
            "SOURCE_MANIFEST_HOLD")
    ids = ids_doc.get("story_ids")
    rows = manifest.get("sources")
    require(isinstance(ids, list) and len(ids) == 8 and len(set(ids)) == 8
            and isinstance(rows, list) and len(rows) == 8,
            "SOURCE_COUNT_HOLD")
    require(set(ids) == {s.get("story_id") for s in rows}, "SOURCE_LIST_BINDING_HOLD")
    require(manifest.get("selection", {}).get("created_before_gpu_run") == 2
            and manifest.get("selection", {}).get("created_after_gpu_run") == 6
            and manifest.get("selection", {}).get("authors") == 7,
            "SOURCE_COHORT_HOLD")
    bykey = {s.get("source_key"): s for s in rows}
    require(len(bykey) == 8, "SOURCE_KEY_HOLD")
    pairs = binding.get("bindings_PRIVATE")
    require(isinstance(pairs, list) and len(pairs) == 8,
            "REVIEWER_BINDING_HOLD")
    for b in pairs:
        s = bykey.get(b.get("source_key_PRIVATE"))
        require(s is not None and b.get("story_id_PRIVATE") == s["story_id"]
                and b.get("public_content_revision_PRIVATE") == s["public_content_revision"],
                "REVIEWER_SOURCE_REVISION_HOLD")
    flagged = [b["story_id_PRIVATE"] for b in pairs
               if b.get("reviewer_ref_PRIVATE") == "P04"]
    require(len(flagged) == 1, "FLAGGED_SOURCE_HOLD")
    for s in rows:
        require(s.get("permission_to_visibility") == "public"
                and s.get("permission_submission_bound") is True
                and s.get("snapshot_matches_current_public_v2") is True
                and s.get("permission_kind") in ("ai", "update")
                and s.get("permission_result") == (
                    "ai_approved" if s["permission_kind"] == "ai" else "approved"
                ), "SOURCE_PERMISSION_HOLD")
        require(timestamp(s.get("created_at_utc")) <= CUTOFF,
                "SOURCE_CREATION_CUTOFF_HOLD")
    return rows, flagged[0]


def edited(md):
    return isinstance(md, dict) and any(
        md.get(k) not in (None, False, "") for k in ("editedAt", "originalContent")
    )


TARGET_SQL = """
SELECT id::text, session_id, turn_index, content, metadata, created_at
FROM public.v2_chat_messages
WHERE story_id = %s AND role = 'assistant' AND status = 'completed'
  AND created_at >= %s AND created_at <= %s AND turn_index > 0
  AND length(btrim(content)) > 0
ORDER BY created_at, session_id, turn_index, id
LIMIT %s
"""
CURRENT_SQL = """
SELECT id::text, content, metadata FROM public.v2_chat_messages
WHERE id = ANY(%s::uuid[])
"""
CHANGED_SQL = """
SELECT EXISTS (
  SELECT 1 FROM public.v2_chat_message_ledger l
  JOIN public.v2_chat_messages m ON m.id = l.message_id
  WHERE l.message_id = ANY(%s::uuid[]) AND l.operation = 'update_before'
    AND l.row_data->>'status' = 'completed'
    AND (l.row_data->>'content') IS DISTINCT FROM m.content
)
"""
REQUEST_SQL = """
SELECT DISTINCT l.request_id
FROM public.chat_latency_metrics l
JOIN public.v2_chat_request_events e ON e.request_id = l.request_id
WHERE l.story_id = %s AND l.session_id = %s
  AND e.story_id = %s AND e.session_id = %s
  AND l.created_at BETWEEN %s AND %s
  AND e.occurred_at BETWEEN %s AND %s
  AND l.status = 200 AND e.status = 200
  AND l.finish_reason = 'stop'
  AND l.system_tokens > 0 AND l.history_tokens > 0 AND l.input_tokens > 0
  AND l.token_breakdown->>'historyMsgCount' = %s
LIMIT 3
"""


def try_case(cur, source, row):
    mid, sid, turn, answer, metadata, created = row
    if not isinstance(answer, str) or not answer.strip() or edited(metadata):
        return None
    story = source["story_id"]
    cur.execute(
        "SELECT deleted_at FROM public.story_v2_sessions "
        "WHERE story_id = %s AND session_id = %s",
        (story, sid),
    )
    session_rows = cur.fetchall()
    if len(session_rows) != 1 or session_rows[0][0] is not None:
        return None
    case = {"case_id": mid, "story_id": story, "session_id": sid,
            "turn_index": turn, "target_sha256": hashlib.sha256(answer.encode()).hexdigest()}
    try:
        recovered = recover_case(cur, case, max_history=40, max_ledger_events=50000)
    except HistoryRecoveryError:
        return None
    history = recovered["history"]
    if not 3 <= len(history) <= 40 or history[-1]["role"] != "user":
        return None
    if any(m["role"] not in ("user", "assistant") or
           not isinstance(m["content"], str) or not m["content"].strip()
           or m["status"] != "completed" for m in history):
        return None
    earliest = max(timestamp(source["first_public_approved_at_utc"]),
                   timestamp(source["public_updated_at_utc"])
                   if source.get("public_updated_at_utc") else
                   timestamp(source["first_public_approved_at_utc"]))
    if timestamp(history[0]["created_at"]) < earliest:
        return None
    if sum(len(m["content"]) for m in history) > 24000:
        return None
    mids = [m["message_id"] for m in history] + [mid]
    cur.execute(CURRENT_SQL, (mids,))
    current = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    if len(current) != len(mids) or any(
        m["message_id"] not in current
        or current[m["message_id"]][0] != m["content"]
        or edited(current[m["message_id"]][1]) for m in history
    ) or mid not in current or current[mid][0] != answer or edited(current[mid][1]):
        return None
    cur.execute(CHANGED_SQL, (mids,))
    if cur.fetchone()[0]:
        return None
    lower, upper = created - timedelta(minutes=5), created + timedelta(minutes=5)
    cur.execute(REQUEST_SQL, (story, sid, story, sid, lower, upper,
                              lower, upper, str(len(history))))
    matches = [x[0] for x in cur.fetchall()]
    if len(matches) != 1:
        return None
    prompt = [{"role":m["role"], "content":m["content"]} for m in history]
    return {
        "source_key_PRIVATE": source["source_key"],
        "story_id_PRIVATE": story, "session_id_PRIVATE": sid,
        "assistant_message_id_PRIVATE": mid, "request_id_PRIVATE": matches[0],
        "target_turn_index_PRIVATE": turn, "target_created_at_PRIVATE": created.isoformat(),
        "prefix_messages_PRIVATE": prompt, "original_reply_PRIVATE": answer,
        "prefix_sha256_PRIVATE": digest(prompt), "original_reply_sha256_PRIVATE": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        "source_public_revision_PRIVATE": source["public_content_revision"],
        "source_snapshot_sha256_PRIVATE": source["submission_snapshot_sha256"],
        "history_recovery_PRIVATE": recovered,
    }


def atomic_new(path, payload):
    raw = canonical(payload) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)


def run(args):
    base = Path.home() / ".local/share/storyforge/r60/private"
    require(base.is_dir() and not base.is_symlink()
            and stat.S_IMODE(base.stat().st_mode) == 0o700,
            "OWNER_PRIVATE_BASE_HOLD")
    sources, flagged = validate_sources(
        load_private(args.ids, 10000),
        load_private(args.manifest, 2000000),
        load_private(args.reviewer_binding, 1000000),
    )
    out = args.output_dir
    require(out.is_absolute() and out.parent == base
            and not out.exists() and not out.is_symlink(),
            "CREATE_ONLY_OUTPUT_TARGET_HOLD")
    dsn = os.environ.get("R60_READONLY_DATABASE_URL", "")
    require(bool(dsn), "READONLY_DATABASE_URL_MISSING")
    try:
        import psycopg
    except ImportError:
        raise Hold("PSYCOPG_NOT_INSTALLED") from None

    selected = []
    examined = 0
    rejected = 0
    try:
        with psycopg.connect(dsn, connect_timeout=10, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout = '60000ms'")
                cur.execute("SET LOCAL lock_timeout = '1000ms'")
                cur.execute("SET LOCAL row_security = on")
                cur.execute("""
                    SELECT current_setting('transaction_read_only'), r.rolsuper, r.rolbypassrls
                    FROM pg_catalog.pg_roles r WHERE r.rolname = current_user
                """)
                rdonly, superuser, bypass = cur.fetchone()
                require(rdonly == "on" and not superuser and not bypass,
                        "READONLY_ROLE_GUARD_HOLD")
                used_prompts, used_replies, used_targets, used_requests = set(), set(), set(), set()
                for source in sources:
                    earliest = max(timestamp(source["first_public_approved_at_utc"]),
                                   timestamp(source["public_updated_at_utc"])
                                   if source.get("public_updated_at_utc") else
                                   timestamp(source["first_public_approved_at_utc"]))
                    cur.execute(TARGET_SQL,
                                (source["story_id"], earliest, CUTOFF, MAX_PER_STORY))
                    targets = cur.fetchall()
                    eligible = []
                    for target in targets:
                        examined += 1
                        candidate = try_case(cur, source, target)
                        if candidate is None:
                            rejected += 1
                            continue
                        eligible.append(candidate)
                    eligible.sort(key=lambda x: (
                        len(x["prefix_messages_PRIVATE"]),
                        x["target_created_at_PRIVATE"],
                        x["session_id_PRIVATE"],
                        x["assistant_message_id_PRIVATE"]
                    ))
                    n = 0
                    for candidate in eligible:
                        ph, rh = candidate["prefix_sha256_PRIVATE"], candidate["original_reply_sha256_PRIVATE"]
                        mid, rid = candidate["assistant_message_id_PRIVATE"], candidate["request_id_PRIVATE"]
                        if ph in used_prompts or rh in used_replies or mid in used_targets or rid in used_requests:
                            continue
                        used_prompts.add(ph); used_replies.add(rh)
                        used_targets.add(mid); used_requests.add(rid)
                        selected.append(candidate)
                        n += 1
                        if n == 6:
                            break
                    require(n == 6, "INSUFFICIENT_SIX_PER_STORY_STRICT_CANDIDATES_HOLD")
            conn.rollback()
    except psycopg.Error:
        raise Hold("BOUNDED_READONLY_DATABASE_QUERY_HOLD") from None
    require(len(selected) == 48 and len({x["session_id_PRIVATE"] for x in selected}) >= 8,
            "CANDIDATE_SET_CARDINALITY_HOLD")
    flagged_rows = [x for x in selected if x["story_id_PRIVATE"] == flagged]
    require(len(flagged_rows) == 6, "FLAGGED_STORY_SIX_CASES_HOLD")
    for idx, row in enumerate(selected, 1):
        row["candidate_case_id_PRIVATE"] = f"G48-C{idx:02d}"
        row["exclude_from_42_sensitivity"] = row["story_id_PRIVATE"] == flagged
    os.mkdir(out, 0o700)
    require(stat.S_IMODE(out.stat().st_mode) == 0o700,
            "PRIVATE_OUTPUT_DIR_MODE_HOLD")
    doc = {
        "schema": "storyforge_r60_gold48_restored_candidate_private_v1",
        "status": "NEW_RECONSTRUCTED_48_CANDIDATES__NOT_OWNER_FROZEN",
        "origin_identity": "PRIOR_20261120_PROVISIONAL_TARGET_IDS_NOT_PRESERVED__NEW_SELECTION",
        "eval_input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "cases_PRIVATE": selected,
    }
    atomic_new(out / "GOLD48_RECOVERED_CANDIDATES_PRIVATE.json", doc)
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "NEW_GOLD48_PRIVATE_CANDIDATES_CAPTURED__NOT_FROZEN",
        "source_count": 8, "case_count": 48,
        "history_prefix_count": 48, "original_reference_count": 48,
        "request_metadata_unique_count": 48,
        "session_count": len({x["session_id_PRIVATE"] for x in selected}),
        "flagged_story_case_count": 6, "primary_count": 48, "sensitivity_count": 42,
        "targets_examined": examined, "targets_rejected": rejected,
        "prior_provisional_48_exact_identity_verified": False,
        "reconstructed_system_world_rules_memory_frozen": False,
        "owner_final_gold48_freeze": False,
        "p2_c_full_universe": "UNVERIFIED",
        "p2_c_scoped_policy": "RISK_ACCEPTED",
        "private_values_emitted": False,
        "database_modified": False, "gpu_started": False, "model_calls": 0,
    }
    atomic_new(out / "GOLD48_CAPTURE_SAFE.json", safe)
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reviewer-binding", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False, sort_keys=True))
    except Hold as exc:
        print(json.dumps({"schema": SAFE_SCHEMA, "status": "HOLD",
                          "reason_code": str(exc),
                          "private_values_emitted": False,
                          "database_modified": False, "gpu_started": False},
                         sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"schema": SAFE_SCHEMA, "status": "HOLD",
                          "reason_code": "PRIVATE_RECOVERY_UNEXPECTED_RUNTIME_HOLD",
                          "private_values_emitted": False,
                          "database_modified": False, "gpu_started": False},
                         sort_keys=True))


if __name__ == "__main__":
    main()
