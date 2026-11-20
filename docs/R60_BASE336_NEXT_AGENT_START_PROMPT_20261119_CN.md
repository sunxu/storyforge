# R60 Base336 P2 Quality-v1：2026-11-19 新 Agent 启动提示词（可直接复制）

## 2026-11-20 必须优先执行的 Owner 最新裁决（覆盖本文 2026-11-19 旧提示）

**唯一现行任务书**：先读 `docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md` 顶端 “Owner 正式批准” 新节与 “2026-11-20 现行唯一执行基线”，不要执行下列旧“5 作者/3+5、缺 172 Story、没有 48 条原始回复、两臂、须查历史 actual-sent”步骤。

Owner 已批准 **`RECONSTRUCTED_EVALUATION_INPUT`** 作 Gold48 统一评估输入：不访问 RolePlay 生产环境，不再将历史 HTTP/Provider 真实发送字节作为本轮 Quality-v1 准入前置；`ACTUAL_SENT_PROMPT_BYTES=UNVERIFIED` 保持。已经核验候选为 **8 Story/7 作者/2 GPU 前+6 后、25 Session、48 个唯一完整历史 Prefix 与 48 个匹配的真实 Historical Original Reference，48/48 成功请求事件元数据唯一匹配**。未正式冻结。

固定四生成模型：Qwen Base、R46 v0.2 ckpt-7、R54 v0.3-A ckpt-16、R60 Base336 ckpt-37；未来四臂用同一冻结重建消息作严格同题配对。第五匿名来源是历史原始回复：六维共同盲评，但当年 Provider 实际 System/Memory 等未验证，所以**只做同历史上下文描述性参考比较，不声称其与新四臂 byte-exact 同 Prompt 或严格因果对比**。主分析若 Owner 仲裁允许保留疑似有角色家族名残留来源，则预注册 48 题和排除此来源六题的 42 题敏感性分析。

已经独立审核 Base336 172 Story/375 版本与历史增量 32 Story/120 版本（去重 204 Story/495 版本）各 8/8 的限定来源语义结果；R45 原始 49/15 与 R46 source-data 相同 Git Blob，已知 R50/R47/R48/R55 子集不重做。**只剩**未闭合的其它历史 Protected/Reserved/Held-out/Dev/Arbitration/Teacher 完整 Authority 与真实新差集、一个 P2 源自身质量仲裁、有效权限及 Owner Gold48 Freeze。缺权威全集为 `UNKNOWN_HOLD`，不可假定通过。**当前 `P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`；没有 GPU/HF/模型调用批准。** 只读/SAFE、禁 R50 sealed、禁敏感原文上 GitHub/Chat。

---


## 2026-11-19 必须包含原始回答 Gold 的最新 Owner 要求（优先于以上内容）

**必需增加第五种“回答来源”：同题、同历史上下文、可追溯来源与授权的原始 Assistant 回答 Gold**。它不是第五个生成模型；正式候选为 **原始 Gold + Qwen Base + R46 v0.2 + R54 v0.3-A + R60 Base336 checkpoint-37**。主比较**必须包括 Base336 vs Gold**；原始 Gold 也接受六维评分、严重违规判定和盲化，不视为天然正确。四模型 48 题产生 192 条模型输出，加 48 条真实原始回复才是 240 份盲评文本。

**目前 P2 新 48 提示是拟从 8 个公开 Story 的 World/Opening 新构造的情境，尚无经验证的逐题原始回复。** 你必须在新 P2 来源隔离工作中确认合法的原始 Prompt/Reply 是否存在、能否与冻结 prompt 逐字逐消息匹配；没有就明确 `P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD`，提出最小的 Owner 决策，**不得**用旧 R48 Gold、公开 Opening、模型代写或私有用户聊天补齐。可复用 `scripts/v02_r48_four_arm_build.py::read_gold` 的完整上下文前缀校验思想；Gold 仅匿名进入 Reviewer，绝不能流入模型生成输入。若不可得，不能冒充新五回答来源测试已经完整；旧 20 题只能独立做 EXPOSED_DEV 回归。

其它 P2-C、来源权利、正式 48 Prompt、GPU/HF 单独授权和非重复执行约束不变。权威细则见 [本轮任务书第八节](R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)。

---


## 2026-11-19 模型阵容更新提示（优先于本文旧两臂文字）

经回顾 R47/R48/R50/R54/R55，**建议预注册四个被测生成模型：同一 Qwen Base、R46 v0.2 checkpoint-7、R54 v0.3-A checkpoint-16、R60 Base336 checkpoint-37**。主检验是 Base336 对 Base 与历史强基准 v0.2；v0.3-A 是旧 R55 混合回退的诊断对照；预算有限则先冻结 Base/v0.2/Base336 三臂。历史 v0.1 非本次必要臂，原始 Gold 不是模型。**这只是模型阵容设计建议，Owner 尚未最终冻结，P2-C 尚未 PASS，P4 GPU/HF 仍须单独批准**。请读完整交接任务书第七节，不要直接按旧提示词的“两臂”硬编码运行时或启动生成。

---


你接手 GitHub 仓库 **sunxu/storyforge** 的 **R60 Base336 训练后独立质量评估**，当前 PR #31，开发分支 `docs/r60-p2-r47-r48-r55-source-shape-audit-20261118`，目标基线 `r60/common2-cpu2-owner`。立即核验实际 HEAD、Actions、工作树/PR 状态；不要假设历史 SHA 仍为最新。

**唯一主线目标**：对已经完成但未晋升的 Base336 checkpoint-37 Adapter，采用 **8 条已批准公开新 Story**，在完成 P2-C 实质语义及来源隔离之后，构造 **8×6=48** 条真实的六维独立质量提示，进行相同 prompt 的 **Qwen Base vs Adapter** 两臂盲化评测，判断是否真实改善质量。不是继续开展 R50/R58 旧审计、旧 35 案例图或重复开发工具。

**先读本次唯一权威任务书**：`docs/R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md`，再按其中定位到 `AGENTS.md`、当前 Quality 计划 / P2 来源 Addendum、最新主线 SAFE 状态以及必要源码；历史旧启动提示词中的“第一步”已过期。

**接收下列已通过证据，禁止重跑**：
- P0/P1 工程训练：293/43，37 steps，checkpoint-37 Adapter，33/33 对象盘点；未晋升，43 Validation 已污染独立评估资格。
- P2-A：8 个公开新 Story（5 作者、8 World JSON）revision/审核/权限 READY；仅限内部评估提示构造。
- P2 × Base336 172 Story 精确 ID overlap=0，336 案例/172 Story 冻结身份预检完成；**完整 172 Story 当前+存档 World/Character/Opening 语义证据仍缺**，Owner 捕获 SQL 停于 `DB_BASE336_SOURCE_QUERY_HOLD`，不再无依据盲试。
- R50 原始 provenance **50=46+4** PASS；冻结 W16–W20 五世界 **恰等于** 50 条来源 Story 集合，P2 × 其精确重叠 0；R50 题目从未打开。**其它 Protected/Reserved 来源全集未闭合**。
- R47/R48/R55 同一旧 **20 Prompt / 2 Story** 精确交集 0；R55 三层 76/68/46 Index 和完整 20/20 回链已 PASS。**其它**历史 Dev/仲裁/训练/教师暴露全集未闭合。
- 旧 Base336 八组 38 Story/59 当前+存档证据、10 边/35 案例图及 A/B 审核已核对；它们**不是 P2 8 个新来源**。Reviewer B 独立性仍未经 Owner 核实，但不要让旧图审计取代新 P2 主线。
- R58 五范围 CSV 的五个引用均为空，不能将其当作源文件不存在或独立隔离 PASS；不要再运行该 CSV 工具。

**下一项实质工作**：围绕**新 P2 8 来源**，基于已存在的 Owner 冻结来源、可信当前+归档版本和世界/角色/开场信息，明确 8×172 中未覆盖的数据范围及可复用证据，推进可验证的语义组件排除与独立审查；并只追踪**尚未关闭的**其它 Protected/Reserved、Dev/仲裁、历史训练/教师曝光权威全集和 actual-sent 证据。来源缺失就保留精确 HOLD，不自行制造“完整”证据；只有知道真实失败原因才考虑有界只读 DB 查询，禁止无限调试/重复建设。对每一步区分精确 ID、语义世界组件、实际发送、权利、Reviewer 独立性与 Owner 冻结。

优先复用 `src/storyforge_dataset/world_isolation.py`、既有来源 preflight、冻结 R50 metadata 读取与 `generation_eval.worker` / HF Runtime / `quality_v1.py`，不复制 World 冲突、生成循环、IO、六维评分逻辑。

**权限**：Owner 已授权本项目限定范围的**只读** DB 核验无需再次逐项请示；不允许写数据库、读 R50 密封正文/答案、读私有聊天、上传私有 UUID/故事/证据/映射、修改冻结训练/验证或旧证据。**GPU/HF 配对推理或训练需要针对具体运行单独授权**，不能继承训练 Job 的批准。

现行硬状态：`P2_A=READY`；`P2_C=HOLD`；`P2_B_48_PROMPTS=NOT_GENERATED`；`train_admitted=0`；`quality_v1_admitted=0`；`model_promoted=false`。

**立即行动**：用真实 GitHub HEAD / SAFE 做一次目标导向的“已证实 → 真正缺什么 → 现成证据如何推进”的差距核对，随后尽可能直接完成一个**新的** P2 来源隔离子成果；不要先发起另一轮历史目录盘点或只增加审计任务书。交付准确的已核验/未核验清单、使用过的现有代码、结果 SAFE、变更 commit/对应 HEAD 的 CI、下一最短动作，并明确本轮有无 DB/GPU/HF/密封内容访问。
