"""R60 GLM: CPU-only symbolic binding trace for frozen quote validator.

Never import, execute, or print frozen source. This is a conservative static
analysis: only approved labels and boolean flags are returned. Unknown alias
provenance stays UNKNOWN; never presume exact runtime cause.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

SCHEMA = "storyforge_r60_glm4_quote_binding_probe_safe_v1"
ERROR = "MODEL_NONEXACT_QUOTE_HOLD"
FIELDS = {"specific_source_quotes", "specific_target_quotes",
          "visible_history", "target_text"}
SAFE_KEYS = {
    "specific_source_quotes": "SOURCE_QUOTE_FIELD",
    "specific_target_quotes": "TARGET_QUOTE_FIELD",
    "visible_history": "VISIBLE_HISTORY",
    "target_text": "TARGET_TEXT",
}
SOURCE_LABELS = {"VISIBLE_HISTORY", "MESSAGE_CONTENT"}
TARGET_LABELS = {"TARGET_TEXT"}
SAFE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


class ProbeHold(ValueError):
    pass


def _raise_matches(node: ast.AST) -> bool:
    return isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and any(
        isinstance(a, ast.Constant) and a.value == ERROR
        for a in node.exc.args
    )


def _field_labels(node: ast.AST) -> set[str]:
    labels: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            if n.value in SAFE_KEYS:
                labels.add(SAFE_KEYS[n.value])
            elif n.value == "content":
                labels.add("MESSAGE_CONTENT")
    return labels


def _bindings(func: ast.AST) -> dict[str, list[ast.AST]]:
    result: dict[str, list[ast.AST]] = {}

    def targets(target: ast.AST):
        if isinstance(target, ast.Name):
            yield target.id
        elif isinstance(target, (ast.Tuple, ast.List)):
            for child in target.elts:
                yield from targets(child)

    for node in ast.walk(func):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not func:
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for target in (node.targets if isinstance(node, ast.Assign)
                           else [node.target]):
                for name in targets(target):
                    if node.value is not None:
                        result.setdefault(name, []).append(node.value)
        elif isinstance(node, (ast.For, ast.comprehension)):
            for name in targets(node.target):
                result.setdefault(name, []).append(node.iter)
        elif isinstance(node, ast.NamedExpr):
            for name in targets(node.target):
                result.setdefault(name, []).append(node.value)
    return result


def _provenance(node: ast.AST, binds: dict[str, list[ast.AST]],
                visiting: frozenset[str] = frozenset(),
                depth: int = 0) -> set[str]:
    if depth > 7:
        return {"UNKNOWN"}
    labels = _field_labels(node)
    # Resolve symbolic aliases. For comprehensions, loop target binding to iter
    # is intentionally conservative; it proves an origin, not runtime type.
    for part in ast.walk(node):
        if not isinstance(part, ast.Name):
            continue
        name = part.id
        if name in visiting or name not in binds:
            continue
        for expr in binds[name][:12]:
            labels |= _provenance(expr, binds, visiting | {name}, depth + 1)
    return labels or {"UNKNOWN"}


def inspect_runner(path: Path) -> dict:
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= 200_000):
        raise ProbeHold("RUNNER_PATH_HOLD")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ProbeHold("RUNNER_PARSE_HOLD") from exc
    validators = [n for n in tree.body if isinstance(n, SAFE_NODES)
                  and n.name == "validate_response"]
    if len(validators) != 1:
        raise ProbeHold("VALIDATOR_COUNT_HOLD")
    func = validators[0]
    binds = _bindings(func)
    raise_sites = [n for n in ast.walk(func) if _raise_matches(n)]
    if len(raise_sites) != 1:
        raise ProbeHold("RAISE_SITE_COUNT_HOLD")
    guard = None
    target = raise_sites[0]
    # Narrow to a direct enclosing if guard; no private source emitted.
    for parent in ast.walk(func):
        if isinstance(parent, ast.If) and any(
            n is target for sub in parent.body for n in ast.walk(sub)
        ):
            guard = parent.test
    if guard is None:
        raise ProbeHold("GUARD_NOT_FOUND_HOLD")
    comparisons = [n for n in ast.walk(guard)
                   if isinstance(n, ast.Compare)]
    membership = []
    for comp in comparisons:
        left = comp.left
        for op, right in zip(comp.ops, comp.comparators):
            if not isinstance(op, (ast.In, ast.NotIn)):
                left = right
                continue
            lhs = sorted(_provenance(left, binds))
            rhs = sorted(_provenance(right, binds))
            rhs_set = set(rhs)
            right_scope = (
                "HISTORY_OR_MESSAGE" if rhs_set & SOURCE_LABELS
                and not rhs_set & TARGET_LABELS else
                "TARGET_TEXT" if rhs_set & TARGET_LABELS
                and not rhs_set & SOURCE_LABELS else
                "MIXED_HISTORY_TARGET" if rhs_set & SOURCE_LABELS
                and rhs_set & TARGET_LABELS else "UNKNOWN"
            )
            membership.append({
                "operator": "NOT_IN" if isinstance(op, ast.NotIn) else "IN",
                "left_provenance": lhs, "right_provenance": rhs,
                "right_scope": right_scope,
                "right_is_variable": isinstance(right, ast.Name),
                "rhs_binding_candidates": (
                    len(binds.get(right.id, [])) if isinstance(right, ast.Name)
                    else 0
                ),
            })
            left = right
    if not membership:
        raise ProbeHold("NO_MEMBERSHIP_COMPARISON_HOLD")
    direct_fields = sorted(_field_labels(guard))
    return {
        "schema": SCHEMA,
        "status": "QUOTE_BINDING_CPU_PASS",
        "frozen_runner_imported": False, "gpu_started": False,
        "private_values_emitted": False,
        "membership_count": len(membership),
        "membership": membership,
        "guard_direct_field_labels": direct_fields,
        "uses_any": any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "any" for n in ast.walk(guard)),
        "uses_negation": any(isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not)
                             for n in ast.walk(guard)),
        "interpretation": "STATIC_ALIAS_OVERAPPROX_NO_RUNTIME_CAUSE_CLAIM",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect_runner(args.runner), sort_keys=True))
        return 0
    except ProbeHold as exc:
        print(json.dumps({"schema": SCHEMA,
                          "status": "QUOTE_BINDING_CPU_HOLD",
                          "reason_code": str(exc), "gpu_started": False,
                          "private_values_emitted": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
