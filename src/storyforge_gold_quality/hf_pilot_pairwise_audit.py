"""Offline Owner-only cross-slot integrity + pairwise pilot audit.

Never uploads data, calls models or changes source/checkpoints. Emits SAFE counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

from . import hf_literary_review as reviewer
from .hf_blind_stage import SCHEMA as STAGE_SCHEMA

A_MODEL = "Qwen/Qwen3-32B"
A_REV = "9216db5781bf21249d130ec9da846c4624c16137"
B_MODEL = "zai-org/GLM-4-32B-0414"
B_REV = "077b5c2f5c43bd3239fd605a0600229e8facbd4a"
CHECKPOINT_SCHEMAS = {
    "A": "storyforge_hf_literary_checkpoint_private_v2",
    "B": "storyforge_hf_literary_checkpoint_private_v3",
}
MODEL_PINS = {"A": [A_MODEL, A_REV], "B": [B_MODEL, B_REV]}
SAFE_SCHEMA = "storyforge_r60_hf_pilot10_owner_pairwise_safe_v1"
REQUIRED_RECEIPT_FIELDS = {
    "schema", "position", "blind_id", "input_sha256", "model",
    "revision", "policy", "response", "receipt_sha256",
}
MAX_JSON_BYTES = 3_000_000


class AuditHold(ValueError):
    """Private review integrity failure, never contain private values."""


def read_json(path: Path, limit: int = MAX_JSON_BYTES) -> dict:
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= limit):
        raise AuditHold("PRIVATE_FILE_HOLD")
    try:
        value = json.loads(path.read_bytes())
    except (ValueError, UnicodeDecodeError):
        raise AuditHold("PRIVATE_JSON_HOLD") from None
    if not isinstance(value, dict):
        raise AuditHold("PRIVATE_SCHEMA_HOLD")
    return value


def read_input(path: Path, sha256: str) -> list[dict]:
    if path.is_symlink() or not path.is_file():
        raise AuditHold("BLIND_INPUT_MISSING_HOLD")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise AuditHold("BLIND_INPUT_HASH_HOLD")
    try:
        return reviewer.read_input(path)
    except reviewer.ReviewError:
        raise AuditHold("BLIND_INPUT_CONTRACT_HOLD") from None


def verified_sources(stage_root: Path) -> tuple[dict, dict, dict[str, list[dict]]]:
    if stage_root.is_symlink() or not stage_root.is_dir():
        raise AuditHold("STAGE_ROOT_HOLD")
    owner = stage_root / "owner"
    if owner.is_symlink() or not owner.is_dir():
        raise AuditHold("OWNER_FOLDER_HOLD")
    manifest = read_json(owner / "stage_manifest.private.json", 50_000)
    crosswalk = read_json(owner / "owner_crosswalk.private.json")
    receipt = manifest.get("receipt_sha256")
    payload = {key: val for key, val in manifest.items() if key != "receipt_sha256"}
    if (manifest.get("schema") != STAGE_SCHEMA
            or crosswalk.get("schema") != STAGE_SCHEMA
            or manifest.get("pool_sha256") != crosswalk.get("pool_sha256")
            or receipt != reviewer.digest(payload)
            or manifest.get("count") != 1000
            or crosswalk.get("count") != 1000
            or manifest.get("model_pins") != MODEL_PINS
            or set(crosswalk.get("bindings", {})) != {"A", "B"}
            or set(manifest.get("source_sha256", {})) != {"A", "B"}):
        raise AuditHold("OWNER_MANIFEST_HOLD")
    rows_by_slot: dict[str, list[dict]] = {}
    source_by_slot: dict[str, dict[int, tuple[dict, dict]]] = {}
    for slot in ("A", "B"):
        rows = read_input(stage_root / f"input_{slot}" / "source.private.jsonl",
                          manifest["source_sha256"][slot])
        bindings = crosswalk["bindings"][slot]
        if not isinstance(bindings, list) or len(bindings) != 1000 or len(rows) != 1000:
            raise AuditHold("OWNER_BINDING_COUNT_HOLD")
        joined: dict[int, tuple[dict, dict]] = {}
        blind_seen: set[str] = set()
        for row, binding in zip(rows, bindings, strict=True):
            if (not isinstance(binding, dict)
                    or type(binding.get("source_index")) is not int
                    or not 0 <= binding["source_index"] < 1000
                    or binding["source_index"] in joined
                    or row["blind_id"] in blind_seen
                    or binding.get("blind_id") != row["blind_id"]
                    or not isinstance(binding.get("case_key"), str)
                    or not binding["case_key"]):
                raise AuditHold("OWNER_BINDING_IDENTITY_HOLD")
            blind_seen.add(row["blind_id"])
            joined[binding["source_index"]] = (row, binding)
        if len(joined) != 1000:
            raise AuditHold("OWNER_BINDING_COVERAGE_HOLD")
        source_by_slot[slot] = joined
        rows_by_slot[slot] = rows
    for source_index in range(1000):
        arow, abind = source_by_slot["A"][source_index]
        brow, bbind = source_by_slot["B"][source_index]
        if (arow["blind_id"] == brow["blind_id"]
                or arow["target_text"] != brow["target_text"]
                or arow["visible_history"] != brow["visible_history"]
                or arow["target_semantics"] != brow["target_semantics"]
                or abind["case_key"] != bbind["case_key"]
                or abind["target_sha256"] != bbind["target_sha256"]
                or abind["history_sha256"] != bbind["history_sha256"]):
            raise AuditHold("OWNER_CROSS_SLOT_SOURCE_HOLD")
    return manifest, crosswalk, rows_by_slot


def verified_checkpoint(path: Path, row: dict, position: int, slot: str) -> dict:
    record = read_json(path, 16_000)
    payload = {key: val for key, val in record.items() if key != "receipt_sha256"}
    if (set(record) != REQUIRED_RECEIPT_FIELDS
            or record["receipt_sha256"] != reviewer.digest(payload)
            or record["schema"] != CHECKPOINT_SCHEMAS[slot]
            or record["position"] != position
            or record["blind_id"] != row["blind_id"]
            or record["input_sha256"] != reviewer.input_digest(row)
            or record["policy"] != reviewer.POLICY
            or record["model"] != MODEL_PINS[slot][0]
            or record["revision"] != MODEL_PINS[slot][1]):
        raise AuditHold("CHECKPOINT_IDENTITY_OR_DIGEST_HOLD")
    try:
        reviewer.validate_response(record["response"], row)
    except reviewer.ReviewError:
        raise AuditHold("CHECKPOINT_RESPONSE_CONTRACT_HOLD") from None
    return record["response"]


def audit(stage_root: Path, a_dir: Path, b_dir: Path) -> dict:
    _, crosswalk, rows_by_slot = verified_sources(stage_root)
    observed: dict[str, dict[int, dict]] = {}
    flags: dict[str, Counter] = {}
    choices: dict[str, Counter] = {}
    contradictions: dict[str, int] = {}
    for slot, folder in (("A", a_dir), ("B", b_dir)):
        if folder.is_symlink() or not folder.is_dir():
            raise AuditHold("REVIEW_DIRECTORY_HOLD")
        records: dict[int, dict] = {}
        flags[slot] = Counter()
        choices[slot] = Counter()
        contradictions[slot] = 0
        for pos in range(1, 6):
            row = rows_by_slot[slot][pos - 1]
            response = verified_checkpoint(
                folder / reviewer.checkpoint_name(pos), row, pos, slot)
            binding = crosswalk["bindings"][slot][pos - 1]
            source_index = binding["source_index"]
            if source_index in records:
                raise AuditHold("REVIEW_SOURCE_DUPLICATE_HOLD")
            records[source_index] = response
            choices[slot][response["decision"]] += 1
            for flag, active in response["severe_flags"].items():
                flags[slot][flag] += int(active)
            contradictions[slot] += int(
                response["severe_flags"]["serious_player_agency"]
                and response["scores"]["player_agency"] >= 4)
        observed[slot] = records
    matched = set(observed["A"]) & set(observed["B"])
    agreement = sum(
        observed["A"][idx]["decision"] == observed["B"][idx]["decision"]
        for idx in matched
    )
    flags_agree = sum(
        observed["A"][idx]["severe_flags"] == observed["B"][idx]["severe_flags"]
        for idx in matched
    )
    return {
        "schema": SAFE_SCHEMA,
        "status": "OWNER_PAIRWISE_AUDIT_COMPLETE__SEMANTIC_HOLD",
        "stage_case_count": 1000,
        "owner_manifest_receipt_verified": True,
        "input_hash_and_cross_slot_binding_verified": True,
        "checkpoint_receipt_and_input_sha256_verified": {"A": 5, "B": 5},
        "checkpoint_validation_complete": True,
        "cases_reviewed_by_slot": {"A": 5, "B": 5},
        "unique_source_cases_in_pilot": len(set(observed["A"]) | set(observed["B"])),
        "matched_cases": len(matched),
        "matched_decision_agreement": agreement,
        "matched_severe_flag_agreement": flags_agree,
        "unmatched_A": 5-len(matched), "unmatched_B": 5-len(matched),
        "per_slot_decisions": {k: dict(choices[k]) for k in ("A", "B")},
        "per_slot_severe_counts": {k: dict(flags[k]) for k in ("A", "B")},
        "severe_agency_with_score_ge4": contradictions,
        "true_dual_model_agreement_evaluable": bool(matched),
        "semantic_severity_adjudication_complete": False,
        "quality_v1_admitted": 0, "training_authorized": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", required=True, type=Path)
    parser.add_argument("--review-a-dir", required=True, type=Path)
    parser.add_argument("--review-b-dir", required=True, type=Path)
    parser.add_argument("--safe-output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.stage_root, args.review_a_dir, args.review_b_dir)
        dest = args.safe_output
        if dest.exists() or dest.is_symlink() or not dest.parent.is_dir():
            raise AuditHold("SAFE_OUTPUT_EXISTS_OR_PARENT_HOLD")
        data = reviewer.canonical(result) + b"\n"
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, "O_NOFOLLOW", 0), stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        print(data.decode("utf-8"), end="")
        return 0
    except (AuditHold, OSError) as exc:
        reason = str(exc) if isinstance(exc, AuditHold) else "SAFE_OUTPUT_IO_HOLD"
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "OWNER_PAIRWISE_AUDIT_HOLD",
            "reason_code": reason, "quality_v1_admitted": 0,
            "training_authorized": False, "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
