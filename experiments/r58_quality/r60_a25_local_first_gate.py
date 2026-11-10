"""A25: one real vLLM instance, locally validated Qwen weights, first-case gate.

Invoked beside a frozen copy of input_A/{runner.py,source.private.jsonl,...}.
The original reviewer still receives the immutable model/revision and writes
original checkpoint IDs. Only its runtime model/tokenizer loads are redirected
to previously verified local weights, without changing sampling or schema.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path

SCHEMA = "storyforge_r60_a25_local_first_gate_safe_v1"
MODEL = "Qwen/Qwen3-32B"
REV = "9216db5781bf21249d130ec9da846c4624c16137"
INPUT_SHA = "492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069"
COUNT = 25
MANIFEST_NAME = "r60_weights_verified_manifest.json"


class Hold(ValueError):
    pass


def emit(event: str, **fields: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **fields},
                     sort_keys=True, separators=(",", ":")), flush=True)


def validate_bundle(runner: Path, argv: list[str], local: Path) -> None:
    parser = argparse.ArgumentParser(add_help=False)
    for item in ("input", "output-dir", "model", "revision"):
        parser.add_argument(f"--{item}", required=True)
    for item in ("start", "limit", "max-model-len",
                 "max-output-tokens", "max-wall-seconds"):
        parser.add_argument(f"--{item}", type=int, required=True)
    parser.add_argument("--confirm-paid-gpu", action="store_true")
    args = parser.parse_args(argv)
    if (args.model != MODEL or args.revision != REV or
            (args.start, args.limit, args.max_model_len,
             args.max_output_tokens) != (1, COUNT, 32768, 2400)
            or not 60 <= args.max_wall_seconds <= 5400
            or not args.confirm_paid_gpu):
        raise Hold("A25_ARGS_HOLD")
    input_path = Path(args.input)
    output = Path(args.output_dir)
    if (input_path != runner.parent / "source.private.jsonl"
            or input_path.is_symlink() or not input_path.is_file()
            or runner.is_symlink() or not runner.is_file()):
        raise Hold("A25_INPUT_PATH_HOLD")
    if (output.is_symlink() or not output.is_dir() or any(output.iterdir())):
        raise Hold("A25_OUTPUT_NOT_EMPTY_HOLD")
    with input_path.open("rb") as stream:
        h = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != INPUT_SHA:
        raise Hold("A25_INPUT_SHA_HOLD")
    if (not local.is_absolute() or local.is_symlink()
            or not local.is_dir() or local.resolve() == runner.parent.resolve()):
        raise Hold("A25_LOCAL_MODEL_PATH_HOLD")
    mf = local / MANIFEST_NAME
    if mf.is_symlink() or not mf.is_file():
        raise Hold("A25_LOCAL_MANIFEST_MISSING")
    try:
        data = json.loads(mf.read_bytes())
    except (ValueError, OSError) as exc:
        raise Hold("A25_LOCAL_MANIFEST_INVALID") from exc
    if (data.get("model") != MODEL or data.get("revision") != REV
            or not isinstance(data.get("files"), list)
            or not data["files"]):
        raise Hold("A25_LOCAL_MANIFEST_INVALID")
    names = {v.get("name") for v in data["files"] if isinstance(v, dict)}
    if not {"config.json", "tokenizer.json",
            "model.safetensors.index.json"}.issubset(names):
        raise Hold("A25_LOCAL_MANIFEST_INVALID")
    # The earlier same-job localizer performs upstream per-shard SHA checking;
    # this gate must never accept a bare bucket path as a verified model.
    if not all((local / n).is_file() for n in names if isinstance(n, str)):
        raise Hold("A25_LOCAL_FILES_MISSING")


def install_first_gate(worker: object, local: Path,
                       transformers: object, vllm: object) -> dict:
    original_inference = worker.inference
    original_write = worker.write_checkpoint
    original_tokenizer = transformers.AutoTokenizer.from_pretrained
    original_llm = vllm.LLM
    state = {"active": False, "validated": 0, "load_count": 0,
             "first_pass": False}

    def local_tokenizer(model: str, *args, **kwargs):
        if model != MODEL or kwargs.get("revision") != REV:
            raise Hold("A25_TOKENIZER_CONTRACT_HOLD")
        kwargs.pop("revision")
        emit("A25_LOCAL_TOKENIZER_LOAD")
        return original_tokenizer(str(local), *args, **kwargs)

    def local_llm(*args, **kwargs):
        if args or kwargs.get("model") != MODEL or kwargs.get("revision") != REV:
            raise Hold("A25_LLM_CONTRACT_HOLD")
        if kwargs.get("tokenizer_revision") != REV or state["load_count"] != 0:
            raise Hold("A25_MODEL_RELOAD_HOLD")
        kwargs = dict(kwargs)
        kwargs["model"] = str(local)
        kwargs["tokenizer"] = str(local)
        kwargs.pop("revision")
        kwargs.pop("tokenizer_revision")
        state["load_count"] += 1
        emit("A25_REAL_LOCAL_ENGINE_START")
        result = original_llm(**kwargs)
        emit("A25_REAL_LOCAL_ENGINE_READY", engine_load_count=state["load_count"])
        return result

    def guarded_write(path: Path, record: dict) -> None:
        if not state["active"]:
            raise Hold("A25_WRITE_OUTSIDE_INFERENCE")
        pos = state["validated"] + 1
        if pos > COUNT or (Path(path) !=
                           state["output"] / worker.checkpoint_name(pos)
                           or record.get("position") != pos):
            raise Hold("A25_CHECKPOINT_SEQUENCE_HOLD")
        original_write(path, record)
        validated = worker.read_checkpoint(
            Path(path), pos, state["rows"][pos - 1], MODEL, REV)
        if validated is None:
            raise Hold("A25_CHECKPOINT_READBACK_HOLD")
        state["validated"] = pos
        if pos == 1:
            state["first_pass"] = True
            emit("A25_FIRST_GATE_PASS", verified=1,
                 continue_without_reload=True)
        else:
            emit("A25_CHECKPOINT_VERIFIED", count=pos)

    def inference(*args, **kwargs):
        bound = inspect.signature(original_inference).bind(*args, **kwargs)
        bound.apply_defaults()
        vals = bound.arguments
        if (len(vals["rows"]) != COUNT or vals["model"] != MODEL
                or vals["revision"] != REV
                or (vals["start"], vals["limit"]) != (1, COUNT)):
            raise Hold("A25_INFERENCE_CONTRACT_HOLD")
        output = vals["output"]
        if not output.is_dir() or any(output.iterdir()):
            raise Hold("A25_INFERENCE_OUTPUT_HOLD")
        state.update({"active": True, "rows": vals["rows"], "output": output})
        transformers.AutoTokenizer.from_pretrained = staticmethod(local_tokenizer)
        vllm.LLM = local_llm
        try:
            result = original_inference(*args, **kwargs)
            if (not state["first_pass"] or state["validated"] != COUNT
                    or state["load_count"] != 1):
                raise Hold("A25_INCOMPLETE_HOLD")
            emit("A25_ALL_VERIFIED", count=COUNT, engine_load_count=1)
            return result
        finally:
            state["active"] = False
            transformers.AutoTokenizer.from_pretrained = staticmethod(
                original_tokenizer)
            vllm.LLM = original_llm

    worker.write_checkpoint = guarded_write
    worker.inference = inference
    return state


def main() -> int:
    runner = Path(__file__).resolve().parent / "runner.py"
    local_value = os.environ.get("R60_A25_LOCAL_MODEL_DIR", "")
    try:
        local = Path(local_value) if local_value else Path(".")
        validate_bundle(runner, sys.argv[1:], local)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        spec = importlib.util.spec_from_file_location("r60_frozen_a25", runner)
        if spec is None or spec.loader is None:
            raise Hold("A25_RUNNER_IMPORT_HOLD")
        sys.path.insert(0, str(runner.parent))
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        for method in ("inference", "write_checkpoint", "read_checkpoint",
                       "checkpoint_name", "main"):
            if not callable(getattr(worker, method, None)):
                raise Hold("A25_RUNNER_API_HOLD")
        import transformers
        import vllm

        install_first_gate(worker, local, transformers, vllm)
        emit("A25_GATE_READY", cases_total=COUNT,
             local_weights=True, model_pinned=True)
        return int(worker.main())
    except Exception as exc:  # noqa: BLE001 - never leak paths or private text
        reason = str(exc) if isinstance(exc, Hold) else "A25_RUNTIME_REDACTED"
        emit("A25_GATE_HOLD", reason_code=reason)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
