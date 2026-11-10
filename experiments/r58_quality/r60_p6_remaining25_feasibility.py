"""R60 P6: one-pass existing-owner-metadata feasibility for remaining 25 cases.

Uses ONLY pinned P2/P4 private outputs and the existing P3 inventory. No
database, broad filesystem traversal, R50, payload reads, automatic promotion.
A request-like field is only a *hint*, never an authenticated attempt or input.
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
from experiments.r58_quality import r60_p4_owner_locator_probe as p4
from experiments.r58_quality.r60_p5_owner_field_audit import SENT_FIELDS

SCHEMA = "storyforge_r60_p6_remaining25_owner_feasibility_safe_v1"
OWN_ROOTS = tuple(p3.ALLOWED_BASE / x for x in (
    "r58/private/quality-v1", "r59/private/quality-v1",
))


def assess(queue: list[dict], p4_rows: list[dict], inventory: dict, loader):
    if (len(queue) != 28 or len({x.get("case_id") for x in queue}) != 28
            or any(not isinstance(x.get("target_sha256"), str) for x in queue)):
        raise p3.Hold("P2_FROZEN_QUEUE_INVALID")
    if len(p4_rows) != 3 or len({x.get("case_id") for x in p4_rows}) != 3:
        raise p3.Hold("P4_PRIOR_THREE_INVALID")
    all_cases = {x["case_id"]: x["target_sha256"] for x in queue}
    prioritized = {x["case_id"] for x in p4_rows}
    if not prioritized.issubset(all_cases) or any(
        all_cases[x["case_id"]] != x.get("target_sha256") for x in p4_rows
    ):
        raise p3.Hold("PRIOR_THREE_PIN_MISMATCH")
    remaining = set(all_cases) - prioritized
    if len(remaining) != 25:
        raise p3.Hold("REMAINING_SET_COUNT_INVALID")
    if inventory.get("schema") != "r60_p3_local_artifact_inventory_private_v1":
        raise p3.Hold("INVENTORY_SCHEMA_INVALID")
    records = inventory.get("records")
    if not isinstance(records, list) or len(records) > 100:
        raise p3.Hold("INVENTORY_RECORDS_INVALID")
    paths = []
    for record in records:
        if "OWNER" not in record.get("categories", []):
            continue
        path = Path(record["private_path"])
        if (not p3.contained(path, p3.ALLOWED_BASE)
                or not any(path.is_relative_to(root) for root in OWN_ROOTS)):
            raise p3.Hold("OWNER_SCOPE_INVALID")
        paths.append(path)
    if len(paths) > 50:
        raise p3.Hold("OWNER_LIMIT_EXCEEDED")
    found = {case_id: [] for case_id in remaining}
    skipped = Counter()
    seen_hashes = set()
    for path in paths:
        try:
            raw = loader(path, p4.MAX_OWNER_BYTES)
        except p3.Hold:
            skipped["unreadable_or_oversized"] += 1
            continue
        fingerprint = hashlib.sha256(raw).hexdigest()
        if fingerprint in seen_hashes:
            skipped["duplicate_content"] += 1
            continue
        seen_hashes.add(fingerprint)
        rows = p4.parse_owner(raw)
        if rows is None or len(rows) > 1000:
            skipped["unsupported_format"] += 1
            continue
        for row in rows:
            cid = row.get("case_id")
            if cid not in remaining:
                continue
            if row.get("target_sha256") != all_cases[cid]:
                skipped["target_hash_mismatch"] += 1
                continue
            fields = sorted(
                key for key in SENT_FIELDS
                if isinstance(row.get(key), str) and bool(row[key].strip())
            )
            found[cid].append({
                "owner_content_sha256": fingerprint,
                "request_hint_field_names": fields,
                "request_or_payload_verified": False,
                "owner_attested": False,
            })
    output = []
    for row in sorted(queue, key=lambda x: x.get("p2_priority_rank", 1000)):
        cid = row["case_id"]
        if cid not in remaining:
            continue
        observations = found[cid]
        output.append({
            "case_id": cid,
            "target_sha256": all_cases[cid],
            "p2_priority_rank": row.get("p2_priority_rank"),
            "owner_metadata_found": bool(observations),
            "request_hint_found": any(x["request_hint_field_names"] for x in observations),
            "owner_metadata_observations": observations,
            "actual_sent_model_input_verified": False,
            "attempt_response_link_verified": False,
            "owner_complete_verified": False,
            "input_evidence_class": "UNKNOWN_NOT_REVIEWED",
            "quality_v1_admitted": False,
        })
    safe = {
        "schema": SCHEMA,
        "status": "P6_REMAINING25_METADATA_FEASIBILITY_ONLY__NO_INPUT_PROOF",
        "frozen_ab_total": 28,
        "prior_three_excluded": len(prioritized),
        "remaining_cases_examined": len(output),
        "owner_inventory_files_considered": len(paths),
        "unique_owner_file_content_hashes_read": len(seen_hashes),
        "owner_metadata_found_cases": sum(x["owner_metadata_found"] for x in output),
        "owner_metadata_missing_cases": sum(not x["owner_metadata_found"] for x in output),
        "cases_with_request_field_hints": sum(x["request_hint_found"] for x in output),
        "skipped_or_mismatch_counts": dict(sorted(skipped.items())),
        "authenticated_attempt_link_count": 0,
        "exact_sent_payload_verified_count": 0,
        "independently_verified_owner_count": 0,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return output, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p2-queue", required=True, type=Path)
    parser.add_argument("--p4-owner-locators", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        queue = p3.parse_lines(p3.private_bytes(args.p2_queue, 5_000_000), 28)
        prior = p3.parse_lines(p3.private_bytes(args.p4_owner_locators, 5_000_000), 3)
        inventory = json.loads(p3.private_bytes(args.inventory, 2_000_000))
        out = args.output_dir
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()
                or stat.S_IMODE(out.parent.stat().st_mode) != 0o700
                or not out.is_relative_to(p3.ALLOWED_BASE / "r59/private")):
            raise p3.Hold("OUTPUT_DIR_INVALID")
        private, safe = assess(queue, prior, inventory, p3.private_bytes)
        out.mkdir(mode=0o700)
        for name, rows, lines in (
            ("R60_P6_REMAINING25_PRIVATE.jsonl", private, True),
            ("R60_P6_SAFE.json", safe, False),
        ):
            fd = os.open(out / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                if lines:
                    for row in rows:
                        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                else:
                    json.dump(rows, handle, ensure_ascii=False, sort_keys=True, indent=2)
                    handle.write("\n")
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0
    except (p3.Hold, OSError, ValueError, TypeError, KeyError, UnicodeError):
        print(json.dumps({
            "schema": SCHEMA, "status": "P6_HOLD",
            "reason_code": "PRIVATE_INPUT_OR_VALIDATION_FAILED",
            "quality_v1_admitted": 0, "gpu_started": False,
            "database_modified": False, "r50_accessed": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
