#!/usr/bin/env python3
"""R58 G1: owner-local, frozen v0.1 Test / legacy DEV20 exact UUID check.

No training, no network, no data export. Test JSONL is read ONLY on the
Owner's computer, strictly to select metadata.story_id; narratives are NEVER
printed, serialized, logged, or written to the private output.

IMPORTANT: The tool verifies two immutable Git blobs and an archived audit
receipt. It does not independently rerun old prompt/source text alignment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SCHEMA = "r58_round1_g1_legacy_dev20_uuid_safe_v1"
SOURCE_BLOB = "c17f225967b6b2f8cbaf3d82fadac1b4031d0654"
SOURCE_SHA256 = "d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d"
MANIFEST_BLOB = "f4e39196c6aa0a87b095d7de5cae4acd8b2fca63"
AUDIT_BLOB = "2e7041c9b2b417c16f926115212157648c8f8406"
BUDGET_BLOB = "8d4b35001a6533972e001736b769b630508941b6"
UUID_RE = re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$", re.I)
UUID_BYTES_RE = re.compile(rb'"story_id"\s*:\s*"([0-9a-fA-F-]{36})"')
SAMPLE_BYTES_RE = re.compile(rb'"id"\s*:\s*"(sample-[0-9]{6})"')
METADATA_BYTES_RE = re.compile(rb'"metadata"\s*:\s*\{')
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
OWNER_POLICY = "OWNER_ATTESTED_ROLEPLAY_UUID_ONE_UUID_ONE_WORLD_V1"

class Hold(ValueError):
    pass


def parse_blob_json(blob: bytes, max_bytes: int = 120_000) -> dict:
    if not 0 < len(blob) <= max_bytes:
        raise Hold("invalid metadata blob size")
    try:
        obj = json.loads(blob)
    except (ValueError, UnicodeDecodeError):
        raise Hold("bad metadata JSON")
    if not isinstance(obj, dict):
        raise Hold("metadata root must be object")
    return obj


def git_blob(repo: Path, sha: str, limit: int) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise Hold("untrusted Git object")
    try:
        r = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", sha],
                           capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Hold("Git blob unavailable")
    if r.returncode != 0 or not 0 < len(r.stdout) <= limit:
        raise Hold("Git source missing or oversized")
    return r.stdout


def source_world_ids(blob: bytes, sha256: str = SOURCE_SHA256) -> set[str]:
    # A full byte-level pin is checked BEFORE any parsing of old Test data.
    if hashlib.sha256(blob).hexdigest() != sha256:
        raise Hold("source SHA256 mismatch")
    if len(blob) > 1_500_000:
        raise Hold("unexpected source size")
    lines = blob.splitlines()
    if len(lines) != 20:
        raise Hold("old Test does not have 20 samples")
    ids, sample_ids = set(), set()
    for raw in lines:
        # Project only unescaped JSON structural tokens from the pinned byte
        # stream. DO NOT json.loads() the Test rows: that would materialize
        # all narrative content into memory. Raw bytes are never emitted.
        worlds = UUID_BYTES_RE.findall(raw)
        samples = SAMPLE_BYTES_RE.findall(raw)
        metas = METADATA_BYTES_RE.findall(raw)
        if len(worlds) != 1 or len(samples) != 1 or len(metas) != 1:
            raise Hold("pinned Test metadata projection ambiguous")
        uid = worlds[0].decode("ascii").lower()
        sample = samples[0].decode("ascii")
        if UUID_RE.fullmatch(uid) is None or sample in sample_ids:
            raise Hold("old Test source identities malformed")
        ids.add(uid)
        sample_ids.add(sample)
    if len(ids) != 2 or len(sample_ids) != 20:
        raise Hold("DEV20 must cover exactly two distinct worlds")
    return ids


def verify_source_receipts(manifest: dict, audit: dict, budget: dict, ids: set[str]):
    if (manifest.get("schema") != "storyforge-blind-v1" or
        manifest.get("count") != 20 or
        not isinstance(manifest.get("samples"), list) or
        len(manifest["samples"]) != 20):
        raise Hold("old Test manifest schema/count mismatch")
    seen = set()
    for index, item in enumerate(manifest["samples"], 1):
        if (not isinstance(item, dict) or item.get("source_line") != index or
            not isinstance(item.get("sample_id"), str) or
            not isinstance(item.get("prompt_sha256"), str) or
            SHA_RE.fullmatch(item["prompt_sha256"]) is None or
            item["sample_id"] in seen):
            raise Hold("Test manifest not a frozen 20-row mapping")
        seen.add(item["sample_id"])
    dataset = audit.get("reproducible_audit", {}).get("checks", {}).get("dataset", {})
    heldout = audit.get("reproducible_audit", {}).get("checks", {}).get("heldout", {})
    if (dataset.get("files_sha256", {}).get("test.jsonl") != SOURCE_SHA256 or
        dataset.get("split_counts", {}).get("test") != 20 or
        dataset.get("stories_by_split", {}).get("test") != 2 or
        heldout.get("test_alignment") != "20/20" or
        heldout.get("same_20_original_test_prompts_in_both_rounds") is not True):
        raise Hold("old frozen cross-artifact linkage receipt insufficient")
    if (budget.get("split_sample_counts", {}).get("test") != 20 or
        budget.get("sample_count") != 100 or
        not isinstance(budget.get("changed_samples"), list) or
        any(x.get("story_id", "").lower() not in ids for x in budget["changed_samples"]
            if isinstance(x, dict) and x.get("split") == "test")):
        raise Hold("budget metadata does not match old Test worlds")


def private_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise Hold("private input is missing or symlink")
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or not 0 < st.st_size <= 200_000:
        raise Hold("private input permissions/size invalid")
    return parse_blob_json(path.read_bytes(), max_bytes=200_000)


def checked_private_rows(sft: dict, r50: dict, r57: dict) -> list[dict]:
    if (sft.get("schema") != "r58_round1_g1_prior_sft_exact_id_holds_private_v2" or
        sft.get("owner_world_identity_policy") != OWNER_POLICY or
        sft.get("namespace_equivalence_owner_confirmed") is not True or
        sft.get("expansion_allowed") is not False or
        r50.get("schema") != "r58_round1_g1_r50_protection_private_v1" or
        r50.get("owner_world_identity_policy") != OWNER_POLICY or
        r50.get("status") != "NO_GLOBAL_G1_CLEARANCE" or
        r50.get("expansion_allowed") is not False or
        r57.get("schema") != "r58_round1_g1_r57_gold195_uuid_private_v1" or
        r57.get("owner_uuid_world_policy") != OWNER_POLICY or
        r57.get("status") != "PROTECTED_METADATA_ONLY__NOT_ADMITTED" or
        r57.get("expansion_allowed") is not False):
        raise Hold("private guard ledger schema/policy mismatch")
    def index(d):
        rows = d.get("entries")
        if not isinstance(rows, list) or len(rows) != 5:
            raise Hold("private five-story queue mismatch")
        out = {}
        for row in rows:
            if not isinstance(row, dict):
                raise Hold("invalid guard row")
            uid = row.get("story_id_PRIVATE")
            if not isinstance(uid, str) or UUID_RE.fullmatch(uid) is None or uid.lower() in out:
                raise Hold("private frozen UUID invalid/duplicate")
            out[uid.lower()] = row
        return out
    a, b, c = index(sft), index(r50), index(r57)
    if set(a) != set(b) or set(a) != set(c):
        raise Hold("private frozen queue drift")
    exposed = 0
    rows = []
    for uid, row in a.items():
        s = row.get("historical_sft_exact_uuid_overlap")
        b_row, c_row = b[uid], c[uid]
        if (type(s) is not bool or b_row.get("historically_sft_exposed") is not s or
            c_row.get("historical_sft_uuid_exposed") is not s or
            type(b_row.get("r50_exact_story_uuid_match")) is not bool or
            type(c_row.get("r50_protected_uuid_match")) is not bool or
            b_row["r50_exact_story_uuid_match"] is not c_row["r50_protected_uuid_match"] or
            type(c_row.get("r57_gold195_source_uuid_match")) is not bool):
            raise Hold("private guard flags inconsistent")
        exposed += int(s)
        if not s and (b_row["r50_exact_story_uuid_match"] or c_row["r57_gold195_source_uuid_match"]):
            raise Hold("unexpected prior R50/Gold collision: do not skip earlier gate")
        rows.append({"story_id_PRIVATE": uid, "historical_sft_uuid_exposed": s,
                     "r50_protected_uuid_match": b_row["r50_exact_story_uuid_match"],
                     "r57_gold195_source_uuid_match": c_row["r57_gold195_source_uuid_match"]})
    if exposed != 1 or len([r for r in rows if not r["historical_sft_uuid_exposed"]]) != 4:
        raise Hold("frozen 1+4 cohort mismatch")
    return rows


def evaluate(rows: list[dict], worlds: set[str]) -> tuple[dict, list[dict]]:
    if len(rows) != 5 or len(worlds) != 2:
        raise Hold("cohort/world count invalid")
    hits = 0
    private_rows = []
    for row in rows:
        uid = row["story_id_PRIVATE"].lower()
        exposed = row["historical_sft_uuid_exposed"]
        match = uid in worlds
        if not exposed:
            hits += int(match)
        status = ("EXCLUDED_PRIOR_SFT_EXACT_UUID_EXPOSURE" if exposed else
                  "HOLD_LEGACY_DEV20_EXACT_UUID_OVERLAP" if match else
                  "HOLD_OTHER_PROTECTED_AND_PRIOR_SFT_COVERAGE")
        private_rows.append({**row, "legacy_dev20_uuid_match": match,
                             "status": status, "train_admitted": False,
                             "expansion_allowed": False})
    safe = {
        "schema": SCHEMA,
        "status": "R58_G1_LEGACY_DEV20_EXACT_UUID_CHECK_DONE__OTHER_PROTECTED_HOLD",
        "fixed_stories": 5,
        "prior_sft_exposed_excluded": 1,
        "legacy_dev20_unique_cases": 20,
        "legacy_dev20_source_story_uuids": 2,
        "legacy_r47_r48_r55_r57_dev20_uuid_index_covered": True,
        "legacy_dev20_exact_uuid_matches_among_remaining_four": hits,
        "remaining_without_sft_r50_r57_gold_or_dev20_uuid_match": 4-hits,
        "old_test_source_sha256_pin_verified": True,
        "old_test_manifest_git_blob_pin_verified": True,
        "old_test_archived_alignment_receipt_verified": True,
        "old_test_content_exported": False,
        "r50_protected_test_content_accessed": False,
        "other_protected_uuids_covered": False,
        "prior_sft_source_registry_complete": False,
        "source_registry_complete": False,
        "g1_clearance": "HOLD",
        "train_admitted": 0, "validation_admitted": 0, "teacher_admitted": 0,
        "expansion_allowed": False,
    }
    return safe, private_rows


def write_private(path: Path, rows: list[dict]):
    if path.exists() or path.is_symlink():
        raise Hold("private output exists")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir() or parent.stat().st_mode & 0o077:
        raise Hold("private destination unsafe")
    # Prevent redirect via symlinked ancestors (Home is expected to be real).
    for p in list(parent.parents)[:-1] + [parent]:
        if p.is_symlink():
            raise Hold("symlinked private ancestor")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"schema": "r58_round1_g1_legacy_dev20_uuid_private_v1",
                       "owner_uuid_world_policy": OWNER_POLICY,
                       "status": "PROTECTED_METADATA_ONLY__NOT_ADMITTED",
                       "entries": rows,
                       "other_protected_and_sft_completeness_pending": True,
                       "expansion_allowed": False}, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(repo: Path, sft_path: Path, r50_path: Path, r57_path: Path, output: Path | None):
    source = git_blob(repo, SOURCE_BLOB, 1_500_000)
    worlds = source_world_ids(source)
    verify_source_receipts(parse_blob_json(git_blob(repo, MANIFEST_BLOB, 20_000)),
                           parse_blob_json(git_blob(repo, AUDIT_BLOB, 40_000)),
                           parse_blob_json(git_blob(repo, BUDGET_BLOB, 20_000)), worlds)
    rows = checked_private_rows(private_json(sft_path), private_json(r50_path),
                                private_json(r57_path))
    safe, private_rows = evaluate(rows, worlds)
    if output is not None:
        write_private(output, private_rows)
        safe["private_case_hold_ledger_written"] = True
    return safe


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--private-sft-holds", type=Path, required=True)
    ap.add_argument("--private-r50-holds", type=Path, required=True)
    ap.add_argument("--private-r57-gold-holds", type=Path, required=True)
    ap.add_argument("--private-output", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = run(args.repo_root, args.private_sft_holds, args.private_r50_holds,
                     args.private_r57_gold_holds, args.private_output)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, Hold, ValueError, TypeError, KeyError):
        print("R58_G1_LEGACY_DEV20: HOLD (source, coverage, or private evidence invalid)",
              file=sys.stderr)
        return 42

if __name__ == "__main__":
    raise SystemExit(main())
