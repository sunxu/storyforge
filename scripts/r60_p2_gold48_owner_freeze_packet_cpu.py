"""Create-only, Owner-private Gold48 scoped freeze decision packet.

Reuses the existing candidate, reconstructed-message, HF Stage and SHA gates.
No new historical-source recovery, tokenizer, model call, database access,
HF Job, training or GPU. No Owner signature or scope escalation. The original
answer stays private and separate from model-visible prompt messages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

from r60_p2_gold48_candidate_preflight_cpu import evaluate as candidates_preflight
from r60_p2_gold48_candidate_preflight_cpu import read_0600
from r60_p2_gold48_hf_cpu_stage import (
    INPUT,
    MANIFEST,
    minimally_staged,
    verify as verify_stage,
)
from r60_p2_gold48_token_preflight_cpu import (
    MODEL,
    REVISION,
    load_draft,
)
from storyforge_dataset.hf_runtime import InputManager

SCHEMA = "storyforge_r60_gold48_owner_freeze_packet_private_v1"
SAFE = "storyforge_r60_gold48_owner_freeze_readiness_safe_v1"
RECEIPT_SCHEMA = "storyforge_r60_gold48_hf_cpu_token_receipt_safe_v1"
STATUS = "GOLD48_OWNER_FREEZE_PACKET_READY__AWAITING_SIGNOFF"
RECEIPT_STATUS = "GOLD48_HF_CPU_TOKEN_PREFLIGHT_COMPLETE__NO_FREEZE"
RUN_KEY_PREFIX = "r60-gold48-cpu-"
SOURCE_BINDING_NAME = "GOLD48_SOURCE_COMPONENT_BINDINGS_PRIVATE.json"
DRAFT_NAME = "GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
RECEIPT_NAME = "GOLD48_HF_CPU_TOKEN_SAFE.json"
BUDGETS = ("context_16384_reserve_1536", "context_32768_reserve_2048")


class Hold(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise Hold(code)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require_file(path, *, max_bytes):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
            and stat.S_IMODE(info.st_mode) == 0o600
            and 0 < info.st_size <= max_bytes, "OWNER_INPUT_FILE_MODE_HOLD")
    return InputManager.open_verified(path, max_bytes=max_bytes).read_bytes()


def make_packet(candidate_dir, binding_dir, draft_dir, stage_dir,
                receipt_dir, run_key):
    check = candidates_preflight(candidate_dir)
    require(check["status"] == "GOLD48_PRIVATE_CANDIDATE_PREFLIGHT_PASS__NOT_FROZEN"
            and check["case_count"] == 48
            and check["original_reference_count"] == 48
            and check["sensitivity_count"] == 42,
            "GOLD48_CANDIDATE_SOURCE_HOLD")

    draft_file = draft_dir / DRAFT_NAME
    raw, messages, memories = load_draft(draft_file)
    draft = json.loads(raw)
    require(draft["source_component_binding_sha256_PRIVATE"] ==
            sha(require_file(binding_dir / SOURCE_BINDING_NAME,
                             max_bytes=10 * 1024 * 1024)),
            "GOLD48_SOURCE_COMPONENT_BINDING_DRIFT_HOLD")
    require(memories.get("NO_VERIFIED_PRETARGET_MEMORY") == 48
            and memories.get("VERIFIED_PRETARGET_SESSION_SUMMARY", 0) == 0,
            "GOLD48_MEMORY_SCOPE_CHANGE_HOLD")
    require(draft["evaluation_time_snapshot"] is True
            and draft["historical_actual_sent_verified"] is False
            and draft["memory_absent_not_fabricated"] is True,
            "RECONSTRUCTION_PROVENANCE_SCOPE_HOLD")

    stage_safe = verify_stage(stage_dir, run_key)
    require(stage_safe["status"] == "GOLD48_HF_CPU_STAGE_VERIFIED__NOT_SUBMITTED"
            and stage_safe["files_verified"] == 16,
            "GOLD48_STAGE_SOURCE_BINDING_HOLD")
    stage_manifest = json.loads(require_file(stage_dir / MANIFEST,
                                             max_bytes=32768))
    require(stage_manifest.get("owner_local_original_draft_sha256_PRIVATE") ==
            sha(raw)
            and stage_manifest.get("model") == MODEL
            and stage_manifest.get("model_revision") == REVISION
            and stage_manifest.get("candidate_count") == 48,
            "GOLD48_STAGE_DRAFT_SHA_OR_MODEL_HOLD")
    expected_staged, expected_draft_sha = minimally_staged(draft_file)
    require(expected_draft_sha == sha(raw), "GOLD48_STAGE_RECONSTRUCTION_HOLD")
    expected_stage_bytes = canonical(expected_staged) + b"\n"
    staged_raw = InputManager.open_verified(
        stage_dir / INPUT,
        max_bytes=32 * 1024 * 1024,
        expected_sha256=stage_manifest["files"][INPUT],
    ).read_bytes()
    require(staged_raw == expected_stage_bytes,
            "GOLD48_STAGE_MINIMIZATION_DRIFT_HOLD")
    stage_cases = json.loads(staged_raw)["cases_PRIVATE"]

    receipt_path = receipt_dir / RECEIPT_NAME
    receipt_raw = require_file(receipt_path, max_bytes=32768)
    receipt = json.loads(receipt_raw)
    require(receipt.get("schema") == RECEIPT_SCHEMA
            and receipt.get("status") == RECEIPT_STATUS
            and receipt.get("stage") == "COMPLETE"
            and receipt.get("run_key") == run_key
            and receipt.get("case_count") == 48
            and receipt.get("input_sha256_verified") is True
            and receipt.get("tokenizer_checked") is True
            and receipt.get("model") == MODEL
            and receipt.get("model_revision") == REVISION
            and receipt.get("tokenizer_version") == "5.16.1"
            and receipt.get("owner_gold48_freeze") is False
            and receipt.get("gpu_started") is False
            and receipt.get("model_calls") == 0
            and receipt.get("private_values_emitted") is False,
            "GOLD48_HF_CPU_RECEIPT_CONTRACT_HOLD")
    modes = receipt.get("mode_stats")
    require(isinstance(modes, dict) and set(modes) == {"default", "disabled"},
            "GOLD48_TOKEN_MODES_HOLD")
    for mode in modes.values():
        require(isinstance(mode, dict) and set(mode) == set(BUDGETS),
                "GOLD48_TOKEN_BUDGET_SET_HOLD")
        for key, stats in mode.items():
            context = int(key.split("_")[1])
            require(isinstance(stats, dict)
                    and type(stats.get("over_budget_count")) is int
                    and stats["over_budget_count"] == 0
                    and type(stats.get("max_total_tokens")) is int
                    and 0 < stats["max_total_tokens"] <= context
                    and all(type(stats.get(metric)) is int
                            and 0 < stats[metric] <= context
                            for metric in ("prompt_tokens_min", "prompt_tokens_median",
                                           "prompt_tokens_p95", "prompt_tokens_max")),
                    "GOLD48_TOKEN_BUDGET_NOT_PASS_HOLD")
    require(receipt.get("memory_pretarget_verified_count") == 0
            and receipt.get("memory_unverified_omitted_count") == 48,
            "GOLD48_TOKEN_MEMORY_SCOPE_HOLD")

    locators = read_0600(
        candidate_dir / "GOLD48_CANDIDATE_LOCATORS_PRIVATE.json"
    )["cases_PRIVATE"]
    original = read_0600(
        candidate_dir / "GOLD48_CANDIDATE_ORIGINAL_REFERENCES_PRIVATE.json"
    )["cases_PRIVATE"]
    require(len(messages) == len(locators) == len(original) == len(stage_cases) == 48,
            "GOLD48_OWNER_PACKET_ROW_COUNT_HOLD")
    entries, groups, flags = [], Counter(), Counter()
    for loc, original_ref, dr, staged in zip(
            locators, original, draft["cases_PRIVATE"], stage_cases, strict=True):
        case_id = loc["candidate_case_id_PRIVATE"]
        group = staged["story_id_PRIVATE"]
        require(case_id == dr.get("candidate_case_id_PRIVATE")
                == staged.get("candidate_case_id_PRIVATE")
                == original_ref.get("candidate_case_id_PRIVATE")
                and loc["story_id_PRIVATE"] == dr["story_id_PRIVATE"]
                and loc["prefix_sha256_PRIVATE"] ==
                dr["history_prefix_sha256_PRIVATE"] ==
                staged["history_prefix_sha256_PRIVATE"]
                and dr["reconstructed_messages_sha256_PRIVATE"] ==
                staged["reconstructed_messages_sha256_PRIVATE"]
                and loc["original_reply_sha256_PRIVATE"] ==
                original_ref["original_reply_sha256_PRIVATE"]
                and group.startswith("ANON-GROUP-")
                and staged["source_revision_PRIVATE"] ==
                dr["source_revision_PRIVATE"],
                "GOLD48_OWNER_CASE_CROSSWALK_HOLD")
        flags[group] += bool(loc["exclude_from_42_sensitivity"])
        groups[group] += 1
        entries.append({
            "candidate_case_id_PRIVATE": case_id,
            "anonymous_group_PRIVATE": group,
            "reconstructed_messages_sha256_PRIVATE":
                dr["reconstructed_messages_sha256_PRIVATE"],
            "history_prefix_sha256_PRIVATE": dr["history_prefix_sha256_PRIVATE"],
            "original_reference_sha256_PRIVATE":
                original_ref["original_reply_sha256_PRIVATE"],
            "exclude_from_42_sensitivity": loc["exclude_from_42_sensitivity"],
        })
    require(len(groups) == 8 and set(groups.values()) == {6}
            and sorted(flags.values()) == [0] * 7 + [6],
            "GOLD48_SENSITIVITY_SCOPE_HOLD")
    require(all(staged["reconstructed_messages_PRIVATE"] == prompt
                for staged, prompt in zip(stage_cases, messages, strict=True)),
            "STAGED_PROMPT_EXACT_IDENTITY_HOLD")

    packet = {
        "schema": SCHEMA,
        "status": STATUS,
        "input_contract": "RECONSTRUCTED_EVALUATION_INPUT",
        "case_count": 48,
        "main_analysis_count": 48,
        "sensitivity_analysis_count": 42,
        "excluded_sensitivity_count": 6,
        "gold_reference_comparison_count": 48,
        "run_key": run_key,
        "stage_manifest_file_sha256_PRIVATE": sha(require_file(
            stage_dir / MANIFEST, max_bytes=32768)),
        "local_reconstructed_draft_file_sha256_PRIVATE": sha(raw),
        "hf_cpu_safe_receipt_file_sha256_PRIVATE": sha(receipt_raw),
        "tokenizer_model": MODEL,
        "tokenizer_revision": REVISION,
        "tokenizer_actual_input_verified": True,
        "token_budget_16k_zero_overflow": True,
        "historical_actual_sent_prompt_verified": False,
        "evaluation_time_story_card_snapshot": True,
        "p2_c_full_protected_universe_verified": False,
        "prior_provisional_48_exact_identity_verified": False,
        "missing_pretarget_memory_omitted": 48,
        "scoped_risk_acceptance_requires_owner_confirmation": True,
        "four_generation_arms_pre_registered": False,
        "generation_parameters_owner_frozen": False,
        "original_reference_to_model_input": False,
        "owner_gold48_freeze": False,
        "model_generation_authorized": False,
        "cases_PRIVATE": entries,
    }
    safe = {
        "schema": SAFE,
        "status": STATUS,
        "case_count": 48,
        "source_count": 8,
        "main_analysis_count": 48,
        "sensitivity_analysis_count": 42,
        "excluded_sensitivity_count": 6,
        "verified_original_reference_hash_count": 48,
        "verified_reconstructed_input_sha_count": 48,
        "source_component_binding_verified": True,
        "stage_manifest_and_cpu_receipt_bound": True,
        "cpu_tokenizer_budget_checked": True,
        "historical_actual_sent_prompt_verified": False,
        "full_p2_c_universe_verified": False,
        "owner_gold48_freeze": False,
        "model_generation_authorized": False,
        "gpu_started": False,
        "model_calls": 0,
        "database_accessed": False,
        "private_values_emitted": False,
    }
    return packet, safe


def run(args):
    root = Path.home() / ".local/share/storyforge/r60/private"
    require(root.is_dir() and not root.is_symlink()
            and stat.S_IMODE(root.stat().st_mode) == 0o700,
            "OWNER_PRIVATE_ROOT_HOLD")
    dirs = (args.candidate_dir, args.binding_dir, args.draft_dir,
            args.stage_dir, args.receipt_dir)
    require(all(p.parent == root and p.is_dir() and not p.is_symlink()
                for p in dirs)
            and args.stage_dir.name == args.run_key
            and args.run_key.startswith(RUN_KEY_PREFIX)
            and args.output_dir.parent == root
            and not args.output_dir.exists()
            and not args.output_dir.is_symlink(),
            "OWNER_PACKET_PATH_SCOPE_HOLD")
    packet, safe = make_packet(*dirs, args.run_key)
    os.mkdir(args.output_dir, mode=0o700)
    for name, doc in (
        ("GOLD48_OWNER_FREEZE_PACKET_PRIVATE.json", packet),
        ("GOLD48_OWNER_FREEZE_READINESS_SAFE.json", safe),
    ):
        path = args.output_dir / name
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(doc) + b"\n")
    return safe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--binding-dir", type=Path, required=True)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except (Hold, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        result = {
            "schema": SAFE,
            "status": "HOLD",
            "reason_code": str(exc) if type(exc) is Hold
            else "GOLD48_OWNER_FREEZE_PACKET_RUNTIME_HOLD",
            "owner_gold48_freeze": False,
            "gpu_started": False,
            "private_values_emitted": False,
        }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
