"""R60 Owner-scoped private evidence candidate extraction for experimental review.

Requires explicitly specified Owner-approved story/session pairs. This script
does not grant training admission, attest license/consent, or prove sent inputs.
No raw content, IDs, SHA, paths, or database exception messages on stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

SCHEMA = "storyforge_r60_scoped_target_evidence_safe_v1"
OWNER_DB_ROLE = "r58_export_reader"
SCOPE_SCHEMA = "storyforge_r60_private_session_scope_v1"
BASE = Path.home() / ".local/share/storyforge/r59/private"
MAX_SESSIONS = 12
MAX_MESSAGES = 80
MAX_OUTPUT_BYTES = 12_000_000


class Hold(ValueError):
    pass


def private_input(path: Path) -> bytes:
    if (not path.is_absolute() or not path.is_relative_to(BASE)
            or path.is_symlink() or not path.is_file()
            or path.parent.is_symlink() or not path.parent.is_dir()):
        raise Hold("PRIVATE_SCOPE_PATH_HOLD")
    st = path.stat()
    if (stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
            or stat.S_IMODE(path.parent.stat().st_mode) != 0o700
            or st.st_size > 50000):
        raise Hold("PRIVATE_SCOPE_PERMISSION_HOLD")
    return path.read_bytes()


def parse_scope(raw: bytes) -> list[dict]:
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise Hold("PRIVATE_SCOPE_FORMAT_HOLD") from exc
    sessions = data.get("sessions") if isinstance(data, dict) else None
    if (data.get("schema") != SCOPE_SCHEMA
            or data.get("approved_purpose") != "PRIVATE_TRAINING_CANDIDATE_REVIEW_ONLY"
            or not isinstance(sessions, list)
            or not 1 <= len(sessions) <= MAX_SESSIONS):
        raise Hold("PRIVATE_SCOPE_SCHEMA_HOLD")
    keys = set()
    for row in sessions:
        if not isinstance(row, dict):
            raise Hold("PRIVATE_SCOPE_SESSION_HOLD")
        story, session = row.get("story_id"), row.get("session_id")
        if (not isinstance(story, str) or not 1 <= len(story) <= 128
                or not isinstance(session, str) or not 1 <= len(session) <= 128
                or row.get("owner_scope_confirmed") is not True
                or row.get("r50_protected_scope_excluded") is not True):
            raise Hold("PRIVATE_SCOPE_SESSION_HOLD")
        # Assertions delimit intended query scope; no independent rights proof.
        if (story, session) in keys:
            raise Hold("PRIVATE_SCOPE_DUPLICATE_HOLD")
        keys.add((story, session))
    return sessions


def select_targets(rows: list[tuple], story: str, session: str) -> tuple[list[dict], dict]:
    if len(rows) > MAX_MESSAGES:
        raise Hold("MESSAGE_LIMIT_HOLD")
    by_turn = {}
    for item in rows:
        if len(item) != 7:
            raise Hold("MESSAGE_ROW_SCHEMA_HOLD")
        mid, db_story, db_session, turn, role, status, created = item
        if (not isinstance(mid, str) or not isinstance(turn, int)
                or not isinstance(db_story, str) or db_story != story
                or not isinstance(db_session, str) or db_session != session
                or not isinstance(role, str)):
            raise Hold("MESSAGE_IDENTITY_HOLD")
        if turn in by_turn:
            raise Hold("DUPLICATE_TURN_HOLD")
        by_turn[turn] = (mid, role, status, str(created))
    targets = []
    for turn in sorted(by_turn):
        mid, role, status, created = by_turn[turn]
        prior = by_turn.get(turn - 1)
        if role != "assistant" or status != "completed" or not prior:
            continue
        user_id, user_role, user_status, _ = prior
        if user_role != "user" or user_status != "completed":
            continue
        targets.append({
            "story_id": story,
            "session_id": session,
            "assistant_message_id": mid,
            "assistant_turn": turn,
            "prior_user_message_id": user_id,
            "created_at": created,
            "provenance": "DB_COMPLETED_MESSAGE_PAIR_ONLY",
            "historical_input_verified": False,
            "provider_attempt_linked": False,
            "provider_single_completion_verified": False,
            "owner_case_rights_verified": False,
            "world_component_verified": False,
            "protected_exposure_verified": False,
            "context_provenance": "UNRECONSTRUCTED",
            "strict_gold_admitted": False,
            "experimental_admitted": False,
            "review_status": "HOLD_PENDING_E0_E3",
        })
    return targets, {"pairs": len(targets), "messages": len(rows)}


SQL = """
SELECT id::text, story_id, session_id, turn_index, role, status, created_at
FROM public.v2_chat_messages
WHERE session_id=%s AND story_id=%s
ORDER BY turn_index DESC LIMIT %s
"""


def assert_owner_db_guard(row: tuple) -> None:
    if row != (OWNER_DB_ROLE, "on", "on", False, False):
        raise Hold("DATABASE_GUARD_HOLD")


def fetch_scoped(dsn: str, sessions: list[dict]) -> tuple[list[dict], int]:
    import psycopg

    records = []
    scanned = 0
    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as db:
        try:
            with db.cursor() as cur:
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
                for record in sessions:
                    cur.execute(SQL, (record["session_id"], record["story_id"], MAX_MESSAGES))
                    rows = cur.fetchall()
                    targets, counts = select_targets(
                        rows, record["story_id"], record["session_id"]
                    )
                    records.extend(targets)
                    scanned += counts["messages"]
        finally:
            db.rollback()
    return records, scanned


def write_private(folder: Path, records: list[dict], safe: dict) -> None:
    if (not folder.is_absolute() or not folder.is_relative_to(BASE)
            or folder.exists() or folder.is_symlink() or folder.parent != BASE
            or not BASE.is_dir() or BASE.is_symlink()
            or stat.S_IMODE(BASE.stat().st_mode) != 0o700):
        raise Hold("PRIVATE_OUTPUT_PATH_HOLD")
    payload = b"".join(
        (json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n").encode()
        for x in records
    )
    if len(payload) > MAX_OUTPUT_BYTES:
        raise Hold("PRIVATE_OUTPUT_SIZE_HOLD")
    folder.mkdir(mode=0o700)
    for filename, blob in (
        ("R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl", payload),
        ("R60_TARGET_PAIR_SAFE.json", (
            json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n"
        ).encode()),
    ):
        fd = os.open(folder / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as dst:
            dst.write(blob)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        raw = private_input(args.scope)
        sessions = parse_scope(raw)
        dsn = os.environ.get("STORYFORGE_SUPABASE_DSN")
        if not dsn:
            raise Hold("DSN_UNAVAILABLE")
        rows, scanned = fetch_scoped(dsn, sessions)
        safe = {
            "schema": SCHEMA,
            "status": "SCOPED_TARGET_PAIR_LOCATORS_EXTRACTED_NOT_ADMITTED",
            "session_scope_count": len(sessions),
            "messages_scanned": scanned,
            "adjacent_completed_pairs": len(rows),
            "scope_sha256": hashlib.sha256(raw).hexdigest(),
            "request_attempt_verified_count": 0,
            "single_completion_verified_count": 0,
            "owner_case_rights_verified_count": 0,
            "independent_worlds_verified": 0,
            "strict_gold_admitted": 0,
            "experimental_admitted": 0,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }
        write_private(args.output_dir, rows, safe)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - do not expose private DB exceptions
        print(json.dumps({
            "schema": SCHEMA,
            "status": "SCOPED_TARGET_PAIR_HOLD",
            "reason_code": str(exc) if isinstance(exc, Hold) else type(exc).__name__,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
