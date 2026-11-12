"""Prepare 40 blinded REAL1000 review packets from immutable Wave40 locators.

No model votes, story IDs, original pool positions, or source keys in the
reviewer packet. A separate private crosswalk is held by Owner. New files are
create-only 0600 inside a new 0700 directory. No DB/model/GPU actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import r60_real1000_calibration_sample_cpu as sample
import r60_real1000_pilot20_local_review as pilot
import r60_real1000_quality_wave40_cpu as wave
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_real1000_quality_wave40_packets_safe_v1"
BLIND_SCHEMA = "storyforge_r60_real1000_quality_wave40_blind_private_v1"
MAP_SCHEMA = "storyforge_r60_real1000_quality_wave40_crosswalk_private_v1"
TEMPLATE_SCHEMA = "storyforge_r60_real1000_quality_wave40_decisions_private_v1"
BLIND_NAME = "R60_REAL1000_WAVE40_BLIND_PRIVATE.json"
MAP_NAME = "R60_REAL1000_WAVE40_CROSSWALK_PRIVATE.json"
TEMPLATE_NAME = "R60_REAL1000_WAVE40_DECISIONS_TEMPLATE_PRIVATE.json"
MAX_WAVE_BYTES = 65536
MAX_FILE_BYTES = 8_000_000


class Hold(ValueError):
    pass


def construct(cases: list[dict], digest: str, locators: dict, frozen_sample: dict) -> tuple[dict, dict, dict]:
    # Full recomputation is necessary: hash alone does not verify selected
    # positions were derived under the frozen Sample100 exclusion policy.
    if (locators.get("schema") != wave.SCHEMA
            or locators.get("status") != wave.STATUS
            or locators.get("pool_sha256") != digest
            or locators.get("sample100_frozen_binding") is not True
            or locators.get("excludes_all_sample100_stories") is not True
            or locators.get("quality_review_performed") is not False
            or locators.get("train_admitted") != 0):
        raise Hold("WAVE40_SOURCE_CONTRACT_HOLD")
    if locators != wave.select(cases, digest, frozen_sample):
        raise Hold("WAVE40_SOURCE_RECOMPUTE_HOLD")
    rows = locators.get("cases")
    if not isinstance(rows, list) or len(rows) != 40:
        raise Hold("WAVE40_COUNT_HOLD")
    if len({x.get("position") for x in rows if isinstance(x, dict)}) != 40:
        raise Hold("WAVE40_DUPLICATE_HOLD")
    if not all(
        type(x.get("position")) is int
        and 1 <= x["position"] <= len(cases)
        and set(x) == {"position", "target_char_bin"}
        and wave.sample.bucket(len(cases[x["position"] - 1]["target_text"])) == x["target_char_bin"]
        for x in rows if isinstance(x, dict)
    ) or any(not isinstance(x, dict) for x in rows):
        raise Hold("WAVE40_INVALID_ROW_HOLD")
    # Stable reviewer order independent of original row order/position.
    ordered = sorted(
        rows, key=lambda x: hashlib.sha256(
            b"r60-wave40-review-blind-v1\x00" + digest.encode("ascii")
            + b"\x00" + cases[x["position"] - 1]["case_key"].encode("utf-8")
        ).hexdigest()
    )
    blind_rows = []
    crosswalk_rows = []
    for i, row in enumerate(ordered, 1):
        case = cases[row["position"] - 1]
        history = case["history_messages"]
        if (len(history) != 3 or
                [x.get("role") for x in history] != ["user", "assistant", "user"]):
            raise Hold("WAVE40_THREE_MSG_HOLD")
        blind_rows.append({
            "blind_index": i,
            "history_messages": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in history
            ],
            "assistant_target": case["target_text"],
        })
        crosswalk_rows.append({
            "blind_index": i,
            "source_position": row["position"],
            "target_char_bin": row["target_char_bin"],
        })
    blind = {
        "schema": BLIND_SCHEMA, "status": "WAVE40_BLIND__NO_MODEL_VOTES",
        "history_scope": "ONLY_3_PRIOR_MESSAGES_NO_ACTUAL_SYSTEM",
        "cases": blind_rows, "quality_review_performed": False,
        "train_admitted": 0,
    }
    digest_blind = pilot.sha(pilot.canonical(blind))
    xwalk = {
        "schema": MAP_SCHEMA, "status": "OWNER_ONLY_SOURCE_POSITIONS",
        "pool_sha256": digest, "blind_sha256": digest_blind,
        "cases": crosswalk_rows, "train_admitted": 0,
    }
    template = {
        "schema": TEMPLATE_SCHEMA, "blind_sha256": digest_blind,
        "reviewer_independent_of_prior_model_votes": False,
        "rubric_dimensions": list(private.FLOORS),
        "severe_flag_names": list(private.SEVERE),
        "cases": [{
            "blind_index": i, "decision": "NOT_REVIEWED",
            "scores": {}, "severe_flags": {},
            "quote_source": "", "exact_quote": "", "reason_cn": "",
        } for i in range(1, 41)],
        "train_admitted": 0,
    }
    return blind, xwalk, template


def write_new(folder: Path, name: str, data: dict) -> None:
    raw = pilot.canonical(data)
    if len(raw) > MAX_FILE_BYTES:
        raise Hold("PACKET_FILE_SIZE_HOLD")
    fd = os.open(
        folder / name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    if stat.S_IMODE((folder / name).stat().st_mode) != 0o600:
        raise Hold("FILE_PERMISSION_HOLD")


def run(args: argparse.Namespace) -> dict:
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    private.private_dir(args.wave_dir, create=False)
    raw = private.read_private(args.wave_dir / wave.FILENAME, MAX_WAVE_BYTES)
    locators = json.loads(raw)
    cases, digest = quality.frozen_pool(args.expand_dir)
    private.private_dir(args.sample_dir, create=False)
    frozen_sample = json.loads(private.read_private(
        args.sample_dir / sample.FILENAME, 65_536,
    ))
    blind, xwalk, template = construct(cases, digest, locators, frozen_sample)
    private.private_dir(args.output_dir, create=True)
    write_new(args.output_dir, BLIND_NAME, blind)
    write_new(args.output_dir, MAP_NAME, xwalk)
    write_new(args.output_dir, TEMPLATE_NAME, template)
    return {
        "schema": SCHEMA, "status": "WAVE40_BLIND_PACKETS_READY__REVIEW_NOT_STARTED",
        "cases_prepared": 40, "private_files_created": 3,
        "reviewer_packet_excludes_positions": True,
        "reviewer_packet_excludes_model_votes": True,
        "reviewer_packet_excludes_source_ids": True,
        "history_scope": "ONLY_3_PRIOR_MESSAGES_NO_ACTUAL_SYSTEM",
        "independent_quality_review_performed": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
        "database_accessed": False, "model_inference_calls": 0,
        "gpu_started": False, "private_values_emitted": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--expand-dir", type=Path, required=True)
    p.add_argument("--wave-dir", type=Path, required=True)
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - never echo user text/IDs/paths
        print(json.dumps({
            "schema": SCHEMA, "status": "WAVE40_BLIND_PACKETS_HOLD",
            "train_admitted": 0, "model_inference_calls": 0,
            "gpu_started": False, "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
