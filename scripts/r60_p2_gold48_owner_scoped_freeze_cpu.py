"""Owner-approved Gold48 SCOPED dataset freeze, create-only and CPU-only.

Consumes and independently revalidates the PREEXISTING Owner readiness packet.
Records the Owner's explicit scoped approval, without modifying any source,
regenerating a candidate, enabling model inference or freezing model profiles.
Historical original replies remain separate; freeze stores SHA256 only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from r60_p2_gold48_owner_freeze_packet_cpu import SAFE as READY_SCHEMA
from r60_p2_gold48_owner_freeze_packet_cpu import SCHEMA as PACKET_SCHEMA
from r60_p2_gold48_owner_freeze_packet_cpu import STATUS as READY_STATUS
from r60_p2_gold48_owner_freeze_packet_cpu import (
    Hold,
    canonical,
    make_packet,
    require,
    require_file,
    sha,
)

SCHEMA = "storyforge_r60_gold48_owner_scoped_freeze_private_v1"
SAFE = "storyforge_r60_gold48_owner_scoped_freeze_safe_v1"
STATUS = "GOLD48_FROZEN_SCOPED__GENERATION_PROFILE_PENDING"
SAFE_STATUS = "GOLD48_SCOPED_OWNER_FREEZE_COMPLETE__GENERATION_PROFILE_PENDING"
APPROVAL = (
    "Owner explicitly approves Gold48 scoped freeze of 48 main cases, "
    "42 sensitivity cases excluding 6 marked risk cases; accepts that "
    "historical actual-sent prompts and the full protected-source universe "
    "are unverified. Four-model generation profile is separate; this "
    "approval does not authorize inference or training."
)
PACKET_NAME = "GOLD48_OWNER_FREEZE_PACKET_PRIVATE.json"
READY_NAME = "GOLD48_OWNER_FREEZE_READINESS_SAFE.json"
MANIFEST_NAME = "GOLD48_SCOPED_FROZEN_MANIFEST_PRIVATE.json"
SAFE_NAME = "GOLD48_SCOPED_OWNER_FREEZE_SAFE.json"
RUN_KEY_RE = re.compile(r"r60-gold48-cpu-\d{8}T\d{6}Z-[a-f0-9]{12}\Z")
CASE_ID_RE = re.compile(r"G48-C\d{2}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


def build_freeze(candidate_dir, binding_dir, draft_dir, stage_dir,
                 receipt_dir, packet_dir, run_key, *, approved):
    require(approved is True, "EXPLICIT_OWNER_SCOPED_APPROVAL_REQUIRED_HOLD")
    require(RUN_KEY_RE.fullmatch(run_key) is not None
            and stage_dir.name == run_key, "GOLD48_FREEZE_RUN_KEY_HOLD")

    packet_raw = require_file(packet_dir / PACKET_NAME, max_bytes=2 * 1024 * 1024)
    ready_raw = require_file(packet_dir / READY_NAME, max_bytes=32768)
    original = json.loads(packet_raw)
    ready = json.loads(ready_raw)
    expected, expected_safe = make_packet(
        candidate_dir, binding_dir, draft_dir, stage_dir, receipt_dir, run_key
    )
    require(packet_raw == canonical(expected) + b"\n"
            and ready_raw == canonical(expected_safe) + b"\n",
            "OWNER_READINESS_SOURCE_VERSION_DRIFT_HOLD")
    require(original.get("schema") == PACKET_SCHEMA
            and original.get("status") == READY_STATUS
            and original.get("owner_gold48_freeze") is False
            and original.get("original_reference_to_model_input") is False
            and original.get("input_contract") == "RECONSTRUCTED_EVALUATION_INPUT"
            and ready.get("schema") == READY_SCHEMA
            and ready.get("status") == READY_STATUS
            and ready.get("owner_gold48_freeze") is False
            and ready.get("model_generation_authorized") is False,
            "OWNER_READINESS_NOT_SIGNABLE_HOLD")
    require(original.get("historical_actual_sent_prompt_verified") is False
            and original.get("p2_c_full_protected_universe_verified") is False
            and original.get("prior_provisional_48_exact_identity_verified") is False
            and original.get("evaluation_time_story_card_snapshot") is True
            and original.get("tokenizer_actual_input_verified") is True
            and original.get("generation_parameters_owner_frozen") is False
            and original.get("four_generation_arms_pre_registered") is False,
            "GOLD48_APPROVED_RISK_BOUNDARY_HOLD")
    cases = original.get("cases_PRIVATE")
    require(isinstance(cases, list) and len(cases) == 48,
            "GOLD48_FREEZE_CASE_COUNT_HOLD")
    groups, flagged = Counter(), Counter()
    for index, case in enumerate(cases, start=1):
        require(isinstance(case, dict)
                and case.get("candidate_case_id_PRIVATE") == f"G48-C{index:02d}"
                and CASE_ID_RE.fullmatch(case["candidate_case_id_PRIVATE"])
                and all(SHA_RE.fullmatch(case.get(k, "")) is not None
                        for k in (
                            "reconstructed_messages_sha256_PRIVATE",
                            "history_prefix_sha256_PRIVATE",
                            "original_reference_sha256_PRIVATE",
                        ))
                and case.get("anonymous_group_PRIVATE", "").startswith("ANON-GROUP-")
                and type(case.get("exclude_from_42_sensitivity")) is bool,
                "GOLD48_FREEZE_CASE_SHA_OR_SCOPE_HOLD")
        group = case["anonymous_group_PRIVATE"]
        groups[group] += 1
        flagged[group] += int(case["exclude_from_42_sensitivity"])
    require(len(groups) == 8 and set(groups.values()) == {6}
            and sorted(flagged.values()) == [0] * 7 + [6],
            "GOLD48_FREEZE_SENSITIVITY_SCOPE_HOLD")

    capture = json.loads(require_file(
        candidate_dir / "GOLD48_CAPTURE_SAFE.json", max_bytes=32768
    ))
    session_count = capture.get("session_count")
    require(type(session_count) is int and 1 <= session_count <= 48,
            "GOLD48_FREEZE_SESSION_SCOPE_HOLD")

    require(original.get("case_count") == 48
            and original.get("main_analysis_count") == 48
            and original.get("sensitivity_analysis_count") == 42
            and original.get("excluded_sensitivity_count") == 6
            and original.get("gold_reference_comparison_count") == 48
            and original.get("missing_pretarget_memory_omitted") == 48
            and original.get("verified_pretarget_memory_count") == 0
            and original.get("run_key") == run_key
            and ready.get("stage_manifest_and_cpu_receipt_bound") is True,
            "GOLD48_FREEZE_AGGREGATE_SCOPE_HOLD")

    # No previously created Owner freeze is overwritten, and no model
    # parameters are silently approved. The canonical private packet remains
    # unchanged and its exact bytes are pinned here.
    freeze = {
        "schema": SCHEMA,
        "status": STATUS,
        "owner_approval": {
            "kind": "EXPLICIT_OWNER_APPROVAL_IN_CURRENT_CONVERSATION",
            "scope_statement": APPROVAL,
            "recorded_at_utc": datetime.now(UTC).isoformat(),
        },
        "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "run_key": run_key,
        "main_analysis_count": 48,
        "sensitivity_analysis_count": 42,
        "excluded_sensitivity_count": 6,
        "source_count": 8,
        "session_count": session_count,
        "original_reference_count": 48,
        "readiness_packet_sha256_PRIVATE": sha(packet_raw),
        "readiness_safe_sha256_PRIVATE": sha(ready_raw),
        "reconstructed_draft_sha256_PRIVATE":
            original["local_reconstructed_draft_file_sha256_PRIVATE"],
        "stage_manifest_sha256_PRIVATE":
            original["stage_manifest_file_sha256_PRIVATE"],
        "hf_cpu_receipt_sha256_PRIVATE":
            original["hf_cpu_safe_receipt_file_sha256_PRIVATE"],
        "tokenizer_model": original["tokenizer_model"],
        "tokenizer_revision": original["tokenizer_revision"],
        "source_snapshot_kind": "EVALUATION_TIME_PUBLIC_CARD",
        "historical_actual_sent_prompt_verified": False,
        "full_protected_universe_independence_verified": False,
        "prior_provisional_48_exact_identity_verified": False,
        "historical_memory_pretarget_verified_count": 0,
        "historical_memory_unverified_omitted_count": 48,
        "flagged_six_retained_in_main_analysis": True,
        "flagged_six_excluded_from_sensitivity": True,
        "historical_original_reference_is_blind_fifth_answer_source": True,
        "historical_original_reference_is_not_ground_truth": True,
        "historical_original_reference_never_in_generation_input": True,
        "cases_PRIVATE": cases,
        "owner_gold48_freeze": True,
        "freeze_scope": "SCOPED_RECONSTRUCTED_EVALUATION",
        "model_generation_profile_frozen": False,
        "four_generation_arms_parameters_frozen": False,
        "model_generation_authorized": False,
        "gpu_authorized_by_this_freeze": False,
        "training_authorized_by_this_freeze": False,
        "quality_v1_admitted": False,
        "model_promoted": False,
    }
    safe = {
        "schema": SAFE,
        "status": SAFE_STATUS,
        "owner_gold48_freeze": True,
        "freeze_scope": "SCOPED_RECONSTRUCTED_EVALUATION",
        "case_count": 48,
        "source_count": 8,
        "session_count": session_count,
        "main_analysis_count": 48,
        "sensitivity_analysis_count": 42,
        "excluded_sensitivity_count": 6,
        "original_reference_hashes_frozen": 48,
        "reconstructed_input_hashes_frozen": 48,
        "stage_and_hf_cpu_receipt_frozen_by_sha": True,
        "historical_actual_sent_prompt_verified": False,
        "full_protected_universe_independence_verified": False,
        "memory_pretarget_verified_count": 0,
        "memory_unverified_omitted_count": 48,
        "model_generation_profile_frozen": False,
        "model_generation_authorized": False,
        "gpu_started": False,
        "model_calls": 0,
        "training_authorized_by_this_freeze": False,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    return freeze, safe


def private_create(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(canonical(data) + b"\n")
        output.flush()
        os.fsync(output.fileno())


def run(args):
    require(args.owner_approved_scoped_freeze is True,
            "EXPLICIT_OWNER_SCOPED_APPROVAL_REQUIRED_HOLD")
    root = Path.home() / ".local/share/storyforge/r60/private"
    require(root.is_dir() and not root.is_symlink()
            and stat.S_IMODE(root.stat().st_mode) == 0o700,
            "OWNER_PRIVATE_ROOT_HOLD")
    sources = (args.candidate_dir, args.binding_dir, args.draft_dir,
               args.stage_dir, args.receipt_dir, args.packet_dir)
    require(all(p.parent == root and p.is_dir() and not p.is_symlink()
                and stat.S_IMODE(p.stat().st_mode) == 0o700 for p in sources)
            and args.output_dir.parent == root
            and not args.output_dir.exists()
            and not args.output_dir.is_symlink(),
            "OWNER_FREEZE_PATH_SCOPE_HOLD")
    freeze, safe = build_freeze(
        *sources, args.run_key, approved=args.owner_approved_scoped_freeze
    )
    os.mkdir(args.output_dir, mode=0o700)
    require(stat.S_IMODE(args.output_dir.stat().st_mode) == 0o700,
            "OWNER_FREEZE_OUTPUT_MODE_HOLD")
    private_create(args.output_dir / MANIFEST_NAME, freeze)
    private_create(args.output_dir / SAFE_NAME, safe)
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--binding-dir", type=Path, required=True)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--owner-approved-scoped-freeze", action="store_true")
    args = parser.parse_args()
    try:
        report = run(args)
    except (ValueError, TypeError, OSError, KeyError, IndexError) as exc:
        report = {
            "schema": SAFE,
            "status": "HOLD",
            "reason_code": (str(exc) if type(exc) is Hold
                            else "GOLD48_OWNER_SCOPED_FREEZE_RUNTIME_HOLD"),
            "owner_gold48_freeze": False,
            "model_generation_authorized": False,
            "gpu_started": False,
            "model_calls": 0,
            "database_accessed": False,
            "private_values_emitted": False,
        }
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
