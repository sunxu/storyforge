"""Gold192 adapter for the shared R59 historical recovery core.

Read-only source reconstruction only. It does not grant Quality-v1 admission,
compile SFT data, access R50, or start HF/GPU work.
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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from experiments.r58_quality.r59_gold192_supabase_extract import (  # noqa: E402
    A_SHA, B_SHA, EX_SHA, PACKETS_SHA, choose_pilot, index_packets,
    select_candidates,
)
from storyforge_gold_quality.history_recovery import recover_cases  # noqa: E402

MAX_INPUT_BYTES = 160 * 1024 * 1024


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def private_bytes(path: Path, label: str) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"{label}_PATH_INVALID")
    if any(parent.is_symlink() for parent in path.parents if parent.exists()):
        raise ValueError(f"{label}_PARENT_SYMLINK")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(f"{label}_PERMISSIONS_INVALID")
    if info.st_size <= 0 or info.st_size > MAX_INPUT_BYTES:
        raise ValueError(f"{label}_SIZE_INVALID")
    if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise ValueError(f"{label}_PARENT_PERMISSIONS_INVALID")
    return path.read_bytes()


def parse_json(raw: bytes, label: str):
    try:
        value = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError(f"{label}_JSON_INVALID") from None
    if not isinstance(value, dict):
        raise ValueError(f"{label}_SHAPE_INVALID")
    return value


def parse_jsonl(raw: bytes, label: str) -> list[dict]:
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError(f"{label}_JSON_INVALID") from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{label}_SHAPE_INVALID")
    return rows


def validate_source_receipt(safe: dict, locators_raw: bytes) -> None:
    if (safe.get("schema") != "r59_gold192_supabase_extract_safe_v1"
            or safe.get("status") != "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED"
            or safe.get("gold192") != 192
            or safe.get("quality_v1_admitted") != 0
            or safe.get("training_authorized") is not False
            or safe.get("gpu_started") is not False
            or safe.get("private_values_emitted") is not False):
        raise ValueError("SOURCE_SAFE_RECEIPT_INVALID")
    artifact = safe.get("artifacts", {}).get("R59_SOURCE_LOCATORS_192.jsonl")
    if (not isinstance(artifact, dict) or artifact.get("records") != 192
            or artifact.get("sha256") != digest(locators_raw)):
        raise ValueError("SOURCE_LOCATOR_PIN_MISMATCH")


def index_source_packets(rows: list[dict]) -> dict[str, dict]:
    """Expand the frozen 13 story-level packet rows into 192 unique case identities."""
    if len(rows) != 13:
        raise ValueError("SOURCE_PACKET_STORY_COUNT_INVALID")
    indexed = index_packets(rows)
    if len(indexed) != 192:
        raise ValueError("SOURCE_PACKET_COUNT_INVALID")
    return indexed


def validate_locators(rows: list[dict], packets: dict[str, dict]) -> dict[str, dict]:
    case_ids = [row.get("case_id") for row in rows if isinstance(row, dict)]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("SOURCE_LOCATOR_IDENTITY_INVALID")
    if len(rows) != len(packets):
        raise ValueError("SOURCE_LOCATOR_COUNT_INVALID")
    indexed = {}
    for row in rows:
        case_id = row.get("case_id")
        source = packets.get(case_id)
        if (not isinstance(case_id, str) or source is None
                or row.get("target_sha256") != source["target_sha256"]
                or row.get("story_id") != source["story_id"]
                or row.get("turn_index") != source["turn_index"]
                or case_id in indexed):
            raise ValueError("SOURCE_LOCATOR_IDENTITY_INVALID")
        indexed[case_id] = row
    if set(indexed) != set(packets):
        raise ValueError("SOURCE_LOCATOR_SET_MISMATCH")
    return indexed


class PilotSourceIdentityHold(ValueError):
    def __init__(self, counts: Counter, safe_indices: list[dict]):
        self.counts = dict(sorted(counts.items()))
        self.safe_indices = safe_indices
        super().__init__("PILOT_SOURCE_IDENTITY_HOLD")


def build_recovery_cases(
    priority: list[dict], locator_index: dict[str, dict],
    verified_duplicate_indices: set[int] | None = None,
) -> list[dict]:
    cases = []
    verified_duplicate_indices = verified_duplicate_indices or set()
    held_source = Counter()
    held_indices = []
    for pilot_index, case in enumerate(priority):
        locator = locator_index[case["case_id"]]
        if locator.get("source_status") != "EXACT_MATCH":
            reason = str(locator.get("source_status", "SOURCE_STATUS_MISSING"))
            held_source[reason] += 1
            held_indices.append({"pilot_index": pilot_index, "reason": reason})
            continue
        match_count = locator.get("matched_message_count")
        if match_count != 1 and not (
            match_count >= 2 and pilot_index in verified_duplicate_indices
        ):
            held_source["SOURCE_MATCH_COUNT_NOT_UNIQUE"] += 1
            held_indices.append({
                "pilot_index": pilot_index,
                "reason": "SOURCE_MATCH_COUNT_NOT_UNIQUE",
                "matched_message_count": match_count,
            })
            continue
        session_id = locator.get("session_id")
        message_id = locator.get("message_id")
        if (not isinstance(session_id, str) or not session_id
                or not isinstance(message_id, str) or not message_id):
            held_source["SOURCE_LOCATOR_INCOMPLETE"] += 1
            held_indices.append({
                "pilot_index": pilot_index,
                "reason": "SOURCE_LOCATOR_INCOMPLETE",
            })
            continue
        cases.append({
            "case_id": case["case_id"], "story_id": case["story_id"],
            "session_id": session_id, "turn_index": case["turn_index"],
            "target_sha256": case["target_sha256"],
        })
    if held_source:
        raise PilotSourceIdentityHold(held_source, held_indices)
    if len(cases) != len(priority):
        raise ValueError("PILOT_CASE_COUNT_INVALID")
    if len({(row["story_id"], row["session_id"], row["turn_index"]) for row in cases}) != len(cases):
        raise ValueError("PILOT_TARGET_LOCATOR_DUPLICATE")
    return cases


def verify_story_owner_scope(cursor, story_ids: list[str]) -> int:
    if len(story_ids) != 13 or len(set(story_ids)) != 13:
        raise ValueError("STORY_SCOPE_INVALID")
    cursor.execute(
        """
        SELECT id::text AS story_id, author_id::text AS owner_id
        FROM public.user_stories
        WHERE id::text = ANY(%s)
        """,
        (story_ids,),
    )
    rows = cursor.fetchall()
    if len(rows) != len(story_ids):
        raise ValueError("STORY_OWNER_SCOPE_INCOMPLETE")
    seen = set()
    owners = set()
    for row in rows:
        if isinstance(row, dict):
            story_id, user_id = row.get("story_id"), row.get("owner_id")
        elif isinstance(row, (tuple, list)) and len(row) == 2:
            story_id, user_id = row
        else:
            raise ValueError("STORY_OWNER_ROW_SHAPE_INVALID")
        if not isinstance(story_id, str) or story_id in seen:
            raise ValueError("STORY_OWNER_STORY_ID_INVALID")
        if not isinstance(user_id, str) or not re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
                user_id):
            raise ValueError("STORY_OWNER_ID_INVALID")
        seen.add(story_id)
        owners.add(user_id.lower())
    if seen != set(story_ids) or not owners:
        raise ValueError("STORY_OWNER_SCOPE_INCOMPLETE")
    return len(owners)


def create_only(path: Path, payload: bytes) -> str:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return digest(payload)


def jsonl_bytes(rows: list[dict]) -> bytes:
    return b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        for row in rows
    )


def summarize_duplicate_identity(
    locator: dict, exact_matches: list[dict], lineage_rows: list[dict],
    max_lineage_depth: int,
) -> dict:
    """Return aggregate-only proof that duplicate exact matches share one canonical root."""
    expected = locator.get("matched_message_count")
    if (not isinstance(expected, int) or isinstance(expected, bool)
            or expected < 2 or len(exact_matches) != expected):
        return {"status": "HOLD", "reason": "SOURCE_MATCH_COUNT_CHANGED"}
    message_ids = [row.get("message_id") for row in exact_matches]
    session_ids = [row.get("session_id") for row in exact_matches]
    if (any(not isinstance(value, str) or not value for value in message_ids + session_ids)
            or len(set(message_ids)) != len(message_ids)):
        return {"status": "HOLD", "reason": "DUPLICATE_MESSAGE_ID_OR_LOCATOR_INVALID"}

    parents = {}
    for row in lineage_rows:
        session_id = row.get("session_id")
        parent_id = row.get("parent_session_id")
        if not isinstance(session_id, str) or not session_id or session_id in parents:
            return {"status": "HOLD", "reason": "SESSION_LINEAGE_ROWS_INVALID"}
        if parent_id is not None and (not isinstance(parent_id, str) or not parent_id):
            return {"status": "HOLD", "reason": "SESSION_LINEAGE_PARENT_INVALID"}
        parents[session_id] = parent_id

    roots = set()
    max_depth_seen = 0
    lineage_complete = True
    cycle_detected = False
    for start in set(session_ids):
        current = start
        seen = set()
        depth = 0
        while True:
            if current in seen:
                cycle_detected = True
                lineage_complete = False
                break
            seen.add(current)
            if current not in parents:
                lineage_complete = False
                break
            parent_id = parents[current]
            if parent_id is None:
                roots.add(current)
                max_depth_seen = max(max_depth_seen, depth)
                break
            depth += 1
            if depth > max_lineage_depth:
                lineage_complete = False
                break
            current = parent_id

    root_message_count = sum(
        1 for row in exact_matches if row.get("session_id") in roots
    )
    one_root = len(roots) == 1
    canonical_locator_matches = False
    if one_root:
        root_id = next(iter(roots))
        root_rows = [row for row in exact_matches if row.get("session_id") == root_id]
        canonical_locator_matches = (
            len(root_rows) == 1
            and locator.get("session_id") == root_id
            and locator.get("message_id") == root_rows[0].get("message_id")
        )
    accepted = (
        lineage_complete and not cycle_detected and one_root
        and root_message_count == 1 and canonical_locator_matches
    )
    return {
        "status": "UNIQUE_ROOT_CANONICAL_MATCH" if accepted else "HOLD",
        "reason": "UNIQUE_ROOT_CANONICAL_MATCH" if accepted else "ROOT_LINEAGE_NOT_UNAMBIGUOUS",
        "exact_match_count": len(exact_matches),
        "distinct_message_count": len(set(message_ids)),
        "distinct_match_session_count": len(set(session_ids)),
        "unique_root_session_count": len(roots),
        "exact_matches_in_root_session": root_message_count,
        "lineage_complete": lineage_complete,
        "lineage_cycle_detected": cycle_detected,
        "lineage_max_depth": max_depth_seen,
        "canonical_locator_matches_root": canonical_locator_matches,
    }


def diagnose_duplicate_source(cursor, case: dict, locator: dict,
                              max_lineage_depth: int) -> dict:
    if locator.get("source_status") != "EXACT_MATCH":
        raise ValueError("DUPLICATE_SOURCE_STATUS_INVALID")
    if locator.get("matched_message_count", 0) < 2:
        raise ValueError("DUPLICATE_SOURCE_NOT_PRESENT")
    cursor.execute(
        """
        SELECT m.id::text AS message_id, m.session_id::text AS session_id,
               m.content, s.parent_session_id::text AS parent_session_id
        FROM public.v2_chat_messages AS m
        JOIN public.story_v2_sessions AS s
          ON s.story_id = m.story_id AND s.session_id = m.session_id
        WHERE m.story_id = %s AND m.turn_index = %s AND m.role = 'assistant'
        ORDER BY m.id
        """,
        (case["story_id"], case["turn_index"]),
    )
    exact_matches = []
    for row in cursor.fetchall():
        message_id, session_id, content, _parent_session_id = row
        if isinstance(content, str) and digest(content.encode("utf-8")) == case["target_sha256"]:
            exact_matches.append({"message_id": message_id, "session_id": session_id})
    if len(exact_matches) != locator.get("matched_message_count"):
        raise ValueError("DUPLICATE_SOURCE_MATCH_COUNT_DRIFT")
    session_ids = sorted({row["session_id"] for row in exact_matches})
    cursor.execute(
        """
        WITH RECURSIVE lineage AS (
            SELECT s.story_id::text AS story_id, s.session_id::text AS session_id,
                   s.parent_session_id::text AS parent_session_id, 0 AS depth,
                   ARRAY[s.session_id::text] AS path, false AS cycle
            FROM public.story_v2_sessions AS s
            WHERE s.story_id::text = %s AND s.session_id::text = ANY(%s)
            UNION ALL
            SELECT p.story_id::text, p.session_id::text,
                   p.parent_session_id::text, l.depth + 1,
                   l.path || p.session_id::text,
                   p.session_id::text = ANY(l.path)
            FROM lineage AS l
            JOIN public.story_v2_sessions AS p
              ON p.story_id::text = l.story_id
             AND p.session_id::text = l.parent_session_id
            WHERE l.depth < %s AND NOT l.cycle
        )
        SELECT DISTINCT session_id, parent_session_id
        FROM lineage
        """,
        (case["story_id"], session_ids, max_lineage_depth),
    )
    lineage_rows = [
        {"session_id": row[0], "parent_session_id": row[1]}
        for row in cursor.fetchall()
    ]
    return summarize_duplicate_identity(
        locator, exact_matches, lineage_rows, max_lineage_depth
    )


def run(*, reviewer_a: Path, reviewer_b: Path, exclusions: Path,
        source_packets: Path, source_locators: Path, source_safe: Path,
        output_dir: Path, dsn: str, pilot: int = 8,
        max_history: int = 20000, max_lineage_depth: int = 16,
        max_ledger_events: int = 100000, diagnostic_only: bool = False,
        diagnose_duplicate_index: int | None = None) -> dict:
    inputs = {
        "REVIEWER_A": private_bytes(reviewer_a, "REVIEWER_A"),
        "REVIEWER_B": private_bytes(reviewer_b, "REVIEWER_B"),
        "EXCLUSIONS": private_bytes(exclusions, "EXCLUSIONS"),
        "SOURCE_PACKETS": private_bytes(source_packets, "SOURCE_PACKETS"),
        "SOURCE_LOCATORS": private_bytes(source_locators, "SOURCE_LOCATORS"),
        "SOURCE_SAFE": private_bytes(source_safe, "SOURCE_SAFE"),
    }
    if source_locators.parent.resolve(strict=True) != source_safe.parent.resolve(strict=True):
        raise ValueError("SOURCE_ARTIFACTS_NOT_SAME_RUN")
    safe_receipt = parse_json(inputs["SOURCE_SAFE"], "SOURCE_SAFE")
    validate_source_receipt(safe_receipt, inputs["SOURCE_LOCATORS"])

    # Retain the already frozen source pins and candidate-selection contract.
    if digest(inputs["REVIEWER_A"]) != A_SHA:
        raise ValueError("REVIEWER_A_SHA_MISMATCH")
    if digest(inputs["REVIEWER_B"]) != B_SHA:
        raise ValueError("REVIEWER_B_SHA_MISMATCH")
    if digest(inputs["EXCLUSIONS"]) != EX_SHA:
        raise ValueError("EXCLUSIONS_SHA_MISMATCH")
    if digest(inputs["SOURCE_PACKETS"]) != PACKETS_SHA:
        raise ValueError("SOURCE_PACKETS_SHA_MISMATCH")

    a = json.loads(inputs["REVIEWER_A"])
    b = json.loads(inputs["REVIEWER_B"])
    excluded = [json.loads(line) for line in inputs["EXCLUSIONS"].splitlines() if line.strip()]
    packet_rows = parse_jsonl(inputs["SOURCE_PACKETS"], "SOURCE_PACKETS")
    packet_index = index_source_packets(packet_rows)
    selected = select_candidates(a, b, excluded, packet_index)
    priority = choose_pilot(selected, pilot)
    locator_index = validate_locators(
        parse_jsonl(inputs["SOURCE_LOCATORS"], "SOURCE_LOCATORS"), packet_index
    )

    if diagnostic_only and diagnose_duplicate_index is not None:
        raise ValueError("DIAGNOSTIC_MODE_CONFLICT")
    if diagnostic_only:
        cases = build_recovery_cases(priority, locator_index)
        return {
            "schema": "r59_gold192_source_identity_diagnostic_safe_v1",
            "status": "PILOT_SOURCE_IDENTITY_PREFLIGHT_PASS__NO_DATABASE",
            "pilot_requested": len(priority),
            "pilot_identity_valid": len(cases),
            "database_connected": False,
            "database_modified": False,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
        }

    if diagnose_duplicate_index is not None:
        if not 0 <= diagnose_duplicate_index < len(priority):
            raise ValueError("DUPLICATE_DIAGNOSTIC_INDEX_INVALID")
        case = priority[diagnose_duplicate_index]
        locator = locator_index[case["case_id"]]
        if locator.get("matched_message_count", 0) < 2:
            raise ValueError("DUPLICATE_SOURCE_NOT_PRESENT")
        import psycopg

        stage = "CONNECT"
        try:
            with psycopg.connect(dsn, autocommit=False, connect_timeout=15) as db:
                stage = "SET_READ_ONLY"
                db.execute("SET TRANSACTION READ ONLY")
                stage = "SET_STATEMENT_TIMEOUT"
                db.execute("SET LOCAL statement_timeout = '90000ms'")
                stage = "SET_LOCK_TIMEOUT"
                db.execute("SET LOCAL lock_timeout = '1000ms'")
                stage = "VERIFY_READ_ONLY_ROLE"
                with db.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT current_user, current_setting('transaction_read_only'),
                               current_setting('row_security'), r.rolsuper, r.rolbypassrls
                        FROM pg_roles AS r WHERE r.rolname = current_user
                        """
                    )
                    role = cursor.fetchone()
                    if (role is None or role[0] != "r58_export_reader"
                            or role[1] != "on" or role[2] != "on"
                            or role[3] is not False or role[4] is not False):
                        raise ValueError("DATABASE_ROLE_NOT_APPROVED")
                    stage = "DUPLICATE_LINEAGE_DIAGNOSTIC"
                    diagnostic = diagnose_duplicate_source(
                        cursor, case, locator, max_lineage_depth
                    )
                stage = "ROLLBACK"
                db.rollback()
        except psycopg.Error as exc:
            sqlstate = getattr(exc, "sqlstate", None)
            if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
                sqlstate = None
            raise DatabaseFailure(stage, sqlstate, type(exc).__name__) from None
        return {
            "schema": "r59_gold192_duplicate_source_diagnostic_safe_v1",
            **diagnostic,
            "status": ("DUPLICATE_SOURCE_CANONICAL_ROOT_PROVEN__NO_ADMISSION"
                       if diagnostic["status"] == "UNIQUE_ROOT_CANONICAL_MATCH"
                       else "DUPLICATE_SOURCE_LINEAGE_HOLD"),
            "pilot_index": diagnose_duplicate_index,
            "database_role_verified": "r58_export_reader",
            "transaction_read_only": True,
            "row_security": True,
            "role_bypassrls": False,
            "database_modified": False,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
        }

    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700):
        raise ValueError("OUTPUT_PARENT_PERMISSIONS_INVALID")
    repo_root = ROOT.resolve(strict=True)
    parent = output_dir.parent.resolve(strict=True)
    if parent == repo_root or repo_root in parent.parents:
        raise ValueError("OUTPUT_MUST_REMAIN_PRIVATE")

    verified_duplicate_indices: set[int] = set()
    import psycopg

    stage = "CONNECT"
    try:
        with psycopg.connect(dsn, autocommit=False, connect_timeout=15) as db:
            stage = "SET_READ_ONLY"
            db.execute("SET TRANSACTION READ ONLY")
            stage = "SET_STATEMENT_TIMEOUT"
            db.execute("SET LOCAL statement_timeout = '90000ms'")
            stage = "SET_LOCK_TIMEOUT"
            db.execute("SET LOCAL lock_timeout = '1000ms'")
            stage = "RECOVERY_QUERIES"
            with db.cursor() as cursor:
                owner_count = verify_story_owner_scope(
                    cursor, sorted({case["story_id"] for case in packet_index.values()})
                )
                for pilot_index, case in enumerate(priority):
                    locator = locator_index[case["case_id"]]
                    if locator.get("matched_message_count") == 1:
                        continue
                    if locator.get("matched_message_count", 0) < 2:
                        raise ValueError("SOURCE_MATCH_COUNT_INVALID")
                    duplicate_proof = diagnose_duplicate_source(
                        cursor, case, locator, max_lineage_depth
                    )
                    if duplicate_proof.get("status") != "UNIQUE_ROOT_CANONICAL_MATCH":
                        raise ValueError("PILOT_SOURCE_IDENTITY_HOLD")
                    verified_duplicate_indices.add(pilot_index)
                cases = build_recovery_cases(
                    priority, locator_index, verified_duplicate_indices
                )
                recovered = recover_cases(
                    cursor, cases, max_history=max_history,
                    max_lineage_depth=max_lineage_depth,
                    max_ledger_events=max_ledger_events,
                )
            stage = "ROLLBACK"
            db.rollback()
    except psycopg.Error as exc:
        sqlstate = getattr(exc, "sqlstate", None)
        if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
            sqlstate = None
        raise DatabaseFailure(stage, sqlstate, type(exc).__name__) from None

    if len(recovered) != len(cases):
        raise ValueError("RECOVERY_COUNT_INVALID")
    output_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(output_dir.stat().st_mode) != 0o700:
        raise ValueError("OUTPUT_PERMISSIONS_INVALID")

    private_payload = jsonl_bytes(recovered)
    private_name = "R59_GOLD192_HISTORICAL_CONTEXT_PRIVATE.jsonl"
    private_sha = create_only(output_dir / private_name, private_payload)
    summary_counts = Counter(row["summary_status"] for row in recovered)
    content_counts = Counter(row["story_content_version_status"] for row in recovered)
    safe = {
        "schema": "r59_gold192_historical_context_safe_v1",
        "status": "GOLD192_HISTORICAL_CONTEXT_RECOVERED__NOT_ADMITTED",
        "gold192_total": 192,
        "reviewer_ab_priority_total": len(selected),
        "pilot_requested": len(priority),
        "pilot_recovered": len(recovered),
        "story_count": len({row["story_id"] for row in recovered}),
        "story_owner_scope_verified": True,
        "distinct_story_owner_count": owner_count,
        "history_message_count_total": sum(row["history_message_count"] for row in recovered),
        "ledger_sessions_read": len({
            (row["story_id"], row["session_id"]) for row in recovered
        }),
        "ledger_events_read_total": sum(
            row["history_reconstruction"]["ledger_event_count"] for row in recovered
        ),
        "ledger_detail_rows_loaded_total": sum(
            row["history_reconstruction"]["ledger_detail_rows_loaded"] for row in recovered
        ),
        "duplicate_source_roots_reverified": len(verified_duplicate_indices),
        "duplicate_source_root_reverification_pilot_indices": sorted(
            verified_duplicate_indices
        ),
        "ledger_commit_order_verified": False,
        "ledger_trigger_continuity_verified": False,
        "historical_system_prompt_verified": False,
        "current_story_snapshot_used": False,
        "target_time_future_leakage": False,
        "summary_status_counts": dict(sorted(summary_counts.items())),
        "story_content_version_status_counts": dict(sorted(content_counts.items())),
        "private_artifact": {"file": private_name, "records": len(recovered),
                             "sha256": private_sha},
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "database_modified": False,
        "private_values_emitted": False,
    }
    safe_payload = (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    safe_sha = create_only(output_dir / "R59_GOLD192_HISTORICAL_CONTEXT_SAFE.json", safe_payload)
    safe["safe_sha256"] = safe_sha
    return safe


class DatabaseFailure(RuntimeError):
    def __init__(self, stage: str, sqlstate: str | None, exception_type: str):
        self.stage = stage
        self.sqlstate = sqlstate
        self.exception_type = exception_type
        super().__init__("DATABASE_OPERATION_FAILED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reviewer-a", "reviewer-b", "exclusions", "source-packets",
                 "source-locators", "source-safe", "output-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--pilot", type=int, default=8, help="0 = all 72 priority cases")
    parser.add_argument("--max-history", type=int, default=20000)
    parser.add_argument("--max-lineage-depth", type=int, default=16)
    parser.add_argument("--max-ledger-events", type=int, default=100000)
    diagnostics = parser.add_mutually_exclusive_group()
    diagnostics.add_argument(
        "--diagnose-source-only", action="store_true",
        help="validate the selected source locators and exit before any database connection",
    )
    diagnostics.add_argument(
        "--diagnose-duplicate-source-index", type=int,
        help="inspect one duplicated Pilot index using the approved read-only DB role",
    )
    args = parser.parse_args()
    try:
        if (args.pilot < 0 or args.pilot > 72 or args.max_history < 1
                or not 1 <= args.max_lineage_depth <= 64
                or not 1 <= args.max_ledger_events <= 500000):
            raise ValueError("PARAMETERS_INVALID")
        dsn = os.environ.get("STORYFORGE_SUPABASE_DSN")
        if not dsn and not args.diagnose_source_only:
            raise ValueError("DB_CONNECTION_MISSING")
        result = run(
            reviewer_a=args.reviewer_a, reviewer_b=args.reviewer_b,
            exclusions=args.exclusions, source_packets=args.source_packets,
            source_locators=args.source_locators, source_safe=args.source_safe,
            output_dir=args.output_dir, dsn=dsn, pilot=args.pilot,
            max_history=args.max_history, max_lineage_depth=args.max_lineage_depth,
            max_ledger_events=args.max_ledger_events,
            diagnostic_only=args.diagnose_source_only,
            diagnose_duplicate_index=args.diagnose_duplicate_source_index,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never emit SQL, DSN, IDs or message text
        diagnostics = {}
        if isinstance(exc, DatabaseFailure):
            reason = "DATABASE_OPERATION_FAILED"
            diagnostics = {
                "database_stage": exc.stage,
                "database_sqlstate": exc.sqlstate,
                "database_exception_type": exc.exception_type,
            }
        elif isinstance(exc, PilotSourceIdentityHold):
            reason = "PILOT_SOURCE_IDENTITY_HOLD"
            diagnostics = {
                "pilot_source_identity_counts": exc.counts,
                "pilot_source_identity_safe_indices": exc.safe_indices,
            }
        else:
            reason = (str(exc) if isinstance(exc, (ValueError, TypeError))
                      and re.fullmatch(r"[A-Z0-9_]+", str(exc))
                      else type(exc).__name__)
        print(json.dumps({
            "schema": "r59_gold192_historical_context_safe_v1",
            "status": "GOLD192_HISTORICAL_CONTEXT_HOLD",
            "reason_code": reason,
            **diagnostics,
            "quality_v1_admitted": 0, "training_authorized": False,
            "gpu_started": False, "r50_accessed": False,
            "database_modified": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
