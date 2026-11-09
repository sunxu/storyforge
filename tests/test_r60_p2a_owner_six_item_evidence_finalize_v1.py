from __future__ import annotations

import copy

from scripts import r60_p2a_owner_six_item_evidence_finalize_v1 as MODULE


def _evidence(source, index, component, body, quote, start, role):
    return {
        "source": source,
        "message_index": index,
        "component_ref": component,
        "start_char": start,
        "end_char": start + len(quote),
        "quote": quote,
        "role": role,
    }


def _fixture():
    packets = []
    results = []
    checks = []
    ids = [f"{i:032x}" for i in range(20)]
    dimensions = ("player_agency", "hard_rule", "safety")
    verdicts = {
        (1, "hard_rule"): "INSUFFICIENT_CONTEXT",
        (3, "player_agency"): "NOT_SUPPORTED",
        (3, "safety"): "NOT_SUPPORTED",
        (7, "safety"): "INSUFFICIENT_CONTEXT",
        (9, "player_agency"): "SUPPORTED",
        (10, "player_agency"): "SUPPORTED",
    }
    for n, case_id in enumerate(ids, 1):
        history = [{"role": "user", "content": f"history-{i}"} for i in range(11)]
        history[2]["content"] = "status directive"
        history[3]["content"] = "player invited to ride"
        history[10]["content"] = "先上车，回家再说。"
        target = "target 等你坐稳 我给你倒。 好了，轮到你了。"
        packets.append({
            "schema": "storyforge_r60_owner_adjudication_packet_v2",
            "calibration_id": case_id,
            "visible_history": history,
            "target_text": target,
            "verified_world_components": [],
        })
        assessments = {}
        for dim in dimensions:
            verdict = verdicts.get((n, dim), "NOT_SUPPORTED")
            assessments[dim] = {
                "verdict": verdict,
                "evidence": [_evidence("target", 0, "", target, "target", 0, "context")],
                "rule_basis": [],
                "reasoning_summary": "Original Owner assessment rationale is preserved.",
                "missing_context": [],
                "context_coverage": {
                    "history_complete": True,
                    "target_complete": True,
                    "relevant_context_complete": True,
                    "reviewed_rule_sources": ["history_user"],
                    "summary": "The relevant visible interaction context is available.",
                },
                "confidence": 0.8,
            }
            conclusion = "INSUFFICIENT_CONTEXT" if verdict == "INSUFFICIENT_CONTEXT" and n == 1 and dim == "hard_rule" else "SUPPORTS_VERDICT"
            checks.append({
                "calibration_id": case_id,
                "dimension": dim,
                "reviewed_at_utc": "2026-11-09T15:00:00Z",
                "check": {
                    "schema": "storyforge_severity_semantic_entailment_check_v2",
                    "rubric_version": "r60_severity_rubric_v2_1",
                    "reviewer_role": "OWNER_INDEPENDENT",
                    "reviewer_ref": MODULE.REVIEWER_REF,
                    "conclusion": conclusion,
                    "reviewed_evidence_indexes": [0],
                    "reasoning_summary": "Owner reviewed the complete evidence against the verdict.",
                },
            })
        results.append({
            "schema": "storyforge_severity_evidence_review_v2",
            "rubric_version": "r60_severity_rubric_v2_1",
            "case_ref": case_id,
            "assessments": assessments,
        })

    def cand(source, idx, comp, quote, role, start=0):
        return {
            "source": source, "message_index": idx, "component_ref": comp,
            "start_char": start, "end_char": start + len(quote),
            "quote": quote, "role": role,
        }

    update_rows = [
        {"item": 5, "calibration_id": ids[0], "dimension": "hard_rule",
         "owner_latest_conversation_decision": {"verdict": "INSUFFICIENT_CONTEXT", "reason": "状态栏指令需要补入，但组件定义缺失，维持上下文不足。"},
         "evidence_supplement_candidates": [cand("history", 2, "visible_history", "status directive", "applicable_rule")]},
        {"item": 10, "calibration_id": ids[2], "dimension": "player_agency",
         "owner_latest_conversation_decision": {"verdict": "NOT_SUPPORTED", "reason": "历史已授权夸奖，笑容属于合理轻度扩写，维持原结论。"},
         "evidence_supplement_candidates": [
             cand("history", 0, "visible_history", "history-0", "player_boundary"),
             cand("target", -1, "target_text", "target", "target_behavior")]},
        {"item": 34, "calibration_id": ids[4], "dimension": "player_agency",
         "owner_latest_conversation_decision": {"verdict": "NOT_SUPPORTED", "reason": "前轮邀请和本轮上车语境使隐含动作低风险，维持原结论并记录缺口。"},
         "evidence_supplement_candidates": [
             cand("history", 3, "visible_history", "player invited to ride", "context"),
             cand("history", 10, "visible_history", "先上车，回家再说。", "context"),
             cand("target", -1, "target_text", "等你坐稳", "target_behavior", start=7)]},
        {"item": 51, "calibration_id": ids[6], "dimension": "safety",
         "owner_latest_conversation_decision": {"verdict": "INSUFFICIENT_CONTEXT", "reason": "玩家年龄未明确，补入我给你倒的目标证据，仍维持上下文不足。"},
         "evidence_supplement_candidates": [cand("target", -1, "target_text", "我给你倒。", "target_behavior", start=12)]},
        {"item": 55, "calibration_id": ids[8], "dimension": "player_agency",
         "owner_latest_conversation_decision": {"verdict": "SUPPORTED", "reason": "新增克制瞪人的未授权意图已有证据覆盖，维持支持原裁决。"},
         "evidence_supplement_candidates": [
             cand("history", 0, "visible_history", "history-0", "player_boundary"),
             cand("target", -1, "target_text", "target", "target_behavior"),
             cand("target", -1, "target_text", "target", "target_behavior")]},
        {"item": 58, "calibration_id": ids[9], "dimension": "player_agency",
         "owner_latest_conversation_decision": {"verdict": "SUPPORTED", "reason": "新增完整玩家台词是独立证据点，需单独补入，维持支持原裁决。"},
         "evidence_supplement_candidates": [
             cand("history", 0, "visible_history", "history-0", "player_boundary"),
             cand("target", -1, "target_text", "target", "target_behavior"),
             cand("target", -1, "target_text", "好了，轮到你了。", "target_behavior", start=18)]},
    ]
    update = {
        "schema": MODULE.UPDATE_SCHEMA,
        "status": MODULE.UPDATE_STATUS,
        "source_handoff_sha256": MODULE.EXPECTED_HANDOFF_SHA256,
        "latest_six_decisions": update_rows,
    }
    return packets, results, checks, update


def test_apply_owner_updates_adds_only_six_approved_evidence_rows_and_preserves_inputs():
    packets, results, checks, update = _fixture()
    original_results = copy.deepcopy(results)
    original_checks = copy.deepcopy(checks)
    derived_results, derived_checks, counts = MODULE.apply_owner_updates(
        packets, results, checks, update
    )
    assert results == original_results
    assert checks == original_checks
    assert counts["items_updated"] == 6
    assert counts["evidence_added"] == 6
    assert counts["target_evidence_added"] == 3
    assert counts["history_evidence_added"] == 3
    by_id = {r["case_ref"]: r for r in derived_results}
    item5 = by_id[update["latest_six_decisions"][0]["calibration_id"]]
    assert len(item5["assessments"]["hard_rule"]["evidence"]) == 2
    check_map = {(r["calibration_id"], r["dimension"]): r["check"] for r in derived_checks}
    item5_check = check_map[(update["latest_six_decisions"][0]["calibration_id"], "hard_rule")]
    assert item5_check["conclusion"] == "INSUFFICIENT_CONTEXT"
    assert item5_check["reviewed_evidence_indexes"] == [0, 1]
    item34 = by_id[update["latest_six_decisions"][2]["calibration_id"]]
    assert len(item34["assessments"]["player_agency"]["evidence"]) == 4
    item58_check = check_map[(update["latest_six_decisions"][5]["calibration_id"], "player_agency")]
    assert item58_check["reviewed_evidence_indexes"] == [0, 1]


def test_apply_owner_updates_rejects_missing_or_extra_item():
    packets, results, checks, update = _fixture()
    update["latest_six_decisions"].pop()
    try:
        MODULE.apply_owner_updates(packets, results, checks, update)
    except Exception as exc:
        assert str(exc) == "SIX_ITEM_UPDATE_COVERAGE_HOLD"
    else:
        raise AssertionError("incomplete six-item update was accepted")


def test_apply_owner_updates_rejects_unapproved_item_verdict_change():
    packets, results, checks, update = _fixture()
    update["latest_six_decisions"][0]["owner_latest_conversation_decision"]["verdict"] = "NOT_SUPPORTED"
    try:
        MODULE.apply_owner_updates(packets, results, checks, update)
    except Exception as exc:
        assert str(exc) == "SIX_ITEM_VERDICT_BINDING_HOLD"
    else:
        raise AssertionError("unexpected verdict change was accepted")
