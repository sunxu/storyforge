"""Offline CPU Qwen tokenizer and actual ms-swift collator audit for Common2.

Never download weights or model files; require an already pinned LOCAL
tokenizer snapshot. Never emit private source text, decoded labels, IDs, or
token digests. The internal ms-swift audit emits detailed stdout, captured and
discarded here. The input stays NOT_ADMITTED regardless of audit success.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
from pathlib import Path

import r60_real1000_common2_sft_experimental_cpu as sft
import r60_real_private_batch as private

SCHEMA = "storyforge_r60_common2_sft_cpu_template_audit_safe_v1"
PIN = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
CEILING = 16384
LIMIT = 8_000_000


class Hold(ValueError):
    pass


def validate_payload(records: list[dict], manifest: dict, raw: bytes) -> None:
    if (manifest.get("schema") != "storyforge_r60_common2_sft_experimental_manifest_private_v1"
            or manifest.get("status") != "EXPERIMENTAL_CONTEXT_CONSTRUCTED__NOT_ADMITTED"
            or manifest.get("examples") != 2
            or manifest.get("window") != 11
            or manifest.get("train_admitted") != 0
            or manifest.get("r50_complete_exclusion_verified") is not False
            or manifest.get("data_sha256") != hashlib.sha256(raw).hexdigest()
            or not isinstance(records, list) or len(records) != 2):
        raise Hold("PRIVATE_EXPERIMENT_CONTRACT_HOLD")
    for row in records:
        msgs = row.get("messages")
        if (row.get("schema") != "storyforge_r60_source_bound_experimental_sft_v1"
                or row.get("input_kind") != "SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT"
                or row.get("supervision_scope") != "FINAL_ASSISTANT_ONLY"
                or row.get("system_prompt", "unexpected") is not None
                or row.get("world_card", "unexpected") is not None
                or row.get("train_admitted") is not False
                or not isinstance(msgs, list) or len(msgs) != 12
                or [m.get("role") for m in msgs] !=
                    ["user" if i % 2 == 0 else "assistant" for i in range(11)]
                    + ["assistant"]
                or any(set(m) != {"role", "content"}
                       or not isinstance(m["content"], str) or not m["content"]
                       for m in msgs)):
            raise Hold("EXPERIMENT_MESSAGE_SEQUENCE_HOLD")


def inspect_rows(rows: list[dict], tokenizer, template=None, phase=None) -> dict:
    results = []
    if template is not None and getattr(template.loss_scale, "base_strategy", None) != "last_round":
        raise Hold("SWIFT_LOSS_SCALE_HOLD")
    for number, row in enumerate(rows, 1):
        messages = row["messages"]
        if phase is not None:
            phase("TOKENIZER_ENCODE")
        ids = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=False,
        )
        if (not isinstance(ids, list) or not ids
                or any(type(x) is not int for x in ids)):
            raise Hold("TOKENIZER_OUTPUT_HOLD")
        n = len(ids)
        if n > CEILING:
            raise Hold("TOKEN_BUDGET_HOLD")
        result = {"input_tokens_with_target": n}
        if template is not None:
            if phase is not None:
                phase("SWIFT_COLLATOR_AUDIT")
            # Use the preexisting, audited R18 strict last_round verifier; its
            # optional decoded debug output MUST NEVER escape this process.
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
            import hf_label_mask_audit as audit
            swift_row = {"messages": [
                {**message, "loss": i == len(messages) - 1}
                for i, message in enumerate(messages)
            ]}
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                audit.audit_row(template, swift_row, number)
                encoded = template.encode(swift_row)
                collator = getattr(template, "data_collator", None)
                if not callable(collator):
                    raise Hold("REAL_COLLATOR_UNAVAILABLE_HOLD")
                batch = collator([encoded])
            unbatched_ids = audit._list_ints(encoded["input_ids"])
            unbatched_labels = audit._list_ints(encoded["labels"])
            batched_ids = audit._list_ints(batch["input_ids"])
            batched_labels = audit._list_ints(batch["labels"])
            if (not unbatched_ids or len(unbatched_ids) != len(unbatched_labels)
                    or len(unbatched_ids) > CEILING
                    or batched_ids[:len(unbatched_ids)] != unbatched_ids
                    or batched_labels[:len(unbatched_labels)] != unbatched_labels
                    or len(batched_ids) != len(batched_labels)
                    or any(x != -100 for x in batched_labels[len(unbatched_labels):])):
                raise Hold("COLLATOR_CONSISTENCY_HOLD")
            result["actual_collator_tokens"] = len(unbatched_ids)
            result["supervised_tokens"] = sum(x != -100 for x in unbatched_labels)
            result["label_mask"] = "ACTUAL_MS_SWIFT_LAST_ROUND_AUDIT_PASS"
        results.append(result)
    return {
        "schema": SCHEMA,
        "status": ("COMMON2_CPU_TOKENIZER_COLLATOR_PASS__R50_TRAIN_HOLD"
                   if template is not None else
                   "COMMON2_CPU_TOKENIZER_PASS__COLLATOR_R50_HOLD"),
        "cases": 2,
        "tokenizer_input_token_counts": [v["input_tokens_with_target"] for v in results],
        "real_collator_token_counts": [
            v["actual_collator_tokens"] for v in results
        ] if template is not None else [],
        "supervised_token_counts": [
            v["supervised_tokens"] for v in results
        ] if template is not None else [],
        "tokenizer_verified": True, "collator_verified": template is not None,
        "r50_complete_exclusion_verified": False, "train_admitted": 0,
        "model_inference_calls": 0, "gpu_started": False,
        "private_values_emitted": False, "database_accessed": False,
    }


SAFE_PHASES = frozenset({
    "SNAPSHOT_CHECK", "PRIVATE_INPUT_CHECK", "TOKENIZER_LOAD",
    "SWIFT_PROCESSOR_LOAD", "SWIFT_TEMPLATE_INIT",
    "TOKENIZER_ENCODE", "SWIFT_COLLATOR_AUDIT",
})


def run(args: argparse.Namespace) -> dict:
    def set_phase(value: str) -> None:
        if value not in SAFE_PHASES:
            raise Hold("UNKNOWN_AUDIT_PHASE_HOLD")
        args._safe_phase = value

    set_phase("SNAPSHOT_CHECK")
    if args.snapshot.is_symlink() or PIN not in str(args.snapshot.resolve()):
        raise Hold("PINNED_LOCAL_SNAPSHOT_HOLD")
    for file in ("tokenizer.json", "tokenizer_config.json"):
        if not (args.snapshot / file).is_file():
            raise Hold("LOCAL_TOKENIZER_FILES_HOLD")
    set_phase("PRIVATE_INPUT_CHECK")
    private.private_dir(args.input_dir, create=False)
    raw = private.read_private(args.input_dir / sft.DATA_NAME, LIMIT)
    manifest = json.loads(private.read_private(
        args.input_dir / sft.MANIFEST_NAME, 65536,
    ))
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
    validate_payload(rows, manifest, raw)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    set_phase("TOKENIZER_LOAD")
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True, trust_remote_code=False,
        use_fast=True,
    )
    template = None
    if args.stage == "both":
        set_phase("SWIFT_PROCESSOR_LOAD")
        from swift import get_processor, get_template
        processor = get_processor(str(args.snapshot))
        set_phase("SWIFT_TEMPLATE_INIT")
        template = get_template(
            processor,
            loss_scale="last_round", max_length=CEILING,
            add_non_thinking_prefix=False,
        )
        template.set_mode("train")
    return inspect_rows(rows, tok, template, phase=set_phase)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--stage", choices=("token", "both"), default="token")
    args = p.parse_args()
    args._safe_phase = "SNAPSHOT_CHECK"
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:  # noqa: BLE001 - no private text/IDs/traceback
        print(json.dumps({
            "schema": SCHEMA, "status": "COMMON2_CPU_TEMPLATE_AUDIT_HOLD",
            "tokenizer_verified": False, "collator_verified": False,
            "r50_complete_exclusion_verified": False, "train_admitted": 0,
            "model_inference_calls": 0, "gpu_started": False,
            "private_values_emitted": False,
            "reason_code": (
                args._safe_phase + "_HOLD"
                if args._safe_phase in SAFE_PHASES else "SAFE_PHASE_UNKNOWN_HOLD"
            ),
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
