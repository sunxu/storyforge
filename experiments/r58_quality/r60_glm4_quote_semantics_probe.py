"""CPU-only AST inspection of GLM B25 frozen quote matching semantics.

Never imports or executes the private frozen runner. Output contains only
fixed allowlisted labels/booleans; no source code, literal content, quotes,
blind IDs, prompts or filename/path. Conservative: unknown is not guessed.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

SCHEMA = "storyforge_r60_glm4_quote_semantics_probe_safe_v1"
CODE = "MODEL_NONEXACT_QUOTE_HOLD"
WATCH = frozenset({
    "specific_source_quotes", "specific_target_quotes",
    "visible_history", "target_text", "source", "target",
})
SAFE_FUNCTIONS = frozenset({"validate_response", "checkpoint_record", "inference"})


class ProbeHold(ValueError):
    pass


def _raise_code(node: ast.Raise) -> bool:
    return (
        isinstance(node.exc, ast.Call)
        and any(isinstance(a, ast.Constant) and a.value == CODE
                for a in node.exc.args)
    )


def _matches(tree: ast.AST) -> list[ast.Compare]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)
    ]


def _label(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return "QUOTED_ITEM" if node.id in {"quote", "q", "item", "text", "snippet"} else (
            "SOURCE_BODY" if node.id in {"history", "body", "message", "content"} else
            "OTHER_VARIABLE"
        )
    if isinstance(node, ast.Subscript):
        key = node.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            if key.value == "target_text":
                return "TARGET_TEXT"
            if key.value == "content":
                return "MESSAGE_CONTENT"
        return "OTHER_SUBSCRIPT"
    if isinstance(node, ast.Attribute):
        if node.attr == "content":
            return "MESSAGE_CONTENT"
        return "OTHER_ATTRIBUTE"
    return "COMPOSITE_EXPRESSION"


def _named_field_refs(node: ast.AST) -> list[str]:
    found = set()
    for part in ast.walk(node):
        if (isinstance(part, ast.Constant) and isinstance(part.value, str)
                and part.value in WATCH):
            found.add(part.value)
    return sorted(found)


def _in_guard(guard: ast.AST) -> bool:
    return any(isinstance(p, ast.Compare)
               and any(isinstance(op, (ast.In, ast.NotIn)) for op in p.ops)
               for p in ast.walk(guard))


def _guard_features(guard: ast.AST) -> dict:
    compares = _matches(guard)
    membership = []
    for comp in compares:
        for op, rhs in zip(comp.ops, comp.comparators):
            if isinstance(op, (ast.In, ast.NotIn)):
                membership.append({
                    "operator": "NOT_IN" if isinstance(op, ast.NotIn) else "IN",
                    "left_role": _label(comp.left),
                    "right_role": _label(rhs),
                })
    calls = {
        part.func.id for part in ast.walk(guard)
        if isinstance(part, ast.Call) and isinstance(part.func, ast.Name)
    }
    return {
        "has_membership": bool(membership),
        "memberships": membership,
        "uses_any": "any" in calls,
        "uses_all": "all" in calls,
        "uses_not": any(isinstance(part, ast.UnaryOp)
                        and isinstance(part.op, ast.Not) for part in ast.walk(guard)),
        "field_refs": _named_field_refs(guard),
        "has_generator": any(isinstance(part, (ast.GeneratorExp, ast.ListComp))
                             for part in ast.walk(guard)),
    }


def inspect(path: Path) -> dict:
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= 200_000):
        raise ProbeHold("RUNNER_PATH_HOLD")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ProbeHold("RUNNER_PARSE_HOLD") from exc
    functions = {node.name: node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name in SAFE_FUNCTIONS}
    if "validate_response" not in functions:
        raise ProbeHold("VALIDATOR_NOT_FOUND_HOLD")
    sites = []

    def visit(node: ast.AST, guards: tuple[ast.AST, ...]) -> None:
        if isinstance(node, ast.If):
            for child in node.body:
                visit(child, guards + (node.test,))
            # Else guard is negation and cannot be attributed to test true.
            for child in node.orelse:
                visit(child, guards + (ast.UnaryOp(op=ast.Not(), operand=node.test),))
            return
        if isinstance(node, ast.Raise) and _raise_code(node):
            if not guards:
                sites.append({"guard_kind": "UNCONDITIONAL", "fields": [],
                              "membership_predicates": []})
            else:
                features = _guard_features(guards[-1])
                sites.append({
                    "guard_kind": ("MEMBERSHIP" if _in_guard(guards[-1])
                                   else "INDIRECT_OR_OTHER"),
                    "fields": features["field_refs"],
                    "membership_predicates": features["memberships"],
                    "uses_any": features["uses_any"],
                    "uses_all": features["uses_all"],
                    "uses_not": features["uses_not"],
                    "has_generator": features["has_generator"],
                    "nesting_depth": len(guards),
                })
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        for child in ast.iter_child_nodes(node):
            visit(child, guards)

    for stmt in functions["validate_response"].body:
        visit(stmt, ())
    if len(sites) != 1:
        raise ProbeHold("UNEXPECTED_QUOTE_RAISE_SITES_HOLD")
    validator = functions["validate_response"]
    referenced = _named_field_refs(validator)
    return {
        "schema": SCHEMA,
        "status": "QUOTE_SEMANTICS_CPU_PASS",
        "frozen_runner_imported": False,
        "gpu_started": False,
        "private_values_emitted": False,
        "quote_raise_site_count": len(sites),
        "validator_field_references": referenced,
        "site": sites[0],
        "interpretation": "STATIC_ONLY_NO_RUNTIME_CAUSE_CLAIM",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runner", required=True, type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(inspect(args.runner), sort_keys=True))
        return 0
    except ProbeHold as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "QUOTE_SEMANTICS_CPU_HOLD",
            "reason_code": str(exc),
            "private_values_emitted": False, "gpu_started": False,
        }, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
