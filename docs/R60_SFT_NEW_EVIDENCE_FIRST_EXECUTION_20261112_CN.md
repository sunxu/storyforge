# StoryForge R60 — 新留证数据优先的SFT主线执行任务书（2026-11-12）

## 2026-11-12 最新Owner裁决：Real1000质量优先，撤销按11月10日后数据日期优先（本节覆盖以下旧优先级）

已确认：RolePlay在11月10日后生成的普通数据**未证明质量或真实生成输入证据优于已有Real1000**；上线留证代码不等于启用真实留证，六张留证表当前无记录。Owner不具备生产服务器权限，本轮不得继续推动无权限的生产环境留证/真实外连/部署，也没有必要仅以日期重新粗筛新数据。**权威主线改为：[R60 Real1000质量优先最终执行决策](R60_REAL1000_QUALITY_FIRST_DECISION_20261112_CN.md)。** 当前任务顺序是：Real1000冻结数据的六维质量精筛→跨故事新40条私有质量审核候选准备→源绑定训练上下文及CPU tokenizer/collator→完整R50隔离→Owner明确训练准入/另行GPU审批。两条Common2独立文学PASS与历史103/243条恢复继续有效，但不等于已还原原生成Prompt或正式可训练。

之前本文中“新留证数据优先”、“下一步核对生产Worker”、“优先获取11月10日后数据”的条款仅作为历史讨论保留，**不再构成当前指令**。今后只有出现真实请求完整留证且获准独立验证的新数据，才应重新比较来源价值与质量。当前`DEFERRED_NO_PRODUCTION_ACCESS`、`quality_v1_admitted=0`、`train_admitted=0`、`gpu_started=false`。


## 十、2026-11-12 主线再次校准：当前无RolePlay生产权限，停止等待真实采集验收

Owner已明确**当前没有RolePlay生产环境权限**。因此此前将`ACTIVE_DEPLOY_SHA/WORKER_STATUS/CAPTURE_SWITCH`列为“下一步唯一优先工作”的安排作废，改记`DEFERRED_NO_PRODUCTION_ACCESS`。后续没有生产权限时，**不得要求Owner先取得服务器权限才能继续StoryForge训练数据整理**。P0A离线合成合同已PASS；P0B为独立有授权才能进行的未来工作，不占当前主线关键路径。即使已部署留证SQL，6张相关表当前均0条，不能用未来采集来代替眼下可用历史数据。

**现在的执行优先级（覆盖本文件前面的P0A→P0B→P1顺序）：**

1. **MAIN-0：真实历史数据质量与SFT输入设计**。以现有Real1000冻结候选为基础，复用Pilot20质量审核、Common2独立PASS及Supabase恢复的103+243条持久化历史。明确两种训练输入策略：`SOURCE_BOUND_DERIVED_CONTEXT`（源历史可核对，System/窗口为当下实验构造）和未来的`CAPTURED_EFFECTIVE_REQUEST`（确有真实请求字节/来源）；两者分别标记，绝不混称原始请求。
2. **MAIN-1：CPU技术筛选/上下文窗口方案**。先用本仓库`experiments/r58_quality/r60_real1000_history_window_cpu.py`对两条已经恢复的真实样本进行6/12/24/48条窗口**消息数与字符数**诊断，验证尾部三消息ID保持及角色顺序，输出SAFE聚合统计。**该脚本不运行Qwen tokenizer、不验证实际发送System、不生成训练样本，也不代表模型可在预算内训练**。窗口必须考虑从user起始、历史跨度与剧情连续性，不能无条件选最短窗口。
3. **MAIN-2：扩大到1000条可审核候选**。已有冻结技术合规1000条不能自动算优质训练集。质量筛选按既定六维文学Rubric；先评估Pilot20审查分歧的来源，再分故事抽取覆盖不同剧情与角色的候选，不机械只取模型一致PASS。真实恢复上下文可按必要范围渐进读取，不要求恢复每条全部历史、更不改冻结数据。
4. **MAIN-3：证据隔离与CPU训练格式验收**。完整核对R50保护集（已知五个story零重叠只是部分证据）、去重/故事分割、训练监督只落最后的assistant目标、固定Qwen tokenizer与chat template后CPU真实长度/Collator验证，形成可追踪的train/val/test候选，最后才由Owner决定GPU。
5. **DEFERRED：RolePlay生产留证上线与新来源数据**。保持P0B单独批准门禁；未来有权访问且有完好留证新数据时，再将其纳入优先候选池，不阻塞MAIN-0至MAIN-3。

**立即可执行的Owner Mac只读CPU步骤（与既有工作树无冲突，固定最新CI通过提交后运行）：**

```bash
set -euo pipefail
cd "$HOME/workspace/storyforge-r60-4router-review"
python3 -m pytest -q tests/test_r60_real1000_history_window_cpu.py
BASE="$HOME/.local/share/storyforge/r60/private"
python3 experiments/r58_quality/r60_real1000_history_window_cpu.py \
  --recovery-dir "$BASE/r60-real1000-qd20-common2-supabase-recovery-v1"
```

预期回执`SOURCE_BOUND_PERSISTED_HISTORY_WINDOWS_ASSESSED__TRAIN_HOLD`，仅包含2条样本不同窗口的汇总消息数、字符数与角色起始数量。该回执无法判断SFT质量，也不能推导实际历史生成Prompt、真正token数、System/世界组件或全部R50隔离。

**主线状态：`REAL1000_SFT_QUALITY_AND_CONTEXT_FIRST__ROLEPLAY_PRODUCTION_DEFERRED__TRAIN_0`。** 保留原始Real1000、历史审计、Owner私有恢复文件、冻结Rubric与训练门禁全部不变。禁止直接训练、自动GPU、修改源数据或生产。后续若AI质量评审需要模型调用，应保留独立执行授权与隐私保护，不在本CPU诊断里触发。


## 九、2026-11-12 P0B先决条件数据库核验已完成，接下来优先核对运行态

已执行并成功复核独立可重复**只读SQL**：`experiments/r58_quality/r60_p0b_roleplay_capture_readiness_readonly.sql`，具体结果见[P0B联验前置清单](R60_P0B_ROLEPLAY_CAPTURE_ACCEPTANCE_GATES_20261112_CN.md)。六张留证相关表均存在、启用RLS，anon/authenticated无表级SELECT，六表记录数全部为0；五份基础生成证据迁移在迁移历史中各登记一次。此次操作不修改数据库，不含原始请求或用户ID。**这是数据库结构现况验证，不是完整生产SQL/权限安全验收，不能证明Worker已运行或抓取开启。**

接下来不应再反复执行相同离线合成测试或对空留证表尝试P1训练提取。P0A离线验证PASS；P0B拆为已完成的**DB_EXISTENCE/BASE_ACL/MIGRATION_REGISTRY**只读子门禁和未完成的**ACTIVE_DEPLOY_SHA/WORKER_INSTALL_AND_STATUS/CAPTURE_SWITCH/GATEWAY_TLS/KEY_STORAGE/PERFORMANCE_BUDGET/INDEPENDENT_WITNESS**。请RolePlay生产Owner在受控环境提供SAFE只读状态、其来源及部署时刻证据，不能由StoryForge连接器猜测生产机器上的进程。任何需要部署/开采集/签发Grant/真实模型联验的动作另行明确批准。训练准入保持0，GPU保持未启动。


**P0B九项外部门禁、已存在的RolePlay工具入口与Owner只读交接命令请见：[R60 P0B留证联验审批前置清单](R60_P0B_ROLEPLAY_CAPTURE_ACCEPTANCE_GATES_20261112_CN.md)。真实采集仍HOLD。**

## 八、2026-11-12 Owner实际执行P0A离线合成预检：主要工程门禁PASS，P0B仍需独立审批

Owner提供的真实本地运行回执（**Owner陈述/日志，GitHub或本环境未独立复核本地result.json原件**）：

- `ops/evidence/validate-acceptance-request.mjs --mode draft`：schema `v2-evidence-acceptance-preflight/1`、`requestState=DRAFT_NOT_AUTHORIZED`、`validationPassed=true`、`preflightPassed=false`、`failures=[]`、`executionAuthorized=false`、`productionAcceptance=false`、`trainingDisposition=HOLD`。申请文件SHA256 `e4c238ac31c95dfcff5674efdbb2567525e4371cadc889785d238e68e4b9ba97`。**此PASS只表示草稿校验，不表示ready或生产授权。**
- `check-v2-generation-evidence-preflight.mjs`：`PASS: acceptance preflight; 69 rejected mutations, 8 CLI cases; draft cannot authorize execution`。
- `check-v2-generation-evidence-witness.mjs`：合成scope下模板不得启用真实调用、最坏费用预留/并发与总额度、费用/token/批准到期校验、协议边界、固定上游、原始字节SSE对照及独立日志映射均PASS。超时/重定向/缺Usage/超额/编码/协议错误场景拒绝继续发送；未启动获批真实模型请求。具体逐条PASS以Owner提供回执为准。
- `check-v2-generation-evidence-consumer.mjs`：`PASS: independent consumer comparison, 31 mutations rejected; no evidence upgrade`。
- Owner保留结果文件：`/Users/keedle/workspace/RolePlay/.claude/temp/v2-provider-witness/1794447385440-29103/result.json`；保留清单：同目录`temporary-files.json`。此为Owner Mac本地私有材料，不将文件内容/秘钥/受控原始请求上传到StoryForge普通GitHub。

**P0A现状：离线合成验证环节PASS；完整P0A验收若包含本机运行环境/实际部署SHA、SQL实例探针与Worker安装状态等仍需只读现场记录。P0B真实生产/外连验收HOLD。** 不能把独立合成Provider接收端当成真实供应商入口；不能把CI、旧Web关闭态发布当成真实采集启用。

下一项明确任务是编制`P0B`独立审批执行包（默认全false），逐项列出`APPROVAL_AUTHENTICITY`、`ENVIRONMENT_AND_ARTIFACT_IDENTITY`、`SQL_EXECUTION_AND_PROBES`、`RUNTIME_ACCESS_AND_RESOURCE_LIMITS`、`LIVE_BUDGET_ENFORCEMENT`、`GRANT_CONTROL_AND_TLS_GATEWAY`、`INDEPENDENT_WITNESS`、`CHAT_EXPERIENCE_AND_BILLING`、`STORYFORGE_SIGNOFF`的缺口、负责人和可验收证据。模板`ready`不能通过前不要进行外连或开启生产Worker/采集；不得推定用户泛化“继续推进”等于这些权限已批准。保持旧1000条P2独立推进，训练准入0、GPU0。


**状态：OWNER方向批准、文档及只读准备已实施；RolePlay真实留证启用/付费调用/生产SQL/训练均未获本轮独立批准。** 本文件明确覆盖原主线任务书中“持续追查旧两条实际历史Prompt是P0”的优先级，但不篡改早期审计记录、冻结Rubric或训练准入门禁。

## 一、目标与原则

从`sunxu/RolePlay`的**实际生成请求留证成功且可独立核验**的后续记录中选取高质量SFT候选。不要把“2026-11-10代码已部署”、“某条消息在部署之后生成”、“数据库存在留证表”、“请求日志有哈希”或“有模型输出”当成成功留证。真正的留证必须检查最终HTTP发送的原文字节或完整可验证引用、对应物理Provider attempt、完成输出、后处理、提交的assistant message及目标revision准确关联，且标明观察边界。即使RolePlay出站已证实，relay内部改写/供应商实际接收内容若不可观察，仍不得冒充`HISTORICAL_WIRE_REQUEST_VERIFIED`。

当前2026-11-12 Supabase只读现场复核：`v2_generation_evidence`、`v2_generation_evidence_exports`、`v2_generation_evidence_grants`、`v2_generation_evidence_request_links`四表均**0行**。仓库`sunxu/RolePlay/.claude/docs/v2-production-release-20261110.md`记录获批关闭态代码于2026-11-10发布，采集/Worker/导出未启用；后续实际状态应始终以最新受控探针为准。不能利用未来启用证据的机制回填旧请求。

## 二、优先级与并行关系

| 优先 | 工作流 | 动作 | 完成标准 | 当前 |
|---|---|---|---|---|
| **P0A** | RolePlay留证工程 | 在**合成、隔离环境**执行既有申请草稿验证、完整校验器合成自测、只读部署/SQL/Worker缺口清单；确定联验observer、费用与体验门禁；**不自动开启采集** | 工程合同/合成预检通过，有可审阅的明确范围和缺口；真实Provider联验另行批准 | 既有实现已存在，真实启用HOLD |
| **P0B** | RolePlay真实受控验收 | 经独立审批后小范围采集，验证`manifest`→独立witness→target完成消息精确绑定、物理调用数、缓存、重试/续写和撤回、权限/保留期；评估首字、吞吐、失败率 | Scope内无不可解释capture gap，逐字节一致且来源等级明确；真实费用、性能和数据负责人独立签收 | 未执行/未授权 |
| **P1** | 新数据候选池 | 仅在P0B确证成功**之后**读取批准范围内的真实留证导出；技术筛选（完整性/消息目标/有效system与运行时状态/去重/时间点）、R50与既有训练/验证重叠审计、按冻结六维Rubric独立质量盲审 | 可复核的样本源绑定和训练输入构造，逐条说明留证边界、质量结论及异常原因；无一条凭“生成成功”直接准入 | 0正式候选 |
| **P2（并行）** | 旧1000条补充候选 | 不再逐条无期限追查历史HTTP请求。保留冻结Real1000、Pilot20、双共同PASS、Owner恢复103+243条历史；若用新通用System/受限窗口，明示`SOURCE_BOUND_DERIVED_TRAINING_INPUT__NOT_HISTORICAL_REQUEST`，对内容缺设定的情形优先HOLD | 与新留证样本分数据来源、上下文契约和验证等级，质量审核不受旧模型投票污染 | 2质量PASS，train=0 |
| **P3** | SFT训练准入 | 在足量且多故事分散的候选中建立稳定train/val/test或protected分组，验证R50完整隔离，固定Qwen tokenizer/chat template、实际ms-swift labels仅监督末条目标，CPU全面检验 | 逐条训练输入/来源/质量/隔离/技术门禁全部PASS、Owner批准明确的数据集冻结SHA；GPU需另行授权 | train=0 / GPU=0 |

**执行顺序**：P0A→P0B→P1→P3；P2可独立并行且不能阻塞P0。P0B需要显式的生产/外连/费用/私有数据授权，本轮“推进”仅授权继续只读、文档及离线工程准备，不推定已有这些授权。不要因新留证数量不足而停掉旧1000条的合格片段整理；也不因旧数据缺历史System而把合成System伪装成实际请求。

## 三、优先复用RolePlay现成工程，避免再造留证系统

真实已找到：
- `sunxu/RolePlay/src/app/api/chat/v2/route.ts` — 从`user_stories.v2_data`拼Runtime prompt，动态记忆/角色指令，数据库历史裁剪、清洗、重试；当前一般窗口12条，空回复重试降至6条，**仅说明当前源码行为**。
- `sunxu/RolePlay/.claude/plans/2026-11-07-v2-generation-evidence.md` — A工作包证据捕获架构、授权与资源/性能边界。
- `sunxu/RolePlay/ops/evidence/preproduction-checklist.md`、`acceptance.md`、`README.md` — 固定环境、授权、验收分工和时序。
- `sunxu/RolePlay/ops/evidence/acceptance-request.example.json` 与 `validate-acceptance-request.mjs` — **草稿/拟执行合同校验**，本身不发起部署或授权。
- `sunxu/RolePlay/scripts/check-v2-generation-evidence-preflight.mjs`、`scripts/check-v2-generation-evidence-witness.mjs`、`scripts/check-v2-generation-evidence-consumer.mjs` — 已有合成自测入口，优先重复利用。
- `sunxu/RolePlay/ops/evidence/provider-witness.md`、`verify-bundle.mjs` — 合成单范围独立见证/原文字节比较；不证明供应商内部或relay最终出口。
- `sunxu/RolePlay/.claude/docs/v2-production-release-20261110.md` — 关闭态生产部署事实，已执行的迁移不可重复执行；原延期SQL/B2/B3/B4不可混为同一授权。

注意：现有RolePlay仓库可能有别的agent同步修改。**本次不向RolePlay写入文件、不改生产代码、不触发Actions部署，不创建重复worker/schema。** 以后如需修改须在独立分支、固定基线提交、限定文件集、单独审查。

## 四、现在可执行的P0A离线预检（无网络/付费/数据库变更）

在已有RolePlay本地干净工作树或**新建隔离worktree**中固定待审版本：

```bash
cd "$HOME/workspace/RolePlay"
node ops/evidence/validate-acceptance-request.mjs \
  --request ops/evidence/acceptance-request.example.json --mode draft
node scripts/check-v2-generation-evidence-preflight.mjs
node scripts/check-v2-generation-evidence-witness.mjs
node scripts/check-v2-generation-evidence-consumer.mjs
```

模板的`DRAFT_NOT_AUTHORIZED`、缺审批引用或`ready`拒绝为**预期安全行为**；所有测试仅合成，不接生产凭据，`draft`成功不等于可以发请求。单项失败保存SAFE阶段/测试名，**不要跳过失败或启动真实Provider修复**。具体脚本的运行依赖以固定版本的RolePlay文档为准。

P0A完成后形成**不含真实用户ID/正文/凭据的SAFE回执**：执行代码SHA、合成测试通过数、未完成依赖、当前实际数据库留证索引数、Worker/采集/导出/发放grant开启状态和来源依据、外连/费用待批事项。CI与本地预检PASS不能代替P0B真实联验。

## 五、P0B必须另行提交的审批包

明确合成`story/session/owner`范围与数据使用用途；RolePlay及StoryForge分别审阅人；当前生产服务部署SHA、采集/Worker制品sha和环境指纹；增量SQL实际状态对照**不重复执行现存17份**；采集/导出/原文访问与撤回权限；保留与删除窗口；指定模型协议、物理请求/token/费用硬上限及当期价格核实；独立接收端/中转出口观察边界；首字、尾延迟、错误率、锁等待、内存/IO等可比基线、灰度回滚负责人。

原文导出与训练授权**独立**。只允许确定的获批合成范围先验证，不能先采真实用户完整请求等以后补授权。未拿到真实Provider接收端证据时，可以报告RolePlay HTTP出口证据及`relay_final_egress_unknown`，不得将来源字段改写成更高等级。任何失败维持`HOLD`。

## 六、新样本入库合同（候选门禁，不是当前可执行导出）

每条输出`source_lane=CAPTURED_NEW` 或 `SOURCE_BOUND_DERIVED_OLD`；独立保留`request_observation_boundary`、`wire_body_authenticated`、`provider_attempt_coverage`、`completed_target_revision_bound`、`historical_effective_prompt_content_verified`、`all_retry_attempts_accounted`、`legacy_data_derived`、`quality_six_dimensions`、`r50_complete_exclusion`、`tokenizer_collator`、`train_admitted`。缺任一关键技术证据标`HOLD`，不因为`source_lane=CAPTURED_NEW`自动PASS。

对新样本仍要认真评价目标本身的叙事质量、世界一致性、角色自主性、玩家自主权、文学表现等冻结六维标准；记录来源与实际输出的重试、删改、审核后处理，确保训练目标是经过审阅的最终回复，而不是途中草稿。保证**训练目标不含未来信息**，样本之间按故事/世界组件而非逐行随机切分。R50原始46条保护范围必须独立核验，不泄露sealed提示词。

## 七、Owner决策点与停机条件

- 当前`P0A_READONLY_AND_SYNTHETIC_PREPARATION`可继续实施；P0B还需要明确的执行审批。没有批准或真实证据记录为0，就保持`NO_LIVE_CAPTURE_AUTHORIZATION`。
- 不得以小样本数替代足量筛选、不得以2条文学PASS断言候选来源质量率、不得因为角色卡版本不全就给当前值造历史有效期。
- 不修改RolePlay生产服务、数据库、Worker、捕获开关、用户会话；不启动真实Provider或GPU。
- 旧两条103/243条恢复记录、独立文学PASS与原Real1000冻结证据不改变；正式Train、Quality-v1均0。

**当前决定：`NEW_CAPTURE_EVIDENCE_FIRST__P0A_OFFLINE_PREP__PRODUCTION_CAPTURE_HOLD__TRAIN_ADMITTED_0`。**
