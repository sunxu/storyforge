"""Sparse message-ledger historical reconstruction (read-only)."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime

COLUMNS = ("id", "message_id", "story_id", "session_id", "role",
           "turn_index", "operation", "row_data", "recorded_at")
SNAPSHOTS = {"update_before", "delete"}
MARKERS = {"insert", "update_after"}


class LedgerRecoveryError(ValueError):
    pass


def _dt(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value)
        except ValueError:
            raise LedgerRecoveryError("LEDGER_TIMESTAMP_INVALID") from None
    else:
        raise LedgerRecoveryError("LEDGER_TIMESTAMP_MISSING")
    if result.tzinfo is None:
        raise LedgerRecoveryError("LEDGER_TIMESTAMP_TIMEZONE_MISSING")
    return result


def _key(event):
    if type(event.get("id")) is not int or event["id"] <= 0:
        raise LedgerRecoveryError("LEDGER_EVENT_ID_INVALID")
    return (_dt(event.get("recorded_at")), event["id"])


def _snapshot_ids_needed(events, targets):
    needed = set()
    for target in targets:
        boundary = _key(target_boundary(events, target))
        grouped = defaultdict(list)
        cutoff = target["turn_index"] - 1
        for event in events:
            if event["turn_index"] <= cutoff:
                grouped[event["message_id"]].append(event)
        for message_events in grouped.values():
            first = next(
                (event for event in sorted(message_events, key=_key)
                 if _key(event) > boundary),
                None,
            )
            if first is not None and first["operation"] in SNAPSHOTS:
                needed.add(first["id"])
    return sorted(needed)


def load_session_events(cursor, story_id, session_id, max_turn_index,
                        targets, max_events=100000):
    if (not isinstance(story_id, str) or not story_id
            or not isinstance(session_id, str) or not session_id
            or type(max_turn_index) is not int or max_turn_index < 1
            or not isinstance(targets, list) or not targets
            or type(max_events) is not int or not 1 <= max_events <= 500000):
        raise LedgerRecoveryError("LEDGER_QUERY_SCOPE_INVALID")
    target_times = [_dt(target.get("created_at")) for target in targets]
    if any(target.get("story_id") != story_id
           or target.get("session_id") != session_id
           for target in targets):
        raise LedgerRecoveryError("LEDGER_TARGET_SCOPE_INVALID")

    # Read the compact event index first. Snapshot JSONB can be large and is
    # fetched separately by primary key only when it is the first post-target
    # event for at least one target in this Session.
    cursor.execute(
        """
        SELECT id, message_id::text AS message_id, story_id, session_id,
               role, turn_index, operation,
               CASE WHEN operation IN ('insert', 'update_after')
                    THEN row_data ELSE NULL END AS row_data,
               recorded_at
        FROM public.v2_chat_message_ledger
        WHERE story_id = %s AND session_id = %s AND turn_index <= %s
        ORDER BY recorded_at, id
        LIMIT %s
        """,
        (story_id, session_id, max_turn_index, max_events + 1),
    )
    result = []
    for row in cursor.fetchall():
        if isinstance(row, Mapping):
            event = dict(row)
        elif isinstance(row, (tuple, list)) and len(row) == len(COLUMNS):
            event = dict(zip(COLUMNS, row, strict=True))
        else:
            raise LedgerRecoveryError("LEDGER_ROW_SHAPE_INVALID")
        if (not isinstance(event.get("message_id"), str)
                or event.get("story_id") != story_id
                or event.get("session_id") != session_id
                or type(event.get("turn_index")) is not int
                or event["turn_index"] < 1
                or event.get("operation") not in SNAPSHOTS | MARKERS):
            raise LedgerRecoveryError("LEDGER_EVENT_LOCATOR_INVALID")
        _key(event)
        if event["operation"] in MARKERS and (
            not isinstance(event.get("row_data"), dict)
            or event["row_data"].get("_ledger_event") != "marker_v1"
        ):
            raise LedgerRecoveryError("LEDGER_MARKER_INVALID")
        result.append(event)
    if len(result) > max_events:
        raise LedgerRecoveryError("LEDGER_SESSION_EVENT_LIMIT_EXCEEDED")

    snapshot_ids = _snapshot_ids_needed(result, targets)
    snapshot_rows = {}
    for start in range(0, len(snapshot_ids), 500):
        batch = snapshot_ids[start:start + 500]
        cursor.execute(
            """
            SELECT id, row_data
            FROM public.v2_chat_message_ledger
            WHERE id = ANY(%s)
            """,
            (batch,),
        )
        for row in cursor.fetchall():
            if isinstance(row, Mapping):
                event_id, row_data = row["id"], row["row_data"]
            elif isinstance(row, (tuple, list)) and len(row) == 2:
                event_id, row_data = row
            else:
                raise LedgerRecoveryError("LEDGER_SNAPSHOT_ROW_SHAPE_INVALID")
            if type(event_id) is not int or not isinstance(row_data, dict):
                raise LedgerRecoveryError("LEDGER_SNAPSHOT_MISSING")
            snapshot_rows[event_id] = row_data
    if set(snapshot_ids) != set(snapshot_rows):
        raise LedgerRecoveryError("LEDGER_SNAPSHOT_MISSING")
    for event in result:
        if event["id"] in snapshot_rows:
            event["row_data"] = snapshot_rows[event["id"]]
    return result


def target_boundary(events, target):
    matches = [
        event for event in events
        if event.get("message_id") == target.get("message_id")
        and event.get("story_id") == target.get("story_id")
        and event.get("session_id") == target.get("session_id")
        and event.get("turn_index") == target.get("turn_index")
        and event.get("role") == "assistant"
        and event.get("operation") in MARKERS
    ]
    if not matches:
        raise LedgerRecoveryError("TARGET_LEDGER_BOUNDARY_MISSING")
    return min(matches, key=_key)


def _snapshot(event):
    data = event.get("row_data")
    fields = ("id", "story_id", "session_id", "turn_index", "role",
              "content", "status", "created_at", "mutation_revision")
    if not isinstance(data, dict) or any(k not in data for k in fields):
        raise LedgerRecoveryError("LEDGER_SNAPSHOT_FIELDS_INCOMPLETE")
    if (str(data["id"]) != event["message_id"]
            or data["story_id"] != event["story_id"]
            or data["session_id"] != event["session_id"]
            or data["role"] != event["role"]
            or data["turn_index"] != event["turn_index"]
            or type(data["turn_index"]) is not int
            or type(data["mutation_revision"]) is not int
            or data["mutation_revision"] < 0
            or not isinstance(data["content"], str)
            or not isinstance(data["status"], str)):
        raise LedgerRecoveryError("LEDGER_SNAPSHOT_IDENTITY_MISMATCH")
    _dt(data["created_at"])
    return {
        "message_id": str(data["id"]), "story_id": data["story_id"],
        "session_id": data["session_id"], "turn_index": data["turn_index"],
        "role": data["role"], "content": data["content"],
        "status": data["status"], "created_at": data["created_at"],
        "mutation_revision": data["mutation_revision"],
    }


def reconstruct_history(current_rows, events, target, story_id, session_id, cutoff):
    boundary = _key(target_boundary(events, target))
    current = {}
    for row in current_rows:
        mid = row.get("message_id")
        if not isinstance(mid, str) or mid in current:
            raise LedgerRecoveryError("CURRENT_HISTORY_IDENTITY_INVALID")
        current[mid] = row
    grouped = defaultdict(list)
    for event in events:
        if event["turn_index"] <= cutoff:
            grouped[event["message_id"]].append(event)
    for group in grouped.values():
        group.sort(key=_key)

    output = []
    restored = excluded = unchanged = 0
    for mid in sorted(set(current) | set(grouped)):
        message_events = grouped.get(mid, [])
        later = [e for e in message_events if _key(e) > boundary]
        first = later[0] if later else None
        if first and first["operation"] in SNAPSHOTS:
            state = _snapshot(first)
            expected_revision = sum(
                e["operation"] == "update_after" and _key(e) < _key(first)
                for e in message_events
            )
            restored += 1
        elif first and first["operation"] in MARKERS:
            excluded += 1
            continue
        else:
            state = current.get(mid)
            if state is None:
                continue
            expected_revision = sum(
                e["operation"] == "update_after" for e in message_events
            )
            unchanged += 1
        revision = state.get("mutation_revision")
        if type(revision) is not int or revision != expected_revision:
            raise LedgerRecoveryError("LEDGER_MUTATION_REVISION_MISMATCH")
        if (state.get("story_id") != story_id
                or state.get("session_id") != session_id
                or type(state.get("turn_index")) is not int
                or state["turn_index"] > cutoff
                or state.get("role") not in {"user", "assistant"}
                or state.get("status") != "completed"):
            continue
        created = _dt(state.get("created_at"))
        if created >= _dt(target["created_at"]):
            continue
        output.append({
            "message_id": mid, "story_id": story_id, "session_id": session_id,
            "turn_index": state["turn_index"], "role": state["role"],
            "content": state["content"], "status": state["status"],
            "created_at": created.isoformat(), "lineage_depth": 0,
        })
    output.sort(key=lambda r: (r["created_at"], r["message_id"]))
    if len({r["message_id"] for r in output}) != len(output):
        raise LedgerRecoveryError("LEDGER_RECONSTRUCTED_DUPLICATE_MESSAGE")
    event = target_boundary(events, target)
    return output, {
        "ledger_event_count": len(events),
        "ledger_target_boundary_id": event["id"],
        "ledger_event_order_basis": "recorded_at_then_id",
        "ledger_commit_order_verified": False,
        "ledger_trigger_continuity_verified": False,
        "history_rows_restored_from_snapshot": restored,
        "history_rows_excluded_by_post_target_marker": excluded,
        "history_rows_using_unchanged_current_state": unchanged,
    }
