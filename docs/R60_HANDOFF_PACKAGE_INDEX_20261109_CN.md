# StoryForge R60 交接包索引与完成清单

更新日期：2026-11-09（当前状态校正）  
仓库：`sunxu/storyforge`  
交接分支：`r60/gold192-history-v3-adapter`  
PR：[#25](https://github.com/sunxu/storyforge/pull/25)（Open / Draft）  
主线 Issue：[#26](https://github.com/sunxu/storyforge/issues/26)  
交接与下一阶段执行 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)

## 1. 交接包的目的与边界

本交接包的目标是让下一位 Agent 无需翻阅数百轮聊天记录，即可准确了解 R60 的历史执行、证据状态、可复用实现、已知故障、未完成事项和下一步执行方法。

**本索引最初记录的是交接材料准备阶段。此后 Owner Mac 已正式完成 P0 冻结，P1 Rubric v2.1 与工程 CI 也已通过。当前接手状态以本索引末尾“当前有效状态”及主任务书 8.25 为准。** Quality-v1 admission 仍为 0，training_authorized=false。

## 2. 必读文件顺序

| 顺序 | 文件 | 用途 | 交接状态 |
|---|---|---|---|
| 1 | [新 Agent 交接任务书](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md) | 下一 Agent 的正式工作指令：目标、当前事实、P0–P6、授权门槛、完成定义 | 已完成 |
| 2 | [新 Agent 交接总览](R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md) | 项目状态、证据事实、边界、代码资产、模型缺口、接手入口 | 已完成 |
| 3 | [详细执行任务书](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md) | P0–P6 的执行顺序、命令、输入、产物和验收标准 | 已完成 |
| 4 | [三模型校准计划](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md) | Gold72/R60 校准集、三模型配对设计和选型目标 | 已存在，作为上位计划 |
| 5 | [R60 真实历史 SFT 主线](R60_REAL_HISTORY_SFT_MAINLINE_CN.md) | 真实历史主线沿革和准入状态；仅按交接总览说明读取历史段落 | 已存在，历史主线文档 |
| 6 | [Pilot10 Reviewer C 报告](R60_HF_PILOT10_C_BLIND_SEMANTIC_REVIEW_20261108_CN.md) | C 的三态结果、绑定和独立性限制 | 已存在 |
| 7 | [Pilot10 Owner Pairwise 报告](R60_HF_PILOT10_OWNER_PAIRWISE_AND_CALIBRATION_20261108_CN.md) | A/B 5+5、无交集、Checkpoint 与 crosswalk 核验 | 已存在 |
| 8 | [1000 条 HF Quality Pipeline 说明](R60_HF_QUALITY_PIPELINE_REUSABLE_1000_CN.md) | 现有可复用审核 Stage、Runner 和限制 | 已存在 |
| 9 | [HF CPU Stage 后预检 Runbook](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md) | Jinja2/Chat Template 故障复盘和可复用预检命令 | 已存在 |
| 10 | [HF Jobs 工程规范](standards/HF_JOBS_ENGINEERING.md) | 共享 Runtime、依赖、隐私、Job 与验收约束 | 已更新 |
| 11 | [HF Runtime 架构](standards/R60_HF_JOBS_RUNTIME_ARCHITECTURE_V1_CN.md) | 共享 Runtime 七模块职责 | 已存在 |
| 12 | [HF Jobs Skill](../skills/storyforge-hf-jobs/SKILL.md) | Owner/Agent 实际操作入口 | 已存在 |

## 3. 交接证据状态矩阵

| 工作项 | 当前证据 | 状态 | 下一位 Agent 是否需要重做 |
|---|---|---|---|
| R60 候选池 1000 条 | 扩样和冻结回执；候选数不等于 PASS | 已完成候选构建 | 不重做扩样 |
| 1000 条 A/B Owner crosswalk | Owner Pairwise SAFE：manifest receipt 与 input hash/cross-slot binding verified；A/B 各 1000/1000 source binding | PASS（来源映射/绑定层） | 不重跑旧审计 |
| Pilot10 A/B Checkpoints | A v2 5 份 + B v3 5 份，10/10 receipt/input SHA 通过 | PASS（回执层） | 不重跑旧推理或旧 checkpoint |
| Pilot10 A/B 逐案一致性 | matched_cases=0、unique_source_cases=10 | 不可评估 | 不得宣称一致 |
| Pilot10 Reviewer C | 10/10 结果与来源绑定；三维三态 SAFE 已有 | 已完成结果整理 | 不重跑旧 C |
| Reviewer C 独立性 | model_identity_independently_verified=false；reviewer_c_independence_verified=false | 未证明 | 作为历史限制保留 |
| Pilot10 严重问题语义仲裁 | semantic_severity_adjudication_complete=false | HOLD | 新 Agent 按任务书建立独立 Owner 参照 |
| Gold72 历史 C/Owner 汇总 | C=38/1/1；Owner=30/4/6；Owner worksheet/aggregate SAFE 已知存在 | 历史聚合已知，需复核定义/分母 | 只读核验，不重复导入 |
| Gold72 A V3/B2 40 条来源集合 | C packets 有 40 条，但独立 A/B 40-case source manifest/crosswalk 未证明；C execution record unavailable | 未完成 | 新 Agent P0 处理 |
| Gold72↔R60 跨集去重 | 尚无已验证的私有跨集 fingerprint SAFE | 未完成 | 新 Agent P0 处理 |
| Quality-v1 admission | 0 | 未准入 | 不得推断 |
| GPU/SFT 授权 | 无新授权 | 未授权 | 不得提交 |

### 3.1 Pilot10 重要数字

- A：5 条，5/5 REJECT。
- B：5 条，5/5 REJECT。
- A/B matched cases：0。
- unique source cases：10。
- Checkpoint receipt/input SHA：10/10 verified。
- Reviewer C：10/10 完成盲输入和绑定。
- C 的 hard_rule：10 NOT_SUPPORTED。
- C 的 player_agency：3 SUPPORTED、7 NOT_SUPPORTED。
- C 的 safety：5 SUPPORTED、1 NOT_SUPPORTED、4 INSUFFICIENT_CONTEXT。
- C 模型身份独立验证：false。
- Quality-v1 admitted：0。

A/B 的 5+5 不是相同案例配对，不能计算逐案双模型一致率。

### 3.2 1000 条 crosswalk 的准确解释

Owner Pairwise SAFE 已验证 A/B 两槽各 1000/1000 来源映射、输入 SHA 和跨槽 source binding。此结论仅说明 1000 条 blind Stage 的来源绑定完整，不表示 1000 条已经完成 A/B 推理或 Quality 审核。此前批量 Stage audit 的 A=0、B=0、complete_pairs=0、HOLD=1000，必须保留该事实。

## 4. 已知故障与永久经验

**R60 Jinja2/Chat Template 故障是 R58 已解决问题的复发。**

已固化到：
- [交接总览 §4A](R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md)
- [任务书 P0.5](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)
- [HF Jobs 工程规范](standards/HF_JOBS_ENGINEERING.md)
- [HF CPU Stage 后预检 Runbook](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md)

关键经验：
- 依赖基线：`transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`。
- Chat Template 必须显式声明 Jinja2；不得依赖镜像预装。
- Job 提交前执行 pip check、版本/import probe 和真实 `apply_chat_template`。
- 失败即停止；不靠换 flavor、namespace 或重复提交绕过。
- 已有 Reviewer 独立依赖输入和 hash-pinned lock；Owner Mac staging/远端目标 Tokenizer 检查尚未完成，不可误写为新 Job 已通过。

## 5. 新 Agent 的最小接手动作

严格从任务书 P0 开始，不提前做 P1–P6：

1. 只读刷新 PR #25 当前 head、分支和 CI；不 reset、不 force-push、不 merge。
2. 在 Owner Mac 只读盘点 Gold72 已知私有文件、SAFE、receipt、Owner ID map 和 A V3/B2 crosswalk；不打印正文。
3. 核验实际文件存在性、SHA、schema、status、计数和来源绑定；历史聚合 40/72、38/1/1、30/4/6 必须回到原始 SAFE 核对定义和分母。
4. 确认准确的 40 条 Gold72 来源，生成独立私有 manifest；划分 20 条 development / 20 条 locked regression。
5. 使用私有规范化来源指纹与 R60 10 条集合去重；只输出交集数、唯一数和 SAFE，不上传 crosswalk。
6. P0 的两集合来源、回执、去重、旧文件不变和无敏感 SAFE 全部通过后，才进入 P1。

不得重复执行已通过的 R60 1000 crosswalk / Pilot10 Checkpoint 审计；不得重跑旧 A/B/C 推理。

## 6. 当前范围内的禁止事项

- 不修改 RolePlay。
- 不读取 R50 正文。
- 不读取全库正文，不扩大 Owner 已给定的私有材料范围。
- 不修改数据库、权限或连接身份。
- 不覆盖 Gold72、Gold192、R50 或旧 A/B/C 的历史文件/结果。
- 不把正文、故事/Session/User ID、blind ID、crosswalk、私有 checkpoint、DSN、凭据写入 GitHub。
- 未经明确 GPU 授权，不提交 GPU Job、不启动 SFT。
- 不把技术优先、三态 NOT_SUPPORTED 或 tokenizer PASS 误写成 Quality-v1 PASS。
- 不重新开展用户已明确要求停止的权利/协议调查。

## 7. 交接材料最终验收

| 验收项 | 结果 |
|---|---|
| 交接总览已存在并含真实状态/边界 | PASS |
| P0–P6 任务书含命令/产物/验收 | PASS |
| 三模型计划与交接入口互链 | PASS |
| Pilot10 SAFE 关键数字和限制已记录 | PASS |
| R60 1000 crosswalk PASS 与批量 A/B 未运行的区别已记录 | PASS |
| Gold72 40 条证据缺口与不得替代的 72-row Stage 已记录 | PASS |
| R58→R60 Jinja2 复发经验进入交接总览、P0.5、HF 标准 | PASS |
| 私有数据不上 GitHub 的边界明确 | PASS |
| 交接材料与 P0–P6 实际执行区分明确 | PASS |
| 新 Agent 的第一步和最小动作明确 | PASS |
| Owner Mac 私有 Gold72 最终文件存在性/SHA/receipt | DEFERRED TO NEXT AGENT |
| Gold72 40 条重建/冻结和跨集去重 | DEFERRED TO NEXT AGENT |
| Quality-v1 admission / GPU / SFT | NOT DONE / NOT AUTHORIZED |

**交接准备结论：文档与任务书已形成可执行交接包；私有 Gold72 P0 尚未执行，明确交由新 Agent。不得将交接准备完成宣称为训练准入完成。**


## 8. P0 Freeze Runner 历史记录（已执行完成，当前 P0=PASS）

已新增 Owner Mac 本地执行工具与合成测试：

- [P0 Freeze Runner](../scripts/r60_calibration_p0_freeze.py)
- [Runner 合成测试](../tests/test_r60_calibration_p0_freeze.py)
- [正式执行命令与安全边界](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#86-owner-mac-一键-p0-freeze-runner代码已提交尚未在-owner-mac-执行)

历史状态：Runner 代码提交后曾尚未在 Owner Mac 运行；该状态已由第 9 节正式 SAFE 取代。当前 P0 已 PASS，不得重跑 Runner 或旧 R60 1000-row crosswalk / Pilot10 Checkpoint 审计。


## 9. P0 正式冻结完成（2026-11-09）

Owner Mac 正式 SAFE 已返回 `CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`，`manifest_files_written=4`。Gold72 40 条、20/20 分层，R60 Severe10 10 条，跨集合三类精确指纹交集均为 0，唯一来源数 50。Gold72/R60 C 独立性限制、Quality-v1 admitted=0、training_authorized=false 均保留。

详细聚合计数及状态边界见 [P0 正式冻结执行记录](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#812-owner-mac-正式冻结完成p0-pass--quality-hold-2026-11-09)。

四份私有产物仅保留在 Owner 私有目录，不得上传 GitHub/HF。P1(v2.1) 后续已独立 PASS；P0 PASS 不代表 Quality-v1 admission、模型选择或 GPU/SFT 授权。


## 10. P1 Rubric v2.1 三维严重证据标准已通过（2026-11-09）

- [当前冻结的三维严重问题证据标准 v2.1](R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md)
- 实现：`src/storyforge_gold_quality/hf_severity_evidence_v2.py`
- 合成回归：`tests/test_hf_severity_evidence_v2.py`
- 旧 v3 Literary Reviewer 与 Reviewer-C v1 兼容路径保持不变。
- 最新实现提交：`c80d6bbc2c7f1cd7a6d5184be808e6a788d0e2b7`；全仓 pytest 859 passed / 5 skipped / 42 subtests；五组 Actions 全部通过。
- 详细验收与边界见 [P1 执行任务书 8.14](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#814-p1-v2-标准与合成回归通过-2026-11-09)。

**当前：P0 PASS、P1 PASS；P2 Owner 独立盲裁决未开始。** Quality-v1 admitted=0；没有模型/HF/GPU/1000 条审核/SFT。


## 11. P2 Owner Development-20 blind packet builder 已实现；v2.0 包已废弃，v2.1 包待生成

- 实现：`src/storyforge_gold_quality/hf_owner_adjudication_v2.py`
- Owner Mac CLI：`scripts/r60_owner_adjudication_v2.py`
- 合成测试：`tests/test_hf_owner_adjudication_v2.py`
- 只准备 Gold72 Development 20；Locked Regression 20 不输出；R60 Severe10 不读取。
- 默认 dry-run，必须显式 `--write` 才 create-only 生成六份 Owner 私有文件。
- 早期 v2.0 Development-20 包已生成，但随后因审核范围变更标记 `SUPERSEDED`，不得用于裁决。
- 当前须在新目录生成 Rubric v2.1 包；生成后 Owner review 才能开始。
- 当前接口与执行命令见 [主任务书 8.21–8.24](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md)。


### P2 Owner 审核结果回执验证

- 验证器：`scripts/r60_owner_adjudication_verify_v2.py`
- 核心实现：`hf_owner_adjudication_v2.verify_owner_results()`
- 固定验收 20 个 verdict + 60 项独立语义复核；按新 calibration_id 绑定；完整检查所有引用索引；输出私有 SHA-256 manifest 和 SAFE。
- 真实 Owner 审核尚未开始。命令与 HOLD 规则见 [任务书 8.16](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#816-p2-owner-结果与-60-项语义复核的私有回执验证器-2026-11-09)。


### P2 工程准备最终 CI 状态（2026-11-09）

- 最新代码提交：`e7917030e76e7ccb96562dec47ce4e879b9306b9`
- pytest 870 passed / 5 skipped / 42 subtests passed；Ruff、CI、Gold Quality Pipeline、R60 HF Runtime CI、R60 HF CPU dependency profiles、R58 scoped synthetic 全部 PASS。
- 依赖锁漂移已通过显式固定 `regex==2026.11.7` 修复；未放宽 hash lock。
- 该段是旧 v2.0 包生成前的历史状态，已由后续 8.20–8.21 更新取代。
- 当前状态：v2.0 包 SUPERSEDED；v2.1 新包未生成；Owner review 未开始。Quality-v1 admission=0、training_authorized=false。


Owner Mac 的精确 P0 manifest 路径、Reviewer-C blind source 路径、项目工作目录和 dry-run 命令已补充至 [任务书 8.18](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#818-owner-mac-dry-run-精确路径与命令)。


### Owner dry-run 输出路径门禁与最新回归

- dry-run 现在也检查正式写入输出路径的绝对路径、父目录 0700、create-only 和仓库外约束；dry-run 本身不写文件。
- 最新代码提交：`bf1181eefc43832e89cb82b76cea45d46e954301`。
- 最终 Actions：871 passed / 5 skipped / 42 subtests；Ruff、CI、Gold Quality Pipeline、R60 Runtime、CPU dependency profiles、R58 scoped synthetic 全部 PASS。
- Owner Mac dry-run 尚未运行。精确路径和命令见 [任务书 8.18](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#818-owner-mac-dry-run-精确路径与命令)。


### Owner Mac Dry-run 实际回执（2026-11-09）

Owner 已在当前 worktree `/Users/keedle/workspace/storyforge-r60-ledger-diagnostics` 对应分支执行 P2 dry-run，SAFE 状态为 `P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN`，20 cases prepared、0 files written。Owner review 未开始；下一步显式 `--write` 前确认输出目录不存在。任务书 8.18 已更正 worktree 路径，并使用普通 `python` 命令，不再要求绝对 Python/venv 路径。


### P2 v2.0 Development-20 盲审包已生成（历史包，SUPERSEDED）

- 旧 SAFE：`P2_OWNER_BLIND_PACKETS_READY__OWNER_REVIEW_NOT_STARTED`，20 cases / 6 files。
- 仅 Gold72 Development-20；未暴露 Locked Regression 20、R60 Severe10、旧 A/B/C、旧 Owner resolution 或旧 blind IDs。
- 该包基于 Rubric v2.0，已由 Owner 明确标记 `SUPERSEDED`，不得用于裁决、不得覆盖或删除。
- v2.1 必须在新目录重新 dry-run / `--write` 生成。


### 审核范围变更：Rubric v2.1（2026-11-09）

Owner 已明确排除数据来源、版权/权利、数据使用授权、隐私合规和数据隔离证明；审核员不得要求这些证据，也不得因缺失而 HOLD。故事内玩家拒绝/同意/行动边界仍属于 Player Agency / Safety 语义证据；盲包文本 locator 与故事规则依据字段仍保留，但不作为数据来源或权利证明。

- Rubric version：`r60_severity_rubric_v2_1`
- v2.0 已生成的 Development-20 六文件包已标记 SUPERSEDED，不得用于裁决、不得覆盖或删除。
- v2.1 新包须生成到 `owner-adjudication-dev20-rubric-v2-1-20261109` 新目录；当前 HEAD 的五组 CI 已全部通过，但接手时仍须重新核验。随后执行 dry-run / 显式 `--write`。
- 完整范围定义、旧包处置和命令见 [任务书 8.21](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#821-owner-要求排除数据来源与权利审核rubric-v21-2026-11-09)。


公开冻结的 v2.1 标准：[R60 Severity Evidence Rubric v2.1](R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md)。Owner instructions 只允许读取新 v2.1 盲包、说明、Schema 和此公开 Rubric；旧 v2.0 包已 SUPERSEDED。


### Rubric v2.1 工程回归最终状态

代码实现基线提交 `f9d23fd11fd5ecdb5e2de41cd203175500bb9004` 已通过完整回归。当前 PR HEAD 已推进至 `4190c6fe895080d99901cb4c5eb3f221c6948d6d`，该 HEAD 的五组 Actions 也已全部 completed/success（具体 run IDs 见主任务书 8.25）。P1 v2.1 实现通过；v2.0 六文件包 SUPERSEDED；v2.1 新包尚待 Owner Mac dry-run / `--write`。Owner review 未开始。


### P2 v2.1 语义蕴含复核接口合同已补齐（2026-11-09）

- 交接任务书新增 **8.23**，正式固定 `storyforge_severity_semantic_entailment_check_v2` 的 JSONL 外层四字段、内层七字段、字段类型/长度/枚举、全部 evidence indexes 覆盖、UTC 时间戳、20×3=60 行去重覆盖、三种 conclusion 的 HOLD 语义及身份认证边界。
- 当前冻结标准为 [Rubric v2.1](R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md)，原始 Rubric v2 保留为历史版本。
- 接口以 `src/storyforge_gold_quality/hf_severity_evidence_v2.py::verify_semantic_entailment_v2` 和 `src/storyforge_gold_quality/hf_owner_adjudication_v2.py` 的实际严格校验为准。
- v2.1 排除数据来源、权利、隐私、授权和数据隔离审核；不得将其重新加入案例 verdict、missing_context 或 semantic HOLD。
- 本次只补充公开交接合同，没有读取/修改 Owner 私有盲包、没有开始 Owner review、没有生成 P2 v2.1 包，也没有调用模型/GPU/HF Job。

详见 [R60 执行任务书 8.23](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#823-p2-v21-semantic-entailment-jsonl-固定接口合同-2026-11-09)。


### P2 v2.1 接口合同 CI 全绿（2026-11-09）

历史 HEAD `9b4f235` 的 CI 快照已被当前 PR HEAD 取代。当前 HEAD 与五组 Actions 状态以主任务书 8.25 为准；不得将旧 SHA 的 run 当作新 HEAD 的 CI 结果。


## 14. 当前有效状态与下一 Agent 唯一接手入口（2026-11-09）

- PR #25：Open / Draft；base `r60/canonical-a-v3-binding`。
- 上一轮核验快照 HEAD：`4190c6fe895080d99901cb4c5eb3f221c6948d6d`，当时五组 Actions 全部 completed/success；之后交接文档校正提交已推进 HEAD。当前 HEAD/CI 必须在接手时实时刷新，不能沿用 8.25 的旧 SHA。
- P0 PASS：Gold72 40、R60 Severe10 10；案例级 20/20；Gold72 Story 可跨集合（shared Story=5）；Gold72↔R60 exact overlaps=0；unique source=50。
- P1 PASS：Rubric v2.1 / Schema / Prompt / synthetic regression / old v3 compatibility。
- P2 v2.0 package：SUPERSEDED；P2 v2.1 package：NOT GENERATED；Owner review：NOT STARTED。
- 下一步先做 P2-A v2.1 新包 dry-run → 显式 `--write` → Owner 20 verdict + 60 semantic checks → 私有验证器；随后 P2-B 需独立准备 Locked20 + Severe10 的 30 Owner results + 90 semantic checks，作为 P4 前置。
- P3 等 P2 完成后进入；P4 GPU、P6 1000 批量审核、SFT 均未授权。
- 不重做 P0/P1，不读取 R50 正文，不修改数据库/RolePlay，不上传私有值。

权威接手任务书：[R60 下一 Agent 交接任务书 v1.1](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md)。详细阶段标准：[R60 执行任务书 v1.2](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)。
