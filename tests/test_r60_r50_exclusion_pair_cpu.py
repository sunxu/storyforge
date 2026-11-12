"""Synthetic only. No R50 private IDs or report values."""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SRC = ROOT / "scripts/r60_r50_exclusion_pair_cpu.py"
spec = importlib.util.spec_from_file_location("pair", SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def write(p, obj):
    p.write_text(json.dumps(obj))
    os.chmod(p, 0o600)
    return p


def fixture(tmp_path, transform=None):
    a = {"original_case_count": 50, "selected_case_count": 46,
         "owner_exclusion_authorized": True,
         "excluded_cases": ["fake-A", "fake-B", "fake-C", "fake-D"]}
    b = {"candidate_case_count": 46, "excluded_case_count": 4,
         "exclude_ids": ["fake-D", "fake-A", "fake-C", "fake-B"]}
    if transform:
        transform(a,b)
    return write(tmp_path/"selection.json",a),write(tmp_path/"admission.json",b)


def test_membership_equal_order_irrelevant_and_final_seal_held(tmp_path):
    r = m.check(*fixture(tmp_path))
    assert r["status"] == "R50_PRESEAL_FOUR_EXCLUSIONS_MATCH__SEAL_HOLD"
    assert r["exclusion_id_sets_equal"] is True
    assert r["final_heldout_seal_verified"] is False
    assert r["r50_complete_exclusion_verified"] is False
    assert r["train_admitted"] == 0
    assert "fake-A" not in json.dumps(r)


def test_different_member_fails_without_leaking(tmp_path):
    def bad(a,b): b["exclude_ids"][0] = "private-like-marker"
    r = m.check(*fixture(tmp_path,bad))
    assert r["reason_code"] == "EXCLUSION_ID_SET_MISMATCH_HOLD"
    assert "private-like-marker" not in json.dumps(r)


def test_non_scalar_exclusion_fails_not_silently_coerced(tmp_path):
    def bad(a,b): a["excluded_cases"][0] = {"case_id":"fake-A"}
    assert m.check(*fixture(tmp_path,bad))["reason_code"] == "EXCLUSION_ID_TYPE_HOLD"


def test_permission_holds(tmp_path):
    a,b = fixture(tmp_path)
    os.chmod(a,0o644)
    assert m.check(a,b)["status"] == "R50_EXCLUSION_PAIR_HOLD"


def test_authorization_not_automatic(tmp_path):
    def bad(a,b): a["owner_exclusion_authorized"] = False
    assert m.check(*fixture(tmp_path,bad))["reason_code"] == "COUNT_OR_AUTH_HOLD"
