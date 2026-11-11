"""R60 GLM-4 B25: ONE locally loaded vLLM engine for multiple batches.

Use with a frozen *copy* of role-B runner.py and source.private.jsonl.
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

MODEL = "zai-org/GLM-4-32B-0414"
REV = "8dea913c41b543527c2860fb6f3c15c202f24aeb"
B25_SHA = "01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9"

MANIFEST = "r60_weights_verified_manifest.json"
SCHEMA = "storyforge_r60_glm4_b25_continuous_review_safe_v1"
INDEXED = re.compile(r"model-\d{5}-of-00014\.safetensors\Z")


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
    if (shards != {f"model-{i:05d}-of-00014.safetensors"
                   for i in range(1, 15)}
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
    if digest != B25_SHA:
        raise Hold("FROZEN_INPUT_SHA_HOLD")
    count = 25
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
                min_remaining_seconds: int = 120) -> dict:
    if len(rows) != 25 or not 1 <= limit <= len(rows):
        raise Hold("REVIEW_SCOPE_INVALID")
    if (not 1 <= batch_size <= 25 or
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
                original_inference(
                    rows, output, MODEL, REV, start, this_batch,
                    max_model_len, max_output_tokens,
                    max(min_remaining_seconds, int(remaining)))
            except Exception as exc:
                # SAFE literal reviewer reasons only. Never log arbitrary
                # exception messages, response text or private case content.
                allowed = {
                    "REVIEW_PROMPT_TOKEN_BUDGET_HOLD",
                    "MODEL_GENERATION_INCOMPLETE_HOLD",
                    "MODEL_JSON_HOLD",
                    "MODEL_RESPONSE_SCHEMA_HOLD",
                    "MODEL_SCORE_OR_SEVERE_HOLD",
                    "MODEL_REASON_HOLD",
                    "MODEL_NOTES_TYPE_HOLD",
                    "MODEL_NOTES_TOO_SHORT_HOLD",
                    "MODEL_UNCERTAINTY_TYPE_HOLD",
                    "MODEL_SEVERE_EVIDENCE_HOLD",
                    "MODEL_UNCERTAINTY_HOLD",
                    "MODEL_NONEXACT_QUOTE_HOLD",
                    "MODEL_SEVERE_MUST_REJECT",
                    "MODEL_BELOW_QUALITY_FLOOR_HOLD",
                    "QUOTE_REPAIR_FIELD_HOLD",
                    "QUOTE_REPAIR_CANDIDATES_HOLD",
                    "QUOTE_REPAIR_ITEMS_HOLD",
                    "QUOTE_REPAIR_SELECTION_HOLD",
                    "QUOTE_REPAIR_NONQUOTE_CHANGED_HOLD",
                    "QUOTE_REPAIR_VALIDATION_HOLD",
                    "QUOTE_REPAIR_TOKEN_ENCODING_HOLD",
                    "QUOTE_REPAIR_TOKEN_BUDGET_HOLD",
                    "QUOTE_REPAIR_GENERATION_HOLD",
                    "QUOTE_REPAIR_INCOMPLETE_HOLD",
                    "QUOTE_REPAIR_JSON_HOLD",
                    "CHECKPOINT_OUTPUT_SIZE_HOLD",
                    "CHECKPOINT_SOURCE_OR_MODEL_HOLD",
                    "CHECKPOINT_SCHEMA_HOLD",
                    "CHECKPOINT_FILE_HOLD",
                }
                candidate = str(exc) if type(exc).__name__ == "ReviewError" else ""
                safe_code = candidate if candidate in allowed else "UNKNOWN_REVIEW_FAILURE"
                emit("REVIEW_BATCH_HOLD", completed=state["completed"],
                     stage=("MODEL_INITIALIZATION" if state["engine_calls"] == 0
                            else "REVIEW_OR_CHECKPOINT"),
                     exception_class=type(exc).__name__,
                     safe_reason_code=safe_code)
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
    parser.add_argument("--retry-baseline-dir", type=Path)
    parser.add_argument("--quote-shape-diagnostic", action="store_true")
    parser.add_argument("--repair-quote-shape", action="store_true")
    parser.add_argument("--quote-match-observer", action="store_true")
    parser.add_argument("--quote-literal-repair", action="store_true")
    parser.add_argument("--literal-probe-cases", type=int, default=0)
    parser.add_argument("--generation-snapshot-dir", type=Path)
    parser.add_argument("--snapshot-probe-cases", type=int, default=0)
    parser.add_argument("--snapshot-primary-only", action="store_true")
    parser.add_argument("--snapshot-full25", action="store_true")
    parser.add_argument("--confirm-paid-gpu", action="store_true")
    args = parser.parse_args()
    try:
        if (not args.confirm_paid_gpu or args.model != MODEL
                or args.revision != REV or args.case_limit < 1):
            raise Hold("REVIEW_ARGS_HOLD")
        integrity = verify_local_manifest(args.local_dir)
        runner = Path(__file__).resolve().parent / "runner.py"
        expected_count = verify_runner_and_input(runner, args.input)
        if args.retry_baseline_dir is not None and (
            not args.isolate_technical_failures or args.resume
            or args.case_limit != 12
            or not (args.quote_shape_diagnostic or args.quote_match_observer
                    or args.quote_literal_repair)
        ):
            raise Hold("RETRY_ARGS_HOLD")
        if args.repair_quote_shape and (
            args.retry_baseline_dir is None or not args.quote_shape_diagnostic
        ):
            raise Hold("REPAIR_SCOPE_HOLD")
        if args.quote_shape_diagnostic and not args.isolate_technical_failures:
            raise Hold("SHAPE_DIAGNOSTIC_REQUIRES_ISOLATION_HOLD")
        if args.quote_match_observer and (
            (args.retry_baseline_dir is None and not args.snapshot_full25)
            or not args.isolate_technical_failures
            or args.quote_shape_diagnostic
            or args.repair_quote_shape
        ):
            raise Hold("MATCH_OBSERVER_SCOPE_HOLD")
        if args.quote_literal_repair and (
            args.retry_baseline_dir is None
            or not args.isolate_technical_failures
            or args.quote_shape_diagnostic
            or args.repair_quote_shape
        ):
            raise Hold("LITERAL_REPAIR_SCOPE_HOLD")
        if args.literal_probe_cases and (
            not 1 <= args.literal_probe_cases <= 2
            or not args.quote_literal_repair
            or not args.quote_match_observer
            or args.retry_baseline_dir is None
            or args.resume
        ):
            raise Hold("LITERAL_PROBE_SCOPE_HOLD")
        if args.literal_probe_cases < 0:
            raise Hold("LITERAL_PROBE_SCOPE_HOLD")
        if args.snapshot_full25 and (
            args.case_limit != 25 or args.retry_baseline_dir is not None
            or not args.isolate_technical_failures
            or args.generation_snapshot_dir is None
            or args.resume or args.snapshot_probe_cases
            or args.literal_probe_cases or args.snapshot_primary_only
            or args.quote_literal_repair or args.quote_shape_diagnostic
            or args.repair_quote_shape
        ):
            raise Hold("SNAPSHOT_FULL25_SCOPE_HOLD")
        if args.snapshot_probe_cases and (
            not 1 <= args.snapshot_probe_cases <= 2
            or args.generation_snapshot_dir is None
            or args.literal_probe_cases
            or args.resume
        ):
            raise Hold("SNAPSHOT_PROBE_SCOPE_HOLD")
        if args.snapshot_probe_cases < 0 or (
            args.generation_snapshot_dir is not None
            and args.snapshot_probe_cases == 0
        ):
            raise Hold("SNAPSHOT_PROBE_SCOPE_HOLD")
        if args.snapshot_primary_only and (
            args.generation_snapshot_dir is None
            or not args.snapshot_probe_cases
            or args.quote_literal_repair
            or args.quote_shape_diagnostic
            or args.repair_quote_shape
        ):
            raise Hold("SNAPSHOT_PRIMARY_ONLY_SCOPE_HOLD")
        if args.generation_snapshot_dir is not None and (
            not args.isolate_technical_failures
            or (args.retry_baseline_dir is None and not args.snapshot_full25)
            or args.resume or not args.quote_match_observer
        ):
            raise Hold("SNAPSHOT_ARGS_HOLD")
        # Private snapshots must never share the SAFE output directory or
        # immutable original source/baseline directories.
        if (args.generation_snapshot_dir is not None
                and args.generation_snapshot_dir.resolve() in (
                    args.output_dir.resolve(),
                    *( [args.retry_baseline_dir.resolve()] if args.retry_baseline_dir is not None else [] ),
                    runner.parent.resolve())):
            raise Hold("SNAPSHOT_DESTINATION_SCOPE_HOLD")
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
        if args.snapshot_primary_only and not isinstance(
            getattr(worker, "QuoteValidationError", None), type
        ):
            raise Hold("FROZEN_PRIMARY_ONLY_API_HOLD")
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
        if args.isolate_technical_failures:
            from r60_review_isolation_core import run_isolated

            retry_rows = rows
            if args.retry_baseline_dir is not None:
                from r60_glm4_b25_retry_contract import verify_baseline

                retry_rows, _original_positions = verify_baseline(
                    worker, rows, args.retry_baseline_dir, args.output_dir)
                emit("RETRY_SUBSET_READY", retry_count=len(retry_rows),
                     selected_from_original_25=True)
            snapshot_store = None
            if args.generation_snapshot_dir is not None:
                from r60_generation_snapshot import GenerationSnapshotStore

                snapshot_store = GenerationSnapshotStore(
                    args.generation_snapshot_dir, worker=worker,
                    model=MODEL, revision=REV,
                    runner_sha256=sha256_file(runner), emit=emit)
                emit("GENERATION_SNAPSHOT_ENABLED",
                     private_output_only=True, write_once=True)
            original_checkpoint_record = worker.checkpoint_record
            original_validate_response = worker.validate_response
            observed_counts = {}
            attempt_guard = None
            repair_telemetry = None
            if args.literal_probe_cases:
                from r60_glm4_repair_telemetry import RepairTelemetry

                repair_telemetry = RepairTelemetry(emit)
            if args.quote_match_observer:
                from r60_glm4_validation_observer import make_observer

                worker.validate_response = make_observer(
                    worker, retry_rows, emit, observed_counts)
                emit("VALIDATOR_OBSERVER_INSTALLED", target="VALIDATE_RESPONSE",
                     observation_only=True)

                def attempt_guard(pos):
                    if observed_counts.get(pos, 0) < 1:
                        emit("VALIDATOR_OBSERVER_COVERAGE_HOLD", position=pos)
                        raise Hold("VALIDATOR_OBSERVER_NOT_REACHED_HOLD")
            if args.quote_shape_diagnostic:
                from r60_glm4_b25_retry_contract import quote_shape_diagnostic

                worker.checkpoint_record = quote_shape_diagnostic(
                    worker, emit, repair=args.repair_quote_shape)
            if args.snapshot_primary_only:
                from r60_glm4_snapshot_primary_only import make_primary_only_checkpoint

                worker.checkpoint_record = make_primary_only_checkpoint(worker, emit)
                emit("SNAPSHOT_PRIMARY_ONLY_INSTALLED",
                     original_quote_validation_preserved=True,
                     secondary_model_repair_skipped=True)
            if args.quote_literal_repair:
                from r60_glm4_exact_quote_repair import make_reconciler

                worker.checkpoint_record = make_reconciler(
                    worker, repair_telemetry.record if repair_telemetry else emit)
                emit("QUOTE_LITERAL_REPAIR_INSTALLED",
                     strict_exact_revalidation=True, nonquote_fields_unchanged=True)
            try:
                result = run_isolated(
                    worker, retry_rows, args.output_dir, args.local_dir,
                    model=MODEL, revision=REV,
                    limit=args.case_limit, batch_size=args.batch_size,
                    max_model_len=args.max_model_len,
                    max_output_tokens=args.max_output_tokens,
                    wall_seconds=args.wall_seconds, resume=args.resume,
                    hf_tokenizer=AutoTokenizer, vllm=vllm,
                    attempt_diagnostic_guard=attempt_guard,
                    stop_after_attempts=(args.snapshot_probe_cases
                                         or args.literal_probe_cases or None),
                    generation_snapshot_store=snapshot_store)
            finally:
                worker.checkpoint_record = original_checkpoint_record
                worker.validate_response = original_validate_response
            if repair_telemetry is not None:
                repair_telemetry.summarize(
                    result["attempted"], result["verified"],
                    result["technical_failures"])
            if args.retry_baseline_dir is not None:
                emit("RETRY_COMBINED_ATTEMPT_SUMMARY",
                     baseline_verified=13, baseline_failed=12,
                     retry_attempted=result["attempted"],
                     retry_verified=result["verified"],
                     retry_technical_failures=result["technical_failures"],
                     combined_verified=13 + result["verified"],
                     combined_unverified=12 - result["verified"],
                     complete_verified_25=result["all_verified"],
                     original_receipts_modified=False)
            if args.snapshot_full25:
                emit("SNAPSHOT_FULL25_SUMMARY", attempted=result["attempted"],
                     verified=result["verified"],
                     technical_failures=result["technical_failures"],
                     snapshots_enabled=True,
                     original_positions_identity=True,
                     original_receipts_modified=False)
            # Retry-subset positions use verified baseline mapping; full25
            # positions are original positions, with independent new receipts.
            return 0 if result["all_verified"] else 42
        result = run_batches(
            worker, rows, args.output_dir, args.local_dir,
            limit=args.case_limit, batch_size=args.batch_size,
            max_model_len=args.max_model_len,
            max_output_tokens=args.max_output_tokens,
            wall_seconds=args.wall_seconds, resume=args.resume,
            hf_tokenizer=AutoTokenizer, vllm=vllm)
        return 0 if result["complete"] else 42
    except Exception as exc:  # noqa: BLE001 - only bounded status, no input
        emit("CONTINUOUS_REVIEW_HOLD",
             reason_code=str(exc) if isinstance(exc, Hold)
             else "REVIEW_RUNTIME_EXCEPTION_REDACTED")
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
