# R60 真实优质历史数据 SFT 主线与任务优先级（2026-11-08）

> **交接包最终索引（2026-11-09）**：[R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md](R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md)。当前 ChatGPT 工作范围为交接材料准备；Gold72 私有 P0 重建/冻结交由新 Agent，不在本轮执行。

> **交接证据状态补充（2026-11-08）**：Pilot10 Owner Pairwise SAFE 已收到：A/B 各 5 条、matched=0、unique=10、Checkpoint receipt/input SHA 10/10 验证通过；同一 SAFE 还证明 A/B 两槽各 1000/1000 source crosswalk、输入 SHA 与跨槽来源绑定通过。R60 来源映射子项已 PASS，不应重跑。Gold72 的 C packets/results-only SAFE 与 Owner worksheet/aggregate SAFE 已存在（Owner=30/4/6、历史 C=38/1/1、A/B disagreement=40/72），但 C execution record unavailable，且独立 40-case A/B source manifest/crosswalk 尚未证明；Gold72 40 条冻结及 Gold72↔R60 跨集去重仍待完成，因此 P0 整体 OPEN。R58→R60 Jinja2/Chat Template 故障复发工程门禁已落实。PR #25 在已验证 commit `32c4965d18ef98cacc25f14de86b8ce824fb0bb5` 的五项 GitHub Actions 均 SUCCESS。

> **2026-11-08 P0.5 工程门禁落实（不代表 HF Job 已执行）**：R60 Reviewer 独立依赖 profile `requirements/hf-quality-reviewer.in` + `requirements/hf-quality-reviewer.lock` 已提交，锁定 Transformers 4.57.1、SentencePiece 0.2.1、Jinja2 3.1.6，含 729 个 SHA256 包哈希；与 R59 Qwen3.8 的 Transformers 5.16.1 profile 分开。GitHub Actions Run `42495819470` 在 commit `32c4965d18ef98cacc25f14de86b8ce824fb0bb5` 验证 lock 重解析、hash 安装、`pip check`、合成 `apply_chat_template` 全部 PASS。R60 CPU Runbook 已改为将 lock 只读加入 A/B 输入、远端校验 lock SHA 后安装。**尚未在 Owner Mac 执行新的 lock staging/上传，也未提交新的 HF Job；不能将 CI smoke 描述为真实模型 Tokenizer PASS。** R59 原 profile 未降级。

> **新 Agent 交接与执行任务书（2026-11-08）**：下一阶段由 [交接总览](R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md) 和 [可执行任务书](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md) 作为接手入口，按 P0 校准集只读库存/分轨/去重/冻结 → P1 三态严重证据规则 → P2 Owner 盲裁决 → P3 三模型配置 → P4 30 条严格配对 → P5 回归验收 → P6 1000 条批量审核执行。按用户明确指示，本阶段不重新探讨权利/协议问题；不改 RolePlay、不读取 R50 正文、不覆盖旧 A/B/C、不访问全库正文。当前无 GPU 授权。

> **下一阶段执行基线已整理（2026-11-08）**：统一按 [R60 下一阶段校准与三模型配对评估计划](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md) 推进。顺序为 Gold72 40 条与 R60 10 条分轨冻结 → 三项严重问题三态证据标准 → Owner 独立参考裁决 → 修复 Qwen3 Thinking/采样配置并保留 GLM-4、评估 GLM-Z1 challenger → 30 条相同案例三模型盲审 → 回归验收 → 1,000 条正式批量审核。当前不启动 GPU；Quality-v1 admitted=0、training_authorized=false。旧 A/B/C Checkpoint 保持不变。

> **2026-11-08 Reviewer C 10/10 已执行、Owner 对账通过；严重度仲裁 HOLD（最新）**：Owner 回传 SAFE `C_CODEX_RESULTS_READY__RECONCILIATION_PENDING` + `C_BLIND_SEMANTIC_RECONCILED__QUALITY_HOLD`。本机 Codex CLI 10 条独立新会话均完成，blind inputs only；本地执行回执、C/原始来源与结果绑定通过。模型身份独立验证仍 false，回执仅为 `OWNER_LOCAL_CODEX_RECEIPTS_NOT_REMOTE_ATTESTATION`。三维对照：`hard_rule` C 10/10 `NOT_SUPPORTED`，原模型 4 条严重标记为 true；`player_agency` 原模型 10/10 true，C `SUPPORTED=3 / NOT_SUPPORTED=7`；`safety` C `SUPPORTED=5 / NOT_SUPPORTED=1 / INSUFFICIENT_CONTEXT=4`。说明原模型严重标记存在显著误报/不确定风险，但 C 结果不是自动真值；接下来仅做这 10 条证据级语义仲裁，不扩样、不跑 GPU。`semantic_severity_adjudication_complete=false`、`quality_v1_admitted=0`、`training_authorized=false` 均保持。执行与 SAFE 见 [Reviewer C 校准报告](R60_HF_PILOT10_C_BLIND_SEMANTIC_REVIEW_20261108_CN.md)。
> **2026-11-08 Owner 原始映射和摘要审计 PASS；转入独立 Reviewer C 盲语义校准（当前最新）**：Owner 实际运行 `hf_pilot_pairwise_audit` 的聚合 SAFE 为 `OWNER_PAIRWISE_AUDIT_COMPLETE__SEMANTIC_HOLD`：`owner_manifest_receipt_verified=true`、`input_hash_and_cross_slot_binding_verified=true`、A/B 冻结各 1000 source 绑定通过、A v2 五份及 B v3 五份 `receipt_sha256/input_sha256` **10/10 完整重算通过**，`matched_cases=0`、`unique_source_cases_in_pilot=10`。因此两槽的 5/5 REJECT 不等于逐案例“双模型一致”。严重 `serious_player_agency=true` 与 `player_agency>=4` 同时发生的 A 为 1 条、B 为 2 条，先核查语义而非批量淘汰。已固化 [Owner PASS SAFE](evidence/R60_HF_PILOT10_OWNER_PAIRWISE_AUDIT_PASS_SAFE_20261108.json) 和开发**无新增 GPU 的第三方 C 盲包流程** `src/storyforge_gold_quality/hf_pilot_semantic_c.py`：从 Owner 现有完整冻结源与 10 个经过摘要重验的 Checkpoint 中生成 10 条独立乱序的 C 私有输入，不向 C 提供 A/B 评分或严重标记；生成私有 Owner 映射和 C 三维（玩家代理/硬规则/安全）严格引用的校验器；即使 C 完成，准入仍须额外独立执行证据与严格语义裁定。用 [单命令 Owner C 盲包脚本](../scripts/r60_hf_pilot10_semantic_c_prepare.sh) 在本机准备，不自动调用任何模型、不修改旧 A/B。**C 盲包尚未在 Owner Mac 实际生成，C 尚未审核；Quality-v1 admitted=0，SFT 未授权**。执行详见 [C 校准文档](R60_HF_PILOT10_C_BLIND_SEMANTIC_REVIEW_20261108_CN.md)。

> **2026-11-08 A/B 两组首五条真正交集为 0，质量校准开始落实（最新）**：对冻结 A 前五条与 B 前五条做 25 组 `target_text + visible_history + target_semantics` 全文严格比较，**相同来源 0 组**。之前的 A `5/5 REJECT` 与 B `5/5 REJECT` 仅是两份不同案例的模型分布，不构成逐案双模型共识。已对 10 条进行明确标为非盲/非独立的事后 AI 严重标记分层：4 条 `UNSUPPORTED_SEVERE_SUSPECTED`、4 条 `CONTEXTUAL_AMBIGUITY_HOLD`、2 条 `SAFETY_POLICY_HOLD`；所有类别仅为待核证线索，不更改原模型 REJECT、不能当作最终 PASS/REJECT，Quality-v1 admitted 仍为 0。见 [SAFE 证据](evidence/R60_HF_PILOT10_POSTHOC_SEVERE_CALIBRATION_SAFE_20261108.json)。已编写并经过全套 CI 合成测试的 Owner-only `src/storyforge_gold_quality/hf_pilot_pairwise_audit.py`，验证冻结源的 1000/1000 A/B owner crosswalk、source/manifest SHA、两个槽共 10 个 Checkpoint receipt/input SHA 后仅输出聚合 SAFE；配备 [单命令脚本](../scripts/r60_hf_pilot10_owner_audit.sh)，Owner Mac 本地无需 GPU 执行，自动寻找唯一匹配 stage 并私有下载 10 个 checkpoint，执行说明 [R60 Owner Pairwise & Calibration](R60_HF_PILOT10_OWNER_PAIRWISE_AND_CALIBRATION_20261108_CN.md)。**脚本尚未实际在 Owner Mac 上运行，不能声称完整 Owner crosswalk 审计通过**。先拿到本地 SAFE 核验，再独立语义裁定严重标记，停止新增 GPU 或数据淘汰；正式 SFT 仍未授权。

> **2026-11-08 B v3 严重分类校准反例（新增）**：在 B v3 五条 Checkpoint 中抽查位置 5 的原始可见历史/目标及评分，发现模型 `decision=REJECT`，`hard_fact_or_ban=true`、`safety_exclusion=true`、`serious_player_agency=true` 三项均真，但源内容是普通互动，未发现可见硬规则违反、明确严重玩家动作越权或安全排除依据；模型六维得分均在准入最低线（4/4/3/4/4/4），文学说明偏正面。**这构成具体的误报嫌疑，而不只是“10 条全 REJECT 比例很高”**。当前只是单例目标性检查，不是盲审仲裁，不得外推总体误报率或直接把这条改为 PASS；应先私下语义复核，明确“NPC 自身主导、表达、威胁”不必然等于“AI 代替玩家作选择”。SAFE 事实见 [R60 B v3 严重标记抽查](evidence/R60_GPU_B_V3_SEMANTIC_FLAG_SPOTCHECK_SAFE_20261108.json)。A/B 技术 Pilot 已完成；仍须 Owner 私有 crosswalk 绑定才可形成两模型逐案例结论，Quality-v1 admitted=0，SFT 未授权。

> **2026-11-08 B v3 H200 首次完整五条评审成功；技术 Pilot 已完成，严重标记仍待语义校准（最新）**：HF B [`6af060700e0338d1bb84b025`](https://huggingface.co/jobs/adradar/6af060700e0338d1bb84b025) 最终 `COMPLETED`，GLM-4-32B 固定 revision 的 14/14 权重已加载；真实 `quote_repair_attempts=1`、`quote_repair_successes=1`，5/5 私有 v3 Checkpoint、`HF_REVIEW_PARTIAL__NO_ADMISSION`、B `PASS=0/HOLD=0/REJECT=5`。已逐条对照 B 冻结源核查 `blind_id` 和 source/target 引用严格子串 5/5 PASS，未独立重算摘要。此前 A Qwen v2 同样 5/5 REJECT；两侧各 `serious_player_agency=true` 5/5，但**不能按编号对应或汇总同值推断两个模型在同一故事上的共识**。因共用审核标准可能导致系统性误判，先 Owner 私有 crosswalk 绑定 5+5 的真实来源与案例，再对“严重侵犯玩家自主权”进行独立语义裁定；任何争议 HOLD，不能把全部 REJECT 当成真实质量淘汰。技术 Pilot A/B 已完成，不再重复 Tokenizer 或 H200 小样本；全量 1000 条、正式 Quality-v1 admitted 与 SFT 仍未授权。公开 SAFE [B v3 结果](evidence/R60_GPU_B_V3_PILOT5_COMPLETED_SAFE_20261108.json)，执行基线 [5+5 Runbook](R60_HF_GPU_REVIEW_PILOT5_AB_20261108_CN.md)。

> **2026-11-08 B H200 v2 引用校验 HOLD；v3 可复用 R58 单次纠错代码已开发（最新状态）**：真实 [B Job `6af05bbf0e0338d1bb84ad9f`](https://huggingface.co/jobs/adradar/6af05bbf0e0338d1bb84ad9f) 完成 GLM-4-32B `14/14` 权重加载与 GPU 推理，但返回 `HF_REVIEW_HOLD / MODEL_NONEXACT_QUOTE_HOLD`、Job **ERROR exit42**，没有写出 B 的有效 checkpoint；A v2 5/5 Checkpoint 已完成但全部 severe player-agency REJECT，尚不能语义裁定或训练准入。利用已验证的 R58 Batch Quote Repair 原则在代码中实现 R60 Reviewer **v3**：一次性收集全部无效引用位置、从可见历史或目标截取≤128精确候选，最多一次 Index-only 受约束纠错，不重判评分/严重标记，重验所有严格引用；任何不符 HOLD，私有数据不进 SAFE 日志。Checkpoint v3 独立拒绝 v2，已有 A、B v2 文件不得修改。新增合成测试、四项 GitHub CI 通过。此 v3 **尚未在 HF 部署或 CPU/GPU 执行**，下一步 Owner Mac 只上传新版公开 Runner 至 `reviewer-runner-v3/runner.py`，接着 B v3 CPU-only Tokenizer 检查；之后才在追加预算审批下提交 B 前 5 条单次 H200。参见 [执行基线](R60_HF_GPU_REVIEW_PILOT5_AB_20261108_CN.md) 与 [失败 SAFE](evidence/R60_GPU_B_V2_PILOT5_NONEXACT_QUOTE_HOLD_SAFE_20261108.json)。不重跑 A、不扩样、不训练。

> **2026-11-08 Reviewer B v2 同镜像真实 CPU Tokenizer 完成（当前最新）**：HF [Job `6af059c4e6320c66fad74722`](https://huggingface.co/jobs/adradar/6af059c4e6320c66fad74722)，`cpu-basic` 固定 vLLM digest，终态 **COMPLETED**，`HF_CPU_RESOURCE_GUARD_PASS`、`HF_REVIEWER_V2_CONTRACT_PASS`，GLM-4-32B-0414 新版 Prompt 1000/1000 Tokenizer `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`，`over_budget_count=0`，max_total_tokens=6006。公开 [B v2 SAFE](evidence/R60_GPUIMAGE_B_REVIEWER_V2_CPU1000_PASS_SAFE_20261108.json)。至此 **A/B 两组 v2 同 GPU 镜像 CPU 预检全部通过**，不再重复 CPU 工作。A 的 5 条 H200 Pilot 已 COMPLETED，模型 5/5 REJECT、`serious_player_agency=true` 5/5，需独立 B 盲审语义校准；**B H200 新 GPU Job 尚未提交，新 B 输出尚不存在**。下一步按最小范围在 Owner Mac 只提交一次 B v2 前 5 条 H200 独立评审，并在两槽完成后按私有 Owner crosswalk 比对，不假定 A/B 文件序号或 blind_id 天然配对。无独立质量判定，`quality_v1_admitted=0`，SFT 不授权。

> **2026-11-08 A H200 v2 真实 5 条技术 Pilot 成功完成、质量结论独立校准 HOLD（最新权威进度）**：HF [Job `6af056bb0e0338d1bb84ac8a`](https://huggingface.co/jobs/adradar/6af056bb0e0338d1bb84ac8a) 终态 **COMPLETED**，已写入 5 个独立私有 v2 Checkpoint，SAFE `HF_REVIEW_PARTIAL__NO_ADMISSION`（5/1000，按计划只评前五条，不是 Job ERROR），A 单模型给出 `PASS=0,HOLD=0,REJECT=5`。已对照冻结输入前五条，安全核验 blind identity 5/5 匹配、source/target 引用均原文逐字子串 5/5；尚未独立复算 SHA256。**重大质量风险：五条均 `serious_player_agency=true`，不能仅凭模型严重标记和引用存在就证明真实玩家自主权被侵犯或可直接淘汰数据**。先保持质量判定的语义校准 HOLD，Quality-v1 admitted=0，不重复 A；接下来 B 固定 vLLM 镜像用已部署 v2 Runner 做 CPU Tokenizer，然后只对 B 前五条做独立 H200 盲审，并在私有 Owner crosswalk 下配对/冲突仲裁，先得到合格真实历史来源候选再规划 SFT。公开 [SAFE 证据](evidence/R60_GPU_A_V2_PILOT5_COMPLETED_SAFE_20261108.json)；B GPU 未启动、全量审核未启动、SFT 未授权。

> **2026-11-08 Reviewer A v2 实际 CPU preflight 通过（最新进度）**：`adradar` [HF Job `6af055ace6320c66fad7456d`](https://huggingface.co/jobs/adradar/6af055ace6320c66fad7456d)，固定 vLLM GPU 镜像下 `cpu-basic`，实际终态 **COMPLETED**。资源 Guard `RESOURCE_AFTER=PASS`，公开新版代码 `HF_REVIEWER_V2_CONTRACT_PASS`、冻结 1000 条输入 `HF_REVIEW_INPUT_VERIFIED__NO_INFERENCE`；新版 Prompt 真实 Tokenizer `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`，`cases_checked=1000`、`over_budget_count=0`，prompt min/median/p95/max=`769/1205/2341/3181`、max total `5581`。公开证据 [R60_GPUIMAGE_A_REVIEWER_V2_CPU1000_PASS_SAFE_20261108.json](evidence/R60_GPUIMAGE_A_REVIEWER_V2_CPU1000_PASS_SAFE_20261108.json)。可在**新的独立**私有输出 `gpu-review-output-A-pilot5-v2-01` 上申请执行 A H200 5 条文学审查（固定 vLLM digest / Qwen revision / `--start 1 --limit 5` / `--confirm-paid-gpu`，35m 单次 Job），而非反复 CPU 排障。原 Pilot v1 Checkpoint 单独留存，不得复用；B H200、全量 1000 条和 SFT 均不自动启动，Quality-v1 admitted 仍为 0。

> **2026-11-08 R60 首次 A H200 文学审核有真实结果但 Pilot HOLD（最新）**：真实 [`r60-quality-gpu-pilot5-A-01` Job `6af051150e0338d1bb84aad1`](https://huggingface.co/jobs/adradar/6af051150e0338d1bb84aad1) 已成功加载 Qwen3-32B 全部 `17/17` 权重分片，随后实际生成并通过旧版校验写入首例私有 `review_0001.private.json`；下一个输出在旧版理由长度/类型校验处返回 `HF_REVIEW_HOLD / MODEL_REASON_HOLD`，Job 终态 ERROR exit42。首例模型决策为 `REJECT`、严重标记 3/3 true，但 **source/target 引用均为 0**。因为旧审核契约只要求 PASS 引用，这个 REJECT 缺乏可核实依据，不能提升为 Quality-v1 实质淘汰或训练准入。旧原始私有 Checkpoint 必须保留。新增更细 SAFE 子码及严重 REJECT 的引用闸门，Checkpoint v2 将拒绝复用旧 v1，合成测试在 GitHub；**新版尚未进入 HF Stage 或产生新的审核结果**。参见 [A Pilot 实际 SAFE 证据](evidence/R60_GPU_REVIEW_A_PILOT5_FIRST_RUN_SAFE_20261108.json) 与 [后续执行基线](R60_HF_GPU_REVIEW_PILOT5_AB_20261108_CN.md)。B H200 尚未启动、5+5 Pilot 未通过、全量质量审核/训练仍 HOLD，须在代码回归与预检通过后重新安排**明确批准的**最小 GPU 重评。

> **2026-11-08 A/B 固定 vLLM 镜像 CPU Tokenizer 全部完成（当前主线状态）**：A `6af04eb10e0338d1bb84a9e1` 与 B `6af04fda0e0338d1bb84aa61` 均 HF **COMPLETED**，在精确固定 vLLM GPU 镜像下 `ResourceGuard=PASS`，各自 1000/1000 Tokenizer `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`，各自 `over_budget_count=0`；B 的最大输入+预留为 `5950`，A 为 `5524`。复发资源问题定因为 CPU-basic 容器 GPU 镜像继承的 `NVIDIA_VISIBLE_DEVICES` 默认非 CPU 可见性，实际 GPU 设备节点检查均 PASS；仅在 CPU-only 的真实无设备前提下设置 `NVIDIA_VISIBLE_DEVICES=void` 并完整复查，绝不放宽资源 Guard。公开 [A SAFE](evidence/R60_GPUIMAGE_A_CPU1000_ENVFIX_PASS_SAFE_20261108.json)、[B SAFE](evidence/R60_GPUIMAGE_B_CPU1000_ENVFIX_PASS_SAFE_20261108.json)。**下一主线：真实 A/B 5+5 H200 文学盲审 Pilot**（优先 A 单槽，核验后 B），私有 checkpoint、严格引用/身份检查；GPU Pilot 仍未发生，文学评分 0、Quality-v1 admitted=0、SFT 禁止。

> **2026-11-08 A 同 GPU 镜像 CPU Tokenizer 真实完成（最新状态）**：A [Job `6af04eb10e0338d1bb84a9e1`](https://huggingface.co/jobs/adradar/6af04eb10e0338d1bb84a9e1) 已 `COMPLETED`，定位此前固定 vLLM 镜像 CPU ResourceGuard HOLD 的唯一失败项为 `nvidia_visibility`，其余四项全部 PASS（包括 NVIDIA 设备节点不可见、无 CUDA 模块导入）；在 `cpu-basic` shell 中将 `NVIDIA_VISIBLE_DEVICES=void`，ResourceGuard 完整复查全部 PASS。随后该固定 GPU 镜像上 A **1000/1000 Tokenizer PASS**、over budget=0、max_total_tokens=5524，`gpu_started=false`，公开 [SAFE](evidence/R60_GPUIMAGE_A_CPU1000_ENVFIX_PASS_SAFE_20261108.json)。B 同镜像检查仍需按同一流程在**新**独立输出完成，不能把 A 推及 B；H200 GPU 文学评分尚未启动，Quality-v1 admission=0、SFT 未授权。原故障历史仍保留。

> **2026-11-08 A/B GPU 镜像 CPU 检查真实失败（新状态）**：Owner 已启动同一固定 vLLM 镜像的两槽 `cpu-basic` 检查，A `6af04c570e0338d1bb84a91e` / B `6af04c58e6320c66fad7416c` 都是 **ERROR / exit 42**。依赖导入已通过，代码 `ResourceGuard.check_cpu_only()` 拦截并给出 `HF_CPU_RESOURCE_GUARD_HOLD`，尚未进入 Tokenizer，**不能把这个结果当成新 Tokenizer 失败或 Quality REJECT**。标准 CPU 镜像中的 A/B 1000/1000 Tokenizer PASS 仍有效。分析表明 GPU 基础镜像可能设置非 CPU 的 `NVIDIA_VISIBLE_DEVICES`，但具体子原因尚待 SAFE checks 证实；优先对 A 在新独立输出执行 CPU-only 资源诊断并严格保留 GPU 设备节点、ACCELERATOR 检查，只有 A 通过后才 B。**GPU 推理任务仍 0、文学评分 0、SFT 未启动**；详见 [R60 5+5 Reviewer Pilot](R60_HF_GPU_REVIEW_PILOT5_AB_20261108_CN.md)。

> **2026-11-08 5+5 GPU Reviewer Pilot 下一闸门（最新状态）**：基于 A/B 两槽真实 HF CPU1000 Token PASS，开始准备 A/B 各前 5 条文学质量审核（只读冻结输入、私有新输出、H200 固定 vLLM digest、35m/槽），**不启动 SFT 或全量 1000**。由于 R58 已证实固定 vLLM 镜像与原 CPU Tokenizer 镜像的 Transformers 版本不完全一致，必须先在精确 GPU 镜像的 `cpu-basic` 上对原 A/B 输入执行 Tokenizer 同镜像核验。ChatGPT HF 连接器尝试提交**仅 A 的 CPU-only 同镜像检查**时被 HF 拒绝 `403 Forbidden`，未拿到 Job ID，组织只读 Job 列表无对应名称。故**目前 5+5 GPU Job 尚未启动、同镜像 CPU PASS 未达成、文学评分仍为零**；改走已经核验的 Owner Mac `hf 2.4.0` 路径，绝不 fallback 个人命名空间或直接跳 GPU。精准命令、范围、预算及验收见 [R60 GPU Reviewer Pilot 5+5](R60_HF_GPU_REVIEW_PILOT5_AB_20261108_CN.md)。

> **最新真实 HF 双槽 CPU 预检完成（2026-11-08，覆盖下面所有“B 尚未启动”旧状态）**：A [Job `6af045fb0e0338d1bb84a4ce`](https://huggingface.co/jobs/adradar/6af045fb0e0338d1bb84a4ce) 与 B [Job `6af047a70e0338d1bb84a5ed`](https://huggingface.co/jobs/adradar/6af047a70e0338d1bb84a5ed) 均已独立只读核验 **HF `COMPLETED` 且 `HF_REVIEW_CPU_TOKEN_PREFLIGHT_PASS__NO_GPU`**。冻结 A/B 各 1000/1000，均 `over_budget_count=0`，预算 `32768` / 输出预留 `2400`。A prompt token min/median/p95/max=`712/1148/2284/3124`，最大输入+预留 `5524`；B=`673/1099/2306/3550`，最大输入+预留 `5950`。均通过固定模型 Revision、依赖 `jinja2==3.1.6`、`sentencepiece==0.2.1`、`transformers==4.57.1`、`pip check` 与公开合成模板 smoke。公开证据：[A SAFE](evidence/R60_HF_A_CPU1000_JINJA_FIX_PASS_SAFE_20261108.json)、[B SAFE](evidence/R60_HF_B_CPU1000_TOKEN_PREFLIGHT_PASS_SAFE_20261108.json)。**新的当前阻塞点已从 CPU 环境/Token 检查切换至真实模型文学双盲审核。** 暂无 A/B 模型文学评分、双盲配对、Quality-v1 训练准入；`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。不得将 Tokenizer PASS 描述为 Quality PASS，也不因先前 1000 HOLD 误称样本质量不合格。下一步需独立制定/核准最小 GPU reviewer Pilot，核验模型容器、5+5 Pilot、输出隐私与评价契约，再按质量闸门扩大；**未授权不得启动 GPU**。

> **最新真实云端结果（2026-11-08，覆盖下面旧的 A CPU 故障待处理说明）**：HF 组织 `adradar` 的 [A Jinja 修复 Job `6af045fb0e0338d1bb84a4ce`](https://huggingface.co/jobs/adradar/6af045fb0e0338d1bb84a4ce) 终态 **COMPLETED**，运行时间 `09:50:51–09:51:29 UTC`。依赖 `jinja2==3.1.6` + `sentencepiece==0.2.1` 导入、`pip check`、公开合成模板 smoke、1000 条输入合同均 PASS；固定 `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137` 的 **1000/1000 CPU Tokenizer PASS**，预算 `32768`、保留输出 `2400`、`prompt_tokens_min/median/p95/max=712/1148/2284/3124`、最大总计 `5524`、`over_budget_count=0`；`gpu_started=false`。证据已固化到 [`docs/evidence/R60_HF_A_CPU1000_JINJA_FIX_PASS_SAFE_20261108.json`](evidence/R60_HF_A_CPU1000_JINJA_FIX_PASS_SAFE_20261108.json)。**只代表 A 的 Tokenizer/输入合同，不代表文学评分、B CPU 预检、Quality-v1 准入或 GPU 训练；这些继续保持 HOLD / 0。** 先完成 B 相同版本的环境/Token 预检，再安排已批准范围内的最小 Reviewer 推理和双盲配对，不重复筛选或改写冻结输入。

> **2026-11-08 CPU 故障修正（最高优先级）**：Owner 运行 A 的 CPU Guard 后获得 `SUBMISSION_REJECTED/HF_JOB_SUBMISSION_FAILED`，但组织 HF Job 列表证实 Job `6af033d10e0338d1bb84941e` 已于 08:33:21Z 成功创建，08:33:55Z 以远程退出码 42 失败；日志含 `HF_REVIEW_HOLD / HF_REVIEW_RUNTIME_ERROR`，故是远程 Worker 运行失败，**不是提交失败、不是质量审核 REJECT**。原 `hf jobs run` 因默认跟随日志而误归类，现 Guard 改用 `--detach`，Worker 提供安全失败阶段码。**暂停 B 与原 A 自动重试**；按 [A CPU 故障诊断说明](R60_HF_CPU_JOB_A_FAILURE_DIAGNOSTIC_20261108_CN.md) 使用隔离的新 Runner 代码目录，保持原冻结 A/B Stage 和 Bucket 输入原样，先 dry-run 验证再单次 CPU 诊断（需 Owner 确认）。截至此回执未执行任何真实文学评分，Quality/Train PASS=0，GPU 未启动。

> **2026-11-08 Owner Mac 实测 Stage 通过**：实际 `prepare` = `HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED`（1000 候选、2 Slot、Owner crosswalk 未上传）；实际 `audit` = `HF_QUALITY_DUAL_PARTIAL__NO_ADMISSION`（A=0、B=0、complete_pairs=0、1000 HOLD，Quality PASS=0、训练准入=0），两 Reviewer 固定 A Qwen3-32B @ `9216db5781bf21249d130ec9da846c4624c16137`、B GLM-4-32B-0414 @ `077b5c2f5c43bd3239fd605a0600229e8facbd4a`。
> **最新 P0 下一步是 HF CPU 模型 Tokenizer/Chat Template 真正预检**，依照 [受控执行书](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md) 只上传两个私有 A/B 输入到 `hf://buckets/adradar/storyforge-training` 下独立 RO 前缀，借由已有 `scripts/hf_job_guard.py` 做 CPU Job 规格检验和必要的受控 CPU 提交；绝不可上传 Owner crosswalk 或整个 Stage。直接 `-v 本地目录` 隐式同步到 `jobs-artifacts` 的过时示例不再作为执行标准。未实际上传 HF 私有正文，CPU/GPU 尚未提交。GPU 推理/训练另行授权。

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

## 2026-11-12 主线状态：真实1000质量精筛准备

Owner 已批准按“先5条校准→再25条→分批扩展剩余970条”的方案推进。**当前完成的是启动流程与PILOT-0只读准备，不是任何真实5条模型评分成功回执。** 正式执行基线：[`R60_REAL1000_PILOT5_START_20261112_CN.md`](R60_REAL1000_PILOT5_START_20261112_CN.md)。

- 冻结1000池为6 seed + 994增量，禁止重扩样；复用现有`r60_real_quality_batch.py`的`init / advance / inspect`。两个Reviewer必须核实身份、独立无结论共享；远端API私有正文外发必须单独确认范围；默认不增加`--owner-attest-independent-ai`，避免虚假独立性声明。
- 首批5条只能从同一冻结1000池进入**相同来源**双模型审核；回执私有0600且create-only。严格六维(4/4/3/4/4/4)、严重标记及证据语义复核，所有上下文无法证实之处保持HOLD。不要复用旧A/B的两个不同5条样本做配对结论。
- 已独立验收的Common2包装System 2/2真实Swift Collator仅关闭**技术门禁**，不代表1000条已经文学精筛，更不能授予Train Admission。
- 较早校准阶段的“不得启动1000条审核”是当时执行范围；现在仅解锁当前5条的准备与只读预检。不自动授权第三方API外发、不运行批量25/1000模型调用、不改旧Gold/不访问R50正文、不启动训练GPU，`train_admitted=quality_v1_admitted=0`。
- 本线限定`r60/common2-cpu2-owner`隔离分支，其他Agent各自负责的Qwen/GLM/R60并行评审工件仍只读，不跨分支合并未核验修改。
