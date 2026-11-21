# R60 Base336 训练后质量评估与 Skill 维护计划（2026-11-17）

## 2026-11-22 现行执行覆盖：结束模型生成，转入 Gold48 Quality-v1 盲评

**以 [主任务书顶部的 2026-11-22 基线](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md) 和 [唯一新 Agent 提示词](../R60_BASE336_NEXT_AGENT_START_PROMPT_20261121_CN.md) 为准。** 下方“等待 GPU/Tokenizer/Owner Freeze”的流程为历史，不再启动。PR #31 最后核验 HEAD `4caf2e3dd5a7d6b2575b2cac0e2c1e0a86a02f40`、7/7 CI；四臂 48×4=192 条真实 HF 推理/交付已完成，Owner Mac 四份结果文件逐臂重新下载 SHA 与结构审计全部 PASS。Base/R46/R54/R60 的 `length` 分别 1/2/1/3，全部保留。四个真实 Job 和 Run ID 见主任务书，不重启不复投。

**唯一剩余质量主线**：现有冻结历史 Original 48 份作为**第五匿名、描述性**参考，共 240 份待评分回答；复用旧 R48 六维 rubric（剧情连续性、角色一致性、指令遵循、文学表现力、互动推进、玩家自主权，1–5），借用旧 R48/R55 v2 匿名/评分冻结/解盲原则而非直接调用硬编码 20×4×3 的旧脚本。Owner 已测试通过 `adradar` 组织计费 HF Inference Providers API；固定模型与提供商/评分 schema/独立评审策略/预算/数据外发边界后，以最薄调用层进行盲审，评分完成并冻结前绝不解盲。8 Story/25 Session，主分析 48；按 Owner 已批准的一整个风险 Story 六题排除做 42 题敏感性分析，须核对既有私有真实绑定。Original 不参与新四臂同输入因果判断。

**证据边界**：`owner_mac_job_image_inspect_verified=false`、签名独立复核仍 false；不能虚构独立镜像证明。`quality_v1_admitted=0`、盲审未开始、模型未晋升。既有 204 Story/495 版本来源审查、Gold48 Frozen Input/原始回复、Tokenizer CPU、四臂 GPU 都不重做；旧章节保留审计历史。不公开私有案例、Story/Session 身份、回复、哈希、评分原文或交叉映射；勿把 Inference Providers 专用 `HF_TOKEN` 混入 Bucket 操作凭据。

---


## 2026-11-21 Gold48 正式计划当前执行覆盖（旧 P2 / Runtime 过程章节仍供溯源）

**现行唯一判断依据**：PR [#31](https://github.com/sunxu/storyforge/pull/31) 实时 HEAD + 实际源码 + 已签收的 SAFE/Owner 私有证据；`1dcbce63e80c5e1d6e1e700f1927bd95f54a08ba` 是最近一次核验基线，不应被硬编码为永远最新。该基线 7/7 GitHub Actions SUCCESS，主 CI `1,778 passed · 6 skipped · 42 subtests passed`，均为**合成/离线**验证，不是 HF GPU 实测。

**唯一业务目标（不可变更）**：48 条已冻结的 `RECONSTRUCTED_EVALUATION_INPUT` × 4 生成臂 = 192 条新回答：Qwen/Qwen3.8-27B Base、R46 v0.2 ckpt-7、R54 v0.3-A ckpt-16、R60 Base336 ckpt-37。再加入**独立的**48 条已冻结历史 Original Assistant 回复作第五种匿名回答来源，共 240 个六维盲评对象（不是 240 次模型推理）。8 Story、25 Session，主分析 48 条、剔除预先指定单一风险 Story 的整组六题后敏感性 42 条；25 Session 聚类，严重违规标记，盲审后解盲。历史 Original 只可作**描述性对照**，不得认定历史 actual-sent 输入与重建输入逐字节一致。冻结 Profile 为 `experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json`；输入/角色/参数/原始回答 SHA、模型 checkpoint 和敏感性分组均不可重新选取或修改。

**证据边界**：Owner Gold48 48 条输入与 48 条原始回复/冻结 SHA 已签收；历史 HF CPU Tokenizer 48/48 SAFE PASS（`6b00971aefaf5e14f4b3b24a`，Run Key `r60-gold48-cpu-20261120T182842Z-e5de137532a1`）。该 CPU Job **只有 SAFE**，没有 `GOLD48_TOKEN_PREFLIGHT_PRIVATE.json`。修复后 `scripts/r60_gold48_gpu_worker_entry.py::STAGED` **恰好 11 份**，已去掉 `token_preflight.private.json`，不得伪造或要求补生成。GPU Loader 在固定 `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` 使用 Tokenizer 并比对同一不可变 revision 的 `chat_template.jinja`，随后才加载模型权重。固定公开模板与该 revision 的 `tokenizer_config.json.chat_template` 已独立只读比对为完全一致（模板 8,952 字节），**但真实 Qwen/PEFT/CUDA GPU 加载及生成尚未实测**。

**唯一下一动作**：在可信 Owner Mac 上，先只读检查**已经存在**的私有 Stage、11 份文件与本次 Owner 显式批准范围、当前 Git HEAD 对应隔离代码 Bundle、三个已签收 Adapter URI；缺失时只补对应真实缺件，不反复执行冻结/签收或创建新系统。必要的代码、私有 Stage 上传使用现有 `hf buckets sync --dry-run` 审核计划，再 `--ignore-existing` 上传至**准确隔离前缀**（跳过同名文件≠核 SHA）。最后用**现有** `scripts/r60_gold48_gpu_cli.py ready` 完成真实远端 11 份 Stage SHA、核心代码 SHA、结果前缀为空、HF Job 历史排重和 CLI dry-run 核验；取得 `GOLD48_GPU_MAC_STAGE_CODE_AND_CLI_READY__NO_JOB` 的真实 SAFE 回执。**截至本交接没有拿到该本轮真实 ready PASS**。

**权限和最短路径**：Mac **不安装** `transformers`/`torch`/`peft`，不在 Mac 运行模型 Tokenizer/Chat Template/Token 预算；HF CPU 历史 PASS 不重跑。已取消 Provider 动态证明/0700 FUSE 原子账本/Owner Ed25519 强制签名，改由单 Owner Mac 的 `approve-one-arm` 0600 create-only 审批、既有 HF 权限、Job 历史与本地一次性提交标记，旧签名逻辑仅兼容历史审计。不使用 Supabase/PostgreSQL、不开新 Runner、不重复 CPU 探针、不修改冻结 Profile、不重复 48 输入与 204 Story/495 版本/R50 等历史审计。**这次文档/接手授权不是 GPU 费用批准**；`ready` 无 GPU，`submit --execute` 是**单臂完整 48 条正式生成**（不是 1 条廉价 Smoke），需 Owner 针对本次模型/Run ID/GPU 预算和范围另外明确批准。未知/失败不自动重试。真实 GPU PASS 后再按另行授权进入 192 生成、Owner 下载 SHA/Inspect、240 对象盲评和 Quality-v1 决议。当前 `quality_v1_admitted=0`、未晋升。

当前唯一新 Agent 指引：[Gold48 启动提示](../R60_BASE336_NEXT_AGENT_START_PROMPT_20261121_CN.md)；完整任务边界：[主任务书](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)；执行命令：[Owner runbook](../R60_GOLD48_OWNER_LOCAL_RUNBOOK_20261121_CN.md)。下方较旧的“必须做 GPU CPU Meta 再研究”“P2 未冻结”“仍待签名”等条目均为历史过程，不可重新排成当前前置步骤。

---


## 2026-11-21 正式计划更新：Gold48 与四模型 Profile 已冻结，转入 Qwen3.8 运行时验证

**本节覆盖以下所有 2026-11-17/19/20 的 P2_B NOT_GENERATED、Gold48 NOT_FROZEN、必须先补完整 Protected/Reserved 权威全集或“模型阵容仍建议中”的旧执行顺序。** 唯一新 Agent 提示词：[2026-11-21 当前启动提示](../R60_BASE336_NEXT_AGENT_START_PROMPT_20261121_CN.md)；权威任务书：[Gold48 P2 Quality-v1 主线](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)。继续 PR #31 实际 HEAD；历史段落保留审计用途，不得重新当作执行指令。

**已经签收、不得重做：** Owner 私有 SAFE `GOLD48_SCOPED_OWNER_FREEZE_COMPLETE__GENERATION_PROFILE_PENDING`：48 主分析 /42 敏感性（剔除单一来源风险六题）/8 来源/25 Session，48 重建输入 SHA 与48 独立历史原始回答 SHA 已冻结。统一消息是 `RECONSTRUCTED_EVALUATION_INPUT`；历史实际发送 Prompt 及全历史保护集独立性未证实，Owner 接受限定来源风险，不能冒充全宇宙隔离 PASS。唯一 HF CPU Tokenizer Job `6b00971aefaf5e14f4b3b24a` 已完成且 Owner SAFE 字节验收，48/48 在两种 Thinking 模式和 16K/32K 诊断预算无溢出；**不重跑**候选、Stage、HF CPU Job、原始回答匹配、历史 204 Story/495 版本来源审阅、R50/R47/R48/R55/R58 已核审计。

**另一个独立签收：** Frozen 四模型 Profile `experiments/r60_quality/gold48_four_arm_generation_profile_frozen_v1.json`，状态 `GOLD48_FOUR_ARM_PROFILE_FROZEN__RUNTIME_VALIDATION_PENDING`，`owner_generation_profile_freeze=true`；候选 Blob SHA 绑定，参数固定 Thinking=false、32K context、30720 input +2048 generation、sampling 0.7/0.8/top_k20/min_p0、seed 42+题目索引、无截断。四臂 Base Qwen3.8-27B /R46 ckpt7 /R54 ckpt16 /R60 Base336 ckpt37，原始 Gold 第五来源为描述性参考；将来 192 条新生成+48 条旧回答共240份六维盲评，按25 Session 聚类、48/42双报告。当前冻结不等于推理许可：`inference_authorized=false`、`gpu_authorized_by_this_document=false`、`quality_v1_admitted=0`、`model_promoted=false`。

**唯一下一阶段里程碑：** Qwen3.8/PEFT 真正可运行合同——复用现有三份 Adapter Release SHA/Reload 凭证、固定精确 Base Revision、`Qwen3_5ForConditionalGeneration`、EOS `[248046,248044]`、PAD `248044`、兼容推理镜像和 hash-pinned 依赖锁，检验 Chat Template、输入预算/停止行为与 Adapter Reload。薄加载器 `src/storyforge_dataset/generation_eval/gold48_qwen35_loader.py`、原 `generation_eval.backend` / `generation_eval.worker` / `hf_runtime` 已有，6/6 合成 CI 通过；**尚未有四臂真实 GPU 运行时 Smoke**。只对真实阻塞补最小适配，不创建新生成器或重复 Tokenizer 核心。HF CPU 技术预检用户已许可（含付费），但真实 GPU/模型 Smoke 与后续192次正式推理必须按冻结 Profile 的 `inference_authorized=false` 边界取得单独授权。无需再开发与主线无关的审计、质量工具或新训练。

**后续通关顺序**：Adapter 权重身份/ SHA 绑定 → 推理镜像与 Qwen3.5/PEFT 版本锁 → 合成 CPU/静态导入核验及必要薄补丁 → 明确授权的真实 GPU 单模型/四臂加载 Smoke（独立 SAFE） → 另行授权 192 次正式配对生成 → 240 对象盲评/六维与严重标记 → 48/42 敏感性和聚类分析 → Owner Quality-v1 裁决；任何一步 HOLD 都不能通过修改已冻结输入、简化四模型或借用旧 P4 Qwen3-32B/GLM 来绕过。

---


## 2026-11-20 Owner 批准限定来源独立性与 Gold48 冻结准备

Owner 已批准 **`INDEPENDENT_WITHIN_VERIFIED_HISTORICAL_SOURCE_SCOPE`** 和未知历史来源暴露风险披露，明确**不再以补齐 Protected/Reserved/Held-out/Dev/Arbitration/Teacher 所有历史总名册为本轮 Gold48 的无限期前置**。已有 204 Story/495 版本独立语义结果、R50/Gold195/旧 Dev20 等已知子集直接复用；总宇宙独立性依旧 `UNVERIFIED`，不可声称全部过去训练/测试/教师输入均无污染。新发现来源重叠时记录受影响 Case 为 `EXPOSED`、报告无污染子集的敏感性结果，不静默改 Gold。正式 Owner 决议：[SAFE](../evidence/R60_BASE336_P2_SCOPED_INDEPENDENCE_OWNER_DECISION_SAFE_20261120.json)。

**实际执行合同**：现在允许 **Gold48 48 条完整历史 Prefix +48 条匹配原始回复的私有冻结准备**（不是提前认定已经冻结）；复用已存在的历史恢复/来源证据/Gold 匹配核心，不执行旧三消息 `r60_base336_p2_public_prompt_package_gate.py` 冒充完整历史 Prompt 验收。每题私有锁定原 Story Revision、许可生效时间、Session、完整 Prefix/真实回复、重建 `System/World/Character/Rules/Memory/History` 分量来源/版本/SHA；四新生成臂同一重建输入，Historical Original Reference 第五来源仅作**描述性历史参考**，不得做同字节因果声明。

单一故事内容瑕疵已获 `OWNER_ACCEPTED_WITH_QUALITY_CAVEAT`：48 题主分析 +按真实 Story 身份排除其**整组六题**的 42 题配对敏感性分析，不凭 `Pxx/Sxx` 编号猜六题，不修改旧 Revision 或原始回复。Owner 本地 Reviewer8↔P2 八来源唯一双射已报告 PASS；**正式六题 Case ID 只能在 48 题私有候选产生后进行匹配**。冻结 Manifest/重建分量哈希/完整权限绑定及 Owner 最终签收尚未发生；`P2_B_48_PROMPTS=NOT_GENERATED`、`quality_v1_admitted=0`、`train_admitted=0`、`model_promoted=false`。本批准不授权新 GPU/HF/付费模型推理。

**现行签收顺序唯一**：私有既有候选精准绑定→内部创建不可变 48 条冻结候选及 48/42 case 选择→Owner 审核与 Source/Prompt/Reference hashes → Gold48 正式签收 → **另行审批** 192 模型生成及 240 来源匿名盲评。详见[主任务书](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md) 顶端新决议；本文以下旧“必须先补完整历史权威名册”属历史严格口径，不应阻止本次限定范围路径。

---


## 2026-11-20 Owner 已完成单一 P2 来源风险仲裁

**`OWNER_ACCEPTED_WITH_QUALITY_CAVEAT` 已获 Owner 明确批准**：不修订原 P2 公开卡，不改写真实历史 Prefix 或原始回答。正式预注册 **48 题/8 Story 主分析**与**剔除有家族/角色命名残留的 1 Story 整组六题后 42 题/7 Story 敏感性分析**。两套结果同时报告，来源原有冲突不应直接记为模型失误，不能等模型结果出来再选择是否排除。实际被标记 Reviewer 匿名键→真实 Story ID→Gold48 六题 ID 的绑定只在 Owner 私有域核验，未完成前状态 `P2_SOURCE_QUALITY_PRIVATE_MAPPING=PENDING`，不得按 P/S 匿名编号猜测。

准入决策 SAFE：[Owner 质量风险仲裁](../evidence/R60_BASE336_P2_SOURCE_QUALITY_OWNER_DECISION_SAFE_20261120.json)。仅已知风险策略关闭；其它历史来源 Authority 完整成员与版本仍 `UNKNOWN_HOLD`，不得宣称 P2-C 已 PASS。输入为已批准的 `RECONSTRUCTED_EVALUATION_INPUT`，历史 Original Reference 为第五匿名**描述性**对照，不能声称同历史实际发送字节。Gold48 未冻结、GPU 推理未批准。

---


## 2026-11-20 Owner 输入合同裁决（优先于下方历史计划）

Owner 已明确批准 `RECONSTRUCTED_EVALUATION_INPUT` 作为 Gold48 Quality-v1 统一输入，且**不访问 RolePlay 生产环境**；无需证明历史 Provider actual-sent 字节即可开展**满足其它门禁后的**受控质量评估。固定四个新生成模型输入的统一重建消息与 SHA 后做四模型同题配对主比较。第五个 Historical Original Reference 仍匿名参加六维评分，但其当年真正 Provider 完整输入未验证，只能做同历史剧情/Prefix 的**描述性参考比较**，不能宣称“原始 Gold 使用了与四模型 byte-exact 一致的重建 Prompt”或据此做严格因果比较。

执行顺序：**只处理剩余 Authority 完整来源/未审差集与单一 P2 卡输入质量仲裁 → Owner 有效 Source/Prompt Freeze → Gold48 私有 create-only 构造 → 单独授权 GPU 推理 → 五来源盲评**。旧段落里等待 Owner 重新批准重建输入、必须核查生产 actual-sent、或仍称 48 Original Reference 不存在的描述均为历史快照。固定 `ACTUAL_SENT_PROMPT_BYTES=UNVERIFIED`、`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`quality_v1_admitted=0`、`train_admitted=0`、`model_promoted=false`。详细唯一现行合同见[主任务书](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md) 顶部。

---


## 2026-11-20 当前质量评估合同（覆盖旧两臂/三消息及“未发现 Gold”设计）

最新唯一执行任务书与新 Agent 启动提示词：[R60 Base336 P2-C → Gold48 → 五来源同题盲评](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md) 顶端。下文 2026-11-17/19 章节作为历史设计，不得把“固定三消息 / 只用公开 Opening 新编 48 题 / 两生成臂 / 不存在匹配 Gold / 全 172 Story 来源未提取”当作当前事实。

**现行固定目标**是 **48 条真实完整持久化历史 Prefix +48 条严格同题 Historical Original Reference**，在完全相同的预注册评估输入上，比较 **Qwen Base、R46 v0.2 ckpt-7、R54 v0.3-A ckpt-16、R60 Base336 ckpt-37** 四生成臂，连同原始回答共 **五种匿名来源、240 个评分对象（192 新生成 +48 原始，不是 240 次推理）**；六维及严重标记，聚类单位按 8 Story/25 Session，历史原始回答不是人工标准答案。Owner 的真实候选筛选已经得到临时 **8 Story /7 作者、2 GPU 前+6 GPU 后、48/48 不同 Prefix/Reference**，48/48 唯一模型成功请求元数据对应；它不是正式 Gold48 Freeze，亦**没有 Provider actual-sent System/World/Rules/Memory/History 字节验证**。历史原始回答有效模型 26/21/1 只在解盲后分析。

**已有隔离核验**：Base336 172 Story/375 版本 Reviewer 8/8 + History32 新 32 Story/120 版本 Reviewer 8/8；共享历史 1 Story 的4/4版本已审，因此限定范围总计 **204 Story/495 版本**，并已核验 StoryID/版本锚及 Owner findings 本地权限双 SAFE；不是所有 Protected/Teacher 的穷尽认证。R50 50→46+4、已知五世界身份、旧 Dev20 及 Gold195、R04 等已核查子集不再重复。

**尚待决议**：其它历史 Protected/Reserved/Dev/Teacher 权威完整曝光范围；实际发送 Prompt 字节不可得时 Owner 是否批准**显式标 `RECONSTRUCTED_EVALUATION_INPUT` 的可复现同题替代输入**；一个 P2 原公开卡自身家族/角色改名残留的输入质量仲裁（预注册 48 及剔除六题的 42 题敏感性方案）。只有以上准入与用途权利、Owner Freeze 完成，才正式生成 Gold48 包并另行申请 GPU/HF/四模型推理预算。**`P2_C=HOLD`、`P2_B_48_PROMPTS=NOT_GENERATED`、`model_promoted=false`**。绝不让参考答案进入生成端。

---

## 2026-11-19 Owner 明确新增：原始回答 Gold 是正式盲评的必要对照

**当前正式设计：四个生成模型 + 一份同题原始回答 Gold（总计五种匿名回答来源，Gold 不是生成模型）。** 具体强制约束见 [现行 Agent 任务书第八节](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)。主比较增列 **R60 Base336 checkpoint-37 vs 原始 Gold**，并保留对 Base 和 v0.2 的主要比较、v0.3-A 的诊断比较；Gold 本身也按六维及严重违规评分，不设为无误绝对真值。

匹配来源真实存在时，48 题 × 4 模型 = **192 份新生成**，另有 **48 份原始 Gold**，即 **240 份匿名盲评回答**，不是 240 次推理；三模型预算方案则 144+48=192 份盲评回答，**绝不删 Gold**。

**前置源数据约束**：当前新 P2 48 提示是基于八条公开 World/Character/Opening **全新构造**的三消息情境，至今未生成，更没有经 Owner 证明与这 48 题精确对应的历史原始回答。旧 R48 的 20 条原始 Gold 不能迁入新 P2，也不能把公开 Opening 或代写答案充作“原始回答”。每条必须满足冻结 Prompt 完整前缀与来源原始回答上下文逐消息严格一致、源回复非空、来源版本/时间、内部评估使用权、历史曝光/训练隔离证明，复用 `scripts/v02_r48_four_arm_build.py::read_gold` 的原有合同。参考回复单独私存、生成侧不得见；Owner 不批准扩大私有会话访问。若 48 个新提示没有合法原始回复，应以 `P2_NEW48_MATCHED_ORIGINAL_GOLD=UNVERIFIED_HOLD / NOT_AVAILABLE` 明示，必要时**先经 Owner 授权调整新来源构造路线**，而不是虚构 Gold 或把已曝光旧题包装成 Held-out。

**正式质量比较进度仍未开始**；P2-C=HOLD、P2-B 48 提示未生成、P4 GPU/HF 仍须独立授权；这次变更只有模型比较与原始回答的设计合同，不是推理或数据访问许可。

---


## 2026-11-19 评估模型阵容重评（方案更新，尚未获 GPU 授权）

现行统一说明：[R60 P2 Quality-v1 接手任务书](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md) 第七节。**此前本计划所述仅 Base vs checkpoint-37 两臂，是最低限度比较而非完整、已获授权的最终评估阵容。**

建议 P2 新 48 条来源冻结且 P2-C PASS 后，以 **Base、R46 v0.2 checkpoint-7、R54 v0.3-A checkpoint-16、R60 Base336 checkpoint-37** 四臂做同轮配对盲评。必须的主比较为 Base336 vs Base、Base336 vs 历史强基准 v0.2；v0.3-A 作为预注册诊断臂用于确认旧 R55 混合回退是否延续；如果预算有限可事先冻结为不含 v0.3-A 的三臂。v0.1 因旧 R47/R48 表现弱、边际价值低，暂不进入新测试；原始 Gold 是旧参考答案不是新生成模型。旧 R50 的 Base/v0.1/v0.2/v0.3 四臂方案属于历史拟议合同，不得误认已执行或照搬 R50 密封题。

四臂共 48×4=192 回复（三臂 144），但**不是 192 个独立 Story**；需独立随机 A/B/C/D 盲化、六维指标/硬规则逐模型比较、世界层聚类，避免简单用单一“胜者”代替主对照。所有冻结 Base/旧 Adapter 与本轮 Adapter 的 SHA、推理模板和消耗预算需先审批；四臂只是设计建议，不等于推理许可。P2-C HOLD、48 Prompt NOT_GENERATED、HF/GPU 无新授权与 model_promoted=false 均不变。

---


## 2026-11-19 最新执行决策（覆盖本文件较早的“下一步”）

**唯一现行新 Agent 任务书：** [R60 Base336 P2 Quality-v1 新 Agent 接手任务书](../R60_BASE336_P2_QUALITY_EVAL_NEXT_AGENT_HANDOFF_20261119_CN.md)。本文件记录总体质量评估合同与历史证据；较早要求“R47/R48/R55 Story ID 还未知”“R55 三层尚未核验”“R50 五世界还未绑定”“第一步重新做 Owner metadata inventory”等均已被新 SAFE 覆盖，**不要再执行**。

主线不可改变：**P2-C 核验 8 条新公开来源的真正独立性 → P2-B 构造并冻结 48 条全新三消息/六维提示 → P3 仅作 Base/Adapter 两臂薄适配 → P4 单独授权配对生成 → P5 六维盲评和 Owner 裁决**。本次唯一训练仍为 Base336 293/43、checkpoint-37，工程 PASS 而质量未评估、模型未晋升。

截至最新 Owner SAFE：P2-A 8 来源 READY；P2 × Base336 172 Story 精确 ID overlap=0，但完整 current/archived World/Character/Opening 语义来源包未生成，Owner 捕获到 `DB_BASE336_SOURCE_QUERY_HOLD`；R50 provenance 50=46+4 与冻结五世界=原始 50 来源 Story 集合均 PASS，P2 对 R50 五世界 overlap=0；R47/R48/R55 已核验同一旧 20 Prompt / 2 Story、三层 Index 来源链，P2 exact overlap=0；R58 旧五范围 CSV 五行空引用，**不代表历史来源不存在**。剩余是新 8 来源的全版本语义隔离、其它 Protected/Reserved 与历史 Dev/训练/教师暴露权威全集、actual-sent、独立 Reviewer 和 Owner Freeze。

**不重复**上述所有 PASS/旧 35 候选图/旧 38 Story 提取；不猜测性重跑失败 SQL，不开发重复 UUID/IO/Blind/Quality-v1 核心。不访问 R50 密封题目和私有聊天，不写 DB，不新建正式 48 包、不启 GPU/HF。Owner 已授权本项目限定**只读**数据库核验无需逐次重复申请；**GPU 推理/训练仍必须逐次单独批准**。P2-C=HOLD、P2-B=NOT_GENERATED、train_admitted=0、quality_v1_admitted=0。

关联 SAFE：`docs/evidence/R60_BASE336_P2C_MAINLINE_GATE_STATUS_SAFE_20261119.json`（状态投影）及其引用的原始 Owner SAFE；最新 PR #31 分支 HEAD/CI 需实时核对。

---


## 1. 当前结论

**工程训练完成；独立质量评估未开始。**

- Owner 分支：`r60/common2-cpu2-owner`。
- 训练 Stage 绑定的源码 HEAD：`87bd0680c9f7321da12c70c490e2a6ebb875d503`。
- Run Key：`r60-base336-gpu-20261117T055622Z-b609cb78661d`。
- Hugging Face Job：[`6afbfd5c98dda891b5df7fd2`](https://huggingface.co/jobs/adradar/6afbfd5c98dda891b5df7fd2)，Owner 查询状态为 `COMPLETED`。
- 唯一提交回执确认 `job_submission_calls=1`、`hf_jobs_submitted=1`；没有自动重试。
- Worker SAFE：`BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED`。
- Train / Validation：293 / 43；37/37 Optimizer Steps；1 Epoch。
- `terminal_checkpoint_verified=true`、`adapter_reload_verified=true`、`model_promoted=false`。
- `train_admitted=0`、`quality_v1_admitted=0`、`r50_read=false`。

Worker SAFE 中的 `hf_jobs_submitted=0` 是 Worker 不提交嵌套 HF Job 的固定字段；它不否定外层提交回执所记录的唯一训练 Job。

## 2. 训练证据摘要

| 项目 | 已核验值 |
|---|---:|
| GPU | NVIDIA A100-SXM4-80GB |
| GPU 总显存 | 79.2 GiB |
| 启动可用显存 | 78.8 GiB |
| 峰值显存 | 36,115 MiB |
| 模型 | Qwen/Qwen3.8-27B |
| 固定 Revision | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| LoRA rank / alpha | 64 / 128 |
| Optimizer Steps | 37 |
| Train Loss（Trainer 汇总） | 2.146966 |
| Terminal Eval Loss | 1.932103 |
| Terminal Eval Token Accuracy | 55.09% |
| Swift train runtime | 1,699.8 秒（约 28分20秒） |
| Worker 总耗时 | 1,948.8 秒（约 32分29秒） |

固定依赖：ms-swift 4.5.3、transformers 5.16.1、bitsandbytes 0.50.2、qwen-vl-utils 0.0.14、huggingface_hub 1.33.0。

训练评估日志的最终记录为 step 37/37，eval_loss=1.932103395；Trainer 汇总 train_loss=2.146966。它们是训练/验证损失指标，不是文学质量结论，也不能单独证明相对 Base 有提升。

## 3. HF 产物只读盘点与完整性边界

Owner 已对独立输出前缀完成递归文件盘点：

- 33 个远端对象，总计 5,604,774,224 bytes。
- 最终 `adapter_model.safetensors`：1,867,797,544 bytes。
- `checkpoint-37/optimizer.pt`：3,736,129,330 bytes。
- Worker SAFE、运行日志、reload 输入/输出、Trainer state、adapter config、训练日志、图表和 TensorBoard 事件均存在。
- HF Job 状态为 COMPLETED；最终 checkpoint、terminal eval、one epoch 和 adapter reload 均由 Worker SAFE 确认。

**已完成（Owner Mac SAFE，2026-11-17）：** `BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION`。固定远端文件集合核验PASS，33/33对象已下载并逐个计算本地SHA256，总计5,604,774,224 bytes；Worker SAFE、checkpoint-37、terminal eval和Adapter Reload证据均再次核验通过。审计期间没有启动GPU或提交HF Job，未输出私有路径、文件名、正文或哈希，未提升模型。私有SHA清单保存在Owner Mac的独立审计目录。重要边界：这是下载对象的本地SHA256 inventory；由于Worker没有发布原始逐文件SHA，不能声称完成了“本地哈希与Worker原始哈希逐文件比对”。工具复用 `r60_base336_gpu_cli._remote_set/_remote_uri` 和 `hf_job_runner.sha256`，不写Bucket、不提交Job、不启动GPU。

## 4. 为什么 43 条 Validation 不能作为独立质量测试

- 43 条 Validation 已作为本次 `swift sft --val_dataset` 输入，并在 terminal step 37 执行 Eval。
- Trainer state 将 `checkpoint-37` 记录为 best checkpoint，best_metric 为 terminal eval_loss。
- 因此这 43 条已参与训练过程中的 checkpoint/模型选择，不能再称为未触碰的独立 Held-out，也不能用于正式模型晋升结论。
- 293 条 Train 更不能用于独立评测；293+43 的 336 条全部属于本次训练/验证池。
- Worker 只对一个 Validation 样本执行了 `swift infer` 的 128-token Adapter Reload smoke；它证明 Adapter 可加载并产生非空结果，不是完整 43 条生成评估，也没有 Base 对照臂。

R50 密封内容仍禁止读取。R47/R48/R55 已暴露开发题不能重新包装成独立测试。REAL1000/Pilot5 的旧 Reviewer 回执也不能被当成 Base336 生成输出的评测结果。

## 5. 现有工具盘点与复用边界（复核后更新）

| 现有能力 | 本轮复用方式 | 不能直接照搬的部分 |
|---|---|---|
| `src/storyforge_dataset/generation_eval/worker.py::run_generation_batch` | 优先复用注入式 Backend 批量生成核心、输入 Manifest / record count / token budget / seed / 输出 Receipt 合同 | profile authorization 与 model_role 仍需适配本轮 Base/Adapter 两臂 |
| `src/storyforge_dataset/hf_runtime/inputs.py` / `outputs.py` | 复用输入 SHA/JSONL 校验、私有输出、create-only 与 SAFE 边界 | 不为 Base336 另建通用输入/输出运行时 |
| `GenerationBackend` Protocol | 复用模型后端抽象，Base 与 Adapter 的加载差异放版本化薄适配器 | P4 已冻结模型角色、revision、依赖锁不能跨任务替换 |
| `src/storyforge_dataset/generation_eval/formal_pairing_gate.py` | 复用 prompt/message 精确配对、哈希清单、reference-label absence 检查思路 | 现有 Gate 固定三模型角色与 Pilot 样本合同，不是 Base/Adapter 两臂 Gate |
| `scripts/prepare_eval_pairs.py` | 复用逐案随机 A/B、私有 answer key 与 create-only 思路 | 旧五维字段/位置型校验不满足本轮 prompt SHA 与六维合同 |
| `experiments/r58_quality/quality_v1.py` | 唯一六维 floors（4/4/3/4/4/4）与 severe flags 来源 | 只复用规则定义；不得将模型生成回复送入源候选 `decide/summarize` 或 Gold Manifest |
| `scripts/analyze_blind_eval.py` / `scripts/export_context_blind_review.py` | 参考历史盲化映射和上下文呈现 | 旧五维 scorecard、固定 15/20 条 Exporter 不适用 |
| `scripts/hf_job_runner.py` | 可复用通用 `Runner`、哈希和非空结果检查小工具 | `make_inference_input` 仅做 Validation 第一条 smoke，不是独立 Held-out 批量 Worker |

**结论：** 生成执行核心与 HF Runtime 已存在，不再另写通用生成循环、JSONL 校验、私有输出写入或 SAFE Receipt。P2 通过前不实现正式 Pairer、Profile 或模型 Backend。P2 通过后只新增版本化 Base/Adapter 薄适配器和对应合成测试；不修改冻结 P4 Profile/CLI，不复制六维 Rubric。

## 6. 正式独立质量评估的必要条件

1. **新的独立测试来源：** Owner 已批准采用 Supabase 公开故事/公开世界设定路线，仅用于内部独立评估提示构造，不读取用户私有会话正文。来源筛选、revision、审核快照 SHA256 和最新公开权限事件绑定 8/8 通过；但截至本次复核，48 条提示包没有可核验的 JSONL/Manifest 文件与 SHA256，不能将其描述为已构造。提示包结构校验器和合成测试代码已存在，但它们不代表真实提示包存在。权威补充记录：`docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`。当前仍是 Draft，不是冻结 Held-out；必须完成 Base336 私有来源、R50 仅元数据、R47/R48/R55 暴露题的交叉排除及 Owner 冻结。若不能取得完整语义隔离证据，对应来源保持 HOLD。
2. **固定生成合同：** Base 与 Adapter 使用相同的三个可见持久化消息、相同模型 Revision、相同上下文长度、解码参数、停止条件和输出 Token 上限；Adapter 路径固定到本次 checkpoint-37。生成参数必须先在合成测试和 CPU CLI 兼容检查中冻结，不能看过质量结果后反复调参。
3. **独立配对生成：** 每个 prompt 对 Base/Adapter 各生成一次；逐项核对 prompt SHA、消息前缀、输出数量、非空、停止/截断元数据。每案随机化 A/B，映射密钥单独 0600 保存，评审者不可见模型身份。
4. **六维盲审：** 严格复用 `quality_v1.py` 冻结六维门槛（4/4/3/4/4/4）与三个严重标记（`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`）；评审只依据给定三消息，不推断隐藏世界设定。保留逐条证据引用、HOLD 不确定性和严重问题，不用旧五维 scorecard 替代。
5. **独立性与裁决：** 评审者必须盲化且执行独立；不同模型 ID 不等于独立。严重标记和世界事实争议由 Owner/独立裁决处理。小样本偏好统计不能被描述为总体提升或生产质量通过。
6. **单独 GPU 推理授权：** 之前授权仅覆盖本 Run Key 的一次探索性训练 Job，不包含 Base/Adapter 配对推理、GPU 评审或新的训练。未来如需 HF GPU inference，须重新提交精确 Job 目的、模型、Flavor、时长、样本数、生成 Token 上限、Bucket RO/RW 前缀和费用范围，等待 Owner 明确批准。

## 7. 下一步顺序与当前决策

| 顺序 | 工作 | 当前状态 |
|---|---|---|
| P0 | 训练 Job / SAFE / Checkpoint / Adapter Reload 证据核验 | PASS |
| P1 | 33 个远端对象下载与本地 SHA256 inventory（33/33，5,604,774,224 bytes） | PASS（Owner SAFE） |
| P2-A | Supabase 公开来源筛选、revision、审核快照和权限事件绑定 | PASS（8/8） |
| P2-B | 48 条提示 JSONL/Manifest/SHA256 | NOT_GENERATED（仅校验器与合成测试代码存在） |
| P2-C | Base336 / R50 元数据 / R47-R48-R55 语义隔离、提示独立复核、Owner 冻结 | **HOLD** |
| P3 | 复用 `generation_eval.worker` / HF Runtime，设计 Base/Adapter 两臂 Profile、Pairing 与六维审核薄适配器及合成测试 | 复用审查完成；实现等 P2-C |
| P4 | Base/Adapter 配对 GPU 推理 | 需单独授权 |
| P5 | 独立盲审、严重标记核验和 Owner 裁决 | 等 P4 |
| P6 | 模型质量结论与是否继续下一轮实验 | HOLD |

**当前最终状态：** `BASE336_GPU_EXPLORATORY_ENGINEERING_PASS__NOT_PROMOTED`，且产物审计为`BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION`。P2-A 来源版本/公开权限证据 8/8 已核验；P2-B 的真实 48 条提示 JSONL/Manifest 尚未生成，只有校验器代码与合成测试。最新收到的 8 组世界来源证据仍是 `all_decisions=HOLD`，`semantic_review_completed=false`，`actual_sent_prompt_verified=false`；7 组标记为当前 Train/Validation 跨集合，全部 8 组仍未完成语义裁决。Base336 世界隔离、R50 元数据排除、R47/R48/R55 暴露排除、提示逐条复核和 Owner 冻结继续 HOLD。保持 `model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`。在 P2-C PASS 前不实现正式 Pairer、不启动推理、不追加训练、不访问 R50 正文、不写数据库。

### Owner Mac 只读产物审计命令（已执行，保留复现记录）

```bash
cd ~/workspace/storyforge-r60-4router-review
PY="$HOME/.local/share/storyforge/venvs/r60-owner/bin/python"
RUN_KEY="r60-base336-gpu-20261117T055622Z-b609cb78661d"
OUT="$HOME/.local/share/storyforge/r60/private/r60-base336-result-audit-$RUN_KEY"
export PYTHONPATH=src:scripts:experiments/r58_quality
"$PY" scripts/r60_base336_gpu_result_audit.py --run-key "$RUN_KEY" --output-dir "$OUT"
```

该命令先只读列举HF Bucket并核对固定33对象清单、磁盘空间和本地私有目录，再逐个下载结果对象到新建私有目录，计算本地SHA256并写0600 Manifest；预计下载约5.61GB。远端大小元数据不完整时会要求至少8GiB空闲空间。下载失败留下的目录不得删除后复用；应先只读检查失败原因并另用新目录。SAFE只报告文件数/字节数，不输出私有路径、文件名、内容或哈希。


### 2026-11-17 Owner Mac 产物审计 SAFE 回执

```json
{
  "status": "BASE336_GPU_RESULT_ARTIFACT_INVENTORY_PASS__NO_PROMOTION",
  "run_key_validated": true,
  "remote_file_set_verified": true,
  "files_downloaded": 33,
  "files_hashed": 33,
  "total_bytes": 5604774224,
  "worker_receipt_verified": true,
  "checkpoint_verified": true,
  "adapter_reload_verified": true,
  "audit_gpu_started": false,
  "hf_jobs_submitted": 0,
  "model_promoted": false,
  "train_admitted": 0,
  "quality_v1_admitted": 0,
  "private_values_emitted": false
}
```

该SAFE不包含本地SHA值、逐案内容或私人路径；本仓库只记录聚合状态，不复制私有Manifest。


## 8. 2026-11-17 生成评估代码复用审查（只读盘点）

P2 来源路线已获 Owner 批准；48 条提示包尚未生成。8 组世界来源证据已收到但全 HOLD，语义隔离和 Owner 冻结仍未通过。本节只记录既有代码的复用边界，不改动运行时、不提交 HF Job。

### 推荐复用顺序

1. **生成执行核心优先复用**：`src/storyforge_dataset/generation_eval/worker.py::run_generation_batch` 是注入式 Backend 的批量生成引擎；它复用 `hf_runtime.InputManager` 校验输入 SHA/JSONL、校验 sample_id 与消息合同，并通过 `OutputManager` create-only 写私有输出，记录 finish_reason / truncation 计数。Base336 不应另写一套通用生成循环、JSONL 校验、私有输出写入或 SAFE Receipt。
2. **HF 公共基础复用**：沿用 `src/storyforge_dataset/hf_runtime/inputs.py`、`outputs.py` 的输入验签和私有输出合同；复用既有 Backend 抽象、依赖锁与镜像摘要验证模式。Base336 专属差异只放在版本化 Profile/Backend Adapter。
3. **配对与盲化复用原则**：复用 `formal_pairing_gate.py` 的 prompt 消息精确配对、哈希清单和 reference-label absence 检查思路；复用 `prepare_eval_pairs.py` 的逐案随机 A/B 和独立 answer-key 思路，但必须先补足本任务的两臂合同、prompt SHA 绑定和安全输出权限。
4. **质量规则只复用唯一来源**：`experiments/r58_quality/quality_v1.py` 是冻结六维门槛/严重标记的唯一来源（floors 4/4/3/4/4/4；三个 severe flags）。生成评估只复用这些规则定义和审核语义；不能把模型生成回复送入该模块的源候选 `decide/summarize`，更不能把它伪装为数据库最终持久化 Assistant 目标或Gold Manifest事件。

### 不能直接照搬的既有模块

- `generation_eval/profiles.py` 与 `worker_cli.py` 当前绑定 P4 的三模型角色 A/B/challenger（Qwen3-32B、GLM-4-32B、GLM-Z1-32B）和其冻结 profile。CLI 还固定 torch 2.6.0+cu124 / transformers 4.57.1；Base336 是 Qwen/Qwen3.8-27B 的固定 revision 与本轮 Adapter，训练环境依赖为 ms-swift 4.5.3 / transformers 5.16.1。P4 profile、模型授权和运行时不能跨项目/模型直接复用，也不能修改旧冻结 profile 以迁就本轮。
- `formal_pairing_gate.py` 目前强制三个角色及 S/W-pilot/W 固定样本数，不适用于 Base/Adapter 两臂；可以复用其严格消息集合哈希和无参考标签检查，但应做任务专属薄适配。
- `r60_p4_evaluation_output_schema_candidate_v1.json` 是旧三维 severity 候选，不是 Quality-v1 六维；不能拿它作本轮评分合同。
- `scripts/prepare_eval_pairs.py` 与 `scripts/analyze_blind_eval.py` 使用旧五维字段；Pairer 的输入校验偏向列表位置和消息前缀，不负责完整 prompt SHA/stop reason/token 计数绑定。不得直接产出本轮六维盲审包。
- `scripts/export_context_blind_review.py` 固定 15/20 条并使用旧五维 scorecard；不可直接用于本轮 40–60 条候选集或六维审核。
- `scripts/hf_job_runner.py` 的 `Runner`、`sha256`、`check_inference_result` 可作为通用命令/哈希/非空结果小工具；其 `make_inference_input` 只取 Validation 第一条做 smoke，不可用于独立 Held-out，也不能代替上面的批量生成 Worker。

### Base336 适配器的冻结前检查项（P2 通过后才实现）

- 两臂严格为 Base 与本次 checkpoint-37 Adapter；模型 ID/revision、Adapter SHA、Tokenizer/Chat Template、依赖锁和 runtime digest 必须固定。Base 与 Adapter 使用完全相同的提示、三个持久化可见消息（无 System）、解码参数、seed、输入/输出 Token 上限、停止条件。
- 每条输入必须由来源包绑定 prompt SHA、故事/World 组件与权限证据；私有身份 crosswalk 只留在 Owner 本机。正式测试源未确认前，不得从 661 个未准入候选、数据库或旧 P4 输入自动抽样。
- 输出需保留 prompt SHA、模型/Adapter 身份、input/output token 计数、finish reason、截断状态及结果 SHA；逐案随机 A/B，blind key 独立 0600 保存，Reviewer 不得看到模型身份。
- P2 已采用 Owner 批准的 Supabase 公开故事路线；48 条 Draft 由 8 个来源构造。仍需完成 Base336 私有 source roster / World component crosswalk、R50 仅元数据排除、R47/R48/R55 暴露排除、提示忠实性复核和 Owner 冻结。未通过则质量评估保持 HOLD。
- 本轮训练授权不包含 Base/Adapter 推理；旧 P4 的授权也不适用于 Qwen3.8-27B Base/Adapter。真实推理前仍需单独明确授权具体输入、模型、Flavor、时长、样本数、Token 上限、Bucket 前缀与预算。


## 9. 新 Agent 接手入口（2026-11-17）

- 权威交接任务书：`docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`。
- P2 来源补充决策与当前状态：`docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`。
- P2 Draft prompts 与 Manifest：`R60_P2_PUBLIC_STORY_PROMPTS_DRAFT_20261117.jsonl`、`R60_P2_PUBLIC_STORY_SOURCE_MANIFEST_DRAFT_20261117.json`（当前会话工件，需由 Owner 转存私有目录并冻结）。
- P2 结构门禁：`experiments/r58_quality/r60_base336_p2_public_prompt_package_gate.py`；测试：`tests/test_r60_base336_p2_public_prompt_package_gate.py`。
- 可直接复制的启动提示词：`docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261117_CN.md`。
- 接手时重新核验当前分支、HEAD、Actions、Issue/PR；本计划与交接文件内的 SHA/CI 都是快照，不得代替实时查询。
- 当前唯一业务阻塞是 P2 新独立 Held-out 来源/权利/上下文/World 隔离证据；Owner 未提供/批准来源前不创建正式测试包、不实现正式 Pairer、不推理。

## 9. 2026-11-18 共享 World 隔离核心与 Quality Pipeline 维护

为避免 Base336 / REAL1000 / 后续 Quality-v1 批次各自实现一套 split-conflict 算法，新增共享纯函数模块：

- `src/storyforge_dataset/world_isolation.py`：
  - `component_split_conflicts()`：只检查上游已审核赋值的 `world_component_id` 在指定 split 间是否冲突；不从 Story ID、JSONB 相等、MD5/SHA、标题、角色名或时间戳推断语义身份。
  - `validate_component_review_assignments()`：校验逐来源语义组件分配的字段、来源证据引用、版本核验声明、审核完成声明、唯一性、预期成员覆盖及 Train/Validation 冲突；只输出 SAFE 聚合，不输出私有 source/component key。
- `experiments/r58_quality/quality_v1.py` 已改为复用 `component_split_conflicts()`，原有六维 FLOORS、严重标记、Review 规则、候选结构与 `quality_v1_admitted=0` 行为保持不变。
- 新增 `tests/test_world_isolation.py`，覆盖跨 split 冲突、同 split 不冲突、缺失/非法赋值、审核字段/成员覆盖、非字符串决策、隐私输出及独立性边界。
- `.github/workflows/r60-real1000-quality-review.yml` 已纳入共享模块、`quality_v1.py` 及两组测试的 Ruff / pytest 范围；不能仅靠 Skill manifest 测试代表算法回归。
- 同步更新 `GOLD_QUALITY_PIPELINE_CN.md`、RolePlay Skill `0.1.19`、Real Quality Reviewer Skill、README、CHANGELOG 与 SAFE Manifest。

此共享 helper 仅校验结构化的语义组件分配声明；它不会把 8 个代表性 World JSON 自动判为模板，也不会代替成员级角色卡/Opening 人工审阅。当前 Base336 8 组仍全 HOLD。helper 的结构 PASS 不自动关闭历史 actual-sent、Reviewer 独立性、R50/R47/R48/R55、来源权利或 Owner 冻结门禁。

共享核心与 Quality-v1 集成代码提交 `471e2e4631405f53c74390a9eebd3732d9a6e95e` 的 GitHub Actions 已完成：`R60 REAL1000 Quality Reviewer (synthetic only)` run `44127200498` SUCCESS（Ruff 通过；离线合成回归 338 passed、2 subtests passed；RolePlay Skill manifest/reuse contract 7 passed）；`R60 Common2 Wrapped HF CPU (synthetic only)` run `44127200345` SUCCESS。随后质量标准文档提交 `5a773e14a5c63cd4808821d1dd6226ccd206ef14` 的 Actions run `44127458330` SUCCESS；当前最新 HEAD `f0e9349a8439393b2d5660ece965ac541611088a` 的 Actions run `44127961963` 也 SUCCESS。其间 `480b6fef76b07e1314eab048cf6b8d14a449cc86`、`fda3208b4298163ae6919d5c954161a8c2d9bf66`、`f0e9349a8439393b2d5660ece965ac541611088a` 均为文档状态同步，没有改变已测试的共享算法。中间版本曾因 Skill manifest 版本/哈希不同步和 Ruff 纳入不可执行历史脚本而失败，均已修正。

## 2026-11-18 Owner SAFE 更新：P2-A 公开来源 Inventory READY；P2-C 仍 HOLD

Owner 本轮真实 SAFE（由 Owner 提供）：

```json
{
  "authors": 5,
  "created_after_gpu_run": 5,
  "created_before_gpu_run": 3,
  "database_accessed": true,
  "database_modified": false,
  "distinct_world_json": 8,
  "exact_world_overlap_pre_cutoff_public_original": 0,
  "gpu_started": false,
  "hf_jobs_submitted": 0,
  "model_promoted": false,
  "model_requests": 0,
  "private_file_created": true,
  "private_values_emitted": false,
  "protected_crosswalk_verified": false,
  "quality_v1_admitted": 0,
  "revision_snapshot_permission_verified": true,
  "rights_scope_owner_confirmed_only": true,
  "schema": "storyforge_r60_base336_p2_public_source_inventory_safe_v1",
  "selected_stories": 8,
  "status": "P2_PUBLIC_SOURCE_INVENTORY_READY__PROTECTED_CROSSWALK_PENDING",
  "train_admitted": 0
}
```

### 证据解释

- P2-A Supabase 公开来源 inventory：READY，8 条来源已选定，revision / snapshot / permission 绑定已验证。
- 本次精确 World JSON 比较在指定的 GPU 前公开原创范围内为 0 overlap；这不是语义世界隔离证明，也不覆盖 Base336 私有来源、R50 Protected/Reserved、R47/R48/R55 暴露材料。
- 8 个不同 World JSON 不等于 8 个语义独立世界。
- 5 条创建于 GPU Run 后只代表数据库记录创建时间；不能单独证明其底层素材、版本或语义未提前暴露。
- 权利状态为 `rights_scope_owner_confirmed_only=true`，只代表 Owner 已确认的内部独立评估提示构造用途；不扩展为训练、再分发或公开用途授权。
- `private_file_created=true` 表示 Owner 私有来源 Manifest 已创建；私有 Manifest、source IDs、作者映射、正文和 SHA 不得上传 GitHub 或贴入聊天。

### P2-C 尚未完成的保护集交叉核验

必须将上述 8 个 P2 来源与以下保护范围进行精确及语义交叉核验：

1. Base336 冻结 Train/Validation 私有 source roster 和已审查的 World component evidence。
2. R50 完整 Protected/Reserved World **仅元数据**清单；不读取 R50 正文、提示、答案或密封材料。
3. R47/R48/R55 已暴露开发题及其语义变体的来源/暴露元数据。
4. 现有其他独立评测集及未解决保护集合；不得将部分保护清单称为完整覆盖。

当前可复用 Base336 Owner-local 证据目录为 `~/.local/share/storyforge/r60/private/r60-base336-world-cross-review-20261115/`，包含既有 8 组 cross-split roster、decision template、Codex review 和代表性 World source evidence；这些历史回执仍不能证明本轮 P2 8 个新来源已与保护集完成 crosswalk。成员级 card/opening 证据此前未确认存在。R50 旧有 pre-seal 证据曾显示完整排除与最终封存仍 HOLD；R47/R48/R55 全量语义变体排除材料也未形成可验证的完整 crosswalk。

### 当前禁止推断

- 不因 8/8 revision / snapshot / permission PASS 推断 P2-C PASS。
- 不因 exact overlap=0 推断语义隔离 PASS。
- 不因 Owner 确认评估用途推断训练授权。
- 不生成正式 48 条 Held-out prompt 包，不启动 Base/Adapter Pairing 或模型推理。
- 不改写 Quality-v1 六维门槛，不新增评分标准，不向 Gold Manifest 追加生成评估事件。

继续保持：`model_promoted=false`、`train_admitted=0`、`quality_v1_admitted=0`、GPU/HF/model requests = 0。

### 下一项最小动作

Owner 已返回 R47/R48/R55 的部分 metadata inventory；这些已确认文件不再重复盘点。下一步对三个 R55 私有 Coordinator Index 做只输出 Schema / 字段名 / 数量 / 版本绑定的结构审计，并寻找 Sample → Story ID 的权威来源映射。P2 Source Manifest、Base336 roster / member evidence、R50 完整 metadata-only roster 等其他保护集仍需按证据索引确认存在性与覆盖。不得 cat / grep 私有正文、上传文件或打印 ID / 正文 / 哈希；真实 Schema 和保护集覆盖确认前，不编造通用适配器或宣称 crosswalk 完成。


## 2026-11-18 下一 Agent 交接与 P2-C 执行冻结

当前 P2-A / P2-B / P2-C 状态以本计划上文 Owner SAFE 和以下专项材料为准：

- P2-A：Supabase 公开来源 Inventory READY（8 条来源；revision / snapshot / permission 绑定通过；指定范围精确 World overlap=0）。
- P2-C：**HOLD**。Base336 完整成员级语义证据、R50 完整 Protected/Reserved metadata-only 排除、R47/R48/R55 完整暴露与语义变体排除、历史 actual-sent 版本、Reviewer 独立性及 Owner 冻结尚未形成可复核闭环。
- P2-B：真实 48 条提示 JSONL / Manifest **NOT_GENERATED**；现有 9/9 是校验器合成测试，不是实际提示包。
- **历史截点说明（后续已更新）**：本节撰写时 Owner Mac 私有文件 metadata inventory 尚未收到；2026-11-18 后续已收到 R47/R48/R55 部分 metadata / shape inventory，详见本计划第 10 节。其他保护集文件仍需分别核验。

### 权威交接物料

1. 本计划：训练后质量评估总体门禁和 P0-P6 顺序。
2. `docs/R60_BASE336_POST_TRAIN_NEXT_AGENT_HANDOFF_20261117_CN.md`：权威任务书与历史事实。
3. `docs/R60_BASE336_NEXT_AGENT_START_PROMPT_20261117_CN.md`：总体启动提示词。
4. `docs/R60_BASE336_P2_CROSSWALK_NEXT_AGENT_PROMPT_20261118_CN.md`：当前专项可复制 Agent 提示词，规定第一步、禁止动作和交付格式。
5. `docs/plans/R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md`：现有工具、输入证据类型、证明边界和缺失项索引。
6. `docs/plans/R60_BASE336_SUPABASE_PUBLIC_STORY_P2_ADDENDUM_20261117_CN.md`：来源路线与 Owner SAFE 补充决策。

### 第一动作：Owner-local metadata inventory

新 Agent 先核对实时 GitHub HEAD / Actions。R47/R48/R55 的部分文件 metadata inventory 已收到；不要重复盘点这些已确认文件。下一步按本计划第 10 节对 R55 私有 Index 做只读 Schema / 覆盖 SAFE 检查，并寻找 Sample → Story ID 权威映射。对 P2 Source Manifest、Base336 与 R50 等其他未确认文件，仍只做文件名、大小、权限、修改时间盘点，不读取正文或输出 ID、作者映射、SHA256 和本机绝对路径。

此前 `r60_base336_group_cards_opening_cpu.py --execute` 只返回泛化 `BASE336_CARD_OPENING_EVIDENCE_HOLD`，没有失败阶段/原因。不得重跑全量 `--execute`，不得重跑 DB 查询，不得重建或覆盖 roster/template/evidence/review/output。先确认现有输出与 SAFE，再定位失败阶段；任何最小修复动作须由 Owner 重新确认。

真实文件 Schema 和保护集覆盖范围未确认前，不开发猜测性 crosswalk。输入齐备后，才设计版本化、Owner-local、create-only 薄适配器；复用 `src/storyforge_dataset/world_isolation.py`，不复制组件冲突算法。P2-C 全部通过并经独立 Reviewer / Owner 冻结之前，不生成正式 48 条提示包，不进入 P3/P4。

交接编写前 HEAD：`3db42078dd6ac7fd8c5815f55f3ded07aa58db21`。这只是文档更新前的 GitHub 快照；新 Agent 必须实时查询，不能将其视为接手时 HEAD 或 CI 结论。

永久保持：`database_modified=false`、`gpu_started=false`、`hf_jobs_submitted=0`、`model_requests=0`、`train_admitted=0`、`quality_v1_admitted=0`、`model_promoted=false`。


## 10. 2026-11-18 R47 / R48 / R55 历史暴露来源形态审计

Owner 已完成本机只读 metadata / shape audit。详细审计记录：[R60 P2 R47/R48/R55 Source Shape Audit](../evidence/R60_P2_R47_R48_R55_SOURCE_SHAPE_AUDIT_20261118_CN.md)；保护集总索引：[P2 Protected Crosswalk Evidence Index](R60_BASE336_P2_PROTECTED_CROSSWALK_EVIDENCE_INDEX_20261118_CN.md)。

### 审计结果

- **R47**：20-row Manifest 的元素字段为 sample_id、prompt_sha256、source_line；compiled Test 有 id/messages/metadata；prompts 只有 messages。现有 R47 校验器验证 Sample / Prompt / 三臂回复盲包的一致性，但未证明 sample_id 与 canonical Test 的 id 以及原始 Story ID 之间的逐案映射。
- **R48**：Source Audit 固定绑定 canonical compiled Test SHA、20 个 Gold target hashes、20 cases / 80 replies，并标记旧 Test exposed；R48 使用同一 R47 20-case Prompt 集，不增加独立案例数。它没有补出 Story ID crosswalk。
- **R55**：Owner metadata inventory 确认三个私有 Coordinator Index（0600）及两个 SAFE 文件存在；本轮只列举文件名、大小和权限，未读取 Index / SAFE 内容，故 Schema、版本、20-case 覆盖及 Story ID 绑定仍未验证。
- **不能推断**：JSONL 行序、source_line、通用 id 字段、不同 Prompt SHA 或不同文件大小均不能自动构成 Story ID 映射或语义独立证明。

### 与 P2 精确交叉结果的关系

此前 Owner SAFE 已确认 P2 × Base336 精确 Story ID overlap 为 0（336 cases / 172 unique stories），P2 × R50 exact Source ID disjoint；本轮结果不改变这两个已通过的限定范围。它们不覆盖 R47/R48/R55。

| 门禁 | 当前状态 |
|---|---|
| P2-A 公开来源 / revision / snapshot / permission | READY |
| P2 × Base336 精确 Story ID 隔离 | PASS（限定于冻结 Base336 身份清单） |
| P2 × R50 精确 Source ID 隔离 | PASS（限定于已有 SAFE 的 Source ID 范围；R50 正文未读取） |
| P2 × R47/R48/R55 精确 Story ID 隔离 | UNKNOWN / HOLD |
| Base336 World 语义隔离、成员级证据及 actual-sent | HOLD / UNKNOWN |
| R47/R48/R55 语义变体排除与完整暴露覆盖 | HOLD |
| P2-B 真实 48 条提示 JSONL / Manifest | NOT_GENERATED |
| P2-C 总门禁 | **HOLD** |

### 下一项最小动作

1. Owner-local 只读检查 R55 三个私有 Coordinator Index 的真实 Schema、元素字段、记录数、版本 / receipt 绑定和 R47 Sample Manifest 覆盖数量；只输出 SAFE 计数，不输出 ID、正文、引文或哈希。
2. 查找 compiled_test.id、R47 sample_id 到 canonical Story ID 的权威映射文件或原始来源证明。若不存在，P2 × R47/R48/R55 精确身份门禁继续 HOLD。
3. 完整暴露覆盖和 source-bound 语义变体审查必须独立完成；actual-sent 版本缺证时保持 UNKNOWN / HOLD。

本次只做文档和证据边界整理；不访问数据库、不修改数据、不启动 GPU / HF Job、不发起模型请求、不读取 R50 正文，不生成正式提示包。维持 train_admitted=0、quality_v1_admitted=0、model_promoted=false。


## 2026-11-18 R47 / R48 / R55 crosswalk code-path refinement

进一步核对仓库代码后，前述“没有 Sample → Story ID 映射路径”的判断需要修正：

- R47 的 \`sample_id\` 可通过 Manifest 的 \`source_line\` / \`prompt_sha256\`，与 canonical compiled Test 对应行的完整 role/content prompt prefix 绑定；该行 \`metadata.story_id\` 才是 Story ID 来源，不能把通用 \`id\` 字段直接当作 Story ID。
- \`scripts/prepare_blind_eval.py\` 生成确定性 Sample ID；\`scripts/audit_v01_integrity.py\` 检查 Test 记录的 \`metadata.story_id\`，并逐案验证 Test / Prompt / Manifest 的前缀、哈希和 source_line；\`scripts/v02_r48_four_arm_build.py\` 固定 canonical Test SHA 并核对完整 prompt prefix。
- R48 复用同一 20 个 R47 prompts 和 canonical Test，不新增独立案例；其精确身份映射应继承 R47 crosswalk。
- R55 第一层 arbitration Index 保存 \`source_sample_id_private\`；第二层通过 \`original_candidate_token_private\` 回连第一层；第三层通过 \`original_second_candidate_token_private\` 与 \`original_first_candidate_token_private\` 回连第二层和第一层。

**代码路径 FOUND，但 Owner-local SAFE 尚未执行。** 下一步：对 R47 Manifest / prompts / canonical Test / R48 Source Audit / P2 private Manifest 做只输出计数的 exact Story ID crosswalk；再核验 R55 三层 Index 的真实 Schema、token 链、20-case 覆盖、各层 SAFE receipt 哈希绑定，以及 \`R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json\` 对 R55 原始案例与 R47 来源的证明。实际 overlap 结果未出前继续 UNKNOWN / HOLD；语义变体排除仍 HOLD。
