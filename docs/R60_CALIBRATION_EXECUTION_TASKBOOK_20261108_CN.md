# R60 下一阶段执行任务书：校准集冻结 → 三态证据审核 → 三模型配对 → 1000 条批量审核

> **当前权威状态（2026-11-10；覆盖下方未标明日期的旧 P2-A 待办叙述）**  
> **P0 PASS、P1 PASS、P2-A COMPLETE；P2-B NOT STARTED、P3 NOT STARTED、P4/P6 NOT AUTHORIZED。** Owner Mac 官方 Verifier SAFE 为 `OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED`：20/20 个案例、60/60 条语义复核，58 `SUPPORTS_VERDICT`、1 `INSUFFICIENT_CONTEXT`、1 `SEMANTIC_ENTAILMENT_NOT_ESTABLISHED_HOLD`，`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`owner_identity_cryptographically_attested=false`。两项语义 HOLD 是真实审核结果，不得通过改判消除。  
> **新 Agent 只从 P2-B 独立 30/90 held-out 参照集工程及 P3 三模型 CPU 预检接手，不重做 P0/P1/P2-A。** 最终官方 SAFE 与阶段收尾详见 [Issue #28 验收回帖](https://github.com/sunxu/storyforge/issues/28#issuecomment-6745451510)，执行提示词见 [2026-11-10 新 Agent 启动指令](R60_NEXT_AGENT_START_PROMPT_20261110_CN.md)。  
> PR #25 在本次核验时 Open/Draft，base `r60/canonical-a-v3-binding`；2026-11-10 核验前 HEAD `352fd48d50f5f24402b2bef849240833f6ab270e` 对应五组 Actions 均 completed/success。**本次文档提交会再次推进 HEAD；新 Agent 必须核对最新 HEAD 与 CI，不得沿用此快照。** 下方“P2-A 尚未开始”“下一步生成 20/60”“P2-A HOLD”等日期较早的章节均仅为历史记录，不得作为执行入口。  
> P2-A 80 个证据 locator 与 39 条历史完整性确认只落在派生文件，原件未修改；正式结论不等于训练准入。P2-B Locked20 + Severe10 不与 Development20 混包，不向模型泄露 held-out Owner labels。P4 GPU、P6 1000 条批量审核、SFT 均需单独授权。


## 2026-11-10 收尾与后续交接（唯一最新行动入口）

| 阶段 | 结果 | 新 Agent 工作 |
|---|---|---|
| P0 | PASS | 只读复用冻结集，不重跑、不重新分组 |
| P1 | PASS | 复用 Rubric v2.1 / Schema / Prompt / regression |
| P2-A Development20 | **COMPLETE**；20 cases + 60 checks；语义 58/1/1，保留两项 HOLD | 冻结留证，不重审、不修改原始 verdict |
| P2-B Locked20 + Severe10 | **NOT STARTED** | 独立 30 results / 90 semantic checks Builder + Verifier；synthetic PASS；Owner 私有 labels 与 model inference 严格隔离 |
| P3 三模型 | **NOT STARTED** | Qwen3/GLM-4/GLM-Z1 精确 revision 与 CPU tokenizer/template/collator/预算 preflight；实际型号差异须明示 |
| P4/P6 | **NOT AUTHORIZED** | 不启动 GPU/HF 推理/1000 批量审核/SFT |

### 接手行动与门禁

1. 阅读 [新 Agent 提示词](R60_NEXT_AGENT_START_PROMPT_20261110_CN.md)，实时核对 PR #25、Issues #26/#28、当前分支 SHA 与该 SHA 的五组 CI；不要将历史快照当当前结果。
2. 复用 P2-A 契约与测试实现 P2-B **独立版本化** 30/90 Builder/Verifier（旧官方 20/60 Verifier 不适用于 30/90）。先 synthetic/CPU 工程，后 Owner 私有 30 项裁决；真实不足继续 HOLD，不得静默改标签。Locked20/Severe10 的 Owner labels、ID Map、旧判断不得进入三模型推理输入。
3. 在不阻塞 P2-B 的前提下，并行准备 P3 只读三模型版本固定和 CPU 预检。CPU 资源如收费先授权；未经允许不发私有文本到外部服务；不启动 GPU/SFT。
4. 提交代码/测试/脱敏 SAFE 和文档；私有正文、映射、逐案证据、密钥仅留 Owner 私有目录。无 Owner Mac 连接则不假称已运行，给出最短受控指令。
5. Issue #28 维持 OPEN；PR #25 维持 Draft，合并另行审查。P2-A 已验收只是这一阶段的闭环，不是自动训练准入。

### P2-A 最终可复核的 SAFE（不含私人内容）

```json
{
  "schema": "storyforge_r60_owner_adjudication_results_safe_v2",
  "status": "OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED",
  "cases_verified": 20,
  "semantic_checks_verified": 60,
  "semantic_supported_count": 58,
  "semantic_insufficient_context_count": 1,
  "semantic_not_established_count": 1,
  "owner_identity_cryptographically_attested": false,
  "quality_v1_admitted": 0,
  "training_authorized": false,
  "gpu_started": false,
  "private_values_emitted": false
}
```

**说明：** 此 SAFE 为 Owner Mac 实际运行仓库官方 `scripts/r60_owner_adjudication_verify_v2.py` 的用户回执，非 GitHub CI 运行；不发布原始私有 JSONL。80 条 evidence locators、39 条 Owner 已批准的 history completeness、4 处 SUPPORTED Player Agency basis 类型均只在派生副本规范化。保留 58/1/1，未做 cryptographic identity attestation。旧模型的 AI Advisory 不冒充 Owner。

---

版本：v1.4 / 2026-11-10（P2-A 验收完成；P2-B/P3 执行版）  
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

- Qwen3-32B：旧 Revision 保留；新版本显式 Thinking=True。官方 Thinking 参数 不传 temperature.6、top_p=0.95、top_k=20、min_p=0；不使用 不传 temperature greedy。
- GLM-4-32B-0414：保留旧 Revision，读取其模型卡、tokenizer/chat template 和 generation_config。
- GLM-Z1-32B-0414：查询并固定完整 40 位 Revision；检查 vLLM、Tokenizer、Chat Template 兼容性。
- 任何模型的 Revision、template、runtime、generation config 不可用或漂移：HOLD，不自动换 pin。

### P3.2 代码要求

- 将 SamplingParams 从全局固定 不传 temperature 改成模型 profile 驱动。
- Qwen profile 显式：enable_thinking=true, 不传 temperature.6, top_p=0.95, top_k=20, min_p=0。
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


---

## 9. 2026-11-09 P2-A Owner approval and execution override (authoritative)

本节优先于前文任何较早的“工作区必须 clean”或“发现未提交修改就停止”要求。

### 已完成的决定与代码交付

- Owner 明确回复“采纳”，正式采纳全部 35 条 AI Advisory：Player Agency 16、Safety 19，保留原 `NOT_SUPPORTED`；verdict changes=0，semantic rechecks=0。
- AI Advisory 原文件和原始 20 results / 60 semantic checks 均保持冻结。
- PR #29 已 squash merge，合并提交：`24eb9f78de6f6e953d84a150d65f020da6ddb4ef`。
- 可复用 normalizer、单元测试和中文 Runbook 已进入当前分支。
- 合并提交六组 GitHub Actions 全部 completed/success（test、resolve-and-verify、runtime-quality-gates、synthetic-and-r57、r58-source-json-structure、r58-synthetic）。

### 不再要求 Owner Mac clean worktree

Owner 已明确要求：不考虑 Owner Mac 当前工作区存在未提交修改，按合理方式推进。因此：
- 不要求 clean status；
- 不执行 reset、clean、stash、checkout 覆盖或其他可能影响既有未提交修改的操作；
- 推荐新建独立 clone 到新目录，直接检出当前 GitHub 分支和合并提交；原 worktree 完全不动。
- GitHub 当前分支为代码事实来源；不要依赖旧本地 worktree 中可能尚未同步的代码。

### 当前唯一执行项：使用真实私有包运行 Owner-approved normalizer

工具：`scripts/r60_owner_approved_package_normalizer_v1.py`  
Runbook：`docs/R60_P2A_OWNER_PACKAGE_NORMALIZER_V1_CN.md`

工具必须读取六份私有输入：原始 blind packets、原始 results、原始 semantic checks、schema、35 行 AI Advisory、AI Advisory SAFE。前四项中的 packet/results/semantic/AI Advisory JSONL 必须通过私有 SHA pin 精确校验；所有私有文件 0600、目录 0700。

执行要求：
1. 原始文件只读，不覆盖、不移动。
2. 显式 `--owner-approved`，对应 Owner 已明确采纳全部 35 条。
3. 输出必须是新的、此前不存在的私有目录。
4. 仅对 35 个已批准 pair 将 `context_coverage.history_complete` 从 false 改为 true；verdict、reasoning、missing_context、evidence quote/offset/role、rule_basis 和其他 coverage 字段不变。
5. 规范化 60 个 target locator（index -1→0、component_ref 清空）和 20 个 history locator（只清空 component_ref）；其他定位信息不变。
6. 原始 60 条 semantic checks 原样复制；先在内存运行完整 verifier，之后 create-only 写副本，再运行官方 CLI verifier。
7. 成功必须返回 20 cases / 60 checks / 35 history confirmations / 60 target locator normalizations / 20 history locator normalizations，并生成正式私有 Manifest + SAFE。所有 semantic HOLD 保留。
8. SAFE 必须明确 `quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`private_values_emitted=false`。

本会话已完成 GitHub 代码与 CI 交付，但尚未取得 Owner Mac 六份真实私有输入，故尚未执行 normalizer；不得将代码合并等同于 P2-A 完成。拿到真实 SAFE/SHA 回执后才可判定 P2-A PASS。

本次不启动 P2-B、P3、HF Job、GPU、1000 条审核或 SFT。


---

## 10. 2026-11-09 Owner additional approval: 4 SUPPORTED cases; normalizer v2

Owner has explicitly approved all four AI advisory recommendations for SUPPORTED / player_agency cases (source result rows 5, 6, 11, 19). The complete approved scope is now 39 exact case-dimension pairs:

- 35 NOT_SUPPORTED pairs: Player Agency 16 + Safety 19; retain their original verdicts.
- 4 SUPPORTED pairs: Player Agency 4; retain their original verdicts.
- For all 39, set only `context_coverage.history_complete=true` in the isolated derived package.
- Verdict changes: 0. Semantic rechecks: 0. Do not modify the original 60 semantic checks.

Versioned implementation:
- `scripts/r60_owner_approved_package_normalizer_v2.py`
- `tests/test_r60_owner_approved_package_normalizer_v2.py`
- `docs/R60_P2A_OWNER_PACKAGE_NORMALIZER_V2_CN.md`

v2 verifies both AI Advisory SAFE contracts, 35-row and 4-row JSONL cardinality, the 4-row worksheet exact order and source binding, the unchanged original semantic check for each SUPPORTED case, exact pair sets, six pinned input SHA-256 values, private file permissions, and create-only output. It calls the unchanged pure verifier and unchanged official CLI verifier. v1 remains intact.

Do not run v2 against real private data until CI for its commit is PASS. Use a fresh output directory ending `owner-approved-v2`; never reuse the v1 output directory. Expected counts: 20 cases, 60 semantic checks, 39 history completeness confirmations, 60 target locator normalizations, 20 history locator normalizations. Preserve all semantic HOLDs. The output SAFE must keep quality admission 0 and training/GPU false.

Owner approval is complete, but P2-A is not yet PASS until the new v2 package is generated from the actual pinned private inputs and the official verifier passes. No P2-B, P3, GPU/HF Job, bulk review, or SFT authorization is implied.


### v2 CI 验证结果（2026-11-09）

最终代码提交 `28d9efa9b186484b61163e150a21316c9cc1f8cb` 六组 Actions 全部 completed/success：test（Ruff + pytest）、resolve-and-verify、runtime-quality-gates、synthetic-and-r57、r58-source-json-structure、r58-synthetic。最初的 Ruff F841/F821 已修复。v2 允许进入真实私有输入执行阶段；CI 通过不等于 P2-A 正式验收通过。

## 11. 2026-11-09 方向校正与 P2-A Rule Basis HOLD

Gold72 Development-20 / Locked Regression-20 来自 A V3 / B2 disagreement set，是严重问题审核规则校准样本，不是按文学质量选出的优秀回复。20 条三维裁决不能作为整体文学质量评级；SUPPORTED / NOT_SUPPORTED 不等于六维 Quality PASS。

新增 Positive Gold 独立计划：`docs/R60_POSITIVE_GOLD_SELECTION_PLAN_CN.md`。候选来源为已冻结的 1,000 条技术候选池；内容筛选复用 Quality-v1 六维门槛（中文表达4、人物一致性4、NPC主动性3、玩家自主权4、规则忠实度4、叙事连贯性4）及三项严重旗标。先经 Owner 确认 Reviewer 和小批范围，再按既有 5/25 受控批次执行；不凑数量，不把 AI-only 建议冒充 Owner Gold，不自动产生训练准入。此计划仅文档化，未启动真实审核。

P2-A 当前 HOLD：原 Owner results 的 4 条 SUPPORTED / Player Agency（result rows 5/6/11/19）均为 `basis_type=player_agency`，而 v2.1 verifier 要求 `player_agency_boundary`。Normalizer v2 已加入 fail-closed guard，不会自动改写原始或派生 rule_basis。需 Owner 明确确认是否允许在独立派生副本中对这 4 个精确 pair 做类型标签规范化；其他字段、verdict、semantic checks 均保持不变。不得创建正式输出目录，直到此问题解决。


### 2026-11-09 Owner 批准 basis_type 精确规范化

Owner 已批准仅在派生副本中，将 4 条 SUPPORTED / Player Agency 的 `basis_type` 从 `player_agency` 规范化为 `player_agency_boundary`。实现严格限定 4 个精确 pair；原始 JSONL、verdict、evidence、其他 rule_basis 字段和 60 semantic checks 不变。Normalizer 的私有 approval 记录明确列出映射和不变性断言，SAFE 输出 `basis_type_normalized=4`。真实 Owner Mac 私有包执行及官方 CLI verifier 尚未完成前，P2-A 仍为 HOLD。


### 2026-11-09 semantic reviewer binding 修复

60 条语义复核诊断结果为 reviewer_role/ref 全部缺失。鉴于 Owner 已确认这些复核均由 Owner 在独立裁决后完成，Normalizer v2 在派生副本中补充统一 role/ref，并记录为回溯性元数据绑定；任何冲突值均 fail-closed。原始 semantic checks 不变。SAFE 明确标注未进行密码学身份认证。P2-A 仍须通过真实私有包和官方 verifier 验收。



## 2026-11-09 权威状态更正：P2-A 语义复核身份

Owner 已明确确认：原 60 条 semantic checks 由 Owner AI 生成，未经 Owner 逐项最终确认。此前关于 Owner 已完成 60 项独立语义复核、允许在派生副本回溯补写 `OWNER_INDEPENDENT` / reviewer_ref 的描述不再有效。Normalizer v2 已 fail-closed：没有真实 Owner reviewer metadata 的 AI 生成文件不能被提升为官方 Owner semantic checks。

按 `docs/R60_P2A_SECOND_MODEL_CROSS_REVIEW_PROTOCOL_V1_CN.md`，先由不同模型提供方/模型家族进行盲交叉审核，结果仅为 AI Advisory；随后 Owner 对全部 60 项作最终复核，独立形成正式语义判断。第二模型不得读取第一模型输出；不向第二模型暴露任何旧 AI semantic checks。Owner 必须保留实际 HOLD，不追求全绿。P2-A 官方 20/60 合同不变，P2-B 30/90、P3、GPU/HF Job、SFT 均未获授权。


## 2026-11-09：CLI Proxy 外部模型调用客户端

新增 `scripts/r60_p2a_openai_compatible_review_client.py`，支持远程 HTTPS OpenAI-compatible Chat Completions、非流式调用、默认 Claude Opus 5.5 High 模型别名、每批 5 案例/4 批、有限网络重试、严格 60 行输出校验和私有断点续跑。API Key 仅从环境变量读取；预检不调用外部服务，实际调用必须显式 `--execute --allow-private-data-egress`。工具不会读取 Owner ID Map、旧 AI semantic checks 或旧 AI advisory。当前未调用模型，待 Owner Mac 配置准确 CLI Proxy endpoint 和环境变量，并通过本地 preflight 后执行。模型输出仍只是 AI Advisory，不解锁 P2-A/P2-B/P3/GPU/SFT。


## 2026-11-09：4Router HTTP 400 诊断

Claude Opus 5.5 首批请求返回 HTTP 400，尚未获得任何有效审核结果。客户端已更新为将每次 HTTP 错误体保存至本地 0600 私有诊断文件，并只在 SAFE 中输出 HTTP 状态及 error type/code/param；不输出服务端 message、请求正文或密钥。继续使用原输出目录加 `--resume`，先读取安全诊断字段，确认拒绝原因后再修复；不得删除/覆盖批次文件或盲目改变请求参数。Owner 已授权的外发范围仍仅限本批 20 条 Development 盲包至 4Router。GPU/HF Job/SFT 未启动。


## 2026-11-09：4Router Claude system 参数格式修复

已根据 Owner 提供的 400 错误原文，将 CLI Proxy 请求从 `messages[0].role=system` 改为顶层 `system` 字段，messages 只保留 user 消息；不传 temperature，其他请求边界不变。新增合成测试。提交：`c1a3d4f`（客户端）、`807495f`（测试）、`c6a5d5c`（协议）。修复尚待 CI 与真实单批调用验证。使用原输出目录 `--resume`，保留原 HTTP 错误记录；不覆盖已验证成功批次。未启动 GPU/HF Job/SFT。


## 2026-11-09：Claude Opus 5.5 第二模型交叉审核调用完成（Advisory only）

Owner 提交的真实 SAFE 回执：

- status：`CROSS_REVIEW_MODEL_CALLS_COMPLETE__ADVISORY_ONLY`
- model：`claude-opus-5-5`
- cases：20；dimensions：60；rows_validated：60；batches：4/4
- reviewer_type：`AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`
- private_data_egress：true（仅此前明确授权的 Development-20 盲包发往 4Router）
- owner_review_completed：false
- gpu_started：false；training_authorized：false；private_values_emitted：false

客户端顶层 `system` 兼容修复对应分支 HEAD `1d337afcea22a52ec0b553b730d3f9b2200fa5c5` 的五项 Actions 均 completed/success：CI、R60 HF Runtime CI、R60 HF CPU dependency profiles、Gold Quality Pipeline、R58 scoped synthetic。该结果验证代码/合成回归，不等于 Owner 内容裁决通过。

**当前唯一下一步：Owner 对 60 项 Claude Advisory 与原始 20 条 Owner results / Rubric v2.1 逐项核对，形成自己的 60 项最终语义判断。** Claude 结论不能自动采纳、不能回填成 Owner semantic checks；逐项保留分歧和真实 HOLD。Owner 最终记录须使用正式七字段合同并由官方 verifier 验证。P2-A 在 Owner 60 项最终复核及官方 verifier PASS 前仍为 HOLD；不启动 P2-B、P3、GPU/HF Job、1000 条审核或 SFT。
