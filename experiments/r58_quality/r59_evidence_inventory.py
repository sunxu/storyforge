#!/usr/bin/env python3
"""R59 private evidence inventory and exact-association audit.

Inventories Owner-local exports only. It does not create attestations, infer
world identity, prove reviewer independence, or infer non-exposure.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "storyforge-r59-evidence-inventory-safe-v1"
STAGED_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGED_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"
MAX_FILE_BYTES = 40 * 1024 * 1024
WORLD_FIELDS = ("world", "components", "character", "characters",
                "director", "opening", "visual")


class InventoryHold(ValueError):
    pass


def _read_private(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise InventoryHold("INPUT_NOT_REGULAR_FILE")
    info = path.stat()
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise InventoryHold("INPUT_PERMISSION_INVALID")
    if info.st_size > MAX_FILE_BYTES:
        raise InventoryHold("INPUT_TOO_LARGE")
    return path.read_bytes()


def _jsonl(raw: bytes) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise InventoryHold("JSONL_INVALID") from None
    if any(not isinstance(row, dict) for row in rows):
        raise InventoryHold("JSONL_ROW_INVALID")
    return rows


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _exact_pair_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    index = {}
    for row in rows:
        case_id, target = row.get("case_id"), row.get("target_sha256")
        if not isinstance(case_id, str) or not case_id:
            continue
        if not isinstance(target, str) or len(target) != 64:
            continue
        key = (case_id, target)
        if key in index:
            raise InventoryHold("DUPLICATE_CASE_TARGET_PAIR")
        index[key] = row
    return index


def build_report(staged, locator_rows, draft_rows, exposure_rows):
    candidates = [
        row for row in staged
        if row.get("schema") == STAGED_SCHEMA and row.get("status") == STAGED_STATUS
    ]
    if not candidates:
        raise InventoryHold("NO_STAGED_CANDIDATES")
    if len(candidates) > 192:
        raise InventoryHold("CANDIDATE_LIMIT_EXCEEDED")

    candidate_ids = [row.get("case_id") for row in candidates]
    candidate_targets = [row.get("target_sha256") for row in candidates]
    if (any(not isinstance(x, str) or not x for x in candidate_ids)
            or len(set(candidate_ids)) != len(candidate_ids)
            or any(not isinstance(x, str) or len(x) != 64 for x in candidate_targets)
            or len(set(candidate_targets)) != len(candidate_targets)):
        raise InventoryHold("STAGED_IDENTITY_INVALID_OR_DUPLICATE")

    locator_index = _exact_pair_index(
        [node for row in locator_rows for node in _walk_dicts(row)]
    )
    exposure_index = _exact_pair_index(
        [node for row in exposure_rows for node in _walk_dicts(row)]
    )
    if any(not isinstance(row.get("story_id"), str) or not row["story_id"]
           for row in draft_rows):
        raise InventoryHold("DRAFT_STORY_ID_INVALID")

    locator_matched = 0
    exposure_matched = 0
    exposure_statuses = Counter()
    exposure_flags = Counter()
    matched_story_ids = {
        row["story_id"] for row in candidates
        if isinstance(row.get("story_id"), str) and row["story_id"]
    }
    draft_matches = [
        row for row in draft_rows if row.get("story_id") in matched_story_ids
    ]
    drafts_by_story = defaultdict(list)
    for row in draft_matches:
        drafts_by_story[row["story_id"]].append(row)

    for candidate in candidates:
        pair = (candidate["case_id"], candidate["target_sha256"])
        locator = locator_index.get(pair)
        exposure = exposure_index.get(pair)
        if locator is not None:
            locator_matched += 1
        if exposure is not None:
            exposure_matched += 1
            status = exposure.get("status")
            if isinstance(status, str):
                exposure_statuses[status] += 1
            for flag in ("train_exposed", "validation_exposed", "test_exposed"):
                value = exposure.get(flag)
                if type(value) is bool:
                    exposure_flags[f"{flag}_{str(value).lower()}"] += 1

    distinct_drafts = [
        draft for story_id in matched_story_ids
        for draft in drafts_by_story.get(story_id, [])
    ]
    world_presence = Counter()
    world_types = Counter()
    for draft in distinct_drafts:
        data = draft.get("v2_data")
        for field in WORLD_FIELDS:
            if isinstance(data, dict) and field in data:
                world_presence[field] += 1
                world_types[f"{field}_{type(data[field]).__name__}"] += 1

    stories_with_draft = sum(bool(drafts_by_story.get(s)) for s in matched_story_ids)
    multi_draft_stories = sum(len(drafts_by_story.get(s, [])) > 1 for s in matched_story_ids)
    updated_at_count = sum(bool(row.get("updated_at")) for row in distinct_drafts)

    return {
        "schema": SCHEMA,
        "status": "EVIDENCE_INVENTORY_COMPLETE__NO_OWNER_ATTESTATION_OR_ADMISSION",
        "staged_rows_read": len(staged),
        "staged_candidates": len(candidates),
        "distinct_candidate_stories": len(matched_story_ids),
        "source_locator_exact_matches": locator_matched,
        "source_locator_missing": len(candidates) - locator_matched,
        "story_draft_records_for_candidate_stories": len(draft_matches),
        "candidate_stories_with_draft": stories_with_draft,
        "candidate_stories_without_draft": len(matched_story_ids) - stories_with_draft,
        "candidate_stories_with_multiple_drafts": multi_draft_stories,
        "matched_draft_updated_at_present": updated_at_count,
        "world_field_presence": {k: world_presence[k] for k in WORLD_FIELDS},
        "world_field_types": dict(sorted(world_types.items())),
        "historical_exposure_exact_matches": exposure_matched,
        "historical_exposure_missing": len(candidates) - exposure_matched,
        "historical_exposure_status_counts": dict(sorted(exposure_statuses.items())),
        "historical_exposure_flag_counts": dict(sorted(exposure_flags.items())),
        "exposure_not_found_is_proof_of_non_exposure": False,
        "reviewer_independence_proven": False,
        "world_component_isolation_proven": False,
        "protected_set_completeness_proven": False,
        "owner_evidence_populated": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
        "private_values_emitted": False,
        "source_modified": False,
    }


def run(args):
    raw = [
        _read_private(args.staged_jsonl),
        _read_private(args.source_locators_jsonl),
        _read_private(args.story_drafts_jsonl),
        _read_private(args.historical_exposure_jsonl),
    ]
    report = build_report(*[_jsonl(item) for item in raw])
    output = args.output_safe
    if output.exists() or output.is_symlink():
        raise InventoryHold("OUTPUT_EXISTS")
    if (not output.parent.is_dir() or output.parent.is_symlink()
            or stat.S_IMODE(output.parent.stat().st_mode) != 0o700):
        raise InventoryHold("OUTPUT_PARENT_INVALID")
    if output.resolve().is_relative_to(Path.cwd().resolve()):
        raise InventoryHold("OUTPUT_INSIDE_REPOSITORY")
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True,
                         indent=2).encode("utf-8") + b"\n"
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-jsonl", required=True, type=Path)
    parser.add_argument("--source-locators-jsonl", required=True, type=Path)
    parser.add_argument("--story-drafts-jsonl", required=True, type=Path)
    parser.add_argument("--historical-exposure-jsonl", required=True, type=Path)
    parser.add_argument("--output-safe", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = run(args)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({
            "schema": SCHEMA, "status": "EVIDENCE_INVENTORY_HOLD",
            "reason_code": "INPUT_OUTPUT_OR_IDENTITY_CHECK_FAILED",
            "quality_v1_admitted": 0, "training_authorized": False,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
