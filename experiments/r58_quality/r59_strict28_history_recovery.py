"""Owner-local Strict28 adapter for the shared historical recovery core.

Reads one byte-pinned private Strict28 audit ledger and a read-only Supabase
connection. It does not admit data, reconstruct the historical provider
System Prompt, access R50, run HF, or start GPU work.
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

from storyforge_gold_quality.history_recovery import (
    HistoryRecoveryError,
    recover_cases,
)

EXPECTED_CASES = 28
EXPECTED_STORIES = 2
CASE_TURN = re.compile(r"t(\d+)$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _private_read(path: Path, label: str) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError(f"{label}_PATH_INVALID")
    if any(parent.is_symlink() for parent in path.parents if parent.exists()):
        raise ValueError(f"{label}_PARENT_SYMLINK")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(f"{label}_PERMISSIONS_INVALID")
    if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise ValueError(f"{label}_PARENT_PERMISSIONS_INVALID")
    repo_root = ROOT.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if repo_root == resolved or repo_root in resolved.parents:
        raise ValueError(f"{label}_MUST_REMAIN_PRIVATE")
    return path.read_bytes()


def validate_safe_receipt(safe: dict) -> str:
    if not isinstance(safe, dict):
        raise TypeError("STRICT28_SAFE_RECEIPT_INVALID")
    ledger = safe.get("private_ledger")
    if (
        safe.get("schema") != "r59_strict28_historical_exposure_safe_v1"
        or safe.get("status") != (
            "STRICT28_HISTORICAL_TARGET_AND_CONTEXT_EXPOSURE_CLASSIFIED__NO_ADMISSION"
        )
        or safe.get("strict28_cases") != EXPECTED_CASES
        or safe.get("strict28_contexts_verified") != EXPECTED_CASES
        or safe.get("review_intersection_verified") is not True
        or safe.get("strict28_exclusions_overlap") != 0
        or safe.get("historical_sources_byte_pinned") is not True
        or safe.get("system_prompt_equivalence_proven") is not False
        or safe.get("quality_v1_admitted") != 0
        or safe.get("training_authorized") is not False
        or safe.get("gpu_started") is not False
        or safe.get("r50_accessed") is not False
        or safe.get("private_values_emitted") is not False
        or not isinstance(ledger, dict)
        or ledger.get("records") != EXPECTED_CASES
        or ledger.get("file") != "R59_STRICT28_HISTORICAL_EXPOSURE_PRIVATE.jsonl"
        or not isinstance(ledger.get("sha256"), str)
        or not HEX64.fullmatch(ledger["sha256"])
    ):
        raise ValueError("STRICT28_SAFE_RECEIPT_INVALID")
    return ledger["sha256"]


def validate_strict28_ledger(raw: bytes, expected_sha256: str) -> list[dict]:
    if not HEX64.fullmatch(expected_sha256) or _sha(raw) != expected_sha256:
        raise ValueError("STRICT28_LEDGER_SHA256_MISMATCH")
    cases = []
    try:
        for line in raw.splitlines():
            if not line.strip():
                continue
            row = json.loads(line, object_pairs_hook=_pairs)
            if not isinstance(row, dict):
                raise TypeError("STRICT28_LEDGER_ROW_INVALID")
            case_id = row.get("case_id")
            target = row.get("target_sha256")
            story_id = row.get("current_story_id")
            story_uuid = row.get("story_uuid")
            session_id = row.get("current_session_id")
            match = CASE_TURN.search(case_id) if isinstance(case_id, str) else None
            if (not isinstance(case_id, str) or not case_id
                    or not isinstance(target, str) or not HEX64.fullmatch(target)
                    or not isinstance(story_id, str) or not story_id
                    or story_uuid != story_id
                    or not isinstance(session_id, str) or not session_id
                    or match is None):
                raise ValueError("STRICT28_LEDGER_LOCATOR_INVALID")
            cases.append({
                "case_id": case_id,
                "story_id": story_id,
                "session_id": session_id,
                "turn_index": int(match.group(1)),
                "target_sha256": target,
            })
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("STRICT28_LEDGER_JSON_INVALID") from None
    if (len(cases) != EXPECTED_CASES
            or len({row["case_id"] for row in cases}) != EXPECTED_CASES
            or len({row["target_sha256"] for row in cases}) != EXPECTED_CASES
            or len({row["story_id"] for row in cases}) != EXPECTED_STORIES):
        raise ValueError("STRICT28_LEDGER_SCOPE_INVALID")
    return sorted(cases, key=lambda row: row["case_id"])


def _jsonl(rows: list[dict]) -> bytes:
    return b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        for row in rows
    )


def _create_only(path: Path, payload: bytes) -> str:
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
    return _sha(payload)


def run(ledger_path: Path, safe_report_path: Path, output_dir: Path, dsn: str, *,
        max_history: int = 20000, max_lineage_depth: int = 16,
        max_ledger_events: int = 100000) -> dict:
    if ledger_path.parent.resolve(strict=True) != safe_report_path.parent.resolve(strict=True):
        raise ValueError("STRICT28_INPUTS_NOT_SAME_RUN_DIRECTORY")
    safe_raw = _private_read(safe_report_path, "STRICT28_SAFE_RECEIPT")
    try:
        safe_receipt = json.loads(safe_raw, object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("STRICT28_SAFE_RECEIPT_JSON_INVALID") from None
    expected_ledger_sha = validate_safe_receipt(safe_receipt)
    raw = _private_read(ledger_path, "STRICT28_LEDGER")
    cases = validate_strict28_ledger(raw, expected_ledger_sha)
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    if (not output_dir.parent.is_dir() or output_dir.parent.is_symlink()
            or stat.S_IMODE(output_dir.parent.stat().st_mode) != 0o700
            or any(parent.is_symlink() for parent in output_dir.parent.parents if parent.exists())):
        raise ValueError("OUTPUT_PARENT_PERMISSIONS_INVALID")
    repo_root = ROOT.resolve(strict=True)
    resolved_parent = output_dir.parent.resolve(strict=True)
    if resolved_parent == repo_root or repo_root in resolved_parent.parents:
        raise ValueError("OUTPUT_MUST_REMAIN_PRIVATE")

    try:
        import psycopg
    except ImportError:
        raise ValueError("PSYCOPG_NOT_INSTALLED") from None

    with psycopg.connect(dsn, autocommit=False, connect_timeout=15) as db:
        db.execute("SET TRANSACTION READ ONLY")
        db.execute("SET LOCAL statement_timeout = '90000ms'")
        db.execute("SET LOCAL lock_timeout = '1000ms'")
        with db.cursor() as cursor:
            recovered = recover_cases(
                cursor, cases, max_history=max_history,
                max_lineage_depth=max_lineage_depth,
                max_ledger_events=max_ledger_events,
            )
        db.rollback()

    if len(recovered) != EXPECTED_CASES:
        raise HistoryRecoveryError("STRICT28_RECOVERY_COUNT_INVALID")

    output_dir.mkdir(mode=0o700, parents=False)
    if stat.S_IMODE(output_dir.stat().st_mode) != 0o700:
        raise ValueError("OUTPUT_PERMISSIONS_INVALID")
    private_payload = _jsonl(recovered)
    _create_only(
        output_dir / "R59_STRICT28_HISTORICAL_CONTEXT_PRIVATE.jsonl",
        private_payload,
    )

    ledger_sessions = {}
    for row in recovered:
        key = (row["story_id"], row["session_id"])
        ledger_sessions[key] = max(
            ledger_sessions.get(key, 0),
            row["history_reconstruction"]["ledger_event_count"],
        )
    summary_counts = Counter(row["summary_status"] for row in recovered)
    content_counts = Counter(row["story_content_version_status"] for row in recovered)
    admin_counts = Counter(row["story_admin_version_status"] for row in recovered)
    safe = {
        "schema": "r59_strict28_historical_context_safe_v1",
        "status": "STRICT28_HISTORICAL_CONTEXT_RECOVERED__NOT_ADMITTED",
        "strict28_cases": len(recovered),
        "target_messages_exactly_verified": len(recovered),
        "history_complete": sum(bool(row["history"]) for row in recovered),
        "history_message_count_total": sum(row["history_message_count"] for row in recovered),
        "session_lineage_nodes_total": sum(len(row["session_lineage"]) for row in recovered),
        "ledger_sessions_read": len(ledger_sessions),
        "ledger_events_read_total": sum(ledger_sessions.values()),
        "ledger_event_order_basis": "recorded_at_then_id",
        "ledger_commit_order_verified": False,
        "history_rows_restored_from_snapshot_total": sum(
            row["history_reconstruction"]["history_rows_restored_from_snapshot"]
            for row in recovered
        ),
        "history_rows_excluded_by_post_target_marker_total": sum(
            row["history_reconstruction"]["history_rows_excluded_by_post_target_marker"]
            for row in recovered
        ),
        "summary_status_counts": dict(sorted(summary_counts.items())),
        "cases_with_verified_pretarget_summaries": sum(bool(row["pretarget_summaries"]) for row in recovered),
        "story_content_version_status_counts": dict(sorted(content_counts.items())),
        "story_admin_version_status_counts": dict(sorted(admin_counts.items())),
        "historical_system_prompt_verified": False,
        "current_story_snapshot_used": False,
        "target_time_future_leakage": False,
        "private_artifact": {
            "file": "R59_STRICT28_HISTORICAL_CONTEXT_PRIVATE.jsonl",
            "records": len(recovered),
        },
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    safe_payload = (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    safe_sha = _create_only(output_dir / "R59_STRICT28_HISTORICAL_CONTEXT_SAFE.json", safe_payload)
    safe["safe_sha256"] = safe_sha
    return safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict28-ledger", required=True, type=Path)
    parser.add_argument("--safe-report", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-history", type=int, default=20000)
    parser.add_argument("--max-lineage-depth", type=int, default=16)
    parser.add_argument("--max-ledger-events", type=int, default=100000)
    args = parser.parse_args()
    try:
        if (args.max_history < 1 or not 1 <= args.max_lineage_depth <= 64
                or not 1 <= args.max_ledger_events <= 500000):
            raise ValueError("PARAMETERS_INVALID")
        dsn = os.environ.get("STORYFORGE_SUPABASE_DSN")
        if not dsn:
            raise ValueError("DB_CONNECTION_MISSING")
        result = run(
            args.strict28_ledger, args.safe_report, args.output_dir, dsn,
            max_history=args.max_history,
            max_lineage_depth=args.max_lineage_depth,
            max_ledger_events=args.max_ledger_events,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - never echo private values or DB errors
        reason = (
            str(exc) if isinstance(exc, (ValueError, TypeError, HistoryRecoveryError))
            and re.fullmatch(r"[A-Z0-9_]+", str(exc))
            else type(exc).__name__
        )
        print(json.dumps({
            "schema": "r59_strict28_historical_context_safe_v1",
            "status": "STRICT28_HISTORICAL_CONTEXT_HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
