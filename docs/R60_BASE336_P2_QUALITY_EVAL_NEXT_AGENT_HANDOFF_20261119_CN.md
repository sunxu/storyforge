# StoryForge R60 Base336 → P2 Quality-v1：新 Agent 唯一现行接手任务书与启动提示词（2026-11-19）

## 2026-11-20 最新执行结论：Gold48 历史请求链路实测；新模型质量比较仍为唯一主线

**本节优先于下方 2026-11-19 的“固定三消息/新造 48 题”“只允许读取公开卡而不能验证聊天”的过时操作步骤；不改变旧冻结训练集、不自动使 P2-C PASS。** Owner 已再次明确授权真实聊天用于本项目**内部独立模型质量评估**；无需再要求重复提交授权证明。现有 SQL 仅返回 SAFE 聚合；不得在公开 GitHub 发布私人会话正文、ID 对应表或请求 trace。没有另行授权训练、付费 GPU/HF 推理、对外分发或 R50 sealed 正文访问。

### 已完成的真实新证据（不可重复做成“新进度”）

1. 固定新来源候选创建时间为 `2026-11-16T02:03:25Z` 至 `2026-11-19T15:30:00Z`：**17 个**公开原创 Story；实时池后增 1 个到 18，不能混入本次固定范围。采用已存在的公开审核快照/revision/许可事件合同，严格完整历史筛选后可用的**临时**来源是 **8 Story / 7 作者 / 8 个不同 World JSON / GPU 前 2 + 后 6**；与先前 Owner 批准的公开元数据原 8（3/5）**不相等**，替换来源还未正式 Owner Freeze。不得声称 2/6 新来源已在旧 Manifest 中冻结。
2. 固定三消息 `user/assistant/user` 不是历史原始模型 Prompt：上一轮 48 候选中 21 条有更早消息。全部 17 来源中完整历史恰好三消息的候选仅 **32**，每 Story 最多 5。**不能继续以 8×6 固定三消息构造 Gold 对照**。
3. 改为每条原始 Gold 之前的**完整持久化 role/content 前缀**，目标非空、`completed`、`finishReason=stop`；前缀中无缺失/非完成 Assistant，首条不早于当前公开卡版本生效时点，最高 40 消息/24,000 字符；只接受公开卡审批绑定通过的来源。额外排除发现的事后删除早轮次消息风险（**8** 个候选）、完成版正文历史差异风险（**4** 个候选）、编辑标记及晚创建前文。在所查范围 **320** 个基本候选中有 **308** 个通过这些历史一致性屏。跨会话精确去重 Prompt 和 Gold 后，在上述临时 8 Story 各取 6，得到 **48/48 不同完整历史 Prompt + 48/48 不同真实原始 Assistant 答案**，覆盖 **25 个历史 Session**，最长所选历史 **13** 条消息。这证明候选容量和可见历史完整性，**不是 48 个独立会话、六维审核或原始实际发送字节 PASS**。
4. **真实请求证据链已找到，勿再盲查空表 `v2_chat_reply_jobs`：** 新范围会话的 `chat_latency_metrics` 有 **1,361** 条请求计量，全部在 `v2_chat_request_events` 以相同 request_id 且相同 Story/Session 一一找到事件。两表无已发送 Prompt 原文，但计量有 `token_breakdown.historyMsgCount`、System/History/Input Token 数与请求结束原因。
5. 对前项经过删除/编辑/正文差异排除且全前缀去重的 48 Gold，在 **同一 Story/Session、±5 分钟、HTTP 200、`historyMsgCount == 数据库完整前缀消息数`** 条件下，**48/48** 都找到**唯一一条成功请求记录**；匹配的 48 个 request_id **互不相同**，**48/48** `finishReason=stop`、System/History/Input Token 计数均非零；**47/48** 时间差不超过 2 分钟、48/48 不超过 5 分钟。仅按“时间最近”会错配（45/48 历史数量吻合），所以必须采用联合绑定；**这仍只证明请求存在、历史消息数及请求计量一致，未还原当时 System/World/Character/Rules 字节、具体历史消息字节是否全部发送及模板/截断。**
6. 直接在只读数据库对上述固定 17 新来源与 Base336 截止 `2026-11-16T02:03:25Z` 前的 **5,436** 条当前/ **6,977** 条存档来源 World/Character/Opening 完整字段比较：**精确完整字段复用命中 0**。WorldSentence 长度至少 16 的新来源有 15 个，与旧 8,332 条长文本所做 `pg_trgm` 非独立预筛，最高相似度 **0.092**、0.45 以上命中 **0**；另 2 个新来源文字过短不能作有效相似性证明。**这只排除覆盖范围内的确切文本复用及明显近似世界句子，不能将其升级为完整角色/事件/世界语义、历史 Dev/Protected/Reserved/Teacher 全集独立性 PASS。**

### 当前唯一最短下游动作

- **P2-C 剩余实际阻塞：** 为临时 2/6 新来源组合绑定有权威来源的 Base336 172 Story + 全版本角色/剧情语义、所有受保护/历史 Dev/Teacher 保留集合，做真正独立的新来源 Reviewer 裁决；只差未覆盖集合，不重审 R50 已闭合五世界、旧 R47/R48 20 题、Base336 老 10 条 Review 边。
- **Gold actual-sent 缺口：** 现有 request_id、System/History/Input Token 和前缀数已验证，但 **原始实际发送的完整模型请求内容未落在当前查过的表中**。下一步仅定位原始模型网关/请求组装记录的可信证据，或明确冻结一个**“历史持久化前缀下的原始 Gold 对比”**实验合同，并公开承认与原服务 System/Memory/Rules 并非已证明的完全同题输入；不能在未授权情形下凭当前公共卡伪造旧 request payload。
- **P2-B：** 新候选来源固定后再以真实完整历史 Prompt + 原始 Gold 为一体逐题冻结；Quality-v1 六维场景归类必须另审。原 `read_gold(expected_count=48)` 精确前缀检查可复用，但仅作来源匹配，不代替真正 request 字节证明。不得重造通用 Gold 抽取器，除非正式合同要求的最小适配确有必要。
- **P4/P5:** 仍以原始 Gold + Qwen Base + R46 v0.2 ckpt7 + R54 v0.3-A ckpt16 + R60 Base336 ckpt37 的**五来源同题匿名盲评**为目标；必须给出 `Base336 vs Gold`、`vs Base`、`vs v0.2` 和 `vs v0.3-A` 六维/严重缺陷结论，不能只比较生成速度、训练 loss 或 Token。
- **门禁不变：** `P2_C=HOLD`；`P2_B_48_PROMPTS=NOT_GENERATED`；`P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD`；`quality_v1_admitted=0`；`model_promoted=false`。此处 `48/48` 指数据库来源/请求**候选容量**，不是 Owner-only 0600 正式字节冻结或真正独立质量评估 PASS。

SAFE 证据保留在现有 [PR #31](https://github.com/sunxu/storyforge/pull/31) 对话（2026-11-19T15:30Z 界限后的 Gold 完整历史核验、请求联合匹配与本节新事实）；真实来源/请求字节若取得只能留在 Owner 私有环境，不能在 GitHub 公开。

---


## 八、2026-11-19 Owner 新要求：原始回答 Gold 必须参加同题盲评

**本节是 Owner 明确提出的评估要求，优先于本文件前面“原始 Gold 不纳入新评估”的旧说法。** “Gold/原始回答”是**第五种回答来源**（冻结原始记录的 Assistant 回复），**不是第五个推理模型**。评估必须回答：训练后的 Base336 输出相比同题原始回答，在六维质量及硬错误上是提升、持平还是回退。

### 正式阵容与计数（待 P2-C / Gold 来源绑定及 Owner 冻结）

| 回答来源 | 类型 | 48 题对应数量 |
|---|---|---:|
| 冻结来源的原始 Assistant 回答（**Gold/reference**） | 现成的来源回复，**不运行生成** | 最多 48；目前新 P2 **尚未证实存在 48 份同题匹配原始回复** |
| Base Qwen 原版 | 模型生成 | 48 |
| R46 v0.2 checkpoint-7 | 模型生成，历史强基准 | 48 |
| R54 v0.3-A checkpoint-16 | 模型生成，诊断臂 | 48 |
| R60 Base336 checkpoint-37 | 模型生成，新训练主角 | 48 |

如果证据就绪，则为 **48 × 4 = 192 份新模型回答 + 48 份冻结原始回答 = 240 份待盲评文本**，不是 240 次模型生成。若预算限制，事先冻结三生成模型 Base + v0.2 + Base336，得到 **144 份模型回答 + 48 份 Gold = 192 份待盲评文本**。**Gold 不能随预算降级而删除**。

### 最重要的数据来源矛盾：不能用不相同的题硬凑 Gold

现行 P2 来源合同是 8 条公开 Story 的 **World/Character/Opening** 元数据，并在每条来源下**新构造六条** `user/assistant/user` 测试上下文。这些新提示**天然没有可证明的“历史原始回答”**。R48 的 Gold 属于旧 R47 20 题（2 Story、已曝光），不是新 48 题的答案；不能把 R48 Gold、公开 Opening、历史 Test 目标、模型代写或无来源的“标准回复”当作新 48 题的原始回答。

**在 P2-C 完成前，应把“原始回答可比性”增加为独立来源门禁**：
1. 先查已批准的 8 个 P2 来源是否**已有合法可用且未参与训练/旧曝光的原始回答与其完整前置 Prompt 上下文**，只核验存在性、权利和冻结 provenance，不访问用户私有会话正文，也不重新抽取已完成的 P2-A Inventory。
2. 若确有合法的新原始回复，必须由 Owner 在**私有空间**确定每个原始回答的 `source revision + cutoff/actual-sent context + final assistant turn`，并验证 `frozen prompt.messages == original_record.messages[:-1]` 的**逐消息 role/content 精确匹配**，`original_record.messages[-1].role == assistant` 且回答非空；参考已存在的 `scripts/v02_r48_four_arm_build.py::read_gold`，**复用合同、不要复制开发一套通用 Gold 提取器**。验证任何原始回复的出处、权限或训练/开发曝光是否不确定时维持 HOLD。
3. 如果 8 个来源只有公开 World/Opening、没有与新 48 提示相同的原始回复，必须明确给出 `P2_NEW48_MATCHED_ORIGINAL_GOLD=NOT_AVAILABLE`，而不是伪造参考答案。Owner 若坚持“正式盲评 48/48 都与原始回答比较”，需在**保留新世界独立性与用途权利**前提下，调整 P2-B 为**有独立原始回答的合法未曝光 Prompt/Gold 对**；可能需要另获授权、重新选择或创建参考回复，并明确这是新增作者/人工回答而**非历史原始回答**。在这项条件满足前，五回答来源正式报告不能声称完成。
4. 已冻结旧 R47/R48 的原始 Gold 可以**仅在完全相同旧 Prompt**上与新模型结果做**单独、明确标记 EXPOSED_DEV** 的回归比较；Base336 293/43 训练与 Validation 原始 target 也只可以单独做**受污染的训练/验证诊断**，绝不能与 P2 的新 Held-out 六维结果混算、补齐 Gold 或当做模型泛化证明。不要为了该补充任务重新跑旧 R48 盲审或打开 R50 密封材料。

### 盲审、审计与评分合同

- 在 Reviewer 所见逐题同一个 Prompt / World 证据框架下，把 **Gold 与所有模型输出完全同权匿名随机排列**（例如五份随机字母，不固定 Gold 的位置），Coordinator-only 0600 私有映射在 Reviewer 评分冻结后再解盲。
- **必须同时报告** `Base336 vs Gold`（Owner 本次核心要求）、`Base336 vs Base`、`Base336 vs v0.2`，有诊断臂时再报 `Base336 vs v0.3-A`；Gold 自身按六维与严重标记评分，**不是绝对正确、也不自动满分**。R48 旧 Gold 曾出现严重玩家自主权标记，不能把“接近 Gold 的文字相似度”冒充质量提高。
- 每题私有证据要分别绑定：原始回答字节/来源 SHA、对应 Prompt SHA、来源时间/版本、权限、是否被旧模型训练/开发曝光、所有模型生成哈希与 stop/truncation 状态；**reference answer 不得进入任何模型生成输入、模型工具链或公开评审包的身份栏**，只能以匿名回答形式进入盲审。
- 48 题属于 8 个来源 / 5 位作者，Reviewer 和模型回答只是重复观测；按来源世界聚类/分层报告并保留不确定性与三种 severe flags，不把 240 份回答当 240 个独立故事。
- 这项 Owner 要求更改的是未来评估合同，**不是授权读取任何私有对话或 R50 sealed 内容，更不是 GPU 运行授权**；不得为补 Gold 悄悄改变 P2 已批准的来源/用途范围。

**此刻状态**：`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD`、`P4_MODEL_REQUESTS=0`、`train_admitted=0`、`quality_v1_admitted=0`、`model_promoted=false`。新 Agent 要把 Gold 逐题绑定作为未来正式 5 份回答盲评的真实输入要求，而不是在源缺失时继续称“48 × 5 现成可评”。

---


## 七、2026-11-19 被评测模型阵容重新评估（取代本文件原先仅 Base/Adapter 两臂的默认设计）

**状态：建议的 preregistration 设计，尚未经 Owner 最终冻结，也不授权新的 GPU/HF 推理。** 本文件第 1 / 5 节原写的“Base/Adapter 两臂”仍是**最低主比较**，不应视为已获批准的最终模型阵容。历史 R50/R56 曾提出 Base/v0.1/v0.2/v0.3 四模型；R47/R48/R55 的真实结果表明应将“新 Base336 对比历史强 Adapter 与最新旧版本的回退”列入同一次新的独立质量评估。

### 推荐：4 个生成臂，分主比较和诊断比较

| 臂 | 冻结模型 | 本轮地位 | 历史证据理由 |
|---|---|---|---|
| A | `Qwen/Qwen3.8-27B` 原始 Base，revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | **必须** | 校验本轮微调是否较 Base 获益 |
| B | R46 **v0.2 checkpoint-7** Adapter（相同 Base revision；历史权重身份必须先验 SHA/加载可用性） | **必须** | R47 旧 20 Prompt 中 11/20 多数偏好；R48 仅略逊原始 Gold；历史强质量对照 |
| C | R54 **v0.3-A checkpoint-16** Adapter（相同 Base revision；旧 frozen checkpoint） | **推荐同轮纳入，预注册为诊断臂** | R55 对 v0.2 旧题 12/20 多数偏好，但六维均分 3.2750 < 3.3972、自主权严重标记 9 > 7；历史 NO-GO 是不批准消耗 R50 密封测试，不是禁止在**新 P2 来源**上诊断 |
| D | **R60 Base336 checkpoint-37** Adapter | **必须；新实验主角** | 已完成工程训练与 Adapter reload，尚无独立质量证明 |

不将 **v0.1 checkpoint-9** 纳入核心新评估：旧 R47/R48 表现偏弱，对判断新模型是否超越历史最佳的边际贡献小，增加一次整套推理/盲审成本。**R48 原始 Gold 仅属于旧 20 Prompt，不能直接移植给 P2 新 48 题；但 Owner 已明确要求未来同题原始回答 Gold 作为匿名对照，必须按本文件第八节解决匹配与来源权限。**旧 R47/R48/R55 20 Prompt 仅涉及 2 个已暴露 Story，不能当新测试数据或替代本次预测。

- 推荐同一次锁定 **48 个新 Prompt × 4 个模型 = 192 份生成结果**。若资源限制且需要严格最短路径，明确降级为**3 个核心臂：Base、v0.2、Base336 = 144 份**；不应降到只有 Base/Base336 两臂。任何降级/是否纳入 v0.3-A **必须在首次查看 P2 生成及评分结果之前由 Owner 冻结**，不得看结果后再选择增加/移除臂。
- **主预注册比较**：Base336 vs Base、Base336 vs v0.2；**诊断比较**：Base336 vs v0.3-A；各臂均同一批 48 Prompt、逐案生成一次，同一 Model revision / Tokenizer / Chat Template / 三消息上下文 / 解码 / seed / stop / token budget。对每对模型的逐案结果、六维得分、严重自主权/禁句/安全标记独立报告，避免只用“四选一冠军”隐藏硬规则回退。
- 盲化时每条 Prompt 的四份回答随机匿名化，保留只在 Owner 的 create-only 0600 身份密钥；评审者不获模型名单对应关系。三名独立 Reviewer 的**独立性**需要实证，不能只凭不同 AI 模型 ID。48 prompts 分 8 世界、5 作者，按世界/作者聚类报告不确定性，不把 192 个输出或 Reviewer × Prompt 评分当作独立 Story。
- 旧 v0.1 / v0.2 / v0.3 数据与训练输入的 System/World/Rules 差异、部署 Prompt 分布差异必须披露；相同推理 Prompt 保证**操作层面可比**，不意味着唯一因果变量是训练数据。任何臂无法验证固定 Base revision、旧 Adapter SHA/加载、历史训练数据泄漏风险或完整 P2-C 许可时，**先 HOLD / 调整正式预注册**，不可静默替换模型。
- 本次变动只更新**方案**；P2-C=HOLD、48 真实 Prompt=NOT_GENERATED、P3 两/四臂 Backend 尚未实现、P4 GPU/HF 未授权、train/quality admission=0、model_promoted=false 均不变。复用 `generation_eval.worker` / HF Runtime，不为四臂重写底层执行器。

**历史决策依据：**
`docs/evidence/V02_R47_2_THREE_MODEL_UNBLIND_RESULTS_20261014.md`；
`docs/evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.md`；
`docs/evidence/V03_R55_CHECKPOINT16_CANDIDATE_GO_NO_GO_20261023.md`；
`docs/evidence/V03_R50_OWNER_STORY_INDEPENDENCE_ATTESTATION_AND_R56_NEXT_GATE_20261023.md`。

---


> **最高优先级 / 直接复制给新 Agent。** 本文取代 2026-11-17 的通用启动提示词和 2026-11-18 的 P2 Crosswalk 提示词中的“当前步骤”与过期状态；旧文件保留为历史过程。若与旧文档的待办、授权要求或文件存在性判断冲突，先核对本文件引用的最新真实 SAFE，再以本文件的工作顺序为准。
>
> 仓库：`sunxu/storyforge`。当前执行 PR：[PR #31](https://github.com/sunxu/storyforge/pull/31)，工作分支 `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118`，目标合并基线 `r60/common2-cpu2-owner`；这些是**截至 2026-11-19 的快照**，新 Agent 必须实时确认 HEAD / PR / CI，不假设本文件记载的提交永远最新。

## 一、唯一业务目标（禁止偏航）

完成已训练的 **R60 Base336 checkpoint-37 Adapter** 与对应 **Qwen Base** 的**新来源、真正独立、六维盲化质量比较**，进而给出有证据边界的质量结论，而不是继续审计旧 R50/R58、反复补写工具或证明模型已晋升。

固定路线：

1. **P0 / P1 已完成**：Base336 探索性 GPU 训练与工程产物核验；293 Train / 43 Validation；37/37 steps，Adapter reload，33/33 远端对象 inventory。模型**未晋升**。293/43 均不可做独立 Held-out，43 曾参与 Eval / checkpoint 选择。
2. **P2-A 已完成**：Owner 已批准 Supabase **8 条公开已发布原创 Story**（来自 5 位作者、8 个不同 World JSON），逐条 revision、moderation snapshot、permission 绑定完成；授权仅限**内部独立评估提示构造**，并非训练、公开发布、再分发授权。不得查询私有会话正文。
3. **P2-C 当前主要阻塞**：对这 **8 条新 P2 来源**证明与已训练/验证、受保护/保留、历史开发/训练/教师暴露来源之间的精确身份和**实质世界/角色/剧情/开场语义**隔离，证明真实历史版本/actual-sent 与受审范围、进行可核验的独立 Reviewer 审查及 Owner 冻结。**不得将只证明局部精确 ID 零交集的 SAFE 升级为 P2-C PASS。**
4. **P2-B（在 P2-C 及用途权利门禁完成后）**：构造并冻结 **8 × 6 = 48** 条真实提示 JSONL / Manifest / SHA256，Quality-v1 六维各来源各 1 条：`chinese_prose`、`character_consistency`、`npc_initiative`、`player_agency`、`rule_fidelity`、`narrative_continuity`。每条是新编 `user / assistant / user` 三条可见持久化消息，**无 System、模型生成输入无参考答案、无私有历史对话**；逐条核验公开素材忠实性、权限、无未来信息、无原文长段复制、无隐藏指令/冒称源事实。当前**没有真实 48 条包**；既有 9/9 是合成测试。
5. **P3（P2-C 后）**：只制作本任务必须的 Base/Adapter 两臂薄适配器与合成测试，优先复用 `generation_eval.worker.run_generation_batch`、`hf_runtime.inputs/outputs`、`GenerationBackend`、现有配对/盲化思路与 `experiments/r58_quality/quality_v1.py`。不写另一套生成循环/IO/六维 Rubric，不修改旧 P4 三臂冻结 Profile。
6. **P4 / P5（另行授权）**：同一冻结 Base revision、checkpoint-37 Adapter、同 prompt SHA、Tokenizer/Template、三消息上下文、seed/解码/Token 上限/stop 条件配对生成；私有 A/B 密钥隔离，独立 Reviewer 六维盲审，重视严重 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`，Owner 裁决。**任何新 GPU/HF 推理、训练或付费任务必须就具体运行另行明确授权**；本任务目前没有此授权。

## 二、最新真实证据状态（2026-11-19）

| 子任务 | 已关闭的实际结果 | **尚未关闭、不能外推** |
|---|---|---|
| P2-A 8 个公开来源 | 8 sources / 5 authors；snapshot、permission、revision 与 World metadata 绑定 READY | P2-C 语义、历史曝光与 Owner 最终冻结 |
| P2 × Base336 冻结身份 | 336 cases / 172 distinct Story，**8 × 172 精确 Story ID overlap=0**，离线捕获范围预检 PASS | 全 172 Story 当前+存档 `world/character/characters/opening` 来源包**尚未生成**；Owner 捕获 `DB_BASE336_SOURCE_QUERY_HOLD`，未有根因证据或全覆盖语义 PASS |
| 旧 Base336 八组成员分析 | 历史 8 组 World，38 Story / 59 当前+存档来源记录已核验；旧 10 条跨拆分候选边图含 16 Story / 35 cases；A/B 表单已填写，B 资格尚未由 Owner 验证 | 这些是**旧 Base336 内部冲突**，**不是新 P2 8 来源**的隔离证明；旧 Reviewer A 无合格独立性证据，B 待 Owner 核验 |
| R50 原始 50 → 46 + 4 | 原始 provenance 50、派生 46、排除 4 元数据补集严格 PASS；密封题目未打开 | R50 正式 sealed cases 字节/Final Seal 不是本轮复核；**其他 Protected/Reserved 世界权威全集**仍 HOLD |
| R50 冻结五世界 | 固定 Git 两份 SAFE Blob 锁定 W16–W20、5 个 Story / 5 个 Session / 35 源文件；Owner 核对五个固定 Story UUID **恰等于原 50 provenance 所有来源 Story 集合**；P2 × 五世界精确交集 **0** | 五世界之外的 Protected/Reserved 源、隐藏语义别名及覆盖权威性均未证明 |
| R47/R48/R55 旧开发链 | 同一 **20 Prompt = 2 个 Story**；R47 Sample→canonical Test Story ID、R48 source SHA、R55 三层 Index **76/68/46** / 20/20 回链已 PASS；P2 × 该链精确交集 **0** | **其他**历史 Dev/仲裁、Teacher、训练、独立保留来源完整暴露全集仍 HOLD |
| R58 旧五范围 CSV | Owner 实际回执：5 行全部 `MISSING_SOURCE_REFERENCE`，`source_files_present_unopened=0` | 只表示这个旧 CSV **没有绑定来源引用**，不代表源文件不存在；**不要再使用/重跑**来冒充 R60 全集证据 |
| 版本/审查 | P2 元数据快照已绑定；旧 38 Story 有静态版本证据 | Base336 历史 `actual-sent`、全部语义世界组件源引用、P2 8 新来源 Reviewer 独立执行与 Owner Freeze 仍 HOLD |

原始已通过 SAFE 的关键路径（GitHub 可公开、没有私人 ID / 原文）：
- `docs/evidence/R60_P2_R50_50_46_4_PROVENANCE_COMPLEMENT_SAFE_20261119.json`
- `docs/evidence/R60_P2_R50_PINNED5_TO_PROVENANCE_OWNER_SAFE_20261119.json`
- `docs/evidence/R60_BASE336_P2C_MAINLINE_GATE_STATUS_SAFE_20261119.json`（衍生状态投影，不是独立 Owner 执行）
- `docs/evidence/R60_P2C_R58_G1_EMPTY_SOURCE_REFERENCES_OWNER_SAFE_20261119.json`
- `docs/evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md`
- `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`（历史与最新附记并存，避免误读旧段）

## 三、**禁止重复清单**（除非发生可验证的输入版本变更）

不再执行：P2-A 8 来源再次筛选/数据库重抽；R50 50/46/4 补集；R50 已固定 5 世界与原 50 来源身份比对；R47/R48 20-case / R55 三层 SHA 与 Token 链；R58 五行空白 CSV；Base336 旧 38 Story/59 records 的 Card/Opening 提取、结构审核；旧 10 边/35 案例冲突预览；293/43 训练/33 产物审计；相同 Base336 全量 SQL 的猜测性重试；生成、重造或覆盖既有私有包。

旧 Reviewer B 的独立资格**仍不等于已认证**，但此事不是当前推进新 P2 8 来源的第一阻塞；不要让旧 35 案例审查反客为主。所有旧结果仅继承其**已证实范围**。禁止为补出漂亮的 PASS 擅自修改冻结数据、换 Story、猜来源、填虚构空白索引、放宽 DB RLS 或将历史匿名评测重新包装成新 Held-out。

## 四、下一 Agent 第一轮应做的**真正新增工作**

1. **定位最后一个能推动 P2-C 的证据缺口**，不要先跑工具：核对 GitHub PR #31 当前 HEAD / Actions 与上面列出的最近 SAFE；给出简洁的“已覆盖集合 → 对 P2 8 来源还缺什么 → 现存可信来源路径 → 可获得性”对照表。已有证据不再计为新成果。
2. **优先针对新 8 P2 来源**形成真实、可审核的语义隔离裁决准备：复用 Owner 本地的已批准 P2 Source Manifest、Base336 冻结 roster、现有成员级 World/Character/Opening 证据与 `src/storyforge_dataset/world_isolation.py`。严格区分精确 ID 零重叠、字段相等、专属角色/组织/地点/事件复用、独立模板，以及完整语义组件同源；每项冲突要有 Owner-only 来源字段、版本与证据引用。**不对旧 Base336 十条边再启动 Reviewer**。已存 38 Story 是部分样本，未核验其余 134 Story 及归档版本的不能静默 PASS。
3. **处理全 172 Story 的数据可获得性，不重复盲调**：既有捕获脚本 `experiments/r58_quality/r60_base336_p2_source_evidence_capture_cpu.py` 在 Owner Mac 停于 `DB_BASE336_SOURCE_QUERY_HOLD`。先查是否存在同版本、可信赖且来源完整的 Owner 本地冻结快照/原版证据可直接复用；若没有，**只在能指认 SQL 执行失败的真实原因与最小修复时**使用已授权的只读 DB 权限推进一次有界恢复，勿不断新增捕获器或扩大权限。证据缺失如实 HOLD，绝不按当前 DB World 值冒充历史实际发送。
4. **旧保护/暴露全集只做未关闭的差集**：R50 的 W16–W20 五世界已闭合；R47/R48/R55 同一 20 Prompt 已闭合。剩余明确是旧 R58 权威来源缺口标签 `r55_r57_other_dev`、`other_reserved_heldout`、`other_historical_training`，以及本 R60 阶段其他真实暴露索引。寻找**经授权、冻结且有来源版本/截止边界**的 metadata-only roster；按世界组件和来源绑定审核，不重做 ID 计数。没有权威全集时写明 UNKNOWN/HOLD 与缺少的确切 source authority，不要无期限扫描全机器或重复运行空索引。**R50 只读身份/保护 metadata，绝不打开密封正文。**
5. **独立 Review / actual-sent / Owner 冻结**：明确新 8 来源当前的独立审核能否执行、历史真实发送内容/版本的证据是否存在。Review 必须独立并有版本化证据引用，不能把已知旧 Reviewer 的主观意见或签字当作 P2 新来源 PASS。Owner 冻结前只保留候选，不宣称正式 P2-C 通过。
6. **收敛而非扩散**：完成一项真实闭合的证据后更新统一 SAFE/文档；若根本缺少权威来源证据，提交清晰的“现有证据不能证明什么 + 最小可信新证据”结论，并推进其它不依赖的既定主线事项。不以单纯加文档、补 CI、旧文件存在性检查或合成测试自称 P2-C 进度。

## 五、权限、代码复用和验收规范

- Owner 已于本轮明确授权 **StoryForge 本任务必需、限定只读范围**的数据库核验，**后续这类只读访问无需逐次重复请示**；继续执行 read-only/RLS、最小字段与固定 ID 过滤。**不授权**写库、读 R50 密封题目/答案/私有聊天、扩大版权用途、修改冻结 Train/Validation、模型推理、GPU/HF 或训练。
- 既有核心优先：`world_isolation.py::validate_component_review_assignments`、`component_split_conflicts`；Owner R50 provenance / protected IDs 复用 `r60_r50_original50_complement_cpu.py` 与 `check_r50_protected_uuid.py`；来源包结构预检 `r60_p2c_existing_source_package_preflight_cpu.py`；P2 Prompt gate `r60_base336_p2_public_prompt_package_gate.py`；P3 则复用 `generation_eval.worker`、HF Runtime。
- 必须区分 **P2 新 8 来源** 与 **Base336 旧 8 组 World**；区分 **20 Prompt** 与 **2 个 Story**；区分“文件存在”、“来源元数据闭合”、“完整语义隔离”、“真实历史发送”和“Owner 冻结”，任何一个都不能代替另一个。
- Owner 私有文件、完整 Story ID/UUID、版本映射、逐条证据引文、SHA Manifest、Reviewer 身份与密钥全部留在 Owner 0700/0600 路径。GitHub/聊天仅放 SAFE 聚合、合成测试与必要的公开代码；不得输出私有正文、连接串、异常原文或逐案映射。
- 每次需要提交代码前先确认现有函数不能完成任务；只作最小必要修复，不为追求“诊断完备”反复扩展工具。GitHub 使用 PR #31 当前分支；不 force push、不覆盖其他 Agent 私有成果；每次提交检查**该 HEAD** 的 CI，不把合成 CI 当作真实来源验收。
- **硬状态不变**：`P2_A=READY`、`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`train_admitted=0`、`quality_v1_admitted=0`、`model_promoted=false`。无新权限不得提交 HF Job 或启动 GPU；在 P2 仍 HOLD 时不得产出正式 48 prompt 包或投入配对推理。

## 六、完整任务书与交接时的输出格式

先读：
1. `AGENTS.md`；
2. `docs/plans/R60_BASE336_POST_TRAIN_QUALITY_EVALUATION_20261117_CN.md` 与 `docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`（总体目标、用途权利与六维合同）；
3. `docs/R60_BASE336_P2C_MAINLINE_NEXT_ACTION_20261119_CN.md` **最顶部最新 Owner 结果**与 `docs/evidence/R60_BASE336_P2C_MAINLINE_GATE_STATUS_SAFE_20261119.json`；
4. 上述已通过 SAFE 原件与 `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md` 的最新段落；
5. 仅在实际动手前读直接相关代码及合成测试，**不必逐个复演历史脚本**。

新 Agent 首次答复应有：当前 HEAD / PR CI；一句话重申最终 **48 prompt → 两臂生成 → 六维独立盲评** 目标；按来源范围拆分的 **PASS / HOLD 与最新 SAFE 引用**；**已证明的内容不再重复做**；下一项最短能实际闭合的 P2 新 8 来源证据动作；无需新代码时明确“不改代码”；是否访问 DB、提交 HF / GPU、读保护内容；新结果若无法产生，也必须准确说明缺少哪一种权威证据。**不要以新的空泛审计任务书代替推进工作。**
