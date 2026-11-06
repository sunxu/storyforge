# R60 Gold72 Reviewer C — 独立盲审说明

**任务：** 对 40 条案例进行独立语义复核  
**审核者：** Reviewer C  
**输入：** `R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl`  
**输出：** 单个 JSON 对象，遵循本文规定的结构

## 1. 独立执行要求

1. 必须在全新、独立的执行环境中完成。优先使用 Temporary Chat（临时聊天）或无会话状态的一次性 API 请求。
2. 不得读取、搜索、请求或引用 Reviewer A、Reviewer B2、Reviewer B1 的任何审核材料、分数、决策、SAFE、分歧清单或历史对话。
3. 不得请求 Owner ID Map、原始 case_id、story_uuid、候选来源分组或筛选原因。
4. 不得使用已有聊天记忆、先前对话、文件连接器、外部搜索、代码仓库或其他工具。只允许使用本次盲审输入和本文。
5. 不得推测案例为何被选中；将 40 条视为一个未知抽样集合，逐案独立判断。
6. 如果无法满足独立执行要求，停止并返回 `REVIEW_EXECUTION_HOLD`，不得伪造完成结果。
7. 执行记录应如实记录实际可获得的 provider、model、request/session ID、开始/结束时间和完整执行转录。平台未提供的字段应明确记为不可获得，不得猜测。

新会话和输入隔离是流程控制，不等于密码学独立性证明。不得声称已验证隐藏的平台状态。

## 2. 审核依据

只依据每条案例实际提供的：
- 可见历史；
- 当前 User 输入；
- 目标 Assistant 回复；
- `review_focus` 中的审查关注点；
- 本说明中的统一评分标准。

不得从未提供的角色卡、系统提示词或世界设定中推断事实。历史若以 Assistant 消息开头，必须保留，不得自动判错。

## 3. 六维评分与最低门槛

每条案例均须给出 1–5 的整数评分：

| 维度 | 最低分 | 评价重点 |
|---|---:|---|
| `chinese_prose` 中文文学表达 | 4 | 自然、具体、有节奏，避免空洞模板化 |
| `character_consistency` 角色一致性 | 4 | 身份、关系、动机、口吻符合可见证据 |
| `npc_initiative` NPC 主动性 | 3 | NPC 能合理推进剧情，不强行替玩家行动 |
| `player_agency` 玩家自主权 | 4 | 不替玩家决定意愿、选择、台词或行动 |
| `narrative_continuity` 剧情连续性 | 4 | 人物、地点、时间、事件保持连续 |
| `rule_fidelity` 规则遵循 | 4 | 遵守明确硬设定、禁令和内容边界 |

决策规则：
- **PASS**：六维全部达到最低分，且 `severe_flags` 为空。
- **HOLD**：上下文不足、事实冲突或需要 Owner 决定。
- **REJECT**：明确违反玩家自主权、明确硬规则/禁令，或存在严重连续性错误。
- 严重问题不得被高平均分抵消。不要为了达到 PASS 数量而调整评分。

每条案例独立评分。证据摘要不超过两三句，不复制目标原文或长篇剧情。

## 4. 结果格式

返回单个 JSON 对象，不要附加 Markdown 代码围栏或长篇总结：

```json
{
  "schema": "r60_gold72_reviewer_c_results_v1",
  "reviewer": "C",
  "status": "REVIEW_COMPLETE",
  "counts": {"PASS": 0, "HOLD": 0, "REJECT": 0},
  "cases": [
    {
      "blind_case_id": "C-...",
      "target_sha256": "<输入中的原样 SHA256>",
      "scores_1_to_5": {
        "chinese_prose": 4,
        "character_consistency": 4,
        "npc_initiative": 3,
        "player_agency": 4,
        "narrative_continuity": 4,
        "rule_fidelity": 4
      },
      "decision": "PASS",
      "severe_flags": [],
      "evidence_summary": "简短说明判断依据，不复制原文。"
    }
  ]
}
```

必须覆盖全部 40 条，`blind_case_id` 不得重复，`target_sha256` 必须逐字照抄输入。六维评分必须全部是 1–5 的整数。counts 必须与 cases 的实际决策数量一致。不得输出原始 case_id、story_uuid、Owner 映射或推测的身份信息。

## 5. 完成后交付

只交付：
1. 上述完整 JSON 结果；
2. 本次执行环境实际提供的执行元数据；
3. 完整执行转录或提供方执行记录。

不要修改输入文件，不要生成训练数据，不要进行 Quality-v1 准入判断，不要启动 GPU。
