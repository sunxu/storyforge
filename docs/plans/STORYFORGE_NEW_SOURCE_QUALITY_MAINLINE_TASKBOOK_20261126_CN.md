# StoryForge — 新来源质量数据建设任务书

**版本：** v1.24（2026-11-27）  
**决议：** Owner 已批准将数据建设主线转向新采集、来源可控的高质量原始互动样本。  
**范围：** 新原创世界有限采集、审核、证据绑定；当前 World04 有限定 HF 双审授权，变更外发路由须确认；非 R61 启动、训练或生产部署授权。  
**文档基线：** `main@5de5f81f1db1724419dc699c815ae4e042639b17`；接手时重新核验 HEAD。  
**状态：** `WORLD04_QUALITY_APPROVED1__SOURCE_ISOLATION_HOLD`；下一阶段 `INDEPENDENT_SOURCE_BINDING_PREFLIGHT_HOLD`。

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

## 0C. RolePlay 最小核查报告与独立来源路径预检（2026-11-27）

Owner 转交 RolePlay 核查 SAFE：`REUSE_CONFIRMED__CAPTURE_PREFLIGHT_PENDING`。最新有记录生产版本 22c25fc6fc0a（11-26 12:16:37 双公网版本及 ready 复核），main 6cd4ccf5ebf9；本 Agent 复核两仓库 HEAD、RolePlay 固定发布文档及源码，未实时登录生产。报告称五份 evidence SQL 已由迁移登记接口回读；本 Agent 未独立重查登记/ACL/函数指纹。历史 Worker、网关、非 root 身份及 11-13 单会话 1 次真实调用/34551 字节对照 PASS 可复用，但原私有包未重验，最近记录关闭不等于当前关闭实证。禁止为审计 PID 启动服务、重复 SQL 或部署；19 份历史延期 SQL 和 Ledger 不纳入。

**路线选择：** 原 RolePlay export/assessment/verify-bundle 保持 PARTIAL/HOLD、用途限制与原接收人约束；不启动最终出口认证工程。StoryForge 优先独立合法来源的 source-bound derived training input，不从用途受限 HOLD 包直接派生训练数据，不宣称 actual-sent。实际适用输入的规则/人物/历史/时间/目标必须独立可证；使用权及权限尚需真实绑定。独立路径若可成立，不必为取得训练候选开启留证 Worker/Archive/Export 或申请 grant；是否使用现有留证作独立辅助证据依单独许可，不作默认必需工程。

**新增查重实证：** RolePlay 固定 main 6cd4ccf5 中 `scripts/export-top-v2-chat-context.mjs::contextQuery` 已有 READ ONLY 会话/故事/玩家设定/记忆与导演状态/有序消息（含 mutation_revision、created_at）查询，但入口默认排名批量采集，单会话三元组与前后快照绑定尚待核验，不运行默认入口；`scripts/export-v2-story-training-evidence.mjs` 已有当前卡、历史内容版本、审核快照、checkpoint 只读提取，不证明实际时间点；`src/app/api/stories/v2/[id]/versions/route.ts` 有认证后版本读取；`src/app/api/chat/v2/messages/route.ts` 的部分 GET 分支可能触发 stale streaming 修复，不能默认当严格零写只读审计入口。冻结 R60 `experiments/r58_quality/gold_source_context_stage.py::stage_source` 已验证目标 SHA、历史角色/完成态、System 绑定与 staged hash，但明确 temporal NOT_PROVEN、source_version_sha256 空；不冒充前瞻资格。已有 `test_gold_source_context_stage.py` 可复用。

**当前唯一下一步：** RolePlay 运行责任方完成关闭态实时回读（不启动服务）与一次纯合成独立来源绑定预检：使用已有查询/版本/目标读回合同和既有测试；先固定新原创世界的适用卡版本及规则、玩家设定、有效历史、状态和当前 User，再模拟目标持久化及 revision 读回；验证生成前快照与生成后目标的同一来源/会话/轮次、原文及摘要，检测版本变化、历史/规则遗漏、未来消息、目标替换、跨会话与摘要不符；缺证即 HOLD。优先选择静态规则、无额外记忆/组件或动态状态依赖的可控会话，若实际存在则完整保留而非删规则。只使用现有合成资产，不访问真实候选、不开采集、不调用模型。随后若证实可行，另行批准一世界一会话一目标、实际所需调用/数据权限，先完成新世界语义审查；不先采集再补证。当前未完成该预检、未核实实时关闭态，不批准新增实现或任何生产/训练动作。保留 221/T 与 World04 原决定。

## 0D. 独立来源绑定预检 HOLD 与最小补齐提案（2026-11-27）

Owner 转交 RolePlay SAFE `INDEPENDENT_SOURCE_BINDING_PREFLIGHT_HOLD`：既有 Source Stage 合成测试5/5通过（正常结构、异常角色、目标摘要、重复目标、System 摘要/权限/不覆盖）；七类端到端拒绝尚未实测，独立时间绑定、上下文完整性和目标 revision 均未验证。公网版本接口无法访问，当前生产实际身份、Worker/网关和 Capture/Archive/Export 未回读，无生产修改、SQL、模型调用、真实候选。修正第 0C 节最近发布记录口径：RolePlay main 6cd4ccf5 内另有 `.claude/docs/gemini-flash-retirement-20261126.md`，登记 11-26 18:18:46 UTC+8 实际部署 20412c0e86b9e4155113ef188bb5d2bb52539915，晚于 22c25fc6；仅历史部署记录，非当前实时状态。

**不扩大主线。** 独立来源绑定为唯一技术缺件；生产关闭态回读由运行责任方另行完成，不为读取 PID 启动服务，不将无 Worker 路径变成全站留证验收。不访问真实候选，不启用留证组件/Grant，不改变 RolePlay HOLD。221/T 与旧 HOLD 不变。

新增查重：冻结 R60 `scripts/r60_p2_gold48_source_component_bind_cpu.py` 及同名测试已有卡 revision、快照、组件、候选 prefix 的绑定参考，但用途明确仅内部评估/NO_TRAINING，不支持本次生成前后独立时间和原始目标证明；不能用其历史材料入训。旧 R02 `evaluations/v0.2/admission-audit-20261013/r02-point-in-time-cards/point_in_time_card_evidence_contract.md` 已指出时间顺序/摘要不足以证明来源。已查 GitHub PR44、R60 归档树，未找到完整前后快照验证器；**不能宣称全仓历史无现成实现**：Mac 本地 `backup/r60-new-generation-evidence-pilot-20261122@ca5ad674262158e9ad6ec747a3cbb8beae54f4bd` 的 `experiments/r58_quality/r60_new_generation_evidence_pilot.py` 与测试无法从 GitHub 获取（固定提交树请求422）；须先在 Owner Mac 只读核查这项已登记资产，不运行其生成入口、不披露内容/私有参数。无可复用实现才最小扩展。

**本节原待专项批准的工作（已获批，实际结果见0E）**：仅 StoryForge 本地、现有 Source Stage/历史 binder 基础上的前后绑定合同与必要薄验证器、合成测试。采用独立于候选自报摘要的可信预生成原件及生成后持久化回执：完整适用卡/规则/玩家/状态、历史消息 ID/revision/正文与顺序、当前 User、世界/会话/轮次、版本和水位，生成后读回同一 scope、前缀与卡未漂移、唯一新成功 Assistant 原始正文及 revision；留原始证据和派生转换绑定。初次仅固定简单新世界、无并发/编辑/分支/重生/动态依赖（若实际存在必须如实保留或 HOLD），不宣称 Provider actual-sent。完整性须对独立原件清单比对，规则适用性另需人工证据，不把 hash、时间排序或自报布尔值当独立证明。七项负例（版本错配、规则遗漏、整轮历史遗漏、未来信息、跨会话、目标替换、摘要错配）应覆盖攻击者重算摘要仍被独立原件拒绝的情形；合法正例通过仅代表技术验证，不代表真实来源、质量、隔离或训练通过。复用 canonical/hash/Source Stage；优先使用一次性私有 CLI 或最小独立纯函数及测试，不建新服务、不提前扩 corpus/Compiler，不改 RolePlay。Owner 后续已批准，实际查重及合成实现见0E。真实采集、外发、模型/HF Job、训练仍各自未授权。

## 0E. 旧 pilot 查重完成与本地薄绑定合成测试（2026-11-27）

Owner 已专项批准第0D节最小本地绑定任务，不包含真实采集、生产变更、模型/HF Job/训练。Mac 固定旧 pilot 已找到（254行、测试272行/20函数），Owner 上传两份源码；本 Agent 实际审查并在隔离环境执行原20函数参数化共27项，27/27 PASS。旧 `review_bundle` 验证请求/尝试/Provider 输出/转换/最终正文及 Shadow 内部一致性，版本摘要仅格式、缺独立 PRE/POST 原件和完整适用输入证明，全部资格 HOLD；保持旧文件原样，不复用该实际生成请求专用 schema 冒称独立来源认证。

确有缺件后，仅在本地隔离工作目录制作 188 行纯 Python 薄层 `independent_source_binding.py` 及合成测试、README（交付 ZIP，未提交仓库程序代码）。复用现有 Source Stage 接口，不复制采集服务或编译器。独立来源观察者分别保留 PRE/POST 原件和可信 pin；预先冻结适用 System、完整卡/版本、scope、有效历史及 planned User，目标持久化后回读同一 scope、相同原始前缀及唯一追加 User/Assistant（时间、revision、原文），状态漂移 fail-closed；候选 claim 即使重算正确摘要仍与独立原件比较。输出仅 Stage row + system + SAFE，不填证据/准入 flags。合成18/18 PASS（七类拒绝含重算摘要、首轮空历史、额外版本/历史/目标漂移等）；另与从冻结 R60 摘取的原始 stage_source/_history/canonical/sha 纯函数衔接1/1 PASS，**不是完整模块或真实数据验收**。Owner Mac 已实际完成冻结归档完整模块回归：首次收集因归档提取遗漏 `src/storyforge_dataset/__init__.py` 导致导入失败，非测试执行失败；补齐固定归档原件并检查三个模块加载位置后，返回 `FROZEN_MODULE_IMPORT_PASS`、`24 passed in 0.12s`（18+1+原5，无 skipped），临时目录清理完成输出。合成/完整模块回归阶段收口，不重跑旧 pilot 或重复新增功能；未改变原归档。

**仍 HOLD：** 真实独立来源取得及规范化字段的实际合同、真实时点与完整性、人工适用规则、生产实时关闭回执、原创世界/隔离/权利/质量均未证；本工具不能认证快照出处、发现原件本身遗漏或中间变化后复原。首个试点只允许可控简单路径；真实字段/动态状态如不符不得伪造或清空。RolePlay 原 PARTIAL/HOLD 保留。Owner Mac 完整冻结模块回归已完成。当前只需由 RolePlay 运行责任方提供关闭态实际只读回执及现有来源读取合同：确认能在指定 owner/story/session 范围内独立取得完整 PRE、POST 的真实字段（故事 revision 与完整卡、persona/runtime context、消息 ID/turn/revision/时间/状态/原文及 metadata），完整枚举而非截断分页，保留原件、独立 pin 与规范化记录；预生成固定 planned User 与人工审过的适用 System，成功后回读唯一追加 User/Assistant。若真实形态不符先报告真实最小缺件，不继续合成工程或伪造字段。无真实候选访问授权，不执行采集；运行回执及字段合同可用后才准备 T 后单一原创世界，实际生成另行批准。221/T、World04、准入0与训练未授权均不变。

## 0F. 完整模块回归完成（2026-11-27）

Owner 实际回执：`FROZEN_MODULE_IMPORT_PASS`，`24 passed in 0.12s`。状态 `INDEPENDENT_SOURCE_BINDING_LOCAL_REGRESSION_PASS__REAL_SOURCE_PREFLIGHT_PENDING`。此为合成数据和冻结模块加载验证，不是生产运行或真实来源认证。独立来源绑定技术试点不再增加功能；下一步只补第0E节真实来源读取合同与实际关闭态回执。原有221/T、PARTIAL/HOLD、真实采集禁止、质量/训练准入0、R60 NO_PROMOTE、R61未启动均不变。验证器仍为 Owner-local 交付，不提交代码或私有材料。

## 0G. 独立来源读取能力确认，技术准备收口（2026-11-27）

Owner 转交 RolePlay 最终核查结论：PRE/POST 所需数据库字段确认存在、既有只读权限已实际确认、接受 StoryForge 24/24 回执；不需要新增 RolePlay 代码、SQL 迁移、Worker、Archive、Export 或 Grant。现有能力原则上可支持首个受控原创会话。**本节优先于此前待确认来源字段合同的表述。** 本 Agent 接受转交结论，未独立重查实际数据库权限或逐字段查询原件；不得将原则可行性记为真实样本绑定通过。

状态 `INDEPENDENT_SOURCE_PATH_READY__PRODUCTION_OFF_RECEIPT_PENDING`。唯一未取得的运行前置回执为 RolePlay 生产关闭态实时回读，由有权限的运行责任方完成；既有版本发布记录不能替代实际状态。保持原 PARTIAL/HOLD，不启动服务、不扩大审计、不新增验证器或测试。获取真实关闭态回执后，准备 T 后作者自有私密原创故事、短历史、无额外面具及复杂记忆依赖的单会话，核对原创权利、冻结完整规则/版本、221已知范围语义隔离及用途划分，并取得单条真实互动的独立批准。实际 PRE/POST 原件及字段映射在受控试点中如实核验；不因字段存在/权限已确认而推断真实来源认证。若发现真实缺件才 HOLD 并报告，禁止预先建设外围工程。首次试点只验证一条原始目标，后续质量双审及 Owner 审阅通过后再考虑扩展；当前真实采集未授权、质量/训练准入0、训练未授权、R61未启动、R60 NO_PROMOTE。221/T 和既有 HOLD 不变。

## 0H. 技术预检 PASS，首个受控原创会话专项审批待定（2026-11-27）

Owner 转交 RolePlay 实际 SAFE：`INDEPENDENT_SOURCE_PREFLIGHT_PASS`。production_revision=20412c0e，production_web_roles_verified=3，web_capture_os_env_enabled=0，capture_control_enabled=false，worker/gateway/canary/acceptance_running=false，archive/export_enabled=false；readonly_source_fields_verified/readonly_permissions_verified=true，binding_synthetic_passed/total=24/24，additional_development_required=false，first_controlled_session_ready=true。原 PARTIAL/HOLD 保持；真实候选、模型调用、生产变更均0，collection_authorized/training_authorized=false。本 Agent 接受运行责任方实际回执，未重新登录生产或查 DB，不将 first_controlled_session_ready 解释为已有真实故事或已完成来源绑定。**本节取代0G及此前关闭态回执待取得的下一步。技术预检正式收口，不重复核查或开发。**

当前状态 `INDEPENDENT_SOURCE_PREFLIGHT_PASS__FIRST_ORIGINAL_SESSION_APPROVAL_PENDING`。下一步只准备首个 T 后全新原创私密世界，确认 Owner 自有会话与原创权利、221已知保护范围语义隔离及用途归属（不重开历史全集），冻结完整适用卡/规则及版本、短有效历史、当前 User、必要 persona/runtime context。初次专项审批严格限定一个世界、一个 Owner 自有会话、一次真实互动、一条未改写的原始 Assistant 目标；具体模型/路由、调用及数据用途需独立授权，不预填假身份或预算。生成前由独立只读路径保存 PRE 原件及 pin，生成后回读 POST 原件与唯一追加目标 revision，复用已有本地绑定器及 Source Stage。若真实字段或来源不符、规则/历史遗漏、出现并发修改/重生/额外目标等即 HOLD，不自动重试、不通过新生成补证。仅在真实绑定/合法性通过后安排质量双审和 Owner 审阅，进一步外发评审及训练另行授权。保留 RolePlay PARTIAL/HOLD、221/T、World04 原结论、R60 NO_PROMOTE、准入0、R61未启动；不启动 Worker/Archive/Export/Grant、不增加开发任务。当前尚未提供实际新故事及其隔离审核，不擅自生成或采集真实样本。

## 0I. 首个受控原创试点专项批准（2026-11-27）

Owner 明确批准第0H节的一世界、一Owner自有会话、一次真实互动、一原始 Assistant 目标限定试点。状态 `FIRST_ORIGINAL_SESSION_PILOT_APPROVED__WORLD_SOURCE_FREEZE_PENDING`。本节取代0H的审批待定表述：该范围的专项批准已取得，不重复征求同一批准；实际执行仍须先满足新世界来源、已知范围语义隔离和 PRE 冻结，并核对实际生成路由、费用及使用权边界。未取得具体世界/会话定位、真实创作证据、人工隔离审查及 PRE 原件前不得生成。授权不包括额外物理调用或重试、外发评审、批量扩展、HF Job、训练、部署或模型晋升。

当前执行：Owner 通过正常业务界面准备 T 后新创作的自有私密故事，记录实际创作方式（包括 AI 辅助如适用）、权利、版本及创建时间；不借用或改写旧来源。用途先定为训练候选世界（非正式准入），同组件不得跨 Validation/独立评估。复用已冻结221来源的限定语义隔离审核，保留未知全集风险；不读 R50 密封正文、不扩大历史审计。确定具体世界和会话后，通过已确认的只读路径冻结 PRE，核验完整规则、玩家设定、有效历史、当前 User 和生成所需状态；通过才执行一次获批互动，独立读取 POST 并复用本地绑定器及 Source Stage。无真实原件或异常即 HOLD，不自动重试。后续质量评审/外发授权单独处理。首个原创世界实际创建、隔离审查及真实 PRE/POST 均未完成；模型调用、真实候选和正式准入仍0。RolePlay 原 PARTIAL/HOLD、生产关闭态、221/T、World04、R60 NO_PROMOTE、R61 未启动不变，不新增工程。

## 0J. 已有原创世界例外获批及有限候选筛选（2026-11-27）

Owner 无法创建新故事，明确批准首个限定试点允许经过专项审核的已有原创故事（包括 T 前创建，接受其额外未知历史暴露风险）。本节仅调整本次试点的新世界创建时间前置，不追溯放行 World04 或旧 HOLD，不重设221保护清单/T，不扩展为所有旧故事的通用准入；T 后已有原创故事优先。已知保护范围真实隔离、合法训练用途权利、实际版本/完整上下文、新生成目标和质量门禁不变。不得将一次新生成当作新世界证明，或把未发现已知重叠写成全历史无暴露。

本 Agent 已用 Supabase 只读连接器实际执行2次查询：四张相关表字段目录及最近100个基础合格 V2 私密故事的有界聚合筛选（非系统、未删除、卡非空、有作者、无 published_as_id/first_public_approved_at）；其中31个具备作者本人简单会话（未删除/未归档/ready、无父会话/面具、total_turns<=6、三类摘要空），T后4个，其中2个同时有简单会话，T前有简单会话29个，100个均有内容 revision。仅输出聚合，不读取故事或聊天正文、不返回候选身份/ID、不读取R50正文；私密与无上述公开记录不代表从未公开，作者自有会话不等于 Owner 账号或训练权利。该100条限定结果不是全库计数，尚未与221清单逐一比对。未完成真实候选选择或 PRE。

状态 `EXISTING_ORIGINAL_WORLD_EXCEPTION_APPROVED__OWNER_SCOPE_PENDING`。下一步由 Owner 本机/RolePlay 运行责任方确认获授权的具体作者/会话身份，在该范围内优先T后、必要时T前，私有比对221清单及可用来源版本，确认原创、无已知训练/评估暴露及训练使用权；只选一个。不得读取无权第三方私密故事、推断Owner账号、扩大热门采集。确有具体合法对象后做语义隔离和 PRE，执行已批准一次互动、POST绑定；不再重复申请同一试点或创建时间例外授权，不新增代码或重复留证预检。当前真实目标0、模型调用0、数据库写入0、准入0、训练未授权、R61未启动，PARTIAL/HOLD不变。

## 0K. 既有全平台内容权利声明及公开故事限定名单（2026-11-27）

Owner 明确纠正：此前已授权平台所有内容的使用权限，不再重复请求。登记总体权利声明 OWNER_ATTESTED，取消首个试点必须由 Owner 本人创作或逐一征求相同内容权限的限制；不等同于实际账号身份、来源真实性、具体故事原创声明的真实性或质量/隔离 PASS，不改变一次新互动与可控会话、外发/训练执行及隐私边界。仍不可冒充他人会话或身份，不扩大为全量聊天扫描。

本 Agent 实际新增3次 Supabase 只读查询：T 后满足指定公开投影条件故事0；最近50个公开 V2 有版本故事中原始来源分类 original 42、ai_assisted 4、dice_cocreate 4，基本卡组件均存在。选择最新3个 original 且有基本卡组件的公开故事作为有限元数据 shortlist（均 T 前，既有第0J节例外已获批准，play_count=0 仅计数器，不证明无历史暴露）。公开故事便于 Owner 使用自己的会话；不读取私人聊天或尝试操控作者会话。原始公开定位字段仅放 Owner-local 交付 JSON，不入 Git；未读故事完整正文、未核实221重叠/衍生、未选定具体目标。三候选不是正式准入。

状态 `OWNER_ATTESTED__PUBLIC_ORIGINAL_SHORTLIST3__ISOLATION_PENDING`。下一步本地用已有冻结221清单核对 shortlist 精确ID重叠（不重建清单），随后从不重叠者择一个进行限定语义隔离和实际完整卡版本/适用规则核对；不得把精确ID不重叠、数据库 original 标记或 play_count=0 当语义隔离证明。确认后按已批一次受控新互动冻结PRE、生成、POST绑定；无需再次请求平台内容权限、创建时间例外或同一试点批准。不新增程序/工程或重复技术预检。正式准入0、模型调用0、写库0、训练未授权，RolePlay PARTIAL/HOLD 保持。

## 0L. C1 语义审核材料就绪，统一本机 DSN（2026-11-27）

Owner 本机实际 SAFE `EXACT_ID_SCREEN_COMPLETED`：冻结221个保护 Story ID，C1/C2/C3三个公开候选均无精确ID重叠。Agent 随后实际执行3次限定公开卡结构/组件查询，C1故事卡最精简、单结构化角色、无自定义标签页、记忆关闭，优先 C1，C2/C3暂留备选；三者均有手机、状态等组件，不宣称无动态依赖或额外物理调用。C1不可省略实际适用组件及规则。

Owner Mac 实际 SAFE `C1_SEMANTIC_REVIEW_READY`：保护元数据恢复221/221、缺失0、特征名称命中0、候选公开 revision验证true、私有文件创建true、完成2次只读查询，模型调用0、准入0、语义独立验证false。私有材料 `~/.local/share/storyforge/r60/private/C1_SEMANTIC_REVIEW_PRIVATE.json` 留在Owner本机，不上传Git或聊天。元数据是当前标题/公开人物检索文本/版本等，不代表221个历史版本全文或语义覆盖；零名称命中不能替代人工限定语义审核。Agent未实际读取此私有文件，不声称语义审查已完成。下一步直接由Owner对照现有冻结来源元数据和C1卡审查核心设定、人物关系、情节/开场及衍生线索，记录实审范围、依据和限制；不能判断则HOLD，不自动通过、不重复相同查询或重建清单。通过才准备Owner可控新会话与PRE，核实实际组件依赖及物理调用范围再执行已批准单互动。仍不读R50密封正文、不新增工程、不再次征求已获授权的内容使用权或试点批准。

**统一数据库连接规范（Owner明确要求）：** 后续Mac命令默认且直接读取 `STORYFORGE_SUPABASE_DSN`，不重新要求输入凭据；复用固定归档 `r60_readonly_db.fetch_dict_rows` 的精确reader角色、REPEATABLE READ READ ONLY、row_security与超时检查；旧代码硬编码其他环境变量时只在命令内作兼容映射，不修改原模块，不输出DSN。不将本轮初次KeyError归为数据库权限失败：改用现有DSN后实际成功。当前状态 `C1_SEMANTIC_REVIEW_READY__HUMAN_DECISION_PENDING`，真实目标0，准入0，训练未授权，PARTIAL/HOLD及221/T不变。

## 0M. AI 来源适用性筛选与 D8 限定元数据语义审查（2026-11-27）

Owner 要求由 AI 直接审核并遵循最小化/最短路径。Agent 已审核上传的 C1 完整故事卡，发现内部规则/玩家自主权/安全及非剧情联系信息风险，排除本次试点，保留原隔离HOLD；C2、C3公开卡实审分别存在复杂关系与自主权风险、机械超1500汉字与强制好感递增/动态系统规则，均不选用本轮，不补旧证据。仅在原最近50公开/42原创池内有界追加8个替代候选，详查其中3个，选择 D8（公开revision=0，original标记，T前已批准例外）。D8世界、人物动机、剧情规则具备首轮质量测试潜力，无机械长度要求或强制好感度增长；固定道侣关系与温柔路线是实际卡规则，角色已有作者设定记忆，手机/状态/commands等组件开启，不假定无动态依赖、额外调用或真实状态变化。实际完整公开卡结构已回读，未修改，不自动填Quality-v1判定。

复用已上传C1审核包内的同一221冻结范围，D8精确ID无重叠、原有8项特征词均0；追加一次限定只读元数据查询，使用当前作者/公开标题、人物搜索文本、简介、分类和标签（不读受保护卡完整正文、聊天或R50密封正文）。实际恢复221/221；人物检索220、简介132、两者均有131、两者均无0；具体特征命中0，较强主题筛选3条，Agent比较三条已有元数据，未识别同一人物/设定或直接衍生证据。决定 `AI_METADATA_SCOPE_NO_IDENTIFIED_DERIVATION__PRE_PENDING`：允许 D8 进入 PRE 准备的限定元数据审查意见，仅覆盖现有字段与已知冻结范围，不等价于逐一历史卡版本全文比较、全面无污染或正式世界图/Quality-v1准入。未知全集风险和历史版本限制明确保留；后发现重叠立即HOLD。不得称为独立双审或 Owner 质量批准。原件及定位不入Git。已知范围不重开，C1-C3不再补证，不重复筛选。

下一步唯一实际操作：Owner 使用自己的会话在业务界面打开 D8（定位和拟定User仅私有JSON交付），暂不发送User；由RolePlay现有只读路径取得独立PRE，核验实际公开版本、选定开场、完整规则、persona/状态/历史和拟定User，确认实际模型调用边界。原始卡含作者记忆及动态组件，现有binder对任意source漂移HOLD；不擅自清空或修改真实状态。PRE未冻结、真实会话未绑定、调用边界未核实前不生成；满足才执行已批准的一次互动、POST和既有绑定器。无新代码、无重跑预检、无额外授权请求、无自动重试；训练/外发评审未授权，真实目标0、准入0、R61未启动、R60 NO_PROMOTE、RolePlay PARTIAL/HOLD不变。Mac默认STORYFORGE_SUPABASE_DSN。

## 0N. 已有真实数据优先，有限历史来源筛选收口（2026-11-27）

Owner 明确要求先复用已有数据，并授权 Agent 通过 Supabase 只读插件进行实际有限筛选；暂停 D8 新互动与离线 Teacher 新生成，取代0M待打开会话/PRE的动作。不需要 Owner 打开故事、创建新会话或输入DSN，不改生产行为，不追加采集/留证/生成工程。平台使用权既有 OWNER_ATTESTED 不重复征求。已有未准入 HOLD 不自动放行，Gold48/E1/E4仍限评估，R50密封正文不读，221/T不重开。原实际适用输入、目标、版本与时间独立可证门禁保留；source-bound 派生输入不强制 actual-sent 字节，但不可伪称历史原始请求。

实际复用上传的221个冻结ID，排除C1-C3，按创建时间选最近50个公开原创非系统有版本故事，每世界最多3个短（2–10轮）ready非分支未归档会话，得到98会话/38世界，89个至少2 User/2已完成非空Assistant且状态检查无失败，80个公开版本更新时间早于/等于首消息。D8总会话28，其中2个至少两轮且状态完整，1个短ready非分支未归档。初次以revision>0作为编辑判据得0，实际Assistant正常修订非0，随后改为显式编辑标记（非未编辑证明）。

89会话进一步只读聚合：生成目标前 story_content_versions 65、story_admin_versions 0、同公开revision审核快照86、Ledger存在89、至少一类上述快照+Ledger 89、无显式编辑标记/面具/摘要且版本时间符合64；历史留证Manifest及live绑定Manifest均0。存在记录不等于完整/目标绑定，实际集合非全库普查，未获取留证对象或用途受限包。D8仅一个短会话实审4条正文（2轮），原始Assistant中文表达自然但未显示明显独立推进优势，非正式质量评分。当前公开revision时间早于消息，但生成目标前审核快照1、精确公开卡+hash匹配0，归档/Admin版本0，历史Manifest0；Ledger事件8、前缀目标边界后事件0、目标insert标记0、前序Assistant revision3/update_after2，依现有PR10 message_ledger重建revision检查预期HOLD，未在Mac执行正式恢复，不补证。当前persona不能证明历史适用性。

同一有限选择条件加非空消息检查后62个简单候选，历史卡要求首消息前的归档同revision/卡JSON或审核同revision/卡JSON/hash精确匹配，Ledger要求所有目标及前缀当前revision计数与update_after相同且有目标业务标记；两项单独及交集均0。这是保守SQL筛选而非正式恢复模块对每条执行或全库不可恢复证明；无精确匹配也可能反映投影/稀疏Ledger结构，不能凭此定性全部历史源不真实。已修正一次uuid/text比较错误。未产生或输出私有身份/对话正文到Git，不写库、不调用生成模型或付费Judge、不开发、不提交HF Job。

状态 `EXISTING_DATA_BOUNDED_SCREEN_HOLD__REUSE_VERIFIED_ARTIFACTS_FIRST`。停止对这62/89条逐一补证、停止 D8 新生成准备；下一步仅检查既有合法、未被保护用途冻结、具有真实生成输入/输出及来源证据的 Teacher/候选私有资产清单，先看已有索引/manifest、不读受保护正文；无合格对象即报告缺口，不新增全库历史审计、付费生成或工程。历史恢复复用PR10固定提交（实际已重读源码与旧R02合同），但不重写恢复器、不将零原始请求证据视为所有派生输入永久禁止。若需改变来源合同或开展新生成，明确另行决策，不偷偷降门禁；实际正式准入仍0、训练未授权、R60 NO_PROMOTE、R61未启动、RolePlay PARTIAL/HOLD不变。统一STORYFORGE_SUPABASE_DSN仅在确需Owner本机时使用，当前优先连接器。

## 0O. 既有 Teacher 资产索引核查收口与来源政策决策（2026-11-27）

本轮仅核对 PR44 资产索引、冻结 R60 完整目录树、main 基线完整树、Teacher 分支名称搜索、R58 Teacher policy、R57 SAFE inventory、R60 Real1000/Common2/Gold48 权威历史文档及可获得的既有历史回执索引。未读保护集正文、未进入 Owner 私有磁盘/HF Bucket、未重查 Supabase 会话。冻结树有 Teacher 政策而未发现合格独立 Teacher 数据清单；main 基线无 Teacher/distill 命名文件、分支搜索无 Teacher 名称命中（命名/索引缺失并非全存储不存在证明）。历史记录中审核输入、裁决、CPU预览、旧模型评估输出、P2/Base336训练资产不等于 teacher_generated/teacher_rewrite。Gold195/历史训练/Gold48/E1/E4保持原用途，Real1000、Common2（独立质量PASS2、CPU验证2）、World04（质量批准1）均不得因本次索引核查而解除各自历史HOLD。未找到可直接准入、非保护用途且有真实输入输出和来源证据的现成Teacher产物；不宣称全量私有存储查无数据。R58 policy要求 teacher_model、teacher_recipe_sha256、parent_target_sha256、输入/输出摘要和Reviewer证据；main Quality-v1当前仅original_gold且仍要求真实source_version_verified、context_is_coherent、context_no_future_leakage_reviewed及质量/隔离等，Teacher政策文件不代表当前编译器已经支持Teacher准入。

状态 `EXISTING_ASSET_INDEX_REVIEW_CLOSED__NO_VERIFIED_REUSABLE_TEACHER__SOURCE_POLICY_DECISION_PENDING`。不再反复盘点、补证或开发。建议下一步由Owner明确是否允许对一个未纳入保护/旧HOLD的已有真实回复，基于可信原始历史与固定来源卡构造明确标注的离线衍生任务，审核适用规则、时间与无未来泄漏、原始目标绑定及世界隔离；不是历史actual-sent复刻，不以当前卡回填过去，不降低六维质量、严重标记、独立双审、隐私或隔离，不伪造source_version_verified。此建议是待决的来源验收口径，不表示已经批准变更0D-0M的独立真实时点证据要求；如不能证明所构造任务的可信上下文，保持HOLD。若坚持原严格来源时点合同且无已有合格产物，唯一合理替代为另批一次最小新生成（仍未授权），不得默认启动。0N的零交集仅保守SQL初筛；不能把当前卡精确相等/所有Ledger计数当成一切离线来源的普遍必要条件。此次仅文档登记，不新造数据、不更改程序或准入、无模型/API推理或HF Job、无数据库写入；R60 NO_PROMOTE、R61未启动、training_authorized=false、quality_v1_admitted=0不变。 

## 0P. Owner批准限定历史衍生输入方案；新批候选适用性筛选（2026-11-27）

Owner 对0O节限定方案明确回复“批准”。允许一个非已知保护、非旧HOLD的新候选使用既有真实历史回复、可信历史卡与原始消息构建明示的离线衍生任务，不强制复刻历史生产请求，不以当前卡倒填历史、不捏造适用规则/状态，不降低来源版本、时间/无未来泄漏、语义隔离、隐私、六维独立双审及Owner质量批准门禁。新生成暂停，旧HOLD不追溯放行，221/T不重开，不访问R50密封正文。不是训练或外发评审授权，不改Quality-v1程序。

本轮通过Supabase只读插件，复用同一221冻结ID，排除C1-C3/D8，优先T后来源及较旧排名71–110的新公开原创池（非上一轮最近50筛查范围的有意复用；排名随实时数据变化，不声称对前次98会话完成逐条集合差证明）。限定40故事、优先作者自有会话、2–12轮、非分支ready未归档；实际10作者会话、8至少两轮完成状态且无显式编辑标记、7有首消息前故事审核快照且无面具/摘要的简单候选（5个世界）。初次附加无历史persona等较严格筛查返回0，之后按已批准离线任务方案检查快照及内容适用性，不以当前hash相等或无原始请求作为普遍必要条件。7个候选中存在强制超长/自主权风险/不适宜规则，包含一个T后创建的世界，均不进入本次试点；最后一候选实查历史revision1卡，6条消息结构，历史persona记录2、实际适用性未证、动态组件及不适宜的自定义内容要求，不擅自删除适用规则；未读取此次候选对话正文，不进行正式质量评分。历史版本时间/消息结构检查不是已证真实完整上下文；本次未构造训练样本、未验证语义隔离（精确ID已排除已知范围），不宣称方案实证成功。无私有标识/原文入Git。

状态 `DERIVED_CONTEXT_POLICY_APPROVED__AUTHOR_SESSION_SCREEN_NO_SUITABLE_SOURCE`。当前仅完成新政策登记与有限适用性筛选，正式准入0；不重复该批筛查，不回到历史留证审计、不为排除卡补证、不开发新工具。若继续既有数据主线，下一次发现应先按故事内容适用性及既有明确规则筛选，再以真实多轮对话数量/可见推进情节选择少量已有回复，只有合适才获取可信历史版本和原始历史并进入既有Source Stage；不以卡长度/回复长度硬筛。保留作者会话优先及既有权限范围；不扩大至未经许可私密对话，不生成新回复。未独立证实全平台不存在合格历史数据。R60 NO_PROMOTE、R61未启动、training_authorized=false、quality_v1_admitted=0不变。

## 0Q. 真实回复质量优先的有限筛选收口（2026-11-27）

Owner继续要求最小化与最短主线。按0P已批准的已有真实历史衍生输入方案，仅Supabase只读查询，排除冻结221个ID及已知此前候选，不读R50密封正文、不打开生产会话、不调用新生成或付费Judge、不开发。以剧情/冒险/悬疑/权谋/成长等题材提示词作发现用（不是文学质量或正式准入门槛）。第一批限定120公开原创故事，58简单组件，取规则初筛20条；后续同样120上限的有界查询排除已实审的一世界，加强规则与作者会话筛选，38规则初筛、11个有短作者会话故事进入元数据shortlist。实时池可变化、两次结果不相加为独立240世界，不宣称全库筛查或实际全语义隔离。作者会话优先，未扩到无授权私密对话。

实际查看3个不同故事作者会话的早期完整消息结构和14条原始Assistant回复（6/4/4轮，均非新生成），对照相应历史故事卡的适用规则，非独立双审、非正式评分、不将其计入Quality-v1候选。职业成长故事：连续相似情绪/动作，职业目标依赖玩家提醒，未见足够独立剧情推进，不选。宫廷复仇故事：反复压制与代写玩家行为状态，非本次目标，不选。宫廷剧情模拟：观察到独立NPC、多线剧情与事件推进，优先检查第三轮场外叙事目标；此前历史前缀也存在代写玩家状态。对应历史卡revision3、6条前缀及目标均completed、显式编辑标记0、该窗口内版本/审核快照变更0；不将这些事实自动解释为完整来源。该目标关键身份/关系与场景事实在历史卡/可见前缀中未充分确立；只读补查完整历史卡特征词及实际当前绑定时间，当前故事persona绑定1、生成首消息前及目标前同时满足绑定和persona时间条件均0，不能证明历史适用persona。历史卡有部分人物但缺关键玩家及亲属/伴侣身份特征，不声称虚构或与历史persona冲突已证明。状态HOLD、不继续逐案追补证据、不删规则、不改写目标。观察到较强推进不等于其全部六维达标。

本批状态 `CONTENT_FIRST_SCREEN_COMPLETE__NPC_ADVANCE_SIGNAL_FOUND__SOURCE_HOLD`，正式候选/准入0；保留真实审阅的定性结论。不得回到宽泛留证盘点或在同一批重复选样。后续若继续已有数据发现，仅作有界高潜力源的内容/质量选择（优先能从卡和可见对话直接确定角色、规则、情节的历史样本，避免依赖不可恢复persona；以实际回复而非题材标签或固定长度判质），若没有合适候选即结束本批、报告缺口，另由Owner决策是否调整数据获得方式；不自动启动新生成。原R60 NO_PROMOTE、R61未启动、training_authorized=false、quality_v1_admitted=0、RolePlay PARTIAL/HOLD及221/T保持不变。无新增代码、无库写入、无正式双审/训练输入构造或HF Job；Git仅SAFE聚合与结论。

## 0R. 限定既有数据发现收口；不再循环低命中选样（2026-11-27）

Owner继续要求最小化/最短主线。复用0P批准的历史衍生输入口径及冻结221 ID，排除已知不选来源，本轮按相同题材提示词查询较旧排名121–220的100个公开原创故事，规则/组件粗筛47、短作者会话14、前几轮完成且首消息前无persona记录的9，取前6元数据；实时排名与上一批不保证完全不交叉，不声称累计独立全库覆盖。实际仅审阅4个作者会话共14个原始Assistant（6/3/3/2轮），并检查相应来源卡。奇幻江湖：历史rev1、无历史persona记录、前6消息无显式编辑标记，但实际回复反复复述玩家动作/心理、与卡明确规则冲突，不选用。宫廷群像：历史rev0，角色区分和对话可见，但反复代写玩家感受，且历史卡存在开启自定义组件，不选用。都市灵异：回复有独立事件与角色行动，实际目标前历史卡变化（版本0–3与后续档案的世界/角色/导演等字段并非相等），无首消息前归档快照，玩家身份未由卡确认，历史角色设定存在不适宜内容，不选用。悬疑博弈：历史rev1、2轮均completed、无显式编辑标记、无历史persona记录，NPC保留玩家选择但推进有限，开场称谓与角色卡名称不一致且未证实别名关系，HOLD。以上仅AI初筛，非正式双审或正式拒绝；没有来源完整性/语义隔离/质量准入PASS，不修改原回复、不回填历史、不删除适用规则。

本批状态 `BOUNDED_EXISTING_SOURCE_DISCOVERY_CLOSED__NO_ADMITTED_SAMPLE`。连续有限发现轮次未产出正式可准入候选；当前建议结束按时间排名/题材逐卡反复抽查，不为本轮候选追加历史取证，不继续自动扩大同类SQL查询。下一步待产品级选择：若有明确不同、已具备优质回复信号且可合法访问的现成来源，则只核查该来源；否则建议Owner决定是否允许最小离线Teacher新生成试点（之前暂停，未获新生成/外发评审/训练授权），先核对现有编译/准入是否支持对应源类型，不预先开发。保持0P衍生方案可用于后续合格历史数据，不因本批失败而撤销或降低门禁。未证明全平台无合格历史数据、未访问Owner私有存储、未完成实际衍生样本验收。数据库写入0、代码新增0、新生成0、付费Judge0、正式准入0；R60 NO_PROMOTE、R61未启动、training_authorized=false、RolePlay PARTIAL/HOLD、221/T不变，禁止访问R50密封正文。Git仅SAFE聚合。

## 0S. Owner明确暂不考虑离线生成；既有显式认可来源核查收口（2026-11-27）

Owner明确“按建议推进，暂不考虑离线生成”。继续既有真实数据路线，不启动Teacher、不预先扩编译器、不创建新互动，不重复排名/题材抽查。仅检查与此前不同的明确用户认可信号，通过Supabase只读插件核查已有schema，发现 `chat_reply_bookmarks` 带source_message_id、session/story/user/turn及收藏内容，适合作为真实回复的定向发现信号而非正式质量标签。实际以冻结221 ID及此前不选来源排除、公开原创V2作者自有会话为边界，最多500收藏的限定查询结果0；随后最近最多1000收藏聚合可见1，公开原创作者自收藏1、有源指针1；再以221名单进行精确聚合确认唯一记录保护重叠1，直接排除，不读其正文、不取其私有标识、不复用作新增训练。另查 `story_ratings` 最近最多1000条非空文字评价，实际可见0；正向叙事质量关键词命中0，有作者会话的匹配世界0。故事点赞/收藏/评分不是回复级质量证明，不以热度或付费/长会话替代六维实审。上述为插件可见范围的有界事实，不证明所有存储或未来数据均不存在合格来源。

状态 `EXISTING_EXPLICIT_QUALITY_SIGNAL_SCREEN_CLOSED__WAITING_FOR_CURATED_SOURCE`。停止自动扩大历史普通回复筛查、停止已知保护/旧HOLD追证；仅在出现明确不同的现成合法高质量原始对话来源（Owner已有精选清单/私有保存包/可定位会话等）时，直接按0P口径核查原文、可信历史上下文、隔离与六维质量，不重新盘点资产索引、不再次申请已有权利。暂无此类源时保持数据阶段HOLD，不用新增工程代替数据缺口。离线生成暂不考虑，旧生成授权不得借用；无正文读取、库写入、代码新增、生成/付费Judge、训练输入构造或正式准入。R60 NO_PROMOTE、R61未启动、training_authorized=false、quality_v1_admitted=0，221/T及RolePlay PARTIAL/HOLD保持不变，不读R50密封正文。Git仅SAFE聚合。

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
