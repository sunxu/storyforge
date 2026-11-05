"""Shared, read-only historical context recovery primitives for StoryForge.

The caller supplies a cursor and pinned case locators. This module never opens
connections, reads credentials, writes files, or decides Quality-v1 admission.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .message_ledger import (
    MARKERS,
    SNAPSHOTS,
    LedgerRecoveryError,
    _key,
    load_session_events,
    reconstruct_history,
    target_boundary,
)

SESSION_COLUMNS = (
    "session_id", "parent_session_id", "forked_from_turn", "memory_summary",
    "recent_summary", "rolling_outline", "last_summary_turn", "last_extract_turn",
    "updated_at", "created_at", "summary_source_end_index",
    "summary_source_dependency_end_index", "summary_text_end_index",
    "summary_legacy_text_end_index",
)
TARGET_COLUMNS = (
    "message_id", "story_id", "session_id", "turn_index", "role", "content",
    "status", "created_at",
)
HISTORY_COLUMNS = (
    "message_id", "story_id", "session_id", "turn_index", "role", "content",
    "status", "created_at", "mutation_revision",
)
CONTENT_VERSION_COLUMNS = (
    "id", "content_revision", "title", "description", "tags", "v2_data",
    "source", "source_updated_at", "archived_at",
)
ADMIN_VERSION_COLUMNS = ("id", "content", "created_at", "updated_at")
SUMMARY_CUTOFF_FIELDS = (
    "last_summary_turn", "last_extract_turn", "summary_source_end_index",
    "summary_source_dependency_end_index", "summary_text_end_index",
    "summary_legacy_text_end_index",
)


class HistoryRecoveryError(ValueError):
    """A source identity, temporal boundary, or lineage invariant failed."""


def sha256_text(value: str) -> str:
    if not isinstance(value, str):
        raise HistoryRecoveryError("TEXT_VALUE_INVALID")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _dict_rows(rows: list[Any], columns: tuple[str, ...]) -> list[dict]:
    result = []
    for row in rows:
        if isinstance(row, Mapping):
            result.append(dict(row))
        elif isinstance(row, (tuple, list)) and len(row) == len(columns):
            result.append(dict(zip(columns, row, strict=True)))
        else:
            raise HistoryRecoveryError("DATABASE_ROW_SHAPE_INVALID")
    return result


def _fetchall(cursor, columns: tuple[str, ...]) -> list[dict]:
    return _dict_rows(cursor.fetchall(), columns)


def _fetchone(cursor, columns: tuple[str, ...]) -> dict | None:
    rows = _dict_rows([row for row in [cursor.fetchone()] if row is not None], columns)
    return rows[0] if rows else None


def _datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise HistoryRecoveryError("DATABASE_TIMESTAMP_INVALID") from None
    else:
        raise HistoryRecoveryError("DATABASE_TIMESTAMP_MISSING")
    if parsed.tzinfo is None:
        raise HistoryRecoveryError("DATABASE_TIMESTAMP_TIMEZONE_MISSING")
    return parsed


def _timestamp(value: Any) -> str:
    return _datetime(value).isoformat()


def _before(left: Any, right: Any) -> bool:
    return _datetime(left) < _datetime(right)


def _session(cursor, story_id: str, session_id: str) -> dict:
    cursor.execute(
        """
        SELECT session_id, parent_session_id, forked_from_turn,
               memory_summary, recent_summary, rolling_outline,
               last_summary_turn, last_extract_turn, updated_at, created_at,
               summary_source_end_index, summary_source_dependency_end_index,
               summary_text_end_index, summary_legacy_text_end_index
        FROM public.story_v2_sessions
        WHERE story_id = %s AND session_id = %s
        """,
        (story_id, session_id),
    )
    row = _fetchone(cursor, SESSION_COLUMNS)
    if row is None or row["session_id"] != session_id:
        raise HistoryRecoveryError("SESSION_LINEAGE_NODE_MISSING")
    return row


def _validate_target_rows(case: dict, rows: list[dict]) -> dict:
    exact = [row for row in rows if sha256_text(row["content"]) == case["target_sha256"]]
    if len(rows) != 1 or len(exact) != 1:
        raise HistoryRecoveryError("TARGET_MESSAGE_IDENTITY_AMBIGUOUS")
    target = exact[0]
    if target["status"] != "completed":
        raise HistoryRecoveryError("TARGET_MESSAGE_NOT_COMPLETED")
    if target["story_id"] != case["story_id"] or target["session_id"] != case["session_id"]:
        raise HistoryRecoveryError("TARGET_LOCATOR_MISMATCH")
    if type(target["turn_index"]) is not int or target["turn_index"] != case["turn_index"]:
        raise HistoryRecoveryError("TARGET_TURN_MISMATCH")
    _timestamp(target["created_at"])
    return target


def _target(cursor, case: dict) -> dict:
    cursor.execute(
        """
        SELECT id::text AS message_id, story_id::text AS story_id,
               session_id, turn_index, role, content, status, created_at
        FROM public.v2_chat_messages
        WHERE story_id = %s AND session_id = %s AND turn_index = %s
          AND role = 'assistant'
        """,
        (case["story_id"], case["session_id"], case["turn_index"]),
    )
    return _validate_target_rows(case, _fetchall(cursor, TARGET_COLUMNS))


def _targets_for_cases(cursor, cases: list[dict]) -> dict[str, dict]:
    """Fetch target rows once per Session, then validate each pinned target hash."""
    grouped = {}
    for case in cases:
        key = (case["story_id"], case["session_id"])
        grouped.setdefault(key, []).append(case)
    targets = {}
    for (story_id, session_id), session_cases in sorted(grouped.items()):
        turns = sorted({case["turn_index"] for case in session_cases})
        cursor.execute(
            """
            SELECT id::text AS message_id, story_id::text AS story_id,
                   session_id, turn_index, role, content, status, created_at
            FROM public.v2_chat_messages
            WHERE story_id = %s AND session_id = %s
              AND turn_index = ANY(%s) AND role = 'assistant'
            """,
            (story_id, session_id, turns),
        )
        rows = _fetchall(cursor, TARGET_COLUMNS)
        by_turn = {}
        for row in rows:
            by_turn.setdefault(row["turn_index"], []).append(row)
        for case in session_cases:
            targets[case["case_id"]] = _validate_target_rows(
                case, by_turn.get(case["turn_index"], [])
            )
    return targets


def _lineage(cursor, story_id: str, leaf_session_id: str,
             max_depth: int, *, session_cache: dict | None = None,
             lineage_cache: dict | None = None) -> list[dict]:
    if type(max_depth) is not int or not 1 <= max_depth <= 64:
        raise HistoryRecoveryError("LINEAGE_DEPTH_LIMIT_INVALID")
    cache_key = (story_id, leaf_session_id, max_depth)
    if lineage_cache is not None and cache_key in lineage_cache:
        return lineage_cache[cache_key]
    chain = []
    seen = set()
    current_id = leaf_session_id
    child = None
    while current_id:
        if current_id in seen:
            raise HistoryRecoveryError("SESSION_LINEAGE_CYCLE")
        if len(chain) >= max_depth:
            raise HistoryRecoveryError("SESSION_LINEAGE_DEPTH_EXCEEDED")
        seen.add(current_id)
        session_key = (story_id, current_id)
        if session_cache is not None and session_key in session_cache:
            node = session_cache[session_key]
        else:
            node = _session(cursor, story_id, current_id)
            if session_cache is not None:
                session_cache[session_key] = node
        _timestamp(node["created_at"])
        if (child is not None
                and _datetime(node["created_at"]) > _datetime(child["created_at"])):
            raise HistoryRecoveryError("SESSION_LINEAGE_TIME_ORDER_INVALID")
        parent_id = node.get("parent_session_id")
        if parent_id is not None:
            if not isinstance(parent_id, str) or not parent_id:
                raise HistoryRecoveryError("SESSION_PARENT_ID_INVALID")
            if parent_id in seen:
                raise HistoryRecoveryError("SESSION_LINEAGE_CYCLE")
            # The database stores this as a story-turn number (not the
            # physical v2_chat_messages.turn_index used by message queries).
            fork_turn = node.get("forked_from_turn")
            if type(fork_turn) is not int or fork_turn < 0:
                raise HistoryRecoveryError("SESSION_FORK_CUTOFF_INVALID")
        chain.append({"session": node, "lineage_depth": len(chain)})
        child = node
        current_id = parent_id
    if lineage_cache is not None:
        lineage_cache[cache_key] = chain
    return chain


def _history(cursor, story_id: str, segment: dict, target_time: Any) -> list[dict]:
    session_id = segment["session"]["session_id"]
    cursor.execute(
        """
        SELECT id::text AS message_id, story_id::text AS story_id,
               session_id, turn_index, role, content, status, created_at,
               mutation_revision
        FROM public.v2_chat_messages
        WHERE story_id = %s AND session_id = %s AND turn_index <= %s
          AND created_at < %s AND role IN ('user', 'assistant')
        ORDER BY created_at, id
        """,
        (story_id, session_id, segment["turn_cutoff"], target_time),
    )
    rows = _fetchall(cursor, HISTORY_COLUMNS)
    output = []
    for row in rows:
        if row["status"] != "completed":
            # Failed and streaming rows are not effective conversational input.
            continue
        if row["role"] not in {"user", "assistant"} or not isinstance(row["content"], str):
            raise HistoryRecoveryError("HISTORY_MESSAGE_SHAPE_INVALID")
        if type(row["turn_index"]) is not int or row["turn_index"] > segment["turn_cutoff"]:
            raise HistoryRecoveryError("HISTORY_TURN_CUTOFF_VIOLATION")
        if not _before(row["created_at"], target_time):
            raise HistoryRecoveryError("HISTORY_FUTURE_TIMESTAMP")
        output.append({
            "message_id": row["message_id"],
            "story_id": row["story_id"],
            "session_id": row["session_id"],
            "turn_index": row["turn_index"],
            "role": row["role"],
            "content": row["content"],
            "status": row["status"],
            "created_at": _timestamp(row["created_at"]),
            "mutation_revision": row["mutation_revision"],
            "lineage_depth": segment["lineage_depth"],
        })
    return output


def _summary_snapshot(session: dict, target_time: Any,
                       target_turn_index: int) -> dict:
    updated_at = session.get("updated_at")
    if updated_at is None or not _before(updated_at, target_time):
        return {"status": "NOT_PROVEN_PRETARGET", "used": False, "fields": {}}

    last_summary_turn = session.get("last_summary_turn")
    last_extract_turn = session.get("last_extract_turn")
    if (type(last_summary_turn) is not int or type(last_extract_turn) is not int
            or last_summary_turn < 0 or last_extract_turn < 0):
        return {"status": "TURN_CUTOFF_NOT_PROVEN", "used": False, "fields": {}}

    # last_*_turn are story-turn numbers. The summary_source/text *_index
    # columns are physical message turn_index values. Never compare these
    # coordinate systems directly. The DB has a legacy fallback for NULL
    # indexes, but this recovery gate deliberately refuses that fallback:
    # trigger-invalidated/legacy coverage is not proven for training input.
    physical_cutoff = target_turn_index - 1
    story_turn_cutoff = physical_cutoff // 2
    source_end = session.get("summary_source_end_index")
    text_end = session.get("summary_text_end_index")
    legacy_text_end = session.get("summary_legacy_text_end_index")
    dependency_end = session.get("summary_source_dependency_end_index")

    physical_cutoffs = (source_end, text_end, legacy_text_end)
    if (any(type(value) is not int or value < 0 or value > physical_cutoff
            for value in physical_cutoffs)
            or (dependency_end is not None and
                (type(dependency_end) is not int or dependency_end < 0
                 or dependency_end > physical_cutoff))
            or last_summary_turn > story_turn_cutoff
            or last_extract_turn > story_turn_cutoff):
        return {"status": "CUTOFF_NOT_PROVEN", "used": False, "fields": {}}

    fields = {
        key: session.get(key)
        for key in ("memory_summary", "recent_summary", "rolling_outline")
        if isinstance(session.get(key), str) and session.get(key).strip()
    }
    if not fields:
        return {"status": "NO_SUMMARY_CONTENT", "used": False, "fields": {}}
    return {
        "status": "PRETARGET_COVERAGE_VERIFIED",
        "used": True,
        "updated_at": _timestamp(updated_at),
        "cutoffs": {
            "physical_message_cutoff": physical_cutoff,
            "story_turn_cutoff": story_turn_cutoff,
            "last_summary_turn": last_summary_turn,
            "last_extract_turn": last_extract_turn,
            "summary_source_end_index": source_end,
            "summary_source_dependency_end_index": dependency_end,
            "summary_text_end_index": text_end,
            "summary_legacy_text_end_index": legacy_text_end,
        },
        "fields": fields,
    }


def _story_versions(cursor, story_id: str, target_time: Any,
                    cache: dict | None = None) -> dict:
    cache_key = (story_id, _timestamp(target_time))
    if cache is not None and cache_key in cache:
        return cache[cache_key]
    cursor.execute(
        """
        SELECT id, content_revision, title, description, tags, v2_data,
               source, source_updated_at, archived_at
        FROM public.story_content_versions
        WHERE story_id = %s AND source_updated_at < %s AND archived_at < %s
        ORDER BY source_updated_at DESC, content_revision DESC, id DESC
        LIMIT 1
        """,
        (story_id, target_time, target_time),
    )
    content = _fetchone(cursor, CONTENT_VERSION_COLUMNS)
    if content is not None:
        if not (_before(content["source_updated_at"], target_time)
                and _before(content["archived_at"], target_time)):
            raise HistoryRecoveryError("CONTENT_VERSION_TEMPORAL_BOUNDARY")
        content = {
            **content,
            "source_updated_at": _timestamp(content["source_updated_at"]),
            "archived_at": _timestamp(content["archived_at"]),
            "temporal_status": "PRETARGET_SOURCE_AND_ARCHIVE",
        }

    cursor.execute(
        """
        SELECT id, content, created_at, updated_at
        FROM public.story_admin_versions
        WHERE story_id = %s AND created_at < %s AND updated_at < %s
        ORDER BY updated_at DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (story_id, target_time, target_time),
    )
    admin = _fetchone(cursor, ADMIN_VERSION_COLUMNS)
    if admin is not None:
        if not (_before(admin["created_at"], target_time)
                and _before(admin["updated_at"], target_time)):
            raise HistoryRecoveryError("ADMIN_VERSION_TEMPORAL_BOUNDARY")
        admin = {
            **admin,
            "created_at": _timestamp(admin["created_at"]),
            "updated_at": _timestamp(admin["updated_at"]),
            "temporal_status": "PRETARGET_RECORD_AND_UPDATE",
        }
    result = {
        "story_content_version": content,
        "story_content_version_status": (
            "PRETARGET_VERSION_FOUND" if content else "NO_PRETARGET_VERSION_FOUND"
        ),
        "story_admin_version": admin,
        "story_admin_version_status": (
            "PRETARGET_VERSION_FOUND" if admin else "NO_PRETARGET_VERSION_FOUND"
        ),
        # An archived card snapshot is not proof of the exact historical
        # provider System Prompt or request bytes.
        "historical_system_prompt_verified": False,
    }
    if cache is not None:
        cache[cache_key] = result
    return result


def recover_case(cursor, case: dict, *, max_history: int = 20000,
                 max_lineage_depth: int = 16,
                 target: dict | None = None,
                 ledger_events: list[dict] | None = None,
                 max_ledger_events: int = 100000,
                 session_cache: dict | None = None,
                 lineage_cache: dict | None = None,
                 story_version_cache: dict | None = None) -> dict:
    required = ("case_id", "story_id", "session_id", "turn_index", "target_sha256")
    if any(key not in case for key in required):
        raise HistoryRecoveryError("CASE_LOCATOR_INCOMPLETE")
    if (not isinstance(case["case_id"], str) or not case["case_id"]
            or not isinstance(case["story_id"], str) or not case["story_id"]
            or not isinstance(case["session_id"], str) or not case["session_id"]
            or type(case["turn_index"]) is not int or case["turn_index"] <= 0
            or not isinstance(case["target_sha256"], str)
            or len(case["target_sha256"]) != 64):
        raise HistoryRecoveryError("CASE_LOCATOR_INVALID")

    target = target if target is not None else _target(cursor, case)
    chain = _lineage(
        cursor, case["story_id"], case["session_id"], max_lineage_depth,
        session_cache=session_cache, lineage_cache=lineage_cache,
    )
    leaf = chain[0]["session"]
    # Fork/rewind materializes the inherited messages into the child session
    # with new message IDs. Read that materialized child history once; merging
    # parent messages would duplicate history and misread forked_from_turn,
    # which is a story-turn number rather than a physical message index.
    leaf_segment = {
        "session": leaf,
        "turn_cutoff": case["turn_index"] - 1,
        "lineage_depth": 0,
    }
    if ledger_events is None:
        ledger_events = load_session_events(
            cursor, case["story_id"], case["session_id"], case["turn_index"],
            targets=[target], max_events=max_ledger_events,
        )
    try:
        current_history = _history(
            cursor, case["story_id"], leaf_segment, target["created_at"]
        )
        history, history_reconstruction = reconstruct_history(
            current_history, ledger_events, target,
            case["story_id"], case["session_id"], case["turn_index"] - 1,
        )
    except LedgerRecoveryError as exc:
        raise HistoryRecoveryError(str(exc)) from None
    summary = _summary_snapshot(leaf, target["created_at"], case["turn_index"])
    summaries = []
    if summary["used"]:
        summaries.append({
            "session_id": leaf["session_id"],
            "lineage_depth": 0,
            **summary,
        })
    history.sort(key=lambda row: (_datetime(row["created_at"]), row["message_id"]))
    message_ids = [row["message_id"] for row in history]
    if len(message_ids) != len(set(message_ids)):
        raise HistoryRecoveryError("HISTORY_DUPLICATE_MESSAGE_ID")
    if len(history) > max_history:
        raise HistoryRecoveryError("HISTORY_LIMIT_EXCEEDED")
    if not history or history[-1]["role"] != "user":
        raise HistoryRecoveryError("HISTORY_SUFFIX_NOT_USER")
    if any(not _before(row["created_at"], target["created_at"]) for row in history):
        raise HistoryRecoveryError("HISTORY_FUTURE_LEAKAGE")

    versions = _story_versions(
        cursor, case["story_id"], target["created_at"], story_version_cache
    )
    return {
        "case_id": case["case_id"],
        "story_id": case["story_id"],
        "session_id": case["session_id"],
        "target_sha256": case["target_sha256"],
        "target": {
            "message_id": target["message_id"],
            "turn_index": target["turn_index"],
            "created_at": _timestamp(target["created_at"]),
            "status": target["status"],
        },
        "history": history,
        "history_message_count": len(history),
        "history_materialized_in_leaf_session": True,
        "history_reconstruction": history_reconstruction,
        "session_lineage": [
            {
                "session_id": node["session"]["session_id"],
                "parent_session_id": node["session"].get("parent_session_id"),
                "forked_from_turn_story_turn": node["session"].get("forked_from_turn"),
                "lineage_depth": node["lineage_depth"],
                "session_created_at": _timestamp(node["session"]["created_at"]),
                "session_updated_at": (
                    _timestamp(node["session"]["updated_at"])
                    if node["session"].get("updated_at") is not None else None
                ),
            }
            for node in chain
        ],
        "pretarget_summaries": summaries,
        "summary_status": (
            "PRETARGET_SUMMARY_AVAILABLE" if summaries else "NO_VERIFIED_PRETARGET_SUMMARY"
        ),
        **versions,
        "training_admitted": False,
    }



def diagnose_history_suffixes(cursor, cases: list[dict], *,
                              max_history: int = 20000,
                              max_lineage_depth: int = 16,
                              max_ledger_events: int = 100000) -> list[dict]:
    """Return aggregate-only current-vs-reconstructed suffix evidence per case."""
    if not cases:
        raise HistoryRecoveryError("CASE_SET_EMPTY")
    ids = [row.get("case_id") for row in cases]
    targets = [row.get("target_sha256") for row in cases]
    if len(ids) != len(set(ids)) or len(targets) != len(set(targets)):
        raise HistoryRecoveryError("CASE_SET_DUPLICATE")

    targets_by_case = _targets_for_cases(cursor, cases)
    by_session = {}
    for case in cases:
        story_id = case.get("story_id")
        session_id = case.get("session_id")
        turn_index = case.get("turn_index")
        if (not isinstance(story_id, str) or not story_id
                or not isinstance(session_id, str) or not session_id
                or type(turn_index) is not int or turn_index <= 0):
            raise HistoryRecoveryError("CASE_LOCATOR_INVALID")
        key = (story_id, session_id)
        entry = by_session.setdefault(key, {"max_turn": 0, "targets": []})
        entry["max_turn"] = max(entry["max_turn"], turn_index)
        entry["targets"].append(targets_by_case[case["case_id"]])

    ledger_by_session = {
        key: load_session_events(
            cursor, key[0], key[1], entry["max_turn"],
            targets=entry["targets"], max_events=max_ledger_events,
        )
        for key, entry in sorted(by_session.items())
    }
    results = []
    for index, case in enumerate(cases):
        base = {"safe_index": index}
        try:
            target = targets_by_case[case["case_id"]]
            chain = _lineage(
                cursor, case["story_id"], case["session_id"], max_lineage_depth
            )
            leaf = chain[0]["session"]
            segment = {
                "session": leaf,
                "turn_cutoff": case["turn_index"] - 1,
                "lineage_depth": 0,
            }
            current_history = _history(
                cursor, case["story_id"], segment, target["created_at"]
            )
            events = ledger_by_session[(case["story_id"], case["session_id"])]
            history, reconstruction = reconstruct_history(
                current_history, events, target, case["story_id"],
                case["session_id"], case["turn_index"] - 1,
            )
            history.sort(
                key=lambda row: (_datetime(row["created_at"]), row["message_id"])
            )
            current_history.sort(
                key=lambda row: (_datetime(row["created_at"]), row["message_id"])
            )
            current_suffix = current_history[-1] if current_history else None
            recovered_suffix = history[-1] if history else None
            boundary = _key(target_boundary(events, target))
            suffix_operation = None
            if current_suffix is not None:
                later_suffix_events = sorted(
                    (
                        event for event in events
                        if event["message_id"] == current_suffix["message_id"]
                        and _key(event) > boundary
                    ),
                    key=_key,
                )
                if later_suffix_events:
                    suffix_operation = later_suffix_events[0]["operation"]

            events_by_message = {}
            for event in events:
                events_by_message.setdefault(event["message_id"], []).append(event)
            first_operation_counts = {}
            excluded_with_prior_snapshot = 0
            excluded_without_prior_snapshot = 0
            excluded_prior_snapshot_same_timestamp = 0
            for row in current_history:
                row_events = events_by_message.get(row["message_id"], [])
                later_events = sorted(
                    (event for event in row_events if _key(event) > boundary),
                    key=_key,
                )
                if not later_events:
                    continue
                operation = later_events[0]["operation"]
                first_operation_counts[operation] = first_operation_counts.get(operation, 0) + 1
                if operation in MARKERS:
                    prior_snapshots = [
                        event for event in row_events
                        if event["operation"] in SNAPSHOTS and _key(event) <= boundary
                    ]
                    if prior_snapshots:
                        excluded_with_prior_snapshot += 1
                        if _key(max(prior_snapshots, key=_key))[0] == boundary[0]:
                            excluded_prior_snapshot_same_timestamp += 1
                    else:
                        excluded_without_prior_snapshot += 1

            suffix_fields = {
                "current_history_message_count": len(current_history),
                "current_history_suffix_role": (
                    current_suffix["role"] if current_suffix else None
                ),
                "current_history_suffix_turn": (
                    current_suffix["turn_index"] if current_suffix else None
                ),
                "reconstructed_history_message_count": len(history),
                "history_suffix_role": (
                    recovered_suffix["role"] if recovered_suffix else None
                ),
                "history_suffix_turn": (
                    recovered_suffix["turn_index"] if recovered_suffix else None
                ),
                "current_suffix_first_post_target_operation": suffix_operation,
                "ledger_event_count": reconstruction["ledger_event_count"],
                "history_rows_restored": reconstruction[
                    "history_rows_restored_from_snapshot"
                ],
                "history_rows_excluded": reconstruction[
                    "history_rows_excluded_by_post_target_marker"
                ],
                "current_history_first_post_target_operation_counts": dict(sorted(first_operation_counts.items())),
                "current_marker_rows_with_preboundary_snapshot": excluded_with_prior_snapshot,
                "current_marker_rows_without_preboundary_snapshot": excluded_without_prior_snapshot,
                "current_marker_prior_snapshot_same_timestamp_as_boundary": excluded_prior_snapshot_same_timestamp,
            }
            if not history or recovered_suffix["role"] != "user":
                results.append({
                    **base, "result": "HOLD",
                    "reason_code": "HISTORY_SUFFIX_NOT_USER",
                    **suffix_fields,
                })
                continue

            recovered = recover_case(
                cursor, case, max_history=max_history,
                max_lineage_depth=max_lineage_depth,
                target=target, ledger_events=events,
                max_ledger_events=max_ledger_events,
            )
            results.append({
                **base,
                "result": "RECOVERED",
                "history_message_count": recovered["history_message_count"],
                "history_suffix_role": recovered["history"][-1]["role"],
                "ledger_event_count": reconstruction["ledger_event_count"],
                "history_rows_restored": reconstruction[
                    "history_rows_restored_from_snapshot"
                ],
                "history_rows_excluded": reconstruction[
                    "history_rows_excluded_by_post_target_marker"
                ],
                "current_history_suffix_role": suffix_fields[
                    "current_history_suffix_role"
                ],
                "current_suffix_first_post_target_operation": suffix_operation,
                "current_history_first_post_target_operation_counts": suffix_fields["current_history_first_post_target_operation_counts"],
                "current_marker_rows_with_preboundary_snapshot": excluded_with_prior_snapshot,
                "current_marker_rows_without_preboundary_snapshot": excluded_without_prior_snapshot,
                "current_marker_prior_snapshot_same_timestamp_as_boundary": excluded_prior_snapshot_same_timestamp,
            })
        except HistoryRecoveryError as exc:
            reason = str(exc)
            if not reason or not reason.replace("_", "").isalnum() or reason.upper() != reason:
                reason = "RECOVERY_CASE_HOLD"
            results.append({**base, "result": "HOLD", "reason_code": reason})
    return results


def recover_cases(cursor, cases: list[dict], *, max_history: int = 20000,
                  max_lineage_depth: int = 16,
                  max_ledger_events: int = 100000) -> list[dict]:
    if not cases:
        raise HistoryRecoveryError("CASE_SET_EMPTY")
    ids = [row.get("case_id") for row in cases]
    targets = [row.get("target_sha256") for row in cases]
    if len(ids) != len(set(ids)) or len(targets) != len(set(targets)):
        raise HistoryRecoveryError("CASE_SET_DUPLICATE")

    # Resolve targets first, then read one bounded ledger metadata stream per
    # Session. Large before-image JSONB snapshots are fetched by primary key
    # only when they are the first post-target event for a requested case.
    targets_by_case = _targets_for_cases(cursor, cases)
    by_session = {}
    for case in cases:
        story_id = case.get("story_id")
        session_id = case.get("session_id")
        turn_index = case.get("turn_index")
        if (not isinstance(story_id, str) or not story_id
                or not isinstance(session_id, str) or not session_id
                or type(turn_index) is not int or turn_index <= 0):
            raise HistoryRecoveryError("CASE_LOCATOR_INVALID")
        key = (story_id, session_id)
        entry = by_session.setdefault(key, {"max_turn": 0, "targets": []})
        entry["max_turn"] = max(entry["max_turn"], turn_index)
        entry["targets"].append(targets_by_case[case["case_id"]])
    ledger_by_session = {
        key: load_session_events(
            cursor, key[0], key[1], entry["max_turn"],
            targets=entry["targets"], max_events=max_ledger_events,
        )
        for key, entry in sorted(by_session.items())
    }
    # Share immutable read results across cases in this single DB transaction.
    # These caches remove repeated session-lineage queries without changing
    # target boundaries, history selection, or admission decisions.
    session_cache = {}
    lineage_cache = {}
    story_version_cache = {}
    return [
        recover_case(
            cursor, row, max_history=max_history,
            max_lineage_depth=max_lineage_depth,
            target=targets_by_case[row["case_id"]],
            ledger_events=ledger_by_session[(row["story_id"], row["session_id"])],
            max_ledger_events=max_ledger_events,
            session_cache=session_cache,
            lineage_cache=lineage_cache,
            story_version_cache=story_version_cache,
        )
        for row in sorted(cases, key=lambda item: item["case_id"])
    ]
