"""Sparse message-ledger historical reconstruction (read-only)."""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime

COLUMNS = ("id", "message_id", "story_id", "session_id", "role",
           "turn_index", "operation", "row_data", "recorded_at")
SNAPSHOTS = {"update_before", "delete"}
MARKERS = {"insert", "update_after"}
LEDGER_METADATA_BATCH_SIZE = 10000


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


def _validate_event_locator(event, story_id, session_id):
    if not isinstance(event.get("message_id"), str) or not event["message_id"]:
        raise LedgerRecoveryError("LEDGER_EVENT_MESSAGE_ID_INVALID")
    if event.get("story_id") != story_id:
        raise LedgerRecoveryError("LEDGER_EVENT_STORY_ID_MISMATCH")
    if event.get("session_id") != session_id:
        raise LedgerRecoveryError("LEDGER_EVENT_SESSION_ID_MISMATCH")
    if type(event.get("turn_index")) is not int:
        raise LedgerRecoveryError("LEDGER_EVENT_TURN_INDEX_TYPE_INVALID")
    if event["turn_index"] < 1:
        raise LedgerRecoveryError("LEDGER_EVENT_TURN_INDEX_NONPOSITIVE")
    if event.get("operation") not in SNAPSHOTS | MARKERS:
        raise LedgerRecoveryError("LEDGER_EVENT_OPERATION_INVALID")


def _required_event_ids(events, targets):
    needed = set()
    index = LedgerEventIndex(events)
    for target in targets:
        try:
            boundary_event = index.target_boundary(target)
        except LedgerRecoveryError as exc:
            if str(exc) == "TARGET_LEDGER_BOUNDARY_MISSING":
                # A missing boundary is a per-target HOLD, not a reason to
                # discard other targets that share this Session.
                continue
            raise
        needed.add(boundary_event["id"])
        boundary = _key(boundary_event)
        cutoff = target["turn_index"] - 1
        for message_id in index.by_message_id:
            first = index.first_post_boundary_event(message_id, boundary, cutoff)
            if first is not None:
                needed.add(first["id"])
    return sorted(needed)


def load_session_events(cursor, story_id, session_id, max_turn_index,
                        targets, max_events=100000):
    if (not isinstance(story_id, str) or not story_id
            or not isinstance(session_id, str) or not session_id
            or type(max_turn_index) is not int or max_turn_index < 1
            or not isinstance(targets, list) or not targets
            or type(max_events) is not int or not 1 <= max_events <= 1000000):
        raise LedgerRecoveryError("LEDGER_QUERY_SCOPE_INVALID")
    if any(target.get("story_id") != story_id
           or target.get("session_id") != session_id
           or not isinstance(target.get("message_id"), str)
           or not target.get("message_id")
           or type(target.get("turn_index")) is not int
           or target["turn_index"] < 1
           for target in targets):
        raise LedgerRecoveryError("LEDGER_TARGET_SCOPE_INVALID")

    # Only ledger events at/after the earliest target boundary can affect any
    # target's historical reconstruction. Locate the small set of target
    # boundary markers first, then keyset-page forward from the earliest one.
    # This avoids transferring the entire pre-target ledger history.
    target_message_ids = sorted({target["message_id"] for target in targets})
    target_turn_indices = sorted({target["turn_index"] for target in targets})
    cursor.execute(
        """
        SELECT id, message_id::text AS message_id,
               story_id::text AS story_id, session_id::text AS session_id,
               role::text AS role, turn_index::integer AS turn_index,
               operation::text AS operation, recorded_at
        FROM public.v2_chat_message_ledger
        WHERE story_id = %s AND session_id = %s
          AND message_id = ANY(%s::uuid[])
          AND turn_index = ANY(%s::integer[])
          AND role = 'assistant'
          AND operation IN ('insert', 'update_after')
        ORDER BY recorded_at, id
        """,
        (story_id, session_id, target_message_ids, target_turn_indices),
    )
    boundary_rows = cursor.fetchall()
    target_pairs = {
        (target["message_id"], target["turn_index"]) for target in targets
    }
    boundary_by_pair = {}
    for row in boundary_rows:
        if isinstance(row, Mapping):
            event = dict(row)
        elif isinstance(row, (tuple, list)) and len(row) == 8:
            event = dict(zip(
                ("id", "message_id", "story_id", "session_id", "role",
                 "turn_index", "operation", "recorded_at"),
                row, strict=True,
            ))
        else:
            raise LedgerRecoveryError("LEDGER_ROW_SHAPE_INVALID")
        _validate_event_locator(event, story_id, session_id)
        _key(event)
        pair = (event["message_id"], event["turn_index"])
        if pair in target_pairs:
            previous = boundary_by_pair.get(pair)
            if previous is None or _key(event) < _key(previous):
                boundary_by_pair[pair] = event

    # Keep each target's own boundary and cutoff. A single Session-wide
    # earliest boundary is only a safe lower bound; it is not sufficient to
    # choose the first post-boundary event for every target.
    target_boundaries = []
    for ordinal, target in enumerate(targets):
        pair = (target["message_id"], target["turn_index"])
        boundary = boundary_by_pair.get(pair)
        if boundary is not None:
            target_boundaries.append((ordinal, target, boundary))
    if not target_boundaries:
        # Missing boundaries remain isolated per-case HOLDs in local evaluation.
        return []

    ordinals = [ordinal for ordinal, _, _ in target_boundaries]
    boundary_turns = [target["turn_index"] for _, target, _ in target_boundaries]
    boundary_times = [boundary["recorded_at"] for _, _, boundary in target_boundaries]
    boundary_ids = [boundary["id"] for _, _, boundary in target_boundaries]

    # Push first-event selection into PostgreSQL. For every target and message,
    # choose the first event after that target's own (recorded_at, id) boundary
    # whose turn_index is within that target's historical cutoff. The union of
    # those rows is sufficient for the existing Python reconstruction semantics:
    # an event selected for another target cannot precede an eligible event for
    # this target without also being eligible and selected for this target.
    cursor.execute(
        """
        WITH targets AS (
            SELECT target_ordinal, turn_index, boundary_recorded_at, boundary_id
            FROM unnest(
                %s::integer[], %s::integer[], %s::timestamptz[], %s::bigint[]
            ) AS t(target_ordinal, turn_index, boundary_recorded_at, boundary_id)
        ),
        first_events AS (
            SELECT DISTINCT ON (t.target_ordinal, e.message_id)
                   e.id, e.message_id::text AS message_id,
                   e.story_id::text AS story_id, e.session_id::text AS session_id,
                   e.role::text AS role, e.turn_index::integer AS turn_index,
                   e.operation::text AS operation, e.recorded_at
            FROM targets t
            JOIN public.v2_chat_message_ledger e
              ON e.story_id = %s AND e.session_id = %s
             AND e.turn_index BETWEEN 1 AND (t.turn_index - 1)
             AND (e.recorded_at, e.id) > (t.boundary_recorded_at, t.boundary_id)
            ORDER BY t.target_ordinal, e.message_id, e.recorded_at, e.id
        )
        SELECT id, message_id, story_id, session_id, role, turn_index,
               operation, recorded_at
        FROM first_events
        ORDER BY recorded_at, id
        """,
        (ordinals, boundary_turns, boundary_times, boundary_ids, story_id, session_id),
    )
    metadata_columns = (
        "id", "message_id", "story_id", "session_id", "role",
        "turn_index", "operation", "recorded_at",
    )
    events_by_id = {}
    for row in cursor.fetchall():
        if isinstance(row, Mapping):
            event = dict(row)
        elif isinstance(row, (tuple, list)) and len(row) == len(metadata_columns):
            event = dict(zip(metadata_columns, row, strict=True))
        else:
            raise LedgerRecoveryError("LEDGER_ROW_SHAPE_INVALID")
        _validate_event_locator(event, story_id, session_id)
        _key(event)
        event["row_data"] = None
        previous = events_by_id.get(event["id"])
        if previous is not None and any(
            previous[field] != event[field] for field in metadata_columns[1:]
        ):
            raise LedgerRecoveryError("LEDGER_EVENT_IDENTITY_CONFLICT")
        events_by_id[event["id"]] = event
        if len(events_by_id) > max_events:
            raise LedgerRecoveryError("LEDGER_SESSION_EVENT_LIMIT_EXCEEDED")
    result = sorted(events_by_id.values(), key=_key)
    boundary_events_by_id = {event["id"]: event for _, _, event in target_boundaries}
    for event_id, event in boundary_events_by_id.items():
        previous = events_by_id.get(event_id)
        if previous is not None and any(
            previous[field] != event[field] for field in metadata_columns[1:]
        ):
            raise LedgerRecoveryError("LEDGER_EVENT_IDENTITY_CONFLICT")
        if previous is None:
            result.append({**event, "row_data": None})
    result.sort(key=_key)
    if len(result) > max_events:
        raise LedgerRecoveryError("LEDGER_SESSION_EVENT_LIMIT_EXCEEDED")

    detail_ids = _required_event_ids(result, targets)
    details = {}
    for start in range(0, len(detail_ids), 500):
        batch = detail_ids[start:start + 500]
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
                raise LedgerRecoveryError("LEDGER_DETAIL_ROW_SHAPE_INVALID")
            if type(event_id) is not int or not isinstance(row_data, dict):
                raise LedgerRecoveryError("LEDGER_DETAIL_MISSING")
            details[event_id] = row_data
    if set(detail_ids) != set(details):
        raise LedgerRecoveryError("LEDGER_DETAIL_MISSING")
    for event in result:
        if event["id"] in details:
            event["row_data"] = details[event["id"]]
            if event["operation"] in MARKERS:
                _validate_business_event_detail(event)
    return result


def _validate_business_event_detail(event):
    """Accept a v1 marker or a validated legacy full after-image.

    Before the sparse-marker migration, INSERT / UPDATE_AFTER events stored a
    full row. Their schema may predate mutation_revision; validate identity
    and business fields without promoting the historical row to a snapshot
    usable for reconstructing a before-image.
    """
    data = event.get("row_data")
    if not isinstance(data, dict):
        raise LedgerRecoveryError("LEDGER_MARKER_INVALID")
    if "_ledger_event" in data:
        if data == {"_ledger_event": "marker_v1"}:
            return "SPARSE_MARKER_V1"
        raise LedgerRecoveryError("LEDGER_MARKER_INVALID")
    required = ("id", "story_id", "session_id", "turn_index",
                "role", "content", "status", "created_at")
    if any(field not in data for field in required):
        raise LedgerRecoveryError("LEDGER_LEGACY_DETAIL_FIELDS_INVALID")
    if (str(data["id"]) != event["message_id"]
            or data["story_id"] != event["story_id"]
            or data["session_id"] != event["session_id"]
            or data["turn_index"] != event["turn_index"]
            or data["role"] != event["role"]):
        raise LedgerRecoveryError("LEDGER_LEGACY_DETAIL_IDENTITY_MISMATCH")
    if (not isinstance(data["content"], str)
            or data["status"] not in {"completed", "streaming", "failed"}):
        raise LedgerRecoveryError("LEDGER_LEGACY_DETAIL_VALUE_INVALID")
    _dt(data["created_at"])
    return "LEGACY_FULL_AFTER_IMAGE"



class LedgerEventIndex:
    """Per-Session immutable event index reused across target reconstructions."""

    def __init__(self, events):
        self.events = events
        grouped = defaultdict(list)
        for event in events:
            grouped[event["message_id"]].append(event)
        self.by_message_id = {}
        self.keys_by_message_id = {}
        for message_id, rows in grouped.items():
            rows.sort(key=_key)
            self.by_message_id[message_id] = rows
            self.keys_by_message_id[message_id] = [_key(row) for row in rows]

    def target_boundary(self, target):
        rows = self.by_message_id.get(target.get("message_id"), ())
        matches = [
            event for event in rows
            if event.get("story_id") == target.get("story_id")
            and event.get("session_id") == target.get("session_id")
            and event.get("turn_index") == target.get("turn_index")
            and event.get("role") == "assistant"
            and event.get("operation") in MARKERS
        ]
        if not matches:
            raise LedgerRecoveryError("TARGET_LEDGER_BOUNDARY_MISSING")
        return matches[0]

    def first_post_boundary_event(self, message_id, boundary, cutoff):
        rows = self.by_message_id.get(message_id, ())
        keys = self.keys_by_message_id.get(message_id, ())
        start = bisect_right(keys, boundary)
        for position in range(start, len(rows)):
            event = rows[position]
            if event["turn_index"] <= cutoff:
                return event
        return None


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
              "content", "status", "created_at")
    if not isinstance(data, dict) or any(k not in data for k in fields):
        raise LedgerRecoveryError("LEDGER_SNAPSHOT_FIELDS_INCOMPLETE")
    revision_present = "mutation_revision" in data
    revision = data.get("mutation_revision")
    if revision_present and (type(revision) is not int or revision < 0):
        raise LedgerRecoveryError("LEDGER_SNAPSHOT_MUTATION_REVISION_INVALID")
    if (str(data["id"]) != event["message_id"]
            or data["story_id"] != event["story_id"]
            or data["session_id"] != event["session_id"]
            or data["role"] != event["role"]
            or data["turn_index"] != event["turn_index"]
            or type(data["turn_index"]) is not int
            or not isinstance(data["content"], str)
            or not isinstance(data["status"], str)):
        raise LedgerRecoveryError("LEDGER_SNAPSHOT_IDENTITY_MISMATCH")
    _dt(data["created_at"])
    return {
        "message_id": str(data["id"]), "story_id": data["story_id"],
        "session_id": data["session_id"], "turn_index": data["turn_index"],
        "role": data["role"], "content": data["content"],
        "status": data["status"], "created_at": data["created_at"],
        "mutation_revision": revision,
    }


def reconstruct_history(current_rows, events, target, story_id, session_id, cutoff,
                       event_index=None):
    event_index = event_index or LedgerEventIndex(events)
    boundary_event = event_index.target_boundary(target)
    boundary = _key(boundary_event)
    current = {}
    for row in current_rows:
        mid = row.get("message_id")
        if not isinstance(mid, str) or mid in current:
            raise LedgerRecoveryError("CURRENT_HISTORY_IDENTITY_INVALID")
        current[mid] = row
    output = []
    restored = excluded = unchanged = 0
    legacy_snapshot_revision_missing = 0
    snapshot_revision_present = 0
    for mid in sorted(set(current) | set(event_index.by_message_id)):
        first = event_index.first_post_boundary_event(mid, boundary, cutoff)
        if first and first["operation"] in SNAPSHOTS:
            state = _snapshot(first)
            restored += 1
            if state["mutation_revision"] is None:
                # Historical to_jsonb(OLD) snapshots predate the mutation_revision
                # column. Their complete business fields remain usable, but the
                # missing revision must be reported rather than inferred from event counts.
                legacy_snapshot_revision_missing += 1
            else:
                snapshot_revision_present += 1
        elif first and first["operation"] in MARKERS:
            excluded += 1
            continue
        else:
            state = current.get(mid)
            if state is None:
                continue
            unchanged += 1
        # update_after also records non-revision business changes such as turn
        # compaction/client metadata. It is not a mutation_revision counter.
        # Legacy to_jsonb(OLD) snapshots may predate the revision column entirely.
        revision = state.get("mutation_revision")
        if revision is None:
            if not (first and first["operation"] in SNAPSHOTS):
                raise LedgerRecoveryError("LEDGER_MUTATION_REVISION_INVALID")
        elif type(revision) is not int or revision < 0:
            raise LedgerRecoveryError("LEDGER_MUTATION_REVISION_INVALID")
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
    event = boundary_event
    return output, {
        "ledger_event_count": len(events),
        "ledger_detail_rows_loaded": sum(
            event.get("row_data") is not None for event in events
        ),
        "ledger_target_boundary_id": event["id"],
        "ledger_event_order_basis": "recorded_at_then_id",
        "ledger_commit_order_verified": False,
        "ledger_trigger_continuity_verified": False,
        "history_rows_restored_from_snapshot": restored,
        "history_rows_restored_with_revision_snapshot": snapshot_revision_present,
        "history_rows_restored_from_legacy_snapshot_without_revision": (
            legacy_snapshot_revision_missing
        ),
        "mutation_revision_evidence_state": (
            "LEGACY_SNAPSHOT_REVISION_UNAVAILABLE"
            if legacy_snapshot_revision_missing
            else "REVISION_FIELD_TYPE_AND_RANGE_VALIDATED"
        ),
        "history_rows_excluded_by_post_target_marker": excluded,
        "history_rows_using_unchanged_current_state": unchanged,
    }
