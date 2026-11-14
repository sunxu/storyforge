"""R60 first-train constructed-System V1: source-aware *candidate* assembly.

Pure CPU code; no DB, network, model weights, train file, or admission.
Actual story-source provenance and Qwen/ms-swift collator remain independent
mandatory gates. Caller assertions are NOT evidence of historical validity.
"""
from __future__ import annotations

from dataclasses import dataclass

CONTRACT_ID = "R60_BASE_CONSTRUCTED_SYSTEM_V1"
PROVENANCE = "TRAINING_CONSTRUCTED_NOT_HISTORICAL"
GENERIC_SYSTEM = (
    "你正在创作中文互动小说。保持文笔自然、角色性格与既定事实一致；让NPC在合理动机下主动行动，"
    "推动故事发生变化，但不要替玩家决定内心、台词、行动或不可撤销的选择。遵守当前故事已提供的规则、"
    "时间线和明确禁令；未知事实保持未知，不擅自补造设定。根据此前对话继续情节，回应用户当前输入，"
    "不复述指令或输出审核说明。"
)


class ContractHold(ValueError):
    pass


@dataclass(frozen=True)
class SourceBoundFact:
    field_path: str
    content: str
    story_id: str
    revision_id: str
    # This records the caller's provenance claim, NOT independent verification.
    target_time_proof_ref: str


def _assert_text(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ContractHold("EMPTY_TEXT_HOLD")
    return value


def _validate_fact(fact: SourceBoundFact, field_prefix: str) -> None:
    if type(fact) is not SourceBoundFact:
        raise ContractHold("UNBOUND_SOURCE_FACT_HOLD")
    if not (fact.field_path == field_prefix
            or fact.field_path.startswith(field_prefix + ".")):
        raise ContractHold("FIELD_PATH_HOLD")
    for item in (fact.content, fact.story_id, fact.revision_id,
                 fact.target_time_proof_ref):
        _assert_text(item)
    # Never accept placeholder "latest" source as a historical provenance.
    if fact.revision_id.casefold() in {"latest", "unknown", "current"}:
        raise ContractHold("UNVERSIONED_FACT_HOLD")


def assemble_candidate(
    history: list[dict],
    target: str,
    *,
    history_turns: tuple[int, int, int],
    target_turn: int,
    world: SourceBoundFact | None = None,
    roles: SourceBoundFact | None = None,
) -> dict:
    """Create a proposed last-assistant-only example; ALWAYS train_admitted=0.

    SourceBoundFact references are claims that later source validators must
    verify, not evidence that its content actually existed at target time.
    """
    if (type(history) is not list or len(history) != 3
            or type(history_turns) is not tuple or len(history_turns) != 3
            or any(type(t) is not int or t < 0 for t in history_turns)
            or type(target_turn) is not int or
            not history_turns[0] < history_turns[1] <
            history_turns[2] < target_turn):
        raise ContractHold("HISTORY_CHRONOLOGY_HOLD")
    roles_expected = ("user", "assistant", "user")
    messages = []
    for expected, row in zip(roles_expected, history, strict=True):
        if type(row) is not dict or set(row) != {"role", "content"}:
            raise ContractHold("MESSAGE_SHAPE_HOLD")
        if row["role"] != expected:
            raise ContractHold("ROLE_ORDER_HOLD")
        messages.append({"role": expected, "content": _assert_text(row["content"])})
    _assert_text(target)
    if world is not None:
        _validate_fact(world, "v2_data.world")
    if roles is not None:
        if (type(roles) is not SourceBoundFact or
                not (roles.field_path == "v2_data.character"
                     or roles.field_path == "v2_data.characters"
                     or roles.field_path.startswith("v2_data.character.")
                     or roles.field_path.startswith("v2_data.characters."))):
            raise ContractHold("ROLE_SOURCE_PATH_HOLD")
        _validate_fact(roles, "v2_data")
    if world is not None and roles is not None and world.story_id != roles.story_id:
        raise ContractHold("CROSS_STORY_CARD_HOLD")
    system = GENERIC_SYSTEM
    if world is not None:
        system += "\n\n当前故事世界规则（来源绑定候选，须核验时序）：\n" + world.content
    if roles is not None:
        system += "\n\n当前故事角色设定（来源绑定候选，须核验时序）：\n" + roles.content
    all_messages = [{"role": "system", "content": system}, *messages,
                    {"role": "assistant", "content": target}]
    return {
        "contract_id": CONTRACT_ID,
        "provenance_label": PROVENANCE,
        "messages": all_messages,
        "assistant_target_index": 4,
        "source_fact_independent_verification": False,
        "actual_collator_verified": False,
        "world_component_isolation_verified": False,
        "reviewer_independence_verified": False,
        "r50_complete_exclusion_verified": False,
        "train_admitted": 0,
    }
