---
name: storyforge-roleplay-sft
version: 0.1.5
language: zh-CN
description: 只读盘点 RolePlay Supabase，按世界隔离筛选多轮 SFT 候选、重放与审核、可选 Teacher 辅助、冻结 Dataset v0.4 并在 Hugging Face CPU 验证。严格保护 R50；明确请求的 HF CPU 预检可执行，不自动启动 GPU。
---

# StoryForge RolePlay SFT · R58

> **2026-11-01 质量优先主线修订：** Owner 的目标是训练高质量中文互动剧情 LoRA，**不要求**生产请求原始字节、历史服务器部署 SHA、Provider request_id 或历史运行时精确回放。这一决定优先于下述 v0.1 旧流程的 G2 回放要求；详见 `docs/plans/R58_LORA_QUALITY_FIRST_MAINLINE_20261101.md` 与 `docs/R58_QUALITY_V1_SFT_CANDIDATE_REVIEW_CN.md`。新 `experiments/r58_quality/quality_v1.py` 是**独立、只读、非准入**的质量候选检查器；旧 `r58_intake.py` 的 G2 相关字段不得伪造为 true，旧代码/冻结合同尚未迁移。保留世界隔离、R50 密封保护、双审、last_round Collator 审计及 GPU 单独授权。

## 适用时机
当用户要求从 RolePlay Supabase 构建 StoryForge SFT 数据、盘点世界与对话、开展 R58 数据审核或冻结 Dataset v0.4 时使用。

## 权限及事实约定
- 已收到 Owner 关于角色、作品、对话及训练使用权的总体声明。按既定项目约定登记为 `OWNER_ATTESTED`，不要反复索要相同声明；这与每条回复的文本质量、目标时点世界规则和历史泄漏门禁相互独立。
- 数据库工具仅使用只读连接及 `SELECT`/元数据查询，明确禁止 DDL/DML、函数副作用、写入临时表、SQL 注入式拼接。
- RolePlay 是生产数据库，优先读 `analytics_story_lifetime` + `user_stories`，不扫描全量 600 万消息全文；对消息内容的读取只能针对经批准的私有会话小批量进行。
- 数据集构建、Tokenizer/Collator 等项目计算在 Hugging Face 环境执行。用户明确要求执行相关工作流时，可直接提交所需的最小 HF CPU Job，无需逐 Job 费用授权；若用户只要求计划/检查则不提交。GPU 推理/训练仍需单独明确授权。
- R50 保护测试内容禁止访问，禁止从中做训练/开发集选择；已有 R55/R57 开发题不得冒充新独立评估集。
- 任何 PRIVATE 原文、Owner Key、逐案标识、用户身份、模型原始输出不得推送普通 GitHub。只允许 SAFE 汇总和非敏感工具源码。

## HF Token 预检复用（每次先检查）

开始 SFT、Gold/文学双审、Held-out、Tokenizer 或 Collator 工作之前，必须先读取仓库 AGENTS.md 的第 2.1–2.2 节及 docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md，盘点已有脚本、历史 SAFE 回执与合成测试。不得仅因为轮次变化重新编写预检器或重复发起付费 HF CPU Job。

1. 共享核心：src/storyforge_dataset/token_preflight.py 是 input_ids 提取、Chat Template 编码、Token 预算和 Prompt 指纹的唯一新代码权威。HF 私有目录使用经过字节核对的 token_core.py 副本。新项目写轻量数据和 Prompt 适配器，不复制底层算法。
2. 已有入口：R58 13 条文学双审使用 experiments/r58_quality/r58_hf_cpu_literary_token_preflight.py 与 r58_hf_gpu_literary_reviewer.py；先检索 R50、R53、R58 CPU132 的历史工具与证据。不同 Prompt 或模型不得借用旧轮次的 Token PASS。
3. 缓存优先：仅当私有输入原始字节、完整序列化 Prompt、代码指纹、模型及不可变 revision、Tokenizer/Transformers 版本、Chat Template/思考模式、上下文及输出预留预算完全一致，才可复用此前可信 HF CPU 结果。使用 --verify-cache-only 做不加载 Tokenizer 的回执核验；不同则 HOLD 并按既有工具重算。当前 R58 实现仅支持整批 13 条缓存复用，不宣称已有跨样本增量缓存。
4. 执行环境：真实 Tokenizer、Chat Template、input_ids 统计仅在 HF CPU 运行；Mac 只做分发、输入完整性、私人同步及 SAFE 回执核验。禁止使用 len(BatchEncoding) 的字段数代替 Token 数；禁止静默截断。
5. 两种检查不能互相替代：通用模型 Token 数核验不是 ms-swift 实际 Collator / last_round 监督标签验证；Token PASS 也不是文学质量、卡片适用性或训练准入。
6. 保留安全边界：用户明确要求 HF CPU 预检工作流时，按要求提交最小必要 CPU Job，无需逐 Job 费用授权；GPU 推理/训练仍需单独明确授权。A/B 私有内容及结果各自隔离，Owner crosswalk 不进入任何评审 Job；日志和 GitHub 只允许 SAFE 汇总，不输出私人逐案正文。


7. 失败诊断：CPU 预检必须使用固定 SAFE 阶段码定位输入校验、Tokenizer 加载、Chat Template 渲染和 Token ID 解析；禁止输出原始异常消息、Prompt、Token ID 或私人路径。诊断码只定位失败，不自动改变 HOLD/PASS。

## 工具变更执行顺序

1. 先查找仓库现有工具、共享核心、SAFE 证据与合成测试。
2. 优先复用；仅在通用能力缺失时扩展共享核心，项目差异保留为薄适配器。
3. 添加覆盖正常、失败、重试上限、隐私与幂等行为的合成回归测试。
4. 更新 Skill 执行顺序及对应 `docs/standards/` 完整技术规范。
5. 最后按私人 STAGE 刷新规则升级代码；已有真实 checkpoint 时拒绝覆盖，不自动提交 GPU。

R58 文学评审遇到 `RESPONSE_NONEXACT_QUOTE` 时，先读取 SAFE 字段诊断和 checkpoint 清单。引用必须是来源单条消息或目标回复中的严格连续原文；只允许一次受控纠错。纠错采用候选索引选择：模型只能返回候选索引，候选由程序从可见历史的单条 user/assistant 消息或 target_text 中切取，绝不从 unapproved_card 取值；程序只替换失败引用位置并再次执行完整严格校验。纠错模型不能修改评分或任何其他评审字段。候选缺失/过多、Token 超限、索引无效或最终校验失败，一律 HOLD，不保存 checkpoint，不放宽引用标准。SAFE 诊断不得包含引用原文、模型原始响应或私人路径。遇到 `RESPONSE_SEVERE_MUST_REJECT` 时，不得仅凭错误码推断具体问题；必须读取 SAFE 的 `case_index`、`model_decision`、`active_severe_flags` 和 `active_severe_flag_count`。若旧回执没有这些字段，明确标记根因未定位；先增强 SAFE 诊断并补合成测试，再决定是否对未完成样本进行有界重试。完整规范见 `docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md`。

每次修复/新增工具应更新可复用共享模块或薄适配器、合成回归测试及使用文档，不更改历史冻结脚本或证据。若已有私人 STAGE 需要更新代码，使用 r58_hf_gpu_review_stage.py --refresh-code 的校验流程；已有 GPU 评审检查点时拒绝覆盖。
## 快速入口
1. 先检查项目 ref、`transaction_read_only=on`、Schema 与表结构。参考 `queries/01_story_inventory.sql`。
2. 通过 `queries/02_story_shortlist.sql` 得到无正文、无用户 ID 的故事统计 CSV。只选择少量故事，不直接导出所有聊天。
3. 在 HF 私有工作区使用 `python scripts/r58_intake.py shortlist --input stories.csv --output selected_private.jsonl --limit 30` 得到候选故事；此结果是 `SHORTLIST_ONLY`，**不是训练准入**。
4. 由独立世界/分支图、历史 SFT 指纹索引与保护集**元数据证明**审查；在分割世界前不得查看潜在最终测试世界的对话正文。
5. 对 Owner 已批准的训练候选按 `queries/03_private_session_export_template.sql` 使用参数化只读查询小批量导出。仅 HF 私有目录保留正文；不得直接把含用户数据的原始内容回传聊天或 GitHub。
6. 逐案判断来源世界/角色卡作为离线训练上下文是否适用，结合可见历史、Gold、硬规则和人物关系审核；导出时卡片是待审快照，不应冒充原始生产 System。**Quality-v1 不要求历史生产请求字节或部署 SHA 精确重放**。无法确定关键事实时质量结论 HOLD，不伪造旧回放证据。
7. 审核结果遵循 `reference/REVIEW_AND_TEACHER_POLICY_CN.md`，两位独立 Reviewer 均须给证据；Teacher 产物只能先作为候选。
8. 使用 Quality-v1 质量评审和独立双审证据核验。旧 `r58_intake.py gate` 保留为历史 G2 旧合同的结构验证入口，**不能作为 Quality-v1 正式准入的替代**，也不能把未验证旧 G2 字段设为 true。
9. 世界组件切分、训练集候选质量和 Owner 批准达到当前 Quality-v1 规则后，方可进入新冻结流程。旧 `r58_intake.py freeze` 依赖旧 G2 结构门禁，迁移之前不可直接用于新质量主线，也不得借用旧 Freeze 状态冒充正式准入。
10. 优先核验能否复用已有真实 Token 预检回执；必要时在 HF CPU 使用目标任务完全相同的模型 revision、Tokenizer、Chat Template 和预算重算 `input_ids`。SFT 单独执行真实 ms-swift `last_round` 标签掩码和 Collator 审计。Owner 对 GPU Job 及预算另行授权；本 Skill **不自动训练**。

## Gate 定义
- `G0`: 训练变量、输入配方、冻结模型与准入协议确认；`B_PROMPT` 与 `B_DATAFIX` 分开。
- `G1`: 来源库存与故事级分池，来源授权 Owner 声明与历史训练曝光元数据、R50 隔离证明。
- `G2`（旧版历史回放合同）：目标时点 System、世界卡和部署信息的精确复现要求保留在旧工具/冻结证据中，但**不是当前 Quality-v1 高质量 LoRA 的必需条件**；旧布尔字段不得臆造 PASS。当前主线独立审核可信卡片的离线适用性、可见历史和 Gold 一致性。
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
