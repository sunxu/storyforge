"""One-engine B25 reviewer gate, with required verified first checkpoint.

Run beside the frozen B25 runner.py. No change to source cases, model,
sampling, rubric, output format or existing checkpoint validation.
First checkpoint must be fully verified before the runner proceeds.
"""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

SCHEMA = "storyforge_r60_b25_first_checkpoint_gate_safe_v1"
B_INPUT_SHA256 = "01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9"
B_MODEL = "zai-org/GLM-4-32B-0414"
B_REV = "8dea913c41b543527c2860fb6f3c15c202f24aeb"
EXPECTED_COUNT = 25


class GateHold(ValueError):
    pass


def emit(event: str, **data: object) -> None:
    print(json.dumps({"schema": SCHEMA, "event": event,
                      "private_values_emitted": False, **data},
                     sort_keys=True, separators=(",", ":")), flush=True)


def check_args(argv: list[str], source: Path) -> None:
    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--max-model-len", type=int, required=True)
    parser.add_argument("--max-output-tokens", type=int, required=True)
    parser.add_argument("--max-wall-seconds", type=int, required=True)
    parser.add_argument("--confirm-paid-gpu", action="store_true")
    params = parser.parse_args(argv)
    if (params.model != B_MODEL or params.revision != B_REV
            or (params.start, params.limit) != (1, EXPECTED_COUNT)
            or params.max_model_len != 32768
            or params.max_output_tokens != 2400
            or not 60 <= params.max_wall_seconds <= 5400
            or not params.confirm_paid_gpu
            or Path(params.input).resolve() !=
            (source.parent / "source.private.jsonl").resolve()):
        raise GateHold("B25_RUN_PARAMETERS_HOLD")
    # Output must be unique, empty and on its original writable mount.
    output = Path(params.output_dir)
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise GateHold("OUTPUT_NOT_EMPTY_HOLD")
    if source.is_symlink() or not source.is_file():
        raise GateHold("RUNNER_NOT_REGULAR_HOLD")
    input_path = Path(params.input)
    if input_path.is_symlink() or not input_path.is_file():
        raise GateHold("INPUT_NOT_REGULAR_HOLD")
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != B_INPUT_SHA256:
        raise GateHold("B25_INPUT_SHA_MISMATCH")


def install_gate(worker: object) -> dict:
    """Gate after the original immutable write and original read validator."""
    original_inference = worker.inference
    original_write = worker.write_checkpoint
    state = {"active": False, "first_verified": False,
             "verified_count": 0, "expected_pos": 1}

    def guarded_write(path: Path, record: dict) -> None:
        if not state["active"]:
            raise GateHold("WRITE_OUTSIDE_B25_INFERENCE")
        pos = state["expected_pos"]
        if pos > EXPECTED_COUNT:
            raise GateHold("EXTRA_CHECKPOINT_HOLD")
        if Path(path) != state["output"] / worker.checkpoint_name(pos):
            raise GateHold("CHECKPOINT_ORDER_HOLD")
        if record.get("position") != pos:
            raise GateHold("CHECKPOINT_POSITION_HOLD")
        # Original function enforces O_EXCL and fsync.
        original_write(path, record)
        # Original validator checks receipt hash, blind ID, input digest,
        # exact model/revision, policy and complete response semantics.
        validated = worker.read_checkpoint(
            Path(path), pos, state["rows"][pos - 1], B_MODEL, B_REV)
        if validated is None:
            raise GateHold("CHECKPOINT_READBACK_HOLD")
        state["verified_count"] += 1
        state["expected_pos"] += 1
        if pos == 1:
            state["first_verified"] = True
            emit("B25_FIRST_GATE_PASS", checkpoint_verified=1,
                 continue_without_reload=True)
        else:
            emit("B25_CHECKPOINT_VERIFIED", count=state["verified_count"])

    def gated_inference(*args, **kwargs):
        bound = inspect.signature(original_inference).bind(*args, **kwargs)
        bound.apply_defaults()
        d = bound.arguments
        if (len(d["rows"]) != EXPECTED_COUNT
                or d["model"] != B_MODEL or d["revision"] != B_REV
                or (d["start"], d["limit"]) != (1, EXPECTED_COUNT)):
            raise GateHold("INFERENCE_CONTRACT_HOLD")
        output = d["output"]
        if not output.is_dir() or any(output.iterdir()):
            raise GateHold("INFERENCE_OUTPUT_NONEMPTY_HOLD")
        state["rows"] = d["rows"]
        state["output"] = output
        state["active"] = True
        try:
            result = original_inference(*args, **kwargs)
            if not state["first_verified"]:
                raise GateHold("FIRST_CHECKPOINT_NOT_VERIFIED")
            if state["verified_count"] != EXPECTED_COUNT:
                raise GateHold("B25_PARTIAL_RESULT_HOLD")
            emit("B25_ALL_VERIFIED", count=state["verified_count"],
                 engine_load_count=1)
            return result
        finally:
            state["active"] = False

    worker.write_checkpoint = guarded_write
    worker.inference = gated_inference
    return state


def main() -> int:
    runner = Path(__file__).resolve().parent / "runner.py"
    try:
        check_args(sys.argv[1:], runner)
        spec = importlib.util.spec_from_file_location("r60_b25_frozen_runner", runner)
        if spec is None or spec.loader is None:
            raise GateHold("IMPORT_SPEC_HOLD")
        sys.path.insert(0, str(runner.parent))
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        for item in ("inference", "write_checkpoint", "read_checkpoint",
                     "checkpoint_name", "main"):
            if not callable(getattr(worker, item, None)):
                raise GateHold("RUNNER_API_HOLD")
        install_gate(worker)
        emit("B25_GATE_READY", cases_total=EXPECTED_COUNT,
             model_pinned=True, revision_pinned=True)
        return int(worker.main())
    except Exception as exc:  # noqa: BLE001 - never print private error or stack
        reason = str(exc) if isinstance(exc, GateHold) else "RUNNER_EXCEPTION_REDACTED"
        emit("B25_GATE_HOLD", reason_code=reason)
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
