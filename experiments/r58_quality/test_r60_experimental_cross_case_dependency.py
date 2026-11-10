"""Synthetic exact dependency graph checks; no private data."""
from __future__ import annotations

import pytest
from quality_v1 import canonical, sha
from r60_experimental_cross_case_dependency import analyze
from r60_p3_stage_pair_probe import Hold

SYSTEM = (
    "你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。\n"
    "保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。\n"
    "不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。"
)


def fixture(links=((0, 1), (1, 2))):
    targets = [f"原创目标{i}" for i in range(3)]
    previews, reviews = [], []
    for i, target in enumerate(targets):
        preceding = [targets[src] for src, dst in links if dst == i]
        history = [{"role": "assistant", "content": " / ".join(preceding) if preceding else f"原创前文{i}"},
                   {"role": "user", "content": f"用户输入{i}"}]
        original = [{"role": "system", "content": SYSTEM}, *history]
        digest = sha(target.encode())
        previews.append({
            "messages": [
                *[dict(m, loss=False) for m in original],
                {"role": "assistant", "content": target, "loss": True},
            ],
            "metadata": {
                "status": "ENGINEERING_PREVIEW_NOT_ADMITTED",
                "source_target_sha256": digest,
                "input_messages_sha256": sha(canonical(original)),
            },
        })
        reviews.append({
            "schema": "storyforge_r60_e03_ai_semantic_result_private_v1",
            "case_id": f"synthetic-{i}",
            "source_target_sha256": digest,
            "input_messages_sha256": sha(canonical(original)),
            "decision": "PASS",
            "context_provenance": "RECONSTRUCTED_NOT_ACTUAL_SENT",
            "owner_attestation": False,
            "quality_v1_admitted": False,
            "training_authorized": False,
        })
    return previews, reviews


def test_chain_forms_single_unsplittable_literal_component():
    preview, reviews = fixture()
    private, safe = analyze(preview, reviews[::-1])
    assert safe["literal_dependency_edges"] == 2
    assert safe["literal_connected_components"] == 1
    assert safe["largest_literal_component"] == 3
    assert safe["all_three_connected_by_literal_edges"]
    assert all(edge["split_across_this_edge_forbidden"] for edge in private["edges"])
    assert safe["quality_v1_admitted"] == 0


def test_independent_rows_remain_three_components():
    preview, reviews = fixture(links=())
    _, safe = analyze(preview, reviews)
    assert safe["literal_connected_components"] == 3
    assert safe["world_component_independently_verified"] is False


def test_user_quoted_prior_target_also_links_cases():
    preview, reviews = fixture(links=())
    preview[1]["messages"][-2]["content"] = "原创目标0"
    original = [{"role": m["role"], "content": m["content"]}
                for m in preview[1]["messages"][:-1]]
    new_sha = sha(canonical(original))
    preview[1]["metadata"]["input_messages_sha256"] = new_sha
    reviews[1]["input_messages_sha256"] = new_sha
    _, safe = analyze(preview, reviews)
    assert safe["literal_dependency_edges"] == 1
    assert safe["user_history_edges"] == 1


def test_unapproved_review_rejected():
    preview, reviews = fixture()
    reviews[0]["decision"] = "HOLD"
    with pytest.raises(Hold, match="REVIEW_IDENTITY_OR_STATE_INVALID"):
        analyze(preview, reviews)


def test_duplicate_review_rejected():
    preview, reviews = fixture()
    reviews[1]["source_target_sha256"] = reviews[0]["source_target_sha256"]
    with pytest.raises(Hold, match="REVIEW_DUPLICATE_TARGET"):
        analyze(preview, reviews)
