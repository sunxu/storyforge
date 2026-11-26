# StoryForge — 新来源质量数据建设任务书

**版本：** v1.1（2026-11-26）  
**决议：** Owner 已批准将数据建设主线转向新采集、来源可控的高质量原始互动样本。  
**范围：** 新原创世界有限采集、审核、证据绑定；当前 World04 有限定 HF 双审授权，变更外发路由须确认；非 R61 启动、训练或生产部署授权。  
**文档基线：** `main@5de5f81f1db1724419dc699c815ae4e042639b17`；接手时重新核验 HEAD。  
**状态：** `WORLD04_REVIEW_INPUT2_READY__HF_ROUTE_SMOKE2_PASS__ADMISSION_HOLD`。

## 0. 2026-11-26 实际进展与现行下一步（覆盖下文旧采集状态）

- 已按 Owner 逐次批准完成四个世界的有限筛选，共 16 条原始回复，World04 冻结 2 条优先候选（另 1 条条件候选不扩入本轮）；未准入。Owner 已确认来源使用权，授权离线重建与本地复用。已有 Source Stage 在 Mac 实测 2/2，消息数 2、10，原始目标和在先正文保持；后续正文任务 System 定稿、排除无关技术字段（29 个技术 ID，另封面资源），盲审包 2/2，URL/邮箱/手机号/UUID 模式零命中。Owner 已明确人工检查盲审包并确认可外发信息范围。原始组件留证不改；正文监督与历史抽取/Compiler 一致，但不是完整生产组件输出合同，也不是实际发送 Prompt 重放；时间点完整性和 Provider 原始请求未证实。
- 本轮 World04 对 Base336、History32、R50 已知五世界、P2 八来源精确 ID 无重叠；Base336 375 版本及 P2 8 版本的四字段与姓名初筛均零命中，History32 版本级筛查本轮未完成。语义独立、完整保护集覆盖仍 HOLD；不读取 R50 密封正文，不重跑旧候选隔离或无限搜索历史全集。
- Owner 批准对两条冻结候选进行 HF 独立双审与数据外发，取消费用上限；原两条路由 4 次 HTTP 400，无有效评审，原回执保留。最新 Router 合成测试 2/2 PASS（DeepSeek-V4.1-Flash-1017 / Cloudflare，Kimi-K3.1-Pro / DeepInfra），无私有正文外发于该合成测试。具体已验证调用规范、模型映射、费用及失败经验见 [资产索引](../REUSABLE_ASSET_INDEX.md)。新模型/服务商实际私有外发须确认；不重复询问已完成的隐私审核或训练权利。
- **唯一下一步**：确认上述新路由正式私有外发范围后，复用已冻结的盲审包及既有评分合同，四次正式调用（两候选 × 两独立 Reviewer），不自动重试/换模型，不改 Prompt 或原文；保存失败/成功原始回执及 SAFE。四次正式有效审查尚未完成（0/4）。仅实际双 PASS 候选继续证据闭合；若无双 PASS，停止本批，不开发 corpus 扩展。完整隔离与 Owner 质量批准仍是独立门禁。正式评审授权不含 HF Job、GPU、训练、生产部署、晋升或 R61。
- 本轮一次性 Mac 操作不提交仓库；已有 Source Stage/Quality-v1/Compiler 等优先复用，只有真实合格样本明确阻塞才做最小兼容实现。保持 `quality_v1_admitted=0`、`train_admitted=0`、`training_authorized=false`、`model_promoted=false`、`r61_started=false`，R60 NO_PROMOTE。

## 1. 唯一产品目标

训练真正优于 Qwen/Qwen3.8-27B Base 的高质量中文互动剧情能力。重点是中文文学表达、角色与世界事实一致性、NPC 有效推进、玩家自主权、硬规则与跨轮连续性。数据数量、回复字数、工程 PASS、训练损失或迁移代码量不是模型质量指标。优先解决真实数据质量，不扩张工具体系。

## 2. 已结论事项与停止边界

| 对象 | 结论与下一步 |
|---|---|
| R60 Base336 / Gold48 | 冻结 NO_PROMOTE。Gold48 已用于诊断，不得冒充新独立测试。R60 冻结归档 `archive/r60-final-20261122@15462b8779401833a5014846bc57318dd6bc1b1c` 不修改。 |
| Base336 输入合同 | 实际发布 293 Train / 43 Validation，三条历史消息＋末轮 Assistant，无 System；训练目标长度偏短。与真实长上下文场景存在输入分布差异；不能据此认定微调退化的唯一因果。 |
| Gold48 | 48 题、8 Story、25 Session，同重建输入四生成臂；历史 Original 仅描述性参考。R60−R54 NPC 评分 −0.198，连续性 −0.167；信号不等于原因。 |
| E1/E4 限定诊断 | HF Job `6b07d8dab6a90bbe997f75fd`，Base/R60 各 10 条，20/20 EOS、无 length 截断；原始输出 token 数均值 550.1 / 253.5（R60 约少 54%，9/10 更短）。此为已执行的限定诊断；Owner 独立质量签署未完成，不能据长度作单一质量裁决。E1/E4 继续评估专用，E2/E3 不恢复；不重跑 GPU 或付费 Judge。 |
| Gold12 历史候选 | 12 条可供私人 triage；已诊断 6 条：1 条优先原始候选、1 条待修订参考、4 条不建议正向准入；其余 6 条停止筛选。修订件为派生参考，非 original Gold；原始评分不覆盖。私有个案映射留 Owner 域。 |
| 历史隔离初筛 | Owner-local 实际 SAFE：Base336 172 + 历史差集 32 = 204 Story，优先原始候选精确 ID overlap=0；R50 已知五 Story、最终 P2 八 Story 精确 ID 无重叠；375+120+8=503 个版本的指定五个人物名与 character/characters/opening 完整字段精确筛查无命中。此为限定范围初筛，不是语义独立或完整保护集证明；未独立重哈希全部历史文件。 |
| 旧 R59 五条 / Gold195 等 | 原有 HOLD 与历史证据保持原样；不重复 Stage、Autolink、Binder、历史恢复、旧评审、保护集无限搜索。 |
| 工程收敛 | PR #38 已合并 Quality-v1 内核及测试。其他资产仍按实际 HEAD 查证，禁止整体合并旧分支、重复开发或提前迁移。 |

优先历史原始候选仅作为质量参考，保持正式准入 HOLD；不再为其追加付费评审、语义审核或编译任务。所有旧未准入数据不自动入训。新证据如证实保护集重叠，立即隔离并记录，不修改冻结原件。

诊断依据：[R60 最终决定](../R60_BASE336_GOLD48_QUALITY_V1_FINAL_OWNER_DECISION_20261122_CN.md)、[最小改进方案](../quality/R60_FAILURE_MODES_MINIMAL_IMPROVEMENT_PLAN_20261122_CN.md)、[Gold3 诊断与收口补充](../quality/GOLD3_OWNER_LOCAL_QUALITY_DIAGNOSIS_20261125_CN.md)。E1/E4 依据既有 HF SAFE 及实际输出 token 计数，原文留私有域。

## 3. 首个新来源试点（建议上限：1 世界、3–5 个目标）

这是小规模数据流程试点，不是训练数据量目标，也不证明泛化。未达质量门槛宁可少收或零收；不自动扩至第二世界或批量采集。优先 Owner 可控、合法原创测试会话，不从生产历史随机抽样。由 Owner 提供或确认原创故事及测试会话、使用权、玩家身份、硬规则和采集方式；不将助手生成的修订/教师续写冒充原始互动，不将未授权第三方内容用于训练。

### A. 先冻结新来源再采集

- 明确来源权利及使用范围；记录新世界来源/创作证据、创建时间、卡版本及摘要，明确原创世界不是既有角色、剧情、改名变体或已知保护源的衍生。
- 预先分配世界组件及用途。首个世界只作为 train-candidate；同一世界所有会话、变体不得跨 Train/Validation/Protected。未来独立评估使用不同合法、预留世界；不从本世界拆出假独立测试。
- 记录完整角色、世界、硬规则、玩家/NPC 归属、允许动作扩写边界、叙事视角、长度/状态栏等格式条件。不得为方便评审而默默删掉有效规则。
- 保护集禁止访问 R50 密封正文，仅使用有权的元数据。历史全集未知继续记 UNKNOWN/HOLD；新创作证据帮助证明新源归属，但不自动代替隔离证据或签收。不继承 R60 限定评估风险接受为本次训练授权。

### B. 采集原始互动

Owner 可控测试会话中进行真实多轮互动，原样保留有效角色顺序、当前 User、所有相关在先上下文及原始 Assistant 目标，记录模型/版本、时间、生成配置（可得时 finish_reason）、故事卡版本与来源绑定。保留上下文/目标摘要、隐私处理的转换关系及必要来源字段，原件 create-only、可追溯、不覆盖。优先在采集时冻结真实输入；若采用合法离线构造，必须明确标注并经批准、可复现、忠实适用、无未来信息；不要求伪造或强制回放历史 Provider 请求字节。

首批选 3–5 条候选，关注真实上下文承接、NPC 自主行动带来新状态且保留玩家反应窗口、复杂约束、角色逻辑、避免历史回放/段落循环。长度随明确要求和叙事任务，不设 300–1500 的机械筛选门槛；明确篇幅/格式要求仍需遵守。禁止合成用户历史冒充真实交互；安全排除的内容不得纳入正向数据。

### C. 审核与证据

沿用 Quality-v1 六维门槛（中文4、角色4、NPC3、玩家自主权4、规则4、连续性4）与三个严重标记。两份独立、匿名、可定位证据的评审；保持各自评分和分歧，严重违规按既有判定，争议 HOLD，不覆盖历史分数。Owner 独立质量批准与审核者真实独立性证据分别记录。助手诊断或单次 AI 评分不是双审；无实际评审不得宣告 PASS。

先做本地隐私审核，联系方式、资源标识、无关用户身份等按用途脱敏；保留原始与派生摘要及转换版本，不静默改写故事逻辑/目标。独立 Reviewer 交付范围和任何外部模型/服务调用须经适用授权。私有文件 0600、目录 0700、Git 外；普通聊天/日志/GitHub 只留 SAFE 聚合，不披露正文、逐案身份、来源哈希或 crosswalk。Owner 定向提供材料时只取必要范围。

### D. 编译与预检（有真实合格候选后）

- 当前主线 `src/storyforge_gold_quality/quality_v1.py` 仅接受 `gold195`、`r58_round1` 与 `source_kind=original_gold`。新来源不冒充旧 corpus；待真实样本、来源及目标合同明确后，先确认现成批次登记能力，确有阻塞才提出最小兼容扩展及合成回归，单独审查。不得删除/放宽原门禁或扩大旧 R58 限额。
- 复用既有 SFT compiler（PR #11，固定来源见资产索引），构建完整适用 System + 有效历史 + 当前 User + 唯一末轮 Assistant 目标；不要为通过 16K 而盲截系统规则或历史。若超预算，审查合法保留策略并明确标注，不暗删。最后一轮监督 `loss_scale: last_round`；真实 tokenizer/chat template/collator 及掩码按现行 HF CPU 合同验证，Mac 只做 stdlib/CLI 私有准备，不安装本机 Transformers/Torch/ms-swift。
- 只有候选证据齐备且有适用的 CPU 执行授权才进行真实预检。结构/Token/Collator PASS 不等于质量准入，也不授予 GPU 训练权限。试点最多是候选流程验证，不能凭 3–5 条安排训练。

## 4. 复用路径

按 [REUSABLE_ASSET_INDEX](../REUSABLE_ASSET_INDEX.md)、[有限工程任务书](STORYFORGE_QUALITY_ENGINEERING_CONSOLIDATION_TASKBOOK_20261124_CN.md) 查重。优先 main Quality-v1；SFT Skill、History Recovery、World Isolation、SFT compiler、HF CPU Runtime 均先查历史固定提交和测试，按需复用，非全部已经在 main。旧 R58 Skill 权威参考位于冻结 R60 `skills/storyforge-roleplay-sft/SKILL.md`；本次 Owner 新来源决议取代旧优先级作为当前工作顺序，但不自动变更任何代码支持的 corpus/门禁。无真实需要不移植，不新建评审器、隔离器、Runtime 或数据管线。

## 5. 交付、停机与授权

当前接手直接依据第 0 节推进已冻结 World04，不重新采集。后续新试点如另获批准，先确认已有材料；不得未经授权创建生产数据、启动模型请求、HF Job、付费 Judge、训练或晋升。

阶段交付：新源的版本/权利/用途与隔离证据、少量原始互动私有候选和 SAFE 回执；独立审核与编译仅在各前置成立时继续。有任何真实阻塞只报告缺件与下一项最小动作，不继续历史搜索或用假 PASS 补齐。首批目标、实际采集量、审核量均未发生时明确为0。

状态保持：`quality_v1_admitted=0`、`train_admitted=0`、`training_authorized=false`、`model_promoted=false`、`r61_started=false`，R60 `NO_PROMOTE`。最终独立评估设计、模型调用、GPU、训练、晋升各自另行授权；禁止利用已暴露 Gold48/E1/E4 做训练或调参。

新 Agent 入口：[接手提示词](../handoffs/STORYFORGE_NEW_SOURCE_QUALITY_NEXT_AGENT_20261126_CN.md)。
