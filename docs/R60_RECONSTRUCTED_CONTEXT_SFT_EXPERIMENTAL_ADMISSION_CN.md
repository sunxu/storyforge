# R60 重建上下文 SFT 实验线：准入合同（草案，非训练授权）

状态：`EXPERIMENTAL_REVIEW_REQUIRED__NOT_TRAINING_AUTHORIZED`。本文件不改变严格 Gold192 Quality-v1 准入标准；不允许把重建的历史上下文称为真实发送给 Provider 的输入。

## 路线边界

- **STRICT_GOLD_QUALITY_V1**：仅接受经过独立真实输入 A 类取证，或独立完整且逐项可复核的历史构建 B 类重建，并满足原有 Reviewer、Owner、Protected Set、世界隔离、曝光检查和 Binder。不能由评分通过、Stage 状态、Owner 文件存在自动升级。
- **RECONSTRUCTED_CONTEXT_SFT_EXPERIMENTAL**：单独的数据集 ID、目录、冻结清单、审核结果、训练运行和评估报告。每条必须明确 `context_provenance=RECONSTRUCTED_NOT_ACTUAL_SENT`；不可在报表中与 Strict Gold 准入合并统计。
- **不能作训练来源的案例**：权益或隐私未核实、世界/Protected Set 边界不清、来源存在已知训练或验证污染且不可清晰标记、最终目标是被后处理或续写混合且无匹配监督语义的案例。

## 单条样本需要的证据（全部 Owner 私有）

1. **身份**：冻结 Case ID、Story/Session/Turn/Target SHA、来源快照及不可变清单校验；排除集不得回流。
2. **历史重建**：准确写明用到的 Ledger 事件边界、系统提示词版本、角色/世界卡版本、记忆注入、历史清洗/裁剪、模型路由和可能的重试分支；未知步骤必须列出，不能填造。明确此输入**未证明曾被发送**。
3. **监督目标**：明确目标是单次 Provider completion 还是 UI 最终交付的组合/过滤结果；若无法建立合法的单次 Assistant loss 标签语义，HOLD。
4. **质量与边界**：复核 Quality-v1 六维评分、Reviewer 独立性、Owner rights/privacy、世界隔离、Protected Set 元数据检查、历史 Train/Validation/Test 曝光。R50 Held-out 及其正文严禁访问。
5. **审核结论**：必须为具体案例逐项签核并保留来源引用、签核人/时间、原件 PIN；自动 True / 模板 Owner 字段不算审核。
6. **训练设计**：新 Train/Validation 世界拆分，避免角色与上下文近重复泄漏。仅监督最终 Assistant 目标，历史 Assistant 不参与 loss；记录 tokenizer 版本、系统 token 长度、截断风险和 collator mask。

## Gate

| Gate | 必须满足 | 不满足的结论 |
|---|---|---|
| E0 来源与权益 | 冻结来源、身份及使用权确认 | HOLD |
| E1 重建透明度 | 每条列明构建步骤、未知部分、原始输入未证明 | HOLD |
| E2 监督一致性 | 目标可解释为合法 SFT 标签，重试/续写/改写有记录 | HOLD |
| E3 质量与边界 | Reviewer/Owner、世界隔离、隐私、Protected Set 与历史曝光独立核实 | HOLD |
| E4 数据冻结 | 不混入 Strict Gold，独立 Train/Validation、manifest SHA | HOLD |
| E5 CPU-only | tokenizer/collator 全量通过，无越界长度/非法 loss mask | HOLD |
| E6 GPU 审批 | Owner 明确批准实验运行参数、GPU 规格、预算与输出路径 | **不得启动 GPU** |

**无最低样本数**，但不足以独立形成有意义的 Train/Validation 时，必须作出“不足以训练”结论，不能通过降低门槛凑数。任何案例无充分证据，应留 HOLD；允许阶段性关闭一次性可行性调查，不等于宣布所有 Gold192 都是 D 类。

## P6 后的决策

- 若 25 条现有 Owner 物料出现真实 Request/Attempt 提示，仅对命中案例做身份与 Payload 完整性取证；提示字段不等于可信请求。
- 若无提示，记录 `EXISTING_OWNER_METADATA_NO_REQUEST_HINTS`，不扩大扫描、不复跑旧失败的 Reply Job / Diagnostic Archive 调查。
- 实验线 E0–E5 可在 Mac CPU-only 和独立 Owner 审核下推进；E6 不获明确授权则停止在 `EXPERIMENTAL_GPU_NOT_AUTHORIZED`。
- 发布 SAFE 只包含聚合数量、状态和工具版本；禁止输出私有 ID、路径、故事正文、系统提示词、请求内容与任何 R50 内容。
