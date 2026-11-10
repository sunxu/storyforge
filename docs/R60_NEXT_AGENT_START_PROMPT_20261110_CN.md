# 2026-11-10 执行状态更新（优先于下方原始启动快照）

**接手时不要再做 P2-B Owner 逐案审核；Owner 已确认 30/30 裁决与 90/90 语义复核。** 当前任务是补齐正式回执并解决真实 HOLD：

1. P2-B 30/90 候选已在工作副本合并并通过 locator/quote/schema/evidence-index 结构预检；这不是 Owner Mac 正式私有包，也不是官方 Verifier PASS。
2. Safety 第21、22条保留 Owner `SUPPORTED`；具体适用安全规则 ID、版本、scope 仍需从获准正式政策来源核实。不得臆造 Rule ID，不得改写 Owner Verdict。核实后运行独立 30/90 官方 Verifier，生成真实 Final SAFE。
3. P3 已完成三个模型的静态 revision/config/template 元数据核查。CPU tokenizer/template/token-budget 仍待执行；GLM-Z1 的 sampling 与 greedy 官方指引存在冲突，先解决 profile。
4. P2-B 聚合状态见 [SAFE 进度记录](evidence/R60_P2B_OWNER_30_90_PROGRESS_SAFE_20261110.md)；P3 模型 pins 见 [静态预检](R60_P3_MODEL_STATIC_PREFLIGHT_20261110_CN.md)。
5. 仍禁止 GPU、付费 HF Job、1000 条批量审核和 SFT；Quality-v1 admitted=0。实时核对 PR #25 当前 HEAD 与五组 CI，PR 保持 Draft。

---

# StoryForge R60 后续 Agent 接手提示词（P2-A 完成后）

版本：v1.0，2026-11-10。此文件是可直接复制到新 Agent 的**正式执行指令**，不包含私有故事正文。

## 直接交给新 Agent 的提示词

你现在接手 `sunxu/storyforge` R60 Quality 校准与模型评估工程。请使用已经连接的 GitHub 仓库直接完成任务，不要从头重建已验收成果。

### 仓库、工作区和准确信息

- 仓库：`sunxu/storyforge`
- 工作分支：`r60/gold192-history-v3-adapter`
- PR：[#25](https://github.com/sunxu/storyforge/pull/25)，base `r60/canonical-a-v3-binding`，交接时状态 Open/Draft
- 主线 Issue：[#26](https://github.com/sunxu/storyforge/issues/26)；执行 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)，均不因 P2-A 收尾而自动关闭
- 交接前一次核对的 PR head：`352fd48d50f5f24402b2bef849240833f6ab270e`，该 SHA 五组 Actions completed/success。该 SHA 是历史快照；**先实时重新查询分支/PR head 与对应五组 Actions**，不得假设仍为最新。
- Owner Mac 常用工作树：`/Users/keedle/workspace/storyforge-r60-ledger-diagnostics`；存在多个 worktree，先 `git worktree list` 确认正确分支，**不要在 detached HEAD 工作树强行 git switch**。
- Owner 私有根目录：`$HOME/.local/share/storyforge/r60/private/`；新 Agent 不可假定能直接访问 Owner Mac。若无授权连接通道，仅生成可执行命令与 SAFE 核验，不声称本地已执行。

### 已经完成、不可重做的阶段

1. **P0 PASS**：Gold72=40（Development20/Locked Regression20），R60 Severe10=10；50 个唯一来源案例。Gold72 分割按案例、不要求 Story 互斥：Development Story=5、Locked Story=6、shared Story=5，`story_disjoint=false`。跨集合 exact history/target/full-history-target overlap=0。不要修改冻结分割。
2. **P1 PASS**：Rubric v2.1、Schema、Prompt、合成回归及旧 v3 兼容已通过。仅评估 Player Agency、Hard Rule、Safety 三维内容语义；不把数据来源、版权、授权、隐私或数据隔离证明作为此轮审核门槛。
3. **P2-A COMPLETE（官方 Verifier 通过）**：Owner Mac 实际运行 `scripts/r60_owner_adjudication_verify_v2.py`，SAFE：`OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED`；`cases_verified=20`、`semantic_checks_verified=60`，其中 `semantic_supported_count=58`、`semantic_insufficient_context_count=1`、`semantic_not_established_count=1`。两项 HOLD 保留，`owner_identity_cryptographically_attested=false`，`quality_v1_admitted=0`，`training_authorized=false`、`gpu_started=false`。此状态证明 P2-A 审核和回执技术验收完成，**不代表所有案例质量通过或训练获准**。
4. P2-A 遗留的 80 个 evidence locator 经过派生副本协议迁移；39 条历史完整性状态依据 Owner 已作批准落实（35 NOT_SUPPORTED + 4 SUPPORTED），4 个 SUPPORTED Player Agency basis type 规范化；不覆盖原始文件。原始 60 条 AI Advisory 与 Claude 第二模型建议只作历史辅助材料；最终 60 行是独立的派生正式回执。不要重新跑 P2-A、重写 58/1/1、为消除 HOLD 伪造确认或冒充密码学身份。
5. P2-A 官方 SAFE 已记入 [Issue #28 的正式验收回帖](https://github.com/sunxu/storyforge/issues/28#issuecomment-6745451510)。接手时检查 Issue 正文/文档是否已同步，不得把旧“未完成”快照当成新事实。

### 本次唯一主要目标：P2-B + P3 CPU 阶段，为之后 P4 独立评估做好准备

**第一优先级：P2-B 独立 held-out Owner references**

- 仅 Gold72 Locked Regression20 + R60 Severe10：20+10=30 条，3 维共 90 个语义复核单元。与 P2-A Development20 的 20/60 完全分开；不将其混为 50/150 直接调用现有 Verifier。
- 先核对 P0 已冻结 manifest、ID/split、目标指纹与交集检查；读取数据须仅在 Owner 允许的受控私有环境，保持 Locked Regression 和 Severe10 的 blind 与标签封存，**不得在三模型预测和 checkpoint 冻结前向模型暴露 Owner labels、旧裁决或 ID Map**。
- 实现可复用、版本化的 P2-B packet builder、Owner results/semantic-check schema、独立 30/90 verifier、synthetic 回归与 SAFE 聚合；优先复用 P2-A 官方契约和固定失败码，而不是复制大段代码。所有结构/定位/引用/UTC/reviewer-binding 验证均 fail-closed，真实语义不足保留 HOLD。
- 必须区分“P2-B 工程预检 PASS”“Owner 30 条独立裁决完成”“90 条语义复核通过”“held-out 已冻结”四个状态。缺少 Owner 私有审核时只标记待审核，禁止伪造完成。
- 不得重新分割 Gold72、扩大 30 条集合、重写旧 A/B/C、阅读 R50 私有 held-out 文本或上传任何私有正文到 GitHub。

**第二优先级：P3 三模型固定与 CPU 预检**

- 在 P2-B 工程准备不受阻的情况下并行推进仅 CPU 的工程事项：核对计划中 Qwen3、GLM-4、GLM-Z1 的**精确模型版本/commit/revision、tokenizer/chat template、推理参数、输入截断策略、对等上下文预算与成本**。如果上位计划的型号与当前可用端点不一致，形成可比较的模型固定方案，记录待 Owner 决定，不暗中换模型。
- 复用既有 HF Runtime、依赖 profile、Jinja2/Chat Template 故障回归；测试 tokenizer/collator、三模型输入一致性、固定 prompt/rubric hash、预算和回执 schema。
- CPU 预检不可触发模型 inference、GPU HF Job 或私有外发，除非 Owner 已单独明确授权相应动作。CPU 自身如产生收费资源也先告知和确认。
- P4 GPU 三模型配对实验、P6 冻结 1000 条正式批量审核、SFT 均仍是独立授权门禁；**不要为了赶进度跳过 held-out 泄漏防线或训练准入**。

### 一开始实际做什么

1. 阅读本提示词、[主任务书](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md)、[执行任务书](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)、[交接总览](R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md)、[交接索引](R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md)、[上位计划](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md)；旧章节如写 P2-A 未开始，以 2026-11-10 最新状态区块和官方 SAFE 为准。
2. 重新读取 PR #25 / Issues #26/#28 当前实际状态、五组 CI；区分当前 HEAD 和历史 SHA。查看已有 P2-B/P3 代码资产与测试，复用可用实现；不要做无关项目清理。
3. 列出 P2-B 的工程缺口与最短可执行方案，随即直接创建代码、合成测试、SAFE 报告和必要文档；使用 GitHub 当前分支 commit；需要 Owner Mac 时提供单次最短的受控命令及输出格式，不要反复让用户重复上传既有材料。
4. 可与 P2-B 同步推进 P3 只读固定与 CPU 准备；以本轮完成的真实结果更新 Issue #28 和任务书。未经测试不要宣称 PASS，未经授权不要启动 GPU。
5. 每个动作结束汇报：本次提交 SHA/文件/CI 状态、阶段 PASS/HOLD、下一项唯一阻塞、是否用了付费 CPU/HF/GPU、原件是否改动。

### 完成标准与行为约束

- P2-B 工程交付：30/90 独立协议/脚本/测试与可重复 CPU/本地预检真实 PASS；私有 labels 在 Owner 审核后单独封存，未审核不能谎称 PASS。
- P3 交付：三模型可复现 revision/prompt/runtime/参数与 CPU preflight SAFE；未获 GPU 授权停在 P3，报告后续 P4 必要输入及预算。
- P2-A 不再追加无关审核、不消除两项真实语义 HOLD、不把 NOT_SUPPORTED 直接当文学质量 PASS。
- 不修改 RolePlay/生产数据库、不提交私有历史内容/ID Map/token/DSN；不在 GitHub 或外部模型输出私人文本；中文文档和错误信息优先。
- 不用“等我后台完成”承诺；有工具立即做，有权限或证据缺口就给出最小阻塞与下一步。
- PR #25 仍为 Draft，合并必须基于当前代码、CI、审查与分支策略另行判断，**不能因为 P2-A PASS 就自动合并**。

请直接开始：实时检查仓库 → 复用现有实现 → 推进 P2-B 独立 30/90 Builder/Verifier 和 P3 CPU 预检；只有真正需要 Owner 的私有裁决或外部执行权限才反馈给我。