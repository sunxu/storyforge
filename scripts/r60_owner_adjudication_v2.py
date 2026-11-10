"""Prepare Gold72 Development-20 Owner blind adjudication packets (no model calls)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import r60_calibration_p0_freeze as p0
from storyforge_gold_quality import hf_owner_adjudication_v2 as adjudication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--owner-data-root", type=Path,
        default=Path.home() / ".local" / "share" / "storyforge",
    )
    parser.add_argument(
        "--p0-freeze-dir", type=Path, required=True,
        help="Owner-private directory containing the frozen P0 Gold72 manifest.",
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True,
        help="New Owner-private output directory; create-only.",
    )
    parser.add_argument(
        "--write", action="store_true",
        help="Write the six private P2 packet artifacts. Without this flag only dry-run is performed.",
    )
    args = parser.parse_args()
    try:
        owner_root = args.owner_data_root.expanduser().resolve(strict=True)
        source_packet = (
            owner_root / p0.GOLD["c_dir"]
            / "R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl"
        )
        result = adjudication.prepare(
            args.p0_freeze_dir.expanduser()
            / "GOLD72_CALIBRATION_MANIFEST_PRIVATE.json",
            source_packet,
            args.output_dir,
            args.repo_root,
            dry_run=not args.write,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        expected = (
            "P2_OWNER_BLIND_PACKETS_READY__OWNER_REVIEW_NOT_STARTED"
            if args.write
            else "P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN"
        )
        return 0 if result.get("status") == expected else 42
    except (adjudication.AdjudicationHold, OSError, ValueError, TypeError, KeyError) as exc:
        reason = (
            str(exc) if isinstance(exc, adjudication.AdjudicationHold)
            else "INPUT_OR_IO_ERROR"
        )
        print(json.dumps({
            "schema": adjudication.SAFE_SCHEMA,
            "status": "P2_OWNER_ADJUDICATION_PREPARE_HOLD",
            "reason_code": reason,
            "private_values_emitted": False,
            "owner_review_started": False,
            "model_calls": 0,
            "hf_jobs_submitted": 0,
            "gpu_started": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
