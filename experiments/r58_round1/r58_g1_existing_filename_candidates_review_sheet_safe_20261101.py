#!/usr/bin/env python3
"""R58 G1: reuse the EXISTING 2026-10-30 private filename candidate manifest.

Do not rerun autodiscovery, open referenced source files or access R50/DEV
contents. Validate frozen filename-only candidate counts and create ONE NEW
PRIVATE owner-review sheet (0600, exclusive). Filename hints are NOT proof that
a source is metadata-only or complete. Do not update the existing inventory.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

from r58_g1_other_three_jobs_private_ledger_crosscheck_safe import (
    DEFAULT_ROOT, read_private,
)
from triage_hf_job_exposure import write_private

SCHEMA = "r58_g1_existing_filename_candidates_review_sheet_safe_v1"
PRIVATE_SCHEMA = "r58_g1_filename_candidates_owner_review_private_v1"
BRANCH = "r58/roleplay-sft-skill-v01"
SOURCE_BASE = Path.home() / ".local" / "share" / "storyforge"
SOURCE_ROOTS = (
    "r52/world_isolation", "r52/world_review",
    "r52/history_exposure_with_r45", "r57/private",
)
SCOPES = (
    "semantic_world_graph", "r50_protected_worlds", "prior_sft_exposure",
    "r55_r57_dev_worlds", "other_protected_or_holdout",
)
# Owner's already-reported 2026-10-30 filename-only discovery, NOT source files.
EXPECTED_COUNTS = {
    "semantic_world_graph": 8,
    "r50_protected_worlds": 0,
    "prior_sft_exposure": 2,
    "r55_r57_dev_worlds": 19,
    "other_protected_or_holdout": 0,
}
EXPECTED_UNIQUE_PATHS = 22
INDEX_HINT = re.compile(
    r"index|roster|manifest|registry|metadata|world|identity|graph|exposure|lineage",
    re.IGNORECASE,
)
REPORT_HINT = re.compile(
    r"report|receipt|safe|summary|result|audit|decision",
    re.IGNORECASE,
)


class Hold(Exception):
    pass


def validate_source_path(value: str) -> str:
    if not isinstance(value, str) or len(value) > 1024 or "\x00" in value:
        raise Hold("invalid private filename candidate")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path.suffix.lower() not in {
        ".json", ".csv", ".md", ".txt",
    }:
        raise Hold("unsafe filename candidate")
    if not any(path.is_relative_to(SOURCE_BASE / r) for r in SOURCE_ROOTS):
        raise Hold("candidate outside previously approved metadata discovery roots")
    # Do not stat or open the discovered candidate: only its path spelling.
    return str(path)


def make_review(manifest: dict) -> tuple[dict, dict]:
    if (manifest.get("schema") != "r58_g1_filename_candidates_private_v1"
            or manifest.get("protected_set_contents_accessed") is not False):
        raise Hold("not the frozen PRIVATE filename-only candidate manifest")
    groups = manifest.get("candidate_paths_by_scope")
    if not isinstance(groups, dict) or set(groups) != set(SCOPES):
        raise Hold("candidate scope set mismatch")
    counts = {}
    all_paths = set()
    entries = []
    for scope in SCOPES:
        filenames = groups[scope]
        if not isinstance(filenames, list):
            raise Hold("candidate list unavailable")
        cleaned = [validate_source_path(v) for v in filenames]
        if len(cleaned) != len(set(cleaned)):
            raise Hold("duplicate candidate inside scope")
        counts[scope] = len(cleaned)
        for path in sorted(cleaned):
            all_paths.add(path)
            name = Path(path).name
            entries.append({
                "scope": scope,
                "source_reference_PRIVATE": path,
                "index_like_filename_hint": bool(INDEX_HINT.search(name)),
                "report_like_filename_hint": bool(REPORT_HINT.search(name)),
                "owner_approved_metadata_only_source": False,
                "source_revision": "",
                "complete_scope_coverage_owner_attested": False,
                "independent_scope_coverage_verified": False,
                "review_status": "UNREVIEWED_FILENAME_ONLY",
            })
    if counts != EXPECTED_COUNTS or len(all_paths) != EXPECTED_UNIQUE_PATHS:
        raise Hold("prior Owner filename discovery cohort has drifted")
    if len(entries) != 29:
        raise Hold("incorrect candidate reference total")
    hints = Counter(
        "INDEX_AND_REPORT" if e["index_like_filename_hint"] and e["report_like_filename_hint"]
        else "INDEX_HINT_ONLY" if e["index_like_filename_hint"]
        else "REPORT_HINT_ONLY" if e["report_like_filename_hint"]
        else "OTHER_NAME_HINT"
        for e in entries
    )
    private = {
        "schema": PRIVATE_SCHEMA,
        "status": "EXISTING_22_PATH_FILENAME_CANDIDATES_OWNER_REVIEW_PENDING",
        "source_origin": "EXISTING_AUTODISCOVERY_PRIVATE_FILENAME_LIST__NOT_SOURCE_BYTES",
        "entries_PRIVATE": entries,
        "coverage_independently_verified": False,
        "no_source_files_opened": True,
        "g1_clearance": "HOLD",
        "expansion_allowed": False,
    }
    safe = {
        "schema": SCHEMA,
        "status": "PRIOR_22_FILENAME_CANDIDATES_REUSED__OWNER_METADATA_SOURCE_SELECTION_PENDING",
        "candidate_counts_by_scope": counts,
        "unique_private_candidate_path_count": len(all_paths),
        "scope_candidate_rows": len(entries),
        "filename_hint_classes": dict(sorted(hints.items())),
        "private_review_rows_owner_approved": 0,
        "actual_source_index_contents_read": False,
        "protected_r50_directories_scanned": False,
        "raw_paths_uuids_or_candidate_source_names_exported": False,
        "existing_private_inventory_modified": False,
        "prior_autodiscovery_rerun": False,
        "source_registry_complete": False,
        "g1_clearance": "HOLD", "g2_clearance": "HOLD",
        "train_admitted": 0, "validation_admitted": 0,
        "teacher_admitted": 0, "expansion_allowed": False,
    }
    return safe, private


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    p.add_argument("--private-candidates", type=Path,
                   default=DEFAULT_ROOT / "g1_index_candidates_autodiscovered_private.json")
    p.add_argument("--private-output", type=Path,
                   default=DEFAULT_ROOT / "g1_existing_candidates_owner_review_PRIVATE_20261101.json")
    args = p.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        branch = subprocess.run(
            ["git", "-C", str(repo), "branch", "--show-current"],
            check=True, timeout=8, capture_output=True, text=True,
        )
        if branch.stdout.strip() != BRANCH:
            raise Hold("wrong repo branch")
        if args.private_output == args.private_candidates:
            raise Hold("cannot overwrite source")
        if args.private_output.exists() or args.private_output.is_symlink():
            raise Hold("review sheet already exists")
        manifest = read_private(args.private_candidates)
        safe, private = make_review(manifest)
        write_private(args.private_output, private)
        safe["new_private_review_sheet_written_exclusive_0600"] = True
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "PRIOR_FILENAME_MANIFEST_OR_PRIVATE_REVIEW_OUTPUT_UNAVAILABLE__G1_HOLD",
            "prior_autodiscovery_rerun": False,
            "raw_paths_uuids_or_candidate_source_names_exported": False,
            "protected_r50_directories_scanned": False,
            "existing_private_inventory_modified": False,
            "hf_job_started": False,
            "g1_clearance": "HOLD", "g2_clearance": "HOLD",
            "train_admitted": 0, "validation_admitted": 0,
            "teacher_admitted": 0, "expansion_allowed": False,
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
