#!/usr/bin/env python3
"""R53 immutable 31/9: HF CPU-only actual Qwen tokenizer/ms-swift/collator audit.

  preflight --stage <private_stage>     -- before remote pip install, stdlib only
  audit     --stage <private_stage> --output-dir <unique result directory>

No train/validation release, training, model weights, or R50 are opened.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any
from collections.abc import Mapping

BASE = "hf://buckets/adradar/storyforge-training"
MODEL = "Qwen/Qwen3.8-27B"
REV = "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"
MANIFEST_SHA = "00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261"
SOURCE_SHA = {
    "train": "f17fc33f566b5a1ddd424de2d26a032a812453255c76e0f5fa321fb0f3a9ecf9",
    "validation": "83e3d1ab4cc955c4b5bba2afc63f355a227934a89203bcc058cfb922a093b01d",
}
COMPILED_SHA = {
    "train": "d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7",
    "validation": "b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d",
}
COUNTS = {"train": 31, "validation": 9}
EXPECTED_PACKAGE_VERSIONS = {"ms-swift": "4.5.3", "transformers": "5.16.1"}
EXPECTED_AUDITOR_BLOB = "15296f1d8438f40d727c84913ac658cf6de01cb4"
R27_SYSTEM_SHA = "5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def ensure(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def canonical_compiled(row: dict[str, Any]) -> bytes:
    clean = []
    for i, msg in enumerate(row["messages"]):
        item = {"role": msg["role"], "content": msg["content"]}
        if item["role"] == "assistant":
            item["loss"] = i == len(row["messages"]) - 1
        clean.append(item)
    return (json.dumps({"messages": clean}, ensure_ascii=False) + "\n").encode()


def preflight(stage: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, bytes]]:
    stage = stage.resolve(strict=True)
    manifest_path = stage / "STAGED_31_9_SOURCE_HASH_MANIFEST_PRIVATE.json"
    ensure(manifest_path.is_file(), "R53 missing frozen stage manifest")
    ensure(sha(manifest_path.read_bytes()) == MANIFEST_SHA, "R53 stage manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_bytes())
    ensure(manifest.get("official_train_val_admitted") is False, "R53 data was improperly marked admitted")
    ensure(manifest.get("r50_sealed") is True and manifest.get("gpu_authorized") is False,
           "R53 gate status modified")
    ensure(manifest.get("loss_policy") == "last_round_FINAL_ASSISTANT_ONLY", "R53 loss-policy mismatch")
    rows: dict[str, list[dict[str, Any]]] = {}
    compiled: dict[str, bytes] = {}
    worlds: dict[str, set[str]] = {}
    seen_ids: set[str] = set()
    system_sha = None
    for split, count in COUNTS.items():
        path = stage / f"STAGED_{split.upper()}_NOT_ADMITTED.jsonl"
        ensure(path.is_file(), f"R53 {split} missing stage file")
        body = path.read_bytes()
        ensure(sha(body) == SOURCE_SHA[split], f"R53 {split} source SHA mismatch")
        node = manifest["staged_files"][split]
        ensure(node["sha256"] == SOURCE_SHA[split] and node["bytes"] == len(body)
               and node["rows"] == count and node["file"] == path.name,
               f"R53 {split} stage-manifest record mismatch")
        current = [json.loads(s) for s in body.splitlines() if s.strip()]
        ensure(len(current) == count, f"R53 {split} count mismatch")
        world_set: set[str] = set()
        chunks: list[bytes] = []
        for r in current:
            cid = r["id"]
            ensure(isinstance(cid, str) and cid and cid not in seen_ids, "R53 duplicate/invalid case ID")
            seen_ids.add(cid)
            md = r["metadata"]
            msgs = r["messages"]
            ensure(len(msgs) >= 3 and msgs[0]["role"] == "system"
                   and msgs[-2]["role"] == "user" and msgs[-1]["role"] == "assistant",
                   "R53 invalid conversation end")
            ensure(all(m["role"] in {"system", "user", "assistant"} and isinstance(m["content"], str)
                       for m in msgs), "R53 unknown role or non-text content")
            ensure(all(m.get("loss") is False for m in msgs[:-1]) and msgs[-1].get("loss") is True,
                   "R53 target-only loss policy violated")
            ensure(md["dataset_admission"] == "NOT_APPROVED" and md["approved_split"] is None
                   and md["gpu_authorized"] is False and md["suggested_split_only"] == split,
                   "R53 unauthorized release or split metadata")
            ensure(md["actual_qwen_collator_pass"] is False, "R53 false historical collator pass")
            ensure(sha(msgs[-1]["content"].encode()) == md["target_sha256"], "R53 target source SHA mismatch")
            history = msgs[1:-1]
            ensure(len(md["history_body_sha256"]) == len(history), "R53 history SHA count mismatch")
            ensure(all(sha(m["content"].encode()) == h for m, h in zip(history, md["history_body_sha256"])),
                   "R53 original history SHA mismatch")
            this_system_sha = sha(msgs[0]["content"].encode())
            ensure(this_system_sha == R27_SYSTEM_SHA, "R53 R27 System prompt changed")
            system_sha = this_system_sha
            ensure(isinstance(md["source_story_id"], str) and md["source_story_id"], "R53 story UUID missing")
            world_set.add(md["source_story_id"])
            chunks.append(canonical_compiled(r))
        data = b"".join(chunks)
        ensure(sha(data) == COMPILED_SHA[split], f"R53 {split} compiled message SHA mismatch")
        rows[split], compiled[split], worlds[split] = current, data, world_set
    ensure(len(seen_ids) == 40, "R53 expected 40 unique cases")
    ensure(len(worlds["train"]) == 5 and len(worlds["validation"]) == 2
           and not worlds["train"] & worlds["validation"], "R53 Train/Val world leakage")
    ensure(manifest["train_val_source_uuid_intersection"] == 0, "R53 manifest world intersection changed")
    ensure(system_sha == R27_SYSTEM_SHA, "R53 system hash lost")
    return rows, compiled


def one_int_list(val: Any) -> list[int]:
    """One sequence from BatchEncoding/tensor/list. Reject ambiguous batch shapes."""
    if isinstance(val, Mapping):
        val = val["input_ids"]
    if hasattr(val, "detach"):
        val = val.detach().cpu().tolist()
    elif hasattr(val, "tolist"):
        val = val.tolist()
    if isinstance(val, tuple):
        val = list(val)
    if isinstance(val, list) and len(val) == 1 and isinstance(val[0], (list, tuple)):
        val = list(val[0])
    ensure(isinstance(val, list) and bool(val) and all(type(i) is int for i in val),
           "R53 expected exactly one nonempty token/label integer sequence")
    return val


def check_collator(single: dict[str, Any], batch: dict[str, Any]) -> dict[str, int]:
    ids = one_int_list(single["input_ids"])
    labels = one_int_list(single["labels"])
    b_ids = one_int_list(batch["input_ids"])
    b_labels = one_int_list(batch["labels"])
    ensure(len(ids) == len(labels) and len(ids) <= 16384, "R53 ms-swift native encoded size invalid")
    ensure(len(b_ids) == len(b_labels) and len(b_ids) >= len(ids), "R53 collator batch size invalid")
    # For a single sample, padding is allowed at either side; verify align and padding.
    matching_offsets = []
    for offset in range(len(b_ids) - len(ids) + 1):
        if b_ids[offset:offset + len(ids)] == ids and b_labels[offset:offset + len(ids)] == labels:
            matching_offsets.append(offset)
    ensure(bool(matching_offsets), "R53 collator changes actual source ids or label positions")
    for offset in matching_offsets:
        if all(x == -100 for x in (b_labels[:offset] + b_labels[offset + len(ids):])):
            break
    else:
        raise ValueError("R53 collator supervised padding tokens")
    active = [x for x in labels if x != -100]
    ensure(bool(active), "R53 final target has no supervised tokens")
    ensure(all(v == ids[i] for i, v in enumerate(labels) if v != -100),
           "R53 non-token supervised label")
    return {"native_tokens": len(ids), "supervised_tokens": len(active), "collated_tokens": len(b_ids),
            "padding_tokens": len(b_ids) - len(ids)}


def audit(stage: Path, out_dir: Path) -> None:
    rows, compiled = preflight(stage)  # No third-party imports before integrity check
    ensure(not out_dir.exists(), "R53 output path already exists: refuse overwrite")
    out_dir.mkdir(parents=True, exist_ok=False)
    result: dict[str, Any] = {
        "schema": "storyforge-r53-hf-cpu-40-real-audit-v1",
        "status": "BLOCKED",
        "formal_training_admission": False,
        "training_performed": False,
        "gpu_used": False,
        "r50_read": False,
        "model": MODEL,
        "model_revision": REV,
        "stage_manifest_sha256": MANIFEST_SHA,
        "source_input_sha256": SOURCE_SHA,
        "compiled_input_sha256": COMPILED_SHA,
        "expected_rows": COUNTS,
        "run_key": os.getenv("STORYFORGE_R53_RUN_KEY", "UNBOUND_LOCAL_DIAGNOSTIC"),
        "auditor_script_sha256": sha(Path(__file__).read_bytes()),
        "worker_bundle_sha256": sha((stage / "../SHA256SUMS.txt").resolve().read_bytes()) if (stage / "../SHA256SUMS.txt").is_file() else None,
        "checked": {"train": 0, "validation": 0},
        "rows": [],
    }
    try:
        versions = {n: importlib.metadata.version(n) for n in EXPECTED_PACKAGE_VERSIONS}
        ensure(versions == EXPECTED_PACKAGE_VERSIONS, "R53 installed dependency pin mismatch")
        result["versions"] = versions
        # This is a public tokenizer-only selective fetch: does not download model weights.
        from huggingface_hub import snapshot_download
        snapshot = Path(snapshot_download(repo_id=MODEL, revision=REV,
            allow_patterns=["tokenizer*", "special_tokens_map.json", "added_tokens.json",
                            "chat_template*", "config.json", "generation_config.json", "*.tiktoken"]))
        ensure(snapshot.resolve().name == REV, "R53 Qwen snapshot revision drift")
        for name in ("config.json", "tokenizer_config.json", "tokenizer.json"):
            ensure((snapshot / name).is_file(), f"R53 tokenizer asset missing: {name}")
        result["tokenizer_asset_sha256"] = {
            name: sha((snapshot / name).read_bytes()) for name in ("tokenizer_config.json", "tokenizer.json")}
        result["snapshot_revision"] = snapshot.name
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True,
                                             trust_remote_code=False, use_fast=True)
        result["chat_template_sha256"] = sha(str(tok.chat_template).encode())
        from swift import get_processor, get_template
        import hf_label_mask_audit as verifier
        ensure(blob_sha(Path(verifier.__file__)) == EXPECTED_AUDITOR_BLOB,
               "R53 official repo label-mask auditor Git blob drift")
        os.environ["HF_HUB_OFFLINE"] = "1"  # ms-swift must reuse locally pinned tokenizer
        processor = get_processor(str(snapshot))
        template = get_template(processor, loss_scale="last_round", max_length=16384,
                                add_non_thinking_prefix=False)
        template.set_mode("train")
        ensure(getattr(template.loss_scale, "base_strategy", None) == "last_round",
               "R53 ms-swift template not last_round")
        collator = getattr(template, "data_collator", None)
        ensure(callable(collator), "R53 real ms-swift data_collator unavailable")
        for split, count in COUNTS.items():
            for row in rows[split]:
                sample_n = result["checked"][split] + 1
                # Render actual transformers chat-template tokens (do not infer length from text).
                raw = [{"role": m["role"], "content": m["content"]} for m in row["messages"]]
                rendered = one_int_list(tok.apply_chat_template(raw, tokenize=True,
                    add_generation_prompt=False, return_dict=True))
                ensure(len(rendered) <= 16384, f"R53 token budget exceeded in {split}")
                # Audited repo implementation proves forbidden segment labels masked.
                verifier.audit_row(template, {"messages": row["messages"]}, sample_n)
                native = template.encode({"messages": row["messages"]})
                collated = collator([native])
                stats = check_collator(native, collated)
                digest = sha(json.dumps(one_int_list(native["labels"]), separators=(",", ":")).encode())
                result["rows"].append({
                    "id": row["id"], "split": split, "target_sha256": row["metadata"]["target_sha256"],
                    "transformers_tokens": len(rendered), "transformers_vs_swift_input_identical":
                        rendered == one_int_list(native["input_ids"]),
                    **stats, "native_label_sha256": digest,
                    "status": "REAL_LAST_ASSISTANT_AND_COLLATOR_PASS",
                })
                result["checked"][split] += 1
        ensure(result["checked"] == COUNTS and len(result["rows"]) == 40,
               "R53 no complete 40/40 audit")
        result["status"] = "R53_HF_CPU40_REAL_TOKENIZER_COLLATOR_MASK_PASS__NO_DATA_ADMISSION"
        print("R53_ACTUAL_HF_CPU40_LABEL_MASK_PASS 40/40")
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:600]}"
        result["error_type"] = type(exc).__name__
        traceback.print_exc()
    # Honest BLOCKED results are useful, but never write a false PASS.
    result_path = out_dir / "R53_HF_CPU40_AUDIT_REPORT_PRIVATE.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print("R53_REPORT=", result_path)
    print("R53_STATUS=", result["status"])
    if result["status"].startswith("R53_HF_CPU40_REAL_TOKENIZER_COLLATOR_MASK_PASS"):
        return
    raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--stage", type=Path, required=True)
    a = sub.add_parser("audit")
    a.add_argument("--stage", type=Path, required=True)
    a.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            x, data = preflight(args.stage)
            print("R53_STAGE_PREFLIGHT_PASS 31/9", {k: len(v) for k, v in x.items()},
                  {k: sha(v) for k, v in data.items()})
        else:
            audit(args.stage, args.output_dir)
    except (ValueError, FileNotFoundError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("R53_HF_CPU40_BLOCKED:", type(exc).__name__, str(exc), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
