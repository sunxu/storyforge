"""Create a private, traced copy of a prepared R60 pilot A input bundle.

CPU only. Does not modify source stage, original runner, model parameters,
prompts, checkpoints, or any source case. Instruments bounded AST statements
in inference() and rejects unexpected runner structure.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

EXPECTED_A_INPUT_SHA256 = "492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069"
SLOT_FILES = ("runner.py", "source.private.jsonl", "token_core.py",
              "runtime_inputs.py", "runtime_resources.py",
              "r60_pilot_diagnostic_launcher.py")
EXPECTED = {"tokenizer": 1, "encode": 1, "engine": 1, "params": 1, "generate": 1}
SCHEMA = "storyforge_r60_pilot_trace_prepare_safe_v1"


class Hold(ValueError):
    pass


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def read_private(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise Hold("PRIVATE_SOURCE_FILE_HOLD")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise Hold("PRIVATE_FILE_MODE_HOLD")
    if not 0 < path.stat().st_size <= 64 * 1024 * 1024:
        raise Hold("PRIVATE_FILE_SIZE_HOLD")
    return path.read_bytes()


def check_dir(path: Path) -> None:
    if path.is_symlink() or not path.is_dir() or stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise Hold("PRIVATE_DIR_MODE_HOLD")


def new_file(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as fp:
        fp.write(data)
        fp.flush()
        os.fsync(fp.fileno())


def classify(node: ast.stmt) -> str | None:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return None
    value = node.value
    if not isinstance(value, ast.Call):
        return None
    fn = value.func
    if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
        if fn.value.id == "AutoTokenizer" and fn.attr == "from_pretrained":
            return "tokenizer"
        if fn.value.id == "engine" and fn.attr == "generate":
            return "generate"
    if isinstance(fn, ast.Name):
        if fn.id == "encode_chat":
            return "encode"
        if fn.id == "LLM":
            return "engine"
        if fn.id == "SamplingParams":
            return "params"
    return None


EVENTS = {
    "tokenizer": ("TOKENIZER_LOAD_START", "TOKENIZER_LOADED"),
    "encode": ("TOKEN_ENCODING_START", "TOKEN_ENCODING_DONE"),
    "engine": ("ENGINE_INIT_START", "ENGINE_READY"),
    "params": ("SAMPLING_PARAMS_START", "SAMPLING_PARAMS_READY"),
    "generate": ("GENERATE_START", "GENERATE_DONE"),
}


def marker(name: str) -> ast.stmt:
    return ast.Expr(value=ast.Call(
        func=ast.Name(id="_r60_diag_event", ctx=ast.Load()),
        args=[ast.Constant(value=name)], keywords=[]))


def instrument(source: str) -> tuple[str, dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise Hold("RUNNER_SYNTAX_HOLD") from exc
    target = next((n for n in tree.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == "inference"), None)
    if not isinstance(target, ast.FunctionDef):
        raise Hold("INFERENCE_FUNCTION_HOLD")
    matches = Counter()

    def visit_body(statements: list[ast.stmt]) -> list[ast.stmt]:
        rewritten = []
        for node in statements:
            kind = classify(node)
            if kind is not None:
                matches[kind] += 1
                rewritten.append(marker(EVENTS[kind][0]))
                rewritten.append(node)
                rewritten.append(marker(EVENTS[kind][1]))
            else:
                for field, value in ast.iter_fields(node):
                    if isinstance(value, list) and value and all(
                        isinstance(item, ast.stmt) for item in value
                    ):
                        setattr(node, field, visit_body(value))
                rewritten.append(node)
        return rewritten

    target.body = visit_body(target.body)
    if dict(matches) != EXPECTED:
        raise Hold("INFERENCE_ANCHOR_COUNT_HOLD")
    # Allowlisted marker function is supplied only by the external launcher.
    ast.fix_missing_locations(tree)
    patched = ast.unparse(tree) + "\n"
    ast.parse(patched)
    return patched, dict(matches)


def prepare(source_dir: Path, destination: Path) -> dict:
    check_dir(source_dir)
    check_dir(destination.parent)
    if source_dir == destination or source_dir.is_relative_to(destination) or destination.is_relative_to(source_dir):
        raise Hold("SOURCE_DESTINATION_OVERLAP_HOLD")
    if destination.exists() or destination.is_symlink():
        raise Hold("DEST_EXISTS_HOLD")
    raw = {name: read_private(source_dir / name) for name in SLOT_FILES}
    if digest(raw["source.private.jsonl"]) != EXPECTED_A_INPUT_SHA256:
        raise Hold("PILOT_A_INPUT_SHA_MISMATCH")
    lines = raw["source.private.jsonl"].splitlines()
    if len(lines) != 25:
        raise Hold("PILOT_A_COUNT_HOLD")
    try:
        runner = raw["runner.py"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Hold("RUNNER_ENCODING_HOLD") from exc
    if ("from vllm.sampling_params import GuidedDecodingParams" not in runner
            or "structured_outputs=" in runner):
        raise Hold("RUNNER_VLLM0100_API_HOLD")
    patched, anchors = instrument(runner)
    raw["runner.py"] = patched.encode("utf-8")

    destination.mkdir(mode=0o700)
    for name, blob in raw.items():
        new_file(destination / name, blob)
    return {
        "schema": SCHEMA,
        "status": "R60_TRACE_A25_PRIVATE_READY__NO_GPU",
        "cases_total": 25,
        "input_sha256": digest(raw["source.private.jsonl"]),
        "original_runner_sha256": digest(runner.encode("utf-8")),
        "traced_runner_sha256": digest(raw["runner.py"]),
        "anchors": anchors,
        "original_unchanged": True,
        "hf_jobs_submitted": 0,
        "gpu_started": False,
        "private_values_emitted": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--dest-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = prepare(args.source_dir, args.dest_dir)
        rc = 0
    except (Hold, OSError, ValueError) as exc:
        result = {
            "schema": SCHEMA, "status": "R60_TRACE_A25_PREPARE_HOLD",
            "reason_code": str(exc) if isinstance(exc, Hold) else "IO_OR_VALUE_HOLD",
            "hf_jobs_submitted": 0, "gpu_started": False,
            "private_values_emitted": False,
        }
        rc = 42
    print(json.dumps(result, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
