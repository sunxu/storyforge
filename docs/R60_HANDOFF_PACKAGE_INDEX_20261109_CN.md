# StoryForge R60 交接包索引与完成清单

更新日期：2026-11-09  
仓库：`sunxu/storyforge`  
交接分支：`r60/gold192-history-v3-adapter`  
PR：[#25](https://github.com/sunxu/storyforge/pull/25)（Open / Draft）  
主线 Issue：[#26](https://github.com/sunxu/storyforge/issues/26)  
交接与下一阶段执行 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)

## 1. 交接包的目的与边界

本交接包的目标是让下一位 Agent 无需翻阅数百轮聊天记录，即可准确了解 R60 的历史执行、证据状态、可复用实现、已知故障、未完成事项和下一步执行方法。

**本次完成的是交接材料准备，不是执行下一阶段。** 本次没有执行 Gold72 重建/冻结，没有修改审核 Prompt，没有运行新模型，没有提交 HF Job/GPU，没有开始 1000 条批量审核，没有修改 RolePlay 或数据库。

交接材料完成不代表 P0 PASS、Quality-v1 admission 或训练授权。

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


## 8. P0 Freeze Runner 更新（2026-11-09）

已新增 Owner Mac 本地执行工具与合成测试：

- [P0 Freeze Runner](../scripts/r60_calibration_p0_freeze.py)
- [Runner 合成测试](../tests/test_r60_calibration_p0_freeze.py)
- [正式执行命令与安全边界](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#86-owner-mac-一键-p0-freeze-runner代码已提交尚未在-owner-mac-执行)

代码提交已通过 GitHub CI / Ruff / Tests。它尚未在 Owner Mac 运行，因此本地私有 manifest、cross-set dedup receipt 和 Inventory SAFE 仍未生成；P0 不得标为 PASS。Runner 不会重跑 R60 1000-row crosswalk 或旧 A/B checkpoints，也不会调用模型/GPU/数据库。


## 9. P0 正式冻结完成（2026-11-09）

Owner Mac 正式 SAFE 已返回 `CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`，`manifest_files_written=4`。Gold72 40 条、20/20 分层，R60 Severe10 10 条，跨集合三类精确指纹交集均为 0，唯一来源数 50。Gold72/R60 C 独立性限制、Quality-v1 admitted=0、training_authorized=false 均保留。

详细聚合计数及状态边界见 [P0 正式冻结执行记录](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#812-owner-mac-正式冻结完成p0-pass--quality-hold-2026-11-09)。

四份私有产物仅保留在 Owner 私有目录，不得上传 GitHub/HF。P1 尚未开始；P0 授权不构成后续阶段或 GPU/SFT 授权。


## 10. P1 三维严重证据标准 v2 已通过（2026-11-09）

- [三维严重问题证据标准 v2](R60_SEVERITY_EVIDENCE_RUBRIC_V2_20261109_CN.md)
- 实现：`src/storyforge_gold_quality/hf_severity_evidence_v2.py`
- 合成回归：`tests/test_hf_severity_evidence_v2.py`
- 旧 v3 Literary Reviewer 与 Reviewer-C v1 兼容路径保持不变。
- 最新实现提交：`c80d6bbc2c7f1cd7a6d5184be808e6a788d0e2b7`；全仓 pytest 859 passed / 5 skipped / 42 subtests；五组 Actions 全部通过。
- 详细验收与边界见 [P1 执行任务书 8.14](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md#814-p1-v2-标准与合成回归通过-2026-11-09)。

**当前：P0 PASS、P1 PASS；P2 Owner 独立盲裁决未开始。** Quality-v1 admitted=0；没有模型/HF/GPU/1000 条审核/SFT。
