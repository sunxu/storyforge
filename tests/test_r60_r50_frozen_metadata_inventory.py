"""Synthetic-only tests for R50 file structure inventory. No real heldout data."""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "scripts/r60_r50_frozen_metadata_inventory.py"
spec = importlib.util.spec_from_file_location("inventory", source)
inventory_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_mod)


def private_file(path, text):
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def test_synthetic_parseable_inventory_remains_coverage_hold(tmp_path):
    cases = private_file(tmp_path / "cases.jsonl", '{"example":1}\n{"example":2}\n')
    prov = private_file(tmp_path / "provenance.jsonl", '{"kind":"fictional"}\n')
    excl = private_file(tmp_path / "exclusion.json", '{"version":"synthetic","cases":[]}')
    result = inventory_mod.inventory(cases, prov, excl)
    assert result["status"] == "R50_METADATA_FILES_PARSEABLE__COVERAGE_HOLD"
    assert result["cases_file_rows"] == 2
    assert result["provenance_file_rows"] == 1
    assert result["r50_complete_exclusion_verified"] is False
    assert result["train_admitted"] == 0
    assert "fictional" not in json.dumps(result)
    assert str(tmp_path) not in json.dumps(result)


def test_invalid_file_never_claims_coverage(tmp_path):
    cases = private_file(tmp_path / "cases.jsonl", '{"private":"sensitive"}\n')
    prov = private_file(tmp_path / "provenance.jsonl", 'not json')
    excl = private_file(tmp_path / "exclusion.json", '{"x":[]}')
    assert inventory_mod.inventory(cases, prov, excl)["status"] == "R50_METADATA_INVENTORY_HOLD"
    os.chmod(prov, 0o644)
    assert inventory_mod.inventory(cases, prov, excl)["reason_code"] == "FILE_MODE_HOLD"


def test_duplicate_and_symlink_fail(tmp_path):
    cases = private_file(tmp_path / "cases.jsonl", '{"sample":1}\n')
    excl = private_file(tmp_path / "exclusion.json", '{}')
    assert inventory_mod.inventory(cases, cases, excl)["reason_code"] == "DUPLICATE_FILE_HOLD"
    link = tmp_path / "link.jsonl"
    link.symlink_to(cases)
    assert inventory_mod.inventory(link, cases, excl)["status"] == "R50_METADATA_INVENTORY_HOLD"
