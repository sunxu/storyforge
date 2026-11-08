"""Owner-Mac P0 freeze runner for Gold72 20/20 and R60 Severe10.

This command is local-only and fail-closed. It reads existing Owner-private
evidence, replays the Gold72 A/B2 and Owner-resolution validators, checks the
existing Pilot10 aggregate SAFE plus its local C execution receipts, performs
exact cross-set fingerprint comparison, and create-only writes three private
manifests/receipts plus one aggregate SAFE. It never calls a model, network,
database, HF job, GPU, or SFT runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import traceback
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SAFE_SCHEMA = "storyforge_r60_calibration_inventory_safe_v1"
GOLD_MANIFEST_SCHEMA = "storyforge_r60_gold72_calibration_manifest_private_v1"
SEVERE_MANIFEST_SCHEMA = "storyforge_r60_severe10_calibration_manifest_private_v1"
DEDUP_SCHEMA = "storyforge_r60_calibration_crossset_dedup_private_v1"

GOLD_SPLIT_QUOTAS = {
    "EXPLICIT_HOLD__B2_PASS": 15,
    "EXPLICIT_HOLD__B2_REJECT": 2,
    "CASE_LEVEL_SCORED_PASS__B2_REJECT": 1,
    "CASE_LEVEL_SCORED_PASS__B2_HOLD": 2,
}
GOLD_STRATA = {
    "EXPLICIT_HOLD__B2_PASS": 30,
    "EXPLICIT_HOLD__B2_REJECT": 3,
    "CASE_LEVEL_SCORED_PASS__B2_REJECT": 2,
    "CASE_LEVEL_SCORED_PASS__B2_HOLD": 5,
}
EXPECTED_GOLD_OWNER = {"PASS": 30, "HOLD": 4, "REJECT": 6}
EXPECTED_GOLD_C = {"PASS": 38, "HOLD": 1, "REJECT": 1}
EXPECTED_PILOT10_C = {
    "hard_rule": {"NOT_SUPPORTED": 10},
    "player_agency": {"NOT_SUPPORTED": 7, "SUPPORTED": 3},
    "safety": {"INSUFFICIENT_CONTEXT": 4, "NOT_SUPPORTED": 1, "SUPPORTED": 5},
}
HEX = set("0123456789abcdef")

CURRENT_PHASE = "startup"


def _set_phase(value: str) -> None:
    global CURRENT_PHASE
    CURRENT_PHASE = value


def _safe_diagnostic(exc: BaseException) -> dict[str, Any]:
    frames = traceback.extract_tb(exc.__traceback__)
    local_frames = [
        frame for frame in frames
        if Path(frame.filename).name == "r60_calibration_p0_freeze.py"
    ]
    diagnostic: dict[str, Any] = {
        "phase": CURRENT_PHASE,
        "exception_type": type(exc).__name__,
        "source_line": local_frames[-1].lineno if local_frames else None,
    }
    if isinstance(exc, OSError):
        diagnostic["errno"] = exc.errno
    message = str(exc)
    if isinstance(exc, FreezeHold):
        diagnostic["validator_reason_code"] = message
    elif (
        type(exc).__name__ in {"OwnerResolutionHold", "CalibrationHold", "AuditHold"}
        and re.fullmatch(r"[A-Z][A-Z0-9_]{1,95}", message)
    ):
        diagnostic["validator_reason_code"] = (
            f"{type(exc).__name__}:{message}"
        )
    return diagnostic

GOLD = {
    "staged": "r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_PRIVATE.jsonl",
    "staging_safe": "r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_SAFE.json",
    "owner_stage": "r59/private/quality-v1/owner-autolink-suffix72-20261104-v1/OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl",
    "a_v3": "r58/private/quality-v1/reviewer-a-v3-normalization-20261103/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED.json",
    "b2_dir": "r59/private/reviewer-b2-runs/gold72-b2-20261106-v1",
    "crosswalk_safe": "r59/private/reviewer-b2-runs/gold72-b2-20261106-v1/R60_GOLD72_REVIEWER_A_B2_CROSSWALK_SAFE.json",
    "b2_safe": "r59/private/reviewer-b2-runs/gold72-b2-20261106-v1/R60_GOLD72_REVIEWER_B2_AUDIT_SAFE.json",
    "c_dir": "r59/private/reviewer-c-runs/gold72-c-20261106-v1",
}
PILOT = {
    "pairwise_safe": "r60/private/hf-pilot10-owner-audit-20261108/R60_OWNER_PAIRWISE_PILOT10_SAFE.json",
    "a_dir": "r60/private/hf-pilot10-owner-audit-20261108/A",
    "b_dir": "r60/private/hf-pilot10-owner-audit-20261108/B",
    "c_dir": "r60/private/hf-pilot10-c-blind-20261108",
    "stage_owner": "r60/private/r60-hf-quality-first-1000/owner",
}


class FreezeHold(ValueError):
    """Stable non-sensitive failure reason."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise FreezeHold("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _json(raw: bytes, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError):
        raise FreezeHold(reason) from None
    if not isinstance(value, dict):
        raise FreezeHold(reason)
    return value


def _jsonl(raw: bytes, reason: str) -> list[dict[str, Any]]:
    try:
        rows = [
            json.loads(line, object_pairs_hook=_pairs)
            for line in raw.decode("utf-8").splitlines()
            if line.strip()
        ]
    except (UnicodeError, json.JSONDecodeError):
        raise FreezeHold(reason) from None
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise FreezeHold(reason)
    return rows


def _is_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in HEX for ch in value)
    )


def _read_private(
    root: Path, relative: str, repo_root: Path, limit: int = 160 * 1024 * 1024
) -> bytes:
    path = root / relative
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise FreezeHold("PRIVATE_INPUT_PATH_INVALID")
    try:
        resolved = path.resolve(strict=True)
        info = path.lstat()
    except OSError:
        raise FreezeHold("PRIVATE_INPUT_MISSING") from None
    if resolved == repo_root or repo_root in resolved.parents:
        raise FreezeHold("PRIVATE_INPUT_INSIDE_REPOSITORY")
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
        raise FreezeHold("PRIVATE_INPUT_NOT_REGULAR_OR_SIZE_INVALID")
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
        raise FreezeHold("PRIVATE_INPUT_FILE_PERMISSIONS_INVALID")
    if stat.S_IMODE(path.parent.stat().st_mode) != 0o700:
        raise FreezeHold("PRIVATE_INPUT_PARENT_PERMISSIONS_INVALID")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise FreezeHold("PRIVATE_INPUT_CHANGED_DURING_OPEN")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
    except OSError:
        raise FreezeHold("PRIVATE_INPUT_READ_FAILED") from None
    if (
        not 0 < len(raw) <= limit
        or (after.st_size, after.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns)
    ):
        raise FreezeHold("PRIVATE_INPUT_CHANGED_DURING_READ")
    return raw


def _input(
    root: Path, repo_root: Path, key: str, relative: str, limit: int = 160 * 1024 * 1024
) -> bytes:
    return _read_private(root, relative, repo_root, limit)


def _unique(rows: list[dict[str, Any]], key: str, reason: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise FreezeHold(reason)
        result[value] = row
    return result


def stratify_gold72(rows: list[dict[str, Any]]) -> tuple[list[dict], list[dict], dict]:
    """Deterministically allocate each disagreement stratum by target SHA."""
    if len(rows) != 40:
        raise FreezeHold("GOLD72_CASE_COUNT_INVALID")
    by_stratum: dict[str, list[dict]] = {}
    for row in rows:
        stratum = row.get("disagreement_type")
        digest = row.get("target_sha256")
        story = row.get("original_story_uuid")
        if (
            stratum not in GOLD_SPLIT_QUOTAS
            or not _is_sha(digest)
            or not isinstance(story, str)
            or not story
        ):
            raise FreezeHold("GOLD72_SPLIT_ROW_INVALID")
        by_stratum.setdefault(stratum, []).append(dict(row))
    if {key: len(value) for key, value in by_stratum.items()} != GOLD_STRATA:
        raise FreezeHold("GOLD72_STRATUM_DISTRIBUTION_INVALID")

    development: list[dict] = []
    locked: list[dict] = []
    stratum_counts: dict[str, dict[str, int]] = {}
    for stratum in sorted(GOLD_SPLIT_QUOTAS):
        cohort = sorted(by_stratum[stratum], key=lambda item: item["target_sha256"])
        split_at = GOLD_SPLIT_QUOTAS[stratum]
        for index, row in enumerate(cohort):
            row["split"] = "development" if index < split_at else "locked_regression"
            row["stratum_rank"] = index + 1
            (development if index < split_at else locked).append(row)
        stratum_counts[stratum] = {
            "development": split_at,
            "locked_regression": len(cohort) - split_at,
        }
    development.sort(key=lambda item: (item["disagreement_type"], item["target_sha256"]))
    locked.sort(key=lambda item: (item["disagreement_type"], item["target_sha256"]))
    if len(development) != 20 or len(locked) != 20:
        raise FreezeHold("GOLD72_SPLIT_TOTAL_INVALID")
    dev_stories = {row["original_story_uuid"] for row in development}
    lock_stories = {row["original_story_uuid"] for row in locked}
    summary = {
        "stratum_counts": stratum_counts,
        "development_story_count": len(dev_stories),
        "locked_regression_story_count": len(lock_stories),
        "shared_story_count": len(dev_stories & lock_stories),
        "story_disjoint": dev_stories.isdisjoint(lock_stories),
    }
    if summary != {
        "stratum_counts": stratum_counts,
        "development_story_count": 5,
        "locked_regression_story_count": 6,
        "shared_story_count": 5,
        "story_disjoint": False,
    }:
        raise FreezeHold("GOLD72_STORY_SPLIT_EXPECTATION_CHANGED")
    return development, locked, summary


def case_fingerprints(messages: list[dict], target_text: str) -> dict[str, str]:
    if not isinstance(messages, list) or not messages:
        raise FreezeHold("CASE_HISTORY_INVALID")
    for message in messages:
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("role"), str)
            or not isinstance(message.get("content"), str)
        ):
            raise FreezeHold("CASE_HISTORY_MESSAGE_INVALID")
    if not isinstance(target_text, str) or not target_text:
        raise FreezeHold("CASE_TARGET_INVALID")
    history = _sha(_canonical(messages))
    target = _sha(target_text.encode("utf-8"))
    full = _sha(_canonical({"messages": messages, "target_text": target_text}))
    return {"history": history, "target": target, "full": full}


def _fingerprint_index(rows: list[dict], kind: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        digest = row[kind]
        if digest in out:
            raise FreezeHold("WITHIN_SET_EXACT_DUPLICATE")
        out[digest] = row["private_case_ref"]
    return out


def compare_crosssets(gold_rows: list[dict], pilot_rows: list[dict]) -> dict:
    gold_indices = {
        kind: _fingerprint_index(gold_rows, kind) for kind in ("history", "target", "full")
    }
    pilot_indices = {
        kind: _fingerprint_index(pilot_rows, kind) for kind in ("history", "target", "full")
    }
    intersections = {}
    overlap_pairs = []
    for kind in ("history", "target", "full"):
        common = sorted(set(gold_indices[kind]) & set(pilot_indices[kind]))
        intersections[kind] = len(common)
        if kind == "full":
            overlap_pairs = [
                {
                    "gold_private_case_ref": gold_indices[kind][digest],
                    "pilot_private_case_ref": pilot_indices[kind][digest],
                    "fingerprint_sha256": digest,
                }
                for digest in common
            ]
    return {
        "schema": DEDUP_SCHEMA,
        "status": (
            "CROSSSET_EXACT_DEDUP_PASS"
            if not any(intersections.values())
            else "CROSSSET_EXACT_OVERLAP_HOLD"
        ),
        "gold_case_count": len(gold_rows),
        "pilot_case_count": len(pilot_rows),
        "within_gold_unique": len(gold_rows),
        "within_pilot_unique": len(pilot_rows),
        "exact_history_overlap_count": intersections["history"],
        "exact_target_overlap_count": intersections["target"],
        "exact_full_history_target_overlap_count": intersections["full"],
        "comparison_method": "canonical_json_utf8_sha256_exact_match_only",
        "semantic_near_duplicate_detection": False,
        "overlap_pairs": overlap_pairs,
        "private_values_emitted": False,
    }


def _source_path(name: str, base: str, filename: str) -> str:
    return f"{base}/{filename}"


def _load_gold(
    root: Path, repo_root: Path, raw: dict[str, bytes]
) -> tuple[list[dict], dict, dict]:
    _set_phase("gold72_read_inputs")
    b2 = GOLD["b2_dir"]
    c = GOLD["c_dir"]
    files = {
        "staged": (GOLD["staged"], 64 * 1024 * 1024),
        "staging_safe": (GOLD["staging_safe"], 2 * 1024 * 1024),
        "owner_stage": (GOLD["owner_stage"], 8 * 1024 * 1024),
        "a_v3": (GOLD["a_v3"], 32 * 1024 * 1024),
        "b2_blind": (f"{b2}/R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl", 16 * 1024 * 1024),
        "b2_instructions": (f"{b2}/R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md", 256 * 1024),
        "b2_map": (f"{b2}/R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json", 8 * 1024 * 1024),
        "b2_result": (f"{b2}/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json", 16 * 1024 * 1024),
        "b2_receipt": (f"{b2}/R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_COMPLETED.json", 2 * 1024 * 1024),
        "b2_record": (f"{b2}/R60_GOLD72_REVIEWER_B2_EXECUTION_RECORD_PRIVATE", 32 * 1024 * 1024),
        "b2_safe": (GOLD["b2_safe"], 2 * 1024 * 1024),
        "crosswalk_safe": (GOLD["crosswalk_safe"], 2 * 1024 * 1024),
        "c_blind": (f"{c}/R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl", 32 * 1024 * 1024),
        "c_instructions": (f"{c}/R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md", 256 * 1024),
        "c_map": (f"{c}/R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json", 8 * 1024 * 1024),
        "c_result": (f"{c}/R60_GOLD72_REVIEWER_C_RESULTS.json", 8 * 1024 * 1024),
        "c_results_safe": (f"{c}/R60_GOLD72_REVIEWER_C_RESULTS_ONLY_AUDIT_SAFE.json", 2 * 1024 * 1024),
        "c_package_safe": (f"{c}/R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json", 2 * 1024 * 1024),
        "c_receipt_template": (f"{c}/R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json", 2 * 1024 * 1024),
        "resolution_template": (f"{c}/R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE_TEMPLATE.json", 8 * 1024 * 1024),
        "owner_resolution": (f"{c}/R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE.json", 16 * 1024 * 1024),
        "owner_resolution_safe": (f"{c}/R60_GOLD72_OWNER_RESOLUTION_SAFE.json", 2 * 1024 * 1024),
    }
    for key, (relative, limit) in files.items():
        raw[key] = _input(root, repo_root, key, relative, limit)

    _set_phase("gold72_replay_a_b2_crosswalk")
    # Re-run the existing canonical 72-row A/B2 audit; it is Gold72-specific,
    # not the already-passed R60 1000-row Owner crosswalk.
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))
    from experiments.r58_quality import r60_reviewer_ab2_gold72_crosswalk as ab2
    from storyforge_gold_quality import gold72_owner_resolution

    fresh_crosswalk = ab2.audit(
        raw["staged"], raw["staging_safe"], raw["owner_stage"], raw["a_v3"],
        raw["b2_blind"], raw["b2_instructions"], raw["b2_map"], raw["b2_result"],
        raw["b2_receipt"], raw["b2_record"], raw["b2_safe"],
    )
    stored_crosswalk = _json(raw["crosswalk_safe"], "GOLD_CROSSWALK_SAFE_INVALID")
    if fresh_crosswalk != stored_crosswalk:
        raise FreezeHold("GOLD_A_B2_CROSSWALK_SAFE_STALE")

    _set_phase("gold72_replay_owner_resolution")
    # Re-run the existing Gold72 Owner-resolution validator into an ephemeral
    # private temp directory, then compare its aggregate SAFE byte-for-value.
    temp_dir = Path(tempfile.mkdtemp(prefix="r60-gold72-safe-check-"))
    os.chmod(temp_dir, 0o700)
    try:
        args = SimpleNamespace(
            repo_root=repo_root,
            package_safe=root / f"{c}/R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json",
            receipt_template=root / f"{c}/R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json",
            blind_input=root / f"{c}/R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl",
            instructions=root / f"{c}/R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md",
            owner_map=root / f"{c}/R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json",
            result=root / f"{c}/R60_GOLD72_REVIEWER_C_RESULTS.json",
            results_only_safe=root / f"{c}/R60_GOLD72_REVIEWER_C_RESULTS_ONLY_AUDIT_SAFE.json",
            resolution_template=root / f"{c}/R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE_TEMPLATE.json",
            reviewer_a_v3=root / GOLD["a_v3"],
            b2_results=root / f"{b2}/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json",
            crosswalk_safe=root / GOLD["crosswalk_safe"],
            owner_resolution=root / f"{c}/R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE.json",
            safe_output=temp_dir / "owner-resolution-safe.json",
        )
        gold72_owner_resolution.validate_owner_resolution(args)
        generated_safe = _json(
            (temp_dir / "owner-resolution-safe.json").read_bytes(),
            "GOLD_OWNER_RESOLUTION_REPLAY_INVALID",
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    stored_owner_safe = _json(raw["owner_resolution_safe"], "GOLD_OWNER_SAFE_INVALID")
    if generated_safe != stored_owner_safe:
        raise FreezeHold("GOLD_OWNER_RESOLUTION_SAFE_STALE")
    if stored_owner_safe.get("owner_decisions") != EXPECTED_GOLD_OWNER:
        raise FreezeHold("GOLD_OWNER_DECISION_COUNTS_INVALID")
    if stored_owner_safe.get("reviewer_c_decisions") != EXPECTED_GOLD_C:
        raise FreezeHold("GOLD_C_DECISION_COUNTS_INVALID")
    if (
        stored_owner_safe.get("execution_record_available") is not False
        or stored_owner_safe.get("reviewer_c_independence_verified") is not False
        or stored_owner_safe.get("cryptographic_independence_proven") is not False
    ):
        raise FreezeHold("GOLD_C_INDEPENDENCE_STATUS_CHANGED")

    _set_phase("gold72_bind_c_packets_and_owner_map")
    packets = _jsonl(raw["c_blind"], "GOLD_C_BLIND_PACKETS_INVALID")
    cases = []
    for packet in packets:
        if (
            packet.get("schema") != "r60_gold72_reviewer_c_blind_story_packet_v1"
            or packet.get("reviewer") != "C"
            or not isinstance(packet.get("cases"), list)
        ):
            raise FreezeHold("GOLD_C_BLIND_PACKET_SCHEMA_INVALID")
        cases.extend(packet["cases"])
    if len(cases) != 40:
        raise FreezeHold("GOLD_C_CASE_COUNT_INVALID")

    owner_map = _json(raw["c_map"], "GOLD_C_OWNER_MAP_INVALID")
    resolution = _json(raw["owner_resolution"], "GOLD_OWNER_RESOLUTION_INVALID")
    map_rows = owner_map.get("mapping")
    resolution_rows = resolution.get("cases")
    if (
        owner_map.get("candidate_count") != 40
        or not isinstance(map_rows, list) or len(map_rows) != 40
        or not isinstance(resolution_rows, list) or len(resolution_rows) != 40
    ):
        raise FreezeHold("GOLD_C_OWNER_MAP_OR_RESOLUTION_COUNT_INVALID")
    case_idx = _unique(cases, "blind_case_id", "GOLD_C_BLIND_ID_DUPLICATE")
    map_idx = _unique(map_rows, "blind_case_id", "GOLD_C_OWNER_MAP_ID_DUPLICATE")
    resolution_idx = _unique(
        resolution_rows, "blind_case_id", "GOLD_OWNER_RESOLUTION_ID_DUPLICATE"
    )
    if set(case_idx) != set(map_idx) or set(map_idx) != set(resolution_idx):
        raise FreezeHold("GOLD_C_OWNER_CASE_SET_MISMATCH")

    manifest_rows = []
    for blind_id, owner in map_idx.items():
        case = case_idx[blind_id]
        resolved = resolution_idx[blind_id]
        target = case.get("target_assistant_text")
        digest = _sha(target.encode("utf-8")) if isinstance(target, str) else None
        if (
            digest != case.get("target_sha256")
            or digest != owner.get("target_sha256")
            or owner.get("original_case_id") != resolved.get("original_case_id")
            or owner.get("original_story_uuid") != resolved.get("original_story_uuid")
            or owner.get("disagreement_type") != resolved.get("disagreement_type")
            or owner.get("reviewer_a_decision") != resolved.get("reviewer_a_decision")
            or owner.get("reviewer_b2_decision") != resolved.get("reviewer_b2_decision")
            or resolved.get("owner_signoff") is not True
            or resolved.get("owner_decision") not in {"PASS", "HOLD", "REJECT"}
        ):
            raise FreezeHold("GOLD_CASE_TO_OWNER_RESOLUTION_BINDING_INVALID")
        manifest_rows.append({
            "blind_case_id": blind_id,
            "original_case_id": owner["original_case_id"],
            "original_story_uuid": owner["original_story_uuid"],
            "target_sha256": digest,
            "disagreement_type": owner["disagreement_type"],
            "reviewer_a_decision": owner["reviewer_a_decision"],
            "reviewer_b2_decision": owner["reviewer_b2_decision"],
            "reviewer_c_decision": resolved["reviewer_c_decision"],
            "owner_decision": resolved["owner_decision"],
            "prior_b2_blind_case_id": owner["prior_b2_blind_case_id"],
        })
    if Counter(row["disagreement_type"] for row in manifest_rows) != Counter(GOLD_STRATA):
        raise FreezeHold("GOLD_MANIFEST_STRATA_INVALID")

    development, locked, split_summary = stratify_gold72(manifest_rows)
    source_pins = {
        key: _sha(value) for key, value in sorted(raw.items())
        if key not in {"owner_resolution_safe"}
    }
    source_pins["owner_resolution_safe"] = _sha(raw["owner_resolution_safe"])
    manifest = {
        "schema": GOLD_MANIFEST_SCHEMA,
        "status": "GOLD72_CALIBRATION_MANIFEST_FROZEN",
        "candidate_count": 40,
        "split_policy": "stratify_by_disagreement_type_then_target_sha256_ascending",
        "development_case_count": 20,
        "locked_regression_case_count": 20,
        "story_disjoint": False,
        "split_summary": split_summary,
        "source_pins_sha256": source_pins,
        "reviewer_c_execution_record_available": False,
        "reviewer_c_independence_verified": False,
        "cryptographic_independence_proven": False,
        "owner_decision_counts": EXPECTED_GOLD_OWNER,
        "reviewer_c_decision_counts": EXPECTED_GOLD_C,
        "development_cases": development,
        "locked_regression_cases": locked,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
    }
    gold_fp_rows = []
    for row in cases:
        owner = map_idx[row["blind_case_id"]]
        messages = list(row.get("history", [])) + [
            {"role": "user", "content": row.get("current_user_text", "")}
        ]
        fp = case_fingerprints(messages, row.get("target_assistant_text", ""))
        if fp["target"] != owner["target_sha256"]:
            raise FreezeHold("GOLD_TARGET_FINGERPRINT_MISMATCH")
        gold_fp_rows.append({
            "private_case_ref": row["blind_case_id"],
            **fp,
        })
    return manifest, gold_fp_rows, {
        "crosswalk_cases": fresh_crosswalk["candidate_count"],
        "a_b2_disagreements": fresh_crosswalk["a_b2_semantic_decision_disagreements"],
        "a_b2_agreements": fresh_crosswalk["a_b2_semantic_decision_agreements"],
        "owner_decisions": stored_owner_safe["owner_decisions"],
        "reviewer_c_decisions": stored_owner_safe["reviewer_c_decisions"],
        "source_file_count": len(files),
    }


def _validate_pilot10(
    root: Path, repo_root: Path, raw: dict[str, bytes]
) -> tuple[dict, list[dict], dict]:
    _set_phase("pilot10_read_inputs")
    c_dir = PILOT["c_dir"]
    owner_dir = PILOT["stage_owner"]
    paths = {
        "pairwise_safe": (PILOT["pairwise_safe"], 2 * 1024 * 1024),
        "c_prepare_safe": (f"{c_dir}/C_PREPARE_SAFE.json", 2 * 1024 * 1024),
        "c_safe": (f"{c_dir}/C_CALIBRATION_SAFE.json", 2 * 1024 * 1024),
        "c_packets": (f"{c_dir}/C_BLIND_PACKETS_PRIVATE.jsonl", 8 * 1024 * 1024),
        "c_owner_map": (f"{c_dir}/C_OWNER_MAP_PRIVATE.json", 2 * 1024 * 1024),
        "c_results": (f"{c_dir}/C_RESULTS_PRIVATE.jsonl", 8 * 1024 * 1024),
        "c_exec_receipt": (f"{c_dir}/C_CODEX_EXECUTION_RECEIPT_PRIVATE.json", 2 * 1024 * 1024),
        "stage_manifest": (f"{owner_dir}/stage_manifest.private.json", 2 * 1024 * 1024),
        "owner_crosswalk": (f"{owner_dir}/owner_crosswalk.private.json", 16 * 1024 * 1024),
    }
    for key, (relative, limit) in paths.items():
        raw[key] = _input(root, repo_root, key, relative, limit)

    pairwise = _json(raw["pairwise_safe"], "PILOT10_PAIRWISE_SAFE_INVALID")
    expected_pairwise = {
        "schema": "storyforge_r60_hf_pilot10_owner_pairwise_safe_v1",
        "status": "OWNER_PAIRWISE_AUDIT_COMPLETE__SEMANTIC_HOLD",
        "cases_reviewed_by_slot": {"A": 5, "B": 5},
        "checkpoint_receipt_and_input_sha256_verified": {"A": 5, "B": 5},
        "checkpoint_validation_complete": True,
        "input_hash_and_cross_slot_binding_verified": True,
        "owner_manifest_receipt_verified": True,
        "matched_cases": 0,
        "unique_source_cases_in_pilot": 10,
        "semantic_severity_adjudication_complete": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "private_values_emitted": False,
    }
    if any(pairwise.get(key) != value for key, value in expected_pairwise.items()):
        raise FreezeHold("PILOT10_PAIRWISE_SAFE_INVALID_OR_STALE")

    prepare = _json(raw["c_prepare_safe"], "PILOT10_C_PREPARE_SAFE_INVALID")
    if (
        prepare.get("schema") != "storyforge_r60_pilot10_c_calibration_safe_v1"
        or prepare.get("status") != "C_BLIND_PACKETS_READY__REVIEW_NOT_STARTED"
        or prepare.get("source_manifest_and_checkpoint_integrity_verified") is not True
        or prepare.get("packet_count") != 10
        or prepare.get("unique_source_cases") != 10
        or prepare.get("model_judgments_exposed_in_blind_packet") is not False
        or prepare.get("private_values_emitted") is not False
    ):
        raise FreezeHold("PILOT10_C_PREPARE_SAFE_INVALID")

    c_safe = _json(raw["c_safe"], "PILOT10_C_SAFE_INVALID")
    if (
        c_safe.get("schema") != "storyforge_r60_pilot10_c_calibration_safe_v1"
        or c_safe.get("status") != "C_BLIND_SEMANTIC_RECONCILED__QUALITY_HOLD"
        or c_safe.get("cases_reviewed") != 10
        or c_safe.get("original_case_source_integrity_verified") is not True
        or c_safe.get("c_packet_and_result_binding_verified") is not True
        or c_safe.get("c_verdict_counts") != EXPECTED_PILOT10_C
        or c_safe.get("reviewer_c_execution_verified") is not True
        or c_safe.get("reviewer_c_independence_verified") is not False
        or c_safe.get("semantic_severity_adjudication_complete") is not False
        or c_safe.get("quality_v1_admitted") != 0
        or c_safe.get("training_authorized") is not False
        or c_safe.get("private_values_emitted") is not False
    ):
        raise FreezeHold("PILOT10_C_SAFE_INVALID_OR_STALE")

    _set_phase("pilot10_validate_stage_and_checkpoints")
    stage = _json(raw["stage_manifest"], "PILOT10_STAGE_MANIFEST_INVALID")
    cross = _json(raw["owner_crosswalk"], "PILOT10_OWNER_CROSSWALK_INVALID")
    if (
        stage.get("schema") != "storyforge_hf_quality_dual_stage_private_v1"
        or stage.get("count") != 1000
        or not _is_sha(stage.get("pool_sha256"))
        or not _is_sha(stage.get("receipt_sha256"))
        or stage.get("model_pins") != {
            "A": ["Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137"],
            "B": ["zai-org/GLM-4-32B-0414", "077b5c2f5c43bd3239fd605a0600229e8facbd4a"],
        }
        or cross.get("schema") != "storyforge_hf_quality_dual_stage_private_v1"
        or cross.get("count") != 1000
        or cross.get("pool_sha256") != stage.get("pool_sha256")
        or not isinstance(cross.get("bindings"), dict)
        or set(cross["bindings"]) != {"A", "B"}
        or any(not isinstance(cross["bindings"][slot], list)
               or len(cross["bindings"][slot]) != 1000 for slot in ("A", "B"))
    ):
        raise FreezeHold("PILOT10_STAGE_SOURCE_MANIFEST_INVALID")

    _set_phase("pilot10_validate_c_packets_and_receipts")
    packets = _jsonl(raw["c_packets"], "PILOT10_C_PACKETS_INVALID")
    owner_map = _json(raw["c_owner_map"], "PILOT10_C_OWNER_MAP_INVALID")
    results = _jsonl(raw["c_results"], "PILOT10_C_RESULTS_INVALID")
    execution_receipt = _json(raw["c_exec_receipt"], "PILOT10_C_EXECUTION_RECEIPT_INVALID")
    # Read the ten existing A/B checkpoint records without rerunning their
    # audit. Bind each C source slot/position to the exact recorded checkpoint.
    checkpoint_by_slot_position = {}
    for slot in ("A", "B"):
        for position in range(1, 6):
            relative = (
                f"{PILOT['a_dir'] if slot == 'A' else PILOT['b_dir']}/"
                f"review_{position:04d}.private.json"
            )
            key = f"checkpoint_{slot}_{position:02d}"
            raw[key] = _input(root, repo_root, key, relative, 2 * 1024 * 1024)
            checkpoint = _json(raw[key], "PILOT10_CHECKPOINT_INVALID")
            ordered_source = cross["bindings"][slot][position - 1]
            if (
                checkpoint.get("schema") not in {
                    "storyforge_hf_literary_checkpoint_private_v2",
                    "storyforge_hf_literary_checkpoint_private_v3",
                }
                or checkpoint.get("position") != position
                or checkpoint.get("blind_id") != ordered_source.get("blind_id")
                or checkpoint.get("model") != stage["model_pins"][slot][0]
                or checkpoint.get("revision") != stage["model_pins"][slot][1]
                or checkpoint.get("policy") != "storyforge_hf_literary_visible_history_v1"
                or not _is_sha(checkpoint.get("input_sha256"))
                or not _is_sha(checkpoint.get("receipt_sha256"))
                or not isinstance(checkpoint.get("response"), dict)
            ):
                raise FreezeHold("PILOT10_CHECKPOINT_BINDING_INVALID")
            checkpoint_by_slot_position[(slot, position)] = checkpoint

    for index in range(1, 11):
        raw[f"c_case_{index:02d}_exec"] = _input(
            root, repo_root, f"c_case_{index:02d}_exec",
            f"{c_dir}/C_CASE_{index:02d}_EXEC_PRIVATE.json", 2 * 1024 * 1024
        )
        raw[f"c_case_{index:02d}_result"] = _input(
            root, repo_root, f"c_case_{index:02d}_result",
            f"{c_dir}/C_CASE_{index:02d}_RESULT_PRIVATE.json", 2 * 1024 * 1024
        )

    if (
        len(packets) != 10
        or owner_map.get("schema") != "storyforge_r60_pilot10_c_owner_map_private_v1"
        or owner_map.get("count") != 10
        or owner_map.get("source_stage_count") != 1000
        or owner_map.get("blinded_packet_sha256") != _sha(raw["c_packets"])
        or owner_map.get("receipt_sha256") != hashlib.sha256(
            _canonical({k: v for k, v in owner_map.items() if k != "receipt_sha256"})
        ).hexdigest()
        or not isinstance(owner_map.get("bindings"), list)
        or len(owner_map["bindings"]) != 10
        or len(results) != 10
    ):
        raise FreezeHold("PILOT10_C_PACKET_OR_MAP_BINDING_INVALID")

    packet_idx = _unique(packets, "calibration_id", "PILOT10_C_PACKET_ID_DUPLICATE")
    result_idx = _unique(results, "calibration_id", "PILOT10_C_RESULT_ID_DUPLICATE")
    map_idx = _unique(owner_map["bindings"], "calibration_id", "PILOT10_C_MAP_ID_DUPLICATE")
    if set(packet_idx) != set(map_idx) or set(map_idx) != set(result_idx):
        raise FreezeHold("PILOT10_C_PACKET_MAP_RESULT_SET_MISMATCH")

    from storyforge_gold_quality import hf_pilot_semantic_c as c_module
    from storyforge_gold_quality import hf_pilot_semantic_c_codex as codex_module

    bindings_by_slot_source: dict[tuple[str, int], dict] = {}
    for slot in ("A", "B"):
        for row in cross["bindings"][slot]:
            source_index = row.get("source_index")
            if type(source_index) is not int:
                raise FreezeHold("PILOT10_CROSSWALK_SOURCE_INDEX_INVALID")
            key = (slot, source_index)
            if key in bindings_by_slot_source:
                raise FreezeHold("PILOT10_CROSSWALK_SOURCE_INDEX_DUPLICATE")
            bindings_by_slot_source[key] = row

    manifest_rows = []
    source_keys = set()
    source_indices = set()
    slot_positions = {"A": set(), "B": set()}
    blind_ids = set()
    slot_counts = Counter()
    for calibration_id, binding in map_idx.items():
        slot = binding.get("slot")
        position = binding.get("position")
        source_index = binding.get("source_index")
        if (
            slot not in {"A", "B"}
            or type(position) is not int or not 1 <= position <= 5
            or type(source_index) is not int
        ):
            raise FreezeHold("PILOT10_C_OWNER_BINDING_INVALID")
        source_key = (slot, source_index)
        source = bindings_by_slot_source.get(source_key)
        ordered_source = cross["bindings"][slot][position - 1]
        if (
            source is None
            or source_key in source_keys
            or source_index in source_indices
            or position in slot_positions[slot]
            or binding.get("blind_id") in blind_ids
            or ordered_source.get("source_index") != source_index
            or ordered_source.get("blind_id") != binding.get("blind_id")
            or not isinstance(source.get("case_key"), str)
            or not _is_sha(source.get("history_sha256"))
            or not _is_sha(source.get("target_sha256"))
            or not _is_sha(binding.get("input_sha256"))
        ):
            raise FreezeHold("PILOT10_C_OWNER_SOURCE_CROSSWALK_MISMATCH")
        source_keys.add(source_key)
        source_indices.add(source_index)
        slot_positions[slot].add(position)
        blind_ids.add(binding["blind_id"])
        slot_counts[slot] += 1
        checkpoint = checkpoint_by_slot_position[(slot, position)]
        if (
            checkpoint.get("blind_id") != binding.get("blind_id")
            or checkpoint.get("input_sha256") != binding.get("input_sha256")
        ):
            raise FreezeHold("PILOT10_CHECKPOINT_TO_C_OWNER_MAP_MISMATCH")
        packet = packet_idx[calibration_id]
        result = result_idx[calibration_id]
        if (
            binding.get("packet_sha256") != hashlib.sha256(_canonical(packet)).hexdigest()
            or packet.get("schema") != "storyforge_r60_pilot10_c_blind_packet_private_v1"
            or not isinstance(packet.get("visible_history"), list)
            or not isinstance(packet.get("target_text"), str)
            or result.get("schema") != "storyforge_r60_pilot10_c_review_private_v1"
        ):
            raise FreezeHold("PILOT10_C_PACKET_RESULT_INTEGRITY_INVALID")
        c_module.validate_c_result(result, packet)
        manifest_rows.append({
            "calibration_id": calibration_id,
            "blind_id": binding["blind_id"],
            "slot": slot,
            "position": position,
            "source_index": source_index,
            "source_case_key": source.get("case_key"),
            "source_history_sha256": source.get("history_sha256"),
            "source_target_sha256": source.get("target_sha256"),
            "input_sha256": binding["input_sha256"],
            "packet_sha256": binding["packet_sha256"],
            "c_result_verdicts": {
                key: result["assessments"][key]["verdict"]
                for key in ("player_agency", "hard_rule", "safety")
            },
        })
    if (
        slot_counts != {"A": 5, "B": 5}
        or slot_positions != {"A": {1, 2, 3, 4, 5}, "B": {1, 2, 3, 4, 5}}
        or len(source_keys) != 10
        or len(source_indices) != 10
        or len(blind_ids) != 10
    ):
        raise FreezeHold("PILOT10_C_SLOT_OR_SOURCE_COUNTS_INVALID")

    _set_phase("pilot10_verify_local_codex_receipts")
    # Reuse the existing local Codex receipt validator. It checks all ten
    # per-case receipts/results and the aggregate receipt without re-running
    # the old A/B 1000-row crosswalk or any model.
    if not codex_module.verify_local_execution_receipt(
        root / c_dir, packets, results
    ):
        raise FreezeHold("PILOT10_C_LOCAL_EXECUTION_RECEIPT_MISSING")

    if (
        execution_receipt.get("schema") != "storyforge_r60_pilot10_c_codex_execution_private_v1"
        or execution_receipt.get("status") != "C_CODEX_10_FRESH_EXEC_RETURNED__OWNER_REVIEW_PENDING"
        or execution_receipt.get("case_count") != 10
        or execution_receipt.get("model_identity_independently_verified") is not False
        or execution_receipt.get("external_proof_of_independence_available") is not False
    ):
        raise FreezeHold("PILOT10_C_EXECUTION_ATTESTATION_INVALID")

    manifest_rows.sort(key=lambda row: (row["slot"], row["position"]))
    source_pins = {key: _sha(value) for key, value in sorted(raw.items())}
    manifest = {
        "schema": SEVERE_MANIFEST_SCHEMA,
        "status": "R60_SEVERE10_CALIBRATION_MANIFEST_FROZEN",
        "candidate_count": 10,
        "source_stage_count": 1000,
        "slot_counts": {"A": 5, "B": 5},
        "matched_cases": 0,
        "unique_source_cases": 10,
        "checkpoint_receipts_verified": {"A": 5, "B": 5},
        "c_execution_verified_by_local_receipts": True,
        "c_model_identity_independently_verified": False,
        "c_independence_verified": False,
        "source_pins_sha256": source_pins,
        "cases": manifest_rows,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
    }
    pilot_fp_rows = []
    for calibration_id, packet in packet_idx.items():
        fp = case_fingerprints(packet["visible_history"], packet["target_text"])
        pilot_fp_rows.append({
            "private_case_ref": calibration_id,
            **fp,
        })
    return manifest, pilot_fp_rows, {
        "case_count": 10,
        "slot_counts": {"A": 5, "B": 5},
        "checkpoint_receipts_verified": {"A": 5, "B": 5},
        "matched_cases": 0,
        "unique_source_cases": 10,
        "c_execution_verified": True,
        "c_independence_verified": False,
        "source_file_count": len(paths),
    }


def _output_directory(path: Path, repo_root: Path) -> None:
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise FreezeHold("OUTPUT_PATH_INVALID")
    if path.resolve(strict=False) == repo_root or repo_root in path.resolve(strict=False).parents:
        raise FreezeHold("PRIVATE_OUTPUT_INSIDE_REPOSITORY")
    parent = path.parent
    if not parent.is_dir() or stat.S_IMODE(parent.stat().st_mode) != 0o700:
        raise FreezeHold("OUTPUT_PARENT_NOT_PRIVATE")
    if path.exists():
        if not path.is_dir() or stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise FreezeHold("OUTPUT_DIRECTORY_INVALID")
    else:
        path.mkdir(mode=0o700)
        path.chmod(0o700)
    names = (
        "GOLD72_CALIBRATION_MANIFEST_PRIVATE.json",
        "R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json",
        "CALIBRATION_CROSSSET_DEDUP_PRIVATE.json",
        "CALIBRATION_INVENTORY_SAFE.json",
    )
    if any((path / name).exists() or (path / name).is_symlink() for name in names):
        raise FreezeHold("CREATE_ONLY_OUTPUT_ALREADY_EXISTS")
    if any(item.name not in names for item in path.iterdir()):
        raise FreezeHold("OUTPUT_DIRECTORY_NOT_EMPTY")


def _write_create_only(path: Path, value: dict) -> None:
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def build_inventory_safe(
    gold_summary: dict, pilot_summary: dict, dedup: dict, *, written: bool
) -> dict:
    no_overlap = not any((
        dedup["exact_history_overlap_count"],
        dedup["exact_target_overlap_count"],
        dedup["exact_full_history_target_overlap_count"],
    ))
    status = (
        "CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD"
        if written and no_overlap
        else "CALIBRATION_INVENTORY_PREFLIGHT_PASS__NO_FILES_WRITTEN"
        if not written and no_overlap
        else "CALIBRATION_INVENTORY_FROZEN__P0_HOLD"
        if written
        else "CALIBRATION_INVENTORY_PREFLIGHT_HOLD"
    )
    return {
        "schema": SAFE_SCHEMA,
        "status": status,
        "gold72_source_cases_verified": 40,
        "gold72_a_b2_comparable_cases": 72,
        "gold72_a_b2_disagreements": 40,
        "gold72_a_b2_agreements": 32,
        "gold72_development_cases": 20,
        "gold72_locked_regression_cases": 20,
        "gold72_development_story_count": gold_summary["development_story_count"],
        "gold72_locked_regression_story_count": gold_summary["locked_regression_story_count"],
        "gold72_shared_story_count": gold_summary["shared_story_count"],
        "gold72_story_disjoint": False,
        "gold72_owner_decisions": EXPECTED_GOLD_OWNER,
        "gold72_reviewer_c_decisions": EXPECTED_GOLD_C,
        "gold72_c_execution_record_available": False,
        "gold72_c_independence_verified": False,
        "r60_severe10_source_cases_verified": 10,
        "r60_ab_checkpoint_receipts_verified": {"A": 5, "B": 5},
        "r60_ab_matched_cases": 0,
        "r60_unique_source_cases": 10,
        "r60_c_execution_verified": True,
        "r60_c_independence_verified": False,
        "crossset_exact_history_overlap": dedup["exact_history_overlap_count"],
        "crossset_exact_target_overlap": dedup["exact_target_overlap_count"],
        "crossset_exact_full_history_target_overlap": dedup["exact_full_history_target_overlap_count"],
        "unique_source_cases_across_sets": (
            50 if no_overlap else 50 - dedup["exact_full_history_target_overlap_count"]
        ),
        "semantic_near_duplicate_detection": False,
        "manifest_files_written": 4 if written else 0,
        "private_values_emitted": False,
        "quality_v1_admitted": 0,
        "training_authorized": False,
        "gpu_started": False,
        "r50_accessed": False,
    }


def _run(args: argparse.Namespace) -> tuple[dict, dict, dict, dict]:
    _set_phase("resolve_roots")
    repo_root = args.repo_root.resolve(strict=True)
    root = args.owner_data_root.expanduser().resolve(strict=True)
    if repo_root == root or repo_root in root.parents or root in repo_root.parents:
        raise FreezeHold("REPOSITORY_AND_OWNER_DATA_ROOT_OVERLAP")
    raw: dict[str, bytes] = {}
    _set_phase("gold72_validation")
    gold_manifest, gold_fp_rows, gold_summary = _load_gold(root, repo_root, raw)
    _set_phase("pilot10_validation")
    pilot_manifest, pilot_fp_rows, pilot_summary = _validate_pilot10(root, repo_root, raw)
    _set_phase("crossset_exact_dedup")
    dedup = compare_crosssets(gold_fp_rows, pilot_fp_rows)
    dedup["source_pins_sha256"] = {
        "gold_manifest": _sha(_canonical(gold_manifest)),
        "pilot_manifest": _sha(_canonical(pilot_manifest)),
    }
    dedup["unique_source_cases_across_sets"] = (
        50 if dedup["status"] == "CROSSSET_EXACT_DEDUP_PASS"
        else 50 - dedup["exact_full_history_target_overlap_count"]
    )
    safe = build_inventory_safe(gold_summary, pilot_summary, dedup, written=not args.dry_run)
    return gold_manifest, pilot_manifest, dedup, safe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--owner-data-root", type=Path,
        default=Path.home() / ".local" / "share" / "storyforge",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path.home() / ".local" / "share" / "storyforge" /
        "r60" / "private" / "calibration-freeze-20261109",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    created: list[Path] = []
    output_dir: Path | None = None
    try:
        _set_phase("run_preflight")
        gold, pilot, dedup, safe = _run(args)
        if args.dry_run:
            print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
            return 0 if safe["status"] == "CALIBRATION_INVENTORY_PREFLIGHT_PASS__NO_FILES_WRITTEN" else 42

        _set_phase("prepare_private_output_directory")
        repo_root = args.repo_root.resolve(strict=True)
        owner_root = args.owner_data_root.expanduser().resolve(strict=True)
        output_dir = args.output_dir.expanduser()
        output_resolved = output_dir.resolve(strict=False)
        if output_resolved == owner_root or owner_root not in output_resolved.parents:
            raise FreezeHold("PRIVATE_OUTPUT_OUTSIDE_OWNER_DATA_ROOT")
        _output_directory(output_dir, repo_root)
        outputs = [
            ("GOLD72_CALIBRATION_MANIFEST_PRIVATE.json", gold),
            ("R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json", pilot),
            ("CALIBRATION_CROSSSET_DEDUP_PRIVATE.json", dedup),
            ("CALIBRATION_INVENTORY_SAFE.json", safe),
        ]
        _set_phase("write_private_manifests_and_safe")
        for filename, value in outputs:
            target = output_dir / filename
            _write_create_only(target, value)
            created.append(target)
        for target in created:
            if stat.S_IMODE(target.stat().st_mode) != 0o600:
                raise FreezeHold("OUTPUT_FILE_PERMISSION_POSTCHECK_FAILED")
        print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
        return 0 if safe["status"] == "CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD" else 42
    except (FreezeHold, OSError, ValueError, TypeError, KeyError) as exc:
        for target in reversed(created):
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        reason = str(exc) if isinstance(exc, FreezeHold) else "INPUT_OR_IO_ERROR"
        diagnostic = _safe_diagnostic(exc)
        print(json.dumps({
            "schema": SAFE_SCHEMA,
            "status": "CALIBRATION_INVENTORY_HOLD",
            "reason_code": reason,
            "diagnostic": diagnostic,
            "private_values_emitted": False,
            "quality_v1_admitted": 0,
            "training_authorized": False,
            "gpu_started": False,
            "r50_accessed": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
