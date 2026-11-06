"""Gold192 adapter for the shared R59 historical recovery core.

Read-only source reconstruction only. It does not grant Quality-v1 admission,
compile SFT data, access R50, or start HF/GPU work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
import time
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
from storyforge_gold_quality.history_recovery import (  # noqa: E402
    diagnose_history_suffixes, evaluate_history_suffix_diagnostics,
    prepare_history_suffix_diagnostics, recover_cases_independently,
)

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
        is_single_match = (
            isinstance(match_count, int) and not isinstance(match_count, bool)
            and match_count == 1
        )
        if not is_single_match and not (
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


def recovery_query_stage(query: str) -> str:
    """Classify a recovery SQL statement without exposing SQL or parameters."""
    sql = query.lower()
    if "from public.user_stories" in sql:
        return "OWNER_SCOPE_QUERY"
    if "from public.v2_chat_message_ledger" in sql:
        return ("LEDGER_DETAIL_QUERY" if "row_data" in sql
                else "LEDGER_METADATA_QUERY")
    if "from public.v2_chat_messages" in sql:
        if "mutation_revision" in sql:
            return "CURRENT_HISTORY_QUERY"
        if "role = 'assistant'" in sql:
            return "TARGET_MESSAGE_QUERY"
        return "MESSAGE_QUERY"
    if "public.story_v2_sessions" in sql:
        return "SESSION_LINEAGE_QUERY"
    if "from public.story_content_versions" in sql:
        return "STORY_VERSION_QUERY"
    if "from public.story_admin_versions" in sql:
        return "ADMIN_VERSION_QUERY"
    return "RECOVERY_QUERY_OTHER"


def safe_explain_plan_summary(payload):
    """Reduce EXPLAIN JSON to a SAFE plan shape without retaining SQL literals."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict) and "QUERY PLAN" in payload:
        payload = payload["QUERY PLAN"]
    if isinstance(payload, list):
        if not payload or not isinstance(payload[0], dict):
            raise ValueError("EXPLAIN_PLAN_SHAPE_INVALID")
        payload = payload[0]
    if not isinstance(payload, dict) or not isinstance(payload.get("Plan"), dict):
        raise ValueError("EXPLAIN_PLAN_SHAPE_INVALID")

    root = payload["Plan"]
    node_types = []
    index_names = set()
    boundary_index_condition = False
    sort_count = unique_count = 0
    stack = [root]
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            raise ValueError("EXPLAIN_PLAN_NODE_INVALID")
        node_type = node.get("Node Type")
        if not isinstance(node_type, str) or not node_type:
            raise ValueError("EXPLAIN_PLAN_NODE_INVALID")
        node_types.append(node_type)
        if node_type in {"Sort", "Incremental Sort"}:
            sort_count += 1
        if node_type == "Unique":
            unique_count += 1
        index_name = node.get("Index Name")
        if index_name is not None:
            if not isinstance(index_name, str) or not re.fullmatch(
                r"[A-Za-z0-9_]+", index_name
            ):
                raise ValueError("EXPLAIN_PLAN_INDEX_NAME_INVALID")
            index_names.add(index_name)
        index_cond = node.get("Index Cond", "")
        if not isinstance(index_cond, str):
            raise ValueError("EXPLAIN_PLAN_INDEX_CONDITION_INVALID")
        if ("recorded_at" in index_cond and "boundary_recorded_at" in index_cond
                and "id" in index_cond and "boundary_id" in index_cond):
            boundary_index_condition = True
        children = node.get("Plans", [])
        if not isinstance(children, list):
            raise ValueError("EXPLAIN_PLAN_CHILDREN_INVALID")
        stack.extend(reversed(children))

    estimated_rows = root.get("Plan Rows", 0)
    estimated_cost = root.get("Total Cost", 0.0)
    if (isinstance(estimated_rows, bool) or not isinstance(estimated_rows, (int, float))
            or estimated_rows < 0
            or isinstance(estimated_cost, bool)
            or not isinstance(estimated_cost, (int, float))
            or not math.isfinite(float(estimated_cost)) or estimated_cost < 0):
        raise ValueError("EXPLAIN_PLAN_ESTIMATE_INVALID")
    return {
        "query_class": "LEDGER_METADATA_QUERY",
        "plan_capture_status": "CAPTURED",
        "node_types": node_types,
        "index_names": sorted(index_names),
        "b2_selected": "idx_v2_chat_message_ledger_r60_b2" in index_names,
        "index_only_scan": "Index Only Scan" in node_types,
        "boundary_range_in_index_condition": boundary_index_condition,
        "sort_node_count": sort_count,
        "unique_node_count": unique_count,
        "estimated_plan_rows": estimated_rows,
        "estimated_total_cost": round(float(estimated_cost), 3),
        "plan_capture_ms": 0.0,
    }


class RecoveryStageCursor:
    """Track query/fetch cost and emit aggregate-only progress events."""

    def __init__(self, cursor, progress_callback=None):
        self._cursor = cursor
        self.stage = "RECOVERY_QUERY_OTHER"
        self._metrics = {}
        self._progress_callback = progress_callback
        self._operation_ordinal = 0
        self._query_plan_summaries = []

    def _capture_plan(self, query, params):
        started = time.perf_counter()
        try:
            self._cursor.execute("SAVEPOINT storyforge_plan_capture")
            self._cursor.execute("EXPLAIN (FORMAT JSON) " + str(query), params)
            row = self._cursor.fetchone()
            if row is None:
                raise ValueError("EXPLAIN_PLAN_RESULT_EMPTY")
            if isinstance(row, dict):
                payload = next(iter(row.values()))
            elif isinstance(row, (tuple, list)) and row:
                payload = row[0]
            else:
                raise ValueError("EXPLAIN_PLAN_RESULT_SHAPE_INVALID")
            summary = safe_explain_plan_summary(payload)
        except Exception:
            self._cursor.execute("ROLLBACK TO SAVEPOINT storyforge_plan_capture")
            self._cursor.execute("RELEASE SAVEPOINT storyforge_plan_capture")
            summary = {
                "query_class": "LEDGER_METADATA_QUERY",
                "plan_capture_status": "EXPLAIN_UNAVAILABLE",
                "node_types": [],
                "index_names": [],
                "b2_selected": False,
                "index_only_scan": False,
                "boundary_range_in_index_condition": False,
                "sort_node_count": 0,
                "unique_node_count": 0,
                "estimated_plan_rows": 0,
                "estimated_total_cost": 0.0,
                "plan_capture_ms": 0.0,
            }
        else:
            self._cursor.execute("RELEASE SAVEPOINT storyforge_plan_capture")
        summary["plan_capture_ms"] = round(
            (time.perf_counter() - started) * 1000, 3
        )
        self._query_plan_summaries.append(summary)

    def _emit(self, event, **fields):
        if self._progress_callback is not None:
            self._progress_callback(event, **fields)

    def _metric(self):
        return self._metrics.setdefault(self.stage, {
            "query_count": 0, "execute_ms": 0.0,
            "fetch_count": 0, "fetch_ms": 0.0, "rows_fetched": 0,
        })

    def execute(self, query, params=None):
        self.stage = recovery_query_stage(str(query))
        if ("WITH targets AS" in str(query)
                and "DISTINCT ON (e.message_id)" in str(query)
                and "public.v2_chat_message_ledger" in str(query)):
            self._capture_plan(query, params)
        metric = self._metric()
        metric["query_count"] += 1
        self._operation_ordinal += 1
        ordinal = self._operation_ordinal
        self._emit("query_started", query_class=self.stage,
                   operation="execute", operation_ordinal=ordinal)
        started = time.perf_counter()
        try:
            if params is None:
                return self._cursor.execute(query)
            return self._cursor.execute(query, params)
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            metric["execute_ms"] += elapsed
            self._emit("query_completed", query_class=self.stage,
                       operation="execute", operation_ordinal=ordinal,
                       elapsed_ms=round(elapsed, 3))

    def fetchone(self):
        metric = self._metric()
        metric["fetch_count"] += 1
        self._operation_ordinal += 1
        ordinal = self._operation_ordinal
        self._emit("query_started", query_class=self.stage,
                   operation="fetchone", operation_ordinal=ordinal)
        started = time.perf_counter()
        row = None
        try:
            row = self._cursor.fetchone()
            metric["rows_fetched"] += int(row is not None)
            return row
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            metric["fetch_ms"] += elapsed
            self._emit("query_completed", query_class=self.stage,
                       operation="fetchone", operation_ordinal=ordinal,
                       elapsed_ms=round(elapsed, 3),
                       rows_fetched=int(row is not None))

    def fetchall(self):
        metric = self._metric()
        metric["fetch_count"] += 1
        self._operation_ordinal += 1
        ordinal = self._operation_ordinal
        self._emit("query_started", query_class=self.stage,
                   operation="fetchall", operation_ordinal=ordinal)
        started = time.perf_counter()
        rows = []
        try:
            rows = self._cursor.fetchall()
            metric["rows_fetched"] += len(rows)
            return rows
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            metric["fetch_ms"] += elapsed
            self._emit("query_completed", query_class=self.stage,
                       operation="fetchall", operation_ordinal=ordinal,
                       elapsed_ms=round(elapsed, 3),
                       rows_fetched=len(rows))

    def safe_metrics(self):
        return {
            "query_classes": {
                key: {
                    "query_count": value["query_count"],
                    "execute_ms": round(value["execute_ms"], 3),
                    "fetch_count": value["fetch_count"],
                    "fetch_ms": round(value["fetch_ms"], 3),
                    "rows_fetched": value["rows_fetched"],
                }
                for key, value in sorted(self._metrics.items())
            },
            "total_query_count": sum(v["query_count"] for v in self._metrics.values()),
            "total_execute_ms": round(sum(v["execute_ms"] for v in self._metrics.values()), 3),
            "total_fetch_ms": round(sum(v["fetch_ms"] for v in self._metrics.values()), 3),
            "total_rows_fetched": sum(v["rows_fetched"] for v in self._metrics.values()),
            "sql_text_retained": False,
            "sql_parameters_retained": False,
            "query_plan_summaries": list(self._query_plan_summaries),
        }

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class SafeProgressWriter:
    """Create-only, private JSONL progress log containing aggregate metadata only."""

    def __init__(self, path: Path, output_dir: Path):
        output_root = output_dir.resolve(strict=True)
        if (path.parent.resolve(strict=True) != output_root
                or path.name in {"", ".", ".."}
                or stat.S_IMODE(output_root.stat().st_mode) != 0o700):
            raise ValueError("PROGRESS_FILE_SCOPE_INVALID")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        self._stream = os.fdopen(fd, "w", encoding="utf-8")

    def emit(self, event, **fields):
        payload = {
            "schema": "r59_gold192_history_progress_safe_v1",
            "event": event,
            **fields,
        }
        self._stream.write(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ) + "\n")
        self._stream.flush()

    def close(self):
        self._stream.close()


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


def merge_safe_metrics(metrics_rows: list[dict]) -> dict:
    merged = {}
    for metrics in metrics_rows:
        for query_class, values in metrics.get("query_classes", {}).items():
            target = merged.setdefault(query_class, {
                "query_count": 0, "execute_ms": 0.0,
                "fetch_count": 0, "fetch_ms": 0.0, "rows_fetched": 0,
            })
            for key in target:
                target[key] += values.get(key, 0)
    return {
        "query_classes": {
            key: {
                "query_count": value["query_count"],
                "execute_ms": round(value["execute_ms"], 3),
                "fetch_count": value["fetch_count"],
                "fetch_ms": round(value["fetch_ms"], 3),
                "rows_fetched": value["rows_fetched"],
            }
            for key, value in sorted(merged.items())
        },
        "total_query_count": sum(v["query_count"] for v in merged.values()),
        "total_execute_ms": round(sum(v["execute_ms"] for v in merged.values()), 3),
        "total_fetch_ms": round(sum(v["fetch_ms"] for v in merged.values()), 3),
        "total_rows_fetched": sum(v["rows_fetched"] for v in merged.values()),
        "sql_text_retained": False,
        "sql_parameters_retained": False,
        "query_plan_summaries": [
            summary for metrics in metrics_rows
            for summary in metrics.get("query_plan_summaries", [])
        ],
    }


def _validate_checkpoint_case_results(rows, expected_indices):
    if not isinstance(rows, list) or len(rows) != len(expected_indices):
        raise ValueError("SESSION_CHECKPOINT_CASE_COUNT_INVALID")
    allowed = {
        "safe_index", "result", "reason_code",
        "current_history_message_count", "current_history_suffix_role",
        "current_history_suffix_turn", "reconstructed_history_message_count",
        "history_suffix_role", "history_suffix_turn",
        "current_suffix_first_post_target_operation", "ledger_event_count",
        "history_rows_restored", "history_rows_excluded",
        "current_history_first_post_target_operation_counts",
        "current_marker_rows_with_preboundary_snapshot",
        "current_marker_rows_without_preboundary_snapshot",
        "current_marker_prior_snapshot_same_timestamp_as_boundary",
        "history_message_count", "current_history_suffix_role",
    }
    seen = set()
    count_fields = {
        "safe_index", "current_history_message_count",
        "current_history_suffix_turn", "reconstructed_history_message_count",
        "history_suffix_turn", "ledger_event_count", "history_rows_restored",
        "history_rows_excluded", "history_message_count",
        "current_marker_rows_with_preboundary_snapshot",
        "current_marker_rows_without_preboundary_snapshot",
        "current_marker_prior_snapshot_same_timestamp_as_boundary",
    }
    for row in rows:
        if not isinstance(row, dict) or set(row) - allowed:
            raise ValueError("SESSION_CHECKPOINT_CASE_SHAPE_INVALID")
        index = row.get("safe_index")
        if type(index) is not int or index not in expected_indices or index in seen:
            raise ValueError("SESSION_CHECKPOINT_INDEX_INVALID")
        seen.add(index)
        if row.get("result") not in {"HOLD", "RECOVERED"}:
            raise ValueError("SESSION_CHECKPOINT_RESULT_INVALID")
        reason = row.get("reason_code")
        if reason is not None and (
            not isinstance(reason, str) or not re.fullmatch(r"[A-Z0-9_]+", reason)
        ):
            raise ValueError("SESSION_CHECKPOINT_REASON_INVALID")
        for key in count_fields & row.keys():
            value = row[key]
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("SESSION_CHECKPOINT_COUNT_INVALID")
        for key in ("current_history_suffix_role", "history_suffix_role"):
            if row.get(key) not in {None, "user", "assistant"}:
                raise ValueError("SESSION_CHECKPOINT_ROLE_INVALID")
        operations = row.get("current_history_first_post_target_operation_counts", {})
        if (not isinstance(operations, dict)
                or any(key not in {"insert", "update_after", "update_before", "delete"}
                       or type(value) is not int or value < 0
                       for key, value in operations.items())):
            raise ValueError("SESSION_CHECKPOINT_OPERATION_COUNTS_INVALID")
    if seen != set(expected_indices):
        raise ValueError("SESSION_CHECKPOINT_INDEX_SET_INVALID")


def _load_session_checkpoint(path: Path, *, fingerprint: str,
                             session_index: int, session_count: int,
                             pilot_indices: list[int]) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("SESSION_CHECKPOINT_FILE_INVALID")
    info = path.stat()
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 5 * 1024 * 1024:
        raise ValueError("SESSION_CHECKPOINT_PERMISSIONS_INVALID")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("SESSION_CHECKPOINT_PARSE_INVALID") from None
    if not isinstance(payload, dict):
        raise ValueError("SESSION_CHECKPOINT_SHAPE_INVALID")
    checkpoint_sha = payload.pop("checkpoint_sha256", None)
    actual_sha = digest(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))
    if checkpoint_sha != actual_sha:
        raise ValueError("SESSION_CHECKPOINT_DIGEST_INVALID")
    if (payload.get("schema") != "r59_gold192_history_session_checkpoint_v1"
            or payload.get("status") != "SESSION_DIAGNOSTIC_COMPLETE"
            or payload.get("run_fingerprint") != fingerprint
            or payload.get("session_index") != session_index
            or payload.get("session_count") != session_count
            or payload.get("pilot_indices") != pilot_indices):
        raise ValueError("SESSION_CHECKPOINT_CONTEXT_MISMATCH")
    _validate_checkpoint_case_results(payload.get("case_results"), pilot_indices)
    metrics = payload.get("performance_metrics")
    if not isinstance(metrics, dict):
        raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
    metric_keys = {
        "query_classes", "total_query_count", "total_execute_ms",
        "total_fetch_ms", "total_rows_fetched",
        "sql_text_retained", "sql_parameters_retained",
        "query_plan_summaries",
    }
    if set(metrics) != metric_keys or (
        metrics.get("sql_text_retained") is not False
        or metrics.get("sql_parameters_retained") is not False
    ):
        raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
    plan_summaries = metrics.get("query_plan_summaries")
    if not isinstance(plan_summaries, list):
        raise ValueError("SESSION_CHECKPOINT_PLAN_SUMMARIES_INVALID")
    plan_keys = {
        "query_class", "plan_capture_status", "node_types", "index_names",
        "b2_selected", "index_only_scan", "boundary_range_in_index_condition",
        "sort_node_count", "unique_node_count", "estimated_plan_rows",
        "estimated_total_cost", "plan_capture_ms",
    }
    for summary in plan_summaries:
        if not isinstance(summary, dict) or set(summary) != plan_keys:
            raise ValueError("SESSION_CHECKPOINT_PLAN_SUMMARIES_INVALID")
        if (summary.get("query_class") != "LEDGER_METADATA_QUERY"
                or summary.get("plan_capture_status") not in {
                    "CAPTURED", "EXPLAIN_UNAVAILABLE"
                }
                or not isinstance(summary.get("node_types"), list)
                or not isinstance(summary.get("index_names"), list)
                or any(not isinstance(value, str) for value in (
                    summary["node_types"] + summary["index_names"]
                ))
                or any(type(summary.get(key)) is not bool for key in (
                    "b2_selected", "index_only_scan",
                    "boundary_range_in_index_condition",
                ))):
            raise ValueError("SESSION_CHECKPOINT_PLAN_SUMMARIES_INVALID")
        for key in ("sort_node_count", "unique_node_count", "estimated_plan_rows"):
            value = summary.get(key)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or value < 0):
                raise ValueError("SESSION_CHECKPOINT_PLAN_SUMMARIES_INVALID")
        for key in ("estimated_total_cost", "plan_capture_ms"):
            value = summary.get(key)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(float(value)) or value < 0):
                raise ValueError("SESSION_CHECKPOINT_PLAN_SUMMARIES_INVALID")
        if summary["plan_capture_status"] == "EXPLAIN_UNAVAILABLE" and (
            summary["node_types"] or summary["index_names"]
            or summary["b2_selected"] or summary["index_only_scan"]
            or summary["boundary_range_in_index_condition"]
        ):
            raise ValueError("SESSION_CHECKPOINT_PLAN_SUMMARIES_INVALID")
    allowed_query_classes = {
        "OWNER_SCOPE_QUERY", "TARGET_MESSAGE_QUERY", "CURRENT_HISTORY_QUERY",
        "SESSION_LINEAGE_QUERY", "LEDGER_METADATA_QUERY", "LEDGER_DETAIL_QUERY",
        "MESSAGE_QUERY", "STORY_VERSION_QUERY", "ADMIN_VERSION_QUERY",
        "RECOVERY_QUERY_OTHER",
    }
    classes = metrics.get("query_classes")
    if not isinstance(classes, dict) or set(classes) - allowed_query_classes:
        raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
    for values in classes.values():
        if not isinstance(values, dict) or set(values) != {
            "query_count", "execute_ms", "fetch_count", "fetch_ms", "rows_fetched"
        }:
            raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
        for key in ("query_count", "fetch_count", "rows_fetched"):
            if type(values[key]) is not int or values[key] < 0:
                raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
        for key in ("execute_ms", "fetch_ms"):
            value = values[key]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not (0 <= value < float("inf"))):
                raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
    for key in ("total_query_count", "total_rows_fetched"):
        if type(metrics.get(key)) is not int or metrics[key] < 0:
            raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
    for key in ("total_execute_ms", "total_fetch_ms"):
        value = metrics.get(key)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not (0 <= value < float("inf"))):
            raise ValueError("SESSION_CHECKPOINT_METRICS_INVALID")
    duplicate_indices = payload.get("duplicate_source_reverification_pilot_indices")
    duplicate_count = payload.get("duplicate_source_roots_reverified")
    if (not isinstance(duplicate_indices, list)
            or any(type(value) is not int or value not in pilot_indices
                   for value in duplicate_indices)
            or len(duplicate_indices) != len(set(duplicate_indices))
            or type(duplicate_count) is not int or duplicate_count < 0
            or len(duplicate_indices) != duplicate_count):
        raise ValueError("SESSION_CHECKPOINT_DUPLICATE_COUNT_INVALID")
    owner_count = payload.get("distinct_story_owner_count")
    if type(owner_count) is not int or owner_count < 1:
        raise ValueError("SESSION_CHECKPOINT_OWNER_COUNT_INVALID")
    elapsed = payload.get("session_elapsed_ms")
    if (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
            or not (0 <= elapsed < float("inf"))):
        raise ValueError("SESSION_CHECKPOINT_ELAPSED_INVALID")
    return payload


def _write_session_checkpoint(path: Path, payload: dict) -> str:
    checkpoint_sha = digest(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"))
    complete = {**payload, "checkpoint_sha256": checkpoint_sha}
    raw = (json.dumps(
        complete, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n").encode("utf-8")
    return create_only(path, raw)


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
        diagnose_duplicate_index: int | None = None,
        diagnose_ledger_event_counts: bool = False,
        diagnose_history_suffix: bool = False,
        progress_file: Path | None = None) -> dict:
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

    if sum((diagnostic_only, diagnose_duplicate_index is not None,
            diagnose_ledger_event_counts, diagnose_history_suffix)) > 1:
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

    if diagnose_history_suffix:
        import psycopg

        if output_dir.is_symlink() or not output_dir.is_dir():
            raise ValueError("OUTPUT_DIRECTORY_INVALID")
        if stat.S_IMODE(output_dir.stat().st_mode) != 0o700:
            raise ValueError("OUTPUT_PERMISSIONS_INVALID")
        progress_writer = (
            SafeProgressWriter(progress_file, output_dir)
            if progress_file is not None else None
        )

        def emit_progress(event, **fields):
            payload = {
                "schema": "r59_gold192_history_progress_safe_v1",
                "event": event,
                **fields,
            }
            if progress_writer is not None:
                progress_writer.emit(event, **fields)
            else:
                print(json.dumps(
                    payload, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")
                ), file=sys.stderr, flush=True)

        checkpoint_dir = output_dir / "history-suffix-checkpoints"
        try:
            checkpoint_dir.mkdir(mode=0o700)
        except FileExistsError:
            pass
        if (checkpoint_dir.is_symlink() or not checkpoint_dir.is_dir()
                or stat.S_IMODE(checkpoint_dir.stat().st_mode) != 0o700):
            if progress_writer is not None:
                progress_writer.close()
            raise ValueError("SESSION_CHECKPOINT_DIRECTORY_INVALID")

        groups = {}
        for pilot_index, case in enumerate(priority):
            locator = locator_index[case["case_id"]]
            key = (case["story_id"], locator["session_id"])
            groups.setdefault(key, []).append((pilot_index, case))
        ordered_groups = sorted(groups.items())
        input_fingerprint = digest(json.dumps({
            "input_sha256": {
                key: digest(value) for key, value in sorted(inputs.items())
            },
            "pilot": len(priority),
            "max_history": max_history,
            "max_lineage_depth": max_lineage_depth,
            "max_ledger_events": max_ledger_events,
            "algorithm_version": "sessionized-v3-target-specific-sql-first-event",
            "schema": "r59_gold192_history_session_checkpoint_v1",
        }, sort_keys=True, separators=(",", ":")).encode("utf-8"))

        all_results = []
        all_metrics = []
        verified_duplicate_indices = set()
        session_checkpoints_reused = 0
        session_checkpoints_created = 0
        owner_count = None
        stage = "CONNECT"
        tracked_cursor = None
        session_count = len(ordered_groups)
        emit_progress(
            "run_started", pilot_count=len(priority),
            session_count=session_count, max_ledger_events=max_ledger_events,
        )
        try:
            with psycopg.connect(
                dsn, autocommit=True, connect_timeout=15,
                application_name="storyforge-r60-history-diagnostic",
                keepalives=1, keepalives_idle=30,
                keepalives_interval=10, keepalives_count=3,
            ) as db:
                # Verify the exact read-only role even when every session is resumed
                # from a previously completed SAFE checkpoint.
                with db.transaction():
                    db.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                    )
                    db.execute("SET LOCAL statement_timeout = '90000ms'")
                    db.execute("SET LOCAL lock_timeout = '1000ms'")
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
                        owner_count = verify_story_owner_scope(
                            cursor,
                            sorted({case["story_id"] for case in packet_index.values()}),
                        )

                for session_number, (_session_key, entries) in enumerate(ordered_groups, 1):
                    global_indices = [index for index, _case in entries]
                    expected_indices = sorted(global_indices)
                    checkpoint_path = checkpoint_dir / (
                        f"session-{session_number:04d}-{input_fingerprint[:16]}.safe.json"
                    )
                    if checkpoint_path.exists() or checkpoint_path.is_symlink():
                        checkpoint = _load_session_checkpoint(
                            checkpoint_path, fingerprint=input_fingerprint,
                            session_index=session_number,
                            session_count=session_count,
                            pilot_indices=expected_indices,
                        )
                        duplicate_indices = checkpoint.get(
                            "duplicate_source_reverification_pilot_indices"
                        )
                        if (not isinstance(duplicate_indices, list)
                                or any(type(value) is not int
                                       or value not in expected_indices
                                       for value in duplicate_indices)
                                or len(duplicate_indices) != len(set(duplicate_indices))
                                or len(duplicate_indices) != checkpoint[
                                    "duplicate_source_roots_reverified"
                                ]):
                            raise ValueError("SESSION_CHECKPOINT_DUPLICATE_INDICES_INVALID")
                        all_results.extend(checkpoint["case_results"])
                        all_metrics.append(checkpoint["performance_metrics"])
                        verified_duplicate_indices.update(duplicate_indices)
                        if owner_count is None:
                            owner_count = checkpoint["distinct_story_owner_count"]
                        elif owner_count != checkpoint["distinct_story_owner_count"]:
                            raise ValueError("STORY_OWNER_SCOPE_DRIFT")
                        session_checkpoints_reused += 1
                        emit_progress(
                            "session_checkpoint_reused",
                            session_index=session_number,
                            session_count=session_count,
                            case_count=len(entries),
                            pilot_indices=expected_indices,
                        )
                        continue

                    emit_progress(
                        "session_started", session_index=session_number,
                        session_count=session_count, case_count=len(entries),
                        pilot_indices=expected_indices,
                    )
                    session_started = time.perf_counter()
                    session_verified_duplicates = set()
                    session_results = []
                    session_prepared = None
                    session_metrics = {}
                    session_owner_count = None
                    tracked_cursor = None
                    stage = "SESSION_TRANSACTION_BEGIN"
                    try:
                        with db.transaction():
                            db.execute(
                                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                            )
                            db.execute("SET LOCAL statement_timeout = '90000ms'")
                            db.execute("SET LOCAL lock_timeout = '1000ms'")
                            with db.cursor() as cursor:
                                tracked_cursor = RecoveryStageCursor(
                                    cursor, progress_callback=emit_progress
                                )
                                stage = "VERIFY_READ_ONLY_ROLE"
                                tracked_cursor.execute(
                                    """
                                    SELECT current_user, current_setting('transaction_read_only'),
                                           current_setting('row_security'), r.rolsuper, r.rolbypassrls
                                    FROM pg_roles AS r WHERE r.rolname = current_user
                                    """
                                )
                                role = tracked_cursor.fetchone()
                                if (role is None or role[0] != "r58_export_reader"
                                        or role[1] != "on" or role[2] != "on"
                                        or role[3] is not False or role[4] is not False):
                                    raise ValueError("DATABASE_ROLE_NOT_APPROVED")

                                stage = "VERIFY_STORY_OWNER_SCOPE"
                                session_owner_count = verify_story_owner_scope(
                                    tracked_cursor,
                                    sorted({case["story_id"] for case in packet_index.values()}),
                                )
                                if owner_count is not None and owner_count != session_owner_count:
                                    raise ValueError("STORY_OWNER_SCOPE_DRIFT")

                                session_priority = [case for _index, case in entries]
                                local_verified_indices = set()
                                for local_index, (global_index, case) in enumerate(entries):
                                    locator = locator_index[case["case_id"]]
                                    match_count = locator.get("matched_message_count")
                                    if (isinstance(match_count, int)
                                            and not isinstance(match_count, bool)
                                            and match_count == 1):
                                        continue
                                    if (not isinstance(match_count, int)
                                            or isinstance(match_count, bool)
                                            or match_count < 2):
                                        raise ValueError("SOURCE_MATCH_COUNT_INVALID")
                                    stage = "DUPLICATE_SOURCE_REVERIFICATION"
                                    proof = diagnose_duplicate_source(
                                        tracked_cursor, case, locator, max_lineage_depth
                                    )
                                    if proof.get("status") != "UNIQUE_ROOT_CANONICAL_MATCH":
                                        raise ValueError("PILOT_SOURCE_IDENTITY_HOLD")
                                    local_verified_indices.add(local_index)
                                    session_verified_duplicates.add(global_index)

                                session_cases = build_recovery_cases(
                                    session_priority, locator_index,
                                    verified_duplicate_indices=local_verified_indices,
                                )
                                stage = "HISTORY_SUFFIX_DATABASE_READ"
                                session_prepared = prepare_history_suffix_diagnostics(
                                    tracked_cursor, session_cases,
                                    max_history=max_history,
                                    max_lineage_depth=max_lineage_depth,
                                    max_ledger_events=max_ledger_events,
                                )
                                session_metrics = tracked_cursor.safe_metrics()
                    except psycopg.Error as exc:
                        sqlstate = getattr(exc, "sqlstate", None)
                        if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
                            sqlstate = None
                        failure_stage = tracked_cursor.stage if tracked_cursor is not None else stage
                        raise DatabaseFailure(
                            failure_stage, sqlstate, type(exc).__name__
                        ) from None

                    emit_progress(
                        "session_database_reads_completed",
                        session_index=session_number,
                        session_count=session_count,
                        case_count=len(entries),
                        total_query_count=session_metrics.get("total_query_count", 0),
                        total_fetch_ms=session_metrics.get("total_fetch_ms", 0.0),
                        total_rows_fetched=session_metrics.get("total_rows_fetched", 0),
                    )
                    emit_progress(
                        "session_local_reconstruction_started",
                        session_index=session_number,
                        session_count=session_count,
                        case_count=len(entries),
                    )
                    session_results = evaluate_history_suffix_diagnostics(
                        session_prepared, progress_callback=emit_progress
                    )
                    del session_prepared

                    for row in session_results:
                        local_index = row.get("safe_index")
                        if (type(local_index) is not int
                                or not 0 <= local_index < len(global_indices)):
                            raise ValueError("SESSION_RESULT_INDEX_INVALID")
                        row["safe_index"] = global_indices[local_index]
                    _validate_checkpoint_case_results(session_results, expected_indices)
                    session_elapsed_ms = round(
                        (time.perf_counter() - session_started) * 1000, 3
                    )
                    checkpoint_payload = {
                        "schema": "r59_gold192_history_session_checkpoint_v1",
                        "status": "SESSION_DIAGNOSTIC_COMPLETE",
                        "run_fingerprint": input_fingerprint,
                        "session_index": session_number,
                        "session_count": session_count,
                        "pilot_indices": expected_indices,
                        "case_results": session_results,
                        "performance_metrics": session_metrics,
                        "duplicate_source_roots_reverified": len(session_verified_duplicates),
                        "duplicate_source_reverification_pilot_indices": sorted(
                            session_verified_duplicates
                        ),
                        "distinct_story_owner_count": session_owner_count,
                        "session_elapsed_ms": session_elapsed_ms,
                    }
                    _write_session_checkpoint(checkpoint_path, checkpoint_payload)
                    all_results.extend(session_results)
                    all_metrics.append(session_metrics)
                    verified_duplicate_indices.update(session_verified_duplicates)
                    if owner_count is None:
                        owner_count = session_owner_count
                    session_checkpoints_created += 1
                    emit_progress(
                        "session_completed", session_index=session_number,
                        session_count=session_count, case_count=len(entries),
                        pilot_indices=expected_indices,
                        elapsed_ms=session_elapsed_ms,
                        recovered_count=sum(row["result"] == "RECOVERED" for row in session_results),
                        hold_count=sum(row["result"] == "HOLD" for row in session_results),
                        total_query_count=session_metrics.get("total_query_count", 0),
                        total_fetch_ms=session_metrics.get("total_fetch_ms", 0.0),
                    )
        except psycopg.Error as exc:
            sqlstate = getattr(exc, "sqlstate", None)
            if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
                sqlstate = None
            failure_stage = tracked_cursor.stage if tracked_cursor is not None else stage
            raise DatabaseFailure(failure_stage, sqlstate, type(exc).__name__) from None
        finally:
            if progress_writer is not None:
                progress_writer.close()

        all_results.sort(key=lambda row: row["safe_index"])
        if len(all_results) != len(priority):
            raise ValueError("SESSION_RESULT_COUNT_INVALID")
        return {
            "schema": "r59_gold192_history_suffix_recovery_diagnostic_safe_v1",
            "status": "HISTORY_SUFFIX_DIAGNOSTIC_COMPLETE",
            "pilot_requested": len(priority),
            "case_results": all_results,
            "session_count": session_count,
            "session_checkpoints_created": session_checkpoints_created,
            "session_checkpoints_reused": session_checkpoints_reused,
            "transaction_scope": "REPEATABLE_READ_READ_ONLY_PER_SESSION",
            "cross_session_snapshot_consistency_proven": False,
            "database_role_verified": "r58_export_reader",
            "transaction_read_only": True,
            "row_security": True,
            "role_bypassrls": False,
            "database_modified": False,
            "private_values_emitted": False,
            "performance_metrics": merge_safe_metrics(all_metrics),
            "duplicate_source_roots_reverified": len(verified_duplicate_indices),
            "distinct_story_owner_count": owner_count,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
        }

    if diagnose_ledger_event_counts:
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
                    verified_duplicate_indices = set()
                    for pilot_index, case in enumerate(priority):
                        locator = locator_index[case["case_id"]]
                        match_count = locator.get("matched_message_count")
                        if (isinstance(match_count, int) and not isinstance(match_count, bool)
                                and match_count == 1):
                            continue
                        if (not isinstance(match_count, int) or isinstance(match_count, bool)
                                or match_count < 2):
                            raise ValueError("SOURCE_MATCH_COUNT_INVALID")
                        proof = diagnose_duplicate_source(
                            cursor, case, locator, max_lineage_depth
                        )
                        if proof.get("status") != "UNIQUE_ROOT_CANONICAL_MATCH":
                            raise ValueError("PILOT_SOURCE_IDENTITY_HOLD")
                        verified_duplicate_indices.add(pilot_index)
                    cases = build_recovery_cases(
                        priority, locator_index, verified_duplicate_indices
                    )
                    grouped = {}
                    for pilot_index, case in enumerate(priority):
                        locator = locator_index[case["case_id"]]
                        key = (case["story_id"], locator["session_id"])
                        entry = grouped.setdefault(key, {"max_turn": 0, "pilot_indices": []})
                        entry["max_turn"] = max(entry["max_turn"], case["turn_index"])
                        entry["pilot_indices"].append(pilot_index)
                    session_counts = []
                    for (story_id, session_id), entry in sorted(grouped.items()):
                        cursor.execute(
                            """
                            SELECT count(*)::bigint
                            FROM public.v2_chat_message_ledger
                            WHERE story_id = %s AND session_id = %s
                              AND turn_index BETWEEN 1 AND %s
                            """,
                            (story_id, session_id, entry["max_turn"]),
                        )
                        count_row = cursor.fetchone()
                        if (not count_row or type(count_row[0]) is not int
                                or count_row[0] < 0):
                            raise ValueError("LEDGER_EVENT_COUNT_INVALID")
                        session_counts.append({
                            "pilot_indices": sorted(entry["pilot_indices"]),
                            "ledger_event_count": count_row[0],
                            "configured_limit": max_ledger_events,
                            "within_limit": count_row[0] <= max_ledger_events,
                        })
                stage = "ROLLBACK"
                db.rollback()
        except psycopg.Error as exc:
            sqlstate = getattr(exc, "sqlstate", None)
            if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
                sqlstate = None
            raise DatabaseFailure(stage, sqlstate, type(exc).__name__) from None
        return {
            "schema": "r59_gold192_ledger_event_count_diagnostic_safe_v1",
            "status": ("LEDGER_EVENT_COUNTS_WITHIN_LIMIT"
                       if all(row["within_limit"] for row in session_counts)
                       else "LEDGER_EVENT_COUNT_LIMIT_EXCEEDED"),
            "session_count": len(session_counts),
            "session_counts": session_counts,
            "duplicate_source_roots_reverified": len(verified_duplicate_indices),
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
    tracked_cursor = None
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
                tracked_cursor = RecoveryStageCursor(cursor)
                owner_count = verify_story_owner_scope(
                    tracked_cursor, sorted({case["story_id"] for case in packet_index.values()})
                )
                for pilot_index, case in enumerate(priority):
                    locator = locator_index[case["case_id"]]
                    match_count = locator.get("matched_message_count")
                    if (isinstance(match_count, int) and not isinstance(match_count, bool)
                            and match_count == 1):
                        continue
                    if (not isinstance(match_count, int) or isinstance(match_count, bool)
                            or match_count < 2):
                        raise ValueError("SOURCE_MATCH_COUNT_INVALID")
                    duplicate_proof = diagnose_duplicate_source(
                        tracked_cursor, case, locator, max_lineage_depth
                    )
                    if duplicate_proof.get("status") != "UNIQUE_ROOT_CANONICAL_MATCH":
                        raise ValueError("PILOT_SOURCE_IDENTITY_HOLD")
                    verified_duplicate_indices.add(pilot_index)
                cases = build_recovery_cases(
                    priority, locator_index, verified_duplicate_indices
                )
                recovery_started = time.perf_counter()
                recovered, case_holds = recover_cases_independently(
                    tracked_cursor, cases, max_history=max_history,
                    max_lineage_depth=max_lineage_depth,
                    max_ledger_events=max_ledger_events,
                )
                recovery_wall_ms = (time.perf_counter() - recovery_started) * 1000
            stage = "ROLLBACK"
            db.rollback()
    except psycopg.Error as exc:
        sqlstate = getattr(exc, "sqlstate", None)
        if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
            sqlstate = None
        failure_stage = tracked_cursor.stage if tracked_cursor is not None else stage
        raise DatabaseFailure(failure_stage, sqlstate, type(exc).__name__) from None

    if len(recovered) + len(case_holds) != len(cases):
        raise ValueError("RECOVERY_COUNT_INVALID")
    output_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(output_dir.stat().st_mode) != 0o700:
        raise ValueError("OUTPUT_PERMISSIONS_INVALID")

    private_payload = jsonl_bytes(recovered)
    private_name = "R59_GOLD192_HISTORICAL_CONTEXT_PRIVATE.jsonl"
    private_sha = create_only(output_dir / private_name, private_payload)
    summary_counts = Counter(row["summary_status"] for row in recovered)
    content_counts = Counter(row["story_content_version_status"] for row in recovered)
    hold_reason_counts = Counter(row["reason_code"] for row in case_holds)
    recovered_case_ids = {row["case_id"] for row in recovered}
    hold_reason_by_case = {
        row["case_id"]: row["reason_code"] for row in case_holds
    }
    ledger_session_keys = {
        (case["story_id"], case["session_id"])
        for case in cases
        if (case["case_id"] in recovered_case_ids
            or not hold_reason_by_case.get(case["case_id"], "").startswith("TARGET_"))
    }
    performance_metrics = tracked_cursor.safe_metrics()
    performance_metrics["recovery_wall_ms"] = round(recovery_wall_ms, 3)
    safe = {
        "schema": "r59_gold192_historical_context_safe_v1",
        "status": (
            "GOLD192_HISTORICAL_CONTEXT_PARTIAL__NOT_ADMITTED"
            if case_holds else "GOLD192_HISTORICAL_CONTEXT_RECOVERED__NOT_ADMITTED"
        ),
        "gold192_total": 192,
        "reviewer_ab_priority_total": len(selected),
        "pilot_requested": len(priority),
        "pilot_recovered": len(recovered),
        "pilot_held": len(case_holds),
        "case_hold_reason_counts": dict(sorted(hold_reason_counts.items())),
        "story_count": len({case["story_id"] for case in cases}),
        "recovered_story_count": len({row["story_id"] for row in recovered}),
        "candidate_session_count": len({
            (case["story_id"], case["session_id"]) for case in cases
        }),
        "story_owner_scope_verified": True,
        "distinct_story_owner_count": owner_count,
        "history_message_count_total": sum(row["history_message_count"] for row in recovered),
        "ledger_sessions_read": len(ledger_session_keys),
        # Per-case attribution may count the same Session event more than once
        # when multiple target cases share a Session. Keep those totals explicit.
        "ledger_events_attributed_to_recovered_cases_total": sum(
            row["history_reconstruction"]["ledger_event_count"] for row in recovered
        ),
        "ledger_detail_rows_attributed_to_recovered_cases_total": sum(
            row["history_reconstruction"]["ledger_detail_rows_loaded"] for row in recovered
        ),
        # These are unique rows returned by the actual batched SQL fetches.
        "ledger_metadata_rows_fetched_total": performance_metrics["query_classes"].get(
            "LEDGER_METADATA_QUERY", {}
        ).get("rows_fetched", 0),
        "ledger_detail_rows_fetched_total": performance_metrics["query_classes"].get(
            "LEDGER_DETAIL_QUERY", {}
        ).get("rows_fetched", 0),
        "ledger_events_read_total": sum(
            row["history_reconstruction"]["ledger_event_count"] for row in recovered
        ),
        "ledger_detail_rows_loaded_total": sum(
            row["history_reconstruction"]["ledger_detail_rows_loaded"] for row in recovered
        ),
        "performance_metrics": performance_metrics,
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
    parser.add_argument("--progress-file", type=Path)
    diagnostics = parser.add_mutually_exclusive_group()
    diagnostics.add_argument(
        "--diagnose-source-only", action="store_true",
        help="validate the selected source locators and exit before any database connection",
    )
    diagnostics.add_argument(
        "--diagnose-duplicate-source-index", type=int,
        help="inspect one duplicated Pilot index using the approved read-only DB role",
    )
    diagnostics.add_argument(
        "--diagnose-history-suffix", action="store_true",
        help="recover each Pilot history independently and emit aggregate-only suffix diagnostics",
    )
    diagnostics.add_argument(
        "--diagnose-ledger-event-counts", action="store_true",
        help="count scoped Pilot ledger events per Session without reading event payloads",
    )
    args = parser.parse_args()
    try:
        if (args.pilot < 0 or args.pilot > 72 or args.max_history < 1
                or not 1 <= args.max_lineage_depth <= 64
                or not 1 <= args.max_ledger_events <= 1000000):
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
            diagnose_ledger_event_counts=args.diagnose_ledger_event_counts,
            diagnose_history_suffix=args.diagnose_history_suffix,
            progress_file=args.progress_file,
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
