from experiments.r58_quality.r60_base336_p2_public_source_inventory_cpu import SQL, Hold, validate_rows


def test_p2_query_projects_current_public_v2_data():
    assert "s.public_v2_data AS current_public_v2_data" in SQL


def test_p2_validation_fails_closed_without_current_public_v2_data():
    row = {
        "story_id": "story-1",
        "author_id": "author-1",
        "world_json_md5": "0" * 32,
    }
    try:
        validate_rows([row] * 8)
    except Hold as exc:
        assert str(exc) == "SOURCE_CURRENT_V2_DATA_HOLD"
    else:
        raise AssertionError("missing current public v2 data must fail closed")
