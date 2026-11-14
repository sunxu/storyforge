"""No-DB synthetic V2 runtime-card structural coverage."""
import pytest
import r60_base336_v2_card_contract_cpu as audit


def sample():
    return [
        ("current", 172, 100, 72, 0, 100, 96, 72, 170, 20),
        ("version", 200, 110, 90, 0, 110, 110, 90, 200, 35),
    ]


def test_verified_counts_remain_held():
    safe = audit.verify(sample())
    assert safe["card_contract_counts"]["current"]["nonempty_char_array"] == 96
    assert safe["story_version_at_target_verified"] is False
    assert safe["train_admitted"] == 0


def test_unrecognized_card_type_not_forced_to_story():
    rows = sample()
    rows[0] = ("current", 172, 100, 70, 1, 100, 96, 70, 170, 20)
    safe = audit.verify(rows)
    assert safe["card_contract_counts"]["current"]["absent_type"] == 1


def test_nonempty_array_cannot_exceed_array_count():
    rows = sample()
    rows[0] = ("current", 172, 100, 72, 0, 100, 101, 72, 170, 20)
    with pytest.raises(audit.Hold, match="CARD_RESULT_BOUNDS_HOLD"):
        audit.verify(rows)


def test_rejects_duplicate_origin():
    rows = sample()
    rows[1] = ("current", *rows[1][1:])
    with pytest.raises(audit.Hold, match="CARD_RESULT_SHAPE_HOLD"):
        audit.verify(rows)
