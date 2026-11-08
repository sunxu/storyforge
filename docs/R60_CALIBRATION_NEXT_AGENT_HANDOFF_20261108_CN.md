# StoryForge R60 下一阶段 Agent 交接总览：Quality 校准与模型选型

更新日期：2026-11-08  
适用分支：r60/gold192-history-v3-adapter  
关联 PR：[ #25 ](https://github.com/sunxu/storyforge/pull/25)  
主线 Issue：[ #26 ](https://github.com/sunxu/storyforge/issues/26)  
专项跟踪 Issue：[ #28 ](https://github.com/sunxu/storyforge/issues/28)  
执行任务：[R60 校准执行任务书](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)  
上位计划：[R60 下一阶段校准与三模型配对评估计划](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md)

## 0. 新 Agent 接手时的唯一目标

当前工作进入 **审核标准校准 → 模型严格配对评估 → 审核器回归 → 1000 条真实候选批量审核** 阶段。

最终目标：把 StoryForge 已有的真实历史候选，交给一套经过真实案例校准、保留证据、追溯模型和规则版本、能够量化误报/漏报的可复用 Quality Pipeline，筛出真正可训练样本。

本交接文档和任务书按用户最新指示整理。**当前阶段不重新讨论权利、协议或重新开展权益来源调查**；按 Owner 对本项目校准集和候选池的明确授权推进。该指示不允许把私人原文、身份、crosswalk 或凭据提交 GitHub/HF 公共位置，数据仍留在 Owner 控制的私有环境。

## 1. 接手必读顺序

1. 本文：当前状态、历史事实、边界和接手原则。
2. [执行任务书](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)：按 P0→P6 顺序执行，含命令、产物和验收。
3. [统一计划](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md)：阶段定义和模型评估设计。
4. [R60 主线状态](R60_REAL_HISTORY_SFT_MAINLINE_CN.md)：历史执行记录与当前准入状态。
5. [Reviewer C 报告](R60_HF_PILOT10_C_BLIND_SEMANTIC_REVIEW_20261108_CN.md)：10 条严重问题三态结果。
6. [Owner Pairwise 报告](R60_HF_PILOT10_OWNER_PAIRWISE_AND_CALIBRATION_20261108_CN.md)：A/B 5+5 不相交、摘要核验和私有审计器。
7. [HF Quality Pipeline 说明](R60_HF_QUALITY_PIPELINE_REUSABLE_1000_CN.md)：现有可复用实现与 1000 候选 Stage。
8. [HF Job 工程规范](standards/HF_JOBS_ENGINEERING.md) 和 [HF CPU Stage 后预检 Runbook](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md)。

## 2. 仓库、分支、PR、Issue 的已核实状态

| 项目 | 当前核实值 |
|---|---|
| 仓库 | sunxu/storyforge（Private） |
| 工作分支 | r60/gold192-history-v3-adapter |
| PR | #25，Open |
| PR 标题 | R60 V3 Gold192 Ledger history recovery adapter |
| 本次交接前 HEAD | 945ab236e36e2451d6e059e4e4c404ba41fbb1e9 |
| 主线 Issue | #26，Open |
| 旧 Issue #27 | 已关闭（not_planned）；本阶段不重开、不重复做权益/协议调查 |
| 最近 CI | 在 945ab2... 上四项 workflow 已全部 SUCCESS |

最近 CI 核验：
- R60 HF Runtime CI：SUCCESS
- Gold Quality Pipeline (synthetic + R57 regression)：SUCCESS
- R58 scoped synthetic (no training)：SUCCESS
- CI：SUCCESS

新 Agent 必须重新 fetch 并核对最新 HEAD 和 CI；上表是本次交接编写时的基线，不保证接手时分支未变化。不要 reset、force-push、merge 或关闭 PR。

## 3. 已完成且不能重复的工作

### 3.1 候选池

- R60 真实历史候选池已冻结为 1,000 条（早期 6 条 Seed + 新增 994 条；20 个私有扩样页、400 个 Story 的扩样过程已完成）。
- 1,000 是候选数量，不是质量 PASS 数，不是训练准入数。
- HF 1000 条盲审 Stage 已 prepare，状态为 HF_QUALITY_BLIND_STAGE_READY__NOT_SUBMITTED。
- 对该 1000 Stage 的 audit 曾返回 A=0、B=0、complete_pairs=0、HOLD=1000；这表示该 1000 Stage 尚无 A/B 推理结果，不能与后续独立 5+5 GPU Pilot 混淆。
- 当前 quality_v1_admitted=0、training_authorized=false。

### 3.2 已完成的 R60 GPU 小 Pilot

- Reviewer A：HF Job 6af056bb0e0338d1bb84b025，Qwen3-32B，5 条，v2 Checkpoint，5/5 REJECT。
- Reviewer B：HF Job 6af060700e0338d1bb84b025，GLM-4-32B-0414，5 条，v3 Checkpoint，5/5 REJECT。
- A 与 B 的 5 条各自独立抽取。Owner 对 25 组可见历史+目标全文比较后，matched_cases=0、唯一来源案例 10 条。
- 因此不能声称两模型对同一案例达成一致；两个 5/5 REJECT 只是不同案例的输出分布。
- 两槽 10 条均出现 serious_player_agency=true，且存在严重 flag 与六维评分/文字说明冲突风险。

### 3.3 Reviewer C 与 Owner 对账

Owner 回传的 SAFE 显示：
- C 10/10 完成、10 个新会话、盲输入；
- C 结果与原始来源/Owner 映射绑定校验通过；
- 执行证据属于 Owner 本地 Codex 回执，不是远端模型身份的独立公证；
- model_identity_independently_verified=false、reviewer_c_independence_verified=false；
- 三维结果：
  - hard_rule：C 10/10 NOT_SUPPORTED；旧模型硬规则 flag 有 4/10 为 true；
  - player_agency：C SUPPORTED=3、NOT_SUPPORTED=7；旧模型 player-agency flag 10/10 为 true；
  - safety：C SUPPORTED=5、NOT_SUPPORTED=1、INSUFFICIENT_CONTEXT=4。
- 这组 C 输出是有价值的独立盲判断，但不是 Owner 最终语义真值。仍须按证据逐案仲裁。
- semantic_severity_adjudication_complete=false、quality_v1_admitted=0、training_authorized=false 保持。

### 3.4 Gold72 历史校准集

- Gold72 有 40 条 A/B 分歧案例，必须完整保留，作为独立校准集。
- 先前汇总曾记载 C 对 40 条为 PASS=38、HOLD=1、REJECT=1，Owner 最终裁决为 PASS=30、HOLD=4、REJECT=6。新 Agent 必须先从 Owner 私有 SAFE/manifest/收据复核这些数字，不能只依赖聊天摘要。
- 这些历史结果是历史证据，不自动成为新版本规则的独立盲参考标签；新版本 Owner adjudication 必须另存，不能覆盖历史裁决。
- 建议将 Gold72 40 条划分为 20 条规则开发集和 20 条锁定回归集；私有 crosswalk 固定分组，公开只存聚合数量和哈希。


## 3.5 交接准备阶段已收到的私有证据（2026-11-08）

本节只记录交接准备期间 Owner 已提供的脱敏摘要，不代表新 Agent 已完成 P0，也不代表训练准入。

| 证据 | 已确认内容 | 尚未确认 / 不得推断 |
|---|---|---|
| R60 Pilot10 Owner Pairwise SAFE | 已收到 Owner 私有审计 SAFE；A=5、B=5；两槽均 5/5 REJECT；matched_cases=0、unique_source_cases=10；10/10 Checkpoint receipt 与 input SHA 绑定验证通过；Owner manifest receipt 通过 | 不能声称 A/B 对相同案例一致；语义严重程度裁决仍未完成；不能转成 Quality PASS |
| Reviewer C | 已完成 10/10 盲输入和结果绑定；hard_rule 10/10 NOT_SUPPORTED；player_agency=3 SUPPORTED/7 NOT_SUPPORTED；safety=5 SUPPORTED/1 NOT_SUPPORTED/4 INSUFFICIENT_CONTEXT | 模型身份独立验证与 Reviewer C 独立性仍未通过；不是 Owner 最终真值 |
| 1000 条 Owner crosswalk | 已有 `OWNER_PAIRWISE_AUDIT_COMPLETE__SEMANTIC_HOLD` SAFE；`owner_manifest_receipt_verified=true`、`input_hash_and_cross_slot_binding_verified=true`；A/B 两槽各 1000/1000 来源映射、输入 SHA 与跨槽 source binding 验证通过；10/10 Checkpoint receipt/input SHA 通过 | `matched_cases=0`、`unique_source_cases=10`；只证明 1000 条来源映射及 10 个 Pilot 回执完整，不证明 A/B 在同一案例上达成一致，也不完成严重度语义裁决 |
| Gold72 40 条 | 已知历史上存在 40 条 A/B 分歧案例，拟作为独立校准集 | 私有原始材料、40 条唯一来源、历史 C/Owner SAFE 分母与数值、文件 SHA、可冻结 manifest 尚待核验 |

**当前交接状态**：
- Pilot10 SAFE：已收到；摘要层面的来源/Checkpoint 核验结果可引用。
- 1000 crosswalk：已有 Owner Pairwise SAFE 验证 A/B 两槽 1000/1000 来源映射及跨槽绑定通过；无需重复执行旧审计。
- Gold72：尚未完成私有材料盘点和 40 条冻结。
- P0：R60 10 条来源/Checkpoint 审计子项已 PASS；整体仍为 OPEN / NOT COMPLETE，阻塞项是 Gold72 40 条私有材料盘点/冻结及 Gold72↔R60 跨集去重。

Owner 私有文件仅保留在本机受控私有目录。GitHub 不存放其正文、crosswalk 内容、blind IDs、source locators 或逐案 Checkpoint。

## 3.6 R58 Jinja2 故障复发：工程门禁已落实（2026-11-08）

- 独立 Reviewer profile：`requirements/hf-quality-reviewer.in` + `requirements/hf-quality-reviewer.lock`。
- 锁定 Transformers 4.57.1、SentencePiece 0.2.1、Jinja2 3.1.6；Hub 解析为 0.36.2；lock 含 729 个 SHA256 包哈希。
- R59 Qwen3.8 的 `hf-cpu-tokenizer.lock`（Transformers 5.16.1）保持独立，未降级或合并。
- GitHub Actions Run `42495819470`（commit `32c4965d18ef98cacc25f14de86b8ce824fb0bb5`）通过：两份 lock 可重解析、hash-verified install、`pip check`、CPU-only boundary、合成 `apply_chat_template`。
- R60 CPU Runbook 已改为将 Reviewer lock 只读复制到 A/B 输入，远端先校验 SHA256，再执行 `pip install --require-hashes`。
- **边界**：以上是 GitHub CI 与文档/脚本准备完成；Owner Mac 尚未执行新的 lock staging/上传，未提交新的 HF Job，未验证本次目标模型 Tokenizer，也没有 GPU/推理/训练动作。

## 4. 当前代码资产：复用，不要重造

| 文件 | 已有责任 | 新阶段需要做什么 |
|---|---|---|
| src/storyforge_gold_quality/hf_literary_review.py | HF 单模型 vLLM Reviewer、六维评分、布尔 severe flags、严格引用校验、checkpoint、CPU Tokenizer preflight | 增加版本化的三态严重证据合同和模型 profile；旧 v3 结果只读保留 |
| src/storyforge_gold_quality/hf_blind_stage.py | 双 Slot 随机盲化、Owner crosswalk、checkpoint/SAFE 对账 | 扩展为可复用三模型盲 Stage，不能将 crosswalk 挂载到 HF |
| src/storyforge_gold_quality/hf_pilot_pairwise_audit.py | R60 Owner-only 1000/1000 来源映射及 A/B 10 Checkpoint 回执校验 | 作为 R60 私有来源验证先例；不要硬套 Gold72 专用格式 |
| src/storyforge_gold_quality/hf_pilot_semantic_c.py | C 盲包、Owner 映射、C 三态结果 reconcile | 复用其三态语义和 fail-closed 模式；不重跑旧 C |
| src/storyforge_dataset/token_preflight.py | 唯一 Tokenizer Core，默认不关闭 Qwen Thinking | 新版明确记录 enable_thinking；保持旧调用向后兼容 |
| tests/test_hf_pilot_pairwise_audit.py | 现有 synthetic-only 私有配对/回执/语义 C 测试 | 扩充回归覆盖，不要用真实正文做 CI |
| scripts/r60_hf_pilot10_owner_audit.sh | Owner Mac 单命令审计旧 A/B 5+5 | 只作为已完成历史工具，不要重复下载或重跑旧审核 |

### 4.1 当前实现的关键缺口（已从代码读取）

- hf_literary_review.py 的 response_schema() 当前使用三个布尔值：serious_player_agency、hard_fact_or_ban、safety_exclusion。
- 该模块的 validate_response() 只验证布尔 flags、决策/分数和逐字引用；逐字引用真实存在不等于语义上支持严重 flag。
- inference() 当前为所有模型共用 SamplingParams(temperature=0, ...)，不适合直接用于 Qwen3 Thinking。
- token_preflight.encode_chat() 的 disable_thinking=False 默认不传 enable_thinking 参数；Qwen3 Chat Template 默认 Thinking=True，但应在新 profile 中显式固定模式，避免只依赖隐式默认。
- Qwen3 官方模型卡对 Thinking=True 推荐 temperature=0.6、top_p=0.95、top_k=20、min_p=0，并明确不建议 greedy decoding。参考：[Qwen3-32B Model Card](https://huggingface.co/Qwen/Qwen3-32B)。
- GLM-4 与 GLM-Z1 必须读取各自模型 Revision 的官方 Chat Template / generation_config；不要把 Qwen 参数机械套给 GLM。
- 当前三态 C 结构存在于 hf_pilot_semantic_c.py，但通用文学 Reviewer 的输出仍是布尔 flags。新版本必须将三态证据作为独立字段，不能将 C 结果硬塞成旧布尔字段。

## 4A. 已知重复故障：Jinja2 / Chat Template（必须先读）

**R60 的 Jinja2 故障是 R58 已解决问题的重复发生，不应作为未知依赖问题重新排查。**

Owner 提供的既有实测记录：
- 2026-11-01，R58 已验证 `transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`。
- 当时缺少 Jinja2 会使 Transformers Chat Template 抛出 `ImportError`；补齐后，A/B 两组真实 HF CPU Tokenizer 预检均通过。
- 2026-11-08，R60 CPU 诊断再次遇到 Jinja2 缺失导致的 Chat Template 故障。R60 后续修复不代表可以删除依赖基线或跳过预检。

**永久经验与执行约束**
1. `jinja2==3.1.6` 必须作为 Transformers Chat Template 运行依赖显式声明，不能依赖环境偶然预装。
2. 与既有 R58 已验证组合保持一致：`transformers==4.57.1`、`sentencepiece==0.2.1`、`jinja2==3.1.6`；若确需变更版本，先做单独兼容性验证并更新 lock/测试。
3. 每个 HF Runner 的依赖清单/安装命令都必须显式覆盖以上依赖；禁止仅在某一次临时 Job 命令中补装而不沉淀到可复用依赖定义。
4. 提交任何 HF CPU/GPU Job 前，在与目标 Job 相同的镜像/依赖安装步骤中执行 `pip check`、版本/import probe，并实际调用目标 Tokenizer 的 `apply_chat_template` 冒烟测试。
5. 依赖探针失败即停止，不提交 Job；不要用重复提交、换 flavor 或换 namespace 规避。
6. 将“缺 Jinja2 → Chat Template ImportError”加入 Runtime/Tokenizer 合成回归与 Job preflight checklist；CI 应检查依赖 pin 不被意外删除。
7. 复用既有 R58 证据和 R60 Runbook，不重复付费复现已知故障。R60 既有实测详见 [HF CPU Stage 后预检 Runbook](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md)。

## 5. 新阶段模型组合

| 角色 | 模型 | 处理 |
|---|---|---|
| A | Qwen/Qwen3-32B | 保留旧 Revision 9216db5781bf21249d130ec9da846c4624c16137；新配置显式 Thinking=True，独立版本化 |
| B | zai-org/GLM-4-32B-0414 | 保留旧 Revision 077b5c2f5c43bd3239fd605a0600229e8facbd4a，作为现有第二评审 |
| Challenger | zai-org/GLM-Z1-32B-0414 | 先从 HF Hub 读取并固定完整 40 位 Revision；不可使用 main 浮动引用 |

GLM-Z1 是 GLM-4 同家族推理增强 Challenger，不是第三个完全独立模型家族。模型选型以 Owner 参考标签准确性、严重误报/漏报、六维评分、互补性、运行成本和稳定性综合判断，不按排行榜单指标选型。

## 6. 30 条严格配对实验的唯一解释

建议样本设计：
- Gold72：20 条锁定回归案例（从 40 条中 Owner 私有固定）。
- R60 severe set：10 条既有 Pilot10 案例。
- 先在 Owner 私有环境对两组来源指纹去重。若发现交集，不能静默重复计数或更改历史集合；保留两集合原始归属，记录唯一来源数。若必须达到 30 个唯一案例，使用 Owner 明确批准的 reserve case 并在 manifest 中说明来源，不得擅自从已用于规则开发的样本替换。
- 三个模型必须审核完全相同的案例、相同上下文、相同 rubric、相同 JSON Schema；每模型独立盲 ID/顺序/输入目录。
- 30 × 3 = 90 个独立结果；Gold72 与 R60 两组必须分别报告，不将其混成单一统计总体。
- 所有模型不可见 A/B/C 历史输出、Owner 参考标签和历史裁决。

30 条是校准/选型 Pilot，不是生产准确率证明。若某个严重维度的三态类别覆盖不足，必须报告覆盖不足，不能通过多数投票补齐。

## 7. 训练和数据准入状态

- 1,000 条候选池：已冻结。
- 1,000 条批量 A/B：未执行（此前 audit A=0/B=0）。
- Quality-v1 admitted：0。
- 训练授权：false。
- 新 GPU Job：未授权。
- 新 SFT：禁止启动。

即使三个模型的严重问题都返回 NOT_SUPPORTED，也只代表这三类严重问题没有得到支持，不代表文学质量 PASS。仍需六维质量门槛、来源/上下文完整性、R50 完整元数据排除、世界组件证据、数据 Split、CPU Tokenizer/Collator 等既有主线验收。

## 8. 用户明确要求与边界

1. 本阶段不重新探讨权利、协议、隐私政策或许可问题；不要将旧 Issue #27 的历史讨论重新作为当前 P0 阻断，也不要让新 Agent 再次要求用户重复确认。
2. 不修改 RolePlay。
3. 不重做 GPU 可行性 Smoke；不重复运行旧 5+5 A/B 或旧 Reviewer C。
4. 不读取 R50 正文；如需 R50 排除，只允许沿用既有完整元数据/SAFE 机制。
5. 不读取全库原文；本阶段只使用 Owner 已准备的 Gold72 40 条、R60 10 条和经明确冻结的 30 条配对 Pilot。
6. 不将真实正文、完整历史、故事/Session/用户 ID、blind ID、crosswalk、私人 Checkpoint、DSN、凭据写入 GitHub。
7. Owner 私有材料只留 Owner 私有目录/受控私有 Bucket；HF 输入 RO、输出 RW；crosswalk 不上传、不挂载。
8. 不修改数据库、不改角色权限、不把 ChatGPT 的 Supabase 连接身份伪装为 Owner 本地 Reader。
9. 不覆盖任何历史 A/B/C 判断、历史 SAFE、Gold72 原裁决、Gold192 冻结数据。
10. GPU 需要用户单独明确授权；当前没有新 GPU Job 授权。完成文档/代码/合成测试/CPU 预检不等于获得 GPU 授权。
11. 不使用合成数据替代真实主线。合成数据只可用于 CI 的工具单元测试。
12. 不以增加候选数量为目标；当前重点是质量标准与模型选型。

## 9. 交接完成定义

新 Agent 不应把“读完文档”当作完成。按任务书逐项交付：
- P0：两个校准集的 Owner 私有冻结 manifest 和无敏感 SAFE；
- P1：三维严重问题证据 rubric v2 与 schema；
- P2：独立 Owner 参考裁决包和锁定标签；
- P3：三模型 profile、固定 Revision、Qwen Thinking 参数修正和测试；
- P4：30 条配对 manifest、90 个结果的 SHA/receipt 验证及 SAFE；
- P5：Gold72/R60 分轨回归报告；
- P6：Owner 批准后才执行 1000 条批量审核；
- 每个阶段更新 Issue #26、主线文档和私有执行收据，不能只发口头汇报。

**第一步只执行任务书 P0 的只读库存与来源指纹冻结。P0 未通过前，不修改审核 Prompt、不运行模型、不提交 HF Job。**
