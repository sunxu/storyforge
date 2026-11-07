"""Read-only RolePlay writer-path inventory; SAFE metadata only."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".sql"}
SCAN_DIRS = ("src/", "apps/", "packages/", "scripts/", "supabase/", "workers/")
MAX_BYTES = 4 * 1024 * 1024
DIRECT_SQL = re.compile(
    r"\b(INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO|TRUNCATE(?:\s+TABLE)?)\s+"
    r'(?:"?public"?\s*\.\s*)?"?v2_chat_messages"?\b', re.IGNORECASE,
)
TABLE_REF = re.compile(r"\.from\s*\(\s*['\"]v2_chat_messages['\"]\s*\)", re.IGNORECASE)
METHOD = re.compile(r"\.\s*(insert|update|delete|upsert)\s*\(", re.IGNORECASE)
RPC_CALL = re.compile(r"\.rpc\s*\(\s*['\"]([a-z][a-z0-9_]+)['\"]", re.IGNORECASE)
FUNCTION = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+"
    r'(?:(?:"?public"?)\s*\.\s*)?"?([a-z_][a-z0-9_]*)"?\s*\(', re.IGNORECASE,
)
TRIGGER = re.compile(r"\bCREATE\s+(?:CONSTRAINT\s+)?TRIGGER\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
RPC_RELEVANT = re.compile(
    r"(?:v2|chat|message|reply|stream|turn|session|fork|rewind|retry|import|claim)", re.IGNORECASE,
)


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL)


def lines_at(contents: str, start: int) -> int:
    return contents.count("\n", 0, start) + 1


def capture(path: str, source: str) -> list[dict]:
    results = []
    for m in DIRECT_SQL.finditer(source):
        results.append({"path": path, "line": lines_at(source, m.start()),
                        "kind": "SQL_MESSAGE_WRITE",
                        "operation": re.sub(r"\s+", "_", m.group(1).upper())})
    # Candidate analysis only: full AST / dynamic SQL still require manual review.
    for m in TABLE_REF.finditer(source):
        tail = source[m.end():min(len(source), m.end() + 1600)]
        statement_end = re.search(r";\s*(?:\n|$)", tail)
        if statement_end:
            tail = tail[:statement_end.start()]
        operations = sorted({x.group(1).upper() for x in METHOD.finditer(tail)})
        results.append({"path": path, "line": lines_at(source, m.start()),
                        "kind": "SUPABASE_MESSAGE_TABLE",
                        "operations_candidate": operations or ["READ_OR_UNKNOWN"]})
    for m in RPC_CALL.finditer(source):
        if RPC_RELEVANT.search(m.group(1)):
            results.append({"path": path, "line": lines_at(source, m.start()),
                            "kind": "RPC_CALL_CANDIDATE", "function": m.group(1)})
    if path.endswith(".sql"):
        for m in FUNCTION.finditer(source):
            if RPC_RELEVANT.search(m.group(1)):
                results.append({"path": path, "line": lines_at(source, m.start()),
                                "kind": "SQL_FUNCTION_DEFINITION", "function": m.group(1)})
        if re.search(r"\bEXECUTE\b", source, re.IGNORECASE) and "v2_chat_messages" in source:
            results.append({"path": path, "line": 0, "kind": "DYNAMIC_SQL_REVIEW_REQUIRED"})
        for m in TRIGGER.finditer(source):
            if "v2_chat_messages" in source[max(0, m.start() - 100):m.start() + 800]:
                results.append({"path": path, "line": lines_at(source, m.start()),
                                "kind": "TRIGGER_DEFINITION_CANDIDATE", "trigger": m.group(1)})
    return results


def run(repo: Path) -> dict:
    root = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if root != repo.resolve():
        raise ValueError("REPO_PATH_NOT_ROOT")
    if "roleplay" not in git(root, "remote", "-v").decode(errors="replace").lower():
        raise ValueError("ROLEPLAY_REMOTE_NOT_VERIFIED")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    tracked = git(root, "ls-files", "-z").decode(errors="surrogateescape").split("\0")
    paths = sorted(p for p in tracked if p and p.startswith(SCAN_DIRS)
                   and Path(p).suffix.lower() in EXTENSIONS)
    results, skipped = [], []
    for path in paths:
        file = root / path
        try:
            if file.is_symlink() or not file.is_file():
                skipped.append({"path": path, "reason": "MISSING_OR_SYMLINK"})
                continue
            if file.stat().st_size > MAX_BYTES:
                skipped.append({"path": path, "reason": "FILE_TOO_LARGE"})
                continue
            try:
                source = file.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                skipped.append({"path": path, "reason": "NON_UTF8"})
                continue
            results.extend(capture(path, source))
        except OSError:
            skipped.append({"path": path, "reason": "READ_ERROR"})
    results.sort(key=lambda x: (str(x["path"]), int(x["line"]), str(x["kind"])))
    dirty = bool(git(root, "status", "--porcelain"))
    return {
        "schema": "storyforge_r60_t1_roleplay_writer_inventory_safe_v1",
        "status": "STATIC_SCAN_INCOMPLETE" if skipped or dirty else "STATIC_SCAN_COMPLETE_NOT_CERTIFIED",
        "head_sha": head, "worktree_dirty": dirty,
        "tracked_source_files_scanned": len(paths) - len(skipped),
        "tracked_source_files_selected": len(paths),
        "skipped_count": len(skipped), "skipped": skipped,
        "counts": dict(sorted(Counter(str(x["kind"]) for x in results).items())),
        "findings": results, "database_connected": False, "database_modified": False,
        "private_values_emitted": False, "ledger_commit_order_verified": False,
        "ledger_trigger_continuity_verified": False, "training_authorized": False,
        "gpu_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roleplay-repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path,
                        help="New local SAFE JSON output; never overwrites existing files")
    args = parser.parse_args()
    if args.output.exists() or not args.output.parent.is_dir():
        print("T1_OUTPUT_PATH_INVALID", file=sys.stderr)
        return 2
    try:
        report = run(args.roleplay_repo)
    except (subprocess.CalledProcessError, ValueError, OSError):
        print("T1_INPUT_REPO_INVALID", file=sys.stderr)
        return 2
    payload = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    with args.output.open("xb") as output:
        output.write(payload)
    print(json.dumps({
        "status": report["status"], "head_sha": report["head_sha"],
        "tracked_source_files_scanned": report["tracked_source_files_scanned"],
        "skipped_count": report["skipped_count"], "counts": report["counts"],
        "safe_sha256": hashlib.sha256(payload).hexdigest(),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
