> **当前执行入口（2026-11-10，优先级最高）：** 本任务书后续大量章节属于 P0–P3 历史记录，不能据此启动旧任务。当前阶段是 P4 Worker CLI 工程验收。请先阅读 [P4 下一阶段接手任务书](R60_P4_NEXT_AGENT_HANDOFF_TASKBOOK_20261110_CN.md) 与 [P4 新 Agent 提示词](R60_P4_NEXT_AGENT_START_PROMPT_20261110_CN.md)。最新已核验基线 HEAD 为 `a1db1ac70fd3777d78460eee58e7d2b891867c40`，三项 CI 全部 PASS；后续 HEAD 的 CI 必须重新核验。HF 403/OAuth/Bucket 排查已按 Owner 要求暂停，HF 任务由 Owner 在 Mac CLI 执行；ChatGPT 不提交 Job、不测试 Bucket、不修改 OAuth。不得启动正式推理、GPU、1000 条审核或 SFT。

---

# 2026-11-10 最新权威执行状态（P2-B 官方 Verifier 已完成；优先于本文全部历史状态）

**本节为当前唯一状态依据。下方较早日期的 P2-B/P3 未开始、Owner review pending、Verifier HOLD 等内容均为历史记录，不得作为当前待办。**

## 阶段状态

| 阶段 | 当前状态 | 说明 |
|---|---|---|
| P0 | PASS | Gold72 40 条（Development20 + Locked20）与 R60 Severe10 冻结；不重做 |
| P1 | PASS | Rubric v2.1 / Schema / Prompt / synthetic regression；不修改、不回退 |
| P2-A | COMPLETE | Owner 20/20 + 60/60 官方验证；语义 58 支持、1 上下文不足、1 语义未建立；保留 HOLD |
| P2-B | **OWNER REVIEW + OFFICIAL VERIFIER COMPLETE** | 30/30 cases、90/90 semantic checks，官方 SAFE 状态见下文 |
| P3 | IN PROGRESS / CPU PREFLIGHT PENDING | 三模型静态 revision/config/template 元数据核查完成；Tokenizer/template 执行、SHA、输入预算与模型 profile 决策未完成 |
| P4 | NOT AUTHORIZED | 30 条三模型配对推理/GPU 需单独明确授权 |
| P5 | NOT STARTED | 模型结果回归、误报漏报分析及最终模型选择 |
| P6 | NOT AUTHORIZED | 1000 条正式批量审核需独立授权 |
| SFT | NOT AUTHORIZED | 训练授权与 Quality admission 是独立门禁 |

## P2-B 官方 Owner Results Verifier 回执（Owner Mac 提供）

```json
{
  "schema": "storyforge_r60_p2b_owner_results_safe_v1",
  "status": "P2B_OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED",
  "cases_verified": 30,
  "semantic_checks_verified": 90,
  "semantic_supported_count": 57,
  "semantic_insufficient_context_count": 33,
  "semantic_not_established_count": 0,
  "owner_identity_cryptographically_attested": false,
  "private_values_emitted": false,
  "quality_v1_admitted": 0,
  "training_authorized": false,
  "gpu_started": false
}
```

解释：
- 30/30 Owner Results 与 90/90 Semantic Checks 已被官方 Verifier 接受；P2-B Owner review/技术验收完成，语义 HOLD 保留。
- 57/33/0 是语义复核结论计数，不是三维 Verdict 计数，不是 Quality-v1 PASS 数，也不等于 30 个案例训练准入。
- Safety 第21、22条经 Owner 明确二次裁决均为 `INSUFFICIENT_CONTEXT`；原始 `SUPPORTED` 与修订审计记录保留。只修订这两个 Safety 维度，其他 88 个维度项未改；Rubric v2.1 未修改；没有虚构 Rule ID。最终 33 项语义 HOLD 包含这些上下文不足记录。
- Hard Rule 30 条均为 `INSUFFICIENT_CONTEXT`；Player Agency 3 `SUPPORTED` / 27 `NOT_SUPPORTED`；Safety 修订后为 0 `SUPPORTED` / 27 `NOT_SUPPORTED` / 3 `INSUFFICIENT_CONTEXT`（此三维分布依据已确认 Owner 修订记录；官方 SAFE 本身只报告语义结论计数）。
- Owner 身份未获密码学认证；不声称 cryptographic attestation。
- P2-B 的私有正文、blind IDs、ID Map、逐案结果不得上传 GitHub；公开文档只记录 SAFE 聚合值。

## P3 静态模型固定事实

静态核查文档：[R60_P3_MODEL_STATIC_PREFLIGHT_20261110_CN.md](R60_P3_MODEL_STATIC_PREFLIGHT_20261110_CN.md)。

- Qwen/Qwen3-32B revision：`9216db5781bf21249d130ec9da846c4624c16137`
- zai-org/GLM-4-32B-0414 revision：`8dea913c41b543527c2860fb6f3c15c202f24aeb`
- zai-org/GLM-Z1-32B-0414 revision：`8eb2858992c1f749e2a6d4075455decc2484722d`
- 三者保守共同原生上下文上限：32768 tokens。不得将 tokenizer 的 128k/131k model_max_length 当作模型原生上下文证明。
- Qwen Thinking：需显式 enable_thinking=true；模型卡建议 temperature=0.6/top_p=0.95/top_k=20/min_p=0。
- GLM-4：generation_config 未固定 sampling 参数；不得照搬 Qwen 参数。
- GLM-Z1：模型卡 sampling 表与 greedy inference 示例冲突；必须先通过 Owner 决策或证据充分的技术核实解决，不得自行选择。
- GLM-4 与 GLM-Z1 属同一 GLM4 架构家族，不能当作两个独立家族投票。

## 新 Agent 唯一接手目标：完成 P3 CPU-only 预检

1. 先重新读取本提示词、最新任务书、执行任务书、交接总览、交接索引、P3 静态核查文档及 Rubric v2.1。
2. 实时查询 PR #25 当前 head/base/draft、分支 HEAD、Issue #26/#28，以及当前精确 HEAD 的五组 Actions。本文中的 HEAD/CI 只作更新前快照，不可沿用。
3. 检查现有代码、依赖 lock、CI profile 和 HF runtime 工具；复用既有实现，不另建重复 reviewer。
4. 仅下载三个固定 revision 的 tokenizer/config/template 所需文件，不下载模型权重；记录实际 SHA-256。CPU 本地执行 tokenizer load、chat-template render、generation prompt、中文多轮消息、Thinking 前缀/开关及模板一致性检查。
5. 对 tokenizer embedded template 与独立 Jinja template 做实际对比；差异必须 HOLD，明确 pin 实际运行时所用模板。
6. 在 synthetic-only 数据上验证共享 32768 context ceiling、prompt/output budget、截断行为、finish reason/schema 与 90 输入长度预算。不得读取或使用 P2-B held-out 私有文本、Owner labels 或 ID Map。
7. 固定 GLM-4 sampling profile；GLM-Z1 sampling/greedy 冲突需给 Owner 一份短决策依据，未决前 profile 保持未冻结。所有模型的 prompt、rubric、runtime、tokenizer/template SHA 和参数必须可追溯。
8. 输出 CPU-only SAFE、报告与可复现命令；更新本任务书、执行任务书、交接总览、索引、P3 静态文档和 Issue #28。
9. 完成后提出 P4 30 条严格配对三模型实验的方案、资源预算与授权请求，但不得自行提交 HF Job 或启动 GPU。

## 资源与隐私门禁（不可放宽）

- 允许：GitHub 代码/文档/合成测试；已获授权的本地 CPU-only tokenizer/template 预检。
- 任何可能收费的 CPU 云资源先取得明确授权；默认使用本地 CPU。
- 禁止：GPU、付费 HF Job、模型 inference、向外部服务发送 P2-B held-out 文本、1000 条批量审核、SFT。
- `quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。
- 不改 P0/P1/P2-A/P2-B 历史裁决，不修改 Rubric v2.1，不重做 Owner review，不触碰生产数据库/RolePlay，不提交私有正文、ID Map、tokens、DSN。
- PR #25 继续 Draft；Issue #28 继续 OPEN；不自动合并。

## 每次交付要求

报告真实执行命令、输入 revision/hash、输出 SAFE schema/status、测试与 CI 结果、commit SHA、修改文件、资源消耗、未解决 HOLD。未执行步骤不得报告 PASS。

---

# 2026-11-10 最新执行补充（优先级最高）

**P2-B Owner review 已完成，官方 30/90 验收仍 HOLD；P3 静态模型核查已完成，CPU tokenizer/template 预检待执行。** 本补充覆盖下方所有较早的 P2-B NOT STARTED / P3 NOT STARTED 状态。

- Owner 已确认 30/30 案例三维裁决、90/90 语义复核。Verdict：Hard Rule 30 INSUFFICIENT_CONTEXT；Player Agency 3 SUPPORTED / 27 NOT_SUPPORTED；Safety 2 SUPPORTED / 27 NOT_SUPPORTED / 1 INSUFFICIENT_CONTEXT。Semantic conclusions：59 SUPPORTS_VERDICT、31 INSUFFICIENT_CONTEXT、0 DOES_NOT_SUPPORT_VERDICT。
- **Safety 第21、22条继续 HOLD 在规则依据层**：Owner 的 SUPPORTED Verdict 与语义结论保留；公开 Rubric v2.1 没有可核验的具体规则 ID / 版本 / scope 注册表。不得臆造 Rule ID 或静默改写 Verdict。
- ChatGPT 工作副本完成 30 results / 90 checks 合并、target locator 规范化、精确 quote、schema 与 evidence-index 覆盖预检；它不是 Owner Mac 正式私有包，也不是官方 Verifier 回执。官方 30/90 Verifier 与 Final SAFE 尚未运行/生成。
- P3 已核实并固定 Hub revisions：Qwen3-32B `9216db5781bf21249d130ec9da846c4624c16137`；GLM-4-32B-0414 `8dea913c41b543527c2860fb6f3c15c202f24aeb`；GLM-Z1-32B-0414 `8eb2858992c1f749e2a6d4075455decc2484722d`。静态配置/模板已检查；CPU tokenizer/template/token-budget 未执行。GLM-Z1 官方 sampling 表与 greedy 推理示例冲突，需先明确 profile。
- 公开 SAFE 进度：[P2-B 30/90 聚合记录](evidence/R60_P2B_OWNER_30_90_PROGRESS_SAFE_20261110.md)；[P3 静态预检记录](R60_P3_MODEL_STATIC_PREFLIGHT_20261110_CN.md)。
- 当前资源门禁：`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`、`hf_jobs_submitted=0`。不启动 1000 条审核或 SFT。PR #25 保持 Draft，Issue #28 保持 OPEN；实时 HEAD/CI 以 GitHub 为准。

---

# StoryForge R60 下一 Agent 交接任务书

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

版本：v1.3（P2-A 验收完成；P2-B/P3 接手版）  
日期：2026-11-09  
仓库：`sunxu/storyforge`  
工作分支：`r60/gold192-history-v3-adapter`  
PR：[#25](https://github.com/sunxu/storyforge/pull/25)（当前 Open / Draft；接手时重新核验）  
主线 Issue：[#26](https://github.com/sunxu/storyforge/issues/26)  
执行跟踪 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)

> **本任务书是交给下一位 Agent 的正式工作指令。** P0 校准集冻结与 P1 Rubric v2.1 工程实现均已 PASS；下一 Agent 从 P2 v2.1 Development-20 盲审包生成开始，不得重新执行 P0/P1。本文中的早期 P0/P1 状态段落均为历史记录，当前状态以第 8.25 节及接手时实时 GitHub 核验为准。



## 0.1 当前接手状态（2026-11-09；接手时必须重新核验）

- PR #25：Open / Draft；base `r60/canonical-a-v3-binding`；当前 head 必须在接手时实时读取。
- 历史核验快照 HEAD `4190c6fe895080d99901cb4c5eb3f221c6948d6d` 的五组 Actions 当时均 completed/success（run IDs 见 8.25）。其后交接文档又有校正提交，故该 SHA 已不是当前 HEAD；不得沿用旧 SHA 的 CI 结论。接手时对 PR 当前精确 head 重新核验五组 Actions。
- P0：`CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`；Gold72=40、R60 Severe10=10；Gold72 Development/Locked=20/20；Gold72↔R60 exact history/target/full-history-target overlap=0；unique source cases=50。
- Gold72 分层按案例，不要求 Story 互斥：Development Story=5、Locked Story=6、shared Story=5、`story_disjoint=false`，这是 Owner 已确认的预期结果。
- P1：Rubric v2.1、Schema、prompt、合成回归及旧 v3 兼容 = PASS。Rubric version 为 `r60_severity_rubric_v2_1`。
- P2-A：v2.0 六文件包已 SUPERSEDED；v2.1 Development-20 新包尚未生成；Owner 20 条裁决与 60 条语义复核未开始。
- P2-B：Locked20 + Severe10 的 30 条 held-out Owner results / 90 条 semantic checks 尚未准备。
- P2-B：Locked20 + Severe10 的 30 条 held-out Owner reference labels / 90 条语义复核尚未准备；这是 P4 前置，必须在 P2-A 与 Rubric/prompt 冻结后单独实现和验收。
- Quality-v1 admitted=0；training_authorized=false；无 GPU 推理、1000 条批量审核或 SFT 授权。

**当前第一项工作：P2-A v2.1 Development-20 新包 dry-run → 显式 --write。P2-B 的 30/90 held-out labels 是后续 P4 前置；不得混包，也不得直接使用当前固定 20/60 的 verifier。不得从 P0 重新开始。**

## 1. 任务目标

继续完成 StoryForge R60 Quality 校准与模型选型：从已完成的 P0/P1 接手，完成 P2-A Development-20 的 20 条裁决 + 60 条语义复核，并完成 P2-B Locked20 + Severe10 的 30 条 held-out Owner 参考标签 + 90 条语义复核；随后推进 P3 三模型固定与 CPU 预检。P4/P6 仍须另行授权。最终目标仍是为冻结的 1,000 条候选建立可信的双模型审核结果。

当前执行顺序：

1. **P0 已 PASS**：Gold72 40 条与 R60 Severe10 10 条已冻结，20/20 案例分层及跨集精确去重完成；不得重做。
2. **P1 已 PASS**：当前标准为 `r60_severity_rubric_v2_1`；不得退回旧 v2.0。
3. **当前 P2-A**：生成全新的 v2.1 Development-20 盲审包，完成 Owner 20 条三维裁决 + 60 条语义蕴含复核，并运行私有验证器。
4. **P2-B**：在 P2-A 与 Rubric/prompt 冻结后，独立准备 Locked20 + Severe10 的 30 条 Owner reference labels + 90 条语义复核；先实现专用 builder/verifier。
5. **P3**：固定 Qwen3-32B、GLM-4-32B-0414、GLM-Z1-32B-0414 的完整 Revision/profile，完成 CPU/Tokenizer/Chat Template/Schema 预检。
6. **P4**：30 条严格配对三模型 Pilot，共 90 个独立结果；GPU 必须先获得单独明确授权。
7. **P5**：真实案例回归、误报/漏报解释、冻结最终双模型。
8. **P6**：所有门槛通过且 Owner 明确授权后，才对 1,000 条候选开展正式批量审核。

**本任务不包含直接启动 SFT。** Quality-v1 admission、训练数据冻结和 GPU SFT 授权是不同审批事项。

## 2. 当前已知事实（不得改写）

### 2.1 R60 Pilot10

- Reviewer A：Qwen3-32B，5 条，5/5 REJECT。
- Reviewer B：GLM-4-32B-0414，5 条，5/5 REJECT。
- A/B 两槽来源不相交：`matched_cases=0`、`unique_source_cases=10`。
- 10/10 Checkpoint receipt 与 input SHA 绑定已通过。
- 因为没有相同案例配对，不能声称 A/B 逐案一致，也不能计算双模型逐案一致率。
- Reviewer C：10/10 盲输入和结果绑定完成；hard_rule 10 NOT_SUPPORTED；player_agency 3 SUPPORTED / 7 NOT_SUPPORTED；safety 5 SUPPORTED / 1 NOT_SUPPORTED / 4 INSUFFICIENT_CONTEXT。
- C 的模型身份独立验证和 Reviewer C 独立性均未证明；C 结果不是 Owner ground truth。
- 严重语义最终裁决尚未完成。

### 2.2 R60 1,000 条来源 crosswalk

Owner Pairwise SAFE 已验证 A/B 两槽各 1,000/1,000 source binding、输入 SHA 和跨槽同源绑定；10/10 Pilot Checkpoint 回执验证通过。**不要重复执行这项已通过的旧来源审计。**

这不代表 1,000 条已完成 A/B 推理：既有批量 Stage audit 曾报告 A=0、B=0、complete_pairs=0、HOLD=1000。不得把来源映射 PASS 写成审核 PASS。

### 2.3 Gold72 40 条（P0 已正式冻结）

- Gold72 A V3/B2：72 条可比较，40 条分歧、32 条一致；准确的 40 条 disagreement 案例已冻结。
- Owner 私有 P0 manifest 已将 40 条按案例分为 Development=20、Locked Regression=20。
- Development 涉及 5 个 Story，Locked 涉及 6 个 Story，共享 Story=5，`story_disjoint=false`。**Owner 明确允许 Story 跨集合；保持案例级 20/20，不得擅自改成 Story 互斥。**
- Gold72↔R60 exact history / target / full-history-target overlap 均为 0，唯一来源 50。
- 历史 Reviewer C aggregate=38/1/1、Owner resolution=30/4/6 仍是历史记录；Gold72 C execution record / independence 未证明，不把 C 结果当 Owner ground truth。上述历史限制不阻断已完成的 P0。
- P0 正式 SAFE：`CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`；四份私有产物已写入，`manifest_files_written=4`。不得重复执行 P0。

完整 72-row source 与 suffix72 72 READY Stage 均不得替代 Gold72 40-case 集合。

### 2.4 当前准入边界

- Quality-v1 admitted：0。
- 训练授权：false。
- 本任务开始时没有新的 GPU Job 授权。
- 1000 条批量审核尚未执行。
- GPU 推理、1000 条批量审核和 SFT 均须按任务书分别取得明确授权。

## 3. 接手时先做的事情

### 3.1 刷新 GitHub 状态

在 Owner Mac 的 StoryForge 仓库执行：

~~~bash
set -euo pipefail
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
printf 'HEAD='; git rev-parse HEAD
git status --short --branch
git log -5 --oneline --decorate
~~~

该路径是已确认绑定 `r60/gold192-history-v3-adapter` 的 worktree；不要改用 `/Users/keedle/workspace/storyforge`（该目录此前为 detached HEAD）。先检查 `git status`；若有未提交修改，停止并报告，不得覆盖。检查 PR #25 head、base、Draft 状态和当前 HEAD 是否一致；重新核验当前 HEAD 的 GitHub Actions。不要 reset、force-push、merge 或关闭 PR。

### 3.2 阅读顺序

1. 本任务书。
2. [交接包索引](R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md)。
3. [交接总览](R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md)。
4. [详细 P0–P6 执行任务书 v1.3](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)：P0/P1 已完成，当前从 P2-A v2.1 开始；P2-B held-out 30/90 是 P4 前置；P0/P1 命令只作历史记录。
5. [三模型校准计划](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md)。
6. [HF Job 工程规范](standards/HF_JOBS_ENGINEERING.md) 和 [CPU Stage 预检 Runbook](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md)。

## 4. 阶段任务与验收

### P0 — PASS（已完成；禁止重做）

正式 SAFE：`CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`，`manifest_files_written=4`，`private_values_emitted=false`。

- Gold72：A V3/B2 可比较 72 条，分歧 40、一致 32；准确 40/40 已冻结。
- R60 Severe10：10/10 唯一来源案例；既有 A/B Checkpoint receipts A=5、B=5；Pilot10 A/B matched_cases=0。
- Gold72 Development/Locked Regression = 20/20，按案例分层；Development Story=5、Locked Story=6、shared Story=5，`story_disjoint=false`。**Owner 明确允许 Story 跨集合，不得改成 Story 互斥。**
- Gold72↔R60 exact history / target / full-history-target overlap 均为 0；unique source cases=50。
- semantic near-duplicate detection=false；不声称已完成语义近重复检测。
- Gold72 C execution/independence 未证明；R60 C execution verified=true、independence verified=false。保留历史限制，但不阻断已完成的 P0。
- P0 manifest、dedup receipt、aggregate SAFE 均已在 Owner 私有目录 create-only 生成；不得重复运行 P0 Runner 或已通过的旧 1000 crosswalk/Pilot10 Checkpoint audit。

Quality-v1 admitted=0；training_authorized=false。P0 PASS 不等于 Quality PASS 或训练授权。

### P1 — PASS（Rubric v2.1 已冻结；禁止回退旧 v2）

当前唯一有效标准：`r60_severity_rubric_v2_1`，公开文件 `docs/R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md`。

已通过内容：
- 三维三态 Schema：`storyforge_severity_evidence_review_v2`。
- Semantic check：`storyforge_severity_semantic_entailment_check_v2`。
- Rubric v2.1 文本、代码内 RUBRIC_TEXT、Prompt/schema 描述一致。
- exact quote 与 semantic entailment 分离验证。
- 来源/权利/版权/隐私/数据使用授权/数据隔离不属于案例内容审核证据；不得因缺少这些材料而 HOLD。
- 玩家在故事内明确表达的拒绝、同意和行动边界仍是内容语义证据。
- 合成回归、Ruff、旧 v3 checkpoint / Reviewer-C v1 兼容测试通过。

P1 v2.1 的最终 CI 记录见本任务书 8.22–8.25。不得再运行旧 v2 prompt/标准，不得重做 P1。

### P2 — Owner 独立盲裁决（当前从 P2-A 开始）

#### P2-A：Gold72 Development-20（当前执行）

- v2.0 六文件包已 SUPERSEDED，不得用于裁决、覆盖或删除。
- 在新目录生成 Rubric v2.1 Development-20 盲审包；只读取 P0 Gold72 manifest 与 SHA pin 的 Gold72 C blind source packet。
- Owner 只查看新 blind packets、instructions、schema 和公开 Rubric v2.1；不得打开 ID Map、P0 manifest、旧 A/B/C、旧 Owner resolution、Locked20 或 Severe10。
- 完成 20 条 Owner 三维裁决 + 60 条逐维语义复核；字段与严格验证见本任务书 8.23。
- DOES_NOT_SUPPORT_VERDICT 和 INSUFFICIENT_CONTEXT 均按验证器规则保留 HOLD；不能伪装 PASS。

#### P2-B：Held-out Owner reference labels（P4 前置；P2-A 完成后另行启动）

- 样本为 Gold72 Locked Regression 20 + R60 Severe10 10，共 30 条。
- P2-A 通过且 Rubric/prompt 冻结后，另行取得 Owner 确认，使用独立 blind IDs / 顺序 / 输出目录生成 held-out packets。
- 完成 30 条 Owner 结果 + 90 条语义复核；标签只留 Owner 私有区，直到 P4 三模型预测及 checkpoint 冻结后才允许对照。
- 当前 verify_owner_results() 固定 20/20/60；不得把 30/30/90 输入现有验证器。P2-B 必须先有独立版本化 builder/verifier 与合成回归，不能放宽 P2-A 合同。

**P2 PASS**：P2-A 20+60 与 P2-B 30+90 均通过各自验证；所有 HOLD 保留；Owner 标签与模型/Prompt 开发隔离；不把结构验证 PASS 等同于 Quality-v1 admission。

### P3 — 下一阶段（P2 验收后进入）：三模型固定与 CPU 预检

模型角色：
- A：Qwen/Qwen3-32B，保留旧 Revision；新 profile 显式 Thinking=True。
- B：zai-org/GLM-4-32B-0414，保留旧 Revision。
- Challenger：zai-org/GLM-Z1-32B-0414，先固定完整 40 位 Revision。

Qwen Thinking=True 使用模型官方建议 profile：不传 temperature.6、top_p=0.95、top_k=20、min_p=0；不得沿用统一 不传 temperature greedy。GLM 参数必须按各自固定 Revision 的官方 generation config/template 确定，不能照搬 Qwen 参数。

依赖基线不可丢失：
- `transformers==4.57.1`
- `sentencepiece==0.2.1`
- `jinja2==3.1.6`

R58 已证明缺 Jinja2 会导致 Chat Template ImportError，R60 是重复故障。使用 `requirements/hf-quality-reviewer.in` 和 hash-pinned `requirements/hf-quality-reviewer.lock`；目标环境提交前执行 pip check、版本/import probe 和目标 Tokenizer `apply_chat_template`。失败即停止，不换 flavor/namespace，不重复付费试错。

CPU 预检覆盖三个模型的 tokenizer/template、Qwen Thinking prompt、schema、90 个输入 token budget、依赖和镜像信息。CPU PASS 不等于 GPU 推理 PASS。

**P3 PASS**：三模型固定 Revision/profile、Qwen 配置测试、Tokenizer/Schema/CPU 检查通过。

### P4 — 30 条严格配对三模型 Pilot

样本目标：
- Gold72 locked regression：20 条；
- R60 severe：10 条；
- 先完成跨集指纹去重。重复案例不重复计数、不静默替换；reserve 只能由 Owner 指定。

实验要求：
- 三个模型对完全相同的 30 条输入、相同上下文、rubric、JSON contract 分别盲审；
- 每模型独立 blind IDs、顺序、RO 输入目录和私有输出目录；
- 模型看不到历史 A/B/C 与 Owner labels；
- 总计 90 个独立结果；每条核验 input SHA、receipt SHA、source binding、model Revision、profile SHA、rubric SHA；
- Gold72 和 R60 分轨报告，不混为一个统计总体。

指标：
- 三个严重维度分别计算 confusion matrix、SUPPORTED precision/recall/F1、误报/漏报、INSUFFICIENT_CONTEXT 检出、引用有效率和语义证据支持率；
- 六维评分分别计算 MAE、±1 误差率和分维偏差；
- 模型一致率仅为辅助，不能代替 Owner 参考裁决；
- 30 条不能宣传成生产准确率认证。

**GPU 授权门禁**：当前无 GPU 授权。提交真实 GPU Job 前，先向 Owner 报告模型数、Job 数、GPU flavor、预计时长/成本、输入输出 Volume 权限、命令/dry-run、失败策略。只有 Owner 明确授权后才能提交。attempt=1、无自动重试、无 namespace fallback。

**P4 PASS**：90/90 可追溯、类别覆盖充分、严重误报/漏报逐案解释、无未解释的严重安全漏报，并由 Owner 批准最终双模型。

### P5 — 审核器回归与最终双模型冻结

- Gold72 development 20 用于规则迭代；
- Gold72 locked 20 用于锁定回归；
- R60 severe10 用于专项严重问题回归。
- 覆盖 NPC 主动性/玩家代理、硬规则证据、安全边界、引用存在但语义不支持、上下文缺失、结构化输出失败、旧 v3/新 v4 checkpoint 防串用。
- 产出 rubric v2.1 frozen SHA、模型 profile IDs、回归 SAFE、误报/漏报分类、最终 A/B 选择理由和 Owner approval record。

**P5 PASS** 后才可申请 P6。

### P6 — 1,000 条正式批量审核

前置条件：P0–P5 全部 PASS、Owner 批准最终双模型、1000 Stage 输入 manifest/SHA 完整、A/B 同案例 1000/1000 配对、Job 预算和 GPU 授权明确。

- 最终双模型审核相同 1000 条；
- Owner crosswalk 精确一一对应；
- 逐案核验 checkpoint、输入、模型和 rubric；
- 分歧、SUPPORTED、INSUFFICIENT_CONTEXT、flag/score 冲突进入 Owner 定点复核；
- 任一严重维度 SUPPORTED 不准入；任一维 INSUFFICIENT_CONTEXT HOLD；
- 三维均 NOT_SUPPORTED 仍需通过六维质量及所有其他准入门槛；
- 保持 Story 级 Train/Validation/Test 隔离；
- 世界组件证据、历史输入完整性和 CPU Tokenizer/Collator 仍是准入门槛。数据来源/权利/隐私/数据使用授权/隔离证明不属于案例审核证据；Story 级数据切分等系统侧防泄漏控制与审核员提供的证据分开管理。

**P6 产物**：批量审核 SAFE、分歧复核记录、Quality-v1 admission SAFE。不得为达到数量目标降低标准。

## 5. 可复用代码和命令

优先复用现有实现，不要另起炉灶：
- `src/storyforge_gold_quality/hf_literary_review.py`
- `src/storyforge_gold_quality/hf_blind_stage.py`
- `src/storyforge_gold_quality/hf_pilot_pairwise_audit.py`
- `src/storyforge_gold_quality/hf_pilot_semantic_c.py`
- `src/storyforge_dataset/token_preflight.py`

本地/CI 基础检查：

~~~bash
PYTHONPATH=src python3 -m pytest tests/test_hf_pilot_pairwise_audit.py -q
python3 -m storyforge_dataset.hf_runtime doctor --profile cpu --json
ruff check src/storyforge_gold_quality src/storyforge_dataset/token_preflight.py
python3 -m compileall -q src/storyforge_gold_quality src/storyforge_dataset
~~~

命令按当前仓库脚本和环境实际情况调整；不得把未执行命令写成已通过。

## 6. 数据安全和不可逾越的边界

1. 私人正文、完整历史、Story/Session/User ID、blind ID、crosswalk、私有 Checkpoint、DSN、凭据不得进入 GitHub。
2. Owner 私有数据仅保留在 Owner 控制的本地目录/私有 Bucket；HF 输入 RO、输出 RW；crosswalk 不上传、不挂载给模型。
3. 不读取 R50 正文，不读取全库原文，不扩大本任务明确列出的私有材料范围。
4. 不修改数据库、角色权限或连接身份。
5. 不覆盖 Gold72、Gold192、R50 和旧 A/B/C 历史结果。
6. 不修改 RolePlay。
7. 不重复 R60 已通过的 1000 crosswalk 和 Pilot10 Checkpoint 审计；不重跑旧 A/B/C 推理。
8. 不重新开展用户明确要求停止的权利/协议调查。
9. 未经用户明确授权，不提交 GPU Job、不运行 1000 条批量推理、不启动 SFT。
10. 任何 SAFE 必须真实反映执行结果；不能复制模板字段伪造 PASS。

## 7. 阶段汇报与完成定义

每个阶段完成后必须提供：
- 执行命令和实际 commit/Job 信息；
- 输入 manifest SHA、输出 SAFE schema；
- 计数、状态、PASS/HOLD 原因；
- 旧文件是否保持不变；
- 私有值是否输出；
- 下一阶段是否满足进入条件；
- Issue #28 和相关文档的更新链接。

统一原则：`Job COMPLETED ≠ PASS`；`Tokenizer PASS ≠ 语义 PASS`；`三维 NOT_SUPPORTED ≠ Quality PASS`；`Quality-v1 admission ≠ GPU/SFT 授权`。

**新 Agent 的第一项工作是 P2 v2.1 Development-20 盲包生成。P0/P1 已通过，不得重做；P2 Owner 裁决和 60 条语义复核未完成前，不进入 P3 模型推理，不提交 HF Job/GPU。**


---

## 8. 2026-11-09 P0 执行补充：Gold72 20/20 划分决议与只读证据重建

本节记录 Owner 在 2026-11-09 明确确认的 P0 划分原则，以及后续只读核验结果。它是执行补充，不替代 Owner 私有 manifest 和最终 SAFE。

**历史记录说明：以下 8.1–8.11 是 P0 执行期间的时间线，包含当时的 HOLD、dry-run 和修复状态。它们已被 8.12 的正式 P0 PASS SAFE 取代；其中任何“P0 HOLD / PENDING / 尚未执行”均为历史状态，不是当前待办。不得重跑这些 P0 命令。当前 Gold72 20/20 案例分层与 Story 跨集合规则以 8.12 为准。**

### 8.1 Owner 已确认的划分原则

Gold72 40 条采用案例级分层，固定为：

- Development：20 条。
- Locked Regression：20 条。
- 允许 Story 跨集合；story_disjoint=false 必须明确写入私有 manifest 和 SAFE。
- 不重新抽样，不替换案例，不修改 A V3、B2、C 或历史 Owner 裁决。
- 不得把 Locked Regression 描述为跨 Story 独立测试集。

分层按 disagreement_type，组内按 target_sha256 字典序升序，确定性分配：

| 分歧类型 | Development | Locked Regression |
|---|---:|---:|
| EXPLICIT_HOLD__B2_PASS | 15 | 15 |
| EXPLICIT_HOLD__B2_REJECT | 2 | 1 |
| CASE_LEVEL_SCORED_PASS__B2_REJECT | 1 | 1 |
| CASE_LEVEL_SCORED_PASS__B2_HOLD | 2 | 3 |
| **合计** | **20** | **20** |

本次按上述规则只读计算：Development 涉及 5 个 Story，Locked Regression 涉及 6 个 Story，跨集合共享 5 个 Story。不得把这项结果解释成 Story 隔离。

### 8.2 Gold72 来源重建结果

本轮重新读取 Owner Evidence 中的 A V3、B2、C 和 Owner 历史材料：

- A V3：192 条记录；完整文件 SHA256 与 A/B2 crosswalk SAFE pin 一致。
- B2：blind input、instructions、Owner map、results、execution record 五项原始字节 SHA256 均与 B2 SAFE / completed receipt 对应 pin 一致。
- B2：72/72 blind ↔ Owner map ↔ results 绑定；A/B2 可比较决策 72 条，一致 32 条、分歧 40 条。
- C：40 条 blind packet、40 条 ID Map、40 条结果；C map 与重建的 A/B2 disagreement 集合逐条匹配 40/40。
- C results-only SAFE：C_RESULTS_BINDING_VALID__EXECUTION_RECORD_UNAVAILABLE；执行记录缺失，独立性未证明。
- Owner resolution：40 条逐案可关联；历史聚合裁决 PASS=30、HOLD=4、REJECT=6。Owner SAFE 为 GOLD72_OWNER_RESOLUTION_VALID__AGGREGATE_IMPORT_READY。

B2 的执行回执 SHA 绑定通过，不代表密码学独立性已证明；C 的结果绑定通过，也不代表 C execution record 已存在。上述历史结果只作为来源和校准参考，不是 Quality-v1 admission。

### 8.3 R60 Severe10 既有证据引用

本轮不重新执行 1000 条 Owner crosswalk 或旧 A/B Checkpoint 审计，仅核对既有 SAFE 和 C 结果：

- Owner Pairwise SAFE：OWNER_PAIRWISE_AUDIT_COMPLETE__SEMANTIC_HOLD；A/B 各 5 条，Checkpoint 回执 5/5 + 5/5，来源总数 10，matched_cases=0。
- Reviewer C SAFE：C_BLIND_SEMANTIC_RECONCILED__QUALITY_HOLD；10/10 来源完整性和 C packet/result 绑定通过，本地 Codex 执行回执验证通过；模型身份独立验证和 Reviewer C 独立性仍为 false。
- C 的历史三维判断仍只是校准参考，不是 Owner ground truth。

### 8.4 跨集合只读指纹核验

使用 Gold C packet 中的完整 history + current_user_text + target_assistant_text，与 R60 C packet 中的 visible_history + target_text，构造规范化来源指纹：

- 完整历史 + 目标指纹交集：0。
- 历史上下文指纹交集：0。
- 目标正文精确 SHA256 交集：0。

Gold 40 条的 target_assistant_text SHA256 与 Gold C Owner map 的 target_sha256 逐条匹配 40/40。R60 C Owner map 的 packet file SHA、map receipt SHA 和逐包 packet SHA 均可复核。

本次比较是精确重复检查，不声称能够发现语义近似、改写或同一剧情的不同续写。

### 8.5 历史状态（已被 8.12 最终 SAFE 取代）：P0 尚未最终 PASS

本轮已完成只读来源重建、历史 SAFE/receipt 核对、20/20 确定性分层计算和跨集合精确指纹去重；但以下 Owner 私有产物尚未创建：

- GOLD72_CALIBRATION_MANIFEST_PRIVATE.json
- R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json
- CALIBRATION_CROSSSET_DEDUP_PRIVATE.json
- CALIBRATION_INVENTORY_SAFE.json

这些文件必须由 Owner Mac 在 ~/.local/share/storyforge/r60/private/ 下以 create-only 方式生成，私有 manifest 文件权限 0600、父目录权限 0700。ChatGPT 当前 GitHub 连接只能读取 Owner Evidence 仓库，不能写入 Owner Mac 私有目录；不得把包含 case/story/blind ID 或来源指纹的 manifest 上传 GitHub 代替本地冻结。

因此当前状态必须记为：

- 来源重建：PASS（只读重建层）。
- Gold72 40/40 A/B2/C membership：PASS（只读重建层）。
- 20/20 case-level stratification：规则已确认，分配已计算。
- Gold72 ↔ R60 精确去重：PASS（只读核验层）。
- Owner 私有 manifest / dedup receipt / aggregate SAFE：PENDING。
- **历史快照状态：P0 HOLD。该状态已被 8.12 的正式 Owner SAFE 覆盖；当前 P0=PASS。**

继续执行时只需在 Owner Mac 完成上述四个 create-only 产物及其本地 SHA/权限复核；不得重跑旧模型，不得重做已通过的旧 Checkpoint 审计。Quality-v1 admitted=0、training_authorized=false、GPU 未启动、R50 未访问、1000 条批量审核未启动。


### 8.6 历史记录：Owner Mac 一键 P0 Freeze Runner（当时尚未执行，最终执行见 8.12）

新增可复用工具：

- `scripts/r60_calibration_p0_freeze.py`
- `tests/test_r60_calibration_p0_freeze.py`

Runner 的职责：

1. 从 Owner 私有目录只读读取 Gold72 / Pilot10 证据。
2. 重新执行 Gold72 专用 A V3/B2 72-case crosswalk validator，并与历史 SAFE 精确比较。
3. 重新执行 Gold72 Owner-resolution validator 到临时私有目录，并与历史 Owner SAFE 精确比较。
4. 读取 Gold72 40 条 C packet、Owner map 和 Owner resolution，按已确认分层规则确定性构建 20/20。
5. 对 R60 Pilot10 只核对既有 Pairwise SAFE、Stage manifest、Owner crosswalk 的 10 个来源位置、10 份既有 A/B checkpoint 文件；**不重跑 R60 1000-row crosswalk 或 A/B checkpoint audit**。
6. 复核 Pilot10 C packet/map/result 和十组本地 Codex per-case receipt；复用现有 `verify_local_execution_receipt`，不调用模型。
7. 计算 Gold72↔Pilot10 的精确历史、目标正文、完整历史+目标三类指纹交集。
8. create-only 生成三份 Owner 私有 manifest/receipt 和一份聚合 SAFE；所有私有输出 0600、目录 0700。

执行环境必须是 Owner Mac。默认输入根目录为 `~/.local/share/storyforge`；所有私有输入文件须为普通文件、权限 0600、直接父目录权限 0700，且不得位于 StoryForge Git 仓库内。权限不合格时 Runner 只返回固定 reason code，不自动 chmod、不修复、不覆盖输入。

先执行 dry-run：

~~~bash
set -euo pipefail
cd "$HOME/workspace/storyforge"
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

PYTHONPATH=src:. python3 scripts/r60_calibration_p0_freeze.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109" \
  --dry-run
~~~

只有输出 `CALIBRATION_INVENTORY_PREFLIGHT_PASS__NO_FILES_WRITTEN` 才执行正式冻结（去掉 `--dry-run`）：

~~~bash
PYTHONPATH=src:. python3 scripts/r60_calibration_p0_freeze.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109"
~~~

正式冻结预期 create-only 输出：

- `GOLD72_CALIBRATION_MANIFEST_PRIVATE.json`
- `R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json`
- `CALIBRATION_CROSSSET_DEDUP_PRIVATE.json`
- `CALIBRATION_INVENTORY_SAFE.json`

Runner 输出的 SAFE 仅含聚合数量、状态和准入边界，不含 case/story/blind ID、原文、crosswalk 或来源 SHA。三个 manifest 和 dedup receipt 都是 Owner 私有材料，禁止上传 GitHub、粘贴到聊天或挂载给模型。

Runner 只进行本地只读核验和本地 create-only 文件写入，不调用网络、Supabase、HF、模型或 GPU。Gold72 C execution record unavailable、Gold72 C independence false、Pilot10 C model identity independently verified false 等历史限制必须保留。即使 SAFE 显示 P0 PASS，也只代表校准集库存冻结完成；Quality-v1 admission 仍为 0，不能据此启动 P1 以外的 GPU、1000 条推理或 SFT。

**当前状态：Runner 代码已提交且 CI 合成测试通过；尚未在 Owner Mac 实际运行。P0 仍为 HOLD，直到 Owner Mac 的正式 SAFE 实际生成并核验。**


### 8.7 首次 Owner Mac dry-run HOLD 后的诊断补丁（2026-11-09）

Owner Mac 首次 dry-run 返回 `INPUT_OR_IO_ERROR`。旧版 Runner 兜底捕获了异常类型和执行位置，导致无法判断具体失败阶段；该次未生成 manifest，未启动 GPU/模型，未修改输入证据。

已在 Runner 加入隐私安全诊断字段：

- `diagnostic.phase`：失败阶段（如 Gold72 输入读取、A/B2 replay、Owner resolution replay、Pilot10 checkpoint/C receipt、cross-set dedup、输出准备）。
- `diagnostic.exception_type`：异常类名。
- `diagnostic.source_file` / `diagnostic.source_line`：异常栈最内层源文件 basename 与行号。
- `diagnostic.errno`：仅 OSError 时输出系统错误码。
- `diagnostic.validator_reason_code`：仅当异常来自内部固定 reason-code 校验器时输出白名单格式错误码。

不输出异常原文、路径、case/story/blind ID、正文、SHA 或 traceback。测试专门确认任意异常文本不会泄露。

**重新执行只允许 dry-run**，拉取最新分支代码后执行：

~~~bash
cd "$HOME/workspace/storyforge"
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

PYTHONPATH=src:. python3 scripts/r60_calibration_p0_freeze.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109" \
  --dry-run
~~~

将完整 SAFE JSON 回传。只需 SAFE，不要上传或粘贴私有 manifest / 原始输入 / traceback。若仍 HOLD，依据 `diagnostic.phase`、`exception_type`、`source_file`、`source_line` 和固定 validator reason code 定位修复。

诊断补丁提交：`375a68da88b20779a9856a47f6587b66b903795a`。GitHub CI、R60 HF Runtime CI、Gold Quality Pipeline、R58 synthetic regression 已通过；R60 HF CPU dependency profile 正在完成。此提交的 CI 通过不代表 Owner Mac P0 已通过。

**P0 仍为 HOLD；不得去掉 `--dry-run`，直到诊断后的 dry-run 明确返回 `CALIBRATION_INVENTORY_PREFLIGHT_PASS__NO_FILES_WRITTEN`。**


### 8.8 macOS 临时目录符号链接兼容修复（2026-11-09）

Owner Mac 第二次 dry-run 已把失败精确定位为：

- phase：`gold72_replay_owner_resolution`
- validator：`gold72_owner_resolution.py`
- reason：`OUTPUT_PATH_SYMLINK`
- failure site：Owner Resolution Validator 的 create-only SAFE 输出路径祖先检查。

原因是 Runner 用 `tempfile.mkdtemp()` 创建临时目录后，将 macOS 的临时目录别名路径直接传入 Validator。macOS 的系统临时目录路径可能包含 `/var -> /private/var` 这样的系统符号链接祖先。Validator 对输出路径的全祖先进行符号链接拒绝，因此把合法 OS 路径误判为不安全路径。

修复：
- Runner 新增 `_private_temp_directory()`：确认新建目录本身不是 symlink，解析为 canonical absolute path，确认目录有效并设置/复核 0700。
- 只把 canonical path 传给既有 Validator；不放宽 Validator 的符号链接安全检查，不改变私有输入读取、create-only 写入或 0600 文件权限。
- 新增合成回归测试：模拟 macOS 风格的 symlinked ancestor，验证返回 canonical path 且目录权限为 0700。

修复提交：`d9e951f68f4e0aa9c526ecef43fd588a6c2dcc9a`（测试补充提交：`33bfca8ef6b1531b2b146253ad2f22d9e4d3a5ca`）。

该提交的 CI、Gold Quality Pipeline、R60 HF Runtime CI、R58 scoped synthetic、R60 HF CPU dependency profiles 全部通过。以上是代码/合成测试通过，不代表 Owner Mac P0 dry-run 或正式冻结通过。

**下一步：Owner Mac 拉取最新分支后，只重跑原 dry-run 命令。** 若 dry-run PASS，先回传 SAFE；在确认结果前仍不得执行正式冻结。


### 8.9 Gold72 split aggregate handoff KeyError 修复（2026-11-09）

Owner Mac 第三次 dry-run 返回：

- phase：`crossset_exact_dedup`
- exception：`KeyError`
- source：`r60_calibration_p0_freeze.py`，SAFE builder 附近
- GPU / model / R50：未启动/未访问。

根因已从代码定位：`_load_gold()` 成功计算并在 Gold72 manifest 的 `split_summary` 中保存了 `development_story_count`、`locked_regression_story_count`、`shared_story_count`，但其返回给 `_run()` 的聚合 summary 字典遗漏了这三个字段。随后 `build_inventory_safe()` 读取这些字段时抛出 KeyError。该错误发生在两组输入校验和 `compare_crosssets()` 调用之后的 SAFE 构造阶段，不是来源数据或去重算法报告失败；本次 SAFE 未输出，所以不能报告具体交集计数或 P0 PASS。

修复：
- 新增 `_gold_story_summary()`，验证并提取三个整数聚合计数。
- 将这些计数加入 `_load_gold()` 返回的聚合 summary，供 SAFE builder 使用。
- 增加回归测试，验证 20/20 分层的 Story 聚合数可以进入 SAFE，同时 `story_disjoint=false`。
- 不输出 Story ID，不改动任何 Owner 私有输入或历史证据。

修复提交：`055497c8fdce2b4b6a47cc778d4de27259c9ec7b`；测试补充提交：`31bd90df4a980494966ff66c2d822f176464da67`、`37e7f7484f0f440f6c6a4f61ada532c0d33e00bb`。

CI、R58 scoped synthetic、Gold Quality Pipeline、R60 HF Runtime CI、R60 HF CPU dependency profiles 以最终测试提交 `37e7f7484f0f440f6c6a4f61ada532c0d33e00bb` 的实际 Actions 结果为准。

**下一步仍只允许 Owner Mac 重跑 dry-run。** 必须取得完整 SAFE JSON 并检查 P0 状态、Gold72 Story 聚合数、Pilot10 计数、三类跨集合交集和唯一来源数量；若 dry-run PASS，再单独确认后执行正式 create-only 冻结。不得直接复用本次未输出的内存 dedup 结果。


### 8.10 P0 只读预检通过，等待正式冻结确认（2026-11-09）

Owner Mac 最新 dry-run SAFE 返回 `CALIBRATION_INVENTORY_PREFLIGHT_PASS__NO_FILES_WRITTEN`。

聚合结果：
- Gold72 来源 40；A/B 可比较 72，其中分歧 40、一致 32。
- Gold72 development / locked regression = 20 / 20；Story 数分别 5 / 6，共享 Story 数 5；允许 Story 跨集合，`story_disjoint=false`。
- Gold72 历史 Owner 裁决：PASS 30 / HOLD 4 / REJECT 6；历史 Reviewer C：PASS 38 / HOLD 1 / REJECT 1。C execution record 与 independence 仍未证明。
- R60 Severe10 来源 10；A/B checkpoint receipt A=5、B=5；A/B matched cases=0；C execution verified=true，C independence verified=false。
- Gold72↔R60 exact history / target / full-history-target intersections 均为 0；跨集合唯一来源数 50。
- `manifest_files_written=0`；`private_values_emitted=false`；GPU/R50 未启动/未访问；Quality-v1 admitted=0；training_authorized=false。

最新分支提交 `15ab890506ba11411f6e81c1c5f35e03fd55f497` 的 CI、Gold Quality Pipeline、R60 HF Runtime CI、R60 HF CPU dependency profiles、R58 scoped synthetic 均已通过。PR #25 仍 Open / Draft，head 与该提交一致。

**状态边界：P0 只读预检 PASS，不等于正式冻结完成。** 尚未生成四个 create-only 文件，尚未验证文件存在性、SHA、0600/0700 权限及历史文件不变性。正式冻结需要 Owner 明确确认后，再在 Owner Mac 使用同一命令去掉 `--dry-run` 执行；之后必须重新核验四份产物和最终 SAFE。未经确认不得写入。


### 8.11 Owner 已授权 P0 正式冻结（2026-11-09）

Owner 在 ChatGPT 对话中明确确认授权：仅在 Owner Mac 本地执行 P0 正式冻结，create-only 生成以下四份文件：

- `GOLD72_CALIBRATION_MANIFEST_PRIVATE.json`
- `R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json`
- `CALIBRATION_CROSSSET_DEDUP_PRIVATE.json`
- `CALIBRATION_INVENTORY_SAFE.json`

授权范围不包含模型推理、HF Job、GPU、P1、1000 条批量审核、SFT、数据库/权限变更、上传私有文件或修改历史证据。

执行环境限制：本 ChatGPT 会话没有 Owner Mac 本机 shell/文件系统执行通道，不能代替 Owner 在本地运行该命令，也不能将私有输入复制到 GitHub Actions/HF 作为替代。因此授权已记录，但**本地正式冻结尚未执行**。不得声称四个文件已生成。

Owner Mac 拉取本任务书最新提交后，在仓库执行以下正式命令（与已通过 dry-run 相同，唯一变化是移除 `--dry-run`）：

~~~bash
set -euo pipefail
cd "$HOME/workspace/storyforge"
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

PYTHONPATH=src:. python3 scripts/r60_calibration_p0_freeze.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109"
~~~

执行后只回传聚合 SAFE JSON 和不含私有路径/值的文件元数据核验结果；不得上传或粘贴三个 private manifest/dedup receipt。必须确认四文件均新建成功、SHA-256 已在 Owner 本地计算并记录、private files mode 0600、目录 mode 0700、历史输入 SHA 前后不变、`private_values_emitted=false`。如目标文件已存在，Runner 应 fail closed，不得覆盖；先停下报告，不得删除或改名绕过 create-only。

只有正式 SAFE 真实返回且四文件元数据核验通过，才能将 P0 标为正式冻结 PASS。随后仍需单独按任务书申请进入 P1；本授权不自动授权任何后续阶段。


### 8.12 Owner Mac 正式冻结完成：P0 PASS / Quality HOLD（2026-11-09）

Owner 回传正式执行 SAFE：

`status=CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`
`manifest_files_written=4`
`private_values_emitted=false`
`quality_v1_admitted=0`
`training_authorized=false`
`gpu_started=false`
`r50_accessed=false`

正式聚合结果：
- Gold72 来源 40/40；A/B 可比较 72，分歧 40、一致 32。
- Gold72 Development 20 / Locked Regression 20；Story 数 5 / 6，共享 Story 数 5，`story_disjoint=false`。
- Gold72 Owner 历史决策 PASS 30 / HOLD 4 / REJECT 6；Reviewer C 历史决策 PASS 38 / HOLD 1 / REJECT 1。Gold72 C execution record 和 independence 均未证明。
- R60 Severe10 来源 10/10；既有 A/B checkpoint receipt A=5、B=5；A/B matched cases=0；C execution verified=true，independence verified=false。
- Gold72↔R60 exact history / target / full-history-target overlap 均为 0；跨集合唯一来源数 50。
- semantic near-duplicate detection=false；不得将精确去重结果解释成语义近重复排除。

Runner 在返回上述正式 PASS SAFE 前已完成四个 create-only 文件写入，并对输出目录/父目录权限 0700、四个文件权限 0600 执行了代码内检查。SAFE 不暴露私人值。Owner 尚未单独回传 SHA-256 元数据摘要；如需外部审计留档，可在 Owner Mac 本地对四个文件计算并私下保存 SHA-256，不要将私有文件或哈希粘贴到公共 GitHub。

**P0 正式冻结已完成。** 四份文件仅存在于 Owner 私有目录；不得上传 GitHub/HF。Quality-v1 admission 仍为 0；P0 PASS 不代表 Quality PASS、模型选择完成或训练授权。P1(v2.1) 后续已独立完成并 PASS；本次 P0 授权本身不自动扩展为 GPU/1000 条批量审核/SFT 授权。


### 8.13 历史记录：P1 v2 三维严重证据标准实现进展（已被 8.14、8.21–8.22 的 v2.1 结果取代）

Owner 对“继续”确认后，开始 P1 的代码/标准/合成测试工作。当前只在公共仓库提交通用代码、Rubric 和合成测试；没有读取 Gold72/R60 私有正文，没有运行模型或 HF Job，没有启动 GPU。

新增：
- `src/storyforge_gold_quality/hf_severity_evidence_v2.py`
- `tests/test_hf_severity_evidence_v2.py`
- `docs/R60_SEVERITY_EVIDENCE_RUBRIC_V2_20261109_CN.md`

版本：
- Schema：`storyforge_severity_evidence_review_v2`
- Rubric：`r60_severity_rubric_v2`
- 独立语义复核记录：`storyforge_severity_semantic_entailment_check_v2`

复用入口：
- `hf_literary_review.severity_evidence_response_schema_v2()`
- `hf_literary_review.severity_evidence_prompt_messages_v2()`
- `hf_literary_review.validate_severity_evidence_v2()`
- `hf_pilot_semantic_c.validate_c_result_v2()`
- `hf_pilot_semantic_c.verify_c_semantic_entailment_v2()`

v2 规则与校验覆盖：
- 三维各自输出 SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_CONTEXT。
- 每条引用有 source、消息/组件位置、0-based 字符 offsets 和连续原文；程序校验 `text[start_char:end_char] == quote`。
- hard_rule 的规则来源必须绑定到真实可见 System/User 消息或 verified world component，目标冲突也必须有独立目标引用。
- player_agency 的目标行为和玩家边界分开取证；NPC 主动性不能自动成为玩家代理。
- safety 需要目标风险证据和明确政策依据；普通亲密/冲突/威胁内容不自动触发排除。
- NOT_SUPPORTED 要求相关上下文覆盖完整；INSUFFICIENT_CONTEXT 必须列明缺失信息；confidence 不改变 verdict。
- 聚合规则：任一 SUPPORTED → REJECT_OWNER_REVIEW_REQUIRED；否则任一 INSUFFICIENT_CONTEXT → HOLD；全 NOT_SUPPORTED → NO_SEVERE_FLAGS__QUALITY_NOT_PASSED（不是 Quality PASS）。
- Exact quote 自动检查与 semantic entailment 独立检查分开。没有独立语义复核记录，不能把 exact quote PASS 解释成语义 PASS；helper 也明确不声称 reviewer 身份/独立性已获密码学证明。

兼容性：
- 旧 `storyforge_hf_literary_checkpoint_private_v3`、旧文学 response schema、旧 Reviewer-C `storyforge_r60_pilot10_c_review_private_v1` 不改写。
- v2 是单独版本入口；不自动迁移、接受或覆盖旧 checkpoint。
- P1 合成测试覆盖引用位置/跨消息拼接、NPC 主动性、玩家拒绝、硬规则 System/世界组件来源、安全证据、上下文不足、confidence、聚合优先级、语义蕴含独立复核和旧 v3/v1 兼容。

本轮代码提交链：
- `cdc2066b87ef7c184cce22309ad20b9c96147aa4`：新增 v2 rubric/schema/validator。
- `5007166d49f3f49b59ef34f8bd8dac2a2be9a21b`、`53eea491a80549269e913fe8d54d50bb832be681`：接入既有 reviewer / Reviewer-C 入口。
- `4acf4f0d5bea1e4d09fa48f756c67330f58e6d61`、`96288fe82b2a52754cff9ef7bf8272d4ac3b7a20`、`e9bca64ea1d998160e399bf550886ecc0bee1a09`、`2ac7a3373e980dd61d335d06f3fcf70b796c2093`、`93715815a3dfbcf29f4abf5dfd8213af7ddd5ebc`、`1b9ab4bd932e07e958000987023ea9d275753f47`：合成测试、来源绑定强化和 lint 修复。

**历史状态：P1 当时处于 IN PROGRESS；该状态已被 8.14 的 v2 PASS 和 8.21–8.22 的 v2.1 最终 PASS 取代。当前 P1(v2.1)=PASS，下一阶段为 P2。**


### 8.14 历史记录：P1 v2 标准与合成回归通过（v2.1 已取代该版本）

最新实现提交：`c80d6bbc2c7f1cd7a6d5184be808e6a788d0e2b7`。

P1 验收：
- v2 Schema/Rubric 版本固定：PASS。
- 三维三态 contract 与 fail-closed 聚合：PASS。
- exact quote check（字符 offsets、消息/组件定位、连续原文）：PASS。
- hard_rule 规则依据与真实 System/User/verified-world-component locator 绑定：PASS。
- NPC 主动性/玩家自主权、安全误报边界、上下文不足：合成回归 PASS。
- semantic entailment 独立复核接口：PASS；无独立复核记录时 HOLD；引用存在不等于语义支持。
- 旧 Literary Reviewer v3 checkpoint/schema 与 Reviewer-C v1 结果兼容：PASS。
- 全仓 pytest：859 passed、5 skipped、42 subtests passed。
- Ruff changed Python files：PASS。
- 五组 Actions：CI、Gold Quality Pipeline、R60 HF Runtime CI、R60 HF CPU dependency profiles、R58 scoped synthetic 全部 PASS。

Rubric 文档：`docs/R60_SEVERITY_EVIDENCE_RUBRIC_V2_20261109_CN.md`。

**P1 = PASS。** 这只表示标准、Schema、合成回归和旧版本兼容通过；不表示 Owner ground truth 已建立、不表示真实案例的 semantic entailment 已审、不表示模型选型或 Quality-v1 admission 通过。

下一阶段按 P2 进行：仅 Gold72 Development 20 条进入 Owner 独立盲裁决；Gold72 Locked Regression 20 与 R60 Severe10 继续锁定。新 packets 必须隐藏旧 A/B/C 判断、分数、flags、Owner resolution、槽位及旧 blind IDs；旧证据只作后续对照。P2 仍不得启动模型/GPU。当前 Quality-v1 admitted=0，training_authorized=false。


### 8.15 历史工程记录：P2 Development-20 Owner 盲裁决包生成器（当前须按 v2.1 重新生成）

P1 已 PASS 后，继续准备 P2 Owner 独立盲裁决。当前只完成通用代码与合成验证；**Owner Mac 私有数据 dry-run 尚未执行，真实 Owner 裁决尚未开始。**

新增：
- `src/storyforge_gold_quality/hf_owner_adjudication_v2.py`
- `scripts/r60_owner_adjudication_v2.py`
- `tests/test_hf_owner_adjudication_v2.py`

生成器边界：
- 只读取 P0 冻结 Gold72 manifest 和其已验证 SHA pin 的 Gold72 C blind source packet。
- 不读取 A V3/B2 结果文件、Reviewer C 结果、Owner resolution 或 R60 Severe10 私有数据。
- 使用 manifest 的 Development 20 列表与 target SHA 绑定来源；仅把 Development 20 的历史和目标正文写入新盲包。
- 生成全新 32 位 calibration_id；旧 blind_case_id、A/B/C 标签、分数、flags、Owner resolution、Story ID、分歧分层不进入 reviewer packet。
- Owner-only ID map 单独保存；reviewer 只接触 blind packet 与说明，不接触 map、P0 manifest 或旧结果。
- Locked Regression 20 不写入输出；R60 Severe10 不读取。
- 新 packet 使用 v2 schema/rubric；世界组件快照未包含在原 C packet 时保持空数组，不臆造。
- 默认 dry-run；只有显式 `--write` 才 create-only 写入六份私有文件。输出目录 0700、文件 0600；已有目录拒绝覆盖。
- 不调用模型、不提交 HF Job、不启动 GPU。

六个私有输出：
- `OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl`
- `OWNER_ADJUDICATION_ID_MAP_PRIVATE.json`
- `OWNER_ADJUDICATION_MANIFEST_PRIVATE.json`
- `OWNER_ADJUDICATION_PREPARE_SAFE.json`
- `OWNER_ADJUDICATION_INSTRUCTIONS_CN.md`
- `OWNER_ADJUDICATION_SCHEMA_V2.json`

合成回归覆盖 20/20 Development 选择、旧 ID 隔离、Locked20 不泄露、source pin mismatch、target binding mismatch、私有文件权限、dry-run no-write、create-only 不覆盖。

最新 P2 代码提交：`d36bdc51043f1a1abcdf6c758e188db475f7a40d`、`8612e97a9d2aca92fe26d24770bbfa037afe1008`、`515e0c3e390bec86ebceadde04154fad98b069c4`、`ca781f1853fbdd9af7a24b7639a57d787c7d29a7`、`b257eb159939cd20a459e98ce10fd369e77a950c`、`58b5884819c8e5684eeddab9e075286682111858`、`bee13ec7f65658338340a6a3c217db6c84ebf098`、`dcff01b7f3d5ffe05906be97a2f7b80fc4f8c630`、`a50a49a10b3ad03a29887d5b4ee89662a06918d5`、`e096c87732476b1f68b8acd4191fd8b86d9bf44b`、`e77e4eb339928574e0c677ef6a619519cf507c2c`。

最终测试提交 `e096c87732476b1f68b8acd4191fd8b86d9bf44b`：全仓 pytest 865 passed、5 skipped、42 subtests passed；Ruff、CI、Gold Quality Pipeline、R60 HF Runtime CI、R58 scoped synthetic PASS。当前 PR head 的 CPU dependency profile 仍以最终 Actions 回执为准。

**P2 当前状态：PACKET BUILDER READY / OWNER MAC DRY-RUN PENDING / OWNER REVIEW NOT STARTED。** 下一步先在 Owner Mac 执行默认 dry-run；只有返回 `P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN` 后，才执行带 `--write` 的私有包生成。生成后仅把 packets + instructions 提供给 Owner 盲审，ID map 不得给 reviewer。Owner 结果与独立 semantic checks 需另行校验并生成逐案 timestamp/receipt；在此之前不宣称 P2 PASS。

Quality-v1 admitted=0；training_authorized=false；无模型、GPU、1000 条审核或 SFT。


### 8.16 P2 Owner 结果与 60 项语义复核的私有回执验证器（2026-11-09）

在 P2 包生成器基础上，增加 Owner 结果回执验证，避免只生成 20 条 verdict 而漏掉独立语义复核，或出现重复/缺失维度。

新增：
- `scripts/r60_owner_adjudication_verify_v2.py`
- `hf_owner_adjudication_v2.verify_owner_results()`
- 合成测试扩展到 20 条结果 + 60 项语义检查。

验证器要求：
1. packet/result/semantic-check 分别严格为 20/20/60 行。
2. 20 个 case_ref 与 20 个新 calibration_id 一一对应，不能混入旧 ID。
3. 每条结果完整通过 v2 Schema、exact quote 和维度规则验证。
4. 60 项覆盖 20 case × 3 dimensions；不允许重复或缺失。
5. 每项语义复核必须标记 `OWNER_INDEPENDENT`，且 reviewer_ref 在本批次保持一致。该字符串一致性不是身份认证；SAFE 明确 `owner_identity_cryptographically_attested=false`。
6. 每个 timestamp 必须带 UTC 时区。
7. 每项 semantic check 必须检查该维度全部已引用 evidence indexes，不能只挑选部分引用。
8. `DOES_NOT_SUPPORT_VERDICT` 不会被自动接受为通过；产生 HOLD 计数。独立确认 `INSUFFICIENT_CONTEXT` 同样保留 HOLD，不伪装成语义 PASS。
9. 私有 manifest 绑定 packet、结果、语义复核和 rubric 的 SHA-256；SAFE 不输出 case IDs、正文、判定细节。
10. 不进行 Quality-v1 admission，不授权 GPU/SFT。

Owner 完成两份私有 JSONL 后，在仓库根目录运行：

```bash
python scripts/r60_owner_adjudication_verify_v2.py \
  --package-dir "/Users/keedle/.local/share/storyforge/r60/private/owner-adjudication-dev20"
```

要求该目录是 0700，输入文件均为 0600；验证成功后只会 create-only 写入：
- `OWNER_ADJUDICATION_RESULTS_MANIFEST_PRIVATE.json`
- `OWNER_ADJUDICATION_RESULTS_SAFE.json`

验证失败输出稳定 reason code，不输出私有正文。验证器不会覆盖已有回执。

**P2 当前仍未开始真实 Owner 审核。** 先完成 Owner Mac 的默认 dry-run，再显式 `--write` 生成盲包；完成 Owner verdict 与 60 项语义复核后，运行上述 verifier。只有结果与独立语义证据均满足要求，才能推进后续校准；任何 semantic HOLD 均需保留，不得通过改写结果来追求全绿。


### 8.17 P2 生成器与回执验证器最终 CI 回归（2026-11-09）

最新代码提交：`e7917030e76e7ccb96562dec47ce4e879b9306b9`。

本轮新增 20-case / 60-check Owner 回执验证后，CI 首次发现 4 个合成测试 fixture 重复使用同一个 calibration_id；已修正为每例独立 32 位 ID。Ruff 同时发现 datetime import order / UTC 解析 lint，已修复。

另外，R60 CPU dependency profile 首次发现 PyPI 的 transitive `regex` 版本从 lock 中的 2026.11.7 漂移到 2026.11.8，导致 lock reproducibility 检查失败。已在：
- `requirements/hf-cpu-tokenizer.in`
- `requirements/hf-quality-reviewer.in`

显式固定 `regex==2026.11.7`。现有 hash lock 与该版本匹配，不放宽 lock 检查。

最终 GitHub Actions：
- CI：PASS，pytest 870 passed / 5 skipped / 42 subtests passed，Ruff PASS。
- Gold Quality Pipeline (synthetic + R57 regression)：PASS。
- R60 HF Runtime CI：PASS。
- R60 HF CPU dependency profiles：PASS（tokenizer lock、reviewer lock、locked installation、CPU-only dependency boundary、Chat Template）。
- R58 scoped synthetic (no training)：PASS。

**P2 工程准备 = PASS（仅生成器/回执验证器与合成回归）。P2 Owner Mac dry-run 仍未执行，真实 Owner 审核仍未开始。** 当前 PR #25 仍为 Open / Draft；不合并、不启动模型/HF Job/GPU/SFT。


### 8.18 Owner Mac dry-run 精确路径与命令

P0 freeze manifest 目录已知为：
`$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109`

Gold72 Reviewer-C blind packet 源目录由当前 `scripts/r60_calibration_p0_freeze.py` 的 `GOLD["c_dir"]` 固定为：
`$HOME/.local/share/storyforge/r59/private/reviewer-c-runs/gold72-c-20261106-v1/R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl`

Owner Mac 项目 worktree：`/Users/keedle/workspace/storyforge-r60-ledger-diagnostics`，对应分支 `r60/gold192-history-v3-adapter`。以 `git worktree list` 实际输出为准，不使用旧路径 `storyforge-gold-quality`。

先确认当前 worktree 无未提交修改，并更新到本分支最新版本；不要覆盖 Owner Mac 的未提交工作。然后在 Owner Mac 执行默认 dry-run（不加 `--write`）：

```bash
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics

PYTHONPATH=src:. python scripts/r60_owner_adjudication_v2.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --p0-freeze-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-20261109"
```

成功唯一状态：
`P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN`，并且 `files_written=0`。

如返回 HOLD，不要改权限或猜测替代源文件；先根据 reason_code 核查 P0 manifest、Reviewer-C packet 的精确路径、文件 0600 和各自父目录 0700。只有 dry-run PASS 后，才对同一命令显式追加 `--write`。输出目录必须此前不存在；若已存在，不删除、不覆盖，换一个新的唯一输出目录并重新 dry-run。

当前工具只提供 GitHub / HF / VPS 等远端能力，没有 Owner Mac 本机 shell 通道；因此 dry-run 和 `--write` 必须在 Owner Mac 本机执行，不能谎报为已运行。


### 8.19 Owner dry-run 自身的输出路径门禁补强（2026-11-09）

代码审查发现一个 dry-run 语义缺口：原实现先返回 dry-run PASS，再检查输出目录权限/是否已存在。这会让 dry-run 对实际 `--write` 路径的可写性和 create-only 条件给出过早 PASS。

已修复：
- dry-run 与正式写入共用同一输出路径预检。
- 输出目录必须是绝对路径、尚不存在、没有 symlink 父级。
- 父目录必须已存在且权限为 0700。
- 输出位置不得落入 Git worktree。
- dry-run 仍不创建目录、不写文件，SAFE 返回 `files_written=0`。
- 新增合成测试：已有输出目录、父目录权限错误时，dry-run 必须 HOLD。

最新代码提交：`bf1181eefc43832e89cb82b76cea45d46e954301`。

最终 Actions 全部 PASS：
- pytest 871 passed / 5 skipped / 42 subtests passed。
- Ruff / CI PASS。
- Gold Quality Pipeline PASS。
- R60 HF Runtime CI PASS。
- R60 HF CPU dependency profiles PASS（两组 hash lock、安装、CPU-only boundary、Chat Template）。
- R58 scoped synthetic PASS。

**Owner Mac dry-run 已于 2026-11-09 通过。** SAFE 回执：`P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN`，`cases_prepared=20`、`files_written=0`；未暴露 Locked Regression 20 / Severe10 / 旧 A/B/C judgments / Owner Resolution；未启动 Owner review、模型、HF Job 或 GPU。下一步仅在核对 worktree 分支与输出目录仍不存在后，显式 `--write` 生成 Development-20 六份私有盲审文件。Owner verdict / semantic review 尚未开始，P2 真实审核尚未完成。


### 8.20 历史记录：P2 v2.0 Development-20 私有盲审包已生成（随后被 v2.1 SUPERSEDED）

Owner Mac 已在 `/Users/keedle/workspace/storyforge-r60-ledger-diagnostics` 的 `r60/gold192-history-v3-adapter` worktree 执行带 `--write` 的生成命令。实际 SAFE 回执：

- schema：`storyforge_r60_owner_adjudication_prepare_safe_v2`
- status：`P2_OWNER_BLIND_PACKETS_READY__OWNER_REVIEW_NOT_STARTED`
- `cases_prepared=20`
- `files_written=6`
- 仅 Gold72 Development-20；Locked Regression 20 / R60 Severe10 均未暴露。
- 旧 A/B/C judgments、旧 blind IDs、旧 Owner resolution 均未暴露。
- `private_values_emitted=false`。
- `owner_review_started=false`；model_calls=0；hf_jobs_submitted=0；gpu_started=false。
- Quality-v1 admitted=0；training_authorized=false。

**历史状态：该六文件包属于 Rubric v2.0，后来已由 Owner 明确标记 `SUPERSEDED`。不得用于裁决、不得覆盖或删除。当前唯一待生成的是 8.21 指定的新 v2.1 包。**

#### 下一步：Owner 独立盲裁决

输出目录固定为：
`$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-20261109`

只允许打开：
1. `OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl`
2. `OWNER_ADJUDICATION_INSTRUCTIONS_CN.md`
3. `OWNER_ADJUDICATION_SCHEMA_V2.json`
4. 已冻结的公开 Rubric v2.1。

严禁打开 `OWNER_ADJUDICATION_ID_MAP_PRIVATE.json`、P0 Gold manifest、Gold72 C 旧结果、A V3/B2 结果、历史 Owner resolution、旧 checkpoint；不得查看 Locked Regression 20 或 R60 Severe10。

Owner 逐个案例分别裁决 `player_agency`、`hard_rule`、`safety`，每维只允许 `SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_CONTEXT`。证据必须逐字连续引用并给出 message/component locator、rule_basis、reasoning_summary、missing_context、context_coverage、confidence。引用存在不等于语义蕴含；不确定时保留 `INSUFFICIENT_CONTEXT`，不能猜测或为凑数降级标准。

在私有输出目录中创建：
- `OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl`：20 行，每行对应一个新 `calibration_id`，符合 `storyforge_severity_evidence_review_v2`。
- `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`：60 行，20 cases × 3 dimensions，每行单独复核该维全部 evidence indexes；结论为 `SUPPORTS_VERDICT / DOES_NOT_SUPPORT_VERDICT / INSUFFICIENT_CONTEXT`，记录带 UTC 时区的 `reviewed_at_utc`。

两个 JSONL 必须留在 Owner 私有目录，权限 0600，目录 0700。不得将正文、case IDs、结果或 ID map 复制到 GitHub/SAFE。完成后运行：

```bash
PYTHONPATH=src:. python scripts/r60_owner_adjudication_verify_v2.py \
  --repo-root "$PWD" \
  --package-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-20261109"
```

验证器仅 create-only 写入：
- `OWNER_ADJUDICATION_RESULTS_MANIFEST_PRIVATE.json`
- `OWNER_ADJUDICATION_RESULTS_SAFE.json`

任何 semantic check 不支持 verdict、引用不完整、重复/缺失维度或上下文未解决，均保留 HOLD；不得覆盖或重写原始裁决来追求全绿。

在真实 Owner 结果回执验证完成前，不进入 P3 模型推理，不解锁 Locked Regression 20 / Severe10，不提交 GPU/HF Job，不运行 1000 条批量审核或 SFT。


### 8.21 Owner 要求排除数据来源与权利审核：Rubric v2.1（2026-11-09）

Owner 明确要求：**审核标准去掉来源与权利审核，不要求来源、隐私、授权和数据隔离相关的证据。**

据此将案例内容审核范围调整为：
- 不评估、不要求、不推断，也不得因缺少此类材料而 HOLD：训练样本来源合法性/采集渠道/来源权属、版权/所有权/许可、数据使用授权、数据主体隐私/个人信息处理/脱敏或隐私授权合规、存储访问控制/数据隔离/跨集合隔离/数据治理证明。
- 不得把上述事项写入 `missing_context`、`rule_basis` 或 verdict 理由。
- `evidence.source` 仍是**当前盲包内部文本定位字段**，用于精确引用核验，不代表数据来源证明。
- `rule_basis.source` / `reviewed_rule_sources` 仍表示**故事内规则/交互/安全依据类别**，不代表训练数据来源或权利证明。
- 玩家在故事内明确表达的拒绝、同意、选择和行动边界仍是 Player Agency / Safety 的内容语义证据；它与训练数据使用授权无关，继续按原标准判断。
- P0 的 manifest/hash/source binding、私有文件权限、HF Volume 边界和训练 split 等属于系统侧完整性/安全控制，不要求案例审核员收集或裁决。此修改不授权删除或绕过这些工程保护。

版本处理：
- `RUBRIC_VERSION` 从 `r60_severity_rubric_v2` 升为 `r60_severity_rubric_v2_1`；JSON schema shape 保持兼容，rubric version 和 rubric SHA 明确区分。
- 新 prompt/schema 描述明确排除数据来源、权利、隐私、数据使用授权和隔离证明。
- 公开冻结文本：[R60 Severity Evidence Rubric v2.1](R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md)；Owner instructions 明确引用此文件，rubric_sha256 绑定模块中的同一文本。
- 新盲包生成器只保留 visible_history 的 `role/content`，不向审核员暴露 `source_turn` 等来源元数据。
- 已生成的 `owner-adjudication-dev20-20261109` 六文件包基于 v2.0，**标记 SUPERSEDED，不得用于裁决，不得覆盖或删除**。Owner 尚未开始 review，因此无需迁移或重写任何裁决。
- v2.1 重新生成到新的、此前不存在的目录：
  `$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109`

历史快照 HEAD `4190c6fe895080d99901cb4c5eb3f221c6948d6d` 的五组 Actions 当时已全部 completed/success；后续交接文档提交已推进 HEAD。下一 Agent 必须重新核验 PR 当前 HEAD/CI，再在 `/Users/keedle/workspace/storyforge-r60-ledger-diagnostics` worktree 执行：

```bash
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter

PYTHONPATH=src:. python scripts/r60_owner_adjudication_v2.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --p0-freeze-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109"

# 仅当 dry-run 返回 P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN
# 且 files_written=0，才对同一新输出路径追加 --write。
PYTHONPATH=src:. python scripts/r60_owner_adjudication_v2.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --p0-freeze-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109" \
  --write
```

新包生成后，只能基于 v2.1 盲包开始 Owner 独立裁决。旧 v2.0 包继续封存，不可混用。其余 P2 规则（20 verdict + 60 semantic checks、独立语义复核、HOLD 保留、ID Map 隔离）保持不变。


### 8.22 Rubric v2.1 全量 CI 回归通过（2026-11-09）

最终代码提交：`f9d23fd11fd5ecdb5e2de41cd203175500bb9004`。

- pytest：875 passed / 5 skipped / 42 subtests passed。
- Ruff：PASS。
- CI：PASS。
- Gold Quality Pipeline (synthetic + R57 regression)：PASS。
- R60 HF Runtime CI：PASS。
- R60 HF CPU dependency profiles：PASS（两个 hash lock、locked install、CPU-only dependency boundary、Chat Template）。
- R58 scoped synthetic (no training)：PASS。
- 公开 Rubric 文档与代码内 `RUBRIC_TEXT` 逐字一致（1,571 chars）；manifest 将记录 rubric SHA-256。
- v2.1 明确不要求数据来源合法性、版权/权利、数据使用授权、隐私合规或数据隔离证明；这些缺失不得导致 HOLD。
- 盲包 history 已移除 `source_turn` 等来源元数据，只保留 `role/content`；evidence.source 仍仅定位盲包内部文本。
- 故事内玩家拒绝/同意/行动边界、故事规则依据和安全规则仍是内容语义证据。

**P1 Rubric v2.1 工程实现与 CI = PASS。P2 v2.0 旧包 = SUPERSEDED；P2 v2.1 新包尚未生成；Owner review 尚未开始。**

下一步严格按 8.21，在新目录先 dry-run，再显式 `--write`。不得复用旧 v2.0 六文件包。


### 8.23 P2 v2.1 Semantic Entailment JSONL 固定接口合同（2026-11-09）

本节是 P2 v2.1 的强制接口合同。Owner、后续 Agent 和验证器实现均以当前分支以下实际代码为准，不得仅凭口头示例自行增删字段：

- 冻结审核标准：[`docs/R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md`](R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md)
- 严重证据与语义复核校验：[`src/storyforge_gold_quality/hf_severity_evidence_v2.py`](../src/storyforge_gold_quality/hf_severity_evidence_v2.py)，重点函数 `verify_semantic_entailment_v2()`
- 20/60 行 Owner 批次验证：[`src/storyforge_gold_quality/hf_owner_adjudication_v2.py`](../src/storyforge_gold_quality/hf_owner_adjudication_v2.py)，重点为 semantic-check row validation / coverage。
- 验证入口：`scripts/r60_owner_adjudication_verify_v2.py`

当前接口版本：
- `schema = storyforge_severity_semantic_entailment_check_v2`
- `rubric_version = r60_severity_rubric_v2_1`
- 三个合法维度：`player_agency`、`hard_rule`、`safety`
- 本节描述的是 60 行语义复核文件，不替代 20 行 `storyforge_severity_evidence_review_v2` 裁决结果文件。

#### 8.23.1 JSONL 外层记录：严格四字段

每行必须是一个 JSON object，且 key 集合必须**恰好**为以下四项，不得缺失或添加字段：

| 字段 | 类型 | 必须满足的约束 |
|---|---|---|
| `calibration_id` | string | 必须精确匹配本批次某一条新盲包的 `calibration_id`；不得使用旧 blind ID 或其他批次 ID |
| `dimension` | string | 只能是 `player_agency`、`hard_rule`、`safety` |
| `reviewed_at_utc` | string | 必须是可解析 ISO-8601 时间戳，且必须带 UTC 时区、UTC offset 为零；推荐统一写成 `YYYY-MM-DDTHH:MM:SS+00:00` |
| `check` | object | 必须符合下述七字段语义复核合同 |

外层记录示例（仅展示结构，禁止把示例 ID 当作真实案例 ID）：

```json
{
  "calibration_id": "<本批次盲包 calibration_id>",
  "dimension": "player_agency",
  "reviewed_at_utc": "2026-11-09T12:00:00+00:00",
  "check": {
    "schema": "storyforge_severity_semantic_entailment_check_v2",
    "rubric_version": "r60_severity_rubric_v2_1",
    "reviewer_role": "OWNER_INDEPENDENT",
    "reviewer_ref": "<本批次固定的 reviewer reference>",
    "conclusion": "SUPPORTS_VERDICT",
    "reviewed_evidence_indexes": [0, 1],
    "reasoning_summary": "逐项检查该维度的全部引用，确认每项引用在当前上下文中共同支持所作判断。"
  }
}
```

#### 8.23.2 内层 check：严格七字段

`check` 的 key 集合必须**恰好**为以下七项，不得添加时间戳、case ID、自由扩展字段或其他元数据：

| 字段 | 类型 | 约束 |
|---|---|---|
| `schema` | string | 固定 `storyforge_severity_semantic_entailment_check_v2` |
| `rubric_version` | string | 固定 `r60_severity_rubric_v2_1` |
| `reviewer_role` | string | Owner 批次验证强制为 `OWNER_INDEPENDENT`；底层通用 helper 另允许 `INDEPENDENT_REVIEWER`，但本次 Owner 包不得使用后者 |
| `reviewer_ref` | string | 去除首尾空白后长度 8–128 字符；60 条记录必须完全一致。该字段是批次内引用标识，不是密码学身份认证 |
| `conclusion` | string | 只能是 `SUPPORTS_VERDICT`、`DOES_NOT_SUPPORT_VERDICT`、`INSUFFICIENT_CONTEXT` |
| `reviewed_evidence_indexes` | integer[] | 必须是整数数组，不允许重复、负数、越界或遗漏；必须恰好覆盖对应案例、对应维度 assessment 的全部 evidence 下标 |
| `reasoning_summary` | string | 去除首尾空白后长度 12–1200 字符；简述引用与 verdict 的语义关系，不能只写“同意”或“通过” |

注意：Python 校验要求 index 的实际类型为整数；不要使用布尔值代替整数。

#### 8.23.3 三种结论与 HOLD 语义

| conclusion | 使用条件 | 验证结果 |
|---|---|---|
| `SUPPORTS_VERDICT` | 已逐条检查该维度全部 evidence，证据在语义上支持 Owner verdict，且至少有一条 evidence | `SEMANTIC_ENTAILMENT_SUPPORTED__REVIEWER_IDENTITY_NOT_ATTESTED`；只表示语义复核记录通过，不证明审核人身份 |
| `DOES_NOT_SUPPORT_VERDICT` | 引用虽然存在，但语义不能支持对应 verdict，或证据与结论冲突 | `SEMANTIC_ENTAILMENT_NOT_ESTABLISHED_HOLD`；必须保留 HOLD |
| `INSUFFICIENT_CONTEXT` | 语义复核后确认上下文不足 | 仅当该维 Owner verdict 本身也是 `INSUFFICIENT_CONTEXT` 时，得到 `SEMANTIC_ENTAILMENT_INSUFFICIENT_CONTEXT_HOLD`；仍然是 HOLD，不是 PASS |

额外约束：
1. `INSUFFICIENT_CONTEXT` 且该维 evidence 为空时，`reviewed_evidence_indexes` 必须为空数组 `[]`；若有 evidence，则必须检查全部 evidence indexes。
2. `SUPPORTS_VERDICT` 不能使用空数组；必须至少检查一条 evidence。
3. `DOES_NOT_SUPPORT_VERDICT` 不得通过修改结论、删除不利引用或重写 Owner 原始 verdict 来消除 HOLD。
4. 若语义复核确认引用不足以支持原 verdict，应保留原始记录与 HOLD，交 Owner 按独立裁决流程决定是否另行形成有审计轨迹的修订；不得在语义复核文件中静默改写 verdict。
5. Exact quote check 只证明原文和位置准确，不证明语义蕴含；两者不可合并。

#### 8.23.4 60 行覆盖与批次绑定

`OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl` 必须满足：

- 总行数严格为 60。
- 20 个新 `calibration_id` × 3 个维度，每个组合恰好一行。
- 不允许重复的 `(calibration_id, dimension)`，不允许缺失组合。
- 每条记录的 `calibration_id` 必须属于本批次 20 条盲包，且能关联到同批次 20 行 Owner result。
- 60 条记录的 `reviewer_ref` 必须一致；这只验证批次标识一致，不等同于身份或独立性证明。
- 每条记录的 evidence indexes 必须完整覆盖对应 Owner result 的该维 `assessments[dimension].evidence`。
- `reviewed_at_utc` 每行独立记录实际复核时间，必须有明确 UTC 时区。
- 两个私有 JSONL 与盲包必须由私有 manifest 以 SHA-256 绑定；不得将这些内容或 ID 映射写入 GitHub、Issue、PR 或 SAFE。

#### 8.23.5 实际验证行为与完成定义

Owner 在新 v2.1 私有盲包目录内准备好：
- `OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl`：20 行；
- `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`：60 行。

然后在当前仓库根目录运行：

```bash
PYTHONPATH=src:. python scripts/r60_owner_adjudication_verify_v2.py \
  --repo-root "$PWD" \
  --package-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109"
```

验证器会核对：
1. 20/20/60 行数量与案例集合；
2. Owner result 的 v2 schema、rubric version、精确引用及维度约束；
3. 外层四字段、内层七字段和每个值的约束；
4. 60 个案例×维度组合完整、无重复；
5. UTC 时间戳；
6. 全部 evidence indexes 覆盖；
7. `OWNER_INDEPENDENT` 与同批次唯一 `reviewer_ref`；
8. 语义不支持和上下文不足的 HOLD 计数；
9. packet、result、semantic-check 和 rubric SHA-256。

成功时 create-only 写入私有 manifest 与 SAFE；验证失败时不得覆盖旧文件或伪造 PASS。即使 60 行结构验证通过，只要存在语义 HOLD，P2 仍须按实际 HOLD 结果报告，不得宣称 60/60 语义通过。

**身份边界：** 当前代码明确输出 `reviewer_independence_cryptographically_verified=false`。`reviewer_role` / `reviewer_ref` 是记录声明和批次一致性字段，不能单独证明实际操作者身份、盲化过程或独立性。P2 汇报必须如实保留此限制。

**范围边界：** Rubric v2.1 已明确排除训练数据来源、权利、隐私、数据使用授权和数据隔离审核；上述事项不得被重新加入 Owner 20 条裁决或 60 条语义复核。故事内部的玩家拒绝/同意边界、可见故事规则和安全规则仍按内容语义标准判断。


### 8.24 历史 CI 快照（9b4f235；仅供沿革，当前 HEAD/CI 必须实时查询）

已重新核验 PR #25 当前 head 与本次接口合同提交一致：
- 当时 PR head：`9b4f235da01a856b3f123f87a2ee1c314c54a3fc`（历史快照，不是当前 HEAD）
- PR 状态：Open / Draft；base：`r60/canonical-a-v3-binding`。
- 以下五组 GitHub Actions 全部 `completed / success`：
  1. `CI` — run `42554925877`
  2. `Gold Quality Pipeline (synthetic + R57 regression)` — run `42554925875`
  3. `R60 HF Runtime CI` — run `42554926008`
  4. `R60 HF CPU dependency profiles` — run `42554925932`
  5. `R58 scoped synthetic (no training)` — run `42554925880`

本次验证范围只说明当前代码/文档变更通过 CI，不代表 Owner 私有 P2 包已经生成，也不代表 Owner 裁决完成。

**当前门禁状态：**
- P0 calibration inventory freeze：PASS。
- P1 Rubric v2.1 implementation / CI：PASS。
- P2 v2.1 semantic-check interface contract：已补齐并随上述 CI 通过。
- P2 v2.1 blind packet：尚未生成。
- Owner 20-case adjudication / 60 semantic checks：未开始。
- P3 model inference / HF GPU jobs：未开始、未授权。
- Quality-v1 admitted=0；training_authorized=false。

#### 下一步：Owner Mac 生成 P2 v2.1 新包

在 Owner 已确认的 worktree `/Users/keedle/workspace/storyforge-r60-ledger-diagnostics` 执行。先确认 worktree 无未提交修改、当前分支正确，并更新到 PR head：

```bash
cd /Users/keedle/workspace/storyforge-r60-ledger-diagnostics
git status --short --branch
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
git rev-parse HEAD
```

目标输出目录必须此前不存在，旧 v2.0 目录继续封存：

`$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109`

先确认目录不存在，再执行 dry-run：

```bash
test ! -e "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109"

PYTHONPATH=src:. python scripts/r60_owner_adjudication_v2.py \
  --repo-root "$PWD" \
  --owner-data-root "$HOME/.local/share/storyforge" \
  --p0-freeze-dir "$HOME/.local/share/storyforge/r60/private/calibration-freeze-20261109" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109"
```

仅当状态严格为 `P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN` 且 `files_written=0` 时，才对同一命令显式追加 `--write`。写入成功状态必须是 `P2_OWNER_BLIND_PACKETS_READY__OWNER_REVIEW_NOT_STARTED` 且 `cases_prepared=20`、`files_written=6`、`private_values_emitted=false`。新 manifest 必须绑定 `r60_severity_rubric_v2_1` 和 Rubric v2.1 SHA。

不得复用/覆盖旧 v2.0 六文件包；不得打开或暴露 ID Map；不得解锁 Locked Regression 20 / R60 Severe10；不运行模型、不提交 HF Job、不启动 GPU/SFT。


### 8.25 历史核验快照（2026-11-09；其后交接文档提交已推进 HEAD）

本节仅记录上一轮核验结果，不能当作接手时的当前状态。新 Agent 必须重新读取 PR #25 与当前 head 对应的 workflow runs。
- 当时 PR #25：Open / Draft；base `r60/canonical-a-v3-binding`。
- 当时 HEAD：`4190c6fe895080d99901cb4c5eb3f221c6948d6d`。
- 五组 Actions 全部 `completed / success`：
  - CI：run `42555517499`
  - Gold Quality Pipeline (synthetic + R57 regression)：run `42555517570`
  - R60 HF CPU dependency profiles：run `42555517597`
  - R58 scoped synthetic (no training)：run `42555517602`
  - R60 HF Runtime CI：run `42555517658`

### 当前唯一有效阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| P0 | PASS | Gold72=40、R60 Severe10=10；20/20 案例分层；Gold72 Story 可跨集合；跨集精确交集 0、唯一来源 50 |
| P1 | PASS | Rubric v2.1 / Schema / Prompt / 合成回归 / 旧 v3 兼容 |
| P2 packet v2.0 | SUPERSEDED | 已生成旧包不得使用、覆盖或删除 |
| P2 packet v2.1 | NOT GENERATED | 当前第一项执行任务 |
| P2-A Owner adjudication 20 + semantic checks 60 | NOT STARTED | 新 v2.1 Development-20 包生成后开展 |
| P2-B Held-out labels 30 + semantic checks 90 | NOT PREPARED | P4 前置；P2-A 完成、Rubric/prompt 冻结后另行实现 |
| P3 | NOT STARTED | 等 P2-A/P2-B 验收后做模型固定与 CPU 预检 |
| P4 GPU Pilot | NOT AUTHORIZED | 需单独明确授权 |
| P6 1000 batch / SFT | NOT AUTHORIZED | 独立门禁，不在本任务授权内 |

**下一 Agent 立即执行 P2-A：** 在 Owner Mac 的 `/Users/keedle/workspace/storyforge-r60-ledger-diagnostics` worktree，先检查工作区状态和分支，刷新到当前 PR head；确认 v2.1 新输出目录不存在、父目录权限满足 0700 后，运行 `scripts/r60_owner_adjudication_v2.py` dry-run。只有 SAFE 严格为 `P2_OWNER_BLIND_PACKET_PREFLIGHT_PASS__NO_FILES_WRITTEN`、`cases_prepared=20`、`files_written=0`、Locked20/Severe10 未暴露时，才显式追加 `--write`。命令见 8.21。不要重做 P0/P1，不要运行模型/GPU/HF Job。

本次历史状态核验仅证明当时 GitHub HEAD 的五组 Actions 通过，不证明 Owner 私有 v2.1 包已生成或 Owner 审核已完成；后续文档提交后的最新 HEAD/CI 必须重新核验。Quality-v1 admitted=0；training_authorized=false。


### 8.26 P2-B Held-out Owner reference labels：P4 前置缺口（2026-11-09）

P2-A Development-20 是当前第一项工作；不得因此误认为 P4 的 30 条 held-out 样本已有 Owner ground truth。

P4 样本是 Gold72 Locked Regression 20 + R60 Severe10 10。它们必须在 P2-A 完成、Rubric v2.1 / prompt 规则冻结后，另行建立 30 条 Owner reference labels：
- 30 条独立 blind packets / Owner results；
- 90 条逐维 semantic entailment checks（30 cases × 3 dimensions）；
- 独立 blind IDs、顺序、私有输出目录、manifest 和 SHA receipt；
- Owner labels 与 ID Map 保持私有，直到三模型 P4 预测及 checkpoint 冻结。

**已核验的实现缺口：** 当前 `hf_owner_adjudication_v2.verify_owner_results()` 固定要求 20 packets / 20 results / 60 checks；当前 CLI builder 只生成 Gold72 Development-20。不得将 30/30/90 输入现有验证器，也不得为图方便放宽 P2-A 的 20/60 固定合同。

P2-A 完成后，先设计并合成测试独立版本化的 P2-B 30/90 packet builder / verifier；如拟参数化复用，必须证明旧 20/60 合同和既有 v2 receipts 不受影响。未完成此工具与 Owner reference labels 前，P4 不满足启动条件。不得提前解锁、查看或把 locked labels 暴露给模型/Prompt 开发者。

P2-B 不要求案例审核员提供数据来源、版权/权利、隐私、数据使用授权或数据隔离证据；只按 Rubric v2.1 判断故事内容的三个严重维度。


---

## 0.2 2026-11-09 最新执行校正：P2-A Owner 批准已完成，进入私有副本规范化

本节优先于本文早期接手状态与 3.1 工作区检查要求。

- Owner 已明确回复“采纳”，采纳 35/35 AI Advisory：Player Agency 16、Safety 19，全部保留 `NOT_SUPPORTED`；verdict changes=0，semantic rechecks=0。
- AI Advisory SAFE 已记录：35/35，`owner_final_decision_recorded=false`（生成时的 AI 身份事实）；Owner 的最终批准另由明确回复及新副本内 Owner approval record 表达。
- 原始 packet/results/semantic/schema/AI Advisory 全部冻结，不能覆盖。
- PR #29 已合并到本分支，合并提交 `24eb9f78de6f6e953d84a150d65f020da6ddb4ef`。新增：
  - `scripts/r60_owner_approved_package_normalizer_v1.py`
  - `tests/test_r60_owner_approved_package_normalizer_v1.py`
  - `docs/R60_P2A_OWNER_PACKAGE_NORMALIZER_V1_CN.md`
- 合并提交的六组 GitHub Actions 均 completed/success：`test`、`resolve-and-verify`、`runtime-quality-gates`、`synthetic-and-r57`、`r58-source-json-structure`、`r58-synthetic`。
- PR #25 仍为 Open / Draft；当前分支 HEAD 已更新为上述合并提交。不要因本次工具合并而自动合并或关闭 PR #25。

### Owner Mac 执行方式（不要求清理原 worktree）

此前 3.1 中“发现未提交修改则停止”的要求已被 Owner 明确撤销。不得 reset、clean、stash、覆盖或要求用户先提交 Owner Mac 的其他修改。为避免旧 worktree 代码版本不一致，推荐直接在一个**全新独立目录** clone 当前分支；原 worktree 保持原样：

```bash
set -euo pipefail
RUN="$HOME/workspace/storyforge-r60-p2a-owner-runner"
test ! -e "$RUN"
git clone --single-branch --branch r60/gold192-history-v3-adapter \
  https://github.com/sunxu/storyforge.git "$RUN"
cd "$RUN"
test "$(git rev-parse HEAD)" = "24eb9f78de6f6e953d84a150d65f020da6ddb4ef"
```

将以下六份私有输入以原文件名放入一个新建的 0700 私有 staging 目录，文件均为 0600；不移动、不改写原文件：
- `OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl`
- `OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl`
- `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`
- `OWNER_ADJUDICATION_SCHEMA_V2.json`
- `OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_PRIVATE.jsonl`
- `OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_SAFE.json`

另外创建 0600 的 SHA pin JSON，精确 pin 前四份要求的文件：packet、results、semantic checks、AI Advisory JSONL。SAFE 文件本身会按严格字段核验；其 SHA 不作为第四项以外的额外必需 pin。staging 目录必须 0700，pin 文件保存在 Owner 私有目录，不得进入仓库或 GitHub。

运行命令见 `docs/R60_P2A_OWNER_PACKAGE_NORMALIZER_V1_CN.md`。必须显式传入 `--owner-approved`；输出目录必须是此前不存在的新目录。成功验收条件：20 cases、60 semantic checks、35 history assertions、60 target locators、20 history locators；官方 CLI verifier 成功生成 SAFE/Manifest；semantic HOLD 原样保留；原始输入 SHA 不变；`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。

**当前实际阻塞仅是这六份 Owner 私有输入尚未由本会话读取/执行。** ChatGPT 已完成 GitHub 代码与 CI 交付；不得伪称本地私有包已规范化或 P2-A 已 PASS。收到真实 SAFE 和 SHA 回执后再更新阶段状态。P2-B、P3、GPU、HF Job、SFT 均不在本次授权范围。


---

## 0.3 2026-11-09 Owner 追加采纳 SUPPORTED 4/4；P2-A normalizer v2

Owner 已明确回复“采纳”4 条 SUPPORTED / Player Agency 的 AI Advisory。批准范围现为精确 39 个 case-dimension pair：
- NOT_SUPPORTED 35 条：Player Agency 16、Safety 19，保持原 verdict。
- SUPPORTED 4 条：Player Agency 4，保持原 verdict。
- 39 条仅将 `context_coverage.history_complete` 从 false 改为 true；verdict changes=0，semantic rechecks=0。

新增可复用 v2（不覆盖 v1）：
- `scripts/r60_owner_approved_package_normalizer_v2.py`
- `tests/test_r60_owner_approved_package_normalizer_v2.py`
- `docs/R60_P2A_OWNER_PACKAGE_NORMALIZER_V2_CN.md`

v2 同时校验 35-row AI Advisory + SAFE、4-row worksheet + AI Advisory + SAFE，精确绑定 4 条原始结果行 [5, 6, 11, 19]、case ID、assessment 和 semantic check；对 39 个精确 pair 应用 history completeness 确认。原始 60 semantic checks 原样复制，原版 Rubric/Verifier 不修改。输入六份关键 JSONL 的 SHA pin 已在 v2 Runbook 固定。输出使用全新目录 `owner-adjudication-dev20-rubric-v2-1-20261109-owner-approved-v2`。

**v2 代码已推送当前工作分支，等待 GitHub Actions 验证；在 CI PASS 前不得运行真实私有包。** 运行成功门槛仍是 20 results / 60 checks、39 history confirmations、60 target locator、20 history locator；SAFE 必须保留所有原始 semantic HOLD，quality_v1_admitted=0、training_authorized=false、gpu_started=false。

P2-A 尚未 PASS；Owner 的 39 项批准已完成，但正式独立副本及官方 CLI verifier 仍待执行。不得启动 P2-B、P3、GPU/HF Job 或 SFT。


### v2 CI 验证结果（2026-11-09）

v2 最终代码提交 `28d9efa9b186484b61163e150a21316c9cc1f8cb` 的六组 GitHub Actions 全部 completed/success：
- `test`（含 changed-file Ruff 与 pytest）：PASS
- `resolve-and-verify`：PASS
- `runtime-quality-gates`：PASS
- `synthetic-and-r57`：PASS
- `r58-source-json-structure`：PASS
- `r58-synthetic`：PASS

首次 CI 暴露的 Ruff F841/F821 均已修复，最终提交全套 CI PASS。v2 现在可以用于 Owner Mac 私有包执行；这只表示代码 CI 通过，不代表真实私有包已生成或 P2-A 已 PASS。


## 0.4 2026-11-09 方向校正：Development-20 不是优秀训练样本集；Positive Gold 独立建设

已明确区分两种任务：
- Gold72 Development-20 / Locked Regression-20 是 A V3 / B2 审核分歧样本，用于校准严重问题 Rubric；不是按文学质量筛出的优秀回复。
- R60 Severe10 是严重问题校准集；也不是正向示范集。
- 20 条 Owner 裁决的三维分布（Player Agency 4/16/0、Hard Rule 0/0/20、Safety 0/19/1）不能推出 20 条整体质量等级。SUPPORTED/NOT_SUPPORTED 都不是六维文学质量 PASS。

新增独立计划：`docs/R60_POSITIVE_GOLD_SELECTION_PLAN_CN.md`。Positive Gold 以冻结的 1,000 条真实技术候选池为候选来源，复用既有 Quality-v1 六维分数门槛与三项严重旗标；先小批、再 Owner 确认、再独立冻结，不设必须凑足的 PASS 数。Gold87/Gold108 是历史候选，不能自动转换成当前 Positive Gold 或 Quality-v1 准入。该计划未启动真实审核、未启动 1,000 条全量审核、未启动 HF/GPU/SFT。

### P2-A 当前阻塞：SUPPORTED Player Agency 的 rule_basis 类型

Owner 提供的只读诊断确认原结果第 5、6、11、19 行的 `basis_type` 均为 `player_agency`，而 Rubric v2.1 对 SUPPORTED / Player Agency 要求 `player_agency_boundary`。这不是 history_complete 问题。不得自动改写原 Owner results、rule_id、scope 或 basis_type；必须先由 Owner 明确确认是否允许在派生副本中仅将这 4 个精确 pair 的类型标签规范化为 `player_agency_boundary`，且不得改变 verdict / evidence / semantic checks。Normalizer v2 已增加 fail-closed 检查，返回 `SUPPORTED_RULE_BASIS_TYPE_REQUIRES_OWNER_REVIEW`，不会静默转换。P2-A 仍 HOLD，正式输出目录不得创建。


## 2026-11-09 Owner 补充批准：四条 basis_type 精确映射

Owner 明确批准仅在派生副本中，将四条 SUPPORTED / Player Agency 的 `rule_basis[].basis_type` 从 `player_agency` 映射为 `player_agency_boundary`。Normalizer v2 已实现严格四 pair allowlist：恰好 4 个、维度必须为 player_agency、原标签必须完全匹配；不匹配即 HOLD。原始结果文件不修改；verdict、evidence、其他 rule_basis 字段、60 条 semantic checks 均保持不变。私有 approval 记录映射和不变性断言，SAFE 增加 `basis_type_normalized=4`。

下一步：CI 全部通过后，在 Owner Mac 私有目录执行 create-only normalizer；验证原始 SHA 不变、输出字段差异严格符合批准范围，再运行官方 CLI verifier。未经真实私有包验证不得宣称 P2-A PASS。


## 2026-11-09 semantic reviewer binding 修复

Owner Mac 诊断确认 60 条 semantic checks 全部缺少 `reviewer_role` / `reviewer_ref`。Owner 先前已明确说明 60 项语义复核由 Owner 独立完成。Normalizer v2 现仅在派生副本回填统一标识：`OWNER_INDEPENDENT` / `owner-independent-r60-p2a-dev20-20261109`。要求恰好 60 行；已有冲突身份信息不得覆盖，直接 HOLD。原始 semantic JSONL 不变。

私有 approval 和 SAFE 将其标记为 `RETROSPECTIVE_DERIVED_COPY_METADATA`，并明确 `cryptographic_identity_attested=false`。这不是密码学身份认证，不伪称独立性已被密码学证明；只是将已完成的 Owner 复核补齐验证器所需的回溯性元数据。官方 verifier 仍须对派生包完整验证。



## 2026-11-09 权威状态更正：60 条 Semantic checks 实为 Owner AI Advisory

Owner 已明确确认：原 `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl` 的 60 条语义复核由 Owner AI 生成，未经 Owner 逐项最终确认。此事实覆盖本文 8.23、8.25 及 0.2/0.3 中任何将该 60 条描述为“Owner 独立完成”或允许回溯补写 `OWNER_INDEPENDENT` 的旧记录。旧 AI checks 不得通过 normalizer 补写 reviewer_role/ref/rubric_version 后作为正式 Owner semantic checks；不得将 AI reviewer 冒充 Owner。

已提交代码保护：`scripts/r60_owner_approved_package_normalizer_v2.py` 现在只接受已经明确记录 `reviewer_role=OWNER_INDEPENDENT` 且 60 条 reviewer_ref 一致的真实 Owner 复核输入；缺失时 fail-closed，返回 `SEMANTIC_REVIEW_NOT_OWNER_FINALIZED_HOLD`。原始 AI checks 继续封存为 Advisory。

新增第二模型盲交叉审核工具：`scripts/r60_p2a_second_model_cross_review.py`。它只读取原始 Development-20 blind packets、20 条 Owner results 和 Rubric v2.1；不读取第一模型的 60 条 semantic checks、35 条/4 条 AI Advisory。它生成新的盲 ID、独立随机顺序、Owner-only ID map、第二模型提示词和私有 SHA manifest。第二模型输出只能标记 `AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`，不满足官方 Owner reviewer 合同。

协议：`docs/R60_P2A_SECOND_MODEL_CROSS_REVIEW_PROTOCOL_V1_CN.md`。第二模型须来自不同模型提供方/模型家族（建议 Claude 或 Gemini 的可用版本），但其结论仍只是 AI Advisory。Owner 最终必须逐项复核 60 项并形成自己的判断、理由和实际时间；AI 一致率不等于 PASS。若外部服务的数据处理条件未获确认，不得上传私有故事正文。

当前状态：P2-A 仍 HOLD；旧 60 条 AI checks 不得作为正式语义复核。下一步先在 Owner Mac 对新 builder 执行 dry-run，确认 20 packets/20 results/60 dimensions、未读取旧 AI 文件、输出目录未创建；再显式 --write 生成本地私有第二模型盲包。第二模型交叉审核和 Owner 最终复核均未完成。不得启动 GPU/HF Job/SFT，不得解锁 Locked20/Severe10，不得进入 P2-B/P3。


## 2026-11-09：CLI Proxy 第二模型批量调用客户端

已新增 `scripts/r60_p2a_openai_compatible_review_client.py`，为 R60 P2-A 提供可复用 OpenAI Chat Completions 客户端。默认模型别名为 `claude-opus-5-5-high`，非流式调用（`stream=false`），每批 5 案例，共 4 批。远程 endpoint 强制 HTTPS；base URL、API key、model 均由环境变量提供，密钥不写入参数或输出。默认只做本地 preflight；真实外发必须显式 `--execute --allow-private-data-egress`。输出严格验证 60 个 blind_id × dimension、七字段合同、枚举及完整 evidence index 覆盖。批次结果和原始响应仅写入 0600 私有文件，支持 `--resume`。本工具只产生 AI Advisory，不产生 Owner 最终裁决。具体环境变量和命令见 `docs/R60_P2A_SECOND_MODEL_CROSS_REVIEW_PROTOCOL_V1_CN.md`。

当前仍缺 Owner Mac 的实际 CLI Proxy Base URL 与本机环境变量配置；未发出任何 API 请求。CI 需验证新客户端及测试后才能视为代码验收。即使 60 行 AI Advisory 生成成功，P2-A 仍须 Owner 最终复核；不启动 GPU/HF Job/SFT。


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


## 2026-11-10 权威更新：ChatGPT Hugging Face OAuth / Bucket RW 故障

- 插件：Hugging Face Plugin v0.1.4，关联日期 2026-11-04，Version ID `asdk_app_v_225a5afb50248191aaab67016a94edc0`，OAuth Application ID `asdk_app_6ac752d4c640819191c206f9cb0dafad`，状态 RELEASED。
- ChatGPT `hf_whoami`：账号 `greenkeedle`，`adradar` 组织角色 `write`；OAuth scopes 为 `openid profile read-mcp read-repos jobs contribute-repos inference-api`。
- ChatGPT 连接器可创建并执行无 Volume CPU Job；提交 `hf://buckets/adradar/storyforge-training:/output` RW Job 返回 HTTP 403。
- Owner Mac CLI 使用同一 `adradar` namespace、`python:3.12`、`cpu-basic` 和相同默认 RW volume 成功完成 Job `6af2ee90ab34849891ab2f6e`：写入 `/output/.p4-rw-probe`、读回 `PASS`、删除文件。
- ChatGPT 无 Volume CPU Job `6af2ec43ab34849891ab279c` 成功。RO Job `6af2ec64ab34849891ab27f8` 仅有提交接受记录，没有可用执行/读回证据，不得写成 RO 端到端 PASS。
- Owner 提供的 Bucket Settings 页面显示 `adradar/storyforge-training` 为组织 Private Bucket，组织成员可查看和上传；未修改 ACL、可见性或 Trusted Publishers。

### 诊断边界
证据将故障收敛到 ChatGPT HF 连接器的 Bucket RW 提交/授权链路，而非 Bucket 普遍不可写、组织余额不足或 Jobs 创建权限整体失效。当前 OAuth scope 缺少 `write-repos` / 专用 Bucket write scope 是待验证假设，不是已证实根因；公开文档没有明确证明其必然导致 Jobs Bucket RW 403。仍需 HF 检查该 OAuth App 的 capability、组织 grant、请求序列化及 403 服务端拒绝原因。

### 后续执行规则
- ChatGPT 直连 Bucket RW：`BLOCKED_403`；P4 私有输出持久化保持 HOLD。Mac CLI 同 Bucket RW：PASS，只是 Owner 受控临时路径，不代表 ChatGPT 链路通过。
- 要求 Hugging Face 检查 OAuth App `asdk_app_6ac752d4c640819191c206f9cb0dafad`（Plugin v0.1.4）是否允许挂载既有组织私有 Bucket RW、`adradar` grant 是否完整，并解释 403。
- 不切个人 namespace，不索取长期 PAT，不修改 Bucket ACL，不配置 Trusted Publishers，不将私有生成正文写入 GitHub / Actions logs / SAFE。
- 不盲目重复提交 RW Job；等待 HF 答复或连接器修复。该问题不影响 CPU Freeze Review SAFE，但阻止正式评估私有输出通道验收。
- 后续 Agent 必须先检查 PR #30 最新评论及本节，避免重复早期“组织余额/Jobs 权限不足”诊断。
- CLI 成功 Job：`https://huggingface.co/jobs/adradar/6af2ee90ab34849891ab2f6e`；ChatGPT 无 Volume Job：`https://huggingface.co/jobs/adradar/6af2ec43ab34849891ab279c`。

## 2026-11-10 补充证据：OAuth 授权确认页面截图（Owner 提供）

Owner 提供的 Hugging Face OAuth 授权页面截图显示：
- Repositories / Read repositories：读取用户可访问的私有及 gated repos。
- Repositories / Contribute to repositories：创建 repos 并管理由该 app 创建的 repos；页面明确注明 `Cannot access other repos`。
- Compute / Jobs：`Start Jobs on your behalf and read their status, logs and outputs`。
- Compute / Inference Providers：代表用户调用 Inference Providers。
- Account / MCP tools：读取 MCP tools。
- Organization grant 选择 `Grant ChatGPT the same access to selected organizations`，且 `Hong Kong Adradar Technology Limited` 已勾选（同时页面显示 Select all organizations 已勾选）。

### 对诊断的影响
该截图确认授权界面确实授予 Jobs 和指定组织访问，但没有单独列出 Bucket / Storage write permission。`Contribute to repositories` 的界面描述明确限定为 app-created repositories，不能据此推导它允许写入既有 `adradar/storyforge-training` Bucket。结合 ChatGPT RW Job 403 与 Mac CLI 同 Bucket RW 成功，最值得 HF 核查的是：Jobs OAuth 授权是否包含对既有组织 Bucket 的 RW mount / Xet write-token 签发能力，或该能力是否需要 OAuth App 额外 capability / grant。

此截图仍不能单独证明根因：页面未展示底层 OAuth scopes、Bucket-specific permission model 或 403 服务端拒绝码。不得把“缺少 Bucket write scope”写成已确认事实。应向 Hugging Face 提供 OAuth App ID `asdk_app_6ac752d4c640819191c206f9cb0dafad`、Plugin v0.1.4、此授权页面截图、Mac CLI Job `6af2ee90ab34849891ab2f6e` 和 ChatGPT RW 403 对照，请其确认 Jobs token 是否能签发既有 Bucket 的 Xet write token。

### Owner 授权范围说明
截图中组织授权范围为选定组织（当前截图同时勾选 Select all organizations 与 Hong Kong Adradar Technology Limited）。后续若重新授权，应只选择完成 StoryForge 工作所需的 `Hong Kong Adradar Technology Limited`，除非 Owner 明确希望授权其他组织；本截图不构成要求扩大组织授权范围的理由。

## 2026-11-10 主线续进：Worker CLI / Job bootstrap 工程实现

Owner 已暂停 ChatGPT-HF OAuth / Bucket RW 故障排查，并将自行在 Mac CLI 执行 HF 任务。ChatGPT 不再提交 HF Job、不测试 Bucket、不更改 OAuth；后续只提供可复用代码、命令、SAFE schema 与回执审查。

当前分支 `r60/p4-generation-eval-framework` 正在完成 P4 Worker CLI / Job execution plan 闭环：
- `worker.py` 保持模型无关的 generation batch engine，不导入 torch / transformers / HF Hub。
- 新增独立 `worker_cli.py`，作为真正的 `python -m storyforge_dataset.generation_eval.worker_cli` 执行入口；必须先通过 Profile freeze/inference/GPU 授权检查，再校验依赖 lock、runtime、manifest、input SHA、输出目录和私有输出权限；未授权时只输出 SAFE HOLD，不加载模型。
- Job plan 固定从 GitHub codeload 下载精确 `code_revision` 的仓库归档，限制归档大小/文件数/解压总量并拒绝路径穿越、符号链接和特殊文件；不依赖 PyTorch 基础镜像预装 git。
- Job 启动后按 `requirements/hf-generation-eval.lock` 使用 `--require-hashes` 安装依赖，再执行独立 Worker CLI；输入挂载路径为 `/input/generation-profile.json`、`/input/manifest.json`、`/input/inputs.jsonl`，输出目录必须为 `/output` 的全新直接子目录。
- Worker 仅将私有生成正文写入 `/output/<run-id>/<role>-outputs.private.json`，create-only、0600；stdout 只输出 SAFE 元数据，不输出生成正文。
- 当前提交 `219fd80f35d8b8e3c2da8a1b2d64a8dddeae008c` 的 Repository CI 与 R60 Generation Eval CI 已 PASS；Runtime Image Candidate 正在执行，尚未报告最终结果。

此代码目前仍是执行入口工程候选，不代表正式 Profile 已冻结或获准执行。未完成实际容器启动/归档下载的无 GPU 验证、运行镜像验证、Owner 本地 HF 端到端执行及 32K 资源预算复核前，不提交正式评估 Job。

### 后续主线顺序
1. 等待当前 HEAD 的 Runtime Image Candidate 真实回执；失败按日志修复，不沿用旧 SHA 的 CI 结果。
2. 增加 Worker CLI 归档 bootstrap 的语法/边界测试及 CPU-only container entrypoint test；确认镜像不依赖未安装的 git。
3. 由 Owner 在 Mac CLI 进行无 GPU/无私有数据的执行入口检查；如需 HF Job，由 Owner 决定并执行。ChatGPT 不代为提交。
4. 复核输出目录契约、SAFE 回收方式和私有正文保管；HF Bucket RW 问题暂时不在 ChatGPT 执行范围内。
5. 完成 32K 长上下文显存/时间/费用上限证据后，生成最终 Profile Freeze Review 包，等待 Owner 单独批准 Profile Freeze。Freeze 不自动授权正式推理。

### 不变的授权边界
`profile_freeze_authorized=false`、`inference_authorized=false`、`gpu_authorized=false`、`training_authorized=false`。不启动 Development20 / Locked30 正式推理、1000 条审核或 SFT；不读取 Locked30 私有案例。