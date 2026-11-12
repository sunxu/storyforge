"""CPU-only AST literal pair probe for frozen GLM quote-to-text scopes.

No imports or execution of private runner. Emits fixed labels only.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

SCHEMA = "storyforge_r60_glm4_quote_pair_probe_safe_v1"
KEYS = {
    "specific_source_quotes": "SOURCE_QUOTES",
    "specific_target_quotes": "TARGET_QUOTES",
    "visible_history": "HISTORY",
    "target_text": "TARGET_TEXT",
    "content": "MESSAGE_CONTENT",
}


class ProbeHold(ValueError):
    pass


def field_labels(node: ast.AST) -> set[str]:
    return {
        KEYS[n.value] for n in ast.walk(node)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and n.value in KEYS
    }


def assignments(func: ast.FunctionDef) -> dict[str, list[ast.AST]]:
    result: dict[str, list[ast.AST]] = {}
    for node in ast.walk(func):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    result.setdefault(target.id, []).append(node.value)
    return result


def provenance(expr: ast.AST, binds: dict[str, list[ast.AST]],
               trail: frozenset[str] = frozenset(), depth: int = 0) -> set[str]:
    if depth >= 8:
        return {"UNKNOWN"}
    labels = field_labels(expr)
    for node in ast.walk(expr):
        if isinstance(node, ast.Name) and node.id not in trail:
            for bound in binds.get(node.id, [])[:8]:
                labels.update(provenance(bound, binds, trail | {node.id}, depth + 1))
    return labels or {"UNKNOWN"}


def inspect_runner(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 200000:
        raise ProbeHold("RUNNER_PATH_HOLD")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ProbeHold("RUNNER_PARSE_HOLD") from exc
    validators = [n for n in tree.body
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "validate_response"]
    if len(validators) != 1:
        raise ProbeHold("VALIDATOR_COUNT_HOLD")
    binds = assignments(validators[0])
    result = []
    for node in ast.walk(validators[0]):
        if not isinstance(node, (ast.Tuple, ast.List)) or len(node.elts) != 2:
            continue
        key, body = node.elts
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            continue
        field = KEYS.get(key.value)
        if field not in {"SOURCE_QUOTES", "TARGET_QUOTES"}:
            continue
        labels = provenance(body, binds)
        history = bool(labels & {"HISTORY", "MESSAGE_CONTENT"})
        target = "TARGET_TEXT" in labels
        scope = ("MIXED_OR_AMBIGUOUS" if history and target else
                 "HISTORY" if history else "TARGET_TEXT" if target else "UNKNOWN")
        entry = {"field": field, "candidate_body_scope": scope,
                 "body_provenance": sorted(labels)}
        if entry not in result:
            result.append(entry)
    return {
        "schema": SCHEMA, "status": "QUOTE_PAIR_CPU_PASS",
        "frozen_runner_imported": False, "gpu_started": False,
        "private_values_emitted": False,
        "pair_count": len(result), "pairings": result,
        "source_pair_found": any(x["field"] == "SOURCE_QUOTES" for x in result),
        "target_pair_found": any(x["field"] == "TARGET_QUOTES" for x in result),
        "interpretation": "STATIC_LITERAL_PAIR_CANDIDATES_ONLY",
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
            "schema": SCHEMA, "status": "QUOTE_PAIR_CPU_HOLD",
            "reason_code": str(exc), "private_values_emitted": False,
            "gpu_started": False}, sort_keys=True))
        return 42


if __name__ == "__main__":
    raise SystemExit(main())
