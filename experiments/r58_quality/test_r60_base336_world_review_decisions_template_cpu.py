"""Synthetic-only 8-group decisions template checks, no DB or private data."""
import json
import stat

import pytest
import r60_base336_world_review_decisions_template_cpu as target


def groups():
    result = []
    for k in range(1, 9):
        members = [
            {"story_id_PRIVATE": f"s-{i}", "split": "train" if i < 28 else "validation",
             "candidate_positions_1based_PRIVATE": [i + 1],
             "archived_revision_ids_PRIVATE": [100 + i],
             "current_world_match": True}
            for i in range(38)
        ]
        result.append({
            "group_ordinal": k, "semantic_verdict": "UNREVIEWED",
            "current_world_cross_split": k < 8,
            "members_PRIVATE": members,
        })
    return result


def payload():
    return {
        "schema": target.roster.SCHEMA,
        "train_admitted": 0,
        "semantic_review_completed": False,
        "actual_sent_version_verified": False,
        "groups_PRIVATE": groups(),
    }


def test_exact_group_inventory_produces_hold_only_template():
    result = target.build_template(target.validate(payload()), "abc")
    assert len(result["group_reviews_PRIVATE"]) == 8
    assert all(x["decision"] == "HOLD" for x in result["group_reviews_PRIVATE"])
    assert result["train_admitted"] == 0
    assert result["world_component_isolation_verified"] is False


def test_missing_source_group_fails_closed():
    p = payload()
    p["groups_PRIVATE"].pop()
    with pytest.raises(target.Hold, match="GROUP_CONTRACT_HOLD"):
        target.validate(p)


def test_no_review_status_promotion():
    p = payload()
    p["groups_PRIVATE"][0]["semantic_verdict"] = "PASS"
    with pytest.raises(target.Hold, match="GROUP_VERDICT_HOLD"):
        target.validate(p)


def test_private_file_create_only_and_0600(monkeypatch, tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    directory = root / "roster"
    directory.mkdir(mode=0o700)
    monkeypatch.setattr(target.private, "BASE", root)
    source = directory / target.roster.FILENAME
    target.private.write_new(
        source, (json.dumps(payload(), ensure_ascii=False) + "\n").encode())
    result = target.run(directory)
    assert result["template_file_created"]
    assert not result["world_content_read"]
    output = directory / target.FILENAME
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    with pytest.raises(target.Hold, match="OUTPUT_EXISTS_HOLD"):
        target.run(directory)
