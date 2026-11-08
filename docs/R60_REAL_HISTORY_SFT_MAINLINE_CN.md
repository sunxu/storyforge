# R60 真实优质历史数据 SFT 主线与任务优先级（2026-11-08）

> **2026-11-08 HF/Quality Pipeline 复用决策（覆盖此前 Owner Mac Ollama 双审步骤）**：真实 1000 候选已采集，质量 0、入训 0。审核工具盘点表明 R58 已有 HF GPU 语义/六维双审、引文校验、A/B 隔离与检查点机制；为避免继续维护 R60 本地第三套审稿器，新增公共 `storyforge_gold_quality.hf_literary_review`、`hf_blind_stage` 和唯一 R60 薄适配 `r60_hf_quality_adapter.py`。先 Owner Mac `prepare` 做严格冻结 SHA + A/B 盲审分发；再经过 HF CPU Tokenizer 预检（共享 core）；模型/镜像实际兼容性和明确 GPU 费用批准后才运行 HF 双模型小批 Pilot。回收 SAFE 后由 `audit` 验收、`export` 生成为原 `storyforge-gold-quality append-review` 可导入的两个私人 Reviewer 文件。**未提交付费 HF Job、未上传私有候选、未执行真实 AI 审核。** 新操作书：[HF × Gold Quality Pipeline 1000 条复用路线](R60_HF_QUALITY_PIPELINE_REUSABLE_1000_CN.md)。此前 `R60_REAL_HISTORY_1000_QUALITY_BATCH_EXECUTION_20261108_CN.md` 的 Ollama 方案仅保留为历史备选，不再作为主线。


> **2026-11-08 完成里程碑：真实候选池 1,000/1,000 已采集，进入 Quality-v1。** Owner Mac 实际 SAFE `EXPANSION_TARGET_REACHED__NOT_ADMITTED`，原始 G1 Seed 6 + 新增 994、20 个私有页、扫描 400 Story；Quality PASS=0、入训=0，R50/world 仍 HOLD，GPU/DB 修改=0。扩样阶段关闭，不再修改原批次、配置或目标数量。
> 已开发 [1,000 条私有批量双模型 AI 质量审阅](R60_REAL_HISTORY_1000_QUALITY_BATCH_EXECUTION_20261108_CN.md)（`experiments/r58_quality/r60_real_quality_batch.py`）：只读验真冻结源、两模型独立评分、每案例私有不可覆盖审阅回执，`init/advance/inspect` 和断点续跑，默认每次最多 5 条、硬上限 25 条；先做 5 条校准，再分段批量执行。Quality PASS 仍只是质量维度，不等于训练准入，历史世界/System、R50 完整排除、CPU 均须独立验收。
> **真实批量 AI 审核尚未在 Owner Mac 运行**。切勿把合成测试通过写为真人历史质量 PASS、训练数据冻结或 GPU 训练已启动。

> **2026-11-08 二次决策：候选池目标从 600 上调到 1000。** Owner Mac 实际完成 **600 条（原 Seed 6 + 新增 594）/ 12 页 / 已扫描 240 Story**，SAFE `EXPANSION_TARGET_REACHED__NOT_ADMITTED`。此状态仅证明技术候选采集，不代表 Quality PASS（当前 0）或训练准入（当前 0）。
> 用户已明确批准继续扩样至 **1000 条真实历史技术候选**；通过 [600→1000 原位续跑说明](R60_REAL_HISTORY_EXPANSION_1000_CONTINUATION_20261108_CN.md) 和 `r60_real_expand_private.py extend --target-total 1000` 追加私有扩容回执，**不覆盖先前 12 页、600 条和源配置**，随后原目录 `advance`、`inspect`。此前 600 目标已完成，但本次对 Owner Mac 的新续跑**尚未实际执行**，不可把 1000 写成已采集完成。
> 达成 1000 后优先真实双模型质量筛查及严重问题排除，再进行 R50 完整元数据/世界组件隔离、CPU Tokenizer/Collator，最后另行申请 GPU 训练。RolePlay、Gold192 不修改。

状态：`REAL_HISTORY_MAINLINE_ACTIVE__TRAINING_ADMISSION_HOLD`  
执行：StoryForge / Owner Mac（本机数据库连接角色 `r58_export_reader`）；ChatGPT 只读连接器 `supabase_read_only_user`，不得混用。  
**RolePlay 不修改；不启动新的 GPU 技术可行性实验；本轮不授权 GPU 训练。**

> **2026-11-08 最新主线调整（覆盖本文此前旧 Pilot 优先级）**：
> Owner Mac 已成功采集真实 G1 **6 条/6 Story**，完成私有模板，不再重复 G1 捕获。
> 下一阶段首先扩样真实历史训练候选至 **总量 600 条**（包含原始 6 条，目标区间 500–1000），使用分 Story 游标、分批只读导出、源哈希与跨页去重；不得直接扩大旧六条脚本的上限。
> 本轮新生产 G0 只读聚合确认：96 Story、1152 最近 completed Assistant、**339 条四消息链技术候选**、67 个 Story；技术候选不是 Quality PASS。
> 已提交独立扩样程序 `experiments/r58_quality/r60_real_expand_private.py` 和 [Owner Mac 600 条扩样执行书](R60_REAL_HISTORY_EXPANSION_600_EXECUTION_20261108_CN.md)。
> **任务序列：P0 扩样 → P0 批量六维质量审核 → P0 R50 完整元数据/世界依赖隔离及目标前上下文 → P1 CPU Tokenizer/Collator → Owner 单独批准 GPU。**
> 本文旧的权益争议调查/单对 G1 阶段说明为历史记录，不再作为当前工作阻断；Owner 已明确授权使用其真实历史数据训练，不再重复讨论该议题。
> 当前训练准入仍 **0**，无 GPU，RolePlay 与 Gold192 不变。

## 一、目标和已证事实

目标是以**真实、优质的历史 User–Assistant 数据**训练中文互动小说模型，不以合成数据替代主线。R46 等已有训练已验证 Runtime/Adapter 技术可行性，不重复做 GPU smoke test。

两轨独立：

- `STRICT_GOLD_QUALITY_V1`：Gold192 原冻结、A/B 输入/单次原始 Provider 证据和既有 Quality-v1 标准不改变，当前准入 0。
- `REAL_HISTORY_FINAL_RESPONSE_SFT_EXPERIMENTAL`：候选来自经授权的真实历史消息，监督标签**定义为数据库已完成的、最终交付的 Assistant 文本**（不是声称原始 Provider 单次 completion）；训练上下文采用可核对的真实历史消息与明确标记的规范化/重建系统约束，标注 `RECONSTRUCTED_NOT_ACTUAL_SENT`，不得假称它是历史实际发送 Prompt。最终必须通过权益、隐私、上下文一致性、质量、世界组件与完整保护集隔离及独立审核后才准入。两轨不得共用数据集 ID、split、冻结列表。

本次 Supabase 只读调查的**非随机活跃 Session 抽样**显示，最近一批样本中 117 条同日 completed Assistant，117 有紧邻 completed User，49 满足长度 >=300、正常 finish、无可见编辑键及无 parseWarnings 键，覆盖 6 个 Story ID。**49 是技术优先候选，不代表训练合法或高质量，不能外推比例**。不同轮次活动 Session 排序或筛选窗口导致 117/152 等抽样差异，不应混算。

Owner Mac 在**唯一明确批准的 Story/Session 对**上已经获取 80 条消息元数据、40 对相邻完成 User–Assistant；原 3 案目标 SHA/身份 PASS，但历史 System/Memory、单次 Provider 证据仍 HOLD。该对的 G0/G1 授权**不自动扩展到其他 Session、其他用户或全站；也不代表 G2 训练授权**。

## 二、正式调整的任务优先级

| 编号 | 优先级 | 任务 | 可交付物 / 完成门槛 | 当前 |
|---|---|---|---|---|
| R60-REAL-01 | P0 | 经授权历史数据的元数据预筛（先用已授权单对 40 pairs） | 每条仅以 DB 精确 ID 与相邻 User 验证，统计字数、正常 finish、编辑/解析迹象；私有 shortlist + SAFE；不得输出正文 | **进行中** |
| R60-REAL-02 | P0 | 真实文本质量审核（文学、角色、NPC、玩家自主权、规则、连贯性） | 私有逐案两名独立审核者/证据引用、严重问题拒绝；不以字数替代质量 | 待 REAL-01 |
| R60-REAL-03 | P0 | 构建准确标记的真实历史训练上下文 | 真正的历史 user/assistant 交替、目标前时间边界、无未来泄漏；规范化重建说明及校验；不得用当前故事卡伪装历史快照 | 与 REAL-02 并行 |
| R60-REAL-04 | P0 | 来源权益、隐私、R50 完整元数据排除、世界及历史曝光 | 每条证据、Owner 审批、授权用途、世界组件及完整保护范围核验；未核实即 HOLD | 并行、阻断准入 |
| R60-REAL-05 | P1 | 独立 Train/Validation 冻结与 CPU Tokenizer/Collator | 同一依赖世界同一 split；独立数据清单 SHA；CPU collator 通过；绝不混入 R50 | 等 P0 |
| R60-REAL-06 | P1 | 训练预算、正式 GPU SFT 审批及模型验证设计 | 经批准的数据集 + 可重放 HF Job 配置 + 用户单独 GPU 授权；**当前不执行** | HOLD |
| R60-REAL-07 | P3 | 原 3 案缺失 Provider/时钟/历史快照追溯 | 只有新独立证据出现才恢复；既有 HOLD 不阻塞实验线初筛 | 暂停 |
| R60-REAL-08 | 暂停 | RolePlay 真实生成证据 Shadow 开发 | 本主线不修改 RolePlay，不以新上报机制作为历史数据前置条件 | 暂停 |
| R60-REAL-09 | 取消 | 重复 GPU 可行性实验/新合成训练集替代主线 | 既有训练链路已验证，避免偏离真实历史数据目标 | 取消 |

## 三、真实历史训练标签的精确定义

`target_semantics=DB_FINAL_DELIVERED_ASSISTANT` 表示最终持久化 completed Assistant，不保证与 Provider 原始字节相同。凡有明确的编辑、fallback、重复、续写、解析异常、UI 与持久化冲突等迹象，先 `MANUAL_REVIEW_HOLD`；没有迹象也只能标为 `TECHNICAL_PRIORITY`，不能认定单次或未变换。

多轮输入必须可检验目标前上下文，并与训练时提供的规范化 System/世界信息一致。对来源版本不明的故事卡，不能默认它是历史时点内容；要么以**独立、原创、静态且显式标注的训练约束**代替并执行语义一致性审核，要么 HOLD。不可把目标未来信息注入输入，不能用 Target 生成 Prompt。

质量审核利用 `quality_v1.py` 中六维评分语义和严重问题，但该工具的原 `gold195/r58_round1` 来源封闭枚举与原 Gold 来源条件不得被偷偷放宽；新实验线建立独立 Schema、Reviewer 记录及入选审查器。既有 Strict Gold 文件不改。

## 四、阶段状态与准入断言

`DISCOVERED` → `METADATA_TRIAGED` → `QUALITY_REVIEWED` → `CONTEXT_VALIDATED` → `ADMISSION_PENDING` → `TRAIN_ADMITTED`。

- G0/G1 只读候选发现与有限私有审核，可以在 R50 状态 `UNKNOWN_HOLD` 时进行**已明确授权的那一个对**。
- `TRAIN_ADMITTED` 须对 E0/E1/E2/E3 权益/隐私、监督目标语义、语境一致、世界与 R50 完整保护集审查全部有独立依据，E4/E5 冻结和 CPU 预检通过，并经 Owner 逐批签核。
- 未通过来源权益/隐私、完整 Test 保护集排除的样本**不得**进入训练，即便质量极高。
- 原 Gold192、R50 内容、旧三案审核结果只可只读引用；不得自动将 40/49 条转为准入，不能把世界 Story ID 当作独立 Validation world。

## 五、立刻执行的第一个 Pilot（R60-REAL-01）

基于现有单对私有 `R60_G0_G1_SINGLE_PAIR_SCOPE_PRIVATE.json`、`R60_TARGET_PAIR_LOCATORS_PRIVATE.jsonl`、`R60_TARGET_PAIR_SAFE.json`（Owner Mac）。本机新工具仅用 `r58_export_reader` **精确查回**这 40 个 `session_id/turn_index/id` 组合的结构字段、字数、`finishReason` 与编辑/解析元数据布尔值；不读取正文或完整 metadata JSONB，查询只读、有界、索引命中。严格校验原始 Scope SHA、pair 数和身份一致性，结果只在 Owner Mac 0700/0600 私有目录。

短名单等级：`TECHNICAL_PRIORITY`（满足约束，**尚未经质量审查**）、`MANUAL_REVIEW_HOLD`（可疑或待审），而不是 `PASS/ADMITTED`。SAFE 仅输出计数和原因码，私有 locator 不上传 GitHub。

第一批目标是形成实际的 **40 → 技术优先名单 → 小批质量审核（先少量）** 的可审计转换，不求扩大未经授权的全站采样。后续才在获得明确授权的更多 Story/Session 上扩展。

## 六、非目标与审批边界

不改 RolePlay、不进行合成数据 SFT、不启动 GPU、不修改生产 Supabase 数据或权限、不关闭 RLS、不读取 R50 正文、不将任何真实用户内容提交 GitHub。程序和合成测试可提交 GitHub。所有模型训练或付费任务单独申请授权。

完成 REAL-01 后，优先推进 REAL-02/03，独立并行解决 REAL-04；不再以缺少旧 Provider raw log 为由停止真实最终回复 SFT 实验线筛选，但也不降低严格 Gold 的 A/B 门槛。

## 2026-11-08 方案 A：G0 全 Story/Session 范围授权与执行进展

Owner 在本轮新增授权：现有 ChatGPT Supabase 只读连接器可对所有 `story_id`/`session_id` 做**聚合式技术元数据发现**。此前仅 1 对 Scope 的限制继续适用于原 Owner Mac `r60_scoped_target_pairs.py`/40 Pair G1 私有审核链，但**不再限制 ChatGPT 的 G0 全范围聚合调查**。这不是全站正文导出/训练许可。

执行回执：[`docs/R60_GLOBAL_SUPABASE_METADATA_DISCOVERY_20261108_CN.md`](R60_GLOBAL_SUPABASE_METADATA_DISCOVERY_20261108_CN.md)；复现 SQL：`experiments/r58_quality/sql/r60_global_real_history_aggregate_READ_ONLY.sql`。四类别各 16 Story 的有界聚合样本，64 Story / 1,280 completed Assistant，523 达技术优先条件。技术优先不是质量或准入；公开原创也不等于微调授权。

**P0 实际推进**：全范围 G0 元数据统计已取得；下一关键环节是先确定各作品与聊天参与者的**内容审核及微调授权依据**，然后针对具备权限的候选进行定点正文审核/上下文构建。没有这个边界，不得使用 BYPASSRLS 账号批量读取所有私有用户原文。现有 `r58_export_reader` 本机方案和 ChatGPT connector 角色不得混同。严格 Gold192 和 R50 未改变，正式准入仍 0。

## 2026-11-08 新 Agent 交接与最新权益调查入口

- [主线新 Agent 总交接](R60_NEW_AGENT_MASTER_HANDOFF_20261108_CN.md)：最新状态、两个 GitHub 仓库、工具角色、复现 SQL、冻结边界、最短实施路径。
- [新 Agent P0 执行任务书](R60_REAL_HISTORY_NEXT_AGENT_P0_TASKBOOK_CN.md)：具体执行顺序、权利与正文审核边界、六维评分、独立世界/R50 和产物验收。
- [历史权益/参与者来源目录审计](R60_REAL_HISTORY_RIGHTS_PROVENANCE_AUDIT_20261108_CN.md)：`voice_consents` 不可代替文字授权；original/private/author==player 30+ 轮 1,039 Session/814 Story、16 Story 新 Pilot 77 技术优先。
- P0 核心阻断 Issue [#27](https://github.com/sunxu/storyforge/issues/27)，跟踪历史版本条款/作品与参与者权利来源及合法 G1 小批范围。
- 最新的跨全库 G0 只是元数据授权；任何未获得独立许可的完整正文均未导出，不能宣称已 Quality PASS。正式训练准入 0/0，GPU 未启动。
