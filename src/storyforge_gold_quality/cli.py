from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .manifest import ManifestError, append_events, load_events, make_event, safe_report, validate_manifest

SOURCE_PINS = {
    "gold87": ("evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl",
               "a2038e18bee8ddef96b93bb6746270a462f9a6e4", 87),
    "gold108": ("evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl",
                "eedb8ff83e6e0629dc2dbc57ee4681fdfde3df90", 108),
}
TOOLS = [
    ("r57.exposure", "scripts/r57_g3_private_exposure_ledger.py", "private ledger + SAFE aggregate", "tests/test_r57_g3_private_exposure_ledger.py"),
    ("r57.lineage", "scripts/r57_training_lineage_audit.py", "private index -> SAFE aggregate", "tests/test_r57_training_lineage_audit.py"),
    ("r57.world", "scripts/r57_g2_target_anchored_world_audit.py", "frozen source -> SAFE aggregate", "tests/test_r57_g2_target_anchored_world_audit.py"),
    ("r57.alias", "scripts/r57_g2_alias_pair_review.py", "private roster/review -> private output", "tests/test_r57_g2_alias_pair_review.py"),
    ("r57.source-index", "scripts/r57_source_index_export.py", "frozen sources -> private index + SAFE", "tests/test_r57_source_index_export.py"),
    ("r57.admission", "scripts/r57_v04_admission_gate.py", "private admission packet -> SAFE", "tests/test_r57_v04_admission_gate.py"),
    ("r58.gold108", "experiments/r58_quality/gold108_review_binding.py", "Gold108 index/evidence -> SAFE", "experiments/r58_quality/test_gold108_review_binding.py"),
    ("r58.target-source", "experiments/r58_quality/gold195_target_source.py", "frozen Gold sources -> SAFE", "experiments/r58_quality/test_gold195_target_source.py"),
    ("r58.private-reuse", "experiments/r58_quality/private_review_evidence_reuse.py", "private manifest/tasks -> SAFE", "experiments/r58_quality/test_private_review_evidence_reuse.py"),
    ("r58.quality-v1", "experiments/r58_quality/quality_v1.py", "private reviewed rows -> SAFE", "experiments/r58_quality/test_quality_v1.py"),
    ("r58.scope", "experiments/r58_quality/gold192_scope_exclusion.py", "private tasks/queue -> SAFE", "experiments/r58_quality/test_gold192_scope_exclusion.py"),
    ("r58.packets", "experiments/r58_quality/gold192_story_review_packets.py", "private tasks -> private packets", "experiments/r58_quality/test_gold192_story_review_packets.py"),
    ("tokenizer.shared", "src/storyforge_dataset/token_preflight.py", "HF CPU token preflight primitives", "tests/test_token_preflight_core.py"),
]
SCORES = {"chinese_prose", "character_consistency", "npc_initiative",
          "player_agency", "narrative_continuity", "rule_fidelity"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path):
    if path.is_symlink() or not path.is_file():
        raise ManifestError("INPUT_NOT_REGULAR_FILE")
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    if path.is_symlink() or not path.is_file():
        raise ManifestError("INPUT_NOT_REGULAR_FILE")
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ManifestError("INPUT_ROW_NOT_OBJECT")
                rows.append(row)
    return rows


def inventory(_args):
    return {"schema": "storyforge_gold_quality_inventory_v1",
            "commands": ["inventory", "verify-source", "import-history", "import-exposure",
                         "append-review", "append-exclusion", "validate", "report-safe"],
            "registered_tools": [{"id": x[0], "path": x[1], "io_contract": x[2], "tests": x[3]}
                                 for x in TOOLS],
            "frozen_sources": {k: {"path": v[0], "git_blob_sha1": v[1], "rows": v[2]}
                               for k, v in SOURCE_PINS.items()},
            "tokenizer_single_source": "src/storyforge_dataset/token_preflight.py"}


def verify_source(args):
    root = args.repo_root.resolve(strict=True)
    result = {}
    for name, (relative, expected, count) in SOURCE_PINS.items():
        path = root / relative
        if path.is_symlink() or not path.is_file():
            result[name] = {"status": "HOLD_SOURCE_MISSING_OR_SYMLINK"}
            continue
        raw = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()
        result[name] = {"status": "PASS" if actual == expected else "HOLD_BLOB_PIN_MISMATCH",
                        "row_count_expected": count, "git_blob_pin_match": actual == expected}
    return {"schema": "storyforge_gold_quality_source_verification_v1", "sources": result,
            "all_sources_pass": all(x["status"] == "PASS" for x in result.values()),
            "private_values_emitted": False}


def import_history(args):
    rows = read_jsonl(args.input)
    expected = {"gold87": 87, "gold108": 108}[args.batch]
    cases, targets, typed, events = set(), {}, set(), []
    for row in rows:
        kind, scope = row.get("event_type"), row.get("scope", "CASE")
        if kind not in {"LEGACY_SELECTION_EVIDENCE", "LEGACY_REVIEW", "SOURCE_METADATA", "EXCLUSION"}:
            raise ManifestError("HISTORY_EVENT_TYPE_INVALID")
        payload = {k: v for k, v in row.items() if k not in {"event_type", "scope"}}
        if scope == "BATCH":
            if payload.get("case_count") != expected:
                raise ManifestError("HISTORY_BATCH_COUNT_INVALID")
            if args.batch == "gold87" and kind == "LEGACY_SELECTION_EVIDENCE":
                if (payload.get("binding_granularity") != "BATCH_LEVEL" or
                    payload.get("reviewer_independence_proven") is not False or
                    payload.get("selection_outcome") != "DUAL_ACCEPT_RECORDED"):
                    raise ManifestError("GOLD87_SELECTION_LAYER_INVALID")
            if args.batch == "gold108" and kind == "LEGACY_REVIEW":
                if (payload.get("binding_granularity") != "BATCH_LEVEL" or
                    payload.get("binding_status") != "HISTORICAL_DUAL_REVIEW_INDEX_BINDING_ONLY__NO_QUALITY_V1_ADMISSION" or
                    payload.get("reviewer_independence_proven") is not False or
                    payload.get("old_review_dimensions") != 5):
                    raise ManifestError("GOLD108_BINDING_RECEIPT_INVALID")
        elif scope == "CASE":
            case, digest = payload.get("case_id"), payload.get("target_sha256")
            if not isinstance(case, str) or not case or not isinstance(digest, str) or len(digest) != 64:
                raise ManifestError("HISTORY_CASE_IDENTITY_INVALID")
            if case in targets and targets[case] != digest:
                raise ManifestError("HISTORY_TARGET_CHANGED")
            if digest in targets.values() and targets.get(case) != digest:
                raise ManifestError("HISTORY_DUPLICATE_TARGET")
            targets[case] = digest
            cases.add(case)
            key = (case, kind)
            if key in typed:
                raise ManifestError("HISTORY_DUPLICATE_TYPED_EVENT")
            typed.add(key)
            if args.batch == "gold87" and kind == "SOURCE_METADATA":
                if payload.get("independent_gold_review") != "NOT_RUN" or payload.get("scores_are_subjective_single_review") is not True:
                    raise ManifestError("GOLD87_METADATA_LAYER_INVALID")
            if args.batch == "gold108" and kind == "LEGACY_REVIEW":
                if payload.get("rubric") != "FIVE_DIMENSION_LEGACY" or payload.get("new_quality_v1") is not False or payload.get("reviewer1_decision") != "ACCEPT" or payload.get("reviewer2_decision") != "ACCEPT":
                    raise ManifestError("GOLD108_LEGACY_REVIEW_INVALID")
        else:
            raise ManifestError("HISTORY_SCOPE_INVALID")
        payload["evidence_tier"] = payload.get("evidence_tier", "OWNER_PRIVATE_SOURCE_IMPORT")
        events.append(make_event(args.batch, kind, payload, now()))
    if len(cases) != expected:
        raise ManifestError("HISTORY_UNIQUE_CASE_COUNT_INVALID")
    if args.batch == "gold87":
        if sum(x["event_type"] == "SOURCE_METADATA" and x["payload"].get("case_id") for x in events) != 87:
            raise ManifestError("GOLD87_METADATA_INCOMPLETE")
        if not any(x["event_type"] == "LEGACY_SELECTION_EVIDENCE" for x in events):
            raise ManifestError("GOLD87_SELECTION_EVIDENCE_MISSING")
    if args.batch == "gold108":
        if sum(x["event_type"] == "LEGACY_REVIEW" and x["payload"].get("case_id") for x in events) != 108:
            raise ManifestError("GOLD108_REVIEW_BINDING_INCOMPLETE")
        if not any(x["event_type"] == "LEGACY_REVIEW" and x["payload"].get("binding_granularity") == "BATCH_LEVEL" for x in events):
            raise ManifestError("GOLD108_BINDING_RECEIPT_MISSING")
    n = append_events(args.manifest, events, args.repo_root)
    return {"schema": "storyforge_gold_quality_history_import_safe_v1", "status": "APPENDED",
            "unique_cases_imported": len(cases), "events_appended": n,
            "quality_v1_admitted": 0, "training_authorized": False, "private_values_emitted": False}


def import_exposure(args):
    data = read_json(args.input)
    if args.kind == "safe-aggregate":
        if not isinstance(data, dict) or not isinstance(data.get("schema"), str):
            raise ManifestError("EXPOSURE_AGGREGATE_INVALID")
        fields = {k: data[k] for k in ("schema", "status", "gold_totals", "exposure", "counts",
                  "evidence_tier", "source", "limits", "training_authorized", "r50_content_accessed") if k in data}
        fields["evidence_tier"] = fields.get("evidence_tier", "OWNER_RETURNED_SAFE_AGGREGATE")
        event = make_event(args.batch, "TRAINING_EXPOSURE_AGGREGATE", fields, now())
        count = append_events(args.manifest, [event], args.repo_root)
        return {"schema": "storyforge_gold_quality_exposure_import_safe_v1", "status": "AGGREGATE_APPENDED",
                "case_level_rows_imported": 0, "case_level_state": "UNKNOWN_NOT_IMPORTED",
                "events_appended": count, "private_values_emitted": False, "training_authorized": False}
    receipt = read_json(args.receipt) if args.receipt else None
    rows = data.get("rows") if isinstance(data, dict) else None
    if (not isinstance(data, dict) or data.get("schema") != "storyforge-r57-g3-private-exact-target-exposure-ledger-v1" or
        data.get("evidence_tier") != "OWNER_LOCAL_FROZEN_BYTES__NOT_ALIAS_VERIFIED" or
        data.get("training_authorized") is not False or data.get("source_content_protected_evaluation_accessed") is not False or
        not isinstance(rows, list) or len(rows) != 195):
        raise ManifestError("PRIVATE_EXPOSURE_LEDGER_INVALID")
    if (not isinstance(receipt, dict) or receipt.get("schema") != "storyforge-r57-g3-exact-target-exposure-count-only-v1" or
        receipt.get("source_byte_pins_verified_by_cli") is not True or receipt.get("gold195_rows") != 195 or
        receipt.get("dataset_v04_admitted") != 0 or receipt.get("training_authorized") is not False or
        receipt.get("r50_content_accessed") is not False):
        raise ManifestError("PRIVATE_EXPOSURE_RECEIPT_INVALID")
    events, seen, targets, ordinals = [], set(), set(), {"GOLD87": set(), "GOLD108": set()}
    valid_sources = {"V01_TRAIN", "V01_VALIDATION", "R46_TRAIN", "R46_VALIDATION", "R54_TRAIN", "R54_VALIDATION"}
    for row in rows:
        if not isinstance(row, dict):
            raise ManifestError("PRIVATE_EXPOSURE_ROW_INVALID")
        source, ordinal, digest = row.get("gold_source"), row.get("source_row_ordinal_1_based"), row.get("target_sha256_private")
        if source not in ordinals or type(ordinal) is not int or not 1 <= ordinal <= (87 if source == "GOLD87" else 108):
            raise ManifestError("PRIVATE_EXPOSURE_ORDINAL_INVALID")
        if not isinstance(digest, str) or len(digest) != 64 or digest in targets:
            raise ManifestError("PRIVATE_EXPOSURE_TARGET_INVALID")
        lineage = row.get("historical_exact_target_sources")
        if not isinstance(lineage, list) or len(lineage) != len(set(lineage)) or any(x not in valid_sources for x in lineage):
            raise ManifestError("PRIVATE_EXPOSURE_SPLIT_LINEAGE_INVALID")
        if row.get("world_alias_graph_verified") is not False or row.get("case_level_rights_quality_safety_verified") is not False or row.get("dataset_v04_decision") != "HOLD_NOT_REVIEWED":
            raise ManifestError("PRIVATE_EXPOSURE_GATE_INVALID")
        ref = f"{source}:{ordinal}"
        if ref in seen:
            raise ManifestError("PRIVATE_EXPOSURE_DUPLICATE_ROW")
        seen.add(ref)
        targets.add(digest)
        ordinals[source].add(ordinal)
        payload = dict(row)
        payload["case_ref"] = ref
        payload["target_sha256"] = digest
        events.append(make_event(args.batch, "TRAINING_EXPOSURE_ROW", payload, now()))
    if ordinals != {"GOLD87": set(range(1, 88)), "GOLD108": set(range(1, 109))}:
        raise ManifestError("PRIVATE_EXPOSURE_COVERAGE_INVALID")
    count = append_events(args.manifest, events, args.repo_root)
    return {"schema": "storyforge_gold_quality_exposure_import_safe_v1", "status": "ROW_LEDGER_APPENDED",
            "case_level_rows_imported": count, "events_appended": count,
            "private_values_emitted": False, "training_authorized": False}


def append_review(args):
    rows = read_jsonl(args.input)
    if not rows:
        raise ManifestError("REVIEW_INPUT_EMPTY")
    events, seen = [], set()
    for row in rows:
        case, digest = row.get("case_id"), row.get("target_sha256")
        if not isinstance(case, str) or not case or not isinstance(digest, str) or len(digest) != 64 or case in seen:
            raise ManifestError("REVIEW_IDENTITY_INVALID")
        if row.get("reviewer_role") not in {"REVIEWER_A", "REVIEWER_B", "AI_REVIEWER", "OWNER_ARBITER"}:
            raise ManifestError("REVIEWER_ROLE_INVALID")
        if row.get("decision") not in {"PASS", "PASS_ONLY", "HOLD", "REJECT"}:
            raise ManifestError("REVIEW_DECISION_INVALID")
        scores = row.get("scores")
        if not isinstance(scores, dict) or set(scores) != SCORES or any(type(x) is not int or not 1 <= x <= 5 for x in scores.values()):
            raise ManifestError("REVIEW_SCORES_INVALID")
        seen.add(case)
        events.append(make_event(args.batch, args.event_type, row, now()))
    count = append_events(args.manifest, events, args.repo_root)
    return {"schema": "storyforge_gold_quality_review_import_safe_v1", "status": "APPENDED",
            "events_appended": count, "private_values_emitted": False,
            "quality_v1_admitted": 0, "training_authorized": False}


def append_exclusion(args):
    rows = read_jsonl(args.input)
    if len(rows) != 3:
        raise ManifestError("GOLD192_EXCLUSION_COUNT_INVALID")
    events, seen = [], set()
    for row in rows:
        case, digest = row.get("case_id"), row.get("target_sha256")
        if not isinstance(case, str) or not isinstance(digest, str) or len(digest) != 64 or case in seen or row.get("reason_code") != "WORLD_IDENTITY_UNRESOLVED":
            raise ManifestError("GOLD192_EXCLUSION_INVALID")
        seen.add(case)
        events.append(make_event(args.batch, "EXCLUSION", {"case_id": case, "target_sha256": digest,
                            "reason_code": row["reason_code"], "quality_v1_admitted": False}, now()))
    count = append_events(args.manifest, events, args.repo_root)
    return {"schema": "storyforge_gold_quality_exclusion_import_safe_v1", "status": "APPENDED",
            "exclusion_events_appended": count, "private_values_emitted": False,
            "quality_v1_admitted": 0, "training_authorized": False}


def main():
    parser = argparse.ArgumentParser(prog="storyforge-gold-quality")
    sub = parser.add_subparsers(dest="command", required=True)

    inventory_parser = sub.add_parser("inventory")
    inventory_parser.set_defaults(func=inventory)

    verify_parser = sub.add_parser("verify-source")
    verify_parser.add_argument("--repo-root", type=Path, required=True)
    verify_parser.set_defaults(func=verify_source)

    commands = (("import-history", import_history), ("import-exposure", import_exposure),
                ("append-review", append_review), ("append-exclusion", append_exclusion))
    for name, func in commands:
        command = sub.add_parser(name)
        if name != "import-history":
            command.add_argument("--batch", required=True)
        else:
            command.add_argument("--batch", choices=("gold87", "gold108"), required=True)
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--repo-root", type=Path, required=True)
        if name == "import-exposure":
            command.add_argument("--kind", choices=("safe-aggregate", "r57-private-ledger"), required=True)
            command.add_argument("--receipt", type=Path)
        if name == "append-review":
            command.add_argument("--event-type",
                                  choices=("INCREMENTAL_REVIEW", "BLIND_REVIEW", "ADJUDICATION"),
                                  default="INCREMENTAL_REVIEW")
        command.set_defaults(func=func)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--manifest", type=Path, required=True)
    validate_parser.set_defaults(func=lambda a: {
        "schema": "storyforge_gold_quality_validation_safe_v1",
        **validate_manifest(load_events(a.manifest)),
        "quality_v1_admitted": 0,
        "training_authorized": False,
    })
    report_parser = sub.add_parser("report-safe")
    report_parser.add_argument("--manifest", type=Path, required=True)
    report_parser.set_defaults(func=lambda a: safe_report(load_events(a.manifest)))

    args = parser.parse_args()
    try:
        result = args.func(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ManifestError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        reason = str(exc) if isinstance(exc, ManifestError) else "INPUT_OR_IO_ERROR"
        print(json.dumps({
            "schema": "storyforge_gold_quality_safe_error_v1",
            "status": "HOLD",
            "reason_code": reason,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "r50_accessed": False,
        }, sort_keys=True))
        return 42

if __name__ == "__main__":
    raise SystemExit(main())
