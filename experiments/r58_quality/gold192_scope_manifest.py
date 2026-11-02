"""Create private Gold192 eligibility scope manifest, not SFT training data."""
import argparse
import json
import os
import stat
from pathlib import Path

from gold192_scope_exclusion import inspect_scope
from legacy_gold_target_reuse import private_file, safe_reason


def build_scope(queue_path):
    records = []
    with open(queue_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                records.append({
                    "case_id": row["case_id"],
                    "scope_status": (
                        "EXCLUDED_WORLD_ID_UNRESOLVED"
                        if row["reason_code"] == "WORLD_OR_TARGET_IDENTITY_HOLD"
                        else "CANDIDATE_ONLY_QUALITY_HOLD"
                    ),
                    "quality_v1_admitted": False,
                    "training_authorized": False,
                })
    return records


def write_manifest(path, root, rows):
    root_resolved = root.resolve()
    parent_resolved = path.parent.resolve()
    if (not path.is_absolute() or path.is_symlink() or path.exists()
            or not path.parent.is_dir() or path.parent.is_symlink()
            or stat.S_IMODE(path.parent.stat().st_mode) & 0o077
            or root_resolved == parent_resolved or root_resolved in parent_resolved.parents):
        raise ValueError("SCOPE_OUTPUT_INVALID")
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--private-tasks", type=Path, required=True)
    p.add_argument("--private-queue", type=Path, required=True)
    p.add_argument("--private-output", type=Path, required=True)
    args = p.parse_args()
    try:
        repo = args.repo_root.resolve()
        tasks = private_file(args.private_tasks, repo)
        queue = private_file(args.private_queue, repo)
        if tasks.resolve() == queue.resolve():
            raise ValueError("SCOPE_INPUTS_NOT_DISTINCT")
        receipt = inspect_scope(tasks, queue)
        rows = build_scope(queue)
        task_ids = set()
        with open(tasks, encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    task_ids.add(json.loads(line)["case_id"])
        if (len(rows) != 195 or len(task_ids) != 195
                or {r["case_id"] for r in rows} != task_ids
                or sum(r["scope_status"] == "EXCLUDED_WORLD_ID_UNRESOLVED" for r in rows) != 3
                or sum(r["scope_status"] == "CANDIDATE_ONLY_QUALITY_HOLD" for r in rows) != 192):
            raise ValueError("SCOPE_COUNT_INVALID")
        write_manifest(args.private_output, repo, rows)
        receipt["status"] = "GOLD192_PRIVATE_SCOPE_WRITTEN__QUALITY_HOLD"
        receipt["private_candidate_artifact_written"] = True
        receipt["scope_receipt_only"] = False
        receipt["private_candidate_scope_written"] = True
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        allowed = {"SCOPE_INPUTS_NOT_DISTINCT", "SCOPE_OUTPUT_INVALID",
                   "SCOPE_COUNT_INVALID", "SCOPE_SET_MISMATCH",
                   "SCOPE_EXPECTED_COUNTS_MISMATCH", "SCOPE_TASK_INVALID",
                   "SCOPE_QUEUE_INVALID"}
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) in allowed else safe_reason(exc)
        print(json.dumps({
            "schema": "r58_gold192_private_scope_manifest_safe_v1",
            "status": "GOLD192_PRIVATE_SCOPE_INVALID__HOLD",
            "reason_code": reason,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
