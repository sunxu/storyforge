"""Owner-only: materialize 20 blinded quality review packets from frozen sample100.

No model calls or database access. Strictly re-derives sample100 from signed
1000-pool before materializing local private text. No review/admission claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import r60_real1000_calibration_sample_cpu as sample
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_real1000_pilot20_private_v1"
SAFE_SCHEMA = "storyforge_r60_real1000_pilot20_safe_v1"
SAMPLE_QUOTAS = {"300_499": 11, "500_999": 8, "1000_1500": 1}
FILENAME = "R60_PILOT20_REVIEW_PACKETS_PRIVATE.json"
MAX_MANIFEST = 65536


class Hold(ValueError):
    pass


def build(cases: list[dict], digest: str, frozen_sample: dict) -> dict:
    if frozen_sample != sample.select(cases, digest):
        raise Hold("SAMPLE100_BINDING_HOLD")
    selections = []
    for entry in frozen_sample["cases"]:
        pos = entry["position"]
        category = entry["target_char_bin"]
        rank = hashlib.sha256(
            b"r60-pilot20-v1\x00" + digest.encode("ascii")
            + b"\x00" + str(pos).encode("ascii")
        ).hexdigest()
        selections.append((rank, pos, category))
    chosen = []
    for category, needed in SAMPLE_QUOTAS.items():
        subset = sorted(x for x in selections if x[2] == category)
        if len(subset) < needed:
            raise Hold("PILOT20_QUOTA_HOLD")
        chosen.extend(subset[:needed])
    chosen.sort(key=lambda row: row[1])
    packets = []
    for _, pos, category in chosen:
        case = cases[pos - 1]
        packets.append({
            "pilot_position": len(packets) + 1,
            "sample100_position": pos,
            "target_char_bin": category,
            "history_messages": case["history_messages"],
            "assistant_target": case["target_text"],
            "human_reference_status": "NOT_ADJUDICATED",
            "model_quality_status": "NOT_REVIEWED",
        })
    return {
        "schema": SCHEMA,
        "status": "PILOT20_PACKETS_PRIVATE__NOT_REVIEWED",
        "sample100_binding": "RECOMPUTED_EXACT",
        "packets": packets,
        "rubric": {
            "dimensions": [
                "chinese_prose", "character_consistency", "npc_initiative",
                "player_agency", "rule_fidelity", "narrative_continuity",
            ],
            "severe_flags": [
                "serious_player_agency", "hard_fact_or_ban", "safety_exclusion",
            ],
            "possible_decisions": ["PASS", "HOLD", "REJECT"],
            "history_scope": "ONLY_3_PRIOR_MESSAGES_NO_ACTUAL_SYSTEM",
        },
        "quality_review_performed": False,
        "train_admitted": 0,
    }


def safe_report(value: dict) -> dict:
    distribution = Counter(x["target_char_bin"] for x in value["packets"])
    return {
        "schema": SAFE_SCHEMA,
        "status": "PILOT20_REVIEW_PACKETS_READY__NO_REVIEWS",
        "cases_prepared": 20,
        "sample100_verified": True,
        "target_char_bins": {k: distribution[k] for k in SAMPLE_QUOTAS},
        "quality_review_performed": False,
        "quality_pass": 0,
        "train_admitted": 0,
        "database_accessed": False,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expand-dir", type=Path, required=True)
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise Hold("OUTPUT_EXISTS_HOLD")
        cases, digest = quality.frozen_pool(args.expand_dir)
        manifest_file = args.sample_dir / sample.FILENAME
        manifest = json.loads(private.read_private(manifest_file, MAX_MANIFEST))
        result = build(cases, digest, manifest)
        private.private_dir(args.output_dir, create=True)
        data = (json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n").encode()
        private.write_new(args.output_dir / FILENAME, data)
        print(json.dumps(safe_report(result), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - redact all private exception details
        print(json.dumps({
            "schema": SAFE_SCHEMA, "status": "PILOT20_PACKETS_HOLD",
            "quality_pass": 0, "train_admitted": 0,
            "database_accessed": False, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
