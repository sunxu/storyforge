"""Offline CPU Qwen tokenizer and actual ms-swift collator audit for Common2.

Never download weights or model files; require an already pinned LOCAL
tokenizer snapshot. Never emit private source text, decoded labels, IDs, or
token digests. The internal ms-swift audit emits detailed stdout, captured and
discarded here. The input stays NOT_ADMITTED regardless of audit success.
"""
from __future__ import annotations

import argparse
import contextlib
from collections.abc import Mapping
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

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
        output = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=False,
        )
        # transformers 5.16.1 returns BatchEncoding for Qwen3.8.
        # Use only its input_ids field; never silently flatten nested batches.
        ids = output.get("input_ids") if isinstance(output, Mapping) else output
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
            # Step-specific SAFE phase codes: never print R18's internal
            # decoded-token leak diagnostics, source text, or exceptions.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                if phase is not None:
                    phase("R18_LABEL_MASK_AUDIT")
                audit.audit_row(template, swift_row, number)
                if phase is not None:
                    phase("SWIFT_ENCODE")
                encoded = template.encode(swift_row)
                if phase is not None:
                    phase("SWIFT_BATCH_COLLATE")
                collator = getattr(template, "data_collator", None)
                if not callable(collator):
                    raise Hold("REAL_COLLATOR_UNAVAILABLE_HOLD")
                batch = collator([encoded])
            if phase is not None:
                phase("BATCH_LABEL_CONSISTENCY")
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
        "model_inference_calls": 0, "model_weights_loaded": False,
        "native_template_token_parity_verified": False,
        "gpu_started": False, "private_values_emitted": False,
        "database_accessed": False,
    }


def bind_text_only_rope(template, snapshot: Path) -> None:
    """Use the official Transformers Qwen3.5 RoPE method without model weights.

    This is a narrow workaround for ms-swift's default CPU collator, which
    otherwise builds a full 27B CPU dummy_model while computing position_ids.
    The actual ms-swift data_collator remains in use; the model lookup used
    to supply its text-only RoPE callback is replaced. No multimodal batches.
    """
    import torch
    from transformers import AutoConfig
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5Model

    config = AutoConfig.from_pretrained(
        str(snapshot), local_files_only=True, trust_remote_code=False,
    )
    if getattr(config, "model_type", None) != "qwen3_5":
        raise Hold("TEXT_ROPE_CONFIG_HOLD")
    config_only = SimpleNamespace(config=config)

    def text_rope(input_ids, **kwargs):
        mm_types = kwargs.get("mm_token_type_ids")
        if (kwargs.get("image_grid_thw") is not None
                or kwargs.get("video_grid_thw") is not None
                or mm_types is None
                or not isinstance(mm_types, torch.Tensor)
                or bool(torch.any(mm_types != 0).item())):
            raise Hold("TEXT_ONLY_ROPE_MODALITY_HOLD")
        # Calls the exact official v5.16.1 RoPE implementation. The
        # config-only receiver has no parameters, weights or inference API.
        return Qwen3_5Model.get_rope_index(
            config_only, input_ids, **kwargs,
        )

    if type(template).__name__ != "Qwen3_8Template":
        raise Hold("QWEN38_TEMPLATE_BINDING_HOLD")
    template._get_get_rope_index = lambda: text_rope


SAFE_PHASES = frozenset({
    "SNAPSHOT_CHECK", "PRIVATE_INPUT_CHECK", "TOKENIZER_LOAD",
    "SWIFT_PROCESSOR_LOAD", "SWIFT_TEMPLATE_INIT", "TEXT_ONLY_ROPE_SETUP",
    "TOKENIZER_ENCODE", "SWIFT_COLLATOR_AUDIT",
    "R18_LABEL_MASK_AUDIT", "SWIFT_ENCODE", "SWIFT_BATCH_COLLATE",
    "BATCH_LABEL_CONSISTENCY",
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
        # Qwen3.8 config.model_type=qwen3_5; ms-swift 4.5.3 cannot
        # resolve this multimodal Processor unless model_type is explicit.
        processor = get_processor(str(args.snapshot), model_type="qwen3_5")
        set_phase("SWIFT_TEMPLATE_INIT")
        # Both qwen3_5 and qwen3_8 templates are registered: require the
        # model-specific Qwen3.8 template rather than picking arbitrarily.
        template = get_template(
            processor, template_type="qwen3_8",
            loss_scale="last_round", max_length=CEILING,
            add_non_thinking_prefix=False,
        )
        template.set_mode("train")
        set_phase("TEXT_ONLY_ROPE_SETUP")
        bind_text_only_rope(template, args.snapshot)
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
            "model_inference_calls": 0, "model_weights_loaded": False,
            "gpu_started": False, "private_values_emitted": False,
            "reason_code": (
                args._safe_phase + "_HOLD"
                if args._safe_phase in SAFE_PHASES else "SAFE_PHASE_UNKNOWN_HOLD"
            ),
        }, sort_keys=True), file=sys.stderr)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
