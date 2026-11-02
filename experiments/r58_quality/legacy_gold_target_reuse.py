"""R58 SAFE target-level Gold87/108 identity matching; no Quality-v1 admission."""
import argparse
import csv
import hashlib
import json
import os
import re
import stat
from collections import Counter, defaultdict
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "r58_gold195_six_dimension_review_task_private_v1"
SAFE_HOLD_CODES = frozenset({
    "PRIVATE_PATH_INVALID", "PRIVATE_PERMISSION_INVALID", "PRIVATE_TOO_LARGE",
    "PRIVATE_PARENT_INVALID", "PRIVATE_INSIDE_REPO", "PRIVATE_OUTPUT_INVALID",
    "LEGACY_INDEX_INVALID", "LEGACY_IDENTITY_INVALID", "LEGACY_DUPLICATE_ID",
    "LEGACY_87_COLUMN_INVALID", "LEGACY_108_COLUMN_INVALID",
    "LEGACY_87_ROW_COUNT_INVALID", "LEGACY_108_ROW_COUNT_INVALID",
    "LEGACY_EVIDENCE_INVALID", "LEGACY_EVIDENCE_COUNT_INVALID",
    "LEGACY_EVIDENCE_ID_SET_MISMATCH", "TASK_SCHEMA_OR_ID_INVALID",
    "TASK_CONTENT_INVALID", "TASK_COUNT_INVALID",
})

def safe_reason(error):
    # Never echo exception text containing a private filename, key or value.
    if isinstance(error, ValueError) and str(error) in SAFE_HOLD_CODES:
        return str(error)
    if isinstance(error, FileNotFoundError):
        return "INPUT_FILE_NOT_FOUND"
    if isinstance(error, PermissionError):
        return "INPUT_FILE_ACCESS_DENIED"
    if isinstance(error, (OSError, UnicodeError, csv.Error)):
        return "INPUT_IO_OR_ENCODING_INVALID"
    return "INPUT_SCHEMA_OR_JSON_INVALID"


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")

def private_file(path, repo):
    p = Path(path)
    if not p.is_absolute() or p.is_symlink() or not p.is_file():
        raise ValueError("PRIVATE_PATH_INVALID")
    if p.stat().st_nlink != 1 or stat.S_IMODE(p.stat().st_mode) != 0o600:
        raise ValueError("PRIVATE_PERMISSION_INVALID")
    if p.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("PRIVATE_TOO_LARGE")
    if p.parent.is_symlink() or stat.S_IMODE(p.parent.stat().st_mode) & 0o077:
        raise ValueError("PRIVATE_PARENT_INVALID")
    if repo == p.resolve() or repo in p.resolve().parents:
        raise ValueError("PRIVATE_INSIDE_REPO")
    return p

def index_rows(path, cohort):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    cols = ("story_id", "sample_target_sha256", "review_A", "review_B", "sample_id") if cohort == 87 else (
        "story_id", "target_sha256", "reviewer1_decision", "reviewer2_decision", "candidate_id")
    if not rows or not set(cols).issubset(rows[0]):
        raise ValueError(f"LEGACY_{cohort}_COLUMN_INVALID")
    if len(rows) != cohort:
        raise ValueError(f"LEGACY_{cohort}_ROW_COUNT_INVALID")
    out = []
    for row in rows:
        world, digest, a, b, ident = (row.get(k, "").strip() for k in cols)
        if not world or not SHA.fullmatch(digest) or not ident:
            raise ValueError("LEGACY_IDENTITY_INVALID")
        out.append((world, digest, cohort, ident, a == b == "ACCEPT"))
    if len({(r[2], r[3]) for r in out}) != len(out):
        raise ValueError("LEGACY_DUPLICATE_ID")
    return out

def review108(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            ident = row["candidate_id"]
            if not isinstance(ident, str) or not ident or ident in out:
                raise ValueError("LEGACY_EVIDENCE_INVALID")
            out[ident] = (
                row.get("reviewer1_decision") == "ACCEPT"
                and row.get("reviewer2_decision") == "ACCEPT"
                and all(isinstance(row.get(k), str) and row[k].strip()
                        for k in ("reviewer1_evidence", "reviewer2_evidence",
                                  "reviewer1_scores", "reviewer2_scores"))
            )
    if len(out) != 108:
        raise ValueError("LEGACY_EVIDENCE_COUNT_INVALID")
    return out

def inspect(gold87, gold108, tasks, evidence108=None):
    legacy = index_rows(gold87, 87) + index_rows(gold108, 108)
    reviews = review108(evidence108) if evidence108 else None
    if reviews is not None and {r[3] for r in legacy if r[2] == 108} != set(reviews):
        raise ValueError("LEGACY_EVIDENCE_ID_SET_MISMATCH")
    lookup = defaultdict(list)
    hashes = defaultdict(set)
    for row in legacy:
        lookup[row[:2]].append(row)
        hashes[row[1]].add(row[0])
    counts = Counter(gold87_rows=87, gold108_rows=108, legacy_rows=195)
    counts["legacy_double_accept_indexed"] = sum(r[4] for r in legacy)
    counts["legacy_duplicate_target_keys"] = sum(max(0, len(v)-1) for v in lookup.values())
    queue = []
    seen = set()
    with open(tasks, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            ident, world, target = r.get("case_id"), r.get("story_uuid"), r.get("target_sha256")
            if r.get("schema") != SCHEMA or not isinstance(ident, str) or not ident or ident in seen:
                raise ValueError("TASK_SCHEMA_OR_ID_INVALID")
            seen.add(ident)
            if (not isinstance(world, str) or not world or not isinstance(target, str)
                    or not SHA.fullmatch(target) or not isinstance(r.get("target_text"), str)
                    or hashlib.sha256(r["target_text"].encode("utf-8")).hexdigest() != target
                    or not isinstance(r.get("messages"), list)
                    or not isinstance(r.get("input_messages_sha256"), str)
                    or hashlib.sha256(canonical(r["messages"])).hexdigest() != r["input_messages_sha256"]
                    or r.get("quality_v1_admitted") is not False
                    or r.get("training_authorized") is not False):
                raise ValueError("TASK_CONTENT_INVALID")
            matches = lookup.get((world, target), [])
            if len(matches) > 1 or (not matches and target in hashes):
                reason = "WORLD_OR_TARGET_IDENTITY_HOLD"
            elif not matches:
                reason = "NO_LEGACY_TARGET_MATCH"
            else:
                counts["target_identity_matched"] += 1
                old = matches[0]
                bound = bool(old[2] == 108 and reviews is not None and reviews.get(old[3]) and old[4])
                if bound:
                    counts["gold108_evidence_basic_bound"] += 1
                    reason = "CONTEXT_EQUIVALENCE_UNVERIFIED"
                else:
                    reason = "HISTORICAL_EVIDENCE_NOT_FULLY_BOUND"
            counts[reason] += 1
            counts["current_tasks_checked"] += 1
            queue.append({"case_id": ident, "reason_code": reason})
            if counts["current_tasks_checked"] > 100000:
                raise ValueError("TASK_COUNT_INVALID")
    if counts["current_tasks_checked"] == 0:
        raise ValueError("TASK_COUNT_INVALID")
    return {
        "schema": "r58_legacy_gold_target_reuse_safe_v1",
        "status": "TARGET_IDENTITY_TRIAGE_ONLY__SEMANTIC_HOLD",
        "counts": dict(sorted(counts.items())),
        "context_changes_verified": False,
        "historical_full_context_equivalence_proven": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "private_values_emitted": False,
    }, queue

def main():
    p = argparse.ArgumentParser()
    for name in ("repo_root", "gold87_index", "gold108_index", "private_tasks"):
        p.add_argument("--" + name.replace("_", "-"), required=True)
    p.add_argument("--gold108-evidence")
    p.add_argument("--private-queue-output")
    a = p.parse_args()
    try:
        repo = Path(a.repo_root).resolve()
        tasks = private_file(a.private_tasks, repo)
        result, queue = inspect(a.gold87_index, a.gold108_index, tasks, a.gold108_evidence)
        if a.private_queue_output:
            output = Path(a.private_queue_output)
            if (not output.is_absolute() or output.exists() or output.is_symlink()
                    or not output.parent.is_dir() or output.parent.is_symlink()
                    or stat.S_IMODE(output.parent.stat().st_mode) & 0o077
                    or repo == output.parent.resolve() or repo in output.parent.resolve().parents):
                raise ValueError("PRIVATE_OUTPUT_INVALID")
            fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for row in queue:
                    f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            result["private_queue_written"] = True
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, csv.Error) as error:
        print(json.dumps({"reason_code": safe_reason(error), "schema": "r58_legacy_gold_target_reuse_safe_v1",
                          "status": "INPUT_OR_BINDING_INVALID__HOLD",
                          "quality_v1_admitted": 0, "training_authorized": False,
                          "private_values_emitted": False}))
        return 42

if __name__ == "__main__":
    raise SystemExit(main())
