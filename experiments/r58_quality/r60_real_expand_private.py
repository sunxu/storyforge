"""R60 REAL expansion: paged, immutable, private SFT candidate discovery.

Owner Mac only. Production data stays in 0700/0600 private files.
No R50 body, DB modification, training admission, or GPU operation.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import secrets
import stat
import sys
from pathlib import Path

import r60_real_private_batch as g1

BASE = g1.BASE
SCHEMA = "storyforge_r60_real_expand_private_v1"
PAGE_SCHEMA = "storyforge_r60_real_expand_page_private_v1"
SAFE_SCHEMA = "storyforge_r60_real_expand_safe_v1"
CONFIG_NAME = "R60_EXPAND_CONFIG_PRIVATE.json"
LOCK_NAME = "R60_EXPAND_LOCK_PRIVATE"
MAX_BATCH_BYTES = 5_000_000
MAX_CONFIG_BYTES = 16_000
MAX_PAGES_PER_CALL = 5
MAX_TOTAL = 1000
PAGE_PREFIX = "R60_EXPAND_PAGE_"
PAGE_SUFFIX = "_PRIVATE.json"
MAX_PAGE_SIZE = 25
RECENT_LIMIT = 20
PER_STORY_LIMIT = 4

# Query is keyset-paged over story world roots, not OFFSET-paged. Each selected
# Story advances the cursor even when no replies qualify. Target text stays
# local to the Owner process; no current/historical world snapshot is invented.
SQL = """
WITH eligible AS MATERIALIZED (
 SELECT DISTINCT ON (s.story_id)
        s.story_id,s.session_id,s.total_turns
 FROM public.story_v2_sessions s
 JOIN public.user_stories st ON st.id=s.story_id
 WHERE st.status='published' AND st.deleted_at IS NULL
  AND st.source_type='original' AND st.visibility='private'
  AND s.deleted_at IS NULL AND s.is_archived=false
  AND s.user_id=st.author_id AND s.total_turns>=30
  AND s.parent_session_id IS NULL AND s.forked_from_turn IS NULL
 ORDER BY s.story_id,s.total_turns DESC,s.session_id
), page AS MATERIALIZED (
 SELECT story_id,session_id,md5(story_id) AS sort_key
 FROM eligible
 WHERE (md5(story_id),story_id) > (%s,%s)
 ORDER BY md5(story_id),story_id LIMIT %s
)
SELECT p.story_id,p.session_id,p.sort_key,
 q.aid::text,q.uid::text,q.pid::text,q.puid::text,
 q.turn_index,q.previous_user_text,q.previous_assistant_text,
 q.user_text,q.assistant_text
FROM page p
LEFT JOIN LATERAL (
 SELECT m.id AS aid,u.id AS uid,pa.id AS pid,pu.id AS puid,
        m.turn_index,pu.content AS previous_user_text,
        pa.content AS previous_assistant_text,
        u.content AS user_text,m.content AS assistant_text
 FROM (
   SELECT id,turn_index,content,metadata
   FROM public.v2_chat_messages
   WHERE story_id=p.story_id AND session_id=p.session_id
    AND role='assistant' AND status='completed'
   ORDER BY turn_index DESC,id DESC LIMIT %s
 ) m
 JOIN public.v2_chat_messages u
  ON u.story_id=p.story_id AND u.session_id=p.session_id
  AND u.turn_index=m.turn_index-1
  AND u.role='user' AND u.status='completed'
 JOIN public.v2_chat_messages pa
  ON pa.story_id=p.story_id AND pa.session_id=p.session_id
  AND pa.turn_index=m.turn_index-2
  AND pa.role='assistant' AND pa.status='completed'
 JOIN public.v2_chat_messages pu
  ON pu.story_id=p.story_id AND pu.session_id=p.session_id
  AND pu.turn_index=m.turn_index-3
  AND pu.role='user' AND pu.status='completed'
 WHERE char_length(m.content) BETWEEN 300 AND 1500
  AND char_length(u.content) BETWEEN 1 AND 800
  AND char_length(pa.content) BETWEEN 1 AND 1800
  AND char_length(pu.content) BETWEEN 1 AND 800
  AND m.metadata->>'finishReason' IN ('stop','STOP','end_turn','END_TURN')
  AND NOT (m.metadata ? 'originalContent' OR m.metadata ? 'editedAt'
           OR m.metadata ? 'parseWarnings')
 ORDER BY m.turn_index DESC,m.id DESC LIMIT %s
) q ON TRUE
ORDER BY p.sort_key,p.story_id,q.turn_index DESC NULLS LAST,q.aid
"""


class Hold(ValueError):
    pass


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def private_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def read_secure(path: Path, limit: int) -> bytes:
    return g1.read_private(path, limit)


def check_seed(path: Path) -> tuple[list[dict], str]:
    # Must be the existing, Owner-only R60 single-batch capture, not a new
    # Supabase query, and not a path outside the private tree.
    if (path.name != "R60_REAL_G1_CAPTURE_PRIVATE.jsonl"
            or path.parent.parent != BASE or path.parent.is_symlink()
            or stat.S_IMODE(path.parent.stat().st_mode) != 0o700):
        raise Hold("SEED_PRIVATE_PATH_HOLD")
    raw = read_secure(path, g1.MAX_CAPTURE_BYTES)
    try:
        cases = [json.loads(x) for x in raw.splitlines() if x.strip()]
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Hold("SEED_PRIVATE_JSON_HOLD") from exc
    if len(cases) != 6:
        raise Hold("SEED_SIX_CASES_REQUIRED")
    g1.review_receipt(cases, [])  # source/target SHA and private schema
    if len({x["source"]["assistant_message_id"] for x in cases}) != 6:
        raise Hold("SEED_DUPLICATE_HOLD")
    return cases, sha_bytes(raw)


def page_name(index: int) -> str:
    return f"{PAGE_PREFIX}{index:04d}{PAGE_SUFFIX}"


def create_config(folder: Path, seed: Path, page_size: int,
                  target_total: int) -> dict:
    if not 1 <= page_size <= MAX_PAGE_SIZE or not 20 <= target_total <= MAX_TOTAL:
        raise Hold("CONFIG_BOUNDS_HOLD")
    seeds, checksum = check_seed(seed)
    g1.private_dir(folder, create=True)
    config = {
        "schema": SCHEMA,
        "seed_capture_file": str(seed),
        "seed_sha256": checksum,
        "seed_cases": len(seeds),
        "page_size": page_size,
        "recent_assistants_per_story": RECENT_LIMIT,
        "max_candidates_per_story": PER_STORY_LIMIT,
        "target_total": target_total,
        "sql_sha256": sha_bytes(SQL.encode("utf-8")),
    }
    g1.write_new(folder / CONFIG_NAME, private_bytes(config))
    return {
        "schema": SAFE_SCHEMA, "status": "EXPANSION_INITIALIZED",
        "seed_cases": len(seeds), "new_cases": 0,
        "total_candidates": len(seeds), "target_total": target_total,
        "train_admitted": 0, "database_modified": False,
        "r50_body_accessed": False, "gpu_started": False,
        "private_values_emitted": False,
    }


def validate_config(folder: Path) -> tuple[dict, list[dict]]:
    g1.private_dir(folder, create=False)
    try:
        config = json.loads(read_secure(folder / CONFIG_NAME, MAX_CONFIG_BYTES))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Hold("CONFIG_FORMAT_HOLD") from exc
    if (not isinstance(config, dict) or config.get("schema") != SCHEMA
            or config.get("sql_sha256") != sha_bytes(SQL.encode("utf-8"))
            or config.get("recent_assistants_per_story") != RECENT_LIMIT
            or config.get("max_candidates_per_story") != PER_STORY_LIMIT
            or type(config.get("page_size")) is not int
            or not 1 <= config["page_size"] <= MAX_PAGE_SIZE
            or type(config.get("target_total")) is not int
            or not 20 <= config["target_total"] <= MAX_TOTAL
            or config.get("seed_cases") != 6):
        raise Hold("CONFIG_VERSION_OR_VALUE_HOLD")
    seed_path = Path(config["seed_capture_file"])
    seeds, checksum = check_seed(seed_path)
    if checksum != config["seed_sha256"]:
        raise Hold("SEED_MUTATED_HOLD")
    return config, seeds


def check_case(case: dict) -> tuple[str, str]:
    if (not isinstance(case, dict) or case.get("schema") != g1.CAPTURE_SCHEMA
            or case.get("train_admitted") is not False
            or case.get("target_semantics") != "DB_FINAL_PERSISTED_ASSISTANT"
            or case.get("history_messages_sha256") !=
            g1.digest(case.get("history_messages"))
            or case.get("assistant_target_sha256") !=
            g1.digest(case.get("target_text"))):
        raise Hold("CASE_TAMPER_HOLD")
    src = case.get("source")
    if (not isinstance(src, dict) or not isinstance(src.get("story_id"), str)
            or not isinstance(src.get("assistant_message_id"), str)
            or not src["assistant_message_id"]):
        raise Hold("CASE_SOURCE_HOLD")
    return src["story_id"], src["assistant_message_id"]


def reconstruct(folder: Path, config: dict, seeds: list[dict]) -> dict:
    known = set()
    for case in seeds:
        _, aid = check_case(case)
        if aid in known:
            raise Hold("SEED_DUPLICATE_HOLD")
        known.add(aid)
    count = len(known)
    story_count = 0
    cursor = ["", ""]
    exhausted = False
    index = 0
    seen_stories = set()
    candidates = sorted(folder.glob(f"{PAGE_PREFIX}*{PAGE_SUFFIX}"))
    for file in candidates:
        index += 1
        if index > 100 or file.name != page_name(index) or exhausted:
            raise Hold("PAGE_SEQUENCE_HOLD")
        try:
            page = json.loads(read_secure(file, MAX_BATCH_BYTES))
        except (ValueError, TypeError, UnicodeError) as exc:
            raise Hold("PAGE_FORMAT_HOLD") from exc
        checksum = page.get("page_sha256")
        raw = {key: value for key, value in page.items() if key != "page_sha256"}
        if (page.get("schema") != PAGE_SCHEMA
                or page.get("page_index") != index
                or page.get("cursor_before") != cursor
                or checksum != g1.digest(raw)
                or not isinstance(page.get("stories"), list)
                or not isinstance(page.get("cases"), list)
                or not 0 <= len(page["stories"]) <= config["page_size"]
                or len(page["cases"]) > config["page_size"] * PER_STORY_LIMIT):
            raise Hold("PAGE_CHECKSUM_OR_FORMAT_HOLD")
        stories = page["stories"]
        last_key = tuple(cursor)
        story_set = set()
        for story in stories:
            if (not isinstance(story, dict)
                    or not isinstance(story.get("story_id"), str)
                    or not isinstance(story.get("session_id"), str)
                    or story.get("sort_key") !=
                    hashlib.md5(story["story_id"].encode("utf-8")).hexdigest()):
                raise Hold("PAGE_STORY_FORMAT_HOLD")
            sort = (story["sort_key"], story["story_id"])
            if sort <= last_key or story["story_id"] in seen_stories:
                raise Hold("PAGE_CURSOR_ORDER_HOLD")
            last_key = sort
            story_set.add(story["story_id"])
            seen_stories.add(story["story_id"])
        expected_cursor = list(last_key)
        if page.get("cursor_after") != expected_cursor:
            raise Hold("PAGE_CURSOR_MISMATCH_HOLD")
        if not stories:
            exhausted = True
            if page["cases"]:
                raise Hold("EXHAUSTED_PAGE_WITH_CASES_HOLD")
        per_story = {}
        for case in page["cases"]:
            story, aid = check_case(case)
            if story not in story_set or aid in known:
                raise Hold("CROSS_PAGE_DUPLICATE_OR_STORY_HOLD")
            per_story[story] = per_story.get(story, 0) + 1
            if per_story[story] > PER_STORY_LIMIT:
                raise Hold("PER_STORY_LIMIT_HOLD")
            known.add(aid)
        cursor = expected_cursor
        story_count += len(stories)
        count += len(page["cases"])
        if count > MAX_TOTAL:
            raise Hold("TOTAL_LIMIT_HOLD")
    return {"next_index": index + 1, "cursor": cursor,
            "exhausted": exhausted, "pages": index,
            "stories_scanned": story_count,
            "new_cases": count - len(seeds), "total": count,
            "known_ids": known}


def parse_page_rows(rows: list[tuple], before: list[str], config: dict,
                    known: set[str], remaining: int) -> tuple[list[dict], list[dict], list[str]]:
    if not isinstance(rows, list) or len(rows) > config["page_size"] * PER_STORY_LIMIT:
        raise Hold("RESULT_ROW_LIMIT_HOLD")
    stories = []
    cases = []
    per_story = {}
    previous_story = None
    last_order = tuple(before)
    encountered = set()
    for row in rows:
        if len(row) != 12:
            raise Hold("RESULT_ROW_FORMAT_HOLD")
        story, session, sortkey, aid, uid, pid, puid, turn, pu, pa, user, target = row
        if (not isinstance(story, str) or not isinstance(session, str)
                or not story or not session or
                sortkey != hashlib.md5(story.encode("utf-8")).hexdigest()):
            raise Hold("RESULT_SOURCE_HOLD")
        order = (sortkey, story)
        if order < last_order or (order == last_order and story != previous_story):
            raise Hold("RESULT_SORT_HOLD")
        if story != previous_story:
            if order <= last_order or story in encountered:
                raise Hold("RESULT_CURSOR_HOLD")
            stories.append({"story_id": story, "session_id": session,
                            "sort_key": sortkey})
            encountered.add(story)
            previous_story = story
            last_order = order
        if stories[-1]["session_id"] != session:
            raise Hold("SESSION_ID_MISMATCH_HOLD")
        if aid is None:
            if any(x is not None for x in (uid, pid, puid, turn, pu, pa, user, target)):
                raise Hold("EMPTY_STORY_ROW_INVALID")
            continue
        per_story[story] = per_story.get(story, 0) + 1
        if per_story[story] > PER_STORY_LIMIT:
            raise Hold("PER_STORY_LIMIT_HOLD")
        if aid in known:
            continue
        if len(cases) >= remaining:
            continue
        source_row = (story, session, aid, uid, pid, puid,
                      turn, pu, pa, user, target)
        case = g1.parse_rows([source_row])[0]
        cases.append(case)
        known.add(aid)
    if len(stories) > config["page_size"]:
        raise Hold("RESULT_STORY_LIMIT_HOLD")
    cursor = ([stories[-1]["sort_key"], stories[-1]["story_id"]]
              if stories else before)
    return stories, cases, cursor


def fetch_page(dsn: str, cursor: list[str], config: dict) -> list[tuple]:
    import psycopg

    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as db:
        try:
            with db.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("SET LOCAL statement_timeout='30000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("""
                    SELECT current_user,current_setting('transaction_read_only'),
                           current_setting('row_security'),r.rolbypassrls,r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                """)
                g1.assert_guard(cur.fetchone())
                cur.execute(SQL, (cursor[0], cursor[1], config["page_size"],
                                  RECENT_LIMIT, PER_STORY_LIMIT))
                return cur.fetchall()
        finally:
            db.rollback()


@contextlib.contextmanager
def locked(folder: Path):
    path = folder / LOCK_NAME
    fd = os.open(path, os.O_RDWR | os.O_CREAT |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600:
            raise Hold("LOCK_FILE_PERMISSION_HOLD")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Hold("EXPANSION_ALREADY_RUNNING") from exc
        yield
    finally:
        os.close(fd)


def immutable_page(folder: Path, index: int, content: dict) -> None:
    payload = private_bytes(content)
    if len(payload) > MAX_BATCH_BYTES:
        raise Hold("PAGE_TOO_LARGE_HOLD")
    dest = folder / page_name(index)
    if dest.exists() or dest.is_symlink():
        raise Hold("PAGE_ALREADY_EXISTS")
    temp = folder / (".R60_EXPAND_PAGE_" + secrets.token_hex(12) + ".tmp")
    try:
        g1.write_new(temp, payload)
        with temp.open("rb") as src:
            os.fsync(src.fileno())
        if dest.exists() or dest.is_symlink():
            raise Hold("PAGE_ALREADY_EXISTS")
        os.replace(temp, dest)
        dirfd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if temp.exists():
            temp.unlink()


def safe_summary(config: dict, progress: dict) -> dict:
    status = ("EXPANSION_EXHAUSTED__NOT_ADMITTED" if progress["exhausted"]
              else "EXPANSION_TARGET_REACHED__NOT_ADMITTED"
              if progress["total"] >= config["target_total"]
              else "EXPANSION_IN_PROGRESS__NOT_ADMITTED")
    return {
        "schema": SAFE_SCHEMA, "status": status,
        "seed_cases": config["seed_cases"],
        "new_cases": progress["new_cases"],
        "total_candidates": progress["total"],
        "stories_scanned": progress["stories_scanned"],
        "private_pages": progress["pages"],
        "target_total": config["target_total"],
        "quality_pass": 0, "train_admitted": 0,
        "world_isolation_verified": False,
        "r50_complete_exclusion_verified": False,
        "database_modified": False, "r50_body_accessed": False,
        "gpu_started": False, "private_values_emitted": False,
    }


def advance(folder: Path, dsn: str, max_pages: int) -> dict:
    if not 1 <= max_pages <= MAX_PAGES_PER_CALL:
        raise Hold("PAGE_CALL_LIMIT_HOLD")
    g1.private_dir(folder, create=False)
    with locked(folder):
        config, seeds = validate_config(folder)
        progress = reconstruct(folder, config, seeds)
        for _ in range(max_pages):
            if progress["exhausted"] or progress["total"] >= config["target_total"]:
                break
            rows = fetch_page(dsn, progress["cursor"], config)
            remaining = min(MAX_TOTAL, config["target_total"]) - progress["total"]
            stories, cases, after = parse_page_rows(
                rows, progress["cursor"], config, set(progress["known_ids"]), remaining)
            entry = {
                "schema": PAGE_SCHEMA, "page_index": progress["next_index"],
                "cursor_before": progress["cursor"], "cursor_after": after,
                "stories": stories, "cases": cases,
            }
            entry["page_sha256"] = g1.digest(entry)
            immutable_page(folder, progress["next_index"], entry)
            progress = reconstruct(folder, config, seeds)
        return safe_summary(config, progress)


def inspect(folder: Path) -> dict:
    config, seeds = validate_config(folder)
    with locked(folder):
        return safe_summary(config, reconstruct(folder, config, seeds))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    ini = sub.add_parser("init")
    ini.add_argument("--output-dir", type=Path, required=True)
    ini.add_argument("--seed-capture", type=Path, required=True)
    ini.add_argument("--page-size", type=int, default=20)
    ini.add_argument("--target-total", type=int, default=600)
    adv = sub.add_parser("advance")
    adv.add_argument("--output-dir", type=Path, required=True)
    adv.add_argument("--max-pages", type=int, default=1)
    view = sub.add_parser("inspect")
    view.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "init":
            safe = create_config(args.output_dir, args.seed_capture,
                                 args.page_size, args.target_total)
        elif args.action == "inspect":
            safe = inspect(args.output_dir)
        else:
            dsn = os.getenv("STORYFORGE_SUPABASE_DSN")
            if not dsn:
                raise Hold("DSN_UNAVAILABLE")
            safe = advance(args.output_dir, dsn, args.max_pages)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never leak private values
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "EXPANSION_HOLD",
            "reason_code": str(exc) if isinstance(exc, Hold) else type(exc).__name__,
            "train_admitted": 0, "database_modified": False,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
