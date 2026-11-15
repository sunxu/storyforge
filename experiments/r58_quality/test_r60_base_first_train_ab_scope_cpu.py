"""Synthetic-only A/B fast-lane risk scopes, no private sources or DB."""
import pytest
import r60_base_first_train_ab_scope_cpu as target
from test_r60_base336_world_review_decisions_template_cpu import groups as fake_groups


def inputs():
    groups = fake_groups()
    # Preserve 38 Story IDs and exactly 82 unique frozen candidate positions.
    for group in groups:
        for index, member in enumerate(group["members_PRIVATE"]):
            member["candidate_positions_1based_PRIVATE"] = [index + 1]
            if index < 22:
                member["candidate_positions_1based_PRIVATE"].extend(
                    [39 + index * 2, 40 + index * 2]
                )
    return groups, {
        "remaining_full_r50_hold": [{"position": i} for i in range(1, 337)],
    }, {
        "cases_checked": 336,
        "provider_execution_independence_verified": False,
        "reviewer_independence_verified": False,
        "side_source_counts": {
            "a_V1": 305, "a_V2": 27, "a_V3": 4,
            "b_V1": 187, "b_V2": 11, "b_V3": 138,
        },
        "v1_pool_config_owner_attestation_present": False,
    }


def test_ab_exact_risk_partition_never_promotes():
    groups, manifest, reviewer = inputs()
    a, b, safe = target.analyze(
        groups, manifest, reviewer, roster_sha="a" * 64)
    assert a["known_world_risk_cases"] == 82
    assert a["outside_known_risk_cases"] == 254
    assert len(a["not_in_known_eight_groups_positions_1based_PRIVATE"]) == 254
    assert not (set(a["known_world_risk_positions_1based_PRIVATE"]) &
                set(a["not_in_known_eight_groups_positions_1based_PRIVATE"]))
    assert b["reviewer_independence_verified"] is False
    assert safe["train_admitted"] == 0
    assert safe["status"].endswith("BOTH_HOLD")


def test_no_provider_independence_claim_allowed():
    groups, manifest, reviewer = inputs()
    reviewer["provider_execution_independence_verified"] = True
    with pytest.raises(target.Hold, match="REVIEW_SCOPE_HOLD"):
        target.analyze(groups, manifest, reviewer, roster_sha="a" * 64)


def test_unknown_world_position_fails_closed():
    groups, manifest, reviewer = inputs()
    groups[0]["members_PRIVATE"][0]["candidate_positions_1based_PRIVATE"] = [1000]
    with pytest.raises(target.Hold, match="WORLD_82_SCOPE_HOLD"):
        target.analyze(groups, manifest, reviewer, roster_sha="a" * 64)


def test_missing_one_frozen_candidate_fails_closed():
    groups, manifest, reviewer = inputs()
    manifest["remaining_full_r50_hold"].pop()
    with pytest.raises(target.Hold, match="FROZEN_336_HOLD"):
        target.analyze(groups, manifest, reviewer, roster_sha="a" * 64)


def test_source_hash_required():
    groups, manifest, reviewer = inputs()
    with pytest.raises(target.Hold, match="ROSTER_HASH_HOLD"):
        target.analyze(groups, manifest, reviewer, roster_sha="placeholder")
