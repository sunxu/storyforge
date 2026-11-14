"""Synthetic aggregate-only shape checks; never touches live DB."""
import pytest
import r60_base336_story_json_shape_cpu as shape


def good():
    return (172, 150, 22, 2, 1, 170, 2, 0, 0, 200, 199, 1, 0, 0)


def test_accepted_aggregate_still_held():
    result = shape.validate(good())
    assert result["json_shape_counts"]["characters_array_rows"] == 150
    assert result["train_admitted"] == 0
    assert result["world_component_isolation_verified"] is False
    assert result["historical_actual_sent_system_verified"] is False


def test_rejects_impossible_counts():
    data = list(good())
    data[3] = 151
    # Every count must fit the total. Zero-content semantics are never guessed.
    data[3] = 173
    with pytest.raises(shape.Hold, match="JSON_COUNTS_BOUNDS_HOLD"):
        shape.validate(tuple(data))


def test_rejects_cross_type_overflow():
    data = list(good())
    data[1] = 160
    data[2] = 23
    with pytest.raises(shape.Hold, match="JSON_COUNTS_BOUNDS_HOLD"):
        shape.validate(tuple(data))


def test_rejects_non_integer_output():
    data = list(good())
    data[1] = True
    with pytest.raises(shape.Hold, match="JSON_COUNTS_CONTRACT_HOLD"):
        shape.validate(tuple(data))
