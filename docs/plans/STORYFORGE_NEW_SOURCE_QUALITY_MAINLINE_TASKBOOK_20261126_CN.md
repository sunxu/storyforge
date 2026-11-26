# StoryForge — 新来源质量数据建设任务书

**版本：** v1.17（2026-11-27）  
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
