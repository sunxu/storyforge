"""R60 dual-track Supabase shortlist: bounded Owner-allowlisted metadata only.

No message text or JSONB is selected. Does not attest rights, actual input, world
isolation, target semantics, or training readiness. Requires non-bypass RLS role.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "storyforge_r60_dual_track_coverage_safe_v1"
ALLOWLIST_SCHEMA = "storyforge_r60_owner_story_scope_private_v1"
ROLE = "r58_export_reader"
ROOT = Path.home() / ".local/share/storyforge/r59/private"
MAX_STORIES = 16
MAX_PER_STORY = 20
HEX = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


class Hold(ValueError):
    pass


def read_scope(path: Path):
    if (not path.is_absolute() or not path.is_relative_to(ROOT)
            or path.is_symlink() or not path.is_file()
            or path.parent.is_symlink()
            or stat.S_IMODE(path.parent.stat().st_mode) != 0o700):
        raise Hold("SCOPE_PATH_OR_PARENT_INVALID")
    info = path.stat()
    if (stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1
            or not 0 < info.st_size <= 20000):
        raise Hold("SCOPE_PERMISSION_OR_SIZE_INVALID")
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise Hold("SCOPE_JSON_INVALID") from exc
    ids = data.get("story_ids")
    if (data.get("schema") != ALLOWLIST_SCHEMA
            or not isinstance(ids, list)
            or not 1 <= len(ids) <= MAX_STORIES
            or any(not isinstance(x, str) or HEX.fullmatch(x) is None for x in ids)
            or len(ids) != len(set(ids))
            or data.get("scope_note") != "OWNER_APPROVED_CANDIDATE_DISCOVERY_ONLY"):
        raise Hold("SCOPE_INVALID")
    return sorted(ids), hashlib.sha256(raw).hexdigest()


def assert_guard(cur):
    cur.execute("SET LOCAL statement_timeout = '3000ms'")
    cur.execute("SET LOCAL lock_timeout = '1000ms'")
    cur.execute("SET LOCAL row_security = on")
    cur.execute("""
        SELECT current_user, current_setting('transaction_read_only'),
               current_setting('row_security'), r.rolbypassrls, r.rolsuper
        FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
    """)
    role, read_only, rls, bypass, superuser = cur.fetchone()
    if (role != ROLE or read_only != "on" or rls != "on"
            or bypass is not False or superuser is not False):
        raise Hold("DB_ROLE_OR_RLS_GUARD_FAILED")
    cur.execute("""
        SELECT c.relname, c.relrowsecurity,
               pg_catalog.has_column_privilege(current_user,c.oid,'story_id','SELECT'),
               EXISTS (
                 SELECT 1 FROM pg_catalog.pg_index i
                 JOIN pg_catalog.pg_attribute a
                   ON a.attrelid=c.oid AND a.attnum=i.indkey[0]
                 WHERE i.indrelid=c.oid AND i.indisvalid AND i.indisready
                   AND a.attname='story_id'
               )
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname='v2_chat_messages'
    """)
    row = cur.fetchone()
    if not row or row[1] is not True or row[2] is not True or row[3] is not True:
        raise Hold("MESSAGE_TABLE_PERMISSION_OR_INDEX_HOLD")


def screen(fetch, story_ids):
    """Pure bounded candidate collector; fetch is a trusted metadata-only callable."""
    if not 1 <= len(story_ids) <= MAX_STORIES:
        raise Hold("SCOPE_COUNT_INVALID")
    out = []
    for story_id in story_ids:
        rows = fetch(story_id)
        if not isinstance(rows, list) or len(rows) > MAX_PER_STORY:
            raise Hold("CANDIDATE_LIMIT_EXCEEDED")
        for row in rows:
            if not isinstance(row, (tuple, list)) or len(row) != 6:
                raise Hold("CANDIDATE_ROW_INVALID")
            message_id, session, turn, created, length, status = row
            if (not isinstance(message_id, str) or not message_id
                    or not isinstance(session, str) or not session
                    or not isinstance(turn, int) or turn < 1
                    or not isinstance(length, int) or length < 100 or length > 6000
                    or status != "completed"):
                raise Hold("CANDIDATE_METADATA_INVALID")
            out.append({
                "story_id": story_id,
                "message_id": message_id,
                "session_id": session,
                "turn_index": turn,
                "created_at": str(created),
                "content_length": length,
                "source_category": "DB_FINAL_MESSAGE_METADATA_ONLY",
                "actual_sent_payload_verified": False,
                "single_completion_verified": False,
                "world_component_verified": False,
                "protected_set_verified": False,
                "owner_case_rights_verified": False,
                "strict_gold_admitted": False,
                "experimental_admitted": False,
                "candidate_status": "METADATA_ONLY_UNREVIEWED",
            })
    keys = [(r["story_id"], r["message_id"]) for r in out]
    if len(keys) != len(set(keys)):
        raise Hold("DUPLICATE_TARGET")
    return out


QUERY = """
    SELECT id::text, session_id, turn_index, created_at,
           char_length(content)::integer, status
    FROM public.v2_chat_messages
    WHERE story_id=%s AND role='assistant' AND status='completed'
      AND content IS NOT NULL AND char_length(content) BETWEEN 100 AND 6000
      AND turn_index >= 1
    ORDER BY turn_index DESC, id DESC
    LIMIT %s
"""


def run(dsn, story_ids):
    import psycopg

    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                assert_guard(cur)
                def fetch(story_id):
                    cur.execute(QUERY, (story_id, MAX_PER_STORY))
                    return list(cur.fetchall())
                candidates = screen(fetch, story_ids)
        finally:
            conn.rollback()
    return candidates


def write_private(output: Path, rows, safe):
    if (not output.is_absolute() or not output.is_relative_to(ROOT)
            or output.exists() or output.is_symlink()
            or output.parent != ROOT and (
                output.parent.is_symlink() or not output.parent.is_dir()
                or stat.S_IMODE(output.parent.stat().st_mode) != 0o700)):
        raise Hold("OUTPUT_PATH_INVALID")
    if output.parent == ROOT and (
        not ROOT.is_dir() or stat.S_IMODE(ROOT.stat().st_mode) != 0o700
    ):
        raise Hold("ROOT_PERMISSION_INVALID")
    output.mkdir(mode=0o700)
    for name, payload in (
        ("R60_DUAL_TRACK_CANDIDATES_PRIVATE.jsonl", b"".join(
            (json.dumps(row, ensure_ascii=False, sort_keys=True)+"\\n").encode()
            for row in rows
        )),
        ("R60_DUAL_TRACK_COVERAGE_SAFE.json", (
            json.dumps(safe, ensure_ascii=False, sort_keys=True)+"\\n").encode()),
    ):
        fd = os.open(output/name, os.O_WRONLY|os.O_CREAT|os.O_EXCL
                     |getattr(os,"O_NOFOLLOW",0), 0o600)
        with os.fdopen(fd,"wb") as file:
            file.write(payload)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner-story-scope", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        ids, scope_sha = read_scope(args.owner_story_scope)
        dsn = os.getenv("STORYFORGE_SUPABASE_DSN")
        if not dsn:
            raise Hold("DSN_UNAVAILABLE")
        rows = run(dsn, ids)
        safe = {
            "schema": SCHEMA,
            "status": "OWNER_SCOPED_METADATA_CANDIDATES_NOT_ADMITTED",
            "owner_scoped_stories_checked": len(ids),
            "candidate_metadata_rows": len(rows),
            "stories_with_candidates": len({r["story_id"] for r in rows}),
            "per_story_candidate_cap": MAX_PER_STORY,
            "owner_scope_sha256": scope_sha,
            "request_attempt_linkage_verified": 0,
            "actual_sent_payload_verified": 0,
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
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never output sensitive DB error text
        print(json.dumps({
            "schema": SCHEMA,
            "status": "OWNER_SCOPED_COVERAGE_HOLD",
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
    raise SystemExit(main())
