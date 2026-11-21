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
import stat
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from itertools import pairwise
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
    def __init__(self, reason, safe_diagnostics=None):
        super().__init__(reason)
        self.safe_diagnostics = safe_diagnostics


def require(ok, reason):
    if not ok:
        raise Hold(reason)


def timestamp(s):
    try:
        d = datetime.fromisoformat(s)
    except (TypeError, ValueError, AttributeError):
        raise Hold("SOURCE_TIMESTAMP_HOLD") from None
    require(d.tzinfo is not None, "SOURCE_TIMESTAMP_ZONE_HOLD")
    return d.astimezone(UTC)


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
  WHERE l.session_id = %s AND l.story_id = %s
    AND l.message_id = ANY(%s::uuid[]) AND l.operation = 'update_before'
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



REQUEST_ZERO_DIAGNOSTIC_SQL = """
WITH matched_time AS (
    SELECT
        (l.status = 200 AND l.finish_reason = 'stop') AS success_metric,
        (l.system_tokens > 0 AND l.history_tokens > 0 AND l.input_tokens > 0)
            AS nonzero_tokens,
        (l.token_breakdown->>'historyMsgCount' = %s) AS same_history_count,
        (e.request_id IS NOT NULL) AS event_exists,
        (e.status = 200) AS event_is_200,
        (e.story_id = l.story_id) AS event_story_matches,
        (e.session_id = l.session_id) AS event_session_matches,
        (e.occurred_at BETWEEN %s AND %s) AS event_time_matches
    FROM public.chat_latency_metrics l
    LEFT JOIN public.v2_chat_request_events e ON e.request_id = l.request_id
    WHERE l.story_id = %s AND l.session_id = %s
      AND l.created_at BETWEEN %s AND %s
)
SELECT
    count(*),
    count(*) FILTER (WHERE success_metric),
    count(*) FILTER (WHERE success_metric AND nonzero_tokens),
    count(*) FILTER (
        WHERE success_metric AND nonzero_tokens AND same_history_count
    ),
    count(*) FILTER (
        WHERE success_metric AND nonzero_tokens AND same_history_count
          AND event_exists
    ),
    count(*) FILTER (
        WHERE success_metric AND nonzero_tokens AND same_history_count
          AND event_exists AND event_is_200
    ),
    count(*) FILTER (
        WHERE success_metric AND nonzero_tokens AND same_history_count
          AND event_exists AND event_is_200 AND event_story_matches
    ),
    count(*) FILTER (
        WHERE success_metric AND nonzero_tokens AND same_history_count
          AND event_exists AND event_is_200 AND event_story_matches
          AND event_session_matches
    ),
    count(*) FILTER (
        WHERE success_metric AND nonzero_tokens AND same_history_count
          AND event_exists AND event_is_200 AND event_story_matches
          AND event_session_matches AND event_time_matches
    )
FROM matched_time
"""


def classify_request_zero_counts(counts):
    labels = (
        "REQUEST_NO_METRIC_WITHIN_5M",
        "REQUEST_METRIC_STATUS_OR_FINISH_MISMATCH",
        "REQUEST_NONZERO_TOKEN_CONTRACT_MISMATCH",
        "REQUEST_HISTORY_MSG_COUNT_MISMATCH",
        "REQUEST_EVENT_ID_NOT_FOUND",
        "REQUEST_EVENT_STATUS_MISMATCH",
        "REQUEST_EVENT_STORY_MISMATCH",
        "REQUEST_EVENT_SESSION_MISMATCH",
        "REQUEST_EVENT_TIME_WINDOW_MISMATCH",
    )
    if len(counts) != len(labels) or any(
        type(v) is not int or v < 0 for v in counts
    ):
        return "REQUEST_DIAGNOSTIC_SHAPE_HOLD"
    if any(left < right for left, right in pairwise(counts)):
        return "REQUEST_DIAGNOSTIC_INCONSISTENT_HOLD"
    for count, label in zip(counts, labels, strict=True):
        if count == 0:
            return label
    return "REQUEST_UNCLASSIFIED_ZERO_MATCH"


def diagnose_request_zero(cur, story, sid, lower, upper, history_count):
    cur.execute(
        REQUEST_ZERO_DIAGNOSTIC_SQL,
        (str(history_count), lower, upper, story, sid, lower, upper),
    )
    row = cur.fetchone()
    return classify_request_zero_counts(row if row is not None else ())


def try_case(cur, source, row, phase=None, reject_counts=None):
    phase = phase if phase is not None else ["CASE_BEGIN"]

    def reject(reason):
        if reject_counts is not None:
            reject_counts[reason] += 1

    mid, sid, turn, answer, metadata, created = row
    if not isinstance(answer, str) or not answer.strip() or edited(metadata):
        return reject("TARGET_INVALID_OR_EDITED")
    story = source["story_id"]
    phase[0] = "SESSION_STATUS"
    cur.execute(
        "SELECT deleted_at FROM public.story_v2_sessions "
        "WHERE story_id = %s AND session_id = %s",
        (story, sid),
    )
    session_rows = cur.fetchall()
    if len(session_rows) != 1 or session_rows[0][0] is not None:
        return reject("SESSION_MISSING_OR_DELETED")
    case = {"case_id": mid, "story_id": story, "session_id": sid,
            "turn_index": turn, "target_sha256": hashlib.sha256(answer.encode()).hexdigest()}
    phase[0] = "HISTORY_LEDGER_RECOVERY"
    try:
        recovered = recover_case(cur, case, max_history=40, max_ledger_events=50000)
    except HistoryRecoveryError as exc:
        # Only expose static uppercase reason codes from the shared recoverer.
        reason = str(exc)
        if not (3 <= len(reason) <= 80
                and all(ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in reason)):
            reason = "UNCLASSIFIED"
        return reject("HISTORY_" + reason)
    history = recovered["history"]
    if not 3 <= len(history) <= 40 or history[-1]["role"] != "user":
        return reject("HISTORY_LENGTH_OR_SUFFIX_HOLD")
    # Fail closed on hidden non-completed / unsupported-role persisted turns:
    # the shared recoverer intentionally excludes these from effective history.
    phase[0] = "PREFIX_PERSISTENCE_COUNT"
    cur.execute(
        "SELECT count(*) FROM public.v2_chat_messages "
        "WHERE story_id = %s AND session_id = %s "
        "AND turn_index <= %s AND created_at < %s",
        (story, sid, turn - 1, created),
    )
    persisted_count = cur.fetchone()[0]
    if persisted_count != len(history):
        return reject(
            "PREFIX_PERSISTENCE_EXCEEDS_RECONSTRUCTED"
            if persisted_count > len(history)
            else "PREFIX_RECONSTRUCTED_EXCEEDS_PERSISTED"
        )
    if any(m["role"] not in ("user", "assistant") or
           not isinstance(m["content"], str) or not m["content"].strip()
           or m["status"] != "completed" for m in history):
        return reject("PREFIX_ROLE_STATUS_OR_CONTENT_HOLD")
    earliest = max(timestamp(source["first_public_approved_at_utc"]),
                   timestamp(source["public_updated_at_utc"])
                   if source.get("public_updated_at_utc") else
                   timestamp(source["first_public_approved_at_utc"]))
    if timestamp(history[0]["created_at"]) < earliest:
        return reject("PREFIX_PREDATES_PUBLIC_REVISION")
    if sum(len(m["content"]) for m in history) > 24000:
        return reject("PREFIX_LENGTH_EXCEEDS_24000")
    mids = [m["message_id"] for m in history] + [mid]
    phase[0] = "PREFIX_CURRENT_IDENTITY"
    cur.execute(CURRENT_SQL, (mids,))
    current = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    if len(current) != len(mids) or any(
        m["message_id"] not in current
        or current[m["message_id"]][0] != m["content"]
        or edited(current[m["message_id"]][1]) for m in history
    ) or mid not in current or current[mid][0] != answer or edited(current[mid][1]):
        return reject("PREFIX_CURRENT_MESSAGE_MISMATCH_OR_EDIT")
    phase[0] = "COMPLETED_HISTORY_EDIT_SCREEN"
    cur.execute(CHANGED_SQL, (sid, story, mids))
    if cur.fetchone()[0]:
        return reject("COMPLETED_HISTORY_EDIT_DETECTED")
    lower, upper = created - timedelta(minutes=5), created + timedelta(minutes=5)
    phase[0] = "UNIQUE_REQUEST_MATCH"
    cur.execute(REQUEST_SQL, (story, sid, story, sid, lower, upper,
                              lower, upper, str(len(history))))
    matches = [x[0] for x in cur.fetchall()]
    if len(matches) != 1:
        if matches:
            return reject("REQUEST_MULTIPLE_MATCHES")
        if reject_counts is None:
            return reject("REQUEST_ZERO_MATCH")
        phase[0] = "REQUEST_ZERO_DIAGNOSTIC"
        detail = diagnose_request_zero(cur, story, sid, lower, upper, len(history))
        return reject(detail)
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



def partition_cases(selected):
    locators, prompts, references = [], [], []
    for item in selected:
        case_id = item["candidate_case_id_PRIVATE"]
        locators.append({
            k: v for k, v in item.items()
            if k not in ("prefix_messages_PRIVATE", "original_reply_PRIVATE",
                         "history_recovery_PRIVATE")
        })
        prompts.append({
            "candidate_case_id_PRIVATE": case_id,
            "prefix_messages_PRIVATE": item["prefix_messages_PRIVATE"],
            "history_recovery_PRIVATE": item["history_recovery_PRIVATE"],
            "prefix_sha256_PRIVATE": item["prefix_sha256_PRIVATE"],
        })
        references.append({
            "candidate_case_id_PRIVATE": case_id,
            "original_reply_PRIVATE": item["original_reply_PRIVATE"],
            "original_reply_sha256_PRIVATE": item["original_reply_sha256_PRIVATE"],
        })
    return locators, prompts, references


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
    phase = ["DB_CONNECT"]
    try:
        with psycopg.connect(dsn, connect_timeout=10, autocommit=False) as conn:
            with conn.cursor() as cur:
                phase[0] = "READONLY_TRANSACTION_SETUP"
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout = '60000ms'")
                cur.execute("SET LOCAL lock_timeout = '1000ms'")
                cur.execute("SET LOCAL row_security = on")
                phase[0] = "READONLY_ROLE_PREFLIGHT"
                cur.execute("""
                    SELECT current_setting('transaction_read_only'), r.rolsuper, r.rolbypassrls
                    FROM pg_catalog.pg_roles r WHERE r.rolname = current_user
                """)
                rdonly, superuser, bypass = cur.fetchone()
                require(rdonly == "on" and not superuser and not bypass,
                        "READONLY_ROLE_GUARD_HOLD")
                used_prompts, used_replies, used_targets, used_requests = set(), set(), set(), set()
                for source_ordinal, source in enumerate(sources, 1):
                    earliest = max(timestamp(source["first_public_approved_at_utc"]),
                                   timestamp(source["public_updated_at_utc"])
                                   if source.get("public_updated_at_utc") else
                                   timestamp(source["first_public_approved_at_utc"]))
                    phase[0] = "BOUNDED_TARGET_DISCOVERY"
                    cur.execute(TARGET_SQL,
                                (source["story_id"], earliest, CUTOFF, MAX_PER_STORY))
                    targets = cur.fetchall()
                    eligible = []
                    reject_counts = Counter()
                    for target in targets:
                        examined += 1
                        candidate = try_case(cur, source, target, phase, reject_counts)
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
                    duplicate_collisions = 0
                    for candidate in eligible:
                        ph, rh = candidate["prefix_sha256_PRIVATE"], candidate["original_reply_sha256_PRIVATE"]
                        mid, rid = candidate["assistant_message_id_PRIVATE"], candidate["request_id_PRIVATE"]
                        if ph in used_prompts or rh in used_replies or mid in used_targets or rid in used_requests:
                            duplicate_collisions += 1
                            continue
                        used_prompts.add(ph); used_replies.add(rh)
                        used_targets.add(mid); used_requests.add(rid)
                        selected.append(candidate)
                        n += 1
                        if n == 6:
                            break
                    if n != 6:
                        # The ordinal is an anonymous position, never a Story/Session ID.
                        # Fail closed: no private output directory has been created.
                        raise Hold("INSUFFICIENT_SIX_PER_STORY_STRICT_CANDIDATES_HOLD", {
                            "source_ordinal_1based": source_ordinal,
                            "targets_fetched": len(targets),
                            "target_limit_hit": len(targets) == MAX_PER_STORY,
                            "eligible_before_cross_source_dedup": len(eligible),
                            "selected_after_cross_source_dedup": n,
                            "cross_source_duplicates_skipped": duplicate_collisions,
                            "rejection_counts": dict(sorted(reject_counts.items())),
                        })
            conn.rollback()
    except psycopg.Error as exc:
        # SQLSTATE is a five-character public PostgreSQL error class code;
        # never print DB exception messages, SQL strings, parameter values or IDs.
        state = exc.sqlstate
        state = state if isinstance(state, str) and len(state) == 5 and state.isalnum() else "NONE"
        raise Hold(f"READONLY_DB_{phase[0]}_SQLSTATE_{state}_HOLD") from None
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
    shared = {
        "status": "NEW_RECONSTRUCTED_48_CANDIDATES__NOT_OWNER_FROZEN",
        "origin_identity": "PRIOR_20261120_PROVISIONAL_TARGET_IDS_NOT_PRESERVED__NEW_SELECTION",
        "eval_input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
    }
    # Deliberately separate model-visible prefix candidates and withheld
    # historical original references. Never create a combined inference file.
    locators, prompts, references = partition_cases(selected)
    atomic_new(out / "GOLD48_CANDIDATE_LOCATORS_PRIVATE.json", {
        "schema": "storyforge_r60_gold48_recovered_locators_private_v1",
        **shared, "cases_PRIVATE": locators,
    })
    atomic_new(out / "GOLD48_CANDIDATE_PREFIXES_PRIVATE.json", {
        "schema": "storyforge_r60_gold48_recovered_prefixes_private_v1",
        **shared, "cases_PRIVATE": prompts,
    })
    atomic_new(out / "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json", {
        "schema": "storyforge_r60_gold48_recovered_references_private_v1",
        **shared, "cases_PRIVATE": references,
    })
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
        safe = {"schema": SAFE_SCHEMA, "status": "HOLD",
                "reason_code": str(exc),
                "private_values_emitted": False,
                "database_modified": False, "gpu_started": False}
        if exc.safe_diagnostics is not None:
            safe["safe_diagnostics"] = exc.safe_diagnostics
        print(json.dumps(safe, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"schema": SAFE_SCHEMA, "status": "HOLD",
                          "reason_code": "PRIVATE_RECOVERY_UNEXPECTED_RUNTIME_HOLD",
                          "private_values_emitted": False,
                          "database_modified": False, "gpu_started": False},
                         sort_keys=True))


if __name__ == "__main__":
    main()
