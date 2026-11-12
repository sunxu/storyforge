"""Offline verification of existing R45 Train49/Val15 vs R50 source report.

Pins the exact historical v03_r50_private_r45_isolation.py output contract.
Validates mechanical checks only; NO semantic world isolation or final seal.
No private IDs, raw strings, hashes, or paths in stdout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.r60_r50_freeze_status_projection_cpu import read_private_json
except ModuleNotFoundError:
    from r60_r50_freeze_status_projection_cpu import read_private_json

SCHEMA = "storyforge_r60_r45_existing_full_source_receipt_safe_v1"
SOURCE_SCHEMA = "storyforge-r50-private-r45-isolation-v1"
SOURCE_STATUS = "R45_FROZEN_49_15_EXACT_SCREEN_PASS__SEMANTIC_REVIEW_PENDING"


def exact_int(value, wanted: int) -> bool:
    return type(value) is int and value == wanted


def verify(path: Path) -> dict:
    out = {
        "schema": SCHEMA,
        "status": "R45_EXISTING_FULL_SOURCE_RECEIPT_HOLD",
        "reason_code": "UNVERIFIED",
        "r45_original_hashes_verified": False,
        "r45_train_count_verified": False,
        "r45_validation_count_verified": False,
        "r50_source_world_count_verified": False,
        "exact_world_collision_zero": False,
        "exact_long_message_hits_zero": False,
        "all_offset_120_window_hits_zero": False,
        "r45_exact_source_screen_verified": False,
        "r45_semantic_world_isolation_verified": False,
        "final_heldout_seal_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "gpu_started": False,
        "hf_jobs_submitted": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    try:
        r = read_private_json(path)
        if r.get("schema") != SOURCE_SCHEMA or r.get("status") != SOURCE_STATUS:
            raise ValueError("FROZEN_REPORT_CONTRACT_HOLD")
        out["r45_original_hashes_verified"] = r.get("frozen_r45_hashes_verified") is True
        counts = r.get("verified_r45_counts")
        if type(counts) is not dict:
            raise ValueError("R45_SPLITS_SCHEMA_HOLD")
        out["r45_train_count_verified"] = exact_int(counts.get("train"), 49)
        out["r45_validation_count_verified"] = exact_int(counts.get("validation"), 15)
        out["r50_source_world_count_verified"] = exact_int(r.get("new_world_count"), 5)
        out["exact_world_collision_zero"] = exact_int(r.get("exact_world_id_conflicts"), 0)
        out["exact_long_message_hits_zero"] = exact_int(r.get("exact_long_message_hit_count"), 0)
        out["all_offset_120_window_hits_zero"] = exact_int(
            r.get("all_offset_120_codepoint_window_hit_count"), 0)
        if (r.get("short_or_paraphrased_context_review") != "PENDING"
                or r.get("incomplete_or_hidden_world_aliases") != "PENDING"
                or not exact_int(r.get("heldout_cases_sealed"), 0)
                or r.get("raw_private_text_or_ids_emitted") is not False
                or r.get("gpu_executed") is not False
                or r.get("model_promotion") is not False):
            raise ValueError("PENDING_SEMANTIC_OR_SEAL_CONTRACT_HOLD")
        positive = (
            "r45_original_hashes_verified", "r45_train_count_verified",
            "r45_validation_count_verified", "r50_source_world_count_verified",
            "exact_world_collision_zero", "exact_long_message_hits_zero",
            "all_offset_120_window_hits_zero")
        if not all(out[k] for k in positive):
            raise ValueError("R45_EXACT_METRIC_HOLD")
        out["r45_exact_source_screen_verified"] = True
        out.update(status="R45_EXISTING_EXACT_SOURCE_SCREEN_PASS__SEMANTIC_SEAL_HOLD",
                   reason_code="FROZEN_R45_49_15_EXACT_REPORT_VERIFIED")
    except Exception as exc:
        known = {
            "FROZEN_REPORT_CONTRACT_HOLD", "R45_SPLITS_SCHEMA_HOLD",
            "PENDING_SEMANTIC_OR_SEAL_CONTRACT_HOLD", "R45_EXACT_METRIC_HOLD",
        }
        out["reason_code"] = (str(exc) if type(exc) is ValueError and
                              str(exc) in known else "SOURCE_OR_RUNTIME_HOLD")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--r45-report", type=Path, required=True)
    args = p.parse_args()
    out = verify(args.r45_report)
    print(json.dumps(out, sort_keys=True))
    return 0 if out["r45_exact_source_screen_verified"] else 42


if __name__ == "__main__":
    raise SystemExit(main())
