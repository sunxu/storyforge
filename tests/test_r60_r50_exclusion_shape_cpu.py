"""Synthetic-only structural diagnostics: never write private data to repo."""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SRC = ROOT / "scripts/r60_r50_exclusion_shape_cpu.py"
spec = importlib.util.spec_from_file_location("r50_shape", SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def files(tmp_path, x=None, y=None):
    if x is None:
        x = [{"case_id": f"secret-{i}", "reason_code": "private",
              "unknown-secret-field": "not-to-print"} for i in range(4)]
    if y is None:
        y = [f"secret-{i}" for i in range(4)]
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps({"excluded_cases": x}))
    b.write_text(json.dumps({"exclude_ids": y}))
    os.chmod(a, 0o600)
    os.chmod(b, 0o600)
    return a, b


def test_object_against_scalar_shows_only_safe_shapes(tmp_path):
    out = m.check(*files(tmp_path))
    assert out["status"] == "R50_EXCLUSION_SHAPES_IDENTIFIED__MAPPING_HOLD"
    assert out["selection"]["element_type_counts"] == {"object": 4}
    assert out["admission"]["element_type_counts"] == {"string": 4}
    assert out["selection"]["recognized_schema_fields"] == ["case_id", "reason_code"]
    assert out["selection"]["unrecognized_field_occurrences"] == 4
    raw = json.dumps(out)
    assert "secret-0" not in raw and "unknown-secret-field" not in raw
    assert out["exclusion_id_sets_equal_verified"] is False
    assert out["train_admitted"] == 0


def test_malformed_array_holds(tmp_path):
    out = m.check(*files(tmp_path, x=[{}]))
    assert out["status"] == "R50_EXCLUSION_SHAPE_HOLD"
    assert out["reason_code"] == "FOUR_ENTRIES_HOLD"


def test_symlink_and_permissions_hold(tmp_path):
    a, b = files(tmp_path)
    os.chmod(a, 0o644)
    assert m.check(a, b)["status"] == "R50_EXCLUSION_SHAPE_HOLD"
    os.chmod(a, 0o600)
    link = tmp_path / "link.json"
    link.symlink_to(a)
    assert m.check(link, b)["status"] == "R50_EXCLUSION_SHAPE_HOLD"


def test_mixed_shapes_never_promote(tmp_path):
    out = m.check(*files(tmp_path, x=[1, True, None, {"case_id": "secret"}]))
    assert out["selection"]["element_type_counts"] == {
        "boolean": 1, "integer": 1, "null": 1, "object": 1}
    assert out["r50_complete_exclusion_verified"] is False
