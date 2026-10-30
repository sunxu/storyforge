---
name: storyforge-roleplay-sft
version: 0.1.0
language: zh-CN
description: 只读盘点 RolePlay Supabase，按世界隔离筛选多轮 SFT 候选、重放与审核、可选 Teacher 辅助、冻结 Dataset v0.4 并在 Hugging Face CPU 验证。严格保护 R50，不自动启用付费计算。
---

# StoryForge RolePlay SFT · R58

## 适用时机
当用户要求从 RolePlay Supabase 构建 StoryForge SFT 数据、盘点世界与对话、开展 R58 数据审核或冻结 Dataset v0.4 时使用。

## 权限及事实约定
- 已收到 Owner 关于角色、作品、对话及训练使用权的总体声明。按既定项目约定登记为 `OWNER_ATTESTED`，不要反复索要相同声明；这与每条回复的文本质量、目标时点世界规则和历史泄漏门禁相互独立。
- 数据库工具仅使用只读连接及 `SELECT`/元数据查询，明确禁止 DDL/DML、函数副作用、写入临时表、SQL 注入式拼接。
- RolePlay 是生产数据库，优先读 `analytics_story_lifetime` + `user_stories`，不扫描全量 600 万消息全文；对消息内容的读取只能针对经批准的私有会话小批量进行。
- 数据集构建、Tokenizer/Collator 等项目计算在 Hugging Face 环境执行。此 Skill 在未获授权时只能制定计划、检查元数据与构建脱敏工件；不提交收费 HF CPU/GPU Job。
- R50 保护测试内容禁止访问，禁止从中做训练/开发集选择；已有 R55/R57 开发题不得冒充新独立评估集。
- 任何 PRIVATE 原文、Owner Key、逐案标识、用户身份、模型原始输出不得推送普通 GitHub。只允许 SAFE 汇总和非敏感工具源码。

## 快速入口
1. 先检查项目 ref、`transaction_read_only=on`、Schema 与表结构。参考 `queries/01_story_inventory.sql`。
2. 通过 `queries/02_story_shortlist.sql` 得到无正文、无用户 ID 的故事统计 CSV。只选择少量故事，不直接导出所有聊天。
3. 在 HF 私有工作区使用 `python scripts/r58_intake.py shortlist --input stories.csv --output selected_private.jsonl --limit 30` 得到候选故事；此结果是 `SHORTLIST_ONLY`，**不是训练准入**。
4. 由独立世界/分支图、历史 SFT 指纹索引与保护集**元数据证明**审查；在分割世界前不得查看潜在最终测试世界的对话正文。
5. 对 Owner 已批准的训练候选按 `queries/03_private_session_export_template.sql` 使用参数化只读查询小批量导出。仅 HF 私有目录保留正文；不得直接把含用户数据的原始内容回传聊天或 GitHub。
6. 重建单条回复产生时的确切 System、角色/世界快照、导演动态状态、分支父历史、完整 User/Assistant 顺序。**不能用今天的 `v2_data` 代替目标时点内容**。不能确定则 `HOLD_RUNTIME_REPLAY`。
7. 审核结果遵循 `reference/REVIEW_AND_TEACHER_POLICY_CN.md`，两位独立 Reviewer 均须给证据；Teacher 产物只能先作为候选。
8. 运行 `python scripts/r58_intake.py gate --input reviewed_private.jsonl --output decision_private.jsonl --safe-output gate_safe.json`，只返回状态和证据完整性，不输出正文。
9. 用经 Owner 确认的世界组件切分、经过门禁的完整私有输入执行 `python scripts/r58_intake.py freeze --input ready_private.jsonl --decision decision_private.jsonl --output-dir NEW_PRIVATE_DIR --world-graph-sha SHA256`。失败不生成部分数据。输出标记 `CONTENT_FREEZE_ONLY__HF_CPU_PREFLIGHT_PENDING`。
10. 在 Hugging Face CPU 使用原定 Qwen 修订、ms-swift 模板，检查 `last_round` 标签掩码、输入长度和 collator。通过后另由 Owner 对具体 GPU Job 及预算独立授权；本 Skill **不自动训练**。

## Gate 定义
- `G0`: 训练变量、输入配方、冻结模型与准入协议确认；`B_PROMPT` 与 `B_DATAFIX` 分开。
- `G1`: 来源库存与故事级分池，来源授权 Owner 声明与历史训练曝光元数据、R50 隔离证明。
- `G2`: 每一回复的精确目标时点 System/世界卡/历史重建、分支图与 SHA256 证据。
- `G3`: 双独立 Reviewer 质量与安全审核；争议 HOLD；Teacher 来源可追踪；Owner 单独签核。
- `G4`: 整个语义世界组件只允许落入一个 Train/Val/Protected 分区；候选与已曝光世界不得误标为新 Held-out。
- `G5`: 私有 SFT JSONL 冻结、逐字节哈希、SAFE 回执；HF CPU tokenizer/collator 预检另行通过。
- `G6`: 获独立授权后才允许 HF GPU 训练（此 Skill 不执行）。

## 严格状态语义
- `SHORTLIST_ONLY` ≠ `ADMITTED`；`OWNER_ATTESTED` ≠ `QUALITY_PASS`。
- `REVIEW_PASS` ≠ `RUNTIME_REPLAY_PASS`；`STRUCTURE_PASS` ≠ `SEMANTIC_WORLD_INDEPENDENCE_PASS`。
- `CONTENT_FREEZE_ONLY` ≠ `CPU_COLLATOR_PASS` ≠ `TRAINING_AUTHORIZED`。
- 未完成任何关键门禁时 `HOLD`，不得猜测或默认 PASS。

## 既有证据与下一阶段
- 历史：Gold195 候选跨 13 个观察到的 UUID；114 条未与历史 SFT 目标产生精确哈希交集，**不表示**可以直接准入。
- RolePlay 只读调查：`user_stories` 5005 行，`story_v2_sessions` 196149 行，V2 消息约 630 万（估算）。`v2_data.world/character/director` 可用于发现结构；`story_admin_versions` 现有 0 行，所以目标时点规则必须经额外的版本证据重放。
- 本包提供的 shortlist、gate、freeze 是**离线校验工具，不是数据库自动导出器、语义评估模型或训练器**。实际 Schema/模型版本及 R57 PR #5 的代码需另行对齐与验收。
