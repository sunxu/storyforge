"""R60 GLM: CPU-only inspect frozen REJECT decision predicates, no source values.

Run on Owner Mac. Static AST scan only, no import of frozen runner; prints only
allowlisted counts and AST node families. Not proof of runtime causality.
"""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path

SCHEMA = "storyforge_r60_glm_reject_gate_ast_safe_v1"
OPS = {ast.Eq:"EQ", ast.NotEq:"NOT_EQ", ast.Gt:"GT", ast.GtE:"GE",
       ast.Lt:"LT", ast.LtE:"LE", ast.In:"IN", ast.NotIn:"NOT_IN",
       ast.Is:"IS", ast.IsNot:"IS_NOT"}
SECTIONS = {"validate_response", "checkpoint_record", "response_schema"}

def check(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 200000:
        raise ValueError("RUNNER_SCOPE_HOLD")
    tree = ast.parse(path.read_bytes(), filename="<private_runner>")
    functions = [n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name in SECTIONS]
    found = []
    for fun in functions:
        reject_lines = set()
        for n in ast.walk(fun):
            if isinstance(n, ast.Constant) and n.value == "REJECT":
                reject_lines.add(n.lineno)
        predicates = []
        for n in ast.walk(fun):
            if isinstance(n, ast.If) and any(
                isinstance(c, ast.Constant) and c.value == "REJECT"
                for c in ast.walk(n)
            ):
                predicates.append({
                    "line": n.lineno, "node": type(n.test).__name__,
                    "comparators": sorted({
                        OPS[type(op)] for x in ast.walk(n.test)
                        if isinstance(x, ast.Compare) for op in x.ops
                        if type(op) in OPS
                    })
                })
        found.append({"function":fun.name, "reject_literal_sites":len(reject_lines),
                      "reject_literal_lines":sorted(reject_lines),
                      "reject_scope_predicates":predicates})
    return {"schema":SCHEMA, "status":"GLM_REJECT_GATE_AST_PASS",
            "static_only":True, "runner_imported":False,
            "gpu_started":False, "private_values_emitted":False,
            "functions":found, "quality_v1_admitted":0,
            "training_authorized":False}

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--runner",type=Path,required=True)
    a=p.parse_args()
    try:
        output=check(a.runner)
        print(json.dumps(output,sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({"schema":SCHEMA, "status":"GLM_REJECT_GATE_AST_HOLD",
                          "gpu_started":False,"private_values_emitted":False}))
        return 42

if __name__=="__main__":
    raise SystemExit(main())
