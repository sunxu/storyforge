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
