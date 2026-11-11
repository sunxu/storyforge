"""Inspect GLM REJECT predicate sites without importing the frozen runner.

This is a static locator, not a causal explanation of quality decisions.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

SCHEMA = "storyforge_r60_glm_reject_gate_ast_safe_v1"
OPS = {
    ast.Eq: "EQ",
    ast.NotEq: "NOT_EQ",
    ast.Gt: "GT",
    ast.GtE: "GE",
    ast.Lt: "LT",
    ast.LtE: "LE",
    ast.In: "IN",
    ast.NotIn: "NOT_IN",
    ast.Is: "IS",
    ast.IsNot: "IS_NOT",
}
SECTIONS = {"validate_response", "checkpoint_record", "response_schema"}


def check(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 200000:
        raise ValueError("RUNNER_SCOPE_HOLD")

    tree = ast.parse(path.read_bytes(), filename="<private_runner>")
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in SECTIONS
    ]
    found = []
    for function in functions:
        reject_lines = {
            node.lineno
            for node in ast.walk(function)
            if isinstance(node, ast.Constant) and node.value == "REJECT"
        }
        predicates = []
        for node in ast.walk(function):
            if not isinstance(node, ast.If):
                continue
            if not any(
                isinstance(child, ast.Constant) and child.value == "REJECT"
                for child in ast.walk(node)
            ):
                continue
            comparators = sorted(
                {
                    OPS[type(operator)]
                    for test in ast.walk(node.test)
                    if isinstance(test, ast.Compare)
                    for operator in test.ops
                    if type(operator) in OPS
                }
            )
            predicates.append(
                {
                    "line": node.lineno,
                    "node": type(node.test).__name__,
                    "comparators": comparators,
                }
            )
        found.append(
            {
                "function": function.name,
                "reject_literal_sites": len(reject_lines),
                "reject_literal_lines": sorted(reject_lines),
                "reject_scope_predicates": predicates,
            }
        )
    return {
        "schema": SCHEMA,
        "status": "GLM_REJECT_GATE_AST_PASS",
        "static_only": True,
        "runner_imported": False,
        "gpu_started": False,
        "private_values_emitted": False,
        "functions": found,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        print(json.dumps(check(arguments.runner), sort_keys=True))
        return 0
    except (OSError, ValueError, SyntaxError, UnicodeError):
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "status": "GLM_REJECT_GATE_AST_HOLD",
                    "gpu_started": False,
                    "private_values_emitted": False,
                }
            )
        )
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
