"""Synthetic V2 world JSON shapes without private content or live DB."""
import pytest
import r60_base336_v2_world_branch_shape_cpu as shape


def sample():
    return [
        ("current", 172, 157, 15, 156, 1, 15,
         170, 0, 2, 0, 1, 0, 0, 169, 172, 0, 0),
        ("version", 200, 165, 35, 165, 0, 35,
         200, 0, 0, 0, 0, 0, 0, 200, 200, 0, 0),
    ]


def test_runtime_branches_without_semantic_promotion():
    out = shape.verify(sample())
    assert out["shape_counts"]["current"]["nonstory_branch"] == 15
    assert out["shape_counts"]["current"]["world_nested_nonempty_object"] == 169
    assert out["world_component_isolation_verified"] is False
    assert out["historical_actual_sent_prompt_verified"] is False
    assert out["train_admitted"] == 0


def test_missing_nonstory_card_is_not_inferred():
    rows = sample()
    rows[0] = (*rows[0][:6], 14, *rows[0][7:])
    out = shape.verify(rows)
    assert out["shape_counts"]["current"]["nonstory_branch_character_object"] == 14
    assert out["train_admitted"] == 0


def test_world_types_cannot_exceed_total():
    rows = sample()
    rows[0] = (*rows[0][:7], 171, *rows[0][8:])
    with pytest.raises(shape.Hold, match="WORLD_SHAPE_BOUNDS_HOLD"):
        shape.verify(rows)


def test_duplicate_origin_fails_closed():
    rows = sample()
    rows[1] = ("current", *rows[1][1:])
    with pytest.raises(shape.Hold, match="WORLD_SHAPE_RESULT_HOLD"):
        shape.verify(rows)


def test_noninteger_count_fails_closed():
    rows = sample()
    rows[0] = (*rows[0][:5], True, *rows[0][6:])
    with pytest.raises(shape.Hold, match="WORLD_SHAPE_TYPE_HOLD"):
        shape.verify(rows)
