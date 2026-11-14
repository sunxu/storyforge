"""Synthetic-only contract tests: no real story text, DB or model."""
import pytest
import r60_base_constructed_system_contract_v1 as c


def fixture():
    return [
        {"role": "user", "content": "虚构请求A"},
        {"role": "assistant", "content": "虚构回应B"},
        {"role": "user", "content": "虚构请求C"},
    ]


def build(**kwargs):
    return c.assemble_candidate(
        fixture(), "虚构最终目标D",
        history_turns=(1, 2, 3), target_turn=4, **kwargs,
    )


def test_synthetic_contract_is_constructed_and_not_admitted():
    result = build()
    assert [x["role"] for x in result["messages"]] == [
        "system", "user", "assistant", "user", "assistant",
    ]
    assert result["provenance_label"] == "TRAINING_CONSTRUCTED_NOT_HISTORICAL"
    assert result["assistant_target_index"] == 4
    assert result["train_admitted"] == 0
    assert result["actual_collator_verified"] is False


def test_future_turn_rejected():
    with pytest.raises(c.ContractHold, match="HISTORY_CHRONOLOGY_HOLD"):
        c.assemble_candidate(
            fixture(), "目标", history_turns=(1, 2, 5), target_turn=4,
        )


def test_mistaken_history_assistant_label_rejected():
    rows = fixture()
    rows[-1]["role"] = "assistant"
    with pytest.raises(c.ContractHold, match="ROLE_ORDER_HOLD"):
        c.assemble_candidate(
            rows, "目标", history_turns=(1, 2, 3), target_turn=4,
        )


def test_unverified_latest_world_rejected():
    with pytest.raises(c.ContractHold, match="UNVERSIONED_FACT_HOLD"):
        build(world=c.SourceBoundFact(
            "v2_data.world", "虚构世界", "fake-story", "latest", "unverified",
        ))


def test_cross_story_cards_rejected():
    with pytest.raises(c.ContractHold, match="CROSS_STORY_CARD_HOLD"):
        build(
            world=c.SourceBoundFact(
                "v2_data.world", "世界", "fake-a", "rev-1", "source-a",
            ),
            roles=c.SourceBoundFact(
                "v2_data.characters", "角色", "fake-b", "rev-2", "source-b",
            ),
        )


def test_matching_cards_are_still_not_independently_verified():
    result = build(
        world=c.SourceBoundFact(
            "v2_data.world", "合成世界", "fake", "rev-1", "source-evidence",
        ),
    )
    assert "合成世界" in result["messages"][0]["content"]
    assert result["source_fact_independent_verification"] is False
    assert result["train_admitted"] == 0


def test_wrong_role_field_path_rejected():
    with pytest.raises(c.ContractHold, match="ROLE_SOURCE_PATH_HOLD"):
        build(roles=c.SourceBoundFact(
            "v2_data.world", "虚构角色", "fake", "rev-1", "source-evidence",
        ))
