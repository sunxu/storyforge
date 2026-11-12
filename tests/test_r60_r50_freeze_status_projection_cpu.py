"""Synthetic-only R50 report projection tests, no real private material."""
import importlib.util
import json
import os
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts/r60_r50_freeze_status_projection_cpu.py"
spec = importlib.util.spec_from_file_location("r50_status_projection", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def files(tmp_path):
    values = {
        "selection": {"original_case_count": 50, "selected_case_count": 46,
                      "excluded_cases": ["secret-id"], "final_heldout_seal": "secret-token",
                      "owner_exclusion_authorized": False},
        "admission": {"candidate_case_count": 46, "excluded_case_count": 4,
                      "exclude_ids": ["secret-id"], "final_heldout_seal": False,
                      "promotion": "secret-string"},
        "worlds": {"same_story_id_pair_count": 0, "heldout_final_seal": False,
                   "semantic_hidden_alias_and_world_component_closure": "secret-note"},
        "r45_gate": {"frozen_r45_hashes_verified": True, "heldout_cases_sealed": False,
                     "incomplete_or_hidden_world_aliases": ["secret-id"],
                     "exact_world_id_conflicts": 0},
    }
    paths = {}
    for name, value in values.items():
        p = tmp_path / (name + ".json")
        p.write_text(json.dumps(value))
        os.chmod(p, 0o600)
        paths[name] = p
    return paths


def test_safe_projection_never_passes_exclusion_or_leaks_values(tmp_path):
    report = m.check(files(tmp_path))
    assert report["status"] == "R50_FREEZE_STATUS_TYPES_READ__EXCLUSION_HOLD"
    assert report["reports"]["selection"]["original_case_count"] == {"type": "integer", "value": 50}
    assert report["reports"]["selection"]["excluded_cases"] == {"type": "array", "count": 1}
    assert report["reports"]["selection"]["final_heldout_seal"] == {"type": "string_or_unsupported"}
    assert "secret-id" not in json.dumps(report)
    assert "secret-token" not in json.dumps(report)
    assert report["train_admitted"] == 0
    assert report["r50_complete_exclusion_verified"] is False


def test_rejects_loose_mode_and_symlink(tmp_path):
    paths = files(tmp_path)
    os.chmod(paths["selection"], 0o644)
    assert m.check(paths)["reason_code"] == "SOURCE_MODE_HOLD"
    os.chmod(paths["selection"], 0o600)
    link = tmp_path / "link.json"
    link.symlink_to(paths["selection"])
    paths["selection"] = link
    assert m.check(paths)["reason_code"] == "SOURCE_LINK_HOLD"


def test_missing_key_and_large_integer_are_not_leaked(tmp_path):
    paths = files(tmp_path)
    p = paths["selection"]
    value = json.loads(p.read_text())
    value.pop("original_case_count")
    value["selected_case_count"] = 999999999999
    p.write_text(json.dumps(value))
    report = m.check(paths)
    assert report["reports"]["selection"]["original_case_count"] == {"type": "missing"}
    assert report["reports"]["selection"]["selected_case_count"] == {"type": "integer_out_of_safe_range"}
