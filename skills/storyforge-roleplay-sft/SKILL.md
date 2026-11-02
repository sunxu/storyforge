---
name: storyforge-roleplay-sft
version: 0.1.9
language: zh-CN
description: 按固定工程顺序执行 StoryForge RolePlay / Quality-v1 数据工作：先查证据和工具、复用既有能力、必要时扩展共享核心、补回归测试，再更新 Skill 与技术规范。保护 R50；HF CPU 与 GPU 权限严格分离。
---

# StoryForge RolePlay SFT · R58

## 目标与适用范围

本 Skill 用于 StoryForge 的 RolePlay 来源盘点、世界隔离、多轮 SFT 候选构建、质量审核、冻结与训练前验证。唯一产品目标是训练更擅长高质量中文互动剧情的 Qwen LoRA，重点关注中文表达、人物/世界及跨轮事实一致性、NPC 主动推进、硬规则和玩家自主权。

Owner 已明确：不要求将样本认证为原始生产 Provider 请求，也不要求历史生产请求字节级回放。不得继续把历史部署 SHA、request_id 因果绑定或逐字生产 Prompt 回放当作新 Quality-v1 主线的阻塞条件。数据来源权利、上下文真实可用性、世界级隔离、质量双审、R50 保护、可复现冻结和训练前验证仍然必须满足。

## 权限与安全边界

- RolePlay 数据库只允许只读连接及 SELECT / 元数据查询；禁止 DDL、DML、函数副作用、临时表写入和不安全 SQL 拼接。
- Owner 对作品、角色和训练使用权的总体声明可登记为 `OWNER_ATTESTED`；它不代表单条样本质量通过、世界规则确认或训练准入。
- PRIVATE 原文、Owner crosswalk、逐案标识、用户身份、模型原始输出、私有输入指纹不得进入普通 GitHub、Job 日志或聊天。
- R50 密封测试正文不得访问或用于训练、开发、Teacher、Prompt 调整或 checkpoint 选择。已暴露的 R55/R57 开发题不得冒充独立 Held-out。
- 模型 Tokenizer / Chat Template / Token 预算预检必须在 HF CPU；Mac 仅做安全准备、同步和 SAFE 回执核验。完整约束见 `docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md`。
- 明确要求的 HF CPU 预检可使用最小必要 CPU Job，无需逐 Job 费用授权。GPU 推理、GPU 评审和训练均须独立明确授权；本 Skill 不自动启动 GPU 或训练。
- 不修改冻结 Gold、私有输入、既有真实 checkpoint 或历史证据；不覆盖已有输出。需要刷新私人 STAGE 时，先核对输入和 checkpoint，再按对应技术规范执行。

## 固定执行顺序（必须遵守）

每一轮工具开发、数据处理或评审工作，都严格按以下顺序执行，不得跳步：

1. **查找已有工具和证据。** 确认仓库、分支、HEAD、工作区状态和本轮目标；检索共享核心、既有适配器、SAFE 回执、缓存、checkpoint、合成测试、历史冻结实现及对应技术规范。
2. **优先复用。** 判断现有实现、回执或 checkpoint 是否与本轮输入、配置和版本完全匹配。只有身份和语义均可验证时才复用；不匹配则明确失效范围，不得伪造缓存 PASS，也不得因轮次或路径变化而重复开发/付费执行。
3. **必要时扩展共享核心。** 只有确认通用能力缺失才修改共享核心；项目专属差异放在薄适配器。禁止在 Skill、worker、Job 脚本或实验目录复制第二份通用算法。保持旧冻结实现兼容，除非有独立批准的迁移方案。
4. **添加回归测试。** 在接入真实数据或 Job 前，使用合成数据覆盖正常路径、失败路径、边界、重试上限、隐私、幂等、不可覆盖和 checkpoint 身份。真实 Tokenizer/模板验证按 HF CPU 规则执行；测试通过不自动代表质量准入。
5. **更新 Skill 和文档。** Skill 只记录 AI 的决策顺序、调用边界、门禁和权威文档入口；`docs/standards/` 保留完整技术规范、算法约束、Schema、失败码、版本和复现步骤。AGENTS.md 只记录跨项目通用规则，不复制项目实现。
6. **验证并报告。** 检查差异、测试结果、文件清单和 SHA256 manifest；明确区分已验证、未验证、HOLD、PASS、授权与未授权。测试未实际运行时必须标记待验证，不能写成 PASS。

## 数据与质量主线

### 优先级

1. 第一优先：复用冻结的 Gold195（Gold87 + Gold108），不重选、不改写原始批次。只从独立授权来源构建可审核的派生 SFT 输入。
2. 第二优先：R58 RolePlay 小试点，仅限既定世界范围内尚未暴露的候选；总量不得超过原计划 20 条，不得擅自扩展世界或样本。来源可使用合法原文与明确标记的离线训练上下文编排，不声称历史生产请求精确回放。
3. 首个新实验使用 original-only。未经独立审核，不得自动用 Teacher 重写原文或将 Teacher-only 内容放入 Validation / Protected Test。

### Quality-v1 必需门禁

- `SOURCE`：来源权利、冻结版本、文本到目标的可追踪关系及上下文因果连贯。
- `ISOLATION`：按语义世界组件划分 Train / Validation / Protected；排除 R50、已知训练/开发/保留测试污染。无法确认的世界关系保持 HOLD。
- `STRUCTURE`：角色顺序、真实当前 User、足够历史、规范 JSONL、唯一末轮 Assistant 目标、无未来剧情透视；Token 上限按当前批准配置执行。
- `QUALITY`：两份独立且盲化模型身份的审核；检查硬事实/禁令、严重玩家自主权侵犯、NPC 主动推进、中文自然度、剧情张力、角色一致性和重复表达。严重问题 REJECT，有争议 HOLD，优秀才 PASS。
- `FREEZE`：冻结来源哈希、派生转换版本、训练标签掩码及世界分组；旧 DEV / 已暴露 Test 不得冒充最终独立晋升测试。
- `TRAINING`：数据和配置正式批准、HF CPU preflight 与真实 ms-swift `last_round` / Collator 检查完成后，仍须单独申请 GPU 训练授权。

旧 `r58_intake.py gate/freeze` 仍承载历史 G2 结构合同，不得伪造 `history_replay_verified` 或 `target_time_canon_verified` 为 true，也不得用旧 Freeze 状态替代新的 Quality-v1 准入。

## R58 评审执行

- R58 GPU 文学评审使用 `experiments/r58_quality/r58_hf_gpu_literary_reviewer.py`；合成回归使用同目录的 `test_r58_hf_gpu_literary_reviewer.py`。
- 引用必须严格来自允许来源；引用诊断、Batch Quote Repair v2、checkpoint v3、严重标记阈值和 SAFE 字段均以 `docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md` 为唯一完整技术规范。Skill 不复制其算法、Schema 或失败码。
- 遇到引用校验失败或严重标记诊断时，先读取 SAFE 回执和 checkpoint 身份，再按规范决定 HOLD / 重试；不得降低引用准确性门槛、擅自改写模型决策或覆盖 checkpoint。
- A/B 比较必须按内容身份对齐，不得按 blind_id 或数组位置推断配对；样本不足以配对时不得声称模型整体优劣。

### 私人审核证据复用

- 复用既有网页/模型审核前，先用 `experiments/r58_quality/private_review_evidence_reuse.py` 对比历史 Manifest 与当前私人任务。
- 只有案例标识、完整输入 SHA256 和目标 SHA256 全部一致，才允许把该案例列为历史证据复用候选；不匹配只 HOLD 对应案例。
- 工具按 Manifest 实际案例数运行，不假定固定批次大小；SAFE 回执不包含私人正文、ID 或哈希。
- 精确匹配不等于历史审核输出有效，也不证明审核者独立或文学质量通过；继续使用对应的历史输出验证器与结案工具。
- 完整算法、Schema、失败码、文件权限与复现方式只维护在 `docs/standards/R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md`，Skill 不复制实现。

### 已验证的当前状态（2026-11-02）

- Batch Quote Repair v2 与 checkpoint v3 已完成；A/B 新版 GPU Pilot 已完成。
- A / Qwen3-32B：2/2 PASS。B / GLM-4-32B-0414：1 PASS、1 HOLD。四个 checkpoint 均通过 CPU 身份与严格引用复核。
- 四条 severe flags 均为 false，四条 card_conflict 均为 false；card_suitable：A case0=true、A case1=true、B case0=true、B case1=false。B case1 因角色身份、故事线和场景对应关系无法由可见历史确认而保留 HOLD，不得改成 PASS。
- 只有 A case0 与 B case0 是共同配对样本；其余本轮结果不构成配对比较，不能据此判断模型整体优劣。
- `quality_v1_admitted=0`、`training_authorized=false`；剩余 11 条未启动，训练未启动。未使用预算不自动授权扩样。

## 权威技术文档

- 共享 Tokenizer 核心的唯一实现入口：`src/storyforge_dataset/token_preflight.py`；禁止在 Skill、worker、Job 或实验目录复制通用算法。
- HF Tokenizer / Chat Template / SAFE cache / 共享核心 / 私有 STAGE：`docs/standards/HF_TOKEN_PREFLIGHT_REUSE_CN.md`
- R58 GPU 评审 / 严格引用 / Batch Quote Repair / checkpoint / severe flags：`docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md`
- R58 私人审核 Manifest 与任务身份复用：`docs/standards/R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md`
- Quality-v1 主线、数据优先级与门禁：`docs/plans/R58_LORA_QUALITY_FIRST_MAINLINE_20261101.md`

## 状态语义

- `OWNER_ATTESTED` ≠ `SOURCE_PASS` ≠ `QUALITY_PASS` ≠ `ADMITTED`。
- `SHORTLIST_ONLY` ≠ `TRAINING_READY`；`REVIEW_PASS` ≠ `TRAINING_AUTHORIZED`。
- `TOKEN_PASS` ≠ `COLLATOR_PASS` ≠ `QUALITY_PASS`。
- `HOLD` 不得推断为 PASS；未执行的测试不得报告为 PASS；未获授权的 GPU / 训练不得启动。
