"""Owner-only SAFE production-era preflight for two recovered R60 case histories.

This checks only timestamps in the immutable read-only recovered private file.
It cannot certify exact production build, original System, provider request,
runtime rollout, prompt revision or history window. No DB or GPU access.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import r60_real_private_batch as private

SCHEMA = "storyforge_r60_roleplay_request_era_safe_v1"
INPUT_SCHEMA = "storyforge_r60_qd20_common2_supabase_recovery_private_v1"
INPUT_NAME = "R60_QD20_COMMON2_SUPABASE_RECOVERY_PRIVATE.json"
# From RolePlay's audited 2026-11-10 deployment document:
RELEASE = datetime.fromisoformat("2026-11-10T10:52:02.950+08:00")
MAX_BYTES = 8_000_000


class Hold(ValueError):
    pass


def assess(data: dict) -> dict:
    if (not isinstance(data, dict)
            or data.get("schema") != INPUT_SCHEMA
            or data.get("status") !=
                "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT"
            or data.get("train_admitted") != 0
            or not isinstance(data.get("cases"), list)
            or len(data["cases"]) != 2):
        raise Hold("RECOVERY_MANIFEST_HOLD")
    earlier = later = 0
    history_counts = []
    for case in data["cases"]:
        if (not isinstance(case, dict)
                or case.get("last_three_exact_source_match") is not True
                or case.get("actual_sent_prompt_verified") is not False
                or case.get("historical_system_verified") is not False
                or case.get("historical_world_components_verified") is not False
                or case.get("r50_full_exclusion_verified") is not False):
            raise Hold("RECOVERY_EVIDENCE_FLAGS_HOLD")
        count = case.get("message_count_before_target")
        history = case.get("history_messages")
        if (type(count) is not int or count < 3 or count > 500
                or not isinstance(history, list) or len(history) != count):
            raise Hold("RECOVERY_HISTORY_COUNT_HOLD")
        raw = case.get("target_created_at")
        try:
            dt = datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            raise Hold("TARGET_TIMESTAMP_HOLD") from None
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise Hold("TARGET_TIMESTAMP_TIMEZONE_HOLD")
        if dt.astimezone(timezone.utc) < RELEASE.astimezone(timezone.utc):
            earlier += 1
        else:
            later += 1
        history_counts.append(count)
    return {
        "schema": SCHEMA,
        "status": "ROLEPLAY_TARGET_ERA_CLASSIFIED__HISTORICAL_REQUEST_UNVERIFIED",
        "candidate_count": 2,
        "history_message_count_by_case": sorted(history_counts),
        "before_20261110_release_count": earlier,
        "at_or_after_20261110_release_count": later,
        "release_commit": "118090a637356686701fd4a2825f3d75f30c031f",
        "exact_target_build_verified": False,
        "actual_sent_prompt_verified": False,
        "production_code_current_state_only": True,
        "historical_runtime_v2_data_verified": False,
        "r50_complete_exclusion_verified": False,
        "quality_v1_admitted": 0,
        "train_admitted": 0,
        "database_accessed": False,
        "database_modified": False,
        "model_inference_calls": 0,
        "gpu_job_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recovery-dir", required=True, type=Path)
    args = p.parse_args()
    try:
        private.private_dir(args.recovery_dir, create=False)
        data = json.loads(private.read_private(
            args.recovery_dir / INPUT_NAME, MAX_BYTES))
        print(json.dumps(assess(data), sort_keys=True))
        return 0
    except Exception as exc:  # noqa: BLE001 — no private text/ID in diagnostics
        reason = str(exc) if isinstance(exc, Hold) else "ROLEPLAY_ERA_INPUT_HOLD"
        print(json.dumps({
            "schema": SCHEMA,
            "status": "ROLEPLAY_TARGET_ERA_HOLD",
            "reason_code": reason,
            "train_admitted": 0, "quality_v1_admitted": 0,
            "database_accessed": False, "database_modified": False,
            "model_inference_calls": 0, "gpu_job_started": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
