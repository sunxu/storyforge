# R58 GPU 文学评审：严格引用诊断与单次纠错规范

状态：实现已提交；合成回归测试通过；B 槽位 GPU 重试尚未获新的费用批准。

## 1. 目标与边界

评审输出必须提供可复核的逐字引用。RESPONSE_NONEXACT_QUOTE 表示至少一个引用不是其允许来源中的严格连续子串。该错误是证据格式失败，不是文学评分结论。

- specific_source_quotes：每一段必须完整存在于一条可见历史 user/assistant 消息中；禁止从未批准卡片引用、跨消息拼接或意译。
- specific_target_quotes：每一段必须完整存在于目标回复中。
- 不得通过模糊匹配、去标点、Unicode 归一化、忽略空格或编辑距离放宽标准。
- 未通过严格校验的响应不写 checkpoint；不得将 HOLD 伪装为 PASS。
- 纠错最多一次，只允许修改两个引用列表。决策、评分、严重标记、卡片状态、文学评价及不确定性必须与第一次响应完全一致。

## 2. SAFE 诊断数据

QuoteValidationError 只保存结构元数据，不保存失败引用文本：

- field：specific_source_quotes 或 specific_target_quotes
- quote_index：引用数组中的 0-based 索引；数组结构错误时可为 null
- source_candidate_count：允许搜索的来源消息数；目标文本固定为 1
- case_index：13 条盲审批次中的 0-based 索引
- repair_attempted：是否已尝试唯一一次纠错

失败时 SAFE 输出允许包含上述字段和固定 reason code。严禁输出引用内容、原始模型响应、Prompt、Token ID、故事标识、私有文件路径或异常 traceback。

## 3. 受控纠错流程

1. 对第一次 JSON 执行完整字段、评分、严重标记与严格引用校验。
2. 只有 RESPONSE_NONEXACT_QUOTE 触发纠错；其他错误直接 HOLD。
3. 将原评审 Prompt、第一次模型 JSON 和安全的失败字段/索引追加为纠错上下文。
4. 要求模型重新输出完整 JSON，但明确只允许修改 specific_source_quotes 与 specific_target_quotes。
5. 用同一 JSON Schema、同一模型、同一 SamplingParams 再生成一次；不递归、不循环、不自动重试。
6. 用同一 validate_response 重新校验，并逐字段比较非引用字段。任何非引用字段变化均以 QUOTE_REPAIR_CHANGED_NONQUOTE_FIELDS HOLD。
7. 对纠错 Prompt 重新计算实际 Token ID；若加上输出预留超过上下文预算，使用 QUOTE_REPAIR_TOKEN_BUDGET_EXCEEDED HOLD。
8. 只有纠错结果完整通过全部校验后才写入原本应写入的 checkpoint。首次失败响应永不保存为 checkpoint。

成功 SAFE 汇总增加 quote_repair_attempts 与 quote_repair_successes，不包含引用正文。

## 4. 固定失败码

| Reason code | 含义 |
|---|---|
| RESPONSE_NONEXACT_QUOTE | 首次或纠错后的引用仍不精确 |
| QUOTE_REPAIR_TOKEN_BUDGET_EXCEEDED | 纠错 Prompt 超出预算 |
| QUOTE_REPAIR_GENERATION_INCOMPLETE | 纠错生成被截断或未正常结束 |
| QUOTE_REPAIR_RESPONSE_INVALID | 纠错输出不是有效 JSON |
| QUOTE_REPAIR_CHANGED_NONQUOTE_FIELDS | 纠错改变了评分或其他非引用字段 |
| RESPONSE_JSON_INVALID | 首次输出不是有效 JSON |

诊断字段只帮助定位，不改变 HOLD/PASS/REJECT 语义。

## 5. 合成回归测试

experiments/r58_quality/test_r58_hf_gpu_literary_reviewer.py 必须覆盖：

- 来源引用错误和目标引用错误分别返回字段名与 0-based 索引。
- 异常消息中不含失败引用原文。
- 一次纠错成功后只保存严格校验通过的 checkpoint。
- 纠错仍失败时不产生任何 checkpoint。
- 纠错不得修改 decision、scores、flags、卡片状态、文学评价或 uncertainty。
- 既有 checkpoint 身份校验、不可覆盖、Token 预算及训练准入边界保持不变。

测试使用虚构样本和 FakeTokenizer/FakeEngine，不访问真实故事、不加载模型权重、不调用 GPU。

## 6. B Pilot 当前状态

2026-11-01 B 槽位报告 R58_HF_GPU_REVIEW_HOLD / RESPONSE_NONEXACT_QUOTE。SAFE 输出未包含私人文本；B 输出 Bucket 未发现两个 checkpoint。由于首次失败的原始生成内容没有被保存，无法从现有证据确定是哪一条引用不精确。

本规范实现与合成测试通过后，仍需在 B 私有 STAGE 中升级 runner，并重新进行 CPU-only 预检。任何新的 B GPU Job 都是额外付费重试；在 Owner 明确批准新费用上限前不得提交。A 已有两个有效 checkpoint，不得覆盖或用新代码重跑。

## 7. 权威实现

- 运行器：experiments/r58_quality/r58_hf_gpu_literary_reviewer.py
- 合成测试：experiments/r58_quality/test_r58_hf_gpu_literary_reviewer.py
- AI 执行顺序：skills/storyforge-roleplay-sft/SKILL.md

共享 Tokenizer 算法仍唯一位于 src/storyforge_dataset/token_preflight.py；本规范不复制或替代该核心。
