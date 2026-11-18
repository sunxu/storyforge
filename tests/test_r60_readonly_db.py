from datetime import UTC, datetime
from uuid import UUID

import pytest

from experiments.r58_quality import r60_readonly_db as db


def test_normalize_identifier_accepts_psycopg_uuid_and_text():
    value = UUID("559c7d10-a470-4498-a9d2-d81043ba703e")
    assert db.normalize_identifier(value) == str(value)
    assert db.normalize_identifier(str(value)) == str(value)


@pytest.mark.parametrize("value", [None, "", 123, object()])
def test_normalize_identifier_rejects_non_identifier(value):
    with pytest.raises(db.ReadOnlyDBHold, match="DB_IDENTIFIER_HOLD"):
        db.normalize_identifier(value)


def test_normalize_timestamp_accepts_aware_datetime_and_z_string():
    expected = datetime(2026, 11, 18, 6, 0, tzinfo=UTC)
    assert db.normalize_timestamp(expected) == expected
    assert db.normalize_timestamp("2026-11-18T06:00:00Z") == expected


def test_normalize_timestamp_rejects_naive_values():
    with pytest.raises(db.ReadOnlyDBHold, match="DB_TIMESTAMP_HOLD"):
        db.normalize_timestamp("2026-11-18T06:00:00")
    with pytest.raises(db.ReadOnlyDBHold, match="DB_TIMESTAMP_HOLD"):
        db.normalize_timestamp(datetime(2026, 11, 18, 6))


def test_normalize_identifier_fields_converts_all_required_fields():
    row = {
        "story_id": UUID("559c7d10-a470-4498-a9d2-d81043ba703e"),
        "author_id": UUID("a9f1a9e2-6a2a-4c3e-bc74-f3f0e8b3f7a0"),
    }
    result = db.normalize_identifier_fields(row, ("story_id", "author_id"))
    assert result is row
    assert all(isinstance(result[key], str) for key in row)


def test_readonly_guard_is_exact():
    db.assert_readonly_guard(("r58_export_reader", "on", "on", False, False))
    with pytest.raises(db.ReadOnlyDBHold, match="DATABASE_GUARD_HOLD"):
        db.assert_readonly_guard(("r58_export_reader", "off", "on", False, False))
    with pytest.raises(db.ReadOnlyDBHold, match="DATABASE_GUARD_HOLD"):
        db.assert_readonly_guard(("other_role", "on", "on", False, False))
