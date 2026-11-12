"""Synthetic-only PRESEAL 46-row crosswalk tests."""
import importlib.util
import json
import os
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts/r60_r50_preseal_crosswalk_cpu.py"
spec = importlib.util.spec_from_file_location("crosswalk", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def write(p, rows, jsonl=False):
    p.write_text(
        ("\n".join(json.dumps(x) for x in rows) + "\n") if jsonl else json.dumps(rows),
        encoding="utf-8",
    )
    os.chmod(p, 0o600)
    return p


def fixtures(tmp_path):
    cases = [{"case_id": f"synthetic-{i}", "user_input": "fiction"} for i in range(46)]
    prov = [
        {"case_id": f"synthetic-{i}", "source_story_id": f"story-{i%5}",
         "source_session_id": f"session-{i}",
         "history_message_ids": [f"message-{i}"]}
        for i in range(46)
    ]
    sel = {"original_case_count": 50, "selected_case_count": 46,
           "excluded_cases": [], "final_heldout_seal": False}
    adm = {"candidate_case_count": 46, "excluded_case_count": 4,
           "final_heldout_seal": False, "promotion": False}
    worlds = {"same_story_id_pair_count": 0, "heldout_final_seal": False,
              "semantic_hidden_alias_and_world_component_closure": False}
    gate = {"frozen_r45_hashes_verified": False, "heldout_cases_sealed": False,
            "incomplete_or_hidden_world_aliases": True}
    return [
        write(tmp_path/"case.jsonl", cases, True),
        write(tmp_path/"provenance.jsonl", prov, True),
        write(tmp_path/"selection.json", sel),
        write(tmp_path/"admission.json", adm),
        write(tmp_path/"worlds.json", worlds),
        write(tmp_path/"gate.json", gate),
    ]


def test_synthetic_crosswalk_never_seals(tmp_path):
    out = m.check(fixtures(tmp_path))
    assert out["status"] == "R50_PRESEAL_46_CROSSWALK_PASS__FINAL_COVERAGE_HOLD"
    assert out["case_id_order_exact"] is True
    assert out["preseal_cases_checked"] == 46
    assert out["r50_complete_exclusion_verified"] is False
    assert out["frozen_protection_50_verified"] is False
    assert out["train_admitted"] == 0
    assert "synthetic-0" not in json.dumps(out)


def test_order_mismatch_holds(tmp_path):
    paths = fixtures(tmp_path)
    data = [json.loads(x) for x in paths[1].read_text().splitlines()]
    data[0]["case_id"], data[1]["case_id"] = data[1]["case_id"], data[0]["case_id"]
    write(paths[1], data, True)
    out = m.check(paths)
    assert out["status"] == "R50_PRESEAL_CROSSWALK_HOLD"
    assert out["reason_code"] == "CASE_ID_ORDER_HOLD"


def test_duplicate_case_id_holds(tmp_path):
    paths = fixtures(tmp_path)
    data = [json.loads(x) for x in paths[0].read_text().splitlines()]
    data[1]["case_id"] = data[0]["case_id"]
    write(paths[0], data, True)
    assert m.check(paths)["reason_code"] == "DUPLICATE_CASE_ID_HOLD"


def test_symlink_and_open_permissions_hold(tmp_path):
    paths = fixtures(tmp_path)
    os.chmod(paths[0], 0o644)
    assert m.check(paths)["reason_code"] == "FILE_PERMISSION_HOLD"
    os.chmod(paths[0], 0o600)
    linked = tmp_path / "link.jsonl"
    linked.symlink_to(paths[0])
    paths[0] = linked
    assert m.check(paths)["reason_code"] == "FILE_SYMLINK_HOLD"
