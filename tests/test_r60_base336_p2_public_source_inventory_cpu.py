"""Synthetic tests for the deterministic R60 P2 Supabase source inventory."""
from uuid import UUID

import pytest

from experiments.r58_quality import r60_base336_p2_public_source_inventory_cpu as target


def candidate(i, created, *, author=None, world=None):
    return {
        "story_id": f"story-{i}",
        "author_id": author or f"author-{i % 5}",
        "created_at": created,
        "first_public_approved_at": created,
        "public_updated_at": created,
        "public_content_revision": 0,
        "public_content_hash": f"{i:032x}",
        "world_json_md5": world or f"{i:032x}",
        "current_public_v2_data": {"cardType": "story", "world": {"worldSentence": "synthetic world"}},
        "world_sentence_length": 20,
        "submission_revision": 0,
        "requested_visibility": "public",
        "submission_content_hash": f"{i:064x}",
        "moderation_submission_id": f"submission-{i}",
        "permission_event_id": f"event-{i}",
        "permission_kind": "ai",
        "permission_result": "ai_approved",
        "permission_submission_id": f"submission-{i}",
        "permission_submission_bound": True,
        "permission_to_visibility": "public",
        "snapshot_v2_match": True,
        "exact_world_overlap_pre_cutoff": False,
    }


def rows():
    values = [
        ("2026-11-16T06:33:25Z", 0),
        ("2026-11-16T14:56:46Z", 1),
        ("2026-11-17T02:34:17Z", 2),
        ("2026-11-17T10:05:16Z", 3),
        ("2026-11-17T11:33:21Z", 4),
        ("2026-11-17T13:10:49Z", 5),
        ("2026-11-17T13:57:33Z", 6),
        ("2026-11-17T15:12:30Z", 7),
        ("2026-11-17T15:16:33Z", 8),
        ("2026-11-17T15:20:00Z", 9),
    ]
    return [candidate(i, created) for created, i in values]


def test_deterministic_3_before_5_after_selection():
    selected = target.select_rows(rows())
    assert len(selected) == 8
    assert [r["story_id"] for r in selected] == [
        "story-0", "story-1", "story-2", "story-3",
        "story-4", "story-5", "story-6", "story-7",
    ]


def test_selection_requires_both_time_pools():
    with pytest.raises(target.Hold, match="SOURCE_TIME_POOL_HOLD"):
        target.select_rows(rows()[:2])


def test_selection_requires_eight_distinct_stories():
    selected = target.select_rows(rows())
    selected[-1]["story_id"] = selected[-2]["story_id"]
    with pytest.raises(target.Hold, match="SOURCE_STORY_ID_UNIQUENESS_HOLD"):
        target.validate_rows(selected)


def test_selection_requires_five_authors():
    selected = target.select_rows(rows())
    for i, row in enumerate(selected):
        row["author_id"] = f"author-{i}"
    with pytest.raises(target.Hold, match="SOURCE_AUTHOR_COUNT_HOLD"):
        target.validate_rows(selected)


def test_selection_requires_eight_distinct_worlds():
    selected = target.select_rows(rows())
    selected[-1]["world_json_md5"] = selected[-2]["world_json_md5"]
    with pytest.raises(target.Hold, match="SOURCE_WORLD_DEDUP_HOLD"):
        target.validate_rows(selected)


def test_psycopg_uuid_identifiers_are_normalized_at_validation_boundary():
    selected = target.select_rows(rows())
    selected[0]["story_id"] = UUID("559c7d10-a470-4498-a9d2-d81043ba703e")
    selected[0]["moderation_submission_id"] = UUID("559c7d10-a470-4498-a9d2-d81043ba703e")
    selected[0]["permission_submission_id"] = UUID("559c7d10-a470-4498-a9d2-d81043ba703e")
    result = target.validate_rows(selected)
    assert result["sources"][0]["story_id"] == "559c7d10-a470-4498-a9d2-d81043ba703e"


def test_revision_snapshot_permission_bindings_are_required():
    selected = target.select_rows(rows())
    selected[0]["submission_revision"] = 99
    with pytest.raises(target.Hold, match="SOURCE_BINDING_HOLD"):
        target.validate_rows(selected)

    selected = target.select_rows(rows())
    selected[0]["snapshot_v2_match"] = False
    with pytest.raises(target.Hold, match="SOURCE_BINDING_HOLD"):
        target.validate_rows(selected)

    selected = target.select_rows(rows())
    selected[0]["permission_submission_bound"] = False
    with pytest.raises(target.Hold, match="SOURCE_BINDING_HOLD"):
        target.validate_rows(selected)


def test_exact_world_overlap_is_fail_closed():
    selected = target.select_rows(rows())
    selected[0]["exact_world_overlap_pre_cutoff"] = True
    with pytest.raises(target.Hold, match="SOURCE_BINDING_HOLD"):
        target.validate_rows(selected)


def test_binding_diagnostics_report_aggregate_codes_without_source_values():
    selected = target.select_rows(rows())
    selected[0]["permission_event_id"] = None
    selected[1]["snapshot_v2_match"] = False
    selected[2]["exact_world_overlap_pre_cutoff"] = True
    selected[3]["permission_kind"] = "initial"

    diagnostics = target.source_binding_diagnostics(selected)

    assert diagnostics == {
        "identifier_permission_event_id_invalid": 1,
        "permission_kind_not_supported": 1,
        "snapshot_v2_mismatch": 1,
        "exact_world_overlap_pre_cutoff": 1,
    }
    rendered = str(diagnostics)
    assert "story-0" not in rendered
    assert "submission-0" not in rendered
    assert "synthetic world" not in rendered


def test_binding_hold_carries_only_aggregate_diagnostics():
    selected = target.select_rows(rows())
    selected[0]["permission_submission_bound"] = False
    with pytest.raises(target.BindingDiagnosticHold) as caught:
        target.validate_rows(selected)

    assert str(caught.value) == "SOURCE_BINDING_HOLD"
    assert caught.value.safe_diagnostics == {
        "schema": "storyforge_r60_p2_source_binding_diagnostic_v1",
        "selected_rows": 8,
        "failed_checks": {"permission_submission_bound_false": 1},
        "private_values_emitted": False,
    }
    assert "story-0" not in str(caught.value.safe_diagnostics)


def test_binding_diagnostics_normalize_psycopg_uuid_before_validation():
    selected = target.select_rows(rows())
    selected[0]["story_id"] = UUID("559c7d10-a470-4498-a9d2-d81043ba703e")
    selected[0]["moderation_submission_id"] = UUID("559c7d10-a470-4498-a9d2-d81043ba703e")
    selected[0]["permission_submission_id"] = UUID("559c7d10-a470-4498-a9d2-d81043ba703e")
    assert target.source_binding_diagnostics(selected) == {}
    assert selected[0]["story_id"] == "559c7d10-a470-4498-a9d2-d81043ba703e"


def test_private_manifest_contains_only_expected_source_metadata():
    result = target.validate_rows(target.select_rows(rows()))
    assert len(result["sources"]) == 8
    assert result["sources"][0]["story_id"] == "story-0"
    assert result["selection"]["selected_stories"] == 8
    assert result["rights_scope"].endswith("NO_TRAINING_OR_REDISTRIBUTION")
    assert result["non_actions"]["train_admitted"] == 0
    assert result["non_actions"]["quality_v1_admitted"] == 0
