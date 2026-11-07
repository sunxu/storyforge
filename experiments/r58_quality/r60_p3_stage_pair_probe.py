"""R60 P3: validate bounded Stage+receipt pairs against P2 frozen queue.

No production database, no R50, no archive discovery, no admission. Only
previously inventoried private filenames are read; zero source text is printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

from experiments.r58_quality.r59_staging_receipt import valid_staging_receipt

SCHEMA = "storyforge_r60_p3_stage_pair_safe_v1"
ALLOWED_BASE = Path.home() / ".local/share/storyforge"
STAGE_SCHEMA = "storyforge-quality-v1-source-staging-private-v1"
STAGE_STATUS = "SOURCE_CONTEXT_STAGED__QUALITY_REVIEW_PENDING"


class Hold(ValueError):
    pass


def fail(code: str) -> None:
    print(json.dumps({
        "schema": SCHEMA, "status": "P3_HOLD", "reason_code": code,
        "quality_v1_admitted": 0, "gpu_started": False,
        "database_modified": False, "r50_accessed": False,
        "private_values_emitted": False,
    }, sort_keys=True), file=sys.stderr)


def private_bytes(path: Path, limit: int) -> bytes:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise Hold("PRIVATE_INPUT_NOT_REGULAR")
    if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise Hold("PRIVATE_INPUT_PARENT_MODE")
    st = path.stat()
    if (stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1
            or not 0 < st.st_size <= limit):
        raise Hold("PRIVATE_INPUT_MODE_OR_SIZE")
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) != st.st_size:
        raise Hold("PRIVATE_INPUT_CHANGED")
    return raw


def parse_lines(raw: bytes, limit: int) -> list[dict]:
    lines = [json.loads(l) for l in raw.splitlines() if l.strip()]
    if len(lines) > limit or any(not isinstance(x, dict) for x in lines):
        raise Hold("INPUT_ROWS_INVALID")
    return lines


def contained(path: Path, base: Path) -> bool:
    return path.is_relative_to(base) and not any(
        part.lower() in ("archive", "diagnostic", "r50")
        for part in path.parts
    )


def investigate(inventory: dict, p2_rows: list[dict], loader) -> tuple[list[dict], dict]:
    if inventory.get("schema") != "r60_p3_local_artifact_inventory_private_v1":
        raise Hold("INVENTORY_SCHEMA_INVALID")
    records = inventory.get("records")
    if not isinstance(records, list) or len(records) > 100:
        raise Hold("INVENTORY_COUNT_INVALID")
    for record in records:
        path = Path(record["private_path"])
        if (not contained(path, ALLOWED_BASE) or
                not any(path.is_relative_to(ALLOWED_BASE / sub) for sub in (
                    "r58/private/quality-v1", "r59/private/quality-v1"
                ))):
            raise Hold("INVENTORY_SCOPE_INVALID")
    ids = {row.get("case_id") for row in p2_rows if row.get("explicit_ab_selected", True)}
    if (len(p2_rows) != 28 or len(ids) != 28 or
            any(not isinstance(x, str) or not x for x in ids)):
        raise Hold("P2_QUEUE_INVALID")
    stages = [r for r in records if "STAGE" in r.get("categories", [])]
    receipts = [r for r in records if "RECEIPT" in r.get("categories", [])]
    pairs = []
    private = []
    for stage in stages:
        stage_raw = loader(Path(stage["private_path"]), 160_000_000)
        stage_hash = hashlib.sha256(stage_raw).hexdigest()
        for receipt in receipts:
            try:
                receipt_raw = loader(Path(receipt["private_path"]), 2_000_000)
                receipt_doc = json.loads(receipt_raw)
            except (Hold, ValueError, UnicodeError):
                continue
            if not valid_staging_receipt(receipt_doc, stage_hash):
                continue
            rows = parse_lines(stage_raw, 192)
            seen = set()
            ready = set()
            for row in rows:
                if row.get("schema") != STAGE_SCHEMA:
                    raise Hold("MATCHED_STAGE_SCHEMA_INVALID")
                cid = row.get("case_id")
                if not isinstance(cid, str) or not cid or cid in seen:
                    raise Hold("MATCHED_STAGE_IDENTITY_INVALID")
                seen.add(cid)
                if row.get("status") == STAGE_STATUS:
                    ready.add(cid)
            pairs.append({
                "stage_sha256": stage_hash,
                "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
                "stage_private_path": stage["private_path"],
                "receipt_private_path": receipt["private_path"],
                "stage_rows": len(rows),
                "staged_status_total": len(ready),
                "staged_intersection_p2": len(ready & ids),
                "staged_case_ids_private": sorted(ready),
                "structural_strict_ready_proven": False,
            })
            private.append((len(ready), len(ready & ids)))
    counts = sorted(set((a, b) for a, b in private))
    safe = {
        "schema": SCHEMA,
        "status": "P3_STAGE_PAIRS_CHECKED_NOT_STRICT_READY",
        "inventory_file_count": len(records),
        "stage_filename_candidates": len(stages),
        "receipt_filename_candidates": len(receipts),
        "validated_stage_receipt_pairs": len(pairs),
        "pair_counts_staged_and_p2_intersection": [
            {"staged_status_total": a, "intersection_with_28": b}
            for a, b in counts
        ],
        "old_strict_structural_ready_5_recomputed": False,
        "actual_input_A_or_B_proven": False,
        "input_evidence_unknown": 192,
        "quality_v1_admitted": 0, "gpu_started": False,
        "database_modified": False, "r50_accessed": False,
        "private_values_emitted": False,
    }
    return pairs, safe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--p2-queue", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        inventory = json.loads(private_bytes(args.inventory, 2_000_000))
        p2_rows = parse_lines(private_bytes(args.p2_queue, 5_000_000), 28)
        out = args.output_dir
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()
                or stat.S_IMODE(out.parent.stat().st_mode) != 0o700
                or not out.is_relative_to(ALLOWED_BASE / "r59/private")):
            raise Hold("OUTPUT_DIR_INVALID")
        pairs, safe = investigate(inventory, p2_rows, private_bytes)
        out.mkdir(mode=0o700)
        for name, data in (
            ("R60_P3_STAGE_PAIRS_PRIVATE.json", pairs),
            ("R60_P3_STAGE_PAIRS_SAFE.json", safe),
        ):
            raw = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
            fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, TypeError, KeyError, UnicodeError):
        fail("STAGE_PAIR_INPUT_OR_VALIDATION_FAILED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
