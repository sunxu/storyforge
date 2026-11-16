"""Transfer R60 HF CPU336 real collator proof to an exact 293/43 partition.

Only when each final row is byte-for-byte identical (as a multiset) to the
336-row technical packet, and the original HF SAFE receipt is independently
accepted. No claim of new ms-swift execution, formal admission, GPU or model
quality. No data contents, row hashes or source identities in stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_base336_exploratory_release_verify as release
import r60_base_cpu336_hf_packet as packet
import r60_real_private_batch as private

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import r60_base_cpu336_hf_receipt_verify as receipt_verifier  # noqa: E402

SAFE = "storyforge_r60_base336_exploratory_collator_transfer_safe_v1"
PINNED_KEY = "r60-base-cpu336-20261114T165256Z-9e35795990aa"
MAX_DATA = 4_000_000


class Hold(ValueError):
    pass


def _rows(raw: bytes, expected: int) -> Counter:
    lines = raw.splitlines()
    if len(lines) != expected or any(not row for row in lines):
        raise Hold("TECHNICAL_ROW_COUNT_HOLD")
    fingerprints = Counter(hashlib.sha256(row).digest() for row in lines)
    if sum(fingerprints.values()) != expected:
        raise Hold("TECHNICAL_FINGERPRINT_HOLD")
    return fingerprints


def verify(release_dir: Path, technical_dir: Path, receipt: Path) -> dict:
    release_safe = release.verify(release_dir)
    private.private_dir(technical_dir, create=False)
    technical_manifest = json.loads(private.read_private(
        technical_dir / packet.MANIFEST, private.MAX_CAPTURE_BYTES))
    if (type(technical_manifest) is not dict
            or technical_manifest.get("schema") != packet.SCHEMA
            or technical_manifest.get("status") != "TECHNICAL_INPUT_ONLY__ALL_HELD"
            or technical_manifest.get("examples") != 336
            or technical_manifest.get("training_dataset_created") is not False
            or technical_manifest.get("train_admitted") != 0
            or technical_manifest.get("input_contract") !=
            "THREE_PERSISTED_MESSAGES_NO_SYSTEM"):
        raise Hold("TECHNICAL_PACKET_CONTRACT_HOLD")
    source_bytes = private.read_private(technical_dir / packet.DATA, MAX_DATA)
    if hashlib.sha256(source_bytes).hexdigest() != technical_manifest.get("data_sha256"):
        raise Hold("TECHNICAL_PACKET_DIGEST_HOLD")
    result = receipt_verifier.accept(receipt, PINNED_KEY)
    if (result.get("status") != "BASE_CPU336_RECEIPT_ACCEPTED__TRAIN_HOLD"
            or result.get("actual_collator_verified") is not True
            or result.get("verified_cases") != 336):
        raise Hold("ORIGINAL_CPU_RECEIPT_HOLD")
    combined = _rows(source_bytes, 336)
    final = Counter()
    for part, n in (("train", 293), ("validation", 43)):
        data = private.read_private(release_dir / f"{part}.jsonl", MAX_DATA)
        final.update(_rows(data, n))
    if final != combined:
        raise Hold("FINAL_ROWS_NOT_IDENTICAL_TO_AUDITED_336_HOLD")
    return {
        "schema": SAFE,
        "status": "BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_PASS__GPU_HOLD",
        "train_rows": release_safe["train_rows"],
        "validation_rows": release_safe["validation_rows"],
        "source_cpu_audited_rows": 336,
        "source_cpu_receipt_accepted": True,
        "all_final_rows_byte_identical_to_audited_rows": True,
        "actual_final_collator_verified": True,
        "collator_executed_in_this_run": False,
        "input_contract": "THREE_PERSISTED_MESSAGES_NO_SYSTEM",
        "formal_source_admission_verified": False,
        "train_admitted": 0,
        "gpu_stage_prepared": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", required=True, type=Path)
    ap.add_argument("--technical-dir", required=True, type=Path)
    ap.add_argument("--cpu336-receipt", required=True, type=Path)
    args = ap.parse_args()
    try:
        print(json.dumps(verify(
            args.release_dir, args.technical_dir, args.cpu336_receipt),
            sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no private body or traceback
        print(json.dumps({
            "schema": SAFE,
            "status": "BASE336_EXPLORATORY_FINAL_COLLATOR_PROOF_TRANSFER_HOLD",
            "actual_final_collator_verified": False,
            "train_admitted": 0,
            "gpu_stage_prepared": False,
            "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
