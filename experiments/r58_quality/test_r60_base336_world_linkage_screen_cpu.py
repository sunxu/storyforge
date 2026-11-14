"""Synthetic exact world linkage screen; no semantic inferences or admissions."""
import pytest
import r60_base336_world_linkage_screen_cpu as linkage
from test_r60_base_start_cpu336_template_audit import sample


def source():
    cases, manifest = sample()
    # The preview contract requires 172 distinct story IDs across 336 cases.
    for item in manifest["remaining_full_r50_hold"]:
        pos = item["position"]
        src = cases[pos - 1]["source"]
        src.update({
            "story_id": f"world-{(pos - 4) % 172}",
            "session_id": f"session-{pos}",
            "assistant_message_id": f"assistant-{pos}",
            "prior_user_message_id": f"prior-user-{pos}",
            "previous_assistant_message_id": f"prior-assistant-{pos}",
            "previous_user_message_id": f"earlier-user-{pos}",
        })
        cases[pos - 1]["history_messages_sha256"] = f"history-{pos}"
        cases[pos - 1]["assistant_target_sha256"] = f"target-{pos}"
    return cases, manifest


def test_no_shared_keys_only_story_disjoint_is_not_semantic_cert():
    cases, manifest = source()
    out = linkage.screen(cases, manifest)
    assert out["cases_checked"] == 336
    assert out["distinct_story_ids"] == 172
    assert out["structural_components"] == 172
    assert out["exact_linked_story_pairs"] == 0
    assert out["world_component_isolation_verified"] is False
    assert out["train_admitted"] == 0


def test_cross_story_same_target_hash_creates_link():
    cases, manifest = source()
    cases[4]["assistant_target_sha256"] = cases[3]["assistant_target_sha256"]
    out = linkage.screen(cases, manifest)
    assert out["edge_counts"]["target_exact_sha"] == 1
    assert out["exact_linked_story_pairs"] == 1
    assert out["multi_story_components"] == 1
    assert out["world_component_isolation_verified"] is False


def test_reused_session_creates_link():
    cases, manifest = source()
    cases[5]["source"]["session_id"] = cases[3]["source"]["session_id"]
    out = linkage.screen(cases, manifest)
    assert out["edge_counts"]["source_session"] == 1
    assert out["structural_components"] == 171


def test_missing_message_id_fails_closed():
    cases, manifest = source()
    del cases[3]["source"]["prior_user_message_id"]
    with pytest.raises(linkage.Hold, match="SOURCE_MESSAGE_HOLD"):
        linkage.screen(cases, manifest)
