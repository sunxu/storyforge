# R60 P2-A 第二模型独立交叉审核协议 v1

日期：2026-11-09

## 目的

对 Development-20 的 60 个维度判断增加第二模型独立交叉审核，识别第一模型的潜在错误、遗漏和上下文问题。第二模型输出只作为 `AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`，不能替代 Owner 最终语义复核，也不能直接写入官方 `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`。

## 已确认事实

- 原 60 条 semantic checks 是 Owner AI 生成，未经 Owner 逐项最终确认。
- 原文件缺少 reviewer_role、reviewer_ref、rubric_version，且额外包含 unresolved_context。
- 原 AI checks 不符合官方七字段合同，也不能通过回溯性元数据补齐伪装为 Owner 独立复核。
- 原 AI checks、35 条 AI history advisory、4 条 AI history advisory 均保持原样封存，只作参考，不作为第二模型输入。
- 原始 20 条 Owner results 是第二模型的核对对象；模型必须独立判断 Owner verdict/evidence 是否成立，不得默认其正确。

## 第二模型输入

Builder 仅读取：
1. `OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl`
2. `OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl`
3. 公开 Rubric v2.1 文件

Builder 明确不读取：
- `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`
- `OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_PRIVATE.jsonl`
- `OWNER_SUPPORTED_HISTORY_COMPLETENESS_AI_REVIEW_4_PRIVATE.jsonl)
- 任何第一模型的输出或建议

Builder 为 20 个案例生成全新 blind IDs 并重新打乱顺序。模型包只含 visible_history、target_text、verified_world_components，以及每个维度待核对的 Owner verdict、evidence、rule_basis、context_coverage。旧 calibration IDs 与 ID map 不进入模型包；ID map 单独留在 Owner 私有目录。

## 模型选择与执行

- 使用与第一模型不同的模型提供方/模型家族。可选择 Claude 或 Gemini 的可用模型；实际模型 ID、版本、调用日期、参数和服务端返回的完成状态必须由执行者记录。
- 不宣称不同供应商即天然无偏；交叉审核仍是 AI Advisory。
- 同一批 20 案例 × 3 维度，共 60 项；必须完整覆盖。
- 模型必须看到完整上下文和对应 Owner verdict/evidence，但不得看到第一模型的 semantic checks 或 AI Advisory。
- 若外部模型服务的隐私/数据处理条件未获用户确认，不得上传私有故事正文；可先只生成本地私有包并暂停外发。
- 不使用 P3 模型训练/GPU/HF Job；本步骤是外部模型辅助内容审核，不启动训练任务。

## 第二模型输出合同

每个 `blind_id × dimension` 恰好一行，输出 JSONL：
- `blind_id`
- `dimension`
- `reviewer_type=AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`
- `conclusion=SUPPORTS_VERDICT | DOES_NOT_SUPPORT_VERDICT | INSUFFICIENT_CONTEXT`
- `reviewed_evidence_indexes`
- `reasoning_summary`
- `unresolved_context`

所有引用索引必须完整覆盖该维度全部 evidence；不得只挑选有利证据。不得更改 Owner verdict。不得因缺少来源、版权、权利、隐私、授权或数据隔离材料而 HOLD；故事内玩家明确拒绝/同意/选择边界、故事硬规则和安全边界仍是内容审核依据。

## Owner 最终复核

第二模型完成后：
1. 将 60 条 AI Advisory 与原始 Owner results、第一模型 Advisory 作差异分析。
2. 按维度列出一致、分歧、第二模型新发现的遗漏、HOLD。
3. Owner 对全部 60 项作最终判断；至少对所有模型分歧项逐条阅读原文、证据和上下文。
4. 只有 Owner 实际完成最终复核的项目，才可生成官方语义复核记录；每行记录实际审核时间、Owner role/ref、rubric version、完整 evidence indexes 和 Owner 自己的 reasoning。
5. 不能复制第二模型 conclusion/reasoning 后直接标记为 Owner。Owner 必须形成自己的判断和理由。
6. 所有未解决项保留 HOLD。AI 一致率不是通过门槛。

## 版本与隔离

- 第二模型私有输出目录 create-only，目录 0700，文件 0600。
- 私有 manifest 绑定原始 packets/results/rubric、第二模型输入包、ID map、prompt 的 SHA-256。
- SAFE 只记录聚合计数和边界，不输出正文、case IDs、blind IDs、reviewer refs、私有 SHA。
- 第二模型结果不得进入模型训练、Prompt 开发或 P2-B held-out labels。
- 本协议不改变 P2-A 20/60 官方 verifier 合同，也不解锁 Locked20 / Severe10。
