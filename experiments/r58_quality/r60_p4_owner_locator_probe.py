"""R60 P4: targeted Owner evidence locator for Stage/P2 intersection.

Read-only private 3-case investigation, no database, GPU, R50 or promotion.
Metadata fields are hints, NOT proofs of sent input or Owner approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path

from experiments.r58_quality import r60_p3_stage_pair_probe as p3
from experiments.r58_quality.r59_staging_receipt import valid_staging_receipt

SCHEMA = "storyforge_r60_p4_targeted_owner_locator_safe_v1"
MAX_OWNER_BYTES = 32_000_000
MAX_OWNER_ROWS = 1000


def parse_owner(raw: bytes) -> list[dict] | None:
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            return obj if all(isinstance(x, dict) for x in obj) else None
        if isinstance(obj, dict):
            for key in ("records", "cases", "rows", "owner_rows"):
                rows = obj.get(key)
                if isinstance(rows, list) and all(isinstance(x, dict) for x in rows):
                    return rows
            return [obj]
    except (ValueError, UnicodeError):
        pass
    try:
        rows = p3.parse_lines(raw, MAX_OWNER_ROWS)
        return rows if rows else None
    except (ValueError, UnicodeError, p3.Hold):
        return None


def inspect(inventory: dict, pairs: list[dict], queue: list[dict], load) -> tuple[list[dict], dict]:
    if (inventory.get("schema") != "r60_p3_local_artifact_inventory_private_v1"
            or not isinstance(inventory.get("records"), list)):
        raise p3.Hold("INVENTORY_SCHEMA_INVALID")
    records = inventory["records"]
    owners = [r for r in records if "OWNER" in r.get("categories", [])]
    if len(owners) > 50:
        raise p3.Hold("OWNER_INVENTORY_BOUND_EXCEEDED")
    if len(queue) != 28 or len({r.get("case_id") for r in queue}) != 28:
        raise p3.Hold("P2_QUEUE_INVALID")
    selected = {r["case_id"]: r for r in queue}
    candidate_ids = set()
    for pair in pairs:
        stage_path = Path(pair["stage_private_path"])
        receipt_path = Path(pair["receipt_private_path"])
        if not all(p3.contained(x, p3.ALLOWED_BASE) for x in (stage_path, receipt_path)):
            raise p3.Hold("STAGE_PAIR_SCOPE_INVALID")
        stage_raw = load(stage_path, 160_000_000)
        receipt_raw = load(receipt_path, 2_000_000)
        if (hashlib.sha256(stage_raw).hexdigest() != pair["stage_sha256"]
                or hashlib.sha256(receipt_raw).hexdigest() != pair["receipt_sha256"]
                or not valid_staging_receipt(json.loads(receipt_raw), pair["stage_sha256"])):
            raise p3.Hold("STAGE_PAIR_PIN_DRIFT")
        rows = p3.parse_lines(stage_raw, 192)
        ready = {r["case_id"] for r in rows
                 if r.get("status") == p3.STAGE_STATUS
                 and r.get("schema") == p3.STAGE_SCHEMA}
        if (sorted(ready) != pair.get("staged_case_ids_private")
                or len(ready) != pair.get("staged_status_total")
                or len(ready & selected.keys()) != pair.get("staged_intersection_p2")):
            raise p3.Hold("STAGE_PAIR_IDENTITY_DRIFT")
        candidate_ids.update(ready & selected.keys())
    if not candidate_ids or len(candidate_ids) > 28:
        raise p3.Hold("STAGE_AB_INTERSECTION_INVALID")

    evidence_names = (
        "reviewer_a_evidence_ref", "reviewer_b_evidence_ref",
        "owner_supplemental_severe_evidence_ref",
        "source_version_sha256", "world_component_id",
        "world_graph_sha256", "split", "request_attempt_id",
        "request_id", "relay_request_id", "provider_request_id",
        "sent_payload_sha256", "exact_sent_payload_sha256",
    )
    matched = {cid: [] for cid in candidate_ids}
    stats = Counter()
    for record in owners:
        path = Path(record["private_path"])
        if not (p3.contained(path, p3.ALLOWED_BASE)
                and any(path.is_relative_to(p3.ALLOWED_BASE / sub) for sub in (
                    "r58/private/quality-v1", "r59/private/quality-v1"
                ))):
            raise p3.Hold("OWNER_PATH_SCOPE_INVALID")
        stats["owner_files_considered"] += 1
        try:
            raw = load(path, MAX_OWNER_BYTES)
        except p3.Hold:
            stats["owner_files_unreadable_or_oversized"] += 1
            continue
        rows = parse_owner(raw)
        if rows is None or len(rows) > MAX_OWNER_ROWS:
            stats["owner_files_not_supported_json_rows"] += 1
            continue
        stats["owner_files_parseable"] += 1
        for row in rows:
            cid = row.get("case_id")
            if cid not in candidate_ids:
                continue
            if row.get("target_sha256") != selected[cid].get("target_sha256"):
                stats["case_id_with_target_mismatch"] += 1
                continue
            fields_present = sorted(k for k in evidence_names
                                    if isinstance(row.get(k), str) and bool(row[k].strip()))
            matched[cid].append({
                "owner_file_sha256": hashlib.sha256(raw).hexdigest(),
                "private_owner_file_path": str(path),
                "metadata_field_names_present": fields_present,
                "has_evidence_dict": isinstance(row.get("evidence"), dict),
                "has_owner_supplemental_flags": isinstance(
                    row.get("owner_supplemental_severe_flags"), dict
                ),
                "proof_independently_verified": False,
            })
            stats["owner_rows_identity_target_matched"] += 1
    rows_out = []
    for cid in sorted(candidate_ids):
        findings = matched[cid]
        rows_out.append({
            "case_id": cid,
            "target_sha256": selected[cid]["target_sha256"],
            "stage_receipt_identity_verified": True,
            "owner_locator_matches": findings,
            "owner_evidence_verified": False,
            "actual_sent_payload_verified": False,
            "attempt_response_link_verified": False,
            "protected_world_exposure_verified": False,
            "input_evidence_class": "UNKNOWN_NOT_REVIEWED",
            "quality_v1_admitted": False,
        })
    safe = {
        "schema": SCHEMA,
        "status": "P4_OWNER_LOCATORS_CHECKED__NO_EVIDENCE_PROMOTION",
        "stage_and_ab_intersection_count": len(candidate_ids),
        "owner_files_considered": stats["owner_files_considered"],
        "owner_files_parseable": stats["owner_files_parseable"],
        "owner_files_unreadable_or_oversized": stats["owner_files_unreadable_or_oversized"],
        "owner_files_not_supported_json_rows": stats["owner_files_not_supported_json_rows"],
        "owner_rows_identity_target_matched": stats["owner_rows_identity_target_matched"],
        "candidate_cases_with_owner_locator": sum(bool(matched[cid]) for cid in candidate_ids),
        "candidate_cases_without_owner_locator": sum(not matched[cid] for cid in candidate_ids),
        "case_id_with_target_mismatch": stats["case_id_with_target_mismatch"],
        "old_strict_structural_ready_5_recomputed": False,
        "actual_sent_payload_verified_count": 0,
        "request_attempt_linkage_verified_count": 0,
        "owner_evidence_verified_count": 0,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return rows_out, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("inventory", "stage-pairs", "p2-queue", "output-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        inventory = json.loads(p3.private_bytes(args.inventory, 2_000_000))
        pairs = json.loads(p3.private_bytes(args.stage_pairs, 2_000_000))
        queue = p3.parse_lines(p3.private_bytes(args.p2_queue, 5_000_000), 28)
        if not isinstance(pairs, list) or not 1 <= len(pairs) <= 3:
            raise p3.Hold("STAGE_PAIRS_INVALID")
        out = args.output_dir
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()
                or stat.S_IMODE(out.parent.stat().st_mode) != 0o700
                or not out.is_relative_to(p3.ALLOWED_BASE / "r59/private")):
            raise p3.Hold("PRIVATE_OUTPUT_DIR_INVALID")
        rows, safe = inspect(inventory, pairs, queue, p3.private_bytes)
        out.mkdir(mode=0o700)
        for name, obj, line_mode in (
            ("R60_P4_OWNER_LOCATORS_PRIVATE.jsonl", rows, True),
            ("R60_P4_SAFE.json", safe, False),
        ):
            fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                if line_mode:
                    for row in obj:
                        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                else:
                    json.dump(obj, stream, ensure_ascii=False, sort_keys=True, indent=2)
                    stream.write("\n")
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (p3.Hold, OSError, ValueError, TypeError, KeyError, UnicodeError):
        print(json.dumps({
            "schema": SCHEMA, "status": "P4_HOLD",
            "reason_code": "PRIVATE_INPUT_OR_PAIR_VALIDATION_FAILED",
            "quality_v1_admitted": 0, "gpu_started": False,
            "database_modified": False, "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
