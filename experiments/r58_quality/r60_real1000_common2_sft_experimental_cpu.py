"""Construct TWO private experimental SFT examples from independently PASS cases.

Only verified persisted history and the exact frozen assistant targets are used.
No fabricated System/world/card, no claim of historical wire-request recovery.
Training admission stays 0 and requires separate R50/tokenizer/collator review.
Outputs are private, create-only 0600; no external connections or GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import r60_real1000_qd20_common_pass_blind_cpu as common
import r60_real1000_qd20_common2_supabase_recovery as recovery
import r60_real_private_batch as private
import r60_real_quality_batch as quality

SCHEMA = "storyforge_r60_common2_sft_experimental_safe_v1"
DATA_NAME = "R60_COMMON2_SFT_EXPERIMENTAL_NOT_ADMITTED_PRIVATE.jsonl"
MANIFEST_NAME = "R60_COMMON2_SFT_EXPERIMENTAL_MANIFEST_PRIVATE.json"
WINDOWS = (7, 11, 23)
MAX_BYTES = 8_000_000


class Hold(ValueError):
    pass


def create(cases: list[dict], blind: dict, decisions: dict, history_manifest: dict,
           window: int) -> tuple[list[dict], dict]:
    if window not in WINDOWS:
        raise Hold("WINDOW_NOT_APPROVED_HOLD")
    try:
        counts = common.validate(blind, decisions)["review_decisions"]
    except Exception as exc:
        raise Hold("INDEPENDENT_REVIEW_HOLD") from exc
    if counts != {"PASS": 2, "HOLD": 0, "REJECT": 0}:
        raise Hold("INDEPENDENT_REVIEW_NOT_2PASS_HOLD")
    if (history_manifest.get("schema") != recovery.PRIVATE_SCHEMA
            or history_manifest.get("status") !=
            "RECOVERED_PERSISTED_HISTORY__NOT_ACTUAL_SENT_PROMPT"
            or history_manifest.get("train_admitted") != 0
            or not isinstance(history_manifest.get("cases"), list)
            or len(history_manifest["cases"]) != 2):
        raise Hold("RECOVERY_CONTRACT_HOLD")
    frozen_by_id = {c["source"]["assistant_message_id"]: c for c in cases}
    if len(frozen_by_id) != 1000:
        raise Hold("FROZEN_IDS_HOLD")
    results, safe = [], []
    used = set()
    for recovered in history_manifest["cases"]:
        key = recovered.get("assistant_message_id")
        if not isinstance(key, str) or key in used or key not in frozen_by_id:
            raise Hold("TARGET_SOURCE_HOLD")
        used.add(key)
        original = frozen_by_id[key]
        if (original["source"]["story_id"] != recovered.get("story_id")
                or original["source"]["session_id"] != recovered.get("session_id")
                or original["source"]["assistant_turn_index"] != recovered.get("target_turn_index")
                or recovered.get("last_three_exact_source_match") is not True
                or recovered.get("actual_sent_prompt_verified") is not False
                or recovered.get("historical_system_verified") is not False
                or recovered.get("historical_world_components_verified") is not False
                or recovered.get("r50_full_exclusion_verified") is not False):
            raise Hold("SOURCE_ATTESTATION_HOLD")
        matches = [b for b in blind["cases"] if
                   b.get("assistant_target") == original["target_text"]
                   and b.get("history_messages") == original["history_messages"]]
        if len(matches) != 1:
            raise Hold("BLIND_EXACT_SOURCE_HOLD")
        full = recovered.get("history_messages")
        if (not isinstance(full, list) or len(full) != recovered.get("message_count_before_target")
                or len(full) < window):
            raise Hold("HISTORY_LENGTH_HOLD")
        if ([(x.get("role"), x.get("content")) for x in full[-3:]]
                != [(x["role"], x["content"]) for x in original["history_messages"]]):
            raise Hold("FROZEN_LAST_THREE_HOLD")
        recent = full[-window:]
        if ([m.get("role") for m in recent] !=
                ["user" if i % 2 == 0 else "assistant" for i in range(window)]):
            raise Hold("HISTORY_ROLE_SEQUENCE_HOLD")
        if (any(not isinstance(m.get("content"), str) or not m["content"]
                for m in recent) or
                not isinstance(original["target_text"], str) or
                not original["target_text"]):
            raise Hold("EMPTY_CONTENT_HOLD")
        # One deliberately minimalist, declared training input: no System.
        messages = [{"role": x["role"], "content": x["content"]} for x in recent]
        messages.append({"role": "assistant", "content": original["target_text"]})
        example = {
            "schema": "storyforge_r60_source_bound_experimental_sft_v1",
            "messages": messages,
            "supervision_scope": "FINAL_ASSISTANT_ONLY",
            "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
            "system_prompt": None,
            "world_card": None,
            "train_admitted": False,
        }
        results.append(example)
        safe.append({
            "source_message_count": len(full),
            "input_message_count": len(messages) - 1,
            "input_character_count": sum(len(m["content"]) for m in messages[:-1]),
            "target_character_count": len(messages[-1]["content"]),
        })
    if len(results) != 2:
        raise Hold("COUNT_HOLD")
    return results, {
        "schema": "storyforge_r60_common2_sft_experimental_manifest_private_v1",
        "status": "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED",
        "examples": 2,
        "window": window,
        "source_binding": safe,
        "source_kind": "PERSISTED_COMPLETED_HISTORY_NOT_ACTUAL_SENT",
        "r50_complete_exclusion_verified": False,
        "tokenizer_verified": False,
        "collator_verified": False,
        "train_admitted": 0,
    }


def private_new(folder: Path, name: str, raw: bytes) -> None:
    if not raw or len(raw) > MAX_BYTES:
        raise Hold("OUTPUT_LIMIT_HOLD")
    fd = os.open(
        folder / name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(fd, "wb") as fp:
        fp.write(raw)
        fp.flush()
        os.fsync(fp.fileno())
    if stat.S_IMODE((folder / name).stat().st_mode) != 0o600:
        raise Hold("FILE_MODE_HOLD")


def run(args: argparse.Namespace) -> dict:
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise Hold("OUTPUT_EXISTS_HOLD")
    cases, _ = quality.frozen_pool(args.expand_dir)
    private.private_dir(args.blind_dir, create=False)
    private.private_dir(args.recovery_dir, create=False)
    blind = json.loads(private.read_private(
        args.blind_dir / common.BLIND_NAME, 200_000,
    ))
    decisions = json.loads(private.read_private(args.decisions, 200_000))
    history = json.loads(private.read_private(
        args.recovery_dir / recovery.FILENAME, MAX_BYTES,
    ))
    examples, manifest = create(cases, blind, decisions, history, args.window)
    payload = b"".join(
        (json.dumps(e, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")) + "\n").encode()
        for e in examples
    )
    manifest["data_sha256"] = hashlib.sha256(payload).hexdigest()
    private.private_dir(args.output_dir, create=True)
    private_new(args.output_dir, DATA_NAME, payload)
    private_new(args.output_dir, MANIFEST_NAME, (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode())
    return {
        "schema": SCHEMA,
        "status": "COMMON2_SFT_EXPERIMENTAL_2_READY__TRAIN_HOLD",
        "cases": 2, "input_window": args.window,
        "input_kind": "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT",
        "system_prompt_fabricated": False,
        "full_r50_exclusion_verified": False,
        "tokenizer_verified": False, "collator_verified": False,
        "train_admitted": 0, "quality_v1_admitted": 0,
        "database_accessed": False, "model_inference_calls": 0,
        "gpu_started": False, "private_values_emitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expand-dir", type=Path, required=True)
    parser.add_argument("--blind-dir", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--recovery-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--window", type=int, choices=WINDOWS, default=11)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - private source/paths must stay private
        print(json.dumps({
            "schema": SCHEMA, "status": "COMMON2_SFT_EXPERIMENTAL_INPUT_HOLD",
            "train_admitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
