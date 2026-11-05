#!/usr/bin/env python3
"""Verify R50's private HF tokenizer report; optionally commit ONLY safe aggregates.

Downloads the report to a private ephemeral directory via authenticated HF CLI.
Never emits/stages original prompts, per-case IDs, per-case token counts or mappings.
No HF Job / GPU / inference. Requires explicit --push for Git mutation.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile

REPO_BRANCH = "audit/r49-r50-source-intake-20261015"
REPO_BUCKET = "hf://buckets/adradar/storyforge-training"
EXPECTED_MODEL = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
EXPECTED_CANDIDATE = "109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2"
EXPECTED_SYSTEM = "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"
EXPECTED_PREFLIGHT_BLOB = "c546194bd02608e921d9c673fa3e549c022468ae"
EXPECTED_WORLDS = {"16": 9, "17": 10, "18": 9, "19": 8, "20": 10}
EXCLUDE = {
    "SFH50-W16-005", "SFH50-W18-003", "SFH50-W19-003", "SFH50-W19-010",
}
RESULT_PATH = "docs/evidence/V03_R50_46_CPU_TOKENIZER_VERIFIED_20261016.json"


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hex_digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def checked_integer(value: object, label: str, *, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum, f"INVALID_{label}")
    return value


def verify_report(data: bytes, job_id: str) -> dict:
    """Return aggregate-only evidence; fail closed on incomplete/incorrect reports."""
    r = json.loads(data.decode("utf-8"))
    require(isinstance(r, dict), "REPORT_NOT_OBJECT")
    expected = {
        "schema": "storyforge-r50-cpu-real-tokenizer-preflight-v1",
        "status": "PREFLIGHT_ONLY_NO_FINAL_SEAL",
        "pinned_model_revision": EXPECTED_MODEL,
        "candidate_original_sha256": EXPECTED_CANDIDATE,
        "system_sha256": EXPECTED_SYSTEM,
        "thinking_mode": "disabled",
        "max_context": 16384,
        "reserved_output_tokens": 1536,
        "case_count": 46,
        "overflow_count": 0,
        "actual_four_model_inference_input_equality": "NOT_VERIFIED_NO_MODEL_EXECUTED",
        "no_model_generation": True,
        "no_gpu": True,
        "no_final_heldout_seal": True,
        "strategy": "PRESERVE_CONSECUTIVE_USER_AND_INJECT_WORLD_RULES_TO_SHARED_SYSTEM__DRAFT_ONLY",
    }
    for key, value in expected.items():
        require(type(r.get(key)) is type(value) and r[key] == value,
                f"EXPECTED_FIELD_MISMATCH_{key}")
    require(hex_digest(r.get("chat_template_sha256")), "MISSING_CHAT_TEMPLATE_SHA")
    file_hashes = r.get("tokenizer_file_sha256")
    require(isinstance(file_hashes, dict), "MISSING_TOKENIZER_FILE_SHA")
    require({"tokenizer.json", "tokenizer_config.json"} <= set(file_hashes),
            "MISSING_REQUIRED_TOKENIZER_FILES")
    require(all(hex_digest(v) for v in file_hashes.values()), "INVALID_TOKENIZER_FILE_SHA")
    require(isinstance(r.get("tokenizer_snapshot"), str) and
            EXPECTED_MODEL in Path(r["tokenizer_snapshot"]).parts,
            "UNPINNED_TOKENIZER_SNAPSHOT_PATH")

    cases = r.get("cases")
    require(isinstance(cases, list) and len(cases) == 46, "CASE_COUNT_MISMATCH")
    seen = set()
    worlds: collections.Counter[str] = collections.Counter()
    history_total = 0
    consecutive = 0
    sizes: list[int] = []
    for row in cases:
        require(isinstance(row, dict), "INVALID_CASE_RECORD")
        ident = row.get("case_id")
        require(isinstance(ident, str), "MISSING_CASE_ID")
        match = re.fullmatch(r"SFH50-W(16|17|18|19|20)-[0-9]{3}", ident)
        require(match is not None and ident not in seen and ident not in EXCLUDE,
                "DUPLICATE_EXCLUDED_OR_INVALID_CASE")
        seen.add(ident)
        worlds[match.group(1)] += 1
        history_total += checked_integer(row.get("history_count"), "HISTORY_COUNT")
        require(type(row.get("consecutive_user")) is bool, "INVALID_CONSECUTIVE_USER")
        consecutive += int(row["consecutive_user"])
        n = checked_integer(row.get("input_tokens"), "INPUT_TOKENS", minimum=1)
        total = checked_integer(row.get("input_plus_output_budget"), "INPUT_BUDGET")
        require(total == n + 1536 and total <= 16384 and
                row.get("within_budget") is True, "TOKEN_BUDGET_HOLD")
        require(hex_digest(row.get("input_id_sha256")), "MISSING_INPUT_ID_SHA")
        sizes.append(n)
    require(dict(worlds) == EXPECTED_WORLDS, "WORLD_COUNTS_MISMATCH")
    require(history_total == 364, "HISTORY_TOTAL_MISMATCH")
    require(consecutive == 12, "CONSECUTIVE_USER_COUNT_MISMATCH")
    require(checked_integer(r.get("overflow_count"), "OVERFLOW_COUNT") == 0,
            "OVERFLOW_HOLD")
    sorted_sizes = sorted(sizes)
    return {
        "schema": "storyforge-r50-cpu-tokenizer-verified-aggregate-v1",
        "source": "OWNER_AUTHENTICATED_HF_PRIVATE_BUCKET_REPORT",
        "validation": "FULL_PRIVATE_REPORT_FIELDS_AND_46_RECORDS_VALIDATED",
        "report_file_sha256": digest(data),
        "hf_job_id": job_id,
        "model_revision": EXPECTED_MODEL,
        "candidate_sha256": EXPECTED_CANDIDATE,
        "system_sha256": EXPECTED_SYSTEM,
        "chat_template_sha256": r["chat_template_sha256"],
        "tokenizer_file_sha256": dict(sorted(file_hashes.items())),
        "thinking_mode": "disabled",
        "context_tokens": 16384,
        "reserved_output_tokens": 1536,
        "case_count": 46,
        "history_message_count": 364,
        "consecutive_user_case_count": 12,
        "world_case_counts": EXPECTED_WORLDS,
        "overflow_count": 0,
        "input_token_distribution": {
            "min": sorted_sizes[0],
            "median": statistics.median(sorted_sizes),
            "p95_nearest_rank": sorted_sizes[math.ceil(0.95 * len(sorted_sizes)) - 1],
            "max": sorted_sizes[-1],
        },
        "result": "R50_46_ACTUAL_QWEN_TOKENIZER_BUDGET_PASS_ONLY",
        "input_strategy": "DRAFT_NOT_PREREGISTERED",
        "semantic_world_alias": "HOLD",
        "four_arm_runtime_input_equality": "NOT_VERIFIED",
        "heldout_final_seal": "NOT_PERFORMED",
        "model_generation": False,
        "gpu_executed": False,
        "model_promotion": False,
        "privacy": "Aggregate only; no prompts, per-case IDs, mappings, token counts or answers.",
    }


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def check_git(repo: Path) -> None:
    require(git(repo, "branch", "--show-current") == REPO_BRANCH,
            "WRONG_GIT_BRANCH")
    require(not git(repo, "status", "--porcelain"),
            "GIT_WORKTREE_NOT_CLEAN")
    require(git(repo, "rev-parse", "HEAD:scripts/v03_r50_cpu_tokenizer_preflight_46.py")
            == EXPECTED_PREFLIGHT_BLOB, "WRONG_PINNED_PREFLIGHT_GIT_BLOB")
    require(not (repo / RESULT_PATH).exists(), "EVIDENCE_PATH_EXISTS")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--stage-key", required=True)
    ap.add_argument("--job-id", required=True)
    ap.add_argument("--push", action="store_true",
                    help="Explicitly commit and push ONLY the sanitized aggregate evidence.")
    args = ap.parse_args()
    require(re.fullmatch(r"r50-token-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}",
                         args.stage_key) is not None, "INVALID_STAGE_KEY")
    require(re.fullmatch(r"[0-9a-f]{24}", args.job_id) is not None,
            "INVALID_HF_JOB_ID")
    repo = args.repo.resolve()
    check_git(repo)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="storyforge-r50-token-") as td:
        private_report = Path(td) / "R50_46_TOKENIZER.json"
        remote = (f"{REPO_BUCKET}/preflight/v03-r50/cpu-tokenizer/"
                  f"{args.stage_key}/reports/R50_46_TOKENIZER.json")
        subprocess.run(["hf", "buckets", "cp", remote, str(private_report)],
                       check=True, stdout=subprocess.DEVNULL)
        private_report.chmod(0o600)
        summary = verify_report(private_report.read_bytes(), args.job_id)
        # Never retain or echo the per-case report beyond this temp directory.
    print("R50_46_PRIVATE_TOKENIZER_REPORT_VERIFIED")
    print(json.dumps({"result": summary["result"],
                      "case_count": summary["case_count"],
                      "overflow_count": summary["overflow_count"],
                      "input_token_distribution": summary["input_token_distribution"]},
                     ensure_ascii=False))
    if args.push:
        check_git(repo)
        out = repo / RESULT_PATH
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2)
                       + "\n", encoding="utf-8")
        try:
            git(repo, "add", "--", RESULT_PATH)
            git(repo, "commit", "-m",
                "docs(r50): validate 46-case pinned Qwen tokenizer budget",
                "--", RESULT_PATH)
            git(repo, "push", "origin", f"HEAD:refs/heads/{REPO_BRANCH}")
        except Exception:
            # Preserve any unpushed audited commit for human conflict recovery.
            raise
        print("R50_AGGREGATE_ONLY_EVIDENCE_PUSHED_TO_GITHUB")
    else:
        print("DRY_RUN_ONLY__NO_GIT_WRITE__USE_PUSH_AFTER_REVIEW")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError,
            UnicodeError, json.JSONDecodeError) as exc:
        print("R50_PRIVATE_TOKENIZER_EVIDENCE_HOLD:", type(exc).__name__,
              str(exc)[:240], file=sys.stderr)
        sys.exit(2)
