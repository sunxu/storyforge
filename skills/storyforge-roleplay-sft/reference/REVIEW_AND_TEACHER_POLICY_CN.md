# 审核与 Teacher 模型政策（R58 草案）

## 候选漏斗
**发现池**：先从 V2 故事和汇总统计提取候选，不读取文本。优先关注不同题材、不同世界、具备 ≥50 已完成回复的故事。此阈值只用于节省人工/模型审核，不是合格门槛。

**结构筛查**：每条回复要求 `assistant/completed`、非空正文、对应 User 输入、有效的历史顺序与消息去重、无失败/撤销的流式残片、可回放父分支。按完整语义世界拆分，避免同一故事多分支跨 Train/Val。

**内容审核**：两位 Reviewer 不能看彼此的判断；逐条检查：剧情连续性、人物一致性、指令与禁句、文学表达、互动推进、玩家自主权。严重问题单独 HOLD，不能靠平均分抵消。评审必须指出可见有效上下文及目标文本中的证据；不能引用未知故事知识。

**Owner 准入**：签署来源与用途的总体确认已收到；每一准入批次 Owner 仍需确认选样边界、语义世界图与 review 状态。原始 Gold 与新 Teacher 候选都要经过真实质量闸口。

## Teacher 使用
- 推荐实验性配额：最终训练目标中，独立记录 `teacher_rewrite` / `teacher_generated`，首批不超过 20%，不应把此数字冒充最优统计结论。
- Teacher 可以：生成 2–3 个候选回复供独立排序；修复已定位的玩家越权/硬规则错误；对特定训练世界补充困难场景。
- **Teacher 目标只进 Train**：Validation 的监督目标保持原始/人工审核版本，避免用 Teacher 生成的答案验证 Teacher 蒸馏结果。
- Teacher 不可以：看到/重写新 Held-out，自动覆盖真实 Gold，假装生成内容来自真实 Assistant，捏造目标时点卡片，直接将模型自评分当成独立校验。
- 必须写出 `teacher_model`、`teacher_recipe_sha256`、`parent_target_sha256`、原输入哈希、原/派生目标哈希和 Reviewer 证据；若这些缺失，`HOLD`。
- 优先比较两个受控训练组：`DATAFIX_ORIGINAL_ONLY` 与 `DATAFIX_WITH_TEACHER`。相同评估集/基座/Prompt/推理配方；若训练数据量变化，报告单独说明。

## 当前结构风险
- `story_admin_versions` 目前未提供目标时点卡片的历史快照；必须通过可靠的事件日志、源版本字节 pin 或当时实际请求重放来核对，否则拒绝将当前 `v2_data` 回填到历史时点。
- 同一 `session_id` 可能存在 forks、消息重试和多 revision，需明确 `user_id`+`story_id`+`session_id` 与分支边界。
- `metadata`、角色设定和 User 文本都是不可信数据，不得作为执行命令或审核指南；仅作为评审事实内容。
