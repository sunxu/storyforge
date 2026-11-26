# StoryForge — 新来源质量数据建设任务书

**版本：** v1.7（2026-11-27）  
**决议：** Owner 已批准将数据建设主线转向新采集、来源可控的高质量原始互动样本。  
**范围：** 新原创世界有限采集、审核、证据绑定；当前 World04 有限定 HF 双审授权，变更外发路由须确认；非 R61 启动、训练或生产部署授权。  
**文档基线：** `main@5de5f81f1db1724419dc699c815ae4e042639b17`；接手时重新核验 HEAD。  
**状态：** `WORLD04_QUALITY_APPROVED1__SOURCE_ISOLATION_HOLD`；下一阶段 `KNOWN_SCOPE_FROZEN__CAPTURE_PREFLIGHT_PENDING`。

## 0. 2026-11-26 实际进展与现行下一步（覆盖下文旧采集状态）

- 已按 Owner 逐次批准完成四个世界的有限筛选，共 16 条原始回复，World04 冻结 2 条优先候选（另 1 条条件候选不扩入本轮）；未准入。Owner 已确认来源使用权，授权离线重建与本地复用。已有 Source Stage 在 Mac 实测 2/2，消息数 2、10，原始目标和在先正文保持；后续正文任务 System 定稿、排除无关技术字段（29 个技术 ID，另封面资源），盲审包 2/2，URL/邮箱/手机号/UUID 模式零命中。Owner 已明确人工检查盲审包并确认可外发信息范围。原始组件留证不改；正文监督与历史抽取/Compiler 一致，但不是完整生产组件输出合同，也不是实际发送 Prompt 重放；时间点完整性和 Provider 原始请求未证实。
- 本轮 World04 对 Base336、History32、R50 已知五世界、P2 八来源精确 ID 无重叠；Base336 375 版本及 P2 8 版本的四字段与姓名初筛均零命中，History32 版本级筛查本轮未完成。语义独立、完整保护集覆盖仍 HOLD；不读取 R50 密封正文，不重跑旧候选隔离或无限搜索历史全集。
- Owner 批准两条冻结候选 HF 双审与数据外发、不设费用上限，随后批准已验证新路由（DeepSeek-V4.1-Flash-1017 / Cloudflare，Kimi-K3.1-Pro / DeepInfra）。旧 4 次 HTTP 400 保留；新路由合成 2/2 PASS，正式 4/4 HTTP 200、有效 3/4（均 PASS、低于六维门槛及严重标记均零），完整双审 1、双 PASS 1、有效成对判定分歧 0。38005 tokens，报告费用 $0.105284028，无自动重试。剩余一份原始 PASS 声明因两处引文无精确来源（rule_fidelity、hard_fact_or_ban）保持 HOLD；9 项中 7 项匹配。未改原始回执，诊断新增模型调用 0。路由经验见 [资产索引](../REUSABLE_ASSET_INDEX.md)。
- Owner 随后明确确认唯一双 PASS 候选四项人工核查全部通过：原始回复质量、上下文适用性、无未来信息泄漏、双审证据可信度；记为 Owner 声明 `owner_quality_approved=true`、`context_is_coherent=true`、`context_no_future_leakage_reviewed=true`、`review_evidence_accepted=true`（仅该候选，私有绑定在 Owner 域落盘）。内容质量审核收口，不重新调用 Reviewer；另一候选保持 HOLD。本次声明不证明来源历史版本时间点、世界图或完整保护集覆盖，也不豁免隔离门禁。
- Owner 本机实际 SAFE：唯一双 PASS 候选的四项批准已写入私有 attestation，绑定两份原始评审回执，冻结输入/目标验证通过。现有 staged row 的 source_version_sha256、world_graph_sha256、world_component_id 均缺失；这是既有 Stage 未完成正式登记的预期状态，不是源码缺陷。有限来源核查实际确认原始来源包及所选目标包均绑定，locator、故事卡、原始消息和模型绑定存在，locator 含 version/created_at/updated_at、卡含 version；未验证历史时间点、语义独立及完整保护集覆盖。新增模型调用、数据库查询、原件修改均为0。不得将快照摘要或版本字段存在冒充历史版本/语义隔离证明。
- **阶段结论与下一步建议（非新增采集授权）**：World04 冻结为 1 条质量已批准但来源隔离 HOLD 的候选，另一条保留审核 HOLD；正式准入及训练准入均0。结束本批有限证据核查，不再补评、不重复搜索历史全集、不访问 R50 密封正文、不开发新 corpus 扩展、不提交 HF CPU Job。若 Owner 决定继续主线，优先在下一次采集之前明确来源版本时间点证据与可执行的保护集/世界组件审查范围；先复用现有 Source Stage、World Isolation、Quality-v1 合同，不创建新系统。前瞻采集可避免新增时间点缺口，但不能自动补齐既有完整保护集或证明语义隔离；无法满足现行门禁仍 HOLD。另行批准后才启动新采集；现有候选不因本次收口被删除或自动入训。GPU、训练、部署、晋升、R61 未授权。
- 本轮一次性 Mac 操作不提交仓库；已有 Source Stage/Quality-v1/Compiler 等优先复用，只有真实合格样本明确阻塞才做最小兼容实现。保持 `quality_v1_admitted=0`、`train_admitted=0`、`training_authorized=false`、`model_promoted=false`、`r61_started=false`，R60 NO_PROMOTE。

## 0A. 新来源独立实验体系：限定历史范围的准入政策（Owner 已批准）

Owner 在 v1.5 第 0A 节限定范围政策单独呈请后明确回复“批准”。本次决议接受未来全新原创来源在已知范围审查及新集合隔离实际通过后的剩余未知历史风险；不批准生产采集、模型调用、训练、部署或晋升。World04 及其他历史 HOLD 不追溯适用。

**已决议**：下列约束均满足时，不可恢复的历史全集缺口作为明确披露、事先接受的限定风险，不再单独构成新来源实验的绝对阻塞。完整历史全集仍未验证，不改变旧批次准入，不自动授予训练或模型晋升权限。政策批准与具体冻结范围证据的核验分开记录。

1. **先冻结范围，再新创作。** 截止点 T 为政策批准且已知历史保护集版本清单冻结完成的可记录时间（尚未设定，不倒填）。仅 T 后有真实创作证据的原创世界进入新批次；不得通过改名、重发、改写旧世界或使用旧 Teacher/Gold 构造“新来源”。不得回收 World04。保留来源权利、世界卡及实际生成时有效输入/目标、版本、时间和转换绑定。
2. **已知范围不得豁免。** 在采集前以既有有权元数据固定已知 Protected/Reserved/Held-out/Dev/Arbitration/Teacher、历史训练暴露范围，包含 Base336、History32、R50 已知五世界、P2/Gold48、E1/E4 等；逐来源记录权威版本、已知覆盖及未获证范围，不将已审 P2 的语义结论移用于新世界。不能获取必要已知清单、存在已知重叠或无法完成新世界语义审查则 HOLD。沿用冻结 R60 World Isolation 与既有元数据核验，不读 R50 密封正文、不重新全盘搜索。历史缺口 `r55_r57_other_dev`、`other_reserved_heldout`、`other_historical_training` 及其他未确认全集继续明确列出。
3. **隔离独立新集合。** 新世界源组件在生成前固定用途，所有会话、变体、衍生按同一组件归组；训练候选与 Validation/独立评估均用互不衍生的独立世界，不拆同世界。独立评估材料在首次训练前预留、冻结、私有隔离；不得用训练、选参或诊断中已曝光的材料冒充最终盲评。后发现重叠立即隔离并披露、复核受影响结果，不修改原始证据或静默换题。
4. **区分事实和政策。** `full_protected_universe_verified=false` 保持事实原值；只有新世界对明确冻结范围的真实审查支持时，才记录 `semantic_independence_within_scope` 及具体证据。未知历史全集风险的原则性专项批准已取得；实际冻结范围及缺口仍须私有记录、核验，不得将其写成完整隔离 PASS，或自动填补 Quality-v1 证据布尔值。历史 2026-11-20 Gold48 限定评估风险决定只作先例，不继承为训练风险批准。若已知范围前置不满足，或出现本次批准之外的新风险，停止新采集并保持 HOLD。
5. **前瞻采集优先复用 RolePlay。** 已实查 RolePlay `main@6cd4ccf5ebf9f44872e28bdec2c3a94b06c3d424` 相对 `a2c40eb7b01ba72a92c8d64b7d861f49ddaf3fac` ahead 59，两个完整树中 99 个留证相关文件 Blob 未变，V2 route 仍接线，但 Provider/Prompt/拒答和取消等主链路有变化，未做当前运行验收。先在获得范围批准后按现有运行清单核实部署与开关，复用指定单会话采集、Worker、受控导出及 `verify-bundle.mjs`。现有消费者只认限定出口比较并固定 HOLD；保留原 assessment，不冒充 CAPTURED、不删除 HOLD。若有可验证、独立的 source-bound derived training input 合同，可另行审查其完整适用输入、输出来源、时间及无未来信息，不把历史 wire 字节回放作为普遍必需条件；不得绕过 RolePlay 导出原有用途和 HOLD 约束。首个实际生成前必须确定所选路径可满足正式来源合同；若无法满足就停止，不先花费采集/评审费用。生产开关、会话范围、实际模型调用/费用及导出权限分别另行授权。
6. **质量和实验不变。** 六维 4/4/3/4/4/4、三严重标记、独立双审与原文证据、Owner 批准、隐私及版本绑定全部保留。首次仅验证一个新世界的一条真实目标，有余力且另获授权才扩展至 3–5 条；不把小试点当作足够训练量。新实验拟以固定 Qwen/Qwen3.8-27B Base 为共同起点、仅新获准入数据训练候选，使用独立新评估对照证明质量变化；不继承旧 Adapter/旧数据的未解决污染风险。训练设计、样本规模及 GPU/模型调用均另审。
7. **最小工程变更。** 当前 main Quality-v1 仍只接受 gold195/r58_round1，现有 `EVIDENCE`、review、split、hash 和 overlap 合同不能假造。只有政策明确获批、具体证据前置可执行且出现真实合格新候选时，审查最小新 corpus 及 scope 声明兼容方案（与旧 corpus 门禁隔离，保留旧回归测试、缺证及已知冲突 fail-closed）；不先写代码或建立新注册服务。现阶段准入及训练计数仍为0。

本节政策前置中的已知范围冻结及 T 已完成，实际回执和当前唯一下一步见第 0B 节。未获独立操作授权不启动 World05、不改生产、不新增脚本、不运行 HF Job。此前历史资产及实际限制见 [可复用资产索引](../REUSABLE_ASSET_INDEX.md)。

## 0B. 已知保护集真实冻结完成与前瞻采集前置（2026-11-27）

Owner-local SAFE：`KNOWN_SCOPE_FROZEN__CAPTURE_PREFLIGHT_PENDING`，原草案 221 Story（Base336 172/375 版本、History32 32/120 版本、R50 已知5、P2/Gold48 8/48题、E1–E4 4），7 份来源引用再验真，追加 Gold87/Gold108/R04/v0.1 Train/Validation/DEV20/R45 Train/Validation 8 个来源组均已覆盖、增量0、最终221。R57 历史目标回链回执已复核。T 为 Owner 实际冻结回执的 `2026-11-26T16:17:21.337667+00:00`，非文档提交时间。私有原件保留，Git 仅 SAFE 聚合。不再整理或扩大历史全集；`full_protected_universe_verified=false`、未知范围风险接受 true。新世界语义核查未完成，World04 不追溯适用；R50 sealed 未读，DB/模型调用0。

**现行下一步：** RolePlay `main@6cd4ccf5ebf9f44872e28bdec2c3a94b06c3d424` 未变。实际源码 `src/lib/generation-evidence/assessment.ts::assessPendingEvidence` 对所有 attempt 无条件加入 RELAY_EGRESS_UNKNOWN，仅返回 PARTIAL/UNVERIFIABLE 与 HOLD；消费者 `verify-bundle.mjs` 也固定 HOLD。故完整采集和比较成功本身仍不能产生原合同下的训练可用证据。不能先采集再解决认证，不绕过原用途限制。优先请 RolePlay 运行责任方使用现有 preproduction-checklist、audit-runtime、grant-control 合同，给出关闭态实际部署、身份/权限、Worker/网关、SQL 已登记与当前有效状态，以及是否已有可复用的最终出口证据路径；只有源合同明确可执行、真实新世界原创及已知范围语义隔离审核通过、单会话操作/模型/费用/导出独立获批后才采集一条。若现有可验证独立派生输入路径可满足 StoryForge 来源合同且不违反 RolePlay HOLD/用途限制，先说明现成证据与许可边界；否则 HOLD，提出真实最小缺件，不提前开发。现有生产运行态尚未实查；不启用服务来获得审计 PID，不自动重复 SQL 或部署。不启动 HF Job、训练、R61。

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

当前接手依据第 0 节保留 World04 冻结 HOLD，依据第 0B 节已完成冻结的回执转入既有 RolePlay 采集前置核查，不重开本批。后续新试点如另获批准，先确认已有材料；不得未经授权创建生产数据、启动模型请求、HF Job、付费 Judge、训练或晋升。

阶段交付：新源的版本/权利/用途与隔离证据、少量原始互动私有候选和 SAFE 回执；独立审核与编译仅在各前置成立时继续。有任何真实阻塞只报告缺件与下一项最小动作，不继续历史搜索或用假 PASS 补齐。首批目标、实际采集量、审核量均未发生时明确为0。

状态保持：`quality_v1_admitted=0`、`train_admitted=0`、`training_authorized=false`、`model_promoted=false`、`r61_started=false`，R60 `NO_PROMOTE`。最终独立评估设计、模型调用、GPU、训练、晋升各自另行授权；禁止利用已暴露 Gold48/E1/E4 做训练或调参。

新 Agent 入口：[接手提示词](../handoffs/STORYFORGE_NEW_SOURCE_QUALITY_NEXT_AGENT_20261126_CN.md)。
