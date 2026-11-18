from experiments.r58_quality.r60_base336_p2_public_source_inventory_cpu import (
    SQL,
    BindingDiagnosticHold,
    validate_rows,
)


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
    except BindingDiagnosticHold as exc:
        assert str(exc) == "SOURCE_BINDING_HOLD"
        assert exc.safe_diagnostics["selected_rows"] == 8
        assert exc.safe_diagnostics["failed_checks"]["moderation_submission_metadata_not_visible"] == 8
        assert exc.safe_diagnostics["failed_checks"]["permission_event_metadata_not_visible"] == 8
    else:
        raise AssertionError("incomplete source and permission bindings must fail closed")
