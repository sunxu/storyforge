"""Bind approved P2 public-card source snapshots to captured Gold48, offline.

Thin join atop the existing Gold48 candidate preflight, source-first inventory,
and frozen Base336 P2 source-evidence format. No database, model, network,
training, inference, or rewriting. Output is Owner-private and NOT a Prompt Freeze.
Only actual existing public snapshot fields are bound. System/Rules/Memory
and historical provider-effective inputs are not inferred or fabricated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

from r60_p2_gold48_candidate_preflight_cpu import evaluate as preflight

EVIDENCE_SCHEMA = "storyforge_r60_base336_p2_source_evidence_private_v1"
INVENTORY_SCHEMA = "storyforge_r60_base336_p2_public_source_inventory_private_v2"
INVENTORY_STATUS = "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING"
SAFE_SCHEMA = "storyforge_r60_p2_gold48_source_component_bind_safe_v1"
FIELDS = ("world", "character", "characters", "opening")
MAX_BYTES = 32 * 1024 * 1024


class Hold(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Hold(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def private_json(path, maximum):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
            and stat.S_IMODE(info.st_mode) == 0o600
            and 0 < info.st_size <= maximum, "PRIVATE_INPUT_MODE_OR_SIZE_HOLD")
    raw = path.read_bytes()
    obj = json.loads(raw)
    require(isinstance(obj, dict), "PRIVATE_INPUT_SCHEMA_HOLD")
    return obj, raw


def check_private_root(path):
    require(path.is_absolute() and path.is_dir() and not path.is_symlink()
            and stat.S_IMODE(path.stat().st_mode) == 0o700,
            "OWNER_PRIVATE_ROOT_HOLD")


def join(derived_dir, evidence_path, inventory_path):
    receipt = preflight(derived_dir)
    require(receipt["status"] == "GOLD48_PRIVATE_CANDIDATE_PREFLIGHT_PASS__NOT_FROZEN",
            "GOLD48_CANDIDATES_PREFLIGHT_HOLD")
    evidence, evidence_raw = private_json(evidence_path, MAX_BYTES)
    inventory, inventory_raw = private_json(inventory_path, 2 * 1024 * 1024)
    require(inventory.get("schema") == INVENTORY_SCHEMA
            and inventory.get("status") == INVENTORY_STATUS
            and inventory.get("rights_scope") ==
            "OWNER_APPROVED_INTERNAL_EVALUATION_PROMPT_CONSTRUCTION_ONLY__"
            "NO_TRAINING_OR_REDISTRIBUTION",
            "PUBLIC_SOURCE_MANIFEST_CONTRACT_HOLD")
    require(evidence.get("schema") == EVIDENCE_SCHEMA
            and evidence.get("p2_scope", {}).get("manifest_sha256_PRIVATE") ==
            sha(inventory_raw), "SOURCE_EVIDENCE_MANIFEST_SHA_HOLD")
    sources = inventory.get("sources")
    evidence_rows = evidence["p2_scope"].get("source_records_PRIVATE")
    require(isinstance(sources, list) and len(sources) == 8
            and isinstance(evidence_rows, list) and len(evidence_rows) == 8,
            "SOURCE_RECORD_COUNT_HOLD")
    by_story = {}
    for row in sources:
        require(isinstance(row, dict)
                and isinstance(row.get("story_id"), str)
                and row["story_id"] not in by_story
                and row.get("snapshot_matches_current_public_v2") is True
                and row.get("snapshot_hash_matches_submission_sha256") is True
                and row.get("permission_submission_bound") is True
                and row.get("permission_to_visibility") == "public",
                "INVENTORY_SOURCE_IDENTITY_OR_RIGHTS_HOLD")
        by_story[row["story_id"]] = row
    evidence_by_story = {}
    for record in evidence_rows:
        require(isinstance(record, dict)
                and isinstance(record.get("story_id_PRIVATE"), str)
                and record["story_id_PRIVATE"] not in evidence_by_story,
                "EVIDENCE_SOURCE_IDENTITY_HOLD")
        source = by_story.get(record["story_id_PRIVATE"])
        require(source is not None
                and record.get("source_key_PRIVATE") == source.get("source_key")
                and record.get("public_content_revision_PRIVATE") ==
                source.get("public_content_revision")
                and record.get("submission_snapshot_sha256_PRIVATE") ==
                source.get("submission_snapshot_sha256")
                and record.get("world_json_md5_PRIVATE") ==
                source.get("world_json_md5"),
                "SOURCE_REVISION_SNAPSHOT_CROSSWALK_HOLD")
        fields = record.get("source_fields_PRIVATE")
        require(isinstance(fields, dict) and set(fields) == set(FIELDS)
                and fields.get("world") is not None
                and fields.get("opening") is not None
                and (fields.get("character") is not None
                     or fields.get("characters") is not None),
                "PUBLIC_STORY_COMPONENTS_INCOMPLETE_HOLD")
        evidence_by_story[record["story_id_PRIVATE"]] = {
            "source_key": source["source_key"],
            "revision": source["public_content_revision"],
            "snapshot": source["submission_snapshot_sha256"],
            "component_hashes": {
                name: sha(canonical(fields[name])) if fields[name] is not None else None
                for name in FIELDS
            },
        }
    require(set(by_story) == set(evidence_by_story),
            "PUBLIC_EVIDENCE_STORY_COVERAGE_HOLD")

    locator_doc, locator_raw = private_json(
        derived_dir / "GOLD48_CANDIDATE_LOCATORS_PRIVATE.json", 5 * 1024 * 1024)
    prompt_doc, prompt_raw = private_json(
        derived_dir / "GOLD48_CANDIDATE_PREFIXES_PRIVATE.json", MAX_BYTES)
    locator_rows = locator_doc.get("cases_PRIVATE")
    prompt_rows = prompt_doc.get("cases_PRIVATE")
    require(isinstance(locator_rows, list) and len(locator_rows) == 48
            and isinstance(prompt_rows, list) and len(prompt_rows) == 48,
            "GOLD48_SOURCE_CASE_COUNT_HOLD")
    prompt_by_id = {x["candidate_case_id_PRIVATE"]: x for x in prompt_rows}
    output_cases = []
    counts = Counter()
    for loc in locator_rows:
        story = loc.get("story_id_PRIVATE")
        case_id = loc.get("candidate_case_id_PRIVATE")
        reference = evidence_by_story.get(story)
        history = prompt_by_id.get(case_id)
        require(reference is not None and isinstance(history, dict)
                and loc.get("source_key_PRIVATE") == reference["source_key"]
                and loc.get("source_public_revision_PRIVATE") == reference["revision"]
                and loc.get("source_snapshot_sha256_PRIVATE") == reference["snapshot"]
                and loc.get("prefix_sha256_PRIVATE") ==
                history.get("prefix_sha256_PRIVATE"),
                "CASE_PUBLIC_CARD_SOURCE_BINDING_HOLD")
        counts[story] += 1
        output_cases.append({
            "candidate_case_id_PRIVATE": case_id,
            "story_id_PRIVATE": story,
            "source_key_PRIVATE": reference["source_key"],
            "source_public_revision_PRIVATE": reference["revision"],
            "source_snapshot_sha256_PRIVATE": reference["snapshot"],
            "prefix_sha256_PRIVATE": loc["prefix_sha256_PRIVATE"],
            "public_component_hashes_PRIVATE": reference["component_hashes"],
            "public_component_provenance": "EVALUATION_TIME_SNAPSHOT",
            "historical_asof_card_verified": False,
            "system_rule_memory_provider_input_verified": False,
            "actual_sent_prompt_bytes_verified": False,
            "reconstructed_messages_frozen": False,
            "original_reference_included": False,
        })
    require(len(counts) == 8 and set(counts.values()) == {6},
            "SOURCE_CASE_BALANCE_HOLD")
    package = {
        "schema": "storyforge_r60_gold48_source_component_binding_private_v1",
        "status": "PUBLIC_CARD_COMPONENTS_BOUND__RECONSTRUCTED_INPUT_PENDING",
        "eval_input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "source_evidence_file_sha256_PRIVATE": sha(evidence_raw),
        "source_manifest_file_sha256_PRIVATE": sha(inventory_raw),
        "gold48_locators_file_sha256_PRIVATE": sha(locator_raw),
        "gold48_prefixes_file_sha256_PRIVATE": sha(prompt_raw),
        "cases_PRIVATE": output_cases,
    }
    safe = {
        "schema": SAFE_SCHEMA,
        "status": "GOLD48_PUBLIC_SOURCE_COMPONENTS_BOUND__INPUT_NOT_FROZEN",
        "case_count": len(output_cases),
        "source_count": len(counts),
        "case_count_per_source": 6,
        "public_card_component_binding_count": len(output_cases),
        "history_prefix_hash_binding_count": len(output_cases),
        "evaluation_time_snapshot": True,
        "historical_asof_card_verified": False,
        "system_rules_memory_reconstruction_verified": False,
        "actual_sent_prompt_bytes_verified": False,
        "owner_gold48_freeze": False,
        "database_accessed": False,
        "files_modified_before_output": False,
        "gpu_started": False,
        "model_calls": 0,
        "private_values_emitted": False,
    }
    return package, safe


def create_new(path, doc):
    raw = canonical(doc) + b"\n"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def run(args):
    root = Path.home() / ".local/share/storyforge/r60/private"
    check_private_root(root)
    require(args.candidate_dir.parent == root
            and args.evidence.is_relative_to(root)
            and args.manifest.is_relative_to(root)
            and args.output_dir.parent == root
            and not args.output_dir.exists()
            and not args.output_dir.is_symlink(),
            "SOURCE_COMPONENT_PATH_SCOPE_HOLD")
    package, safe = join(args.candidate_dir, args.evidence, args.manifest)
    os.mkdir(args.output_dir, mode=0o700)
    require(stat.S_IMODE(args.output_dir.stat().st_mode) == 0o700,
            "COMPONENT_OUTPUT_DIR_MODE_HOLD")
    create_new(args.output_dir / "GOLD48_SOURCE_COMPONENT_BINDINGS_PRIVATE.json",
               package)
    create_new(args.output_dir / "GOLD48_SOURCE_COMPONENT_BINDING_SAFE.json", safe)
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
    except (Hold, ValueError, TypeError, KeyError, IndexError, OSError) as exc:
        # Hold codes are internal fixed literals. Never reveal exception text
        # from filesystem, JSON parsing, or other untrusted inputs.
        reason = (str(exc) if isinstance(exc, Hold)
                  else "GOLD48_SOURCE_COMPONENT_UNEXPECTED_RUNTIME_HOLD")
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "HOLD",
            "reason_code": reason,
            "database_accessed": False, "gpu_started": False,
            "model_calls": 0, "private_values_emitted": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
