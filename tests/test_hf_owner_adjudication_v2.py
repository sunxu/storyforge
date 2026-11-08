"""Synthetic-only tests for Owner Gold72 Development-20 adjudication preparation."""
from __future__ import annotations

import json
import stat

import pytest

from storyforge_gold_quality import hf_owner_adjudication_v2 as p2


def fixture_data():
    development = []
    locked = []
    cases = []
    for index in range(40):
        old_id = f"old-blind-case-{index:02d}"
        target = f"合成目标文本第{index:02d}条。"
        target_sha = p2.sha(target.encode("utf-8"))
        row = {
            "blind_case_id": old_id,
            "target_sha256": target_sha,
            "original_story_uuid": f"private-story-{index % 7}",
            "disagreement_type": "SYNTHETIC_DISAGREEMENT",
            "split": "development" if index < 20 else "locked_regression",
        }
        (development if index < 20 else locked).append(row)
        cases.append({
            "blind_case_id": old_id,
            "priority": index + 1,
            "history_starts_with_assistant": False,
            "review_focus": ["synthetic-only"],
            "history": [
                {
                    "role": "user", "content": f"玩家历史问题第{index:02d}条。",
                    "source_turn": index + 1,
                },
                {"role": "assistant", "content": f"NPC 历史回应第{index:02d}条。"},
            ],
            "current_user_text": f"玩家当前输入第{index:02d}条。",
            "target_assistant_text": target,
            "target_sha256": target_sha,
        })
    wrappers = [
        {
            "schema": p2.SOURCE_PACKET_SCHEMA,
            "reviewer": "C",
            "blind_story_packet_id": "old-story-packet-a",
            "case_count": 20,
            "cases": cases[:20],
        },
        {
            "schema": p2.SOURCE_PACKET_SCHEMA,
            "reviewer": "C",
            "blind_story_packet_id": "old-story-packet-b",
            "case_count": 20,
            "cases": cases[20:],
        },
    ]
    source_raw = b"".join(p2.canonical(row) + b"\n" for row in wrappers)
    manifest = {
        "schema": p2.P0_GOLD_SCHEMA,
        "status": "GOLD72_CALIBRATION_MANIFEST_FROZEN",
        "candidate_count": 40,
        "development_case_count": 20,
        "locked_regression_case_count": 20,
        "story_disjoint": False,
        "source_pins_sha256": {"c_blind": p2.sha(source_raw)},
        "development_cases": development,
        "locked_regression_cases": locked,
        "quality_v1_admitted": 0,
        "training_authorized": False,
    }
    return manifest, source_raw


def test_build_package_exposes_only_fresh_development20_packets():
    manifest, source_raw = fixture_data()
    next_id = 0

    def token_factory():
        nonlocal next_id
        next_id += 1
        return f"{next_id:032x}"

    packet_raw, owner_map, manifest_out, safe, instructions = p2.build_package(
        manifest, source_raw, p0_manifest_sha256="a" * 64,
        token_factory=token_factory, shuffle=lambda values: None,
    )
    packets = [json.loads(line) for line in packet_raw.splitlines()]
    assert len(packets) == 20
    assert len({item["calibration_id"] for item in packets}) == 20
    old_ids = {row["blind_case_id"] for row in manifest["development_cases"]}
    assert not old_ids.intersection({item["calibration_id"] for item in packets})
    assert all(item["schema"] == p2.PACKET_SCHEMA for item in packets)
    assert all(len(item["visible_history"]) == 3 for item in packets)
    assert all(item["visible_history"][0]["source_turn"] > 0 for item in packets)
    assert all(item["verified_world_components"] == [] for item in packets)
    assert not (p2.FORBIDDEN_PACKET_KEYS & set(p2._walk_keys(packets)))
    assert len(owner_map["mapping"]) == 20
    assert manifest_out["locked_regression_cases_in_packets"] == 0
    assert manifest_out["r60_severe10_cases_in_packets"] == 0
    assert safe["gold72_development_cases_only"] is True
    assert safe["old_a_b_c_judgments_exposed"] is False
    assert safe["private_values_emitted"] is False
    assert "不要打开 Owner ID Map" in instructions.decode("utf-8")


def test_build_package_rejects_source_packet_pin_mismatch():
    manifest, source_raw = fixture_data()
    manifest["source_pins_sha256"]["c_blind"] = "0" * 64
    with pytest.raises(p2.AdjudicationHold, match="P0_GOLD_C_BLIND_SOURCE_PIN_MISMATCH"):
        p2.build_package(manifest, source_raw)


def test_build_package_rejects_development_target_binding_mismatch():
    manifest, source_raw = fixture_data()
    manifest["development_cases"][0]["target_sha256"] = "f" * 64
    with pytest.raises(p2.AdjudicationHold, match="GOLD_DEVELOPMENT_SOURCE_BINDING_HOLD"):
        p2.build_package(manifest, source_raw)


def test_prepare_dry_run_writes_nothing_and_formal_write_is_create_only(tmp_path):
    manifest, source_raw = fixture_data()
    owner_root = tmp_path / "owner"
    owner_root.mkdir(mode=0o700)
    p0_dir = owner_root / "p0"
    p0_dir.mkdir(mode=0o700)
    source_dir = owner_root / "c-source"
    source_dir.mkdir(mode=0o700)
    output_parent = owner_root / "p2"
    output_parent.mkdir(mode=0o700)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    p0_path = p0_dir / "GOLD72_CALIBRATION_MANIFEST_PRIVATE.json"
    p0_path.write_bytes(p2.canonical(manifest) + b"\n")
    p0_path.chmod(0o600)
    source_path = source_dir / "R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl"
    source_path.write_bytes(source_raw)
    source_path.chmod(0o600)
    output = output_parent / "owner-adjudication-dev20"

    preflight = p2.prepare(p0_path, source_path, output, repo_root, dry_run=True)
    assert preflight["status"] == "P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN"
    assert preflight["files_written"] == 0
    assert not output.exists()

    written = p2.prepare(p0_path, source_path, output, repo_root, dry_run=False)
    assert written["status"] == p2.SAFE_STATUS
    assert written["files_written"] == 6
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert len(list(output.iterdir())) == 6
    assert all(stat.S_IMODE(item.stat().st_mode) == 0o600 for item in output.iterdir())
    with pytest.raises(p2.AdjudicationHold, match="PRIVATE_OUTPUT_DIRECTORY_HOLD"):
        p2.prepare(p0_path, source_path, output, repo_root, dry_run=False)


def test_prepare_rejects_private_input_with_unsafe_mode(tmp_path):
    manifest, source_raw = fixture_data()
    owner_root = tmp_path / "owner"
    owner_root.mkdir(mode=0o700)
    p0_dir = owner_root / "p0"
    p0_dir.mkdir(mode=0o700)
    source_dir = owner_root / "c-source"
    source_dir.mkdir(mode=0o700)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    p0_path = p0_dir / "manifest.json"
    p0_path.write_bytes(p2.canonical(manifest))
    p0_path.chmod(0o600)
    source_path = source_dir / "packets.jsonl"
    source_path.write_bytes(source_raw)
    source_path.chmod(0o644)
    output = owner_root / "out-parent" / "output"
    (owner_root / "out-parent").mkdir(mode=0o700)
    with pytest.raises(p2.AdjudicationHold, match="PRIVATE_INPUT_PERMISSION_OR_SIZE_HOLD"):
        p2.prepare(p0_path, source_path, output, repo_root, dry_run=True)
