"""R60 REAL-01：Owner 单对真实历史 User–Assistant 的只读技术优先级预筛。

输入为原 G0 提取器的私有 Scope、40 对 locator 与 SAFE。
仅查询目标精确身份、文本长度和有限元数据标记，不 SELECT 正文。
所有样本状态仍是未审核、未获训练准入；R50 排除仍 UNKNOWN。
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import uuid

from r60_scoped_target_pairs import (
    BASE,
    LIMITED_SCOPE_SCHEMA,
    Hold,
    assert_owner_db_guard,
    parse_scope,
    private_input,
)

SCHEMA = "storyforge_r60_real_history_triage_safe_v1"
MAX_PAIRS = 40
NORMAL_FINISH = frozenset(("stop", "STOP", "end_turn", "END_TURN"))
SQL = """
SELECT a.id::text, u.id::text, a.story_id, a.session_id, a.turn_index,
       a.role, a.status, u.role, u.status, u.story_id,
       char_length(a.content), char_length(btrim(u.content)),
       a.metadata->>'finishReason',
       COALESCE(a.metadata ? 'editedAt', false),
       COALESCE(a.metadata ? 'originalContent', false),
       COALESCE(a.metadata ? 'parseWarnings', false),
       COALESCE(u.metadata->>'type', ''),
       jsonb_typeof(a.metadata)
FROM public.v2_chat_messages a
JOIN public.v2_chat_messages u
  ON u.session_id = a.session_id AND u.turn_index = a.turn_index - 1
WHERE a.session_id = %s AND a.story_id = %s AND a.turn_index = %s
LIMIT 1
"""


def load_sources(scope: Path, locators: Path, receipt: Path):
    """只接受现存单对 G0 回执，不能把其他 Story/Session 混入本次授权。"""
    if len({str(scope), str(locators), str(receipt)}) != 3:
        raise Hold("SOURCE_PATHS_DUPLICATED")
    if (locators.name != "R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl"
            or receipt.name != "R60_TARGET_PAIR_SAFE.json"):
        raise Hold("SOURCE_FILENAMES_HOLD")
    scope_raw = private_input(scope)
    scope_obj = json.loads(scope_raw)
    if scope_obj.get("schema") != LIMITED_SCOPE_SCHEMA:
        raise Hold("SINGLE_PAIR_AUTHORIZATION_REQUIRED")
    sessions = parse_scope(scope_raw)
    if len(sessions) != 1:
        raise Hold("SINGLE_PAIR_AUTHORIZATION_REQUIRED")
    approved = sessions[0]
    raw_receipt = json.loads(private_input(receipt))
    import hashlib

    if (not isinstance(raw_receipt, dict)
            or raw_receipt.get("status") != "SCOPED_TARGET_PAIR_LOCATORS_EXTRACTED_NOT_ADMITTED"
            or raw_receipt.get("scope_sha256") != hashlib.sha256(scope_raw).hexdigest()
            or raw_receipt.get("session_scope_count") != 1
            or raw_receipt.get("strict_gold_admitted") != 0
            or raw_receipt.get("experimental_admitted") != 0):
        raise Hold("G0_RECEIPT_OR_SCOPE_HOLD")
    raw_pairs = private_input(locators)
    try:
        pairs = [json.loads(line) for line in raw_pairs.splitlines() if line.strip()]
    except ValueError as exc:
        raise Hold("PAIR_JSONL_FORMAT_HOLD") from exc
    if (not 1 <= len(pairs) <= MAX_PAIRS
            or raw_receipt.get("adjacent_completed_pairs") != len(pairs)):
        raise Hold("PAIR_COUNT_OR_RECEIPT_HOLD")
    keys = set()
    for item in pairs:
        if not isinstance(item, dict):
            raise Hold("PAIR_RECORD_HOLD")
        turn = item.get("assistant_turn")
        if (item.get("story_id") != approved["story_id"]
                or item.get("session_id") != approved["session_id"]
                or type(turn) is not int or turn < 2
                or item.get("provenance") != "DB_COMPLETED_MESSAGE_PAIR_ONLY"
                or item.get("experimental_admitted") is not False):
            raise Hold("PAIR_SCOPE_OR_STATUS_HOLD")
        for field in ("assistant_message_id", "prior_user_message_id"):
            value = item.get(field)
            if not isinstance(value, str):
                raise Hold("PAIR_MESSAGE_ID_HOLD")
            try:
                uuid.UUID(value)
            except ValueError as exc:
                raise Hold("PAIR_MESSAGE_ID_HOLD") from exc
        if turn in keys:
            raise Hold("PAIR_DUPLICATE_TURN_HOLD")
        keys.add(turn)
    return approved, sorted(pairs, key=lambda r: r["assistant_turn"])


def classify(pair: dict, row: tuple) -> dict:
    if row is None or len(row) != 18:
        raise Hold("EXACT_PAIR_NOT_FOUND")
    (aid, uid, story, session, turn, role, status, user_role, user_status,
     user_story, alen, ulen, finish, edited, original, warning,
     user_type, meta_type) = row
    if (aid != pair["assistant_message_id"]
            or uid != pair["prior_user_message_id"]
            or story != pair["story_id"]
            or session != pair["session_id"]
            or turn != pair["assistant_turn"]
            or role != "assistant" or status != "completed"
            or user_role != "user" or user_status != "completed"
            or user_story != story):
        raise Hold("PAIR_DB_IDENTITY_MISMATCH")
    if (type(alen) is not int or type(ulen) is not int
            or any(type(x) is not bool for x in (edited, original, warning))):
        raise Hold("PAIR_METADATA_TYPE_HOLD")
    reasons = []
    if alen < 300:
        reasons.append("TARGET_SHORTER_THAN_300")
    if ulen < 1 or user_type == "continue":
        reasons.append("EMPTY_OR_CONTINUE_USER")
    if finish not in NORMAL_FINISH:
        reasons.append("FINISH_REASON_UNVERIFIED")
    if edited or original:
        reasons.append("EDIT_METADATA_PRESENT")
    if warning:
        reasons.append("PARSE_WARNING_KEY_PRESENT")
    if meta_type != "object":
        reasons.append("ASSISTANT_METADATA_UNAVAILABLE")
    tier = "TECHNICAL_PRIORITY" if not reasons else "MANUAL_REVIEW_HOLD"
    return {
        "story_id": story,
        "session_id": session,
        "assistant_message_id": aid,
        "prior_user_message_id": uid,
        "assistant_turn": turn,
        "assistant_chars": alen,
        "prior_user_nonspace_chars": ulen,
        "target_semantics": "DB_FINAL_DELIVERED_ASSISTANT_CANDIDATE",
        "context_provenance": "UNRECONSTRUCTED",
        "technical_tier": tier,
        "technical_reason_codes": reasons,
        "quality_review_status": "UNREVIEWED",
        "rights_verified": False,
        "r50_exclusion_status": "UNKNOWN_HOLD",
        "world_component_status": "UNKNOWN_HOLD",
        "train_validation_split": None,
        "strict_gold_admitted": False,
        "experimental_admitted": False,
        "training_authorized": False,
    }


def fetch_exact(dsn: str, pairs: list[dict]) -> list[dict]:
    import psycopg

    results = []
    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout='5000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("""
                    SELECT current_user, current_setting('transaction_read_only'),
                           current_setting('row_security'), r.rolbypassrls, r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                """)
                assert_owner_db_guard(cur.fetchone())
                for pair in pairs:
                    cur.execute(SQL, (
                        pair["session_id"], pair["story_id"], pair["assistant_turn"],
                    ))
                    results.append(classify(pair, cur.fetchone()))
        finally:
            conn.rollback()
    return results


def safe_summary(rows: list[dict]) -> dict:
    tiers = Counter(row["technical_tier"] for row in rows)
    reasons = Counter(
        code for row in rows for code in row["technical_reason_codes"]
    )
    return {
        "schema": SCHEMA,
        "status": "REAL_HISTORY_METADATA_TRIAGED__QUALITY_NOT_REVIEWED",
        "owner_authorized_story_session_pairs": 1,
        "exact_pairs_revalidated": len(rows),
        "technical_priority": tiers["TECHNICAL_PRIORITY"],
        "manual_review_hold": tiers["MANUAL_REVIEW_HOLD"],
        "technical_reason_counts": dict(sorted(reasons.items())),
        "quality_reviewed": 0,
        "context_validated": 0,
        "rights_verified": 0,
        "r50_exclusion_verified": 0,
        "independent_worlds_verified": 0,
        "strict_gold_admitted": 0,
        "experimental_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_content_accessed": False,
        "private_values_emitted": False,
    }


def write_private(output: Path, rows: list[dict], safe: dict) -> None:
    if (not output.is_absolute() or not output.is_relative_to(BASE)
            or output.parent != BASE or output.exists() or output.is_symlink()
            or not BASE.is_dir() or BASE.is_symlink()
            or (BASE.stat().st_mode & 0o777) != 0o700):
        raise Hold("OUTPUT_PRIVATE_PATH_HOLD")
    output.mkdir(mode=0o700)
    for name, payload in (
        ("R60_REAL_HISTORY_TRIAGE_PRIVATE.jsonl", b"".join(
            (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode()
            for row in rows
        )),
        ("R60_REAL_HISTORY_TRIAGE_SAFE.json", (
            json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n"
        ).encode()),
    ):
        fd = os.open(
            output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
            getattr(os, "O_NOFOLLOW", 0), 0o600,
        )
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--target-pairs", type=Path, required=True)
    parser.add_argument("--g0-safe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        _approved, pairs = load_sources(args.scope, args.target_pairs, args.g0_safe)
        dsn = os.getenv("STORYFORGE_SUPABASE_DSN")
        if not dsn:
            raise Hold("DSN_UNAVAILABLE")
        rows = fetch_exact(dsn, pairs)
        safe = safe_summary(rows)
        write_private(args.output_dir, rows, safe)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - redact private DB or FS details
        print(json.dumps({
            "schema": SCHEMA,
            "status": "REAL_HISTORY_TRIAGE_HOLD",
            "reason_code": str(exc) if isinstance(exc, Hold) else type(exc).__name__,
            "strict_gold_admitted": 0,
            "experimental_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "r50_content_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
