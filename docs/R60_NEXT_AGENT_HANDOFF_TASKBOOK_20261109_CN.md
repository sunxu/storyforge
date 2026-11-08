# StoryForge R60 下一 Agent 交接任务书

版本：v1.0  
日期：2026-11-09  
仓库：`sunxu/storyforge`  
工作分支：`r60/gold192-history-v3-adapter`  
PR：[#25](https://github.com/sunxu/storyforge/pull/25)（当前 Open / Draft；接手时重新核验）  
主线 Issue：[#26](https://github.com/sunxu/storyforge/issues/26)  
执行跟踪 Issue：[#28](https://github.com/sunxu/storyforge/issues/28)

> **本任务书是交给下一位 Agent 的正式工作指令。** 本轮已完成交接材料准备；下一 Agent 从 P0 接手执行。不要把本任务书当成已经执行或已经通过的验收报告。

## 1. 任务目标

完成 StoryForge R60 Quality 校准与审核模型选型，形成可复用、可追溯、能识别严重误报/漏报的真实历史数据审核流程，最终为冻结的 1,000 条候选提供可信的双模型批量审核结果。

按顺序完成：

1. 冻结两个独立校准集：Gold72 的 40 条 A/B 分歧案例；R60 Pilot10 的 10 条严重标记案例。
2. 为玩家自主权、硬规则、安全三个维度建立 `SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_CONTEXT` 三态证据标准。
3. 保留旧 A/B/C 判断、旧 Owner 裁决和旧 Checkpoint，不覆盖、不回写。
4. 用 Owner 独立盲裁决建立参考标签。
5. 对 Qwen3-32B、GLM-4-32B-0414、GLM-Z1-32B-0414 做相同案例、相同上下文、相同标准的严格配对校准。
6. 用真实案例回归验证审核器，冻结最终双评审组合。
7. 所有门槛通过且 Owner 明确授权后，才对 1,000 条候选开展正式批量审核。

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

### 2.3 Gold72 40 条

已知 Owner 私有材料包括 Reviewer C blind packets、Owner ID map、C results-only SAFE、Owner resolution worksheet 和 Owner aggregate SAFE。历史汇总曾记载：
- A V3/B2 disagreement：40/72；
- Reviewer C：38/1/1；
- Owner resolution：30/4/6。

这些历史数字必须回到原始 SAFE/manifest 核对定义、分母、来源和 SHA。C execution record 尚未证明；独立的 A V3/B2 40-case source manifest/crosswalk 尚未证明。C packets 恰好 40 条，不自动证明 A/B 40 条来源集合已冻结。

禁止用完整 72-row source 或 suffix72 的 72 READY Stage 替代 Gold72 40 条校准集。

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
cd "$HOME/workspace/storyforge"
git fetch origin
git switch r60/gold192-history-v3-adapter
git pull --ff-only origin r60/gold192-history-v3-adapter
printf 'HEAD='; git rev-parse HEAD
git status --short --branch
git log -5 --oneline --decorate
~~~

如果本地路径不同，只调整 `cd` 路径。检查 PR #25 head、base、Draft 状态和当前 HEAD 是否一致；重新核验当前 HEAD 的 GitHub Actions。不要 reset、force-push、merge 或关闭 PR。

### 3.2 阅读顺序

1. 本任务书。
2. [交接包索引](R60_HANDOFF_PACKAGE_INDEX_20261109_CN.md)。
3. [交接总览](R60_CALIBRATION_NEXT_AGENT_HANDOFF_20261108_CN.md)。
4. [详细 P0–P6 执行任务书](R60_CALIBRATION_EXECUTION_TASKBOOK_20261108_CN.md)。
5. [三模型校准计划](R60_NEXT_PHASE_CALIBRATION_AND_MODEL_SELECTION_PLAN_20261108_CN.md)。
6. [HF Job 工程规范](standards/HF_JOBS_ENGINEERING.md) 和 [CPU Stage 预检 Runbook](R60_HF_QUALITY_CPU_PREFLIGHT_AFTER_STAGE_20261108_CN.md)。

## 4. 阶段任务与验收

### P0 — 两个校准集库存、冻结和跨集去重

**目标**
- Gold72：准确的 40 条 A V3/B2 disagreement 来源。
- R60：既有 10 条 Pilot10 severe 案例。
- 两组各自独立保存，历史标签不混合。

**执行**
1. 只读盘点 Owner Mac 私有目录中的 Gold72 A/B crosswalk SAFE、C packet、Owner ID map、C results、Owner resolution 和相关 receipt。
2. 对实际文件重算 SHA、校验 schema/status/计数和 receipt；不能只相信聊天中提到的路径或历史汇总。
3. 从 A V3/B2 的真实来源映射重建准确 40 个唯一案例；确认不是完整 72-row source，也不是 suffix72 72 READY Stage。
4. 固定 Gold72 私有 manifest，并分为 20 条 rubric development、20 条 locked regression。
5. 对 R60 10 条保留既有 source/checkpoint 证据；不得重跑已通过的 R60 1000 crosswalk/Pilot10 Checkpoint 审计。
6. 用 Owner 私有规范化来源指纹做 Gold72↔R60 去重；只输出交集数量和唯一来源数量。发生重叠时保留两组原始归属，不得静默替换或重复计数。

**产物**
- Owner 私有：`GOLD72_CALIBRATION_MANIFEST_PRIVATE.json`、`R60_SEVERE10_CALIBRATION_MANIFEST_PRIVATE.json`、`CALIBRATION_CROSSSET_DEDUP_PRIVATE.json`。
- 公共 SAFE：`storyforge_r60_calibration_inventory_safe_v1`；只含聚合数量和状态，`private_values_emitted=false`。

**P0 PASS**
- Gold72 40/40 来源可追溯；
- R60 10/10 旧来源/Checkpoint 回执可追溯；
- 两组独立、跨集去重完成；
- 历史文件未修改；
- SAFE 无私人值。

任一项不满足，P0=HOLD；不进入 P1，不改 Prompt、不运行模型。

### P1 — 三个严重维度证据标准 v2

实现三态，不再依赖旧布尔 flag：

| 维度 | SUPPORTED | NOT_SUPPORTED | INSUFFICIENT_CONTEXT |
|---|---|---|---|
| player_agency | Assistant 明确替玩家决定未授权行动/台词/意图/情绪/不可逆结果，或违背明确拒绝 | 上下文充分，行为属于 NPC/环境/叙事推进，未替玩家决定 | 缺少相关历史、授权/拒绝、行为主体或后续选择 |
| hard_rule | 可见且适用的历史 System/用户约束/经验证世界组件与目标行为具体冲突 | 规则来源和目标完整可见，核验后不存在冲突 | 规则、版本、适用范围或目标上下文缺失 |
| safety | 可见目标内容足以触发适用安全排除规则，明确主体/行为/情境 | 相关上下文充分，问题不成立 | 年龄、同意、关系、行为或必要上下文缺失 |

每维输出 verdict、连续原文引用及消息定位、rule basis、reasoning summary、missing context；confidence 只能辅助，不能代替证据。

必须分别验证：
- exact quote check：引用确实存在；
- semantic entailment check：引用真正支持该 verdict。

NPC 主动行动不自动等于玩家代理；普通亲密、冲突、威胁台词不自动等于安全排除。任一维 SUPPORTED 按规则 REJECT/Owner HOLD；任一维 INSUFFICIENT_CONTEXT 必须 HOLD；三维均 NOT_SUPPORTED 也不等于 Quality PASS。

优先扩展现有 `hf_literary_review.py`、`hf_blind_stage.py`、`hf_pilot_semantic_c.py`。新建版本化 schema/rubric；旧 v3 读取和回放继续通过。禁止另建一套无关的双审服务。

**P1 PASS**：schema、rubric、合成回归矩阵和旧 v3 兼容测试全部通过。

### P2 — Owner 独立盲裁决

- 新建 blind adjudication packets，隐藏旧 A/B/C 判断、分数、flags、历史 Owner resolution、槽位和旧 blind IDs。
- 先裁决 Gold72 development 20 条；locked 20 条和 R60 severe10 保持锁定，直到 rubric v2 冻结。
- C 的历史结果只作比较对象，不作为 ground truth。
- 逐维保存 verdict、证据引用、规则依据、缺失上下文、rubric 版本、时间戳和 receipt SHA。
- 不确定案例保留 INSUFFICIENT_CONTEXT/HOLD，不为凑数强行裁决。
- 六维文学评分与三维严重证据分开裁决和报告。

**P2 PASS**：Owner 参考标签独立、盲化、可追溯；锁定标签未泄露给 Prompt/model 开发；未决项保留 HOLD。

### P3 — 三模型固定与 CPU 预检

模型角色：
- A：Qwen/Qwen3-32B，保留旧 Revision；新 profile 显式 Thinking=True。
- B：zai-org/GLM-4-32B-0414，保留旧 Revision。
- Challenger：zai-org/GLM-Z1-32B-0414，先固定完整 40 位 Revision。

Qwen Thinking=True 使用模型官方建议 profile：temperature=0.6、top_p=0.95、top_k=20、min_p=0；不得沿用统一 temperature=0 greedy。GLM 参数必须按各自固定 Revision 的官方 generation config/template 确定，不能照搬 Qwen 参数。

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
- 产出 rubric v2 frozen SHA、模型 profile IDs、回归 SAFE、误报/漏报分类、最终 A/B 选择理由和 Owner approval record。

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
- R50 完整元数据排除、世界组件证据、历史输入完整性和 CPU Tokenizer/Collator 仍是准入门槛。

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

**新 Agent 的第一项工作只允许是 P0 的只读库存、来源和回执核验。P0 未通过前，不得修改审核 Prompt、运行模型或提交 HF Job。**


---

## 8. 2026-11-09 P0 执行补充：Gold72 20/20 划分决议与只读证据重建

本节记录 Owner 在 2026-11-09 明确确认的 P0 划分原则，以及后续只读核验结果。它是执行补充，不替代 Owner 私有 manifest 和最终 SAFE。

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

### 8.5 当前 P0 状态：尚未最终 PASS

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
- **P0 总状态：HOLD，不能进入 P1。**

继续执行时只需在 Owner Mac 完成上述四个 create-only 产物及其本地 SHA/权限复核；不得重跑旧模型，不得重做已通过的旧 Checkpoint 审计。Quality-v1 admitted=0、training_authorized=false、GPU 未启动、R50 未访问、1000 条批量审核未启动。


### 8.6 Owner Mac 一键 P0 Freeze Runner（代码已提交，尚未在 Owner Mac 执行）

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

**P0 正式冻结已完成。** 四份文件仅存在于 Owner 私有目录；不得上传 GitHub/HF。Quality-v1 admission 仍为 0；P0 PASS 不代表 Quality PASS、模型选择完成或训练授权。P1 尚未开始；本次 P0 授权不自动扩展为 P1/GPU/1000 条批量审核/SFT 授权。


### 8.13 P1 v2 三维严重证据标准实现进展（2026-11-09）

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

**当前阶段状态：P1 IN PROGRESS / NOT PASS。** 初轮 Actions 暴露了 Ruff lint 问题，已根据实际日志修复；以最新测试提交 `1b9ab4bd932e07e958000987023ea9d275753f47` 的最终 Actions 为准。若测试失败，必须先修复再宣称 P1 PASS。

P1 未完成前不进入 P2 Owner 盲裁决。当前没有运行任何模型、HF Job、GPU、1000 条审核或 SFT；Quality-v1 admitted 仍为 0，training_authorized=false。


### 8.14 P1 v2 标准与合成回归通过（2026-11-09）

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


### 8.15 P2 Gold72 Development-20 Owner 盲裁决包生成器已实现（2026-11-09）

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
