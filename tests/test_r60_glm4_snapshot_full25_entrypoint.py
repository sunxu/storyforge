"""Guardrails for full25 GPU entrypoint: static CPU-only checks."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "experiments/r58_quality"


def test_full25_entrypoint_immutable_outputs_and_exact_scope():
    code = (BASE / "r60_glm4_full25_snapshot_entrypoint.sh").read_text()
    assert "--snapshot-full25" in code
    assert "--case-limit 25" in code
    assert "--isolate-technical-failures" in code
    assert "--generation-snapshot-dir" in code
    assert "--confirm-paid-gpu" in code
    assert "--resume" not in code
    assert "--snapshot-probe-cases" not in code
    assert "--retry-baseline-dir" not in code
    assert "--quote-literal-repair" not in code
    assert "FULL25_DESTINATION_EXISTS_HOLD" in code
    assert 'mkdir -m 700 "$OUTPUT"' in code
    assert 'mkdir -m 700 "$SNAP"' in code
    assert 'exec python3 -u /input/r60_glm4_b25_continuous_review.py' in code
    assert "model-cache" not in code
    assert "/bucket/private-generation-snapshots/" in code


def test_full25_mode_is_opt_in_and_no_relabeling_of_failed12():
    source = (BASE / "r60_glm4_b25_continuous_review.py").read_text()
    assert 'parser.add_argument("--snapshot-full25", action="store_true")' in source
    assert 'args.case_limit != 25' in source
    assert 'args.retry_baseline_dir is not None' in source
    assert 'raise Hold("SNAPSHOT_FULL25_SCOPE_HOLD")' in source
    assert 'original_positions_identity=True' in source



def test_full25_snapshot_scope_guard_does_not_require_probe_cases():
    """Execute the exact CLI gate condition: old logic rejected full25."""
    import ast
    from types import SimpleNamespace

    source = (BASE / "r60_glm4_b25_continuous_review.py").read_text()
    tree = ast.parse(source)
    gate = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for child in node.body:
            if isinstance(child, ast.Raise) and isinstance(child.exc, ast.Call):
                if (isinstance(child.exc.func, ast.Name)
                        and child.exc.func.id == "Hold"
                        and child.exc.args
                        and isinstance(child.exc.args[0], ast.Constant)
                        and child.exc.args[0].value == "SNAPSHOT_PROBE_SCOPE_HOLD"):
                    gate = node.test
                    break
    assert gate is not None
    condition = compile(ast.Expression(gate), "<snapshot-scope-gate>", "eval")

    def blocked(full25, probe, has_snapshot):
        args = SimpleNamespace(
            snapshot_full25=full25, snapshot_probe_cases=probe,
            generation_snapshot_dir="/bucket/new" if has_snapshot else None)
        return eval(condition, {"args": args})

    assert blocked(full25=True, probe=0, has_snapshot=True) is False
    assert blocked(full25=False, probe=0, has_snapshot=True) is True
    assert blocked(full25=False, probe=1, has_snapshot=True) is False
    assert blocked(full25=True, probe=-1, has_snapshot=True) is True
