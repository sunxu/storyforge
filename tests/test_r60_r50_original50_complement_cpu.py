"""Synthetic-only R50 50=46+4 invariant tests; override expected hashes in test scope."""
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("r50_original_audit", ROOT / "scripts/r60_r50_original50_complement_cpu.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def write(path, obj, jsonl=False):
    data = ("\n".join(json.dumps(x) for x in obj) + "\n") if jsonl else json.dumps(obj)
    path.write_text(data)
    os.chmod(path, 0o600)
    return path


def make(tmp_path, monkeypatch):
    original = [{"case_id": f"fixture-{i}"} for i in range(50)]
    provenance = [
        {"case_id": f"fixture-{i}", "source_story_id": f"story-{i%5}",
         "source_session_id": f"session-{i}", "history_message_ids": [f"msg-{i}"],
         "cutoff_message_id": f"cutoff-{i}"}
        for i in range(50)
    ]
    selection = {"original_case_count": 50, "selected_case_count": 46,
                 "owner_exclusion_authorized": True,
                 "selected_parent_line_numbers_1_based": list(range(1, 47)),
                 "excluded_cases": [
                     {"case_id": f"fixture-{i}", "reason": "synthetic"}
                     for i in range(46, 50)]}
    admission = {"candidate_case_count": 46, "excluded_case_count": 4,
                 "exclude_ids": [f"fixture-{i}" for i in range(46, 50)]}
    values = [original, provenance, original[:46], provenance[:46],
              selection, admission]
    names = ("original_cases", "original_provenance", "derived_cases",
             "derived_provenance", "selection", "admission")
    paths = {}
    for i, name in enumerate(names):
        paths[name] = write(tmp_path / f"{name}.json{'l' if i < 4 else ''}",
                            values[i], jsonl=i < 4)
    hashes = {kind: hashlib.sha256(paths[key].read_bytes()).hexdigest()
              for kind, key in (("cases", "original_cases"),
                                ("provenance", "original_provenance"))}
    sizes = {kind: paths[key].stat().st_size
             for kind, key in (("cases", "original_cases"),
                               ("provenance", "original_provenance"))}
    monkeypatch.setattr(m, "ORIGINAL_SHA", hashes)
    monkeypatch.setattr(m, "SIZE", sizes)
    return paths


def test_frozen_complement_and_provenance_pass_but_seal_held(tmp_path, monkeypatch):
    result = m.audit(make(tmp_path, monkeypatch))
    assert result["original_50_complete_cohort_verified"] is True
    assert result["original_hashes_verified"] is True
    assert result["excluded_four_match_original_complement"] is True
    assert result["selected_source_provenance_matches_original"] is True
    assert result["r50_complete_exclusion_verified"] is False
    assert result["final_heldout_seal_verified"] is False
    assert result["train_admitted"] == 0
    assert "fixture-" not in json.dumps(result)


def test_wrong_exclusion_id_holds(tmp_path, monkeypatch):
    paths = make(tmp_path, monkeypatch)
    selection = json.loads(paths["selection"].read_text())
    selection["excluded_cases"][0]["case_id"] = "fixture-NOT"
    write(paths["selection"], selection)
    result = m.audit(paths)
    assert result["reason_code"] == "EXCLUDED_REPORT_MISMATCH_HOLD"
    assert result["original_50_complete_cohort_verified"] is False


def test_manifest_parent_line_mismatch_holds(tmp_path, monkeypatch):
    paths = make(tmp_path, monkeypatch)
    selection = json.loads(paths["selection"].read_text())
    selection["selected_parent_line_numbers_1_based"][0] = 47
    write(paths["selection"], selection)
    assert m.audit(paths)["reason_code"] == "PARENT_LINE_MAPPING_HOLD" or m.audit(paths)["reason_code"] == "PARENT_LINE_NUMBERS_HOLD"


def test_source_provenance_mismatch_holds(tmp_path, monkeypatch):
    paths = make(tmp_path, monkeypatch)
    rows = [json.loads(line) for line in paths["derived_provenance"].read_text().splitlines()]
    rows[0]["source_story_id"] = "WRONG"
    write(paths["derived_provenance"], rows, jsonl=True)
    result = m.audit(paths)
    assert result["reason_code"] == "SOURCE_PROVENANCE_MISMATCH_HOLD"


def test_frozen_original_hash_mismatch_holds(tmp_path, monkeypatch):
    paths = make(tmp_path, monkeypatch)
    rows = [json.loads(line) for line in paths["original_cases"].read_text().splitlines()]
    rows[0]["case_id"] = "tampered"
    write(paths["original_cases"], rows, jsonl=True)
    assert m.audit(paths)["reason_code"] == "ORIGINAL_SHA_HOLD"
