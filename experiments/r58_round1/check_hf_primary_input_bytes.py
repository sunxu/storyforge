#!/usr/bin/env python3
"""R58 G1: narrowly scoped, Owner-opted read-only HF primary input byte audit.

Reads exactly four immutable-by-contract HF Bucket paths (R46 and R54).
Streams existing private bytes through SHA256 only; no text parsing, file
writes, logs, Job inspection, new Job, or source content output. Hash equality
of current Bucket objects is NOT an attestation of immutable past execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass

BUCKET = "hf://buckets/adradar/storyforge-training"
R46 = f"{BUCKET}/experiments/v02-r46/r46-20261014T070529Z-248172"
R54 = f"{BUCKET}/preflight/v03-r54/gpu/runs/r54-v2-20261021T161818Z-507469/private/release"

@dataclass(frozen=True)
class Pin:
    role: str
    uri: str
    rows: int
    digest: str
    expected_bytes: int | None = None

PINS = (
    Pin("R46_TRAIN", f"{R46}/train.jsonl", 49,
        "a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517", 391988),
    Pin("R46_VALIDATION", f"{R46}/validation.jsonl", 15,
        "cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c", 151854),
    Pin("R54_TRAIN", f"{R54}/train.jsonl", 31,
        "d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7"),
    Pin("R54_VALIDATION", f"{R54}/validation.jsonl", 9,
        "b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d"),
)
SCHEMA = "r58_g1_hf_primary_input_byte_audit_safe_v1"
MAX_FILE_BYTES = 6_000_000
CHUNK = 1024 * 1024

class Hold(Exception):
    pass


def hash_existing_object(file) -> tuple[str, int, int]:
    """Hash bytes from an open binary stream; never decode or store content."""
    h = hashlib.sha256()
    total = 0
    n_newline = 0
    last = b""
    while True:
        chunk = file.read(CHUNK)
        if type(chunk) is not bytes:
            raise Hold("nonbinary HF file")
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_BYTES:
            raise Hold("HF file too large")
        n_newline += chunk.count(b"\n")
        last = chunk[-1:]
        h.update(chunk)
    if total == 0:
        raise Hold("empty HF file")
    return h.hexdigest(), total, n_newline + int(last != b"\n")


def read_and_verify(fs, pins=None) -> dict:
    pins = PINS if pins is None else pins
    if len(pins) != 4 or len({p.role for p in pins}) != 4 or len({p.uri for p in pins}) != 4:
        raise Hold("frozen source pins invalid")
    results = []
    for pin in pins:
        # Only explicit code-owned targets. fs.open is read-only and does not
        # submit HF Jobs or download a file to disk.
        with fs.open(pin.uri, "rb") as file:
            digest, size, rows = hash_existing_object(file)
        if digest != pin.digest or rows != pin.rows:
            raise Hold("remote file hash or row count differs from frozen contract")
        if pin.expected_bytes is not None and size != pin.expected_bytes:
            raise Hold("remote byte length differs")
        results.append(pin)
    if {x.role for x in results} != {"R46_TRAIN", "R46_VALIDATION", "R54_TRAIN", "R54_VALIDATION"}:
        raise Hold("unexpected inputs")
    return {
        "schema": SCHEMA,
        "status": "R58_G1_R46_R54_CURRENT_REMOTE_INPUT_BYTES_MATCH_GITHUB_PINS__HISTORY_AND_OTHER_HOLD",
        "owner_opt_in_private_bucket_byte_read": True,
        "hf_bucket_objects_read": len(results),
        "r46_original_run_compiled_train_validation_bytes_verified": True,
        "r54_original_run_staged_release_train_validation_bytes_verified": True,
        "r46_split_rows_verified": 64,
        "r54_split_rows_verified": 40,
        "known_primary_split_placements_verified_here": 104,
        "current_bucket_equality_proves_historical_job_read_these_bytes": False,
        "historical_bucket_object_immutability_proven": False,
        "r50_protected_content_absence_proven": False,
        "r50_text_decoded_or_inspected": False,
        "source_bytes_or_remote_uris_exported": False,
        "private_world_uuids_exported": False,
        "new_job_started": False,
        "other_hf_jobs_reviewed": False,
        "all_actual_sft_runs_and_input_sources_proven_complete": False,
        "source_registry_complete": False,
        "g1_clearance": "HOLD",
        "train_admitted": 0,
        "validation_admitted": 0,
        "teacher_admitted": 0,
        "expansion_allowed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-read-only-private-primary-input-bytes", action="store_true")
    args = parser.parse_args(argv)
    if not args.allow_read_only_private_primary_input_bytes:
        print("R58_G1_PRIMARY_INPUT_BYTES: HOLD (explicit Owner opt-in required)", file=sys.stderr)
        return 42
    try:
        from huggingface_hub import HfFileSystem
        result = read_and_verify(HfFileSystem())
    except Exception:
        # Never print exception text: providers can embed tokens/paths in errors.
        print("R58_G1_PRIMARY_INPUT_BYTES: HOLD (missing/changed/unsafe remote source)", file=sys.stderr)
        return 42
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
