"""R60 REAL-02: bounded real-history capture and fail-closed quality receipt.

Capture only in Owner Mac's restricted private directory. Never log story/user
IDs, message content, source hashes, case locators, credentials or file paths.
No DB writes, no R50 body, no train admission, no GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
import sys
from collections import Counter
from pathlib import Path

BASE = Path.home() / ".local/share/storyforge/r60/private"
CAPTURE_SCHEMA = "storyforge_r60_real_private_capture_v1"
REVIEW_SCHEMA = "storyforge_r60_real_independent_review_v1"
SAFE_SCHEMA = "storyforge_r60_real_quality_safe_v1"
FLOORS = {
    "chinese_prose": 4, "character_consistency": 4, "npc_initiative": 3,
    "player_agency": 4, "rule_fidelity": 4, "narrative_continuity": 4,
}
SEVERE = ("serious_player_agency", "hard_fact_or_ban", "safety_exclusion")
MAX_CASES = 6
MAX_CAPTURE_BYTES = 200_000
MAX_REVIEW_BYTES = 80_000

# Bounded sample, with exact adjacent four-message chain and source message IDs.
# Note: no current story cards are selected, and no future turn is included.
SQL = """
WITH eligible AS MATERIALIZED (
  SELECT DISTINCT ON (s.story_id) s.story_id, s.session_id, s.total_turns,
         s.parent_session_id, s.forked_from_turn
  FROM public.story_v2_sessions s
  JOIN public.user_stories st ON st.id=s.story_id
  WHERE st.status='published' AND st.deleted_at IS NULL
    AND st.source_type='original' AND st.visibility='private'
    AND s.deleted_at IS NULL AND s.is_archived=false
    AND s.user_id=st.author_id AND s.total_turns>=30
  ORDER BY s.story_id, s.total_turns DESC, s.session_id
), sampled AS MATERIALIZED (
  SELECT story_id,session_id,parent_session_id,forked_from_turn
  FROM eligible ORDER BY md5(story_id) LIMIT 16
), replies AS MATERIALIZED (
  SELECT c.story_id,c.session_id,m.id AS aid,m.turn_index,
         m.content AS assistant_text,m.metadata,
         char_length(m.content) AS target_chars
  FROM sampled c CROSS JOIN LATERAL (
    SELECT id,turn_index,content,metadata
    FROM public.v2_chat_messages
    WHERE story_id=c.story_id AND session_id=c.session_id
      AND role='assistant' AND status='completed'
    ORDER BY turn_index DESC LIMIT 20
  ) m
  WHERE c.parent_session_id IS NULL AND c.forked_from_turn IS NULL
), qualified AS (
  SELECT r.*,u.id AS uid,u.content AS user_text,
         p.id AS pid,p.content AS previous_assistant_text,
         pu.id AS puid,pu.content AS previous_user_text,
         row_number() OVER (PARTITION BY r.story_id
                           ORDER BY r.turn_index DESC) AS story_rank
  FROM replies r
  JOIN public.v2_chat_messages u
    ON u.story_id=r.story_id AND u.session_id=r.session_id
   AND u.turn_index=r.turn_index-1
   AND u.role='user' AND u.status='completed'
  JOIN public.v2_chat_messages p
    ON p.story_id=r.story_id AND p.session_id=r.session_id
   AND p.turn_index=r.turn_index-2
   AND p.role='assistant' AND p.status='completed'
  JOIN public.v2_chat_messages pu
    ON pu.story_id=r.story_id AND pu.session_id=r.session_id
   AND pu.turn_index=r.turn_index-3
   AND pu.role='user' AND pu.status='completed'
  WHERE r.target_chars BETWEEN 300 AND 1500
    AND r.metadata->>'finishReason' IN ('stop','STOP','end_turn','END_TURN')
    AND NOT (r.metadata ? 'originalContent' OR r.metadata ? 'editedAt'
             OR r.metadata ? 'parseWarnings')
    AND char_length(u.content) BETWEEN 1 AND 800
    AND char_length(p.content) BETWEEN 1 AND 1800
    AND char_length(pu.content) BETWEEN 1 AND 800
)
SELECT story_id, session_id, aid::text, uid::text, pid::text, puid::text,
       turn_index, previous_user_text, previous_assistant_text,
       user_text, assistant_text
FROM qualified WHERE story_rank=1 ORDER BY story_id LIMIT 6
"""


class Hold(ValueError):
    pass


def digest(value: object) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def assert_guard(row: tuple) -> None:
    if row != ("r58_export_reader", "on", "on", False, False):
        raise Hold("DATABASE_GUARD_HOLD")


def parse_rows(rows: list[tuple]) -> list[dict]:
    if not 1 <= len(rows) <= MAX_CASES:
        raise Hold("CAPTURE_COUNT_HOLD")
    cases = []
    unique_stories, unique_targets = set(), set()
    for row in rows:
        if len(row) != 11:
            raise Hold("SOURCE_ROW_FORMAT_HOLD")
        story, session, aid, uid, pid, puid, turn, pu, pa, user, target = row
        if (not all(isinstance(x, str) and x for x in
                    (story, session, aid, uid, pid, puid, pu, pa, user, target))
                or type(turn) is not int or turn < 4
                or len(target) < 300 or len(target) > 1500
                or len(user) > 800 or len(pa) > 1800 or len(pu) > 800):
            raise Hold("SOURCE_ROW_CONTENT_OR_BOUND_HOLD")
        if story in unique_stories or aid in unique_targets:
            raise Hold("DUPLICATE_STORY_OR_TARGET_HOLD")
        unique_stories.add(story)
        unique_targets.add(aid)
        history = [
            {"role": "user", "content": pu},
            {"role": "assistant", "content": pa},
            {"role": "user", "content": user},
        ]
        cases.append({
            "schema": CAPTURE_SCHEMA,
            "case_key": secrets.token_hex(12),
            "source": {
                "story_id": story, "session_id": session,
                "assistant_message_id": aid, "prior_user_message_id": uid,
                "previous_assistant_message_id": pid,
                "previous_user_message_id": puid,
                "assistant_turn_index": turn,
            },
            "history_messages": history,
            "target_text": target,
            "history_messages_sha256": digest(history),
            "assistant_target_sha256": digest(target),
            "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
            "historical_system_provenance": "UNKNOWN_NOT_ACTUAL_SENT",
            "normalized_system_provenance": "RECONSTRUCTED_NOT_ACTUAL_SENT",
            "quality_status": "UNREVIEWED",
            "world_component_status": "UNKNOWN_HOLD",
            "r50_complete_exclusion_status": "UNKNOWN_HOLD",
            "train_admitted": False,
        })
    return cases


def fetch(dsn: str) -> list[dict]:
    import psycopg

    with psycopg.connect(dsn, autocommit=False, connect_timeout=10) as db:
        try:
            with db.cursor() as cur:
                cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout='20000ms'")
                cur.execute("SET LOCAL lock_timeout='1000ms'")
                cur.execute("SET LOCAL row_security=on")
                cur.execute("""
                    SELECT current_user,current_setting('transaction_read_only'),
                           current_setting('row_security'),r.rolbypassrls,r.rolsuper
                    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                """)
                assert_guard(cur.fetchone())
                cur.execute(SQL)
                return parse_rows(cur.fetchall())
        finally:
            db.rollback()


def private_dir(path: Path, *, create: bool) -> None:
    if (not path.is_absolute() or not path.is_relative_to(BASE)
            or path.parent != BASE or path.is_symlink()
            or BASE.is_symlink() or not BASE.is_dir()
            or stat.S_IMODE(BASE.stat().st_mode) != 0o700):
        raise Hold("PRIVATE_DIR_GUARD_HOLD")
    if create:
        if path.exists():
            raise Hold("OUTPUT_EXISTS_HOLD")
        path.mkdir(mode=0o700)
    if (not path.is_dir() or stat.S_IMODE(path.stat().st_mode) != 0o700):
        raise Hold("PRIVATE_DIR_GUARD_HOLD")


def write_new(path: Path, data: bytes) -> None:
    if len(data) > MAX_CAPTURE_BYTES:
        raise Hold("OUTPUT_SIZE_HOLD")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as dest:
        dest.write(data)


def read_private(path: Path, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Hold("INPUT_FILE_GUARD_HOLD")
    st = path.stat()
    if (stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
            or st.st_size <= 0 or st.st_size > max_bytes):
        raise Hold("INPUT_FILE_GUARD_HOLD")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as src:
        return src.read(max_bytes + 1)


def encode_lines(rows: list[dict]) -> bytes:
    return b"".join((json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n").encode()
                    for r in rows)


def capture(directory: Path, dsn: str) -> dict:
    # Refuse an existing path before doing a production read.
    if directory.exists():
        raise Hold("OUTPUT_EXISTS_HOLD")
    # Check the private parent before touching DB.
    if (directory.parent != BASE or BASE.is_symlink()
            or not BASE.is_dir() or stat.S_IMODE(BASE.stat().st_mode) != 0o700):
        raise Hold("PRIVATE_DIR_GUARD_HOLD")
    cases = fetch(dsn)
    private_dir(directory, create=True)
    write_new(directory / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl", encode_lines(cases))
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "EXACT_G1_CAPTURED__INDEPENDENT_REVIEW_PENDING",
        "cases_captured": len(cases),
        "distinct_stories": len(cases),
        "quality_pass": 0, "train_admitted": 0,
        "r50_exclusion_verified": 0, "world_component_verified": 0,
        "r50_body_accessed": False, "database_modified": False,
        "gpu_started": False, "private_values_emitted": False,
    }
    write_new(directory / "R60_REAL_G1_CAPTURE_SAFE.json", (
        json.dumps(safe, sort_keys=True) + "\n").encode())
    return safe


def validated_review(review: object, case: dict) -> tuple[str, str]:
    if not isinstance(review, dict) or review.get("schema") != REVIEW_SCHEMA:
        return "HOLD", "REVIEW_SCHEMA_HOLD"
    if (review.get("case_key") != case["case_key"]
            or review.get("assistant_target_sha256") != case["assistant_target_sha256"]
            or review.get("history_messages_sha256") != case["history_messages_sha256"]):
        return "HOLD", "REVIEW_SOURCE_MISMATCH"
    entries = review.get("reviews")
    if not isinstance(entries, list) or len(entries) != 2:
        return "HOLD", "TWO_INDEPENDENT_REVIEWS_REQUIRED"
    reviewer_keys = []
    for entry in entries:
        if not isinstance(entry, dict):
            return "HOLD", "REVIEW_FORMAT_HOLD"
        key = entry.get("reviewer_key")
        if not isinstance(key, str) or not key.strip():
            return "HOLD", "REVIEW_FORMAT_HOLD"
        reviewer_keys.append(key)
    if len(set(reviewer_keys)) != 2:
        return "HOLD", "REVIEWER_NOT_DISTINCT"
    for entry in entries:
        flags = entry.get("severe_flags")
        if (not isinstance(flags, dict) or set(flags) != set(SEVERE)
                or any(type(flags[f]) is not bool for f in SEVERE)):
            return "HOLD", "SERIOUS_FLAGS_UNVERIFIED"
        if any(flags.values()) or entry.get("decision") == "REJECT":
            return "REJECT", "SEVERE_OR_REVIEWER_REJECT"
    for entry in entries:
        scores = entry.get("scores")
        if (entry.get("decision") != "PASS"
                or not isinstance(entry.get("private_evidence_ref"), str)
                or not entry["private_evidence_ref"].strip()
                or not isinstance(scores, dict) or set(scores) != set(FLOORS)
                or any(type(scores[k]) is not int or not 1 <= scores[k] <= 5
                       for k in FLOORS)):
            return "HOLD", "REVIEW_INCOMPLETE"
        if any(scores[k] < FLOORS[k] for k in FLOORS):
            return "HOLD", "BELOW_QUALITY_FLOOR"
    if review.get("reviewers_independent_owner_attested") is not True:
        return "HOLD", "INDEPENDENCE_NOT_ATTESTED"
    return "PASS", "DUAL_REVIEW_QUALITY_ONLY"


def review_receipt(cases: list[dict], reviews: list[dict]) -> dict:
    if not 1 <= len(cases) <= MAX_CASES:
        raise Hold("CASE_COUNT_HOLD")
    case_map = {c.get("case_key"): c for c in cases
                if isinstance(c, dict) and c.get("schema") == CAPTURE_SCHEMA}
    if len(case_map) != len(cases):
        raise Hold("CAPTURE_SCHEMA_OR_DUPLICATE_HOLD")
    for c in cases:
        if (c.get("target_semantics") != "DB_FINAL_PERSISTED_ASSISTANT"
                or c.get("train_admitted") is not False
                or c.get("history_messages_sha256") != digest(c.get("history_messages"))
                or c.get("assistant_target_sha256") != digest(c.get("target_text"))):
            raise Hold("CAPTURE_TAMPER_HOLD")
    if len(reviews) > len(cases):
        raise Hold("REVIEW_COUNT_HOLD")
    review_map = {}
    for review in reviews:
        if not isinstance(review, dict) or review.get("case_key") not in case_map:
            raise Hold("UNKNOWN_REVIEW_CASE_HOLD")
        if review["case_key"] in review_map:
            raise Hold("DUPLICATE_REVIEW_HOLD")
        review_map[review["case_key"]] = review
    counts, reasons = Counter(), Counter()
    for key, case in case_map.items():
        result, reason = validated_review(review_map.get(key), case)
        counts[result] += 1
        if result != "PASS":
            reasons[reason] += 1
    return {
        "schema": SAFE_SCHEMA,
        "status": "DUAL_REVIEW_AGGREGATED__TRAIN_ADMISSION_HOLD",
        "cases_captured": len(cases),
        "review_decisions": {x: counts[x] for x in ("PASS", "HOLD", "REJECT")},
        "hold_reject_codes": dict(sorted(reasons.items())),
        "reviewer_independence_independently_proven_by_script": False,
        "r50_complete_exclusion_verified": False,
        "world_components_verified": False,
        "historical_system_snapshot_verified": False,
        "train_admitted": 0, "private_values_emitted": False,
        "database_modified": False, "r50_body_accessed": False,
        "gpu_started": False,
    }


def create_review_template(directory: Path) -> dict:
    """Create unfilled private review envelopes; never invent scores or approval."""
    private_dir(directory, create=False)
    raw = read_private(directory / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl",
                       MAX_CAPTURE_BYTES)
    try:
        cases = [json.loads(x) for x in raw.splitlines() if x.strip()]
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Hold("PRIVATE_JSONL_FORMAT_HOLD") from exc
    # Reuse source-hash and count checks before producing review forms.
    review_receipt(cases, [])
    entries = [{
        "schema": REVIEW_SCHEMA,
        "case_key": case["case_key"],
        "assistant_target_sha256": case["assistant_target_sha256"],
        "history_messages_sha256": case["history_messages_sha256"],
        "reviewers_independent_owner_attested": False,
        "reviews": [],
    } for case in cases]
    write_new(directory / "R60_REAL_G1_REVIEWS_PRIVATE.jsonl",
              encode_lines(entries))
    return {"schema": SAFE_SCHEMA,
            "status": "PRIVATE_REVIEW_TEMPLATE_CREATED__REVIEWS_UNFILLED",
            "review_templates": len(entries), "train_admitted": 0,
            "private_values_emitted": False,
            "database_modified": False, "gpu_started": False}


def review(directory: Path, review_file: Path) -> dict:
    private_dir(directory, create=False)
    if review_file.parent != directory:
        raise Hold("PRIVATE_REVIEW_PATH_HOLD")
    capture_bytes = read_private(directory / "R60_REAL_G1_CAPTURE_PRIVATE.jsonl",
                                 MAX_CAPTURE_BYTES)
    review_bytes = read_private(review_file, MAX_REVIEW_BYTES)
    try:
        cases = [json.loads(x) for x in capture_bytes.splitlines() if x.strip()]
        reviews = [json.loads(x) for x in review_bytes.splitlines() if x.strip()]
    except (ValueError, TypeError, UnicodeError) as exc:
        raise Hold("PRIVATE_JSONL_FORMAT_HOLD") from exc
    safe = review_receipt(cases, reviews)
    write_new(directory / "R60_REAL_G1_REVIEW_SAFE.json", (
        json.dumps(safe, sort_keys=True) + "\n").encode())
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    cap = modes.add_parser("capture")
    cap.add_argument("--output-dir", type=Path, required=True)
    temp = modes.add_parser("template")
    temp.add_argument("--capture-dir", type=Path, required=True)
    rev = modes.add_parser("review")
    rev.add_argument("--capture-dir", type=Path, required=True)
    rev.add_argument("--reviews", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "capture":
            dsn = os.getenv("STORYFORGE_SUPABASE_DSN")
            if not dsn:
                raise Hold("DSN_UNAVAILABLE")
            safe = capture(args.output_dir, dsn)
        elif args.mode == "template":
            safe = create_review_template(args.capture_dir)
        else:
            safe = review(args.capture_dir, args.reviews)
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - redact DB exceptions, paths, text
        print(json.dumps({"schema": SAFE_SCHEMA,
                          "status": "R60_REAL_PRIVATE_PIPELINE_HOLD",
                          "reason_code": (str(exc) if isinstance(exc, Hold)
                                          else type(exc).__name__),
                          "train_admitted": 0,
                          "private_values_emitted": False,
                          "database_modified": False,
                          "gpu_started": False}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
