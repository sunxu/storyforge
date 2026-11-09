"""Synthetic P2-B tests; never use Owner private data."""
import json
import stat

import pytest

from scripts import r60_owner_heldout_p2b_v1 as cli
from storyforge_gold_quality import hf_owner_adjudication_v2 as base
from storyforge_gold_quality import hf_owner_heldout_p2b_v1 as heldout


def fixture_inputs():
    gold_sources = []
    locked = []
    development = []
    for i in range(40):
        old_id = f"gold_{i:02d}"
        target = f"合成回复{i}"
        digest = base.sha(target.encode())
        case = {
            "blind_case_id": old_id, "target_sha256": digest,
            "history": [{"role": "system", "content": "合成规则"}],
            "current_user_text": "下一步？",
            "target_assistant_text": target,
        }
        gold_sources.append(case)
        entry = {"blind_case_id": old_id, "target_sha256": digest,
                 "split": "development" if i < 20 else "locked_regression"}
        (development if i < 20 else locked).append(entry)
    gold_raw = base.canonical({
        "schema": base.SOURCE_PACKET_SCHEMA, "reviewer": "C", "cases": gold_sources
    }) + b"\n"
    gold = {
        "schema": base.P0_GOLD_SCHEMA,
        "status": "GOLD72_CALIBRATION_MANIFEST_FROZEN",
        "candidate_count": 40, "development_case_count": 20,
        "locked_regression_case_count": 20, "story_disjoint": False,
        "source_pins_sha256": {"c_blind": base.sha(gold_raw)},
        "development_cases": development, "locked_regression_cases": locked,
        "quality_v1_admitted": 0, "training_authorized": False,
    }
    severe_packets = []
    severe_cases = []
    for i in range(10):
        old_id = f"severe_{i:02d}"
        severe_cases.append({"calibration_id": old_id})
        severe_packets.append({
            "schema": "storyforge_r60_pilot10_c_blind_packet_private_v1",
            "calibration_id": old_id,
            "visible_history": [{"role": "user", "content": "测试？"}],
            "target_text": f"合成严重案例{i}",
            "target_semantics": {"prior_label": "MUST_NOT_LEAK"},
        })
    severe_raw = b"".join(base.canonical(x) + b"\n" for x in severe_packets)
    severe = {
        "schema": "storyforge_r60_severe10_calibration_manifest_private_v1",
        "status": "R60_SEVERE10_CALIBRATION_MANIFEST_FROZEN",
        "candidate_count": 10, "unique_source_cases": 10,
        "source_pins_sha256": {"c_packets": base.sha(severe_raw)},
        "cases": severe_cases,
        "quality_v1_admitted": 0, "training_authorized": False,
    }
    dedup = {
        "schema": "storyforge_r60_calibration_crossset_dedup_private_v1",
        "status": "CROSSSET_EXACT_DEDUP_PASS", "gold_case_count": 40,
        "pilot_case_count": 10, "within_gold_unique": 40,
        "within_pilot_unique": 10, "exact_history_overlap_count": 0,
        "exact_target_overlap_count": 0,
        "exact_full_history_target_overlap_count": 0,
    }
    return gold, severe, dedup, gold_raw, severe_raw


def build(inputs):
    n = iter(range(30))
    return heldout.build_package(
        *inputs, token_factory=lambda: f"{next(n):032x}",
        shuffle=lambda rows: rows.reverse()
    )


def test_p2b_exact_30_90_contract_and_no_label_leak():
    raw, mapping, manifest, safe = build(fixture_inputs())
    packets = [json.loads(line) for line in raw.splitlines()]
    assert len(packets) == 30
    assert len({p["calibration_id"] for p in packets}) == 30
    assert all(set(p) == {"schema", "calibration_id", "visible_history",
                           "target_text", "verified_world_components"} for p in packets)
    assert all(p["schema"] == heldout.PACKET_SCHEMA for p in packets)
    assert b"MUST_NOT_LEAK" not in raw
    assert b"gold_" not in raw and b"severe_" not in raw
    assert mapping["case_count"] == manifest["case_count"] == 30
    assert safe["semantic_checks_expected"] == 90
    assert safe["owner_review_started"] is False
    assert safe["training_authorized"] is False


@pytest.mark.parametrize("field", ["exact_history_overlap_count",
                                     "exact_target_overlap_count",
                                     "exact_full_history_target_overlap_count"])
def test_p2b_dedup_must_fail_closed(field):
    inputs = list(fixture_inputs())
    inputs[2][field] = 1
    with pytest.raises(base.AdjudicationHold, match="P2B_P0_FREEZE_BINDING_HOLD"):
        build(inputs)


def test_p2b_source_pin_and_split_must_fail_closed():
    inputs = list(fixture_inputs())
    inputs[1]["source_pins_sha256"]["c_packets"] = "0" * 64
    with pytest.raises(base.AdjudicationHold, match="P2B_P0_FREEZE_BINDING_HOLD"):
        build(inputs)
    inputs = list(fixture_inputs())
    inputs[0]["locked_regression_cases"][0]["split"] = "development"
    with pytest.raises(base.AdjudicationHold, match="P2B_FROZEN_COHORT_COUNT_HOLD"):
        build(inputs)


def test_p2b_rejects_duplicate_blind_ids():
    inputs = fixture_inputs()
    with pytest.raises(base.AdjudicationHold, match="P2B_NEW_BLIND_ID_INVALID"):
        heldout.build_package(*inputs, token_factory=lambda: "0" * 32)


def test_p2b_verify_fails_closed_for_missing_owner_results():
    raw, *_ = build(fixture_inputs())
    with pytest.raises(base.AdjudicationHold, match="OWNER_RESULT_SET_CARDINALITY_HOLD"):
        heldout.verify(raw, b'{"empty":true}\n', b'{"empty":true}\n')


def test_p2a_default_cardinality_unchanged():
    with pytest.raises(base.AdjudicationHold, match="OWNER_RESULT_SET_CARDINALITY_HOLD"):
        base.verify_owner_results(b'{"empty":true}\n', b'{"empty":true}\n',
                                  b'{"empty":true}\n')


def test_p2b_manifest_map_binding_fail_closed_before_owner_review():
    raw, mapping, manifest, _ = build(fixture_inputs())
    result_raw = b'{"not_ready":true}\n'
    check_raw = b'{"not_ready":true}\n'
    # A real frozen packet and map pass the binding checks, then the absent
    # Owner result set is correctly refused by the 30/90 verifier.
    with pytest.raises(base.AdjudicationHold, match="OWNER_RESULT_SET_CARDINALITY_HOLD"):
        heldout.verify_package(
            raw, result_raw, check_raw,
            base.canonical(manifest), base.canonical(mapping)
        )
    tampered_manifest = dict(manifest)
    tampered_manifest["packet_sha256"] = "0" * 64
    with pytest.raises(base.AdjudicationHold, match="P2B_MANIFEST_OR_MAP_BINDING_HOLD"):
        heldout.verify_package(
            raw, result_raw, check_raw,
            base.canonical(tampered_manifest), base.canonical(mapping)
        )
    tampered_map = dict(mapping)
    tampered_map["mapping"] = [dict(x) for x in mapping["mapping"]]
    tampered_map["mapping"][0]["cohort"] = "development"
    with pytest.raises(base.AdjudicationHold, match="P2B_MANIFEST_OR_MAP_BINDING_HOLD"):
        heldout.verify_package(
            raw, result_raw, check_raw,
            base.canonical(manifest), base.canonical(tampered_map)
        )


def test_verifier_split_directories_write_only_receipt(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    package = tmp_path / "package"
    owner = tmp_path / "owner"
    receipt = tmp_path / "receipt"
    repo.mkdir()
    for directory in (package, owner, receipt):
        directory.mkdir(mode=0o700)
        directory.chmod(0o700)
    names = (
        (package, heldout.PACKET_NAME), (package, heldout.MANIFEST_NAME),
        (package, heldout.MAP_NAME), (owner, heldout.RESULT_NAME),
        (owner, heldout.CHECK_NAME),
    )
    for directory, name in names:
        path = directory / name
        path.write_bytes(b"{}\n")
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    monkeypatch.setattr(cli.base, "_read_private", lambda *args, **kwargs: b"{}\n")
    monkeypatch.setattr(
        cli.heldout, "verify_package", lambda *args: ({"manifest": True}, {"safe": True})
    )
    monkeypatch.setattr(
        cli, "_private_dir", lambda path, repo, must_exist: path.expanduser()
    )
    monkeypatch.setattr(
        "sys.argv", [
            "r60_owner_heldout_p2b_v1.py", "--repo-root", str(repo), "--verify",
            "--package-dir", str(package), "--owner-results-dir", str(owner),
            "--receipt-dir", str(receipt),
        ]
    )
    assert cli.main() == 0
    assert (receipt / "P2B_REVIEW_FINAL_SAFE.json").read_text() == (
        '{"safe":true}\n'
    )
    assert not (receipt / "P2B_OWNER_RESULTS_MANIFEST_PRIVATE.json").exists()


def test_verifier_split_directories_must_be_distinct(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    shared = tmp_path / "shared"
    repo.mkdir()
    shared.mkdir(mode=0o700)
    shared.chmod(0o700)
    monkeypatch.setattr(
        "sys.argv", [
            "r60_owner_heldout_p2b_v1.py", "--repo-root", str(repo), "--verify",
            "--package-dir", str(shared), "--owner-results-dir", str(shared),
            "--receipt-dir", str(shared),
        ]
    )
    assert cli.main() == 42
