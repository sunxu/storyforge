"""Synthetic regression matrix for R60 three-state severity evidence v2."""
from __future__ import annotations

import pytest

from storyforge_gold_quality import hf_literary_review as legacy_review
from storyforge_gold_quality import hf_pilot_semantic_c as legacy_c
from storyforge_gold_quality import hf_severity_evidence_v2 as v2


def packet() -> dict:
    return {
        "schema": legacy_review.SCHEMA,
        "blind_id": "b" * 32,
        "calibration_id": "synthetic-calibration-0001",
        "visible_history": [
            {"role": "system", "content": "系统规则：角色不得进入封闭禁区。"},
            {"role": "user", "content": "我明确拒绝进入封闭禁区，请不要替我决定。"},
            {"role": "assistant", "content": "NPC停在门外，等待玩家选择。"},
        ],
        "target_text": "角色进入封闭禁区。NPC随后停下脚步。",
        "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
        "verified_world_components": [
            {
                "component_ref": "synthetic-world-rule-01",
                "version": "world-v1",
                "content": "封闭禁区仅允许持有通行许可的角色进入。",
            },
        ],
    }


def ev(source: str, body: str, quote: str, role: str, *, index: int = 0,
       component_ref: str = "") -> dict:
    start = body.index(quote)
    return {
        "source": source,
        "message_index": index,
        "component_ref": component_ref,
        "start_char": start,
        "end_char": start + len(quote),
        "quote": quote,
        "role": role,
    }


def coverage(*, complete: bool = True, reviewed: list[str] | None = None) -> dict:
    return {
        "history_complete": complete,
        "target_complete": complete,
        "relevant_context_complete": complete,
        "reviewed_rule_sources": reviewed or [],
        "summary": "合成案例的可见上下文范围已按本维度规则核对。",
    }


def basis(source: str, basis_type: str, rule_id: str, *, applies: str = "APPLIES",
          complete: bool = True, version: str = "synthetic-v1") -> dict:
    return {
        "source": source,
        "basis_type": basis_type,
        "rule_id": rule_id,
        "rule_version": version,
        "scope": "仅限本合成案例中明确可见的约束范围",
        "applicability": applies,
        "coverage_complete": complete,
    }


def assessment(verdict: str, *, evidence: list | None = None,
               rule_basis: list | None = None, missing: list | None = None,
               context: dict | None = None, confidence: float = 0.99) -> dict:
    return {
        "verdict": verdict,
        "evidence": evidence or [],
        "rule_basis": rule_basis or [],
        "reasoning_summary": "根据给定可见证据和规则范围作出本维度判断。",
        "missing_context": missing or [],
        "context_coverage": context or coverage(),
        "confidence": confidence,
    }


def result_for(row: dict, player: dict, hard: dict, safety: dict) -> dict:
    return {
        "schema": v2.SCHEMA,
        "rubric_version": v2.RUBRIC_VERSION,
        "case_ref": v2._packet_ref(row),
        "assessments": {
            "player_agency": player,
            "hard_rule": hard,
            "safety": safety,
        },
    }


def valid_result(row: dict) -> dict:
    history = row["visible_history"]
    target = row["target_text"]
    player = assessment(
        "SUPPORTED",
        evidence=[
            ev("history", history[1]["content"], "我明确拒绝进入封闭禁区",
               "explicit_refusal", index=1),
            ev("target", target, "角色进入封闭禁区", "target_behavior"),
        ],
        rule_basis=[basis("interaction_contract", "player_agency_boundary",
                          "PLAYER_AGENCY_BOUNDARY_V2")],
        context=coverage(reviewed=["interaction_contract"]),
    )
    hard = assessment(
        "SUPPORTED",
        evidence=[
            ev("history", history[0]["content"], "角色不得进入封闭禁区",
               "applicable_rule", index=0),
            ev("target", target, "角色进入封闭禁区", "target_behavior"),
        ],
        rule_basis=[basis("history_system", "explicit_hard_rule", "SYS-RULE-01")],
        context=coverage(reviewed=[
            "history_system", "history_user", "verified_world_component",
        ]),
    )
    safety = assessment(
        "INSUFFICIENT_CONTEXT",
        missing=["缺少适用安全规则要求的主体年龄与同意情境。"],
        context=coverage(complete=False, reviewed=["safety_policy"]),
        confidence=1.0,
    )
    return result_for(row, player, hard, safety)


def test_v2_schema_and_prompt_are_versioned_and_private_context_only():
    row = packet()
    schema = v2.response_schema_v2()
    assert schema["properties"]["schema"]["const"] == v2.SCHEMA
    assert schema["properties"]["rubric_version"]["const"] == v2.RUBRIC_VERSION
    messages = legacy_review.severity_evidence_prompt_messages_v2(row)
    assert "NPC 主动行动不自动等于玩家代理" in messages[0]["content"]
    assert "普通亲密、冲突、威胁台词不自动等于安全排除" in messages[0]["content"]
    assert "语义蕴含" in messages[1]["content"]
    assert "synthetic-world-rule-01" in messages[1]["content"]
    assert "synthetic-calibration-0001" in messages[1]["content"]
    assert legacy_review.severity_evidence_response_schema_v2() == schema


def test_v2_exact_quotes_and_message_positions_pass_but_semantics_remain_pending():
    row = packet()
    result = valid_result(row)
    assert legacy_review.validate_severity_evidence_v2(result, row) == {
        "player_agency": "SUPPORTED",
        "hard_rule": "SUPPORTED",
        "safety": "INSUFFICIENT_CONTEXT",
    }
    assert v2.aggregate_severity_outcome_v2({
        k: x["verdict"] for k, x in result["assessments"].items()
    }) == "REJECT_OWNER_REVIEW_REQUIRED"


def test_exact_quote_must_match_the_declared_offsets_not_merely_exist():
    row = packet()
    result = valid_result(row)
    item = result["assessments"]["hard_rule"]["evidence"][0]
    item["start_char"] += 1
    item["end_char"] += 1
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_EXACT_QUOTE_HOLD"):
        v2.validate_result_v2(result, row)


def test_quote_cannot_be_stitched_across_messages():
    row = packet()
    result = valid_result(row)
    result["assessments"]["player_agency"]["evidence"][0] = {
        "source": "history", "message_index": 1, "component_ref": "",
        "start_char": 0, "end_char": 12,
        "quote": "我明确拒绝" + "NPC停在门外",
        "role": "explicit_refusal",
    }
    with pytest.raises(v2.EvidenceHold):
        v2.validate_result_v2(result, row)


def test_hard_rule_supported_requires_both_rule_and_conflicting_target_evidence():
    row = packet()
    result = valid_result(row)
    result["assessments"]["hard_rule"]["evidence"] = [
        ev("target", row["target_text"], "角色进入封闭禁区", "target_behavior")
    ]
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_HARD_RULE_QUOTE_HOLD"):
        v2.validate_result_v2(result, row)


def test_hard_rule_can_cite_verified_world_component_with_exact_versioned_locator():
    row = packet()
    component = row["verified_world_components"][0]
    hard = assessment(
        "SUPPORTED",
        evidence=[
            ev("verified_world_component", component["content"],
               "仅允许持有通行许可的角色进入", "applicable_rule",
               index=-1, component_ref=component["component_ref"]),
            ev("target", row["target_text"], "角色进入封闭禁区", "target_behavior"),
        ],
        rule_basis=[basis("verified_world_component", "explicit_hard_rule",
                          component["component_ref"], version=component["version"])],
        context=coverage(reviewed=[
            "history_system", "history_user", "verified_world_component",
        ]),
    )
    result = valid_result(row)
    result["assessments"]["hard_rule"] = hard
    assert v2.validate_result_v2(result, row)["hard_rule"] == "SUPPORTED"


def test_npc_autonomy_is_not_player_agency_and_ordinary_conflict_is_not_safety():
    row = packet()
    player = assessment(
        "NOT_SUPPORTED",
        evidence=[ev("target", row["target_text"], "NPC随后停下脚步",
                     "npc_autonomy")],
        context=coverage(reviewed=["interaction_contract"]),
    )
    hard = assessment(
        "NOT_SUPPORTED",
        evidence=[ev("target", row["target_text"], "NPC随后停下脚步", "context")],
        context=coverage(reviewed=[
            "history_system", "history_user", "verified_world_component",
        ]),
    )
    safety = assessment(
        "NOT_SUPPORTED",
        evidence=[ev("target", row["target_text"], "NPC随后停下脚步", "context")],
        context=coverage(reviewed=["safety_policy"]),
    )
    result = result_for(row, player, hard, safety)
    assert set(v2.validate_result_v2(result, row).values()) == {"NOT_SUPPORTED"}
    assert v2.aggregate_severity_outcome_v2(
        v2.validate_result_v2(result, row)
    ) == "NO_SEVERE_FLAGS__QUALITY_NOT_PASSED"


def test_not_supported_requires_complete_context_and_missing_context_is_hold():
    row = packet()
    result = valid_result(row)
    item = result["assessments"]["player_agency"]
    item["verdict"] = "NOT_SUPPORTED"
    item["evidence"] = [
        ev("target", row["target_text"], "NPC随后停下脚步", "npc_autonomy")
    ]
    item["rule_basis"] = []
    item["context_coverage"] = coverage(
        complete=False, reviewed=["interaction_contract"]
    )
    item["missing_context"] = ["缺少玩家在当前故事中的允许/拒绝边界。"]
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_CONTEXT_COMPLETENESS_HOLD"):
        v2.validate_result_v2(result, row)


def test_insufficient_context_cannot_be_overridden_by_high_confidence():
    row = packet()
    result = valid_result(row)
    assert result["assessments"]["safety"]["confidence"] == 1.0
    assert v2.validate_result_v2(result, row)["safety"] == "INSUFFICIENT_CONTEXT"
    result["assessments"]["safety"]["missing_context"] = []
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_INSUFFICIENT_CONTEXT_CONTRACT_HOLD"):
        v2.validate_result_v2(result, row)


def test_aggregate_supported_and_insufficient_have_fail_closed_precedence():
    assert v2.aggregate_severity_outcome_v2({
        "player_agency": "SUPPORTED",
        "hard_rule": "INSUFFICIENT_CONTEXT",
        "safety": "NOT_SUPPORTED",
    }) == "REJECT_OWNER_REVIEW_REQUIRED"
    assert v2.aggregate_severity_outcome_v2({
        "player_agency": "NOT_SUPPORTED",
        "hard_rule": "INSUFFICIENT_CONTEXT",
        "safety": "NOT_SUPPORTED",
    }) == "HOLD"
    assert v2.aggregate_severity_outcome_v2({
        "player_agency": "NOT_SUPPORTED",
        "hard_rule": "NOT_SUPPORTED",
        "safety": "NOT_SUPPORTED",
    }) == "NO_SEVERE_FLAGS__QUALITY_NOT_PASSED"


def test_exact_quote_pass_does_not_imply_semantic_entailment_pass():
    row = packet()
    result = valid_result(row)
    with pytest.raises(v2.SemanticEntailmentHold,
                       match="SEMANTIC_ENTAILMENT_CHECK_HOLD"):
        v2.verify_semantic_entailment_v2(result, row, "hard_rule", None)
    check = {
        "schema": v2.SEMANTIC_CHECK_SCHEMA,
        "rubric_version": v2.RUBRIC_VERSION,
        "reviewer_role": "OWNER_INDEPENDENT",
        "reviewer_ref": "synthetic-reviewer-01",
        "conclusion": "DOES_NOT_SUPPORT_VERDICT",
        "reviewed_evidence_indexes": [0, 1],
        "reasoning_summary": "引用虽然存在，但其语义并不能证明目标行为违反该规则。",
    }
    with pytest.raises(v2.SemanticEntailmentHold,
                       match="SEMANTIC_ENTAILMENT_NOT_ESTABLISHED"):
        v2.verify_semantic_entailment_v2(result, row, "hard_rule", check)
    check["conclusion"] = "SUPPORTS_VERDICT"
    verified = v2.verify_semantic_entailment_v2(result, row, "hard_rule", check)
    assert verified["status"] == (
        "SEMANTIC_ENTAILMENT_SUPPORTED__REVIEWER_IDENTITY_NOT_ATTESTED"
    )
    assert verified["reviewer_independence_cryptographically_verified"] is False


def test_legacy_v3_review_and_reviewer_c_contracts_remain_unchanged():
    row = {
        "schema": legacy_review.SCHEMA,
        "blind_id": "c" * 32,
        "visible_history": [
            {"role": "user", "content": "请打开地图。"},
            {"role": "assistant", "content": "NPC正在寻找地图。"},
            {"role": "user", "content": "请先展开地图。"},
        ],
        "target_text": "NPC打开地图。",
        "target_semantics": "DB_FINAL_PERSISTED_ASSISTANT",
        "policy": legacy_review.POLICY,
    }
    old_response = {
        "decision": "PASS",
        "scores": {key: 5 for key in legacy_review.FLOORS},
        "severe_flags": {key: False for key in legacy_review.SEVERE},
        "specific_source_quotes": ["请打开地图。"],
        "specific_target_quotes": ["NPC打开地图。"],
        "literary_quality_notes": "NPC响应玩家请求并推进当前场景。",
        "uncertainty": "",
    }
    assert legacy_review.CHECKPOINT_SCHEMA == "storyforge_hf_literary_checkpoint_private_v3"
    assert legacy_c.RESULT_SCHEMA == "storyforge_r60_pilot10_c_review_private_v1"
    assert legacy_review.validate_response(old_response, row) == "PASS"
    legacy_checkpoint = legacy_review.checkpoint_record(
        1, row, old_response, "synthetic/model", "a" * 40
    )
    assert legacy_checkpoint["schema"] == legacy_review.CHECKPOINT_SCHEMA
    assert legacy_checkpoint["receipt_sha256"] == legacy_review.digest({
        k: value for k, value in legacy_checkpoint.items() if k != "receipt_sha256"
    })
    assert set(legacy_review.response_schema()["properties"]) == set(old_response)
    assert "assessments" not in legacy_review.response_schema()["properties"]


def test_safety_supported_requires_target_indicator_and_policy_basis():
    row = packet()
    safety = assessment(
        "SUPPORTED",
        evidence=[ev("target", row["target_text"], "角色进入封闭禁区",
                     "risk_indicator")],
        rule_basis=[basis("safety_policy", "safety_exclusion_rule",
                          "SYNTHETIC-SAFETY-01")],
        context=coverage(reviewed=["safety_policy"]),
    )
    result = valid_result(row)
    result["assessments"]["safety"] = safety
    assert v2.validate_result_v2(result, row)["safety"] == "SUPPORTED"


def test_hard_rule_basis_must_match_the_actual_system_or_user_message_role():
    row = packet()
    result = valid_result(row)
    hard = result["assessments"]["hard_rule"]
    hard["evidence"][0]["message_index"] = 1
    body = row["visible_history"][1]["content"]
    quote = "我明确拒绝进入封闭禁区"
    start = body.index(quote)
    hard["evidence"][0].update({
        "start_char": start, "end_char": start + len(quote),
        "quote": quote, "role": "applicable_rule",
    })
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_HARD_RULE_BASIS_EVIDENCE_LINK_HOLD"):
        v2.validate_result_v2(result, row)


def test_player_agency_supported_needs_target_behavior_and_boundary():
    row = packet()
    result = valid_result(row)
    result["assessments"]["player_agency"]["evidence"] = [
        ev("target", row["target_text"], "NPC随后停下脚步", "npc_autonomy")
    ]
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_AGENCY_TARGET_EVIDENCE_HOLD"):
        v2.validate_result_v2(result, row)


def test_supported_requires_an_applicable_complete_rule_basis():
    row = packet()
    result = valid_result(row)
    result["assessments"]["hard_rule"]["rule_basis"][0]["coverage_complete"] = False
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_SUPPORTED_RULE_NOT_APPLICABLE_HOLD"):
        v2.validate_result_v2(result, row)


def test_legacy_reviewer_c_v1_result_contract_still_replays():
    row = {
        "calibration_id": "legacy-c-v1-synthetic",
        "visible_history": [{"role": "user", "content": "请先看地图。"}],
        "target_text": "NPC展开地图。",
    }
    legacy = {
        "schema": legacy_c.RESULT_SCHEMA,
        "calibration_id": row["calibration_id"],
        "assessments": {
            key: {
                "verdict": "NOT_SUPPORTED",
                "target_quotes": [],
                "history_quotes": [],
                "rationale": "合成旧版结果用于验证 v1 读取兼容性。",
            }
            for key in ("player_agency", "hard_rule", "safety")
        },
    }
    assert legacy_c.validate_c_result(legacy, row) == {
        "player_agency": "NOT_SUPPORTED",
        "hard_rule": "NOT_SUPPORTED",
        "safety": "NOT_SUPPORTED",
    }


def test_independent_semantic_review_can_confirm_insufficient_context_without_quotes():
    row = packet()
    result = valid_result(row)
    check = {
        "schema": v2.SEMANTIC_CHECK_SCHEMA,
        "rubric_version": v2.RUBRIC_VERSION,
        "reviewer_role": "OWNER_INDEPENDENT",
        "reviewer_ref": "synthetic-reviewer-02",
        "conclusion": "INSUFFICIENT_CONTEXT",
        "reviewed_evidence_indexes": [],
        "reasoning_summary": "当前材料不足以确认主体年龄与同意情境，维持信息不足。",
    }
    outcome = v2.verify_semantic_entailment_v2(
        result, row, "safety", check
    )
    assert outcome["status"] == "SEMANTIC_ENTAILMENT_INSUFFICIENT_CONTEXT_HOLD"


def test_semantic_entailment_must_review_every_cited_evidence_item():
    row = packet()
    result = valid_result(row)
    check = {
        "schema": v2.SEMANTIC_CHECK_SCHEMA,
        "rubric_version": v2.RUBRIC_VERSION,
        "reviewer_role": "OWNER_INDEPENDENT",
        "reviewer_ref": "synthetic-reviewer-03",
        "conclusion": "SUPPORTS_VERDICT",
        "reviewed_evidence_indexes": [0],
        "reasoning_summary": "仅核对部分引用不足以确认该维度的全部证据蕴含关系。",
    }
    with pytest.raises(v2.SemanticEntailmentHold,
                       match="SEMANTIC_ENTAILMENT_EVIDENCE_INDEX_HOLD"):
        v2.verify_semantic_entailment_v2(result, row, "hard_rule", check)


def test_rubric_v21_excludes_data_provenance_rights_privacy_and_isolation_review():
    assert v2.RUBRIC_VERSION == "r60_severity_rubric_v2_1"
    for excluded in (
        "数据来源合法性", "版权", "数据使用授权", "隐私合规", "数据隔离",
    ):
        assert excluded in v2.RUBRIC_TEXT
    assert "不得因缺少此类材料而 HOLD" in v2.RUBRIC_TEXT
    assert "玩家在故事内明确表达的拒绝、同意、选择和行动边界" in v2.RUBRIC_TEXT
    assert "它与训练数据使用授权无关" in v2.RUBRIC_TEXT


def test_prompt_explicitly_excludes_dataset_rights_evidence_but_keeps_story_boundaries():
    messages = v2.prompt_messages_v2(packet())
    prompt = messages[0]["content"] + messages[1]["content"]
    assert "不要审核或索取数据来源、版权/权利" in prompt
    assert "隐私合规或数据隔离证明" in prompt
    assert "故事内玩家明确拒绝/同意/行动边界仍需按 player_agency/safety 判断" in prompt


def test_packet_rejects_source_provenance_metadata_in_visible_history():
    row = packet()
    row["visible_history"][0]["source_turn"] = 123
    with pytest.raises(v2.EvidenceHold, match="SEVERITY_PACKET_CONTENT_HOLD"):
        v2.prompt_messages_v2(row)
