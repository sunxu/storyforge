# 0.1.6 — 2026-11-02

- 明确三个 severe flag 的阈值，特别区分 NPC 自主行动与严重玩家自主权侵犯。
- 将 `review_policy_version` 与 `prompt_sha256` 纳入 checkpoint v2 身份，Prompt/规则变更后拒绝复用旧 checkpoint。
- 增加严重标记定义与 Prompt 身份回归测试；HF CPU reviewer tests 13/13 PASS。
- 不放宽 severe gate，不将旧 A/B checkpoint 混入新 Prompt 版本；新版本 A/B pilot 尚未获 GPU 重跑授权。

# 0.1.5 — 2026-11-02

- 为 `RESPONSE_SEVERE_MUST_REJECT` 增加 SAFE 结构化诊断：case_index、model_decision、active_severe_flags、active_severe_flag_count。
- SAFE 仅包含枚举值和白名单标记名，不包含模型原始响应、故事正文或引用文本。
- 增加 PASS/HOLD 与严重标记组合的合成回归覆盖；12/12 PASS。
- 明确旧 SAFE 回执缺少具体标记信息时不得推断根因；先诊断，再决定是否重试。
- 不改变严重标记门槛，不自动把 PASS/HOLD 改成 REJECT，不扩大 GPU 样本范围或训练授权。

# 0.1.4 — 2026-11-02

- 将 R58 引用纠错从自由文本重写改为受限候选索引选择，模型只输出整数索引，程序从允许来源逐字切取原文。
- 来源候选仅来自 visible_history 中单条 user/assistant 消息；目标候选仅来自 target_text；unapproved_card 永不作为引用来源。
- 只替换失败引用位置，其他评分/结论字段由程序原样保留；候选缺失、超量、Token 超限、索引无效或严格校验失败仍 HOLD。
- 新增候选来源、精确子串、字段隔离和 target quote 端到端合成测试；12/12 PASS。
- 本次变更不增加样本范围、不覆盖旧 checkpoint、不自动启动 GPU、不授予训练准入。

# 0.1.3 — 2026-11-02

- 明确工具开发固定顺序：先查工具与证据、优先复用、必要时扩展共享核心、补合成回归测试，再更新 Skill 与技术规范。
- 为 R58 文学评审增加 SAFE 字段级引用失败诊断，并仅允许一次有预算检查的引用纠错；非引用字段必须保持完全一致。
- 纠错失败仍 HOLD，不保存 checkpoint，不放宽严格连续子串规则；不自动重跑 GPU、不扩大样本范围、不授予训练准入。
- 完整实现细节见 `docs/standards/R58_GPU_REVIEW_QUOTE_VALIDATION_CN.md`。

# 0.1.2 — 2026-11-01

- 将 CPU Token 预检失败诊断细化为安全阶段码：区分 Chat Template 渲染失败、Token ID 结构无效及其他编码失败；异常原文不进入日志。
- 更新 Skill 执行顺序与技术文档：先复用共享核心，修复后补充合成回归测试，再刷新私人 STAGE。
- 明确用户要求 HF CPU 预检工作流时无需逐 Job 费用授权；GPU 推理/训练仍须单独明确授权。
- 不修改私人输入或已有回执；不执行推理、GPU 或训练，不授予质量准入。

# 0.1.1 — 2026-11-01

- 将仓库 `AGENTS.md` 的“优先复用 HF CPU Token 预检”落入 Skill 执行顺序：先查现有工具和可信 SAFE 回执，再决定是否运行付费 Job。
- 指向唯一共享实现 `src/storyforge_dataset/token_preflight.py`、历史 R50/R53/R58 CPU132 证据与 R58 13 条双审适配器，明确不在 Skill 内复制底层算法。
- 明确 Mac 只做数据准备和 SAFE 回执复核，真实 Tokenizer 在 HF CPU 运行；严格检查输入、序列化 Prompt、模型/版本、thinking、输出预算及共享核心代码的匹配才允许复用。
- 区分 Token 预算与真实 ms-swift Collator/last_round 训练标签检查；两者都不构成文学质量或数据准入。
- 修正过时的生产请求精确回放 G2 门禁对 Quality-v1 LoRA 主线的干扰，保留旧代码和冻结证据但禁止伪造旧 G2 PASS。
- 保持私人 A/B 隔离、R50 保护和 HF CPU/GPU 分别授权；本次更新不发起 Job、不给质量准入。

# 0.1.0 — 2026-10-30

- 增加只读 RolePlay 表结构/故事候选 SQL 模板（不读取正文）。
- 增加 HF 私有环境离线 `shortlist` / `gate` / `freeze` CLI。
- 强制逐案双 Reviewer（声明与证据）、Owner 批准、世界组件隔离、Source/Input/Target SHA256、派生模型谱系；不宣称可以机器证明语义正确。
- Teacher 上限默认 20%，仅允许进入 Train；验证集不得使用 Teacher 产物。
- 不覆盖输出；保护文件模式 0600；摘要不包含原文或逐案 ID。
- 使用虚构样本完成 10 个单元测试。真实 Supabase 数据未导出，正式准入仍为 0（本 Skill 阶段）。
