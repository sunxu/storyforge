"""Synthetic-only verification of frozen R45 report format."""
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("r45_receipt", ROOT / "scripts/r60_r45_existing_full_source_receipt_cpu.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def make(tmp_path, change=None):
    record = {
        "schema": m.SOURCE_SCHEMA,
        "status": m.SOURCE_STATUS,
        "frozen_r45_hashes_verified": True,
        "verified_r45_counts": {"train": 49, "validation": 15},
        "r45_distinct_story_ids": 9,
        "new_world_count": 5,
        "exact_world_id_conflicts": 0,
        "exact_long_message_hit_count": 0,
        "all_offset_120_codepoint_window_hit_count": 0,
        "short_or_paraphrased_context_review": "PENDING",
        "incomplete_or_hidden_world_aliases": "PENDING",
        "heldout_cases_sealed": 0,
        "raw_private_text_or_ids_emitted": False,
        "gpu_executed": False,
        "model_promotion": False,
    }
    if change:
        change(record)
    path = tmp_path / "r45.json"
    path.write_text(json.dumps(record))
    os.chmod(path, 0o600)
    return path


def test_valid_exact_report_still_holds_semantics_and_training(tmp_path):
    r = m.verify(make(tmp_path))
    assert r["r45_exact_source_screen_verified"] is True
    assert r["status"] == "R45_EXISTING_EXACT_SOURCE_SCREEN_PASS__SEMANTIC_SEAL_HOLD"
    assert r["r45_semantic_world_isolation_verified"] is False
    assert r["final_heldout_seal_verified"] is False
    assert r["train_admitted"] == 0


def test_nonzero_overlap_holds(tmp_path):
    r = m.verify(make(tmp_path, lambda d: d.update(exact_world_id_conflicts=1)))
    assert r["reason_code"] == "R45_EXACT_METRIC_HOLD"
    assert r["r45_exact_source_screen_verified"] is False


def test_wrong_status_or_semantic_field_holds(tmp_path):
    def bad(d):
        d["status"] = "UNKNOWN"
    assert m.verify(make(tmp_path, bad))["reason_code"] == "FROZEN_REPORT_CONTRACT_HOLD"
    def not_pending(d):
        d["incomplete_or_hidden_world_aliases"] = "PASS"
    assert m.verify(make(tmp_path, not_pending))["reason_code"] == "PENDING_SEMANTIC_OR_SEAL_CONTRACT_HOLD"


def test_boolean_zero_is_not_accepted(tmp_path):
    r = m.verify(make(tmp_path, lambda d: d.update(heldout_cases_sealed=False)))
    assert r["reason_code"] == "PENDING_SEMANTIC_OR_SEAL_CONTRACT_HOLD"


def test_invalid_permissions_holds_without_leak(tmp_path):
    path = make(tmp_path, lambda d: d.update(secret_private_field="not-reveal"))
    os.chmod(path, 0o644)
    r = m.verify(path)
    assert r["status"] == "R45_EXISTING_FULL_SOURCE_RECEIPT_HOLD"
    assert "not-reveal" not in json.dumps(r)
