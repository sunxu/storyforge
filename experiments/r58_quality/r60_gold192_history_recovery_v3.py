"""R60 Canonical A V3 adapter for read-only Gold192 Ledger history recovery.

This adapter consumes the V3 source receipt and frozen V3 reviewer inputs.
It re-verifies duplicate exact matches against PostgreSQL before recovery.
It never admits Quality-v1 data, compiles SFT, accesses R50, or starts GPU work.
"""
from __future__ import annotations

import argparse
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

try:
    from . import r59_gold192_history_recovery as recovery
    from . import r60_gold192_supabase_extract_v3 as source
except ImportError:
    import r59_gold192_history_recovery as recovery
    import r60_gold192_supabase_extract_v3 as source

from storyforge_gold_quality.history_recovery import recover_cases_independently

SCHEMA = "r60_gold192_history_recovery_v3_safe_v1"
MAX_LEDGER_EVENTS_HARD = 1_000_000
MAX_INPUT_BYTES = 160 * 1024 * 1024


def _read_private(path: Path, label: str) -> bytes:
    return recovery.private_bytes(path, label)


def _parse_json(raw: bytes, label: str) -> dict:
    return recovery.parse_json(raw, label)


def _parse_jsonl(raw: bytes, label: str) -> list[dict]:
    return recovery.parse_jsonl(raw, label)


def _validate_source_receipt(safe: dict, locator_raw: bytes) -> None:
    if (
        safe.get("schema") != "r60_gold192_supabase_extract_v3_safe_v1"
        or safe.get("status") != "SOURCE_EXTRACTED__NOT_QUALITY_ADMITTED"
        or safe.get("gold192") != 192
        or safe.get("quality_v1_admitted") != 0
        or safe.get("training_authorized") is not False
        or safe.get("gpu_started") is not False
        or safe.get("database_modified") is not False
        or safe.get("private_values_emitted") is not False
    ):
        raise ValueError("SOURCE_SAFE_RECEIPT_INVALID")
    artifact = safe.get("artifacts", {}).get("R60_SOURCE_LOCATORS_192.jsonl")
    if (
        not isinstance(artifact, dict)
        or artifact.get("records") != 192
        or artifact.get("sha256") != recovery.digest(locator_raw)
    ):
        raise ValueError("SOURCE_LOCATOR_PIN_MISMATCH")


def _load_inputs(args):
    raw = {
        "REVIEWER_A": _read_private(args.reviewer_a, "REVIEWER_A"),
        "REVIEWER_B": _read_private(args.reviewer_b, "REVIEWER_B"),
        "EXCLUSIONS": _read_private(args.exclusions, "EXCLUSIONS"),
        "SOURCE_PACKETS": _read_private(args.source_packets, "SOURCE_PACKETS"),
        "SOURCE_LOCATORS": _read_private(args.source_locators, "SOURCE_LOCATORS"),
        "SOURCE_SAFE": _read_private(args.source_safe, "SOURCE_SAFE"),
    }
    if args.source_locators.parent.resolve(strict=True) != args.source_safe.parent.resolve(strict=True):
        raise ValueError("SOURCE_ARTIFACTS_NOT_SAME_RUN")
    pins = {
        "REVIEWER_A": source.A_SHA,
        "REVIEWER_B": source.B_SHA,
        "EXCLUSIONS": source.EX_SHA,
        "SOURCE_PACKETS": source.PACKETS_SHA,
    }
    for label, expected in pins.items():
        if recovery.digest(raw[label]) != expected:
            raise ValueError(label + "_SHA_MISMATCH")

    safe = _parse_json(raw["SOURCE_SAFE"], "SOURCE_SAFE")
    _validate_source_receipt(safe, raw["SOURCE_LOCATORS"])
    reviewer_a = _parse_json(raw["REVIEWER_A"], "REVIEWER_A")
    reviewer_b = _parse_json(raw["REVIEWER_B"], "REVIEWER_B")
    exclusions = [
        json.loads(line) for line in raw["EXCLUSIONS"].splitlines() if line.strip()
    ]
    packet_rows = _parse_jsonl(raw["SOURCE_PACKETS"], "SOURCE_PACKETS")
    packet_index = source.index_packets(packet_rows)
    selected = source.select_candidates(reviewer_a, reviewer_b, exclusions, packet_index)
    priority = source.choose_pilot(selected, args.pilot)
    locator_rows = _parse_jsonl(raw["SOURCE_LOCATORS"], "SOURCE_LOCATORS")
    locator_index = recovery.validate_locators(locator_rows, packet_index)
    return raw, safe, packet_index, selected, priority, locator_index


def _precheck_candidate(case: dict, locator: dict) -> str | None:
    if locator.get("source_status") != "EXACT_MATCH":
        return "SOURCE_IDENTITY_NOT_CANONICAL"
    count = locator.get("matched_message_count")
    if type(count) is not int or count < 1:
        return "SOURCE_MATCH_COUNT_INVALID"
    if not isinstance(locator.get("message_id"), str) or not locator["message_id"]:
        return "SOURCE_LOCATOR_INCOMPLETE"
    if not isinstance(locator.get("session_id"), str) or not locator["session_id"]:
        return "SOURCE_LOCATOR_INCOMPLETE"
    if (
        locator.get("story_id") != case.get("story_id")
        or locator.get("turn_index") != case.get("turn_index")
        or locator.get("target_sha256") != case.get("target_sha256")
    ):
        return "SOURCE_LOCATOR_IDENTITY_MISMATCH"
    return None


def _duplicate_target_statuses_valid(rows, expected_count: int, target_sha256: str) -> str | None:
    exact = [
        row for row in rows
        if isinstance(row, (tuple, list)) and len(row) == 3
        and isinstance(row[1], str)
        and source.sha_text(row[1]) == target_sha256
    ]
    if len(exact) != expected_count:
        return "DUPLICATE_SOURCE_MATCH_COUNT_DRIFT"
    if any(row[2] != "completed" for row in exact):
        return "DUPLICATE_TARGET_STATUS_DRIFT"
    return None


def _reverify_duplicate_source(cursor, case: dict, locator: dict) -> dict:
    cursor.execute(
        """
        SELECT id::text AS message_id, content, status
        FROM public.v2_chat_messages
        WHERE story_id = %s AND turn_index = %s AND role = 'assistant'
        """,
        (case["story_id"], case["turn_index"]),
    )
    reason = _duplicate_target_statuses_valid(
        cursor.fetchall(), locator["matched_message_count"], case["target_sha256"]
    )
    if reason:
        return {"status": "HOLD", "reason": reason}
    return recovery.diagnose_duplicate_source(
        cursor, case, locator, max_lineage_depth=16
    )


def _verify_and_build_cases(cursor, priority: list[dict], locator_index: dict):
    eligible = []
    duplicate_indices = set()
    holds = []
    duplicate_verified = 0
    for original_index, case in enumerate(priority):
        locator = locator_index[case["case_id"]]
        reason = _precheck_candidate(case, locator)
        if reason:
            holds.append({"case_id": case["case_id"], "reason_code": reason})
            continue
        match_count = locator["matched_message_count"]
        if match_count > 1:
            try:
                proof = _reverify_duplicate_source(cursor, case, locator)
            except ValueError:
                holds.append({
                    "case_id": case["case_id"],
                    "reason_code": "DUPLICATE_SOURCE_REVERIFICATION_FAILED",
                })
                continue
            if proof.get("status") != "UNIQUE_ROOT_CANONICAL_MATCH":
                holds.append({
                    "case_id": case["case_id"],
                    "reason_code": "DUPLICATE_SOURCE_LINEAGE_NOT_UNAMBIGUOUS",
                })
                continue
            duplicate_indices.add(len(eligible))
            duplicate_verified += 1
        eligible.append(case)

    if not eligible:
        return [], holds, duplicate_verified
    built = recovery.build_recovery_cases(
        eligible, locator_index, verified_duplicate_indices=duplicate_indices
    )
    return built, holds, duplicate_verified


def _connect_and_verify(db, cursor):
    db.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
    db.execute("SET LOCAL statement_timeout = '90000ms'")
    db.execute("SET LOCAL lock_timeout = '1000ms'")
    cursor.execute(
        """
        SELECT current_user, current_setting('transaction_read_only'),
               current_setting('row_security'), r.rolsuper, r.rolbypassrls
        FROM pg_roles AS r WHERE r.rolname = current_user
        """
    )
    role = cursor.fetchone()
    if (
        role is None or role[0] != "r58_export_reader"
        or role[1] != "on" or role[2] != "on"
        or role[3] is not False or role[4] is not False
    ):
        raise ValueError("DATABASE_ROLE_NOT_APPROVED")


def _ledger_counts(cursor, cases: list[dict], priority: list[dict]) -> list[dict]:
    grouped = {}
    for case in cases:
        key = (case["story_id"], case["session_id"])
        entry = grouped.setdefault(key, {"max_turn": 0, "indices": []})
        entry["max_turn"] = max(entry["max_turn"], case["turn_index"])
        entry["indices"].append(
            next(i for i, candidate in enumerate(priority)
                 if candidate["case_id"] == case["case_id"])
        )
    rows = []
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
        value = cursor.fetchone()
        if not value or type(value[0]) is not int or value[0] < 0:
            raise ValueError("LEDGER_EVENT_COUNT_INVALID")
        rows.append({
            "pilot_indices": sorted(entry["indices"]),
            "ledger_event_count": value[0],
        })
    return rows


def _safe_base(priority, selected, owner_count, duplicate_verified, cases, identity_holds):
    return {
        "schema": SCHEMA,
        "pilot_requested": len(priority),
        "priority_candidates": len(selected),
        "candidate_policy": "EXPLICIT_CASE_LEVEL_SCORED_A_V3_PASS_AND_B_PASS_MINUS_11_EXCLUSIONS",
        "source_identity_eligible": len(cases),
        "source_identity_held": len(identity_holds),
        "source_identity_hold_reason_counts": dict(sorted(
            Counter(row["reason_code"] for row in identity_holds).items()
        )),
        "duplicate_source_roots_reverified": duplicate_verified,
        "distinct_story_owner_count": owner_count,
        "transaction_scope": "REPEATABLE_READ_READ_ONLY_PER_RUN",
        "database_role_verified": "r58_export_reader",
        "transaction_read_only": True,
        "row_security": True,
        "role_bypassrls": False,
        "ledger_commit_order_verified": False,
        "ledger_trigger_continuity_verified": False,
        "historical_system_prompt_verified": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "database_modified": False,
        "private_values_emitted": False,
    }


def _validate_output_target(output_dir: Path | None) -> None:
    if output_dir is None:
        raise ValueError("OUTPUT_DIRECTORY_REQUIRED")
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    parent = output_dir.parent
    if (
        not parent.is_dir() or parent.is_symlink()
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
    ):
        raise ValueError("OUTPUT_PARENT_PERMISSIONS_INVALID")
    root_repo = Path(__file__).resolve().parents[2]
    resolved_parent = parent.resolve(strict=True)
    if resolved_parent == root_repo or root_repo in resolved_parent.parents:
        raise ValueError("OUTPUT_MUST_REMAIN_PRIVATE")


def _write_outputs(output_dir: Path, recovered: list[dict], holds: list[dict],
                   packet_index: dict, safe: dict) -> None:
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    parent = output_dir.parent
    if (
        not parent.is_dir() or parent.is_symlink()
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
    ):
        raise ValueError("OUTPUT_PARENT_PERMISSIONS_INVALID")
    root_repo = Path(__file__).resolve().parents[2]
    if parent.resolve(strict=True) == root_repo or root_repo in parent.resolve(strict=True).parents:
        raise ValueError("OUTPUT_MUST_REMAIN_PRIVATE")
    output_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(output_dir.stat().st_mode) != 0o700:
        raise ValueError("OUTPUT_PERMISSIONS_INVALID")

    private_recovered = []
    for row in recovered:
        packet = packet_index[row["case_id"]]
        private_recovered.append({
            **row,
            "target_assistant_text": packet["target_assistant_text"],
            "history_recovery_status": "FULL_HISTORY_RECOVERED",
            "training_admitted": False,
        })
    files = {
        "R60_HISTORY_CONTEXT_PRIVATE.jsonl": recovery.jsonl_bytes(private_recovered),
        "R60_HISTORY_HOLDS_PRIVATE.jsonl": recovery.jsonl_bytes(holds),
    }
    artifacts = {}
    for name, payload in files.items():
        artifacts[name] = {
            "records": len(private_recovered) if "CONTEXT" in name else len(holds),
            "sha256": recovery.create_only(output_dir / name, payload),
        }
    safe["artifacts"] = artifacts
    safe["pilot_recovered"] = len(recovered)
    safe["pilot_held"] = len(holds)
    safe["case_hold_reason_counts"] = dict(sorted(
        Counter(row["reason_code"] for row in holds).items()
    ))
    safe["full_history_recovered"] = len(recovered)
    safe["verified_window_recovered"] = 0
    safe["verified_window_implementation_status"] = "NOT_IMPLEMENTED"
    safe["status"] = (
        "GOLD192_HISTORICAL_CONTEXT_RECOVERED__NOT_ADMITTED"
        if recovered and not holds
        else "GOLD192_HISTORICAL_CONTEXT_PARTIAL__NOT_ADMITTED"
        if recovered
        else "GOLD192_HISTORICAL_CONTEXT_HOLD"
    )
    payload = (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    recovery.create_only(output_dir / "R60_HISTORY_SAFE.json", payload)


def run(args) -> dict:
    if args.pilot < 0 or args.pilot > 192:
        raise ValueError("PILOT_PARAMETER_INVALID")
    if args.max_ledger_events < 1 or args.max_ledger_events > MAX_LEDGER_EVENTS_HARD:
        raise ValueError("LEDGER_EVENT_LIMIT_INVALID")
    if not args.diagnose_source_only and not args.diagnose_ledger_event_counts:
        _validate_output_target(args.output_dir)
    _raw, _source_safe, packet_index, selected, priority, locator_index = _load_inputs(args)

    if args.diagnose_source_only:
        counts = Counter(locator_index[case["case_id"]]["source_status"] for case in priority)
        return {
            "schema": "r60_gold192_history_source_preflight_v3_safe_v1",
            "status": "SOURCE_IDENTITY_PREFLIGHT_COMPLETE__NO_DATABASE",
            "pilot_requested": len(priority),
            "source_status_counts": dict(sorted(counts.items())),
            "multiple_match_cases": sum(
                locator_index[case["case_id"]]["matched_message_count"] > 1
                for case in priority
            ),
            "database_connected": False,
            "database_modified": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "private_values_emitted": False,
        }

    dsn = os.environ.get(args.dsn_env)
    if not dsn:
        raise ValueError("DB_CONNECTION_MISSING")
    import psycopg

    tracked = None
    try:
        with psycopg.connect(
            dsn, autocommit=False, connect_timeout=15,
            application_name="storyforge-r60-gold192-history-v3",
            keepalives=1, keepalives_idle=30,
            keepalives_interval=10, keepalives_count=3,
        ) as db:
            with db.cursor() as cursor:
                _connect_and_verify(db, cursor)
                owner_count = recovery.verify_story_owner_scope(
                    cursor, sorted({case["story_id"] for case in packet_index.values()})
                )
            with db.cursor() as cursor:
                tracked = recovery.RecoveryStageCursor(cursor)
                cases, identity_holds, duplicate_verified = _verify_and_build_cases(
                    tracked, priority, locator_index
                )
                safe = _safe_base(
                    priority, selected, owner_count, duplicate_verified,
                    cases, identity_holds,
                )
                counts = _ledger_counts(tracked, cases, priority) if cases else []
                over_limit = [
                    row for row in counts
                    if row["ledger_event_count"] > args.max_ledger_events
                ]
                safe["session_count"] = len(counts)
                safe["session_event_counts"] = [
                    {
                        "pilot_indices": row["pilot_indices"],
                        "ledger_event_count": row["ledger_event_count"],
                        "configured_limit": args.max_ledger_events,
                        "within_limit": row["ledger_event_count"] <= args.max_ledger_events,
                    }
                    for row in counts
                ]
                if args.diagnose_ledger_event_counts:
                    db.rollback()
                    safe["status"] = (
                        "LEDGER_EVENT_COUNTS_WITHIN_LIMIT"
                        if not over_limit else "LEDGER_EVENT_COUNT_LIMIT_EXCEEDED"
                    )
                    safe["database_modified"] = False
                    return safe
                if over_limit:
                    db.rollback()
                    safe["status"] = "HISTORY_RECOVERY_BLOCKED_EVENT_LIMIT"
                    safe["recovery_started"] = False
                    return safe
                if not cases:
                    db.rollback()
                    safe["status"] = "GOLD192_HISTORICAL_CONTEXT_HOLD"
                    safe["pilot_recovered"] = 0
                    safe["pilot_held"] = len(identity_holds)
                    safe["case_hold_reason_counts"] = dict(sorted(
                        Counter(row["reason_code"] for row in identity_holds).items()
                    ))
                    return safe
                recovered, recovery_holds = recover_cases_independently(
                    tracked, cases, max_history=args.max_history,
                    max_lineage_depth=16,
                    max_ledger_events=args.max_ledger_events,
                )
                metrics = tracked.safe_metrics()
                db.rollback()
        holds = identity_holds + recovery_holds
        safe["performance_metrics"] = metrics
        safe["recovery_started"] = True
        safe["ledger_commit_order_verified"] = False
        safe["ledger_trigger_continuity_verified"] = False
        safe["historical_system_prompt_verified"] = False
        safe["database_modified"] = False
        safe["private_values_emitted"] = False
        _write_outputs(args.output_dir, recovered, holds, packet_index, safe)
        # The SAFE receipt is the only stdout payload; private histories stay local.
        return safe
    except psycopg.Error as exc:
        sqlstate = getattr(exc, "sqlstate", None)
        if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
            sqlstate = None
        return {
            "schema": SCHEMA,
            "status": "HISTORY_RECOVERY_FAILED__HOLD",
            "database_failure_phase": tracked.stage if tracked else "DATABASE",
            "database_exception_type": type(exc).__name__,
            "database_sqlstate": sqlstate,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "private_values_emitted": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--exclusions", type=Path, required=True)
    parser.add_argument("--source-packets", type=Path, required=True)
    parser.add_argument("--source-locators", type=Path, required=True)
    parser.add_argument("--source-safe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--pilot", type=int, default=7)
    parser.add_argument("--max-history", type=int, default=20000)
    parser.add_argument("--max-ledger-events", type=int, default=100000)
    parser.add_argument("--dsn-env", default="STORYFORGE_SUPABASE_DSN")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--diagnose-source-only", action="store_true")
    modes.add_argument("--diagnose-ledger-event-counts", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if result.get("status") in {
            "HISTORY_RECOVERY_FAILED__HOLD", "HISTORY_RECOVERY_BLOCKED_EVENT_LIMIT",
            "GOLD192_HISTORICAL_CONTEXT_HOLD",
        }:
            return 42
        return 0
    except Exception as exc:  # noqa: BLE001 - never emit private values
        reason = (
            str(exc) if isinstance(exc, ValueError)
            and re.fullmatch(r"[A-Z0-9_]+", str(exc))
            else type(exc).__name__
        )
        print(json.dumps({
            "schema": SCHEMA,
            "status": "HISTORY_RECOVERY_FAILED__HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "database_modified": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
