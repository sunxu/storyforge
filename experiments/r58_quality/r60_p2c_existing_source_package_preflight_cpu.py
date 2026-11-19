"""Check existing P2 × full Base336 captured source package; never access DB.

This tool checks identity/coverage/manifest byte binding, not semantic identity,
actual-sent historical versions, or any protected-set exclusion outside Base336.
All identifiers and fields remain Owner-private; stdout is SAFE aggregates only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
from collections import Counter
from pathlib import Path

PACKAGE_SCHEMA = "storyforge_r60_base336_p2_source_evidence_private_v1"
MANIFEST_SCHEMA = "storyforge_r60_base336_p2_public_source_inventory_private_v1"
SAFE_SCHEMA = "storyforge_r60_base336_p2_full_source_package_preflight_safe_v1"
FIELDS = frozenset(("world", "character", "characters", "opening"))
MAX_PACKAGE_BYTES = 100_000_000


class Hold(ValueError):
    """Fixed non-sensitive failure reason."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Hold(reason)


def read_private(path: Path, max_bytes: int) -> bytes:
    require(path.is_file() and not path.is_symlink(), "INPUT_MISSING_OR_TYPE_HOLD")
    require(stat.S_IMODE(path.stat().st_mode) == 0o600, "INPUT_MODE_HOLD")
    size = path.stat().st_size
    require(0 < size <= max_bytes, "INPUT_SIZE_HOLD")
    raw = path.read_bytes()
    require(len(raw) == size, "INPUT_SIZE_DRIFT_HOLD")
    return raw


def parse(raw: bytes) -> dict:
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise Hold("INPUT_JSON_HOLD") from None
    require(type(value) is dict, "INPUT_ROOT_HOLD")
    return value


def evaluate(package: dict, manifest: dict, manifest_sha: str) -> dict:
    require(package.get("schema") == PACKAGE_SCHEMA, "PACKAGE_SCHEMA_HOLD")
    require(manifest.get("schema") == MANIFEST_SCHEMA, "MANIFEST_SCHEMA_HOLD")
    require(package.get("p2_scope", {}).get("manifest_sha256_PRIVATE") == manifest_sha,
            "P2_MANIFEST_BINDING_HOLD")
    selected = manifest.get("sources")
    require(type(selected) is list and len(selected) == 8, "P2_SOURCE_MANIFEST_HOLD")
    p2_by_id = {}
    for row in selected:
        require(type(row) is dict, "P2_MANIFEST_ROW_HOLD")
        sid, key = row.get("story_id"), row.get("source_key")
        require(type(sid) is str and bool(sid) and type(key) is str and bool(key),
                "P2_MANIFEST_ID_HOLD")
        require(sid not in p2_by_id, "P2_MANIFEST_DUPLICATE_HOLD")
        p2_by_id[sid] = row
    base = package.get("base336_scope")
    p2 = package.get("p2_scope")
    require(type(base) is dict and type(p2) is dict, "PACKAGE_SCOPE_HOLD")
    require(base.get("cases") == 336, "BASE_CASES_HOLD")
    ids = base.get("story_ids_PRIVATE")
    require(type(ids) is list and len(ids) == 172
            and all(type(x) is str and bool(x) for x in ids)
            and len(set(ids)) == 172, "BASE_STORY_ROSTER_HOLD")
    base_ids = set(ids)
    cases = base.get("candidate_source_bindings_PRIVATE")
    require(type(cases) is list and len(cases) == 336, "BASE_CASE_COVERAGE_HOLD")
    seen_positions = set()
    for item in cases:
        require(type(item) is dict, "BASE_CASE_ROW_HOLD")
        pos, sid = item.get("candidate_position_1based_PRIVATE"), item.get("story_id_PRIVATE")
        require(type(pos) is int and 1 <= pos <= 336 and pos not in seen_positions
                and sid in base_ids, "BASE_CASE_SOURCE_BINDING_HOLD")
        seen_positions.add(pos)
    require(len(seen_positions) == 336, "BASE_CASE_COVERAGE_HOLD")
    source_rows = base.get("source_records_PRIVATE")
    require(type(source_rows) is list and len(source_rows) >= 172, "BASE_SOURCE_ROWS_HOLD")
    current, archived = Counter(), set()
    for item in source_rows:
        require(type(item) is dict and item.get("story_id_PRIVATE") in base_ids,
                "BASE_SOURCE_ID_HOLD")
        require(type(item.get("source_fields_PRIVATE")) is dict
                and set(item["source_fields_PRIVATE"]) == FIELDS,
                "BASE_FIELDS_HOLD")
        sid, kind, rev = (item["story_id_PRIVATE"], item.get("source_kind"),
                          item.get("revision_id_PRIVATE"))
        if kind == "current":
            require(rev is None, "BASE_CURRENT_REVISION_HOLD")
            current[sid] += 1
        elif kind == "archived":
            require(type(rev) is int and rev > 0 and (sid, rev) not in archived,
                    "BASE_ARCHIVED_REVISION_HOLD")
            archived.add((sid, rev))
        else:
            raise Hold("BASE_SOURCE_KIND_HOLD")
    require(set(current) == base_ids and all(v == 1 for v in current.values()),
            "BASE_CURRENT_COVERAGE_HOLD")
    p2_rows = p2.get("source_records_PRIVATE")
    require(type(p2_rows) is list and len(p2_rows) == 8,
            "P2_SOURCE_ROWS_HOLD")
    seen = set()
    for item in p2_rows:
        require(type(item) is dict, "P2_SOURCE_ROW_HOLD")
        sid = item.get("story_id_PRIVATE")
        manifest_row = p2_by_id.get(sid)
        require(manifest_row is not None and sid not in seen, "P2_SOURCE_BINDING_HOLD")
        seen.add(sid)
        require(item.get("source_key_PRIVATE") == manifest_row.get("source_key")
                and item.get("public_content_revision_PRIVATE") == manifest_row.get("public_content_revision")
                and item.get("submission_id_PRIVATE") == manifest_row.get("moderation_submission_id")
                and item.get("permission_event_id_PRIVATE") == manifest_row.get("permission_event_id")
                and item.get("submission_snapshot_sha256_PRIVATE") == manifest_row.get("submission_snapshot_sha256")
                and item.get("world_json_md5_PRIVATE") == manifest_row.get("world_json_md5"),
                "P2_SOURCE_VERSION_BINDING_HOLD")
        require(type(item.get("source_fields_PRIVATE")) is dict
                and set(item["source_fields_PRIVATE"]) == FIELDS,
                "P2_FIELDS_HOLD")
    overlap = len(base_ids & set(p2_by_id))
    require(overlap == 0, "BASE_P2_EXACT_STORY_OVERLAP_HOLD")
    matches = package.get("exact_field_match_pairs_PRIVATE")
    require(type(matches) is list, "MATCH_LIST_HOLD")
    for row in matches:
        require(type(row) is dict and row.get("field_PRIVATE") in FIELDS
                and row.get("p2_story_id_PRIVATE") in seen
                and row.get("base_story_id_PRIVATE") in base_ids,
                "MATCH_PAIR_BINDING_HOLD")
    return {
        "schema": SAFE_SCHEMA,
        "status": "P2_8X172_SOURCE_PACKAGE_STRUCTURALLY_READY__SEMANTIC_CROSSWALK_HOLD",
        "p2_sources": 8,
        "base336_stories": 172,
        "base336_case_source_bindings": 336,
        "base336_current_source_rows": len(current),
        "base336_archived_source_rows": len(archived),
        "p2_snapshot_manifest_byte_binding": True,
        "p2_base336_exact_story_overlap": overlap,
        "exact_field_match_rows_metadata_count": len(matches),
        "exact_matches_semantically_adjudicated": False,
        "historical_actual_sent_verified": False,
        "r50_complete_exclusion_verified": False,
        "full_exposure_universe_closed": False,
        "all_p2_sources_semantically_independent_verified": False,
        "reviewer_independence_verified": False,
        "owner_freeze": False,
        "p2_c": "HOLD",
        "p2_b_48_prompts": "NOT_GENERATED",
        "train_admitted": 0,
        "database_accessed": False,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--p2-manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        package = parse(read_private(args.package, MAX_PACKAGE_BYTES))
        manifest_raw = read_private(args.p2_manifest, 2_000_000)
        result = evaluate(package, parse(manifest_raw), hashlib.sha256(manifest_raw).hexdigest())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 - no private values in stdout
        code = str(exc) if type(exc) is Hold else "INPUT_RUNTIME_HOLD"
        print(json.dumps({"schema": SAFE_SCHEMA, "status": "P2_8X172_SOURCE_PACKAGE_HOLD",
                          "reason_code": code, "database_accessed": False,
                          "private_values_emitted": False, "p2_c": "HOLD", "train_admitted": 0},
                         sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
