"""Owner-only create-once R60 Base-start CPU336 technical packet (NOT SFT data).

Rechecks frozen V123 crosswalk and R50 known5 quarantine. Writes a private
technical-only input; never promotes or exports training/validation splits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import r60_base_start_cpu336_template_audit as audit
import r60_real1000_candidate_identity_audit as identity
import r60_real1000_r50_known5_quarantine as quarantine
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_base_cpu336_hf_packet_private_v1"
SAFE = "storyforge_r60_base_cpu336_hf_packet_safe_v1"
DATA = "R60_BASE_CPU336_TECHNICAL_NOT_ADMITTED_PRIVATE.jsonl"
MANIFEST = "R60_BASE_CPU336_TECHNICAL_MANIFEST_PRIVATE.json"
MAX_DATA = 4_000_000


class Hold(ValueError):
    pass


def packet(cases: list[dict], frozen: dict) -> tuple[bytes, bytes]:
    rows = audit.prepare(cases, frozen)
    data = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")) + "\n").encode()
        for row in rows
    )
    if not 0 < len(data) < MAX_DATA:
        raise Hold("TECHNICAL_PACKET_SIZE_HOLD")
    manifest = {
        "schema": SCHEMA, "status": "TECHNICAL_INPUT_ONLY__ALL_HELD",
        "examples": len(rows),
        "data_sha256": hashlib.sha256(data).hexdigest(),
        "input_contract": "THREE_PERSISTED_MESSAGES_NO_SYSTEM",
        "source_crosswalk_sha256": frozen["source_crosswalk_sha256"],
        "r50_complete_exclusion_verified": False,
        "model_weights_loaded": False,
        "training_dataset_created": False, "train_admitted": 0,
    }
    m = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return data, m


def run(args: argparse.Namespace) -> dict:
    if (args.output_dir.parent != private.BASE
            or not args.output_dir.name.startswith("r60-base-cpu336-hf-packet-")
            or args.output_dir.exists() or args.output_dir.is_symlink()):
        raise Hold("PACKET_OUTPUT_PATH_HOLD")
    cases, report = identity.verified_cases_report(
        args.old_dir, args.plan_dir, args.v2_dir,
        args.v3_dir, args.audit_dir)
    original = private.read_private(
        args.audit_dir / quarantine.crosswalk.FILENAME,
        quarantine.crosswalk.MAX_REPORT)
    frozen = quarantine.construct(
        cases, report, hashlib.sha256(original).hexdigest())
    saved = json.loads(private.read_private(
        args.quarantine_dir / quarantine.FILENAME,
        quarantine.MAX_PRIVATE_REPORT))
    if saved != frozen:
        raise Hold("QUARANTINE_DRIFT_HOLD")
    data, manifest = packet(cases, saved)
    if args.write:
        private.private_dir(args.output_dir, create=True)
        private.write_new(args.output_dir / DATA, data)
        private.write_new(args.output_dir / MANIFEST, manifest)
    return {
        "schema": SAFE,
        "status": ("BASE_CPU336_TECHNICAL_PACKET_SAVED__TRAIN_HOLD"
                   if args.write else "BASE_CPU336_TECHNICAL_PACKET_PREFLIGHT__NO_FILES"),
        "cases": 336, "input_messages_per_case": 4,
        "system_origin": "NONE_NOT_HISTORICAL",
        "input_bytes": len(data),
        "r50_complete_exclusion_verified": False,
        "training_dataset_created": False,
        "train_admitted": 0, "gpu_started": False,
        "model_requests": 0, "database_modified": False,
        "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old", "plan", "v2", "v3", "audit", "quarantine", "output"):
        parser.add_argument(f"--{name}-dir", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no private text/path/hash leaks
        print(json.dumps({
            "schema": SAFE, "status": "BASE_CPU336_TECHNICAL_PACKET_HOLD",
            "train_admitted": 0, "private_values_emitted": False,
            "gpu_started": False, "model_requests": 0,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    sys.exit(main())
