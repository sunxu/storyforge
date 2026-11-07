"""R60 experimental-only adapter reusing R59 SFT shape and CPU validators.

Builds an engineering preview from the *already receipt-verified* Stage/P2
intersection, never a training dataset. All provenance/Owner gates stay HOLD.
No reimplementation of the SFT packer, system prompt, tokenizer, or collator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from r59_sft_collator_cpu import validate_preview_row
from r59_sft_shape_preview import build_preview
from r59_staging_receipt import valid_staging_receipt
from r60_p3_stage_pair_probe import (
    ALLOWED_BASE,
    STAGE_SCHEMA,
    STAGE_STATUS,
    Hold,
    contained,
    parse_lines,
    private_bytes,
)

SCHEMA = "storyforge_r60_experimental_shape_adapter_safe_v1"
NOT_ACTUAL_SENT = "RECONSTRUCTED_NOT_ACTUAL_SENT"
GATES = ("E0_SOURCE_AND_RIGHTS", "E1_RECONSTRUCTION", "E2_TARGET_SEMANTICS",
         "E3_PRIVACY_WORLD_PROTECTED_EXPOSURE", "E4_SPLIT_AND_FREEZE",
         "E5_ACTUAL_CPU_COLLATOR", "E6_GPU_OWNER_APPROVAL")


def make_preview(pairs: list[dict], queue: list[dict], loader):
    if len(pairs) != 1 or len(queue) != 28:
        raise Hold("PAIRS_OR_FROZEN_QUEUE_INVALID")
    selected = {}
    for row in queue:
        cid, digest = row.get("case_id"), row.get("target_sha256")
        if (not isinstance(cid, str) or not cid
                or not isinstance(digest, str) or len(digest) != 64
                or cid in selected):
            raise Hold("FROZEN_QUEUE_IDENTITY_INVALID")
        selected[cid] = digest
    pair = pairs[0]
    stage_path, receipt_path = (Path(pair[k]) for k in
                                ("stage_private_path", "receipt_private_path"))
    scope = tuple(ALLOWED_BASE / p for p in (
        "r58/private/quality-v1", "r59/private/quality-v1",
    ))
    if any(not contained(p, ALLOWED_BASE) or
           not any(p.is_relative_to(root) for root in scope)
           for p in (stage_path, receipt_path)):
        raise Hold("STAGE_SCOPE_INVALID")
    stage_bytes = loader(stage_path, 160_000_000)
    receipt_bytes = loader(receipt_path, 2_000_000)
    stage_sha = hashlib.sha256(stage_bytes).hexdigest()
    receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
    if (pair.get("stage_sha256") != stage_sha
            or pair.get("receipt_sha256") != receipt_sha
            or not valid_staging_receipt(json.loads(receipt_bytes), stage_sha)):
        raise Hold("STAGE_RECEIPT_PIN_INVALID")
    staged = parse_lines(stage_bytes, 192)
    seen, ready = set(), {}
    for row in staged:
        cid = row.get("case_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise Hold("STAGE_CASE_ID_INVALID")
        seen.add(cid)
        if row.get("status") != STAGE_STATUS:
            continue
        if row.get("schema") != STAGE_SCHEMA:
            raise Hold("STAGE_SCHEMA_INVALID")
        ready[cid] = row
    if (sorted(ready) != pair.get("staged_case_ids_private")
            or len(ready) != pair.get("staged_status_total")):
        raise Hold("STAGE_READINESS_DRIFT")
    intersection = sorted(set(ready) & set(selected))
    if (len(intersection) != pair.get("staged_intersection_p2")
            or len(intersection) != 3):
        raise Hold("FROZEN_INTERSECTION_DRIFT")
    rows = []
    for cid in intersection:
        if ready[cid].get("target_sha256") != selected[cid]:
            raise Hold("TARGET_PIN_MISMATCH")
        rows.append(ready[cid])
    # Reuse the existing, pinned R27 no-card system validation and message packer.
    preview, result = build_preview(rows)
    if result.get("preview_rows") != len(intersection):
        raise Hold("PREVIEW_COUNT_INVALID")
    for row in preview:
        validate_preview_row(row)  # Existing CPU schema/loss validator; no model imports.

    review = [{
        "case_id": cid,
        "source_target_sha256": ready[cid]["target_sha256"],
        "stage_file_sha256": stage_sha,
        "context_provenance": NOT_ACTUAL_SENT,
        "target_semantics": "NOT_INDEPENDENTLY_REVIEWED",
        "world_component_id": None,
        "train_validation_split": None,
        "gates": {gate: "HOLD_UNREVIEWED" for gate in GATES},
        "quality_v1_admitted": False,
        "training_authorized": False,
    } for cid in intersection]
    safe = {
        "schema": SCHEMA,
        "status": "EXPERIMENTAL_ENGINEERING_PREVIEW_ONLY__ALL_REVIEW_GATES_HOLD",
        "frozen_ab_candidates": 28,
        "verified_stage_intersection": len(intersection),
        "engineering_preview_rows": len(preview),
        "existing_shape_packer_reused": True,
        "existing_cpu_shape_validator_reused": True,
        "context_provenance": NOT_ACTUAL_SENT,
        "owner_review_gates_complete": 0,
        "independent_world_split_verified": False,
        "actual_ms_swift_collator_run": False,
        "experimental_dataset_frozen": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "database_modified": False,
        "r50_accessed": False,
        "private_values_emitted": False,
    }
    return preview, review, safe


def create(path: Path, records, lines: bool):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        if lines:
            for row in records:
                f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        else:
            json.dump(records, f, sort_keys=True, ensure_ascii=False, indent=2)
            f.write("\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage-pairs", required=True, type=Path)
    ap.add_argument("--p2-queue", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args()
    try:
        pairs = json.loads(private_bytes(args.stage_pairs, 2_000_000))
        queue = parse_lines(private_bytes(args.p2_queue, 5_000_000), 28)
        out = args.output_dir
        if (not out.is_absolute() or out.exists() or out.is_symlink()
                or not out.parent.is_dir() or out.parent.is_symlink()
                or stat.S_IMODE(out.parent.stat().st_mode) != 0o700
                or not out.is_relative_to(ALLOWED_BASE / "r59/private")):
            raise Hold("PRIVATE_OUTPUT_DIR_INVALID")
        preview, tasks, safe = make_preview(pairs, queue, private_bytes)
        out.mkdir(mode=0o700)
        try:
            create(out / "R60_EXPERIMENTAL_PREVIEW_PRIVATE.jsonl", preview, True)
            create(out / "R60_EXPERIMENTAL_REVIEW_TASKS_PRIVATE.jsonl", tasks, True)
            create(out / "R60_EXPERIMENTAL_SAFE.json", safe, False)
        except OSError:
            for p in out.iterdir():
                p.unlink()
            out.rmdir()
            raise
        print(json.dumps(safe, sort_keys=True))
        return 0
    except (Hold, OSError, ValueError, KeyError, TypeError, UnicodeError):
        print(json.dumps({
            "schema": SCHEMA, "status": "EXPERIMENTAL_ADAPTER_HOLD",
            "quality_v1_admitted": 0, "training_authorized": False,
            "gpu_started": False, "r50_accessed": False,
            "database_modified": False, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
