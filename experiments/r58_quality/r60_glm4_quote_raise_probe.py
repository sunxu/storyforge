"""CPU-only inspection of exact MODEL_NONEXACT_QUOTE_HOLD raise guards.

Does not import/execute frozen code. Does not emit source, quote text, private
values, code fragments or line numbers. Only approved AST feature labels.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

CODE = "MODEL_NONEXACT_QUOTE_HOLD"


class ProbeHold(ValueError):
    pass


def _contains(node: ast.AST, kind: type) -> bool:
    return any(isinstance(part, kind) for part in ast.walk(node))


def _names(node: ast.AST) -> set[str]:
    return {
        part.id for part in ast.walk(node)
        if isinstance(part, ast.Name)
    }


def _calls(node: ast.AST) -> set[str]:
    return {
        part.func.id for part in ast.walk(node)
        if isinstance(part, ast.Call) and isinstance(part.func, ast.Name)
        and part.func.id in {"len", "isinstance", "any", "all", "str"}
    }


def _category(guard: ast.AST | None) -> str:
    if guard is None:
        return "UNCONDITIONAL_OR_UNKNOWN"
    features = _calls(guard)
    names = _names(guard)
    uses_membership = _contains(guard, ast.In) or _contains(guard, ast.NotIn)
    uses_limit = bool(features & {"len"})
    uses_type = "isinstance" in features
    if uses_membership:
        return "MEMBERSHIP_OR_TEXT_MATCH"
    if uses_type and uses_limit:
        return "TYPE_AND_LENGTH"
    if uses_type:
        return "TYPE_CHECK"
    if uses_limit:
        return "LENGTH_CHECK"
    if names & {"quote", "quotes", "histories", "bodies", "source", "target"}:
        return "QUOTE_RELATED_OTHER"
    return "OTHER_GUARD"


def _raise_code(node: ast.Raise) -> bool:
    expr = node.exc
    if not isinstance(expr, ast.Call):
        return False
    return any(
        isinstance(argument, ast.Constant) and argument.value == CODE
        for argument in expr.args
    )


def inspect_runner(path: Path) -> dict:
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= 200_000):
        raise ProbeHold("RUNNER_FILE_HOLD")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (UnicodeError, SyntaxError, OSError) as exc:
        raise ProbeHold("RUNNER_PARSE_HOLD") from exc
    sites: list[dict] = []
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for function in functions:
        if function.name not in {
            "validate_response", "checkpoint_record", "inference",
        }:
            continue
        function_name = function.name

        def visit(node: ast.AST, guards: tuple[ast.AST, ...]) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return
            if isinstance(node, ast.If):
                visit(node.test, guards)
                visit(node.body[0], guards + (node.test,)) if node.body else None
                for child in node.body[1:]:
                    visit(child, guards + (node.test,))
                for child in node.orelse:
                    visit(child, guards)
                return
            if isinstance(node, ast.Raise) and _raise_code(node):
                sites.append({
                    "function": function_name,
                    "guard_category": _category(guards[-1] if guards else None),
                    "guard_depth": len(guards),
                })
                return
            for child in ast.iter_child_nodes(node):
                visit(child, guards)

        for statement in function.body:
            visit(statement, ())
    categories = sorted({item["guard_category"] for item in sites})
    return {
        "schema": "storyforge_r60_glm4_quote_raise_probe_safe_v1",
        "status": "QUOTE_RAISE_CPU_INSPECT_PASS",
        "private_values_emitted": False,
        "frozen_runner_imported": False,
        "gpu_started": False,
        "raise_site_count": len(sites),
        "guard_categories": categories,
        "sites": sites,
        "direct_quote_error_possible":
            any(item["function"] == "validate_response" for item in sites),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_runner(args.runner), sort_keys=True))
        return 0
    except ProbeHold as exc:
        print(json.dumps({
            "schema": "storyforge_r60_glm4_quote_raise_probe_safe_v1",
            "status": "QUOTE_RAISE_CPU_INSPECT_HOLD",
            "reason_code": str(exc),
            "private_values_emitted": False,
            "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
