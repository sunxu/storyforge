# 0.1.15 — 2026-11-03

- 将稀疏 `v2_chat_message_ledger` 恢复纳入共享历史恢复核心；区分 INSERT / UPDATE_AFTER marker 与 UPDATE_BEFORE / DELETE 旧行快照。
- 新增按 story/session/turn ceiling 的有界账本读取；每个 Session 一次查询，默认最多 100,000 条，禁止全表扫描。
- 对目标后编辑、删除、插入和流式完成事件分别处理；用 `mutation_revision` 与 `update_after` 数量交叉核验，未记录的状态变更触发 HOLD。
- 增加独立账本核心测试及历史恢复集成测试；覆盖编辑旧快照、删除恢复、目标后插入排除、revision 不匹配和事件数超限。
- 明确 `recorded_at` 是事务时间而非提交时间；SAFE 保留 `ledger_commit_order_verified=false`，不宣称严格 commit-order 回放。
- 更新 Gold Quality 技术规范、Skill 和 scoped CI；不访问私人 Strict28 正文、不启动 GPU、不授予 Quality-v1 准入或训练授权。

# 0.1.14 — 2026-11-03

- 新增可复用的只读历史上下文恢复核心：按目标消息时间、Session lineage、fork cutoff、summary cutoff 与历史故事版本恢复上下文。
- 新增 Strict28 薄适配器，固定校验 28 条私有历史曝光 ledger 的 SHA256；只查询指定 story/session/turn，不进行全库扫描。
- 新增合成回归，覆盖父 Session 分叉、未来消息、目标精确匹配、失败状态、摘要更新时间/cutoff、历史版本时间边界、循环 lineage、超限不截断和私有输出不可覆盖。
- 明确历史故事卡快照不等于历史 Provider System Prompt；当前快照、未验证摘要与 Volume Memory 不得自动进入训练输入。
- 根据数据库 fork/rewind 函数定义，纠正 lineage 恢复：继承消息已复制到子 Session，父消息不得二次拼接；`forked_from_turn` 是 story-turn。摘要物理索引与 story-turn 分开核验，缺少显式覆盖索引时拒绝 legacy fallback。
- Strict28 输入不再使用未经 Owner 核验的固定 ledger digest；必须与同一次 PR #9 SAFE receipt 配对，并从其 `private_ledger.sha256` 重新校验实际字节。
- 更新 Quality Pipeline 技术规范、CI 和 Skill Manifest；不访问私人故事正文、不启动 GPU、不授予 Quality-v1 准入或训练授权。

# 0.1.13 — 2026-11-02

- 新增统一 Gold Quality Pipeline：私有 append-only Manifest、CLI、历史 Gold87/Gold108 分层证据导入、R57 Gold195 曝光导入及独立审核事件。
- 新增 SAFE-only 计数报告、来源 pin 检查、私有目录/权限边界和合成回归测试；Tokenizer 预检继续复用唯一共享核心。
- 明确旧批次证据不构成 Quality-v1 准入；Reviewer A/B、AI、Owner 仲裁与 REJECT/HOLD 分歧必须保留。
- 本次仅创建独立 Draft PR；不修改冻结数据，不读取 R50，不启动 GPU/训练，不授予 Quality-v1 admission。

# 0.1.12 — 2026-11-02

- 根据 Owner 本地只读 SAFE 回执，将 Gold195 任务、Grok Pilot Manifest、Follow-up 和 Case02 disposition 路径从“未确认”更新为已由实际命令读取验证。
- 记录历史 Manifest 3/3 精确匹配当前 195 条任务；192 条仅为该 Manifest 未覆盖项，不是质量失败或自动外发授权。
- 记录三案 Grok Web Pilot 结案：Case01/03 双审暂定通过但语义 HOLD，Case02 严重问题争议未决；Quality-v1 admission 仍为 0。
- 新增两份不含私人正文、ID 或哈希的 SAFE 证据回执；更新技术规范、Skill、README 与合成契约测试。
- 没有读取 Mac 私人文件正文；只根据 Owner 提供的 SAFE 结果更新仓库记录。未修改原始评审、Gold、训练数据或 GPU Job；未访问 R50，未授权扩样或训练。

# 0.1.11 — 2026-11-02

- 纠正 v0.1.10 将 Gold195 任务迁移目标路径误写为已确认存在的问题。
- 根据历史记录区分 Gold195 任务的旧目录生成路径、统一目录迁移事实与迁移后文件存在性；记录用户已确认新目录下原先假定的任务路径不存在。
- Grok Pilot Manifest 新路径改为“依据目录结构推定、尚未验证存在”，不再当作已确认输入。
- 技术规范改为先只读 find 定位、检查唯一性和权限，再运行身份复用核验；禁止静默回退旧目录、自动搬动或重新生成任务。
- 更新 Skill、README、契约测试与 SAFE Manifest。未访问 Mac 文件系统，未移动/创建/修改私人文件，未读取私有任务正文。
- Quality-v1 admission 仍为 0；GPU / 训练授权状态不变。

# 0.1.10 — 2026-11-02

- 根据 2026-11-01 历史迁移约定，统一 R58 私人审核目录文档为 `$HOME/.local/share/storyforge/r58/`。
- 固定当前 Gold195 任务文件与历史 Grok Pilot Manifest 的规范相对路径；明确旧 `~/storyforge-review-private` 已退役，不得静默 fallback。
- 记录 Gold 卡片快照、Gold 审核记录、user-first 任务、Case02 disposition、Grok Pilot 与 Follow-up 子目录的历史布局。
- 更新复用工具技术规范、Skill、README、契约测试与 SAFE Manifest；本次只更新 GitHub 文档，没有访问或移动 Mac 私人文件，也没有验证本地文件存在。
- Quality-v1 admission 仍为 0；GPU / 训练授权状态不变。

# 0.1.9 — 2026-11-02

- 新增通用私人审核证据复用核验器：按 Manifest 实际案例数量工作，不固定 Gold195/3 条或其他批次大小。
- 以稳定 case_id、完整输入消息 SHA256、目标 SHA256 三重匹配；支持部分匹配并逐案 HOLD 不匹配项。
- 重新计算当前任务输入/目标哈希和 Manifest 目标哈希；拒绝重复 ID、重复 JSON key、非未审核任务及已获质量/训练准入的任务。
- 私人输入要求仓库外、文件 0600、父目录私密、无硬链接；只读、不写文件、不访问网络/HF/GPU/R50，SAFE 不输出私人值。
- 新增 14 项合成回归测试，覆盖可变批量、匹配/不匹配、哈希篡改、重复项、权限和隐私边界。
- 更新 Skill 到 v0.1.9，并将完整实现规范放入 `docs/standards/R58_PRIVATE_REVIEW_EVIDENCE_REUSE_CN.md`；AGENTS.md 只保留仓库通用规则，不复制项目实现。
- 本次代码与合成测试不读取真实私人 Manifest、Reviewer 输出或任务正文；不授予 Quality-v1 准入、GPU 或训练授权。

# 0.1.8 — 2026-11-02

- 收敛文件职责：AGENTS.md 只保留仓库通用规则；SKILL.md 只保留 AI 执行顺序、权限边界、门禁和权威文档入口。
- Skill 不再复制 Token Preflight 算法、缓存细节、SAFE 诊断码或 Batch Quote Repair 的候选索引实现；完整技术约束分别维护在两份 `docs/standards/` 文档与唯一共享源码中。
- 固化执行顺序：查找已有工具和证据 → 优先复用 → 必要时扩展共享核心 → 添加回归测试 → 更新 Skill 和文档。
- 更新 R58 A/B v3 GPU Pilot 状态；明确 B case1 的 `card_suitable=false`、唯一共同配对样本及训练准入仍为 0。
- 更新 Skill contract 测试以检查职责边界、技术规范链接、共享核心唯一性和 manifest 完整性。
- 不修改私人输入、旧 checkpoint、历史评审输出或训练数据；不提交 GPU、不扩大样本、不授予训练准入。

# 0.1.7 — 2026-11-02

- 将 R58 引用纠错升级为 Batch Quote Repair v2：单次纠错批量覆盖 source/target 两个引用列表的所有无效位置。
- 模型仅返回 field / quote_index / candidate_index；程序验证位置集合无遗漏、无重复、无额外项，并从合法原文候选中逐字替换。
- 保留严格连续子串校验；任何候选/结构/预算/索引/最终校验问题仍 HOLD，不保存 checkpoint，不放宽门槛。
- Checkpoint schema 升级 v3，Prompt SHA256 纳入 quote-repair 版本、提示模板、Schema 模板与候选/修复数量上限；旧 v1/v2 checkpoint 不得复用。
- HF CPU reviewer 合成测试 13/13 PASS，覆盖跨字段、多位置批量修复、重复/遗漏索引拒绝、仅修改引用字段及 checkpoint 保存。
- 仅更新非敏感代码、Skill 与规范；Gold195 私有输入、旧 checkpoint 和既有 A/B 结果不变；GPU 重评须在新隔离 STAGE 中进行。

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
