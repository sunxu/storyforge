"""CPU-only R60 GLM frozen runner control-flow inventory.

No source lines, strings, prompts, tokens, quotes or private values emitted.
This is static inspection of AST; it does not prove which branch was executed.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


class ProbeHold(ValueError):
    pass


def inspect_runner(path: Path) -> dict:
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= 200_000):
        raise ProbeHold("RUNNER_FILE_HOLD")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (UnicodeError, SyntaxError, OSError) as exc:
        raise ProbeHold("RUNNER_PARSE_HOLD") from exc
    funcs = {
        node.name: node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if "inference" not in funcs:
        raise ProbeHold("INFERENCE_NOT_FOUND_HOLD")
    def call_targets(fn: str) -> set[str]:
        if fn not in funcs:
            return set()
        return {
            call.func.id for call in ast.walk(funcs[fn])
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        }
    inference = call_targets("inference")
    checkpoint = call_targets("checkpoint_record")
    validator = call_targets("validate_response")
    repairs = call_targets("repair_generated_quotes")
    classes = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    checks = {
        "inference_calls_checkpoint_record":
            "checkpoint_record" in inference,
        "inference_calls_validate_response":
            "validate_response" in inference,
        "inference_calls_repair_generated_quotes":
            "repair_generated_quotes" in inference,
        "checkpoint_record_calls_validate_response":
            "validate_response" in checkpoint,
        "has_direct_validate_response":
            "validate_response" in funcs,
        "has_quote_validation_error_class":
            "QuoteValidationError" in classes,
        "has_repair_generated_quotes":
            "repair_generated_quotes" in funcs,
        "repair_calls_validate_response":
            "validate_response" in repairs,
        "validate_response_recurses":
            "validate_response" in validator,
    }
    # Detect whether old wrapper hooks reach frozen functions.
    current_hook_reachable = checks["inference_calls_checkpoint_record"]
    result = {
        "schema": "storyforge_r60_glm4_runner_route_probe_safe_v1",
        "status": "RUNNER_ROUTE_CPU_INSPECT_PASS",
        "private_values_emitted": False,
        "gpu_started": False,
        "frozen_runner_imported": False,
        "checks": checks,
        "old_checkpoint_record_hook_reachable": current_hook_reachable,
        "recommended_next_step": (
            "CHECK_EXCEPTION_CLASS_AND_VALIDATE_RESPONSE_PATH"
            if current_hook_reachable else
            "OLD_CHECKPOINT_RECORD_HOOK_CANNOT_OBSERVE_INFERENCE"
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_runner(args.runner), sort_keys=True))
        return 0
    except ProbeHold as exc:
        print(json.dumps({
            "schema": "storyforge_r60_glm4_runner_route_probe_safe_v1",
            "status": "RUNNER_ROUTE_CPU_INSPECT_HOLD",
            "reason_code": str(exc),
            "private_values_emitted": False,
            "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
