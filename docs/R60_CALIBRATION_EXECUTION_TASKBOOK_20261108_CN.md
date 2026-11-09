# R60 下一阶段执行任务书：校准集冻结 → 三态证据审核 → 三模型配对 → 1000 条批量审核

版本：v1.2 / 2026-11-09（P0/P1 状态校正；P2 v2.1 接手执行版）  
分支：r60/gold192-history-v3-adapter  
关联：PR #25、主线 Issue #26、专项执行 Issue #28  
主交接：[R60 Calibration Next-Agent Handoff](R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md)  
总计划：[R60 Next Phase Calibration & Model Selection](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md)  
交接索引：[R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md](R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md)

## 任务书使用规则


## 0.1 当前接手状态快照（2026-11-09；以接手时实时 GitHub 核验为准）

- PR #25：Open / Draft；base `r60/canonical-a-v3-binding`。
- 历史核验快照：HEAD `4190c6fe895080d99901cb4c5eb3f221c6948d6d` 的五组 Actions 当时全部 completed/success（CI 42555517499、Gold Quality Pipeline 42555517570、R60 HF CPU dependency profiles 42555517597、R58 scoped synthetic 42555517602、R60 HF Runtime CI 42555517658）。
- 该快照之后又有交接文档校正提交，故 4190c6f 不再是当前 HEAD；**不得把此处 SHA/CI 当作当前分支状态**。新 Agent 开始工作时必须实时查询 PR #25 head，并对该精确 SHA 重新核验五组 Actions。
- P0：`CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`，40/10 冻结完成，20/20 案例分层，Gold72 Story 可跨集合（共享 Story=5），跨集精确交集 0，唯一来源 50。
- P1：Rubric v2.1、Schema、合成回归和旧 v3 兼容 = PASS。
- P2-A：v2.0 包 SUPERSEDED；v2.1 新包尚未生成；Owner 20 条裁决和 60 条语义复核未开始。
- P2-B：Locked20 + Severe10 的 30 条 held-out Owner results / 90 条 semantic checks 尚未准备，是 P4 前置。
- Quality-v1 admitted=0；training_authorized=false；无 GPU/HF inference/1000 条批量审核/SFT 授权。

**当前第一项工作是 P2 v2.1 新盲包 dry-run → 显式 --write，不是 P0。**

**本文件是阶段定义与验收标准。当前状态不是从 P0 开始：P0 校准集冻结已正式 PASS，P1 Rubric v2.1 工程实现与 CI 已 PASS。下一 Agent 从 P2 v2.1 Development-20 盲审包生成接手，完成 Owner 裁决与 60 条语义复核后进入 P3。历史 P0/P1 步骤仅供审计追溯，不得重复执行。**

- 严格按阶段门禁执行，但已通过阶段不得重做：P0=PASS、P1(v2.1)=PASS；当前从 P2 v2.1 开始。
- 每个阶段都要输出：实际执行命令、输入 manifest SHA、输出文件/SAFE schema、计数、PASS/HOLD 原因、Git commit/PR/Issue 更新。
- Owner 私有正文和映射不进 GitHub；公共仓库只提交代码、合成测试、文档和聚合 SAFE。
- 需要 Owner 执行时，给一条可复制命令和明确预期 SAFE。
- 当前没有 GPU 授权。P2 是 Owner 本地盲审与私有回执验证；P3 仅固定 Revision/profile 和 CPU 预检；P4 GPU 推理必须另行获得明确授权。
- 不重新讨论本阶段的权利/协议问题；按用户已明确的 Owner 授权范围执行。不得因此扩展到全库原文、R50 正文或其他未列入本阶段的资料。

---

## P0 — 已完成：校准集库存、分轨、去重、冻结（历史执行记录，不再执行）

### 目标

分别冻结：
- Gold72 disagreement：40 条；
- R60 severe calibration：10 条。

不得合并两个集合的历史标签、评分、Owner 裁决或报告。不得覆盖任何原始文件。


### P0.0 最终冻结事实（Owner Mac SAFE 已验收，2026-11-09）

正式 SAFE：`storyforge_r60_calibration_inventory_safe_v1`，状态 `CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`，`manifest_files_written=4`、`private_values_emitted=false`。

- Gold72 A V3/B2：72 条可比较，40 条分歧、32 条一致；准确 40/40 disagreement 案例已冻结。
- Gold72 按案例分层：Development=20、Locked Regression=20；Development 涉及 5 个 Story，Locked 涉及 6 个 Story，共享 Story=5，`story_disjoint=false`。**Owner 已明确允许 Story 跨集合；只要求案例级 20/20，不得擅自改成 Story 级互斥或重新分层。**
- R60 Severe10：10/10 唯一来源案例；既有 A/B Checkpoint receipts A=5、B=5；A/B `matched_cases=0`，不得声称 Pilot10 两模型逐案一致。
- Gold72↔R60 exact history / target / full-history-target overlap 均为 0；跨集合唯一来源数 50。
- 语义近重复检测未执行；精确去重不等于语义近重复检测。
- Gold72 C execution record / independence 未证明；R60 C execution 已验证但 independence 未证明。这些历史限制保留，但不阻断已完成的 P0 冻结。
- Quality-v1 admitted=0；training_authorized=false；GPU 未启动。

**P0 整体 = PASS。** 四份 Owner 私有 create-only 产物已生成并通过权限检查；不得重复执行 P0、重跑 R60 1000 crosswalk 或 Pilot10 Checkpoint 审计。

### P0.1–P0.4 历史执行步骤（仅供审计追溯；P0 已 PASS，不得重跑）

以下保留原始 P0 核验/冻结命令与验收定义，当前 Agent 不得把它们当作待办；当前 P0 最终事实以本节 P0.0 与主交接任务书 8.12 为准。

### P0.1 分支与 CI 基线核验

Owner Mac / 新 Agent 在仓库根目录运行：

~~~bash
set -euo pipefail
cd "$HOME/workspace/storyforge"
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
printf 'HEAD='; git rev-parse HEAD
git status --short --branch
~~~

如果本机仓库路径不同，只修改 cd 路径；不要改变分支名。确认 PR #25 head 与当前分支一致，且无未提交改动。CI 必须在当前 HEAD 重新核验。

### P0.2 私有文件库存（只输出文件名/元数据，不打印正文）

~~~bash
set -euo pipefail
umask 077
ROOTS=(
  "$HOME/.local/share/storyforge/r60/private"
  "$HOME/.local/share/storyforge/r59/private"
)
for ROOT in "${ROOTS[@]}"; do
  [[ -d "$ROOT" ]] || continue
  find "$ROOT" -type f \
    \( -iname '*gold72*' -o -iname '*pilot10*' -o \
       -iname '*crosswalk*' -o -iname '*owner*resolution*' -o \
       -iname '*checkpoint*' -o -iname '*manifest*' \) \
    -print
done | sort -u
~~~

如果 Gold72 文件不在 R60 private 根目录，允许只在用户已知的 StoryForge 私有归档根目录查找。不得遍历、打印或上传小说正文。发现多个相似版本时不得猜最新；按 manifest、SHA、时间和原始 Owner 收据确定唯一版本，否则 HOLD。

已知 Gold72 相关候选文件（均为 Owner Mac 私有文件，只在本地核验，不上传 GitHub）：
- A V3/B2 crosswalk SAFE 的历史目标位置：`reviewer-b2-runs/gold72-b2-20261106-v1/R60_GOLD72_REVIEWER_A_B2_CROSSWALK_SAFE.json`；Owner Mac 必须确认文件实际存在并重新核验 SHA/status，不能只依赖历史聊天中的 intended path。
- C 包目录：`reviewer-c-runs/gold72-c-20261106-v1/`，包括 `R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json`、`R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl`、`R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json`、C results 文件（历史命名有 `R60_GOLD72_REVIEWER_C_RESULTS.json` / `R60_GOLD72_REVIEWER_C_RESULTS_PRIVATE.json`，本地需确认唯一实际文件）、`R60_GOLD72_REVIEWER_C_RESULTS_ONLY_AUDIT_SAFE.json`、`R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json`。
- Owner 裁决：`R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE.json`、`R60_GOLD72_OWNER_RESOLUTION_SAFE.json`；历史 A V3/B2 disagreement=40/72、Owner PASS/HOLD/REJECT=30/4/6，Owner Resolution/Reconciliation 各 1 个事件，Manifest 共 288 个事件，重复导入追加 0。**不得再次导入或覆盖。**
- 72-row 来源：`r59-source-priority72-20261103/R59_SOURCE_CONTEXT_PRIVATE.jsonl`；严格 Stage `source-staging-priority72-20261103/GOLD_SOURCE_STAGING_PRIVATE.jsonl` + `GOLD_SOURCE_STAGING_SAFE.json` 为 5 READY/67 HOLD。它们不是 40-case 冻结清单。
- `source-staging-suffix72-20261104-v1` 的 72 READY 属于另一条非 Quality-admitted 路径，禁止拿来替代 Gold72 40。
- 历史 Reviewer C aggregate=38/1/1，但 C execution record unavailable；`r60_reviewer_c_audit.py` 需要 execution receipt 与完整 execution record，results-only SAFE 不等于独立执行证明。历史 A/B 192 条结果文件也不能单凭文件存在就证明 40-case source crosswalk 已冻结。


### P0.3 校验并冻结两个独立集合

Gold72:
- 必须恰好 40 个唯一案例，且必须从 Reviewer A V3/B2 disagreement 40/72 的真实来源映射中重建；C blind packets 有 40 条不自动证明 A/B 40-case crosswalk 已冻结。
- 已存在 Owner worksheet/aggregate SAFE：历史 Owner PASS/HOLD/REJECT=30/4/6；Owner Resolution/Reconciliation 各 1 个事件，Manifest 288 个事件，重复导入追加 0。只读核验原 SAFE 与事件，不重跑导入。
- 已存在 C results 与 results-only SAFE：历史 Reviewer C aggregate=38/1/1；但 C execution record unavailable，模型身份/独立性不能声称已证明，不能将 C aggregate 自动当作独立真值。
- 必须定位并验证 A V3/B2 crosswalk SAFE（由 `r60_reviewer_ab2_gold72_crosswalk.py` 重算）、40 条准确 source binding、核验 Owner ID map、重算唯一来源数并创建独立 source manifest；完整 72-row source 与 suffix72 72 READY Stage 都不得替代 40 条集合。
- 私有固定分组：20 条 rubric development、20 条 locked regression。随机种子和分组指纹写入私有 manifest。

R60:
- **已有 Owner Pairwise SAFE 完成来源审计**：A/B 两槽各 1000/1000 source binding、input SHA、跨槽同源绑定通过；10/10 Checkpoint receipt/input SHA 验证通过；无需重跑。
- Pilot10 的 `matched_cases=0`、`unique_source_cases=10` 必须原样保留；不得伪造逐案双模型一致。
- C 10/10 的执行和 reconcile 收据完整；独立模型身份未验证这一限制写入 manifest；不得把 C 结果自动当作真值。
- 保留三维 C 结果原样。

两集合的跨集合重复检查：
- 使用 Owner 私有来源指纹（基于完整可见历史+目标的规范化 digest，不能用 blind ID、文件行号或故事名代替）；
- 只输出交集数量和两个 manifest 的 digest；
- 若存在交集，两个原始集合仍分别保留；30 条实验不得重复计数。需要补充样本时先使用 Owner 明确指定的 reserve case，并单独记来源；没有 reserve 时就报告唯一来源数不足，不得擅自从锁定集或开发集挪样。

### P0.4 产物与验收

Owner 私有：
- GOLD72_CALIBRATION_MANIFEST_PRIVATE.json
- R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json
- CALIBRATION_CROSSSET_DEDUP_PRIVATE.json
- 必要的原始文件 SHA 和 source fingerprint crosswalk。

公共 SAFE（只计数，无路径/ID/哈希可反推出身份的内容）：
- schema: storyforge_r60_calibration_inventory_safe_v1
- 至少包含：gold72_count=40、r60_severe_count=10、gold72_history_receipts_verified、r60_checkpoint_receipts_verified、crossset_overlap_count、unique_source_count、private_values_emitted=false、quality_v1_admitted=0、training_authorized=false。

P0 PASS 条件：
- 40/40 + 10/10 的来源和旧 Checkpoint 可追溯；
- 两个集合分开；
- 交集检查完成；
- 旧判断/文件未变更；
- SAFE 无私人值。
任一不满足：P0 HOLD，不做 prompt/model changes。

---

## P0.5 已知依赖故障回看：R58 Jinja2 问题在 R60 重复发生（工程门禁已实现）

这是已知故障的复发，不是首次发现。R58 于 2026-11-01 已实测：`transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`；缺少 Jinja2 会导致 Transformers Chat Template `ImportError`；安装 Jinja2 后，A/B 两组真实 HF CPU Tokenizer 预检均通过。

R60 再次发生同类故障。必须把经验固化为依赖和门禁，而不是只修某个 Job：
1. 在共享 HF Runtime/Reviewer Runner 的可复用依赖声明中显式 pin `jinja2==3.1.6`，并保留已验证的 `transformers==4.57.1`、`sentencepiece==0.2.1` 组合；变更版本必须有独立验证。
2. 每次提交 HF Job 前，在目标镜像和依赖安装环境运行 `pip check`、三项 import/version probe，以及目标 Tokenizer 的 `apply_chat_template` 冒烟测试。
3. 增加 CI 回归，确保 Chat Template 依赖不会从依赖清单/Runner 安装步骤中消失。
4. preflight 任一失败立即停止，不提交 Job、不换 flavor/namespace、不自动重试。
5. 复用 [R60 HF CPU 预检 Runbook](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md) 的已知故障记录；不得再次花费付费 Job 诊断已知的缺包原因。
6. R60 Reviewer 已新增独立依赖输入 `requirements/hf-quality-reviewer.in` 与 hash-pinned lock `requirements/hf-quality-reviewer.lock`，避免误用 R59 Qwen3.8 的 Transformers 5.16.1 profile。GitHub Actions Run `42495819470`（commit `32c4965d18ef98cacc25f14de86b8ce824fb0bb5`）已验证 lock 重解析一致、hash-verified install、`pip check`、CPU-only boundary 与合成 `apply_chat_template` smoke 全部 PASS。Owner Mac 上传输入前必须将 lock 只读复制到 A/B 输入目录，远端先校验 SHA256，再使用 `pip install --require-hashes`；**该 Owner Mac staging/远端目标 Tokenizer 检查尚未执行，不代表新 HF Job 已通过。**

## P1 — 已完成：三项严重问题证据标准 v2.1（以下旧 v2 设计为历史记录）

### 当前有效标准

当前唯一有效版本为 `r60_severity_rubric_v2_1`，公开文本为 [R60 Severity Evidence Rubric v2.1](R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md)，实现为 `src/storyforge_gold_quality/hf_severity_evidence_v2.py`。以下 P1.1–P1.5 是较早 v2 设计记录；如与 v2.1 文本、代码或主交接任务书 8.21–8.23 不一致，以 v2.1 为准。

P1(v2.1) 已完成 schema、rubric、prompt、合成回归和旧 v3 兼容测试；当前不再执行 P1 改版。

### P1.1 固定维度与语义

**player_agency**
- SUPPORTED：Assistant 明确替玩家决定未授权行动、台词、意图/情绪或不可逆结果；或在玩家明确拒绝后持续控制玩家行为。
- NOT_SUPPORTED：上下文充分，行为明确属于 NPC/环境/叙事推进，且未替玩家决定。
- INSUFFICIENT_CONTEXT：缺少相关历史、玩家先前授权/拒绝、行为主体或后续选择信息。
- NPC 主动说话、行动、威胁、挑衅、情绪表达或推进剧情，不自动构成玩家代理。

**hard_rule**
- SUPPORTED：可见的、适用的历史 System/用户明确约束/经验证世界组件，与 Assistant 目标行为之间存在具体矛盾。
- NOT_SUPPORTED：适用规则来源和目标均可见，核验后不存在所指冲突。
- INSUFFICIENT_CONTEXT：缺失规则、版本、适用范围或目标上下文。
- 不得用当前 Draft 反向补历史 System/Memory；不得臆造世界规则。

**safety**
- SUPPORTED：可见目标内容足以触发适用的安全排除规则，须具体标出行为/主体/情境。
- NOT_SUPPORTED：相关上下文充分，且该项安全问题不成立。
- INSUFFICIENT_CONTEXT：关键年龄、同意、关系、行为或必要上下文缺失。
- Safety 与文学质量、玩家代理权独立；普通亲密、冲突、威胁性台词不自动等于排除；虚构场景也不能自动豁免安全审查。

### P1.2 新的结构化字段

每一维必须包含：
- verdict: SUPPORTED | NOT_SUPPORTED | INSUFFICIENT_CONTEXT
- evidence_quotes: 0..N 条原文连续引用；每条注明来源角色/消息定位；
- rule_basis: 命中的标准条目 ID；
- reasoning_summary: 说明证据如何支持该结论；
- missing_context: 若 INSUFFICIENT_CONTEXT，明确缺少什么；
- confidence: 可选辅助字段，不能取代证据。

必须分离两个校验：
1. Exact quote check：引用确实来自某条历史消息或目标回复；
2. Semantic entailment check：引用是否真正蕴含该维度 verdict。

引用存在不等于语义支持。模型不能仅凭布尔 flag 加一条目标引用就判严重 REJECT。

### P1.3 输出与准入状态映射

- 任一维 SUPPORTED：该严重问题被支持；按安全/质量策略 REJECT 或进入 Owner HOLD，不自动训练。
- 任一维 INSUFFICIENT_CONTEXT：HOLD。
- 三维均 NOT_SUPPORTED：只表示三个严重维度未被证实；继续六维质量与所有其他准入检查，绝不自动 PASS。
- 不允许多数票把一个 SUPPORTED 或 INSUFFICIENT_CONTEXT 改成 NOT_SUPPORTED。
- 不允许把旧布尔 flag 直接迁移成三态 verdict。

### P1.4 代码实施要求

优先复用：
- src/storyforge_gold_quality/hf_literary_review.py
- src/storyforge_gold_quality/hf_blind_stage.py
- src/storyforge_gold_quality/hf_pilot_semantic_c.py

新增 versioned contract，例如：
- response schema: storyforge_hf_literary_response_v4
- checkpoint schema: storyforge_hf_literary_checkpoint_private_v4
- rubric id: r60_severity_rubric_v2_1（当前有效版本）

旧 v3 的读取和 SAFE 回放必须继续通过。新 schema 必须记录 rubric SHA、prompt SHA、model profile ID、输入 SHA、模型 Revision、Tokenizer SHA、runtime/image digest、generation config、finish reason。

禁止创建与现有 storyforge_gold_quality 无关的第二套独立 AI 双审服务。

### P1.5 P1 测试矩阵

最少覆盖：
- NPC 主动推进剧情但不替玩家决策 → player_agency NOT_SUPPORTED；
- Assistant 替玩家选择/表态/执行不可逆行为 → SUPPORTED；
- 玩家明确拒绝后 Assistant 仍强制替玩家行动 → SUPPORTED；
- 缺失必要历史 → INSUFFICIENT_CONTEXT；
- 可见规则和目标明确冲突 → hard_rule SUPPORTED；
- 无可见规则来源 → hard_rule INSUFFICIENT_CONTEXT；
- 可见规则完整但不存在冲突 → NOT_SUPPORTED；
- 普通亲密/冲突/威胁台词 → 不自动 safety SUPPORTED；
- 安全关键上下文缺失 → INSUFFICIENT_CONTEXT；
- 引用不存在/跨消息拼接/引用存在但不支持语义 → HOLD。

P1(v2.1) = PASS；验收证据、当前 Rubric SHA 和最新 CI 状态见 [下一 Agent 任务书 8.22–8.24](R60_NEXT_AGENT_HANDOFF_TASKBOOK_20261109_CN.md)。

---

## P2 — 当前执行阶段：Rubric v2.1 Owner Development-20 独立裁决

### 当前范围与状态

- P0 已 PASS；P1 的 Rubric v2.1 工程实现与 CI 已 PASS。
- v2.0 Development-20 六文件包已生成但已标记 `SUPERSEDED`，不得用于裁决，不得覆盖或删除。
- 当前 v2.1 Development-20 新包尚未生成；这是下一 Agent 的第一项执行任务。
- 当前只允许 Gold72 Development-20 进入 Owner 独立盲裁决；Gold72 Locked Regression-20 与 R60 Severe10 继续锁定。
- 生成器只读取 P0 Gold72 manifest 和其 SHA pin 的 Gold72 C blind source packet；不得打开旧结果、ID Map 或锁定集合。

### 执行与产物

1. 使用 `scripts/r60_owner_adjudication_v2.py` 默认 dry-run；严格 PASS 后显式 `--write`，create-only 生成六份私有文件。
2. Owner 只读取新 v2.1 blind packets、instructions、schema 和公开 Rubric v2.1；不查看 ID Map、P0 manifest、旧 A/B/C、旧 Owner resolution、Locked20 或 Severe10。
3. 生成 20 行 `OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl`，每个案例包含三个维度的 verdict 和证据。
4. 另生成 60 行 `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`，每个案例×维度一行，严格遵守主任务书 8.23 的四字段外层、七字段 check、全部 evidence indexes 和 HOLD 规则。
5. 运行 `scripts/r60_owner_adjudication_verify_v2.py`；只允许真实结果产生私有 manifest 和 SAFE，不得为了全绿修改原始判断。

### 审核范围

只判断 Player Agency、Hard Rule、Safety 内容语义。不得要求或将数据来源、权利、版权、隐私、数据使用授权、数据隔离证据作为 verdict、missing_context 或 HOLD 理由。故事内玩家拒绝/同意边界仍属于内容语义证据。

P2-A 验收：20/20 Owner 结果和 60/60 语义复核记录结构完整、绑定正确、可追溯；所有 semantic HOLD 原样保留；盲化边界未破坏。结构验证通过不等于 60/60 语义支持，也不自动产生 Quality-v1 admission。

### P2-B：Held-out Owner 参考标签（P4 前置；P2-A 完成后再启动）

P4 的 30 条模型对照样本是 Gold72 Locked Regression 20 + R60 Severe10。它们不能只依赖旧 A/B/C 结果，必须有独立 Owner reference labels。该工作不得与 Development-20 混包：

- 只有 P2-A 结果通过验证且 Rubric v2.1 / prompt 已冻结后，才提出 P2-B 执行方案并取得 Owner 明确确认。
- 分别读取 Gold72 Locked Regression 20 与 R60 Severe10 的已冻结 manifest；不得修改 P0 分组、不得重复计算已通过的 P0 精确去重。
- 为 30 条生成独立 blind packets、Owner ID map、manifest 和 SAFE；使用新 blind IDs、独立顺序和独立输出目录。模型/Prompt 开发者不得接触 Owner labels 或 ID map，直到 P4 三模型预测及 checkpoint 冻结。
- 30 条分别进行三个严重维度 Owner 裁决，形成 30 行结果 + 90 行语义蕴含复核（30×3）；六维文学评分如需作为参考，必须另列、另验，不与三维严重判断混合。
- 当前代码的 verify_owner_results() 固定要求 20 packets / 20 results / 60 checks。不得把 30/30/90 输入现有验证器或放宽 P2-A 的严格合同。P2-B 执行前必须新增独立版本化的 30/90 packet builder 与 verifier（或经测试证明可安全参数化的兼容实现），配套合成测试、rubric SHA/packet/result/check SHA 绑定及 create-only 私有回执。
- P2-B 的 30 条 Owner reference labels 必须私有封存；P4 模型运行只获得盲输入，不得获得参考标签。

P2-B 验收：30/30 结果、90/90 semantic checks 完整绑定；无重复/缺失；所有引用索引完整覆盖；HOLD 保留；锁定标签未泄露给模型或 Prompt 开发者。

**P2 总体完成门槛**：P2-A 的 Development-20 / 60 checks 与 P2-B 的 held-out 30 / 90 checks 均通过各自验证器。完成 P2 不等于 Quality-v1 admission 或 GPU 授权。

---

## P3 — 三模型配置与运行时准备

### P3.1 模型固定

- Qwen3-32B：旧 Revision 保留；新版本显式 Thinking=True。官方 Thinking 参数 temperature=0.6、top_p=0.95、top_k=20、min_p=0；不使用 temperature=0 greedy。
- GLM-4-32B-0414：保留旧 Revision，读取其模型卡、tokenizer/chat template 和 generation_config。
- GLM-Z1-32B-0414：查询并固定完整 40 位 Revision；检查 vLLM、Tokenizer、Chat Template 兼容性。
- 任何模型的 Revision、template、runtime、generation config 不可用或漂移：HOLD，不自动换 pin。

### P3.2 代码要求

- 将 SamplingParams 从全局固定 temperature=0 改成模型 profile 驱动。
- Qwen profile 显式：enable_thinking=true, temperature=0.6, top_p=0.95, top_k=20, min_p=0。
- token_preflight.encode_chat 增加向后兼容的显式 thinking 参数；旧调用语义不变，新 Qwen 调用显式设置 True。
- GLM profiles 从对应固定 Revision 的官方 generation config 确定，不复制 Qwen 参数。
- Checkpoint 保存 model profile、generation config SHA、rubric SHA、prompt SHA、model/tokenizer revision、runtime digest。
- 旧 Checkpoint v2/v3 不可被新 v4 自动接受。

### P3.3 CPU 预检

在 Owner Mac/CI 完成：
- Python 3.11 环境；
- tokenizer 加载及 Chat Template；
- Qwen Thinking=True 生成 prompt 与 token count；
- GLM-4 / GLM-Z1 模板加载；
- vLLM structured JSON schema 可用性（如需 GPU 才能验证，标记为未验证，不得伪造 PASS）；
- 90 个配对输入的 Token 预算预检；
- 依赖和容器 image digest 记录。
本阶段 CPU PASS 不等于 GPU 推理 PASS，也不授权提交付费 Job。

P3 PASS：三模型固定 Revision/profile、Qwen 配置测试、Tokenizer/Schema/CPU 检查通过。

---

## P4 — 30 条严格配对三模型校准 Pilot

### 样本

- Gold72 锁定回归集 20 条；
- R60 severe calibration set 10 条；
- 先做跨集来源指纹去重。发现重复时不得静默替换或重复计入总体指标；由 Owner 指定 reserve，若无 reserve 就如实报告实际 unique count 并暂停 30 unique 的验收。

### 盲化与运行

- 每模型同一 30 条、同一可见历史/目标、同一 rubric/JSON contract。
- 独立 blind IDs、独立顺序、独立输入只读目录和输出私有目录。
- 模型看不到历史 A/B/C 和 Owner reference labels。
- 总计 90 个 checkpoint；每个都验证 input SHA、receipt SHA、source binding、model pin、profile SHA、rubric SHA。
- 不将 Gold72 和 R60 混成一个总体指标；分别报告。

### 授权

当前无 GPU 授权。P4 的真实 HF GPU 推理必须先向 Owner 汇报：
- 模型数量和 Job 数；
- 预计 GPU flavor、时长和成本；
- 输入/输出 Bucket 路径与 RO/RW；
- 每个 Job 的命令和 dry-run；
- 失败策略（attempt=1、无自动重试、无 namespace fallback）。
只有用户明确授权后才能提交。

### 指标

三个严重维度分别计算：
- confusion matrix；
- SUPPORTED precision/recall/F1；
- NOT_SUPPORTED false-negative/false-positive 解释；
- INSUFFICIENT_CONTEXT detection；
- 安全 SUPPORTED 漏报；
- exact quote validity；
- semantic evidence support rate。

六维分别计算：
- MAE、±1 误差率、分维系统偏差、与 Owner 参考分布差异。

模型一致率只作辅助，不替代 Owner 参考裁决。30 条结果不能宣传成生产准确率认证。

P4 PASS：90/90 可追溯；输出 schema/引用完整；所有严重误报/漏报逐案解释；类别覆盖足够；无严重安全漏报；模型互补性与成本评估完成；Owner 批准最终双模型。

---

## P5 — 审核器回归与最终模型组合冻结

建立独立回归分组：
- Gold72 development 20：用于 rubric 迭代；
- Gold72 locked 20：锁定回归，规则冻结后才解盲；
- R60 severe10：专项严重证据回归。

回归主题：
- NPC 主动性 vs 玩家自主权；
- Assistant 替玩家决定 vs NPC 自主行为；
- 可见硬规则冲突 vs 不可见规则臆测；
- safety 风险 vs 普通亲密/冲突描写；
- 引用存在但语义不支持；
- 必要上下文缺失；
- 模型 JSON/finish reason/引用修复失败；
- 旧 v3 Checkpoint 兼容和新 v4 Checkpoint 防串用。

输出：
- rubric v2 frozen SHA；
- final model profile IDs；
- regression SAFE；
- 误报/漏报分类；
- final A/B choice rationale；
- Owner approval record。

P5 PASS 后，才允许进入 1000 条正式审核。

---

## P6 — 1000 条正式批量审核与 Quality-v1

前置条件：
- P0-P5 全部 PASS；
- Owner 明确批准最终双模型；
- 1000 Stage 原始 manifest 和 A/B 输入 SHA 完整；
- 同案例 A/B 1,000/1,000 配对；
- 新 Job 明确预算授权。

执行：
1. 使用最终双模型审核相同 1,000 条。
2. A/B blind IDs 可不同，但 Owner crosswalk 必须精确一一对应。
3. 逐案核验 checkpoint、输入、模型和 rubric。
4. 分歧、SUPPORTED、INSUFFICIENT_CONTEXT 和 flag/score 冲突进入 Owner 定点复核。
5. 任一严重维度 SUPPORTED 不准入；任一维 INSUFFICIENT_CONTEXT HOLD；三维均 NOT_SUPPORTED 仍需通过六维评分和其他门槛。
6. 保留每个 Story 的 train/validation/test 隔离。
7. R50 完整元数据排除、世界组件证据、历史输入完整性和 CPU Tokenizer/Collator 仍是训练准入门槛。
8. 输出 Quality-v1 admission SAFE；不得为达到数量目标降低标准。

---

## 通用命令与交接回执模板

### 当前仓库状态

~~~bash
set -euo pipefail
git status --short --branch
git rev-parse HEAD
git log -5 --oneline --decorate
~~~

### 现有 Owner R60 配对/语义工具合成回归

~~~bash
PYTHONPATH=src python3 -m pytest tests/test_hf_pilot_pairwise_audit.py -q
~~~

### HF Runtime Doctor（CPU）

~~~bash
python3 -m storyforge_dataset.hf_runtime doctor --profile cpu --json
~~~

### Ruff / 编译（环境具备时）

~~~bash
ruff check src/storyforge_gold_quality src/storyforge_dataset/token_preflight.py
python3 -m compileall -q src/storyforge_gold_quality src/storyforge_dataset
~~~

### 每阶段 SAFE 最低要求

~~~json
{
  "private_values_emitted": false,
  "database_modified": false,
  "r50_body_accessed": false,
  "gpu_started": false,
  "quality_v1_admitted": 0,
  "training_authorized": false
}
~~~

以上字段按真实执行情况填写；不得把模板当成真实结果。

### 阶段汇报格式

- Phase / Status:
- Branch / Commit:
- 实际调用工具与执行命令:
- 输入数据集计数与 Manifest SHA（私有 SHA 不公开）:
- 实际完成数量:
- PASS / HOLD / REJECT / INSUFFICIENT_CONTEXT:
- 关键误报/漏报分类:
- SAFE 文件（仅泛化目录说明）:
- GitHub Commit / PR / Issue:
- 是否产生 HF Job / GPU 费用:
- 是否修改数据库/RolePlay/R50:
- 下一最小可执行动作:
