"""R60 Qwen: local weights, ONE vLLM engine across consecutive review batches.

Use with a frozen *copy* of role-A runner.py and source.private.jsonl.
Original reviewer owns prompt, SamplingParams, quote repair, schema validation,
checkpoint format, model identity and revision. No training or admission.
Fail closed: mandatory first valid checkpoint; uninterrupted monotonically
increasing checkpoints; per-batch progress; resumable verified prefix only.

No large-file SHA on this path: localizer does size checks against the pinned
Hub metadata. This script never claims a fresh content-hash verification.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

MODEL = "Qwen/Qwen3-32B"
REV = "9216db5781bf21249d130ec9da846c4624c16137"
A25_SHA = "492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069"
A1000_SHA = "687528efe5081ac8ce32dcb88f575b3e59d9e7536baf6bd5ec1563283e455320"
MANIFEST = "r60_weights_verified_manifest.json"
SCHEMA = "storyforge_r60_qwen_continuous_review_safe_v1"
INDEXED = re.compile(r"model-\d{5}-of-00017\.safetensors\Z")


class Hold(ValueError):
    pass


def emit(event: str, **fields: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **fields},
                     sort_keys=True, separators=(",", ":")), flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for piece in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def verify_local_manifest(local: Path) -> str:
    if not local.is_absolute() or local.is_symlink() or not local.is_dir():
        raise Hold("LOCAL_MODEL_DIR_INVALID")
    manifest_path = local / MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise Hold("LOCAL_MANIFEST_MISSING")
    try:
        payload = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise Hold("LOCAL_MANIFEST_INVALID") from exc
    if (not isinstance(payload, dict)
            or payload.get("model") != MODEL or payload.get("revision") != REV
            or payload.get("integrity_mode") not in (
                "sha256-verified", "size-only-upstream-sha-declared")
            or not isinstance(payload.get("files"), list)):
        raise Hold("LOCAL_MANIFEST_INVALID")
    entries = payload["files"]
    names = set()
    shards = set()
    for item in entries:
        if (not isinstance(item, dict)
                or set(item) != {"name", "size", "sha256"}
                or not isinstance(item["name"], str)
                or not isinstance(item["size"], int)
                or isinstance(item["size"], bool)
                or item["size"] <= 0
                or not isinstance(item["sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])
                or item["name"] in names
                or "/" in item["name"] or "\\" in item["name"]
                or item["name"] in (".", "..")):
            raise Hold("LOCAL_MANIFEST_INVALID")
        names.add(item["name"])
        file = local / item["name"]
        if file.is_symlink() or not file.is_file() or file.stat().st_size != item["size"]:
            raise Hold("LOCAL_MODEL_FILE_SIZE_HOLD")
        if INDEXED.fullmatch(item["name"]):
            shards.add(item["name"])
    if (shards != {f"model-{i:05d}-of-00017.safetensors"
                   for i in range(1, 18)}
            or not {"tokenizer.json", "config.json",
                    "model.safetensors.index.json"}.issubset(names)):
        raise Hold("LOCAL_MODEL_INVENTORY_HOLD")
    try:
        idx = json.loads((local / "model.safetensors.index.json").read_text())
        idx_names = set(idx["weight_map"].values())
    except (OSError, ValueError, KeyError, AttributeError, TypeError) as exc:
        raise Hold("LOCAL_WEIGHT_INDEX_HOLD") from exc
    if idx_names != shards:
        raise Hold("LOCAL_WEIGHT_INDEX_HOLD")
    return payload["integrity_mode"]


def verify_runner_and_input(runner: Path, input_path: Path) -> int:
    if (runner.is_symlink() or not runner.is_file()
            or input_path.is_symlink() or not input_path.is_file()
            or input_path != runner.parent / "source.private.jsonl"):
        raise Hold("FROZEN_INPUT_PATH_HOLD")
    digest = sha256_file(input_path)
    if digest == A25_SHA:
        count = 25
    elif digest == A1000_SHA:
        count = 1000
    else:
        raise Hold("FROZEN_INPUT_SHA_HOLD")
    content = runner.read_text()
    if ("GuidedDecodingParams" not in content
            or "from vllm.sampling_params import StructuredOutputsParams" in content):
        raise Hold("REVIEWER_VLLM_API_NOT_PATCHED")
    return count


def checked_prefix(worker: object, rows: list[dict], output: Path,
                   *, resume: bool) -> int:
    if output.is_symlink() or not output.is_dir():
        raise Hold("REVIEW_OUTPUT_INVALID")
    objects = list(output.iterdir())
    if not resume and objects:
        raise Hold("REVIEW_OUTPUT_NONEMPTY_HOLD")
    slots = set()
    for item in objects:
        if (item.is_symlink() or not item.is_file()
                or not re.fullmatch(r"review_\d{4}\.private\.json", item.name)):
            raise Hold("REVIEW_OUTPUT_FOREIGN_FILE_HOLD")
        position = int(item.name[7:11])
        if not 1 <= position <= len(rows) or item.name != worker.checkpoint_name(position):
            raise Hold("REVIEW_CHECKPOINT_NAME_HOLD")
        slots.add(position)
    if slots != set(range(1, len(slots) + 1)):
        raise Hold("REVIEW_PREFIX_GAP_HOLD")
    for position in sorted(slots):
        record = worker.read_checkpoint(
            output / worker.checkpoint_name(position),
            position, rows[position - 1], MODEL, REV)
        if record is None:
            raise Hold("REVIEW_PREFIX_CHECKPOINT_HOLD")
    return len(slots)


def run_batches(worker: object, rows: list[dict], output: Path,
                local: Path, *, limit: int, batch_size: int,
                max_model_len: int, max_output_tokens: int,
                wall_seconds: int, resume: bool,
                hf_tokenizer: object, vllm: object,
                diagnose_generation: bool = False,
                min_remaining_seconds: int = 120) -> dict:
    if len(rows) not in (25, 1000) or not 1 <= limit <= len(rows):
        raise Hold("REVIEW_SCOPE_INVALID")
    if (not 1 <= batch_size <= 100 or
            max_model_len != 32768 or max_output_tokens != 2400
            or not 120 <= wall_seconds <= 43200):
        raise Hold("REVIEW_RUNTIME_CONFIG_HOLD")
    prefix = checked_prefix(worker, rows, output, resume=resume)
    if prefix > limit:
        raise Hold("REVIEW_RESUME_SCOPE_HOLD")
    if prefix:
        emit("REVIEW_PREFIX_VERIFIED", count=prefix)
    original_inference = worker.inference
    original_write = worker.write_checkpoint
    original_tokenizer = hf_tokenizer.from_pretrained
    original_llm = vllm.LLM
    state = {
        "completed": prefix, "engine": None, "engine_calls": 0,
        "tokenizer": None, "first_pass": prefix >= 1,
        "rows": rows, "output": output,
    }

    def tokenizer_load(model, *args, **kwargs):
        # The frozen reviewer loads by Hub ID+revision. The vLLM engine can
        # separately ask Transformers for the already verified local folder.
        # Reject any other path/repo to preserve offline fail-closed behavior.
        if model == str(local):
            if kwargs.get("revision") not in (None, REV):
                raise Hold("LOCAL_TOKENIZER_REVISION_HOLD")
            kwargs = dict(kwargs)
            kwargs.pop("revision", None)
            emit("VLLM_INTERNAL_LOCAL_TOKENIZER")
            return original_tokenizer(str(local), *args, **kwargs)
        if model != MODEL or kwargs.get("revision") != REV:
            raise Hold("TOKENIZER_IDENTITY_HOLD")
        if state["tokenizer"] is None:
            kwargs = dict(kwargs)
            kwargs.pop("revision")
            emit("LOCAL_TOKENIZER_INIT")
            try:
                state["tokenizer"] = original_tokenizer(str(local), *args, **kwargs)
            except Exception as exc:
                emit("LOCAL_TOKENIZER_HOLD", exception_class=type(exc).__name__)
                raise
        return state["tokenizer"]

    def engine_load(*args, **kwargs):
        if (args or kwargs.get("model") != MODEL
                or kwargs.get("revision") != REV
                or kwargs.get("tokenizer_revision") != REV):
            raise Hold("ENGINE_IDENTITY_HOLD")
        if state["engine"] is None:
            args_for_local = dict(kwargs)
            args_for_local["model"] = str(local)
            args_for_local["tokenizer"] = str(local)
            args_for_local.pop("revision")
            args_for_local.pop("tokenizer_revision")
            emit("REAL_ENGINE_INIT_START")
            try:
                state["engine"] = original_llm(**args_for_local)
            except Exception as exc:
                emit("REAL_ENGINE_INIT_HOLD", exception_class=type(exc).__name__,
                     stage="VLLM_CONSTRUCTOR")
                raise
            state["engine_calls"] += 1
            emit("REAL_ENGINE_READY", engine_init_count=1)
        else:
            emit("REAL_ENGINE_REUSED", engine_init_count=state["engine_calls"])
        if diagnose_generation:
            from r60_qwen_guidance_diagnostic import TracedEngine

            return TracedEngine(state["engine"], emit)
        return state["engine"]

    def guarded_write(path: Path, record: dict) -> None:
        position = state["completed"] + 1
        if (position > limit
                or Path(path) != output / worker.checkpoint_name(position)
                or record.get("position") != position):
            raise Hold("REVIEW_CHECKPOINT_ORDER_HOLD")
        original_write(path, record)
        if worker.read_checkpoint(path, position, rows[position - 1], MODEL, REV) is None:
            raise Hold("REVIEW_CHECKPOINT_READBACK_HOLD")
        state["completed"] = position
        if position == 1:
            state["first_pass"] = True
            emit("FIRST_CHECKPOINT_GATE_PASS", completed=1,
                 same_engine_next=True)
        elif position % batch_size == 0 or position == limit:
            emit("REVIEW_CHECKPOINT_PROGRESS", completed=position, target=limit)

    hf_tokenizer.from_pretrained = staticmethod(tokenizer_load)
    vllm.LLM = engine_load
    worker.write_checkpoint = guarded_write
    started = time.monotonic()
    try:
        while state["completed"] < limit:
            elapsed = time.monotonic() - started
            remaining = wall_seconds - elapsed
            if remaining < min_remaining_seconds:
                emit("REVIEW_WALL_BUDGET_HOLD", completed=state["completed"],
                     target=limit)
                break
            start = state["completed"] + 1
            this_batch = min(batch_size, limit - state["completed"])
            emit("BATCH_START", start=start, batch_size=this_batch,
                 already_completed=state["completed"])
            before = state["completed"]
            try:
                if diagnose_generation:
                    import vllm.sampling_params as sampling_module
                    from r60_qwen_guidance_diagnostic import (
                        trace_generation_stages, trace_reviewer_stages)

                    with (trace_generation_stages(vllm, sampling_module, emit),
                          trace_reviewer_stages(worker, emit)):
                        original_inference(
                            rows, output, MODEL, REV, start, this_batch,
                            max_model_len, max_output_tokens,
                            max(min_remaining_seconds, int(remaining)))
                else:
                    original_inference(
                        rows, output, MODEL, REV, start, this_batch,
                        max_model_len, max_output_tokens,
                        max(min_remaining_seconds, int(remaining)))
            except Exception as exc:
                # Only immutable, reviewed errors from the frozen verifier;
                # never expose arbitrary exception string or private payload.
                safe_reasons = {
                    "MODEL_GENERATION_INCOMPLETE_HOLD",
                    "MODEL_JSON_HOLD", "MODEL_RESPONSE_SCHEMA_HOLD",
                    "MODEL_NONEXACT_QUOTE_HOLD",
                    "QUOTE_REPAIR_VALIDATION_HOLD",
                    "QUOTE_REPAIR_GENERATION_HOLD",
                    "QUOTE_REPAIR_INCOMPLETE_HOLD",
                    "QUOTE_REPAIR_JSON_HOLD",
                    "MODEL_BELOW_QUALITY_FLOOR_HOLD",
                    "MODEL_SEVERE_MUST_REJECT",
                    "CHECKPOINT_OUTPUT_SIZE_HOLD",
                    "CHECKPOINT_FILE_HOLD",
                    "CHECKPOINT_SCHEMA_HOLD",
                    "CHECKPOINT_SOURCE_OR_MODEL_HOLD",
                }
                code = (str(exc) if type(exc).__name__ == "ReviewError"
                        and str(exc) in safe_reasons else "UNKNOWN_REVIEW_FAILURE")
                emit("REVIEW_BATCH_HOLD", completed=state["completed"],
                     stage=("MODEL_INITIALIZATION" if state["engine_calls"] == 0
                            else "REVIEW_OR_CHECKPOINT"),
                     exception_class=type(exc).__name__,
                     safe_reason_code=code)
                raise
            if state["completed"] == before:
                raise Hold("REVIEW_BATCH_NO_PROGRESS_HOLD")
            if not state["first_pass"]:
                raise Hold("FIRST_CHECKPOINT_NOT_VERIFIED")
            emit("BATCH_COMPLETE", completed=state["completed"],
                 target=limit, engine_init_count=state["engine_calls"])
        if state["completed"] == limit:
            if state["engine_calls"] != (0 if prefix == limit else 1):
                raise Hold("ENGINE_RELOAD_OR_MISSING_HOLD")
            emit("CONTINUOUS_REVIEW_COMPLETE", completed=limit,
                 engine_init_count=state["engine_calls"])
            return {"completed": state["completed"], "complete": True}
        return {"completed": state["completed"], "complete": False}
    finally:
        worker.write_checkpoint = original_write
        hf_tokenizer.from_pretrained = staticmethod(original_tokenizer)
        vllm.LLM = original_llm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--local-dir", type=Path, required=True)
    parser.add_argument("--case-limit", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--max-output-tokens", type=int, default=2400)
    parser.add_argument("--wall-seconds", type=int, default=5400)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--isolate-technical-failures", action="store_true")
    parser.add_argument("--diagnose-generation-stages", action="store_true")
    parser.add_argument("--confirm-paid-gpu", action="store_true")
    args = parser.parse_args()
    try:
        if (not args.confirm_paid_gpu or args.model != MODEL
                or args.revision != REV or args.case_limit < 1):
            raise Hold("REVIEW_ARGS_HOLD")
        integrity = verify_local_manifest(args.local_dir)
        runner = Path(__file__).resolve().parent / "runner.py"
        expected_count = verify_runner_and_input(runner, args.input)
        if args.case_limit > expected_count:
            raise Hold("REVIEW_SCOPE_INVALID")
        spec = importlib.util.spec_from_file_location("r60_frozen_reviewer", runner)
        if spec is None or spec.loader is None:
            raise Hold("REVIEWER_IMPORT_HOLD")
        sys.path.insert(0, str(runner.parent))
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        for attr in ("read_input", "read_checkpoint", "write_checkpoint",
                     "checkpoint_name", "inference"):
            if not callable(getattr(worker, attr, None)):
                raise Hold("REVIEWER_API_HOLD")
        rows = worker.read_input(args.input)
        if len(rows) != expected_count:
            raise Hold("REVIEW_INPUT_COUNT_HOLD")
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        import vllm
        from transformers import AutoTokenizer

        emit("CONTINUOUS_REVIEW_READY", input_count=expected_count,
             target=args.case_limit, batch_size=args.batch_size,
             integrity_mode=integrity, model_pinned=True)
        if args.isolate_technical_failures and args.diagnose_generation_stages:
            raise Hold("DIAGNOSTIC_AND_ISOLATION_COMBINATION_HOLD")
        if args.isolate_technical_failures:
            from r60_review_isolation_core import run_isolated

            result = run_isolated(
                worker, rows, args.output_dir, args.local_dir,
                model=MODEL, revision=REV,
                limit=args.case_limit, batch_size=args.batch_size,
                max_model_len=args.max_model_len,
                max_output_tokens=args.max_output_tokens,
                wall_seconds=args.wall_seconds, resume=args.resume,
                hf_tokenizer=AutoTokenizer, vllm=vllm)
            # All attempted with technical failures is an analysis artifact,
            # NOT a complete validated review / training admission.
            return 0 if result["all_verified"] else 42
        result = run_batches(
            worker, rows, args.output_dir, args.local_dir,
            limit=args.case_limit, batch_size=args.batch_size,
            max_model_len=args.max_model_len,
            max_output_tokens=args.max_output_tokens,
            wall_seconds=args.wall_seconds, resume=args.resume,
            hf_tokenizer=AutoTokenizer, vllm=vllm,
            diagnose_generation=args.diagnose_generation_stages)
        return 0 if result["complete"] else 42
    except Exception as exc:  # noqa: BLE001 - only bounded status, no input
        emit("CONTINUOUS_REVIEW_HOLD",
             reason_code=str(exc) if isinstance(exc, Hold)
             else "REVIEW_RUNTIME_EXCEPTION_REDACTED")
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
