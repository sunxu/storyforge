"""Offline, create-only Base336 independent reviewer preparation and SAFE validation.

Never transmits content or prints private story names/IDs/evidence. Uses only
Owner-provided existing private files. Independent judgment happens outside
this program; its attestations never prove reviewer independence on their own.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

PACKET_SCHEMA = "storyforge_r60_base336_component_review_packet_private_v1"
GROUP_SCHEMA = "storyforge_r60_base336_card_opening_evidence_private_v1"
REVIEW_SCHEMA = "storyforge_r60_base336_independent_edge_review_private_v2"
SCHEMA_FILENAME = "R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json"
SAFE_SCHEMA = "storyforge_r60_base336_independent_review_safe_v1"
DECISIONS = {"SAME_SEMANTIC_COMPONENT", "INDEPENDENT_TEMPLATE_ONLY", "INSUFFICIENT_EVIDENCE"}


class Hold(Exception):
    pass


def require(condition: bool, code: str):
    if not condition:
        raise Hold(code)


def regular_file(path: Path, limit: int = 900_000) -> bytes:
    require(path.is_file() and not path.is_symlink(), "INPUT_TYPE_HOLD")
    require(0 < path.stat().st_size <= limit, "INPUT_SIZE_HOLD")
    with path.open("rb") as stream:
        return stream.read(limit + 1)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_new(path: Path, payload: dict) -> None:
    raw = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(raw)


def packet_and_pin(path: Path):
    raw = regular_file(path, 600_000)
    p = json.loads(raw)
    require(p.get("schema") == PACKET_SCHEMA, "PACKET_SCHEMA_HOLD")
    edges = p.get("edges_PRIVATE")
    locators = p.get("record_locators_PRIVATE")
    require(isinstance(edges, list) and len(edges) == 26, "PACKET_EDGE_COUNT_HOLD")
    require(isinstance(locators, list) and len(locators) == 59, "PACKET_RECORD_COUNT_HOLD")
    require([e.get("edge_ordinal") for e in edges] == list(range(1, 27)), "PACKET_EDGE_ORDER_HOLD")
    require(sum(e.get("cross_split") is True for e in edges) == 10, "PACKET_SPLIT_COUNT_HOLD")
    return p, digest(raw)


def load_evidence(p: dict, input_dir: Path):
    files = p.get("input_file_sha256s_PRIVATE", [])
    require(len(files) == 8, "INPUT_PINS_HOLD")
    by_group = {}
    for group in range(1, 9):
        name = f"R60_BASE336_WORLD_GROUP_{group:02d}_CARD_OPENING_PRIVATE.json"
        pin = next((item for item in files if item.get("filename_PRIVATE") == name), None)
        require(pin is not None, "MISSING_PIN_HOLD")
        raw = regular_file(input_dir / name)
        require(digest(raw) == pin.get("sha256_PRIVATE"), "INPUT_HASH_HOLD")
        obj = json.loads(raw)
        require(obj.get("schema") == GROUP_SCHEMA, "GROUP_SCHEMA_HOLD")
        require(obj.get("roster_sha256_PRIVATE") == p.get("roster_sha256_PRIVATE"), "ROSTER_BINDING_HOLD")
        require(obj.get("group_evidence_PRIVATE", {}).get("group_ordinal") == group, "GROUP_ID_HOLD")
        by_group[group] = obj["group_evidence_PRIVATE"]["matched_source_records_PRIVATE"]

    records = []
    counters = Counter()
    for loc in p["record_locators_PRIVATE"]:
        g = loc["group_ordinal"]
        idx = counters[g]
        source = by_group[g]
        require(idx < len(source), "LOCATOR_INDEX_HOLD")
        rec = source[idx]
        counters[g] += 1
        require(rec.get("story_id_PRIVATE") == loc.get("story_id_PRIVATE"), "LOCATOR_STORY_HOLD")
        require(rec.get("source_kind") == loc.get("source_kind"), "LOCATOR_KIND_HOLD")
        require(rec.get("revision_id_PRIVATE") == loc.get("revision_id_PRIVATE"), "LOCATOR_REVISION_HOLD")
        require(rec.get("source_fields", {}).keys() == {"character_PRIVATE", "characters_PRIVATE", "opening_PRIVATE"}, "LOCATOR_FIELDS_HOLD")
        records.append(rec)
    require(len(records) == 59 and all(counters[g] == len(by_group[g]) for g in range(1, 9)), "LOCATOR_COVERAGE_HOLD")
    return records


def prepare(args):
    packet, packet_sha = packet_and_pin(args.packet)
    records = load_evidence(packet, args.inputs)
    require(not args.output_dir.exists() and not args.output_dir.is_symlink(), "OUTPUT_EXISTS_HOLD")
    require(args.output_dir.parent.is_dir() and not args.output_dir.parent.is_symlink(), "OUTPUT_PARENT_HOLD")
    os.mkdir(args.output_dir, 0o700)
    count = 0
    for edge in packet["edges_PRIVATE"]:
        if edge["cross_split"] is not True:
            continue
        idx = edge["edge_ordinal"]
        refs = {}
        # Include all matching current/archived records for each story.
        for side in ("a", "b"):
            sid = edge[f"source_{side}_PRIVATE"]
            refs[side.upper()] = [
                {"source_record_index_PRIVATE": n,
                 "source_kind": rec["source_kind"],
                 "revision_id_PRIVATE": rec.get("revision_id_PRIVATE"),
                 "group_ordinal": packet["record_locators_PRIVATE"][n]["group_ordinal"],
                 "fields_PRIVATE": rec["source_fields"]}
                for n, rec in enumerate(records) if rec["story_id_PRIVATE"] == sid
            ]
        require(refs["A"] and refs["B"], "EDGE_SOURCE_HOLD")
        write_new(args.output_dir / f"EDGE_{idx:02d}_EVIDENCE_PRIVATE.json", {
            "schema": "storyforge_r60_base336_independent_edge_evidence_private_v1",
            "edge_ordinal": idx,
            "review_packet_sha256_PRIVATE": packet_sha,
            "side_A_PRIVATE": refs["A"],
            "side_B_PRIVATE": refs["B"],
            "instructions_cn": "独立阅读两侧完整角色卡、开场和所有列出的版本。先不要看任何旧 Codex 建议。判断是否同一专属人物/组织/事件/共享剧情组件，或仅通用模板。写出具体版本和字段证据；不要凭文字匹配长度直接下结论。"
        })
        write_new(args.output_dir / f"EDGE_{idx:02d}_DECISION_PRIVATE.json", {
            "schema": REVIEW_SCHEMA,
            "edge_ordinal": idx,
            "review_packet_sha256_PRIVATE": packet_sha,
            "decision": None,
            "reason_cn_PRIVATE": "",
            "source_evidence_refs_PRIVATE": [],
            "reviewer_key_PRIVATE": "",
            "independent_execution_attested": False,
            "source_version_reviewed": False,
            "historical_actual_sent_verified": False
        })
        count += 1
    require(count == 10, "REVIEW_COUNT_HOLD")
    print(json.dumps({"status": "REVIEWER_DOSSIERS_CREATED__DECISIONS_PENDING", "review_edges": count,
                      "private_files_created": count * 2, "source_files_verified": 8,
                      "database_accessed": False, "model_requests": 0, "gpu_started": False,
                      "p2_c": "HOLD", "train_admitted": 0}, ensure_ascii=False))


def require_schema(doc: dict, schema_path: Path) -> None:
    """Validate against our versioned JSON Schema; no implicit/legacy fallback."""
    schema = json.loads(regular_file(schema_path, 100_000))
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "JSON_SCHEMA_VERSION_HOLD")
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        raise Hold("JSONSCHEMA_DEPENDENCY_HOLD") from None
    require(Draft202012Validator.check_schema(schema) is None, "JSON_SCHEMA_INVALID_HOLD")
    require(Draft202012Validator(schema).is_valid(doc), "REVIEW_JSON_SCHEMA_HOLD")


def pointer_value(obj, pointer: str):
    require(isinstance(pointer, str) and pointer.startswith("/"), "EVIDENCE_POINTER_HOLD")
    value = obj
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        # Reject malformed RFC6901 escape syntax.
        require("~" not in raw_part.replace("~1", "").replace("~0", ""), "EVIDENCE_POINTER_HOLD")
        if isinstance(value, dict):
            require(part in value, "EVIDENCE_POINTER_HOLD")
            value = value[part]
        elif isinstance(value, list):
            require(part.isdigit() and (part == "0" or not part.startswith("0")), "EVIDENCE_POINTER_HOLD")
            index = int(part)
            require(index < len(value), "EVIDENCE_POINTER_HOLD")
            value = value[index]
        else:
            raise Hold("EVIDENCE_POINTER_HOLD")
    require(value is not None and value != "" and value != [] and value != {}, "EVIDENCE_POINTER_EMPTY_HOLD")
    return value


def evidence_and_refs(edge: dict, packet: dict, packet_sha: str, records: list, reviews_dir: Path, decision: dict):
    idx = edge["edge_ordinal"]
    evidence_path = reviews_dir / f"EDGE_{idx:02d}_EVIDENCE_PRIVATE.json"
    evidence = json.loads(regular_file(evidence_path, 900_000))
    require(evidence.get("schema") == "storyforge_r60_base336_independent_edge_evidence_private_v1", "EVIDENCE_SCHEMA_HOLD")
    require(evidence.get("edge_ordinal") == idx, "EVIDENCE_EDGE_HOLD")
    require(evidence.get("review_packet_sha256_PRIVATE") == packet_sha, "EVIDENCE_PACKET_HOLD")
    keys = {"schema", "edge_ordinal", "review_packet_sha256_PRIVATE", "side_A_PRIVATE", "side_B_PRIVATE", "instructions_cn"}
    require(set(evidence) == keys, "EVIDENCE_KEYS_HOLD")
    # Rebuild the complete expected evidence dossier from pinned source files;
    # binding only its packet SHA is insufficient to detect edited dossier text.
    for side in ("A", "B"):
        story = edge[f"source_{side.lower()}_PRIVATE"]
        expected = [
            {"source_record_index_PRIVATE": n,
             "source_kind": rec["source_kind"],
             "revision_id_PRIVATE": rec.get("revision_id_PRIVATE"),
             "group_ordinal": packet["record_locators_PRIVATE"][n]["group_ordinal"],
             "fields_PRIVATE": rec["source_fields"]}
            for n, rec in enumerate(records)
            if rec["story_id_PRIVATE"] == story
        ]
        require(expected and evidence[f"side_{side}_PRIVATE"] == expected,
                "EVIDENCE_SOURCE_CONTENT_BINDING_HOLD")
    seen_sides = set()
    seen_refs = set()
    refs = decision["source_evidence_refs_PRIVATE"]
    for ref in refs:
        side = ref["side"]
        matches = [r for r in evidence[f"side_{side}_PRIVATE"]
                   if r["source_record_index_PRIVATE"] == ref["source_record_index_PRIVATE"]]
        require(len(matches) == 1, "EVIDENCE_RECORD_BINDING_HOLD")
        record = matches[0]
        require(record["source_kind"] == ref["source_kind"], "EVIDENCE_SOURCE_KIND_HOLD")
        require(record.get("revision_id_PRIVATE") == ref["revision_id_PRIVATE"], "EVIDENCE_REVISION_HOLD")
        require(record["group_ordinal"] == ref["group_ordinal"], "EVIDENCE_GROUP_HOLD")
        pointer_value(record["fields_PRIVATE"], ref["field_path"])
        key = (side, ref["source_record_index_PRIVATE"], ref["field_path"])
        require(key not in seen_refs, "EVIDENCE_DUPLICATE_REF_HOLD")
        seen_refs.add(key)
        seen_sides.add(side)
    require(seen_sides == {"A", "B"}, "EVIDENCE_BOTH_SIDES_REQUIRED_HOLD")


def verify(args):
    packet, packet_sha = packet_and_pin(args.packet)
    records = load_evidence(packet, args.inputs)
    edges = [e for e in packet["edges_PRIVATE"] if e["cross_split"] is True]
    require(args.reviews_dir.is_dir() and not args.reviews_dir.is_symlink(), "REVIEW_DIRECTORY_HOLD")
    expected_files = {f"EDGE_{e['edge_ordinal']:02d}_{suffix}_PRIVATE.json" for e in edges for suffix in ("EVIDENCE", "DECISION")}
    require({p.name for p in args.reviews_dir.iterdir()} == expected_files, "REVIEW_FILE_SET_HOLD")
    counts = Counter()
    filled = attested = source_versions_reviewed = 0
    for edge in edges:
        idx = edge["edge_ordinal"]
        path = args.reviews_dir / f"EDGE_{idx:02d}_DECISION_PRIVATE.json"
        doc = json.loads(regular_file(path, 200_000))
        require(isinstance(doc, dict), "REVIEW_DOCUMENT_HOLD")
        require_schema(doc, args.schema)
        require(doc["edge_ordinal"] == idx, "REVIEW_EDGE_HOLD")
        require(doc["review_packet_sha256_PRIVATE"] == packet_sha, "REVIEW_PACKET_BINDING_HOLD")
        decision = doc["decision"]
        if decision is None:
            counts["PENDING"] += 1
            continue
        require(len(doc["reason_cn_PRIVATE"].strip()) >= 20, "REASON_REQUIRED_HOLD")
        evidence_and_refs(edge, packet, packet_sha, records, args.reviews_dir, doc)
        require(doc["historical_actual_sent_verified"] is False, "ACTUAL_SENT_EXTERNAL_HOLD")
        counts[decision] += 1
        filled += 1
        attested += doc["independent_execution_attested"] is True
        source_versions_reviewed += doc["source_version_reviewed"] is True
    completed = filled == 10 and attested == 10 and source_versions_reviewed == 10
    safe = {"schema": SAFE_SCHEMA,
            "status": "REVIEW_FORMS_COMPLETE__OWNER_INDEPENDENCE_CHECK_PENDING" if completed else "REVIEW_INCOMPLETE_HOLD",
            "review_edges_expected": 10, "review_edges_filled": filled, "review_edges_pending": 10 - filled,
            "decision_counts": {k: counts[k] for k in ("SAME_SEMANTIC_COMPONENT", "INDEPENDENT_TEMPLATE_ONLY", "INSUFFICIENT_EVIDENCE", "PENDING")},
            "self_attested_independence_count": attested,
            "source_versions_reviewed_count": source_versions_reviewed,
            "reference_binding_verified_for_filled": filled,
            "reviewer_independence_independently_verified": False,
            "source_version_actual_sent_verified": False,
            "r50_complete_exclusion_verified": False,
            "p2_c": "HOLD", "p2_b_48_prompts": "NOT_GENERATED", "train_admitted": 0,
            "database_accessed": False, "private_values_emitted": False}
    if args.safe_output:
        require(not args.safe_output.exists() and not args.safe_output.is_symlink(), "SAFE_OUTPUT_EXISTS_HOLD")
        write_new(args.safe_output, safe)
    print(json.dumps(safe, ensure_ascii=False, sort_keys=True))

def main():
    ap = argparse.ArgumentParser()
    commands = ap.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Create private blind per-edge evidence and empty decision forms")
    prep.add_argument("--inputs", type=Path, required=True)
    prep.add_argument("--packet", type=Path, required=True)
    prep.add_argument("--output-dir", type=Path, required=True)
    validate = commands.add_parser("verify", help="Validate reviewer decisions, print aggregate SAFE only")
    validate.add_argument("--packet", type=Path, required=True)
    validate.add_argument("--inputs", type=Path, required=True)
    validate.add_argument("--reviews-dir", type=Path, required=True)
    validate.add_argument("--safe-output", type=Path)
    validate.add_argument("--schema", type=Path, default=Path(__file__).with_name(SCHEMA_FILENAME))
    args = ap.parse_args()
    try:
        if args.command == "prepare":
            prepare(args)
        else:
            verify(args)
    except Exception as exc:  # noqa: BLE001 - redact untrusted private input errors
        code = str(exc) if type(exc) is Hold else "UNEXPECTED_HOLD"
        print(json.dumps({"status": "HOLD", "reason_code": code, "private_values_emitted": False}))
        raise SystemExit(42)


if __name__ == "__main__":
    main()