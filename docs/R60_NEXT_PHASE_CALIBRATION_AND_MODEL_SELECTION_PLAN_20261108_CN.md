# R60 下一阶段：质量标准校准、三模型配对评估与 1000 条批量审核计划

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

日期：2026-11-08  
目标分支：`r60/gold192-history-v3-adapter`  
关联主线：PR #25 / Issue #26  
当前状态（2026-11-09）：**P0 正式冻结 PASS；P1 Rubric v2.1 / Schema / Prompt / 合成回归 / 旧 v3 兼容 PASS。P2 v2.0 盲审包已 SUPERSEDED；P2 v2.1 Development-20 新包尚未生成，Owner 20 条裁决与 60 条语义复核尚未开始。上一轮核验快照 HEAD `4190c6fe895080d99901cb4c5eb3f221c6948d6d` 的五组 Actions 全部 completed/success；其后交接文档校正提交已推进 HEAD，接手时必须实时核验当前 PR #25 head/CI。当前下一步为 P2 v2.1 新包 dry-run → 显式 `--write`。没有运行新模型、没有提交 HF GPU Job、没有启动 GPU/SFT；Quality-v1 admitted=0、training_authorized=false。**

## 0. 执行目标与当前基线

目标不是再做一次“两个模型都给出 REJECT”的演示，而是建立可重复、可审计的真实历史数据 Quality Pipeline：

1. 先修正严重问题判定标准，明确证据门槛；
2. 保留 Gold72 与 R60 两批历史校准材料，不覆盖原始 A/B/C；
3. 用相同的 30 条真实案例比较 Qwen3、GLM-4、GLM-Z1；
4. 用独立 Owner 证据裁决参照评估误报、漏报和六维评分；
5. 验收通过后，才对冻结的 1,000 条候选执行正式批量审核；
6. Quality-v1 通过、R50 隔离和世界组件证据等门槛满足后，才准备正式 SFT。

当前已知基线：

- Gold72：40 条 A/B 分歧案例已冻结；按案例分为 Development=20 / Locked Regression=20。Development 涉及 5 个 Story、Locked 涉及 6 个 Story、共享 Story=5；Owner 允许 Story 跨集合，不得改为 Story 互斥。
- R60 Pilot10：10 条唯一来源案例；A、B 各自抽取的 5 条没有交集，不能声称 A/B 逐案一致。
- R60 Reviewer C：10/10 已执行并完成来源/结果绑定核验；本地 Codex 回执不是远端模型身份公证。
- R60 C 三维聚合：hard_rule 为 10/10 NOT_SUPPORTED；player_agency 为 SUPPORTED=3、NOT_SUPPORTED=7；safety 为 SUPPORTED=5、NOT_SUPPORTED=1、INSUFFICIENT_CONTEXT=4。
- 现有 A/B/C 原始 Checkpoint 均为历史证据，只读保留。
- 1,000 候选池已冻结，但 Quality-v1 admitted=0、training_authorized=false。

**禁止事项**：不得覆盖旧 A/B/C 判断；不得把 NOT_SUPPORTED 直接等同于文学质量 PASS；不得把 INSUFFICIENT_CONTEXT 当作安全或质量通过；不得用模型多数票代替 Owner 证据裁决；不得在本计划完成前批量审核 1,000 条或启动 SFT。

## 1. 数据集分轨与冻结（P0）

建立两个完全独立的校准集，分开存储、分开报告、分开计算指标：

### 1.1 Gold72 disagreement set

- 范围：既有 40 条 A/B 分歧案例。
- 保留字段：原始 A、B、C 判断、Owner 历史裁决（如存在）、原始来源绑定、引用和 Checkpoint 收据。
- 用途：审核标准开发、分歧类型归纳、历史回归。
- 已冻结的内部划分：20 条规则开发集 + 20 条锁定回归集；按案例分层，Story 允许跨集合（shared Story=5、story_disjoint=false），不得重分组。
- 原始历史标签不因新标准而改写；新裁决另存为版本化标签。

### 1.2 R60 severe-flag set

- 范围：R60 Pilot10 的 10 条唯一来源案例。
- 保留字段：A/B 原始 Checkpoint、C 三维判断、C 执行回执、Owner 来源/结果绑定收据。
- 用途：玩家自主权、硬规则、安全三项严重标记的专项校准。
- 这 10 条与 Gold72 不合并成一个标签池。先在 Owner 私有环境用稳定来源指纹检查两集合是否存在重复；若有重复，保留原集合归属，并在 30 条配对评估中去重替换，不公开来源 ID。
- C 的三态结论只作为一份独立模型判断，不自动作为真值。

### 1.3 冻结规则

- 两集合分别生成只读 manifest，包含来源指纹、案例数、历史版本、输入 SHA、旧 Checkpoint SHA、规则版本。
- 私有正文、故事 ID、Session ID、blind ID、crosswalk、逐案引用只留 Owner 私有目录。
- GitHub 只提交代码、规则、测试、聚合 SAFE 和不含私人正文的哈希/计数。
- 新结果使用新 schema/version 和新目录；禁止覆盖原始结果。

**P0 已正式 PASS**：Owner SAFE 为 `CALIBRATION_INVENTORY_FROZEN__P0_PASS__QUALITY_HOLD`；Gold72=40、R60=10；20/20 案例分层；Gold72↔R60 exact history/target/full-history-target overlap=0；unique source=50。语义近重复检测未执行。P0 已完成，不得重复执行。

## 2. 三项严重问题证据标准（P1）

三个维度必须分别判断，不得互相替代。每一维输出：

- `SUPPORTED`：有足够、可定位的真实证据，达到该维度严重问题定义。
- `NOT_SUPPORTED`：已经检查了足够且相关的上下文，证据明确不满足严重问题门槛。
- `INSUFFICIENT_CONTEXT`：缺少判断所必需的历史、规则、主体、故事内玩家允许/拒绝/同意边界或安全情境，既不能确认，也不能排除。

### 2.1 玩家自主权（player_agency）

只有出现以下可证实行为，才可标记严重问题：

- Assistant 替玩家决定未授权的行动、选择、承诺或不可逆结果；
- Assistant 将玩家未表达的想法、情绪、意图或台词写成既定事实，并实质限制后续选择；
- 在玩家明确拒绝或保留选择权后，Assistant 仍持续控制玩家行为。

不得自动判为严重问题的情况：

- NPC 自己说话、行动、表达情绪、威胁、挑衅或主动推进剧情；
- NPC 主动接近、触碰或改变场景，但没有据此替玩家决定反应；
- 叙事使用第二人称，但仍保留玩家选择空间。

遇到不情愿身体接触、胁迫或其他安全风险时，必须另行审查 safety；不能因为 player_agency 不成立就自动放行。

### 2.2 硬规则与禁令（hard_rule）

`SUPPORTED` 必须同时提供：

1. 可见且适用的故事规则/事实依据（盲包中的历史 System、用户明确约束、随包提供的经验证世界组件）；
2. 目标回复中的精确冲突行为；
3. 两者之间可解释、可复核的矛盾关系。

不得从当前 Story Draft 反向伪造历史 System/Memory；不得臆造不可见世界规则；不得把“没有看到规则”直接当作“规则没有被违反”。

如果所需故事规则/事实依据不在盲包可见范围，使用 `INSUFFICIENT_CONTEXT`。

### 2.3 安全排除（safety）

- 安全独立于文学质量、角色一致性和玩家自主权。
- 必须指出具体内容、主体、关系、行为和适用的安全规则。
- 对年龄、同意、强迫、伤害等关键信息缺失的案例，使用 `INSUFFICIENT_CONTEXT`，不得猜测。
- 不得将普通亲密表达、冲突、威胁性 NPC 台词或文学描写自动归入严重排除；也不得因为文字风格是虚构就跳过安全审查。

### 2.4 证据对象的强制字段

每个维度都要有：

- `verdict`：三态之一；
- `evidence_quote`：来自真实输入的逐字连续引用；
- `evidence_role`：Assistant / User / NPC / System / verified_world_component / unavailable；
- `rule_basis`：适用的定义或规则条目；
- `reasoning_summary`：简短说明引用如何支持或不支持严重问题；
- `missing_context`：若信息不足，明确缺失什么；
- `confidence`：校准置信度，不得代替证据。

引用存在只证明引用真实，不证明语义蕴含成立。引用校验和语义支持校验必须分开。

### 2.5 与训练决策的关系

| 严重维度状态 | 质量处理 |
|---|---|
| 任一维 SUPPORTED | 严重问题成立，REJECT/HOLD 依政策处置，不准入 |
| 任一维 INSUFFICIENT_CONTEXT | HOLD，不准入 |
| 三维均 NOT_SUPPORTED | 仅表示这三项严重问题未被证实；仍须通过六维文学质量和适用的故事世界组件/历史输入质量门槛。数据来源、版权/权利、数据使用授权、隐私合规和数据隔离证明不属于案例审核证据，不得因此 HOLD |

**NOT_SUPPORTED 绝不等于 Quality PASS。** 数据来源/权利/隐私/数据使用授权/隔离证明不属于本轮内容审核证据；P0 manifest/hash、私有目录权限、HF Volume 边界和训练 split 等仍是系统侧工程安全控制，不要求案例审核员收集或判断。

## 3. 独立 Owner 证据裁决参照（P2）

P2 分为开发校准和锁定评估参考两段，不能把 Development 标签与 Locked/Severe held-out 标签混用。

### P2-A：Gold72 Development-20（当前首先执行）

1. 使用当前 P0 manifest 与 Gold72 C blind source packet，按 Rubric v2.1 生成全新的 Development-20 blind packet；旧 v2.0 包 SUPERSEDED，不得使用。
2. Owner 仅查看新 blind packet、instructions、schema 和公开 Rubric v2.1；不查看 ID Map、P0 manifest、旧 A/B/C 结果、旧 Owner resolution、Locked20 或 Severe10。
3. 对 20 个案例分别裁决 player_agency / hard_rule / safety，生成 20 行 Owner result 和 60 行逐维 semantic entailment checks。
4. 使用 storyforge_severity_semantic_entailment_check_v2 固定接口和私有验证器；具体字段、索引覆盖、UTC、HOLD 规则见主交接任务书 8.23。
5. 这 20 条用于开发/校准，不作为 held-out 模型准确率评估集。

### P2-B：锁定评估参考标签（P4 前置，当前不解锁）

在 P2-A 完成且 Rubric v2.1 / prompt 规则冻结后，另行准备并经 Owner 确认：Gold72 Locked Regression 20、R60 Severe10 10。为这 30 条建立独立 blind packets、Owner 参考标签及逐维语义复核。不得复用 Development-20 的 ID、顺序、输出或映射；模型/Prompt 开发者不得接触这 30 条参考标签，直到三模型预测与 checkpoint 冻结。若当前代码没有对应的安全生成器，先实现并合成测试独立 create-only builder；不得手工复制/解锁私有 manifest 来绕过工具门禁。

### 通用裁决要求

- 复核者只看盲包提供的故事历史上下文和目标，不看旧 A/B/C 判断、严重 flags、旧 Owner resolution 或后验分层。
- 只审核 Player Agency、Hard Rule、Safety 内容语义；不得要求数据来源、版权/权利、隐私、数据使用授权或数据隔离证明，也不得因缺少这些材料而 HOLD。
- 按三态定义分别裁决；六维文学质量另行评分，不与三维严重证据混合。
- 每条参考标签必须附精确引用、适用故事规则、缺失上下文、rubric version、timestamp 和 receipt。
- 对无法独立裁决的案例保留 INSUFFICIENT_CONTEXT/HOLD，不得为了提高可用样本数强行标注。
- 原始 A/B/C 判断保留为历史预测，不参与参考标签生成。

参考标签是项目内 Owner evidence adjudication reference，不是普适真值或外部认证金标准。

**P2 完成门槛**：Development-20 的 20+60 回执验证通过；Held-out Locked20 + Severe10 的 30 条参考标签与逐维语义复核已独立冻结；两组盲化隔离有效；所有不确定项保留 HOLD。P2 完成不等于 Quality-v1 admission。

## 4. 三模型选型与推理配置（P3）

### 4.1 固定模型角色

| 角色 | 模型 | 处理 |
|---|---|---|
| A 基线 | `Qwen/Qwen3-32B` | 保留既有模型 Revision；新实验使用修正后的独立配置版本 |
| B 基线 | `zai-org/GLM-4-32B-0414` | 保留既有 Revision，作为第二评审基线 |
| Challenger | `zai-org/GLM-Z1-32B-0414` | 新增候选；查询并固定完整 40 位 Hub Revision 后才可运行 |

GLM-Z1-32B-0414 是 GLM-4-32B-0414 基础上强化推理训练的模型，适合作为同家族 challenger；但它不是与 GLM-4 完全独立的模型家族。最终不能仅按排行榜选型，必须比较它是否带来更好的证据判断和互补性。

### 4.2 Qwen3 Thinking/采样配置修正

当前仓库的 tokenizer wrapper 默认不关闭 Thinking，而 Reviewer 使用 `temperature=0`。Qwen3 官方模型卡对 Thinking 模式推荐 `temperature=0.6`、`top_p=0.95`、`top_k=20`、`min_p=0`，并明确不建议 Thinking 模式采用 greedy decoding。

新版本应：

- 明确设置 `enable_thinking=true`，不依赖隐式默认值；
- 使用官方 Thinking 推荐采样参数；
- 记录并固定 seed、vLLM/Transformers 版本、GPU 镜像 digest、模型 Revision、Tokenizer SHA、Prompt SHA、输出预算；
- 记录完整 finish_reason；长度截断、格式错误、引用失败一律 HOLD；
- 旧 Qwen 5 条 Pilot 结果保持原样，不能与新配置结果混作同一实验。

参考：[Qwen3-32B 官方模型卡与推荐参数](https://huggingface.co/Qwen/Qwen3-32B)。

### 4.3 GLM 配置

- GLM-4 和 GLM-Z1 使用各自模型的 Chat Template 与官方 generation config。
- 不得把 Qwen 的 temperature/top_p/top_k 参数机械套给 GLM。
- 在提交前读取并固定对应 Revision 的 `generation_config.json`、Tokenizer 和 Chat Template SHA。
- 如果模型推理模板或 vLLM 运行时不兼容，先 CPU/小规模运行时预检；不得自动切换模型或 Revision。

### 4.4 公共 Reviewer 工具改造

复用现有 `src/storyforge_gold_quality/hf_literary_review.py`、`hf_blind_stage.py` 和既有 Quality Pipeline，不开发第三套审核器。

新增版本化的 model profile / rubric profile：

- 模型专属模板和采样参数；
- 三项严重维度独立的三态 verdict；
- 严重证据引用及语义蕴含校验；
- 六维评分与严重判定分离；
- 结构化错误码和不可覆盖的 Checkpoint；
- 输入、模型、Prompt、规则、运行时的完整 SHA 绑定。

## 5. 30 条严格配对三模型实验（P4）

### 5.1 配对样本设计

建议首轮 30 条由以下部分组成：

- Gold72 锁定回归子集 20 条；
- R60 severe-flag 子集 10 条。

Gold72 40 条先分为 20 条规则开发集和 20 条锁定回归集；R60 10 条始终作为单独的严重问题校准集。两集合分别出报告，不把它们混成一个统计总体。

在 Owner 私有环境先执行来源指纹去重。如果 Gold72 与 R60 有重复，替换重复项，保证 30 个唯一来源；不公开任何来源 ID。

若某个严重维度在 30 条中缺少足够的 SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_CONTEXT 覆盖，必须明确报告该维度证据不足，并补充定向样本；不能用总体准确率掩盖类别缺失。

### 5.2 严格配对与盲化

- 三个模型审核完全相同的 30 条案例，共 90 份独立输出。
- 每个模型使用独立随机 blind ID、独立输入顺序和独立只读输入卷；Owner crosswalk 留在私有环境。
- 三个模型均不接触旧 A/B/C 判断、Owner 参考标签、Gold72 原裁决或其他模型输出。
- 三个模型使用相同审核任务定义、证据标准、JSON Schema、输入上下文和目标文本；Chat Template 与采样参数按模型各自配置。
- 每条案例均绑定 source SHA、prompt/rubric SHA、model revision、tokenizer SHA、runtime digest、参数和 checkpoint receipt。
- 先完成 CPU Tokenizer/Runtime 预检，再由 Owner 明确授权付费 GPU Job。没有 GPU 授权不提交 Job。

### 5.3 评估指标

**严重问题（三个维度分别统计）**

- 对 Owner 参考标签的 confusion matrix；
- SUPPORTED 的 precision、recall、F1；
- NOT_SUPPORTED 的误报率；
- INSUFFICIENT_CONTEXT 的识别率及比例；
- 安全严重问题漏报单独列为关键风险；
- 逐字引用有效率、引用是否真正蕴含 verdict；
- A/B/Challenger 两两一致率仅作辅助指标，不替代对参考标签的准确性。

**六维文学质量**

- 六维分别统计 MAE、绝对误差分布、±1 分内一致率和系统性偏差；
- 对人物一致性、NPC 主动性、玩家自主权、规则忠实、叙事连贯分别分析；
- 不把严重问题 flag 与六维总分合并成单一平均分。

**统计说明**

30 条是模型筛选与校准 Pilot，不足以证明总体误报率/漏报率已达到生产级。报告必须给出原始分子/分母和不确定性；若类别覆盖不足，继续补充定向案例。

### 5.4 通过门槛（实验前预注册）

- 30/30 三模型输入绑定正确，90/90 Checkpoint 可核验；
- 结构化输出和引用完整性 100%；任何不完整输出均 HOLD；
- 三态不允许被压缩成二分类；INSUFFICIENT_CONTEXT 永远不自动 PASS；
- 安全 SUPPORTED 参考案例不得出现未解释的模型漏报；
- 所有严重误报/漏报都必须逐案有原因分类和规则修正，不得以多数票消除；
- 参考标签覆盖不足的维度不得宣称通过；
- 六维评分必须达到预注册的误差目标；目标值在读取 Owner 参考评分分布后、模型推理前冻结，不得看完模型结果再调整。

**模型选择依据**：参考标签准确性优先，其次是严重误报/漏报风险、六维评分质量、与另一模型的互补性、运行成本和稳定性。GLM-4 与 GLM-Z1 的同家族关系必须纳入多样性评估。

## 6. 审核器回归验收（P5）

将 Gold72 规则开发集、锁定回归集、R60 severe-flag set 固化为三组独立测试：

- 正例：有足够证据支持严重问题；
- 反例：上下文充分但不满足严重问题定义；
- 信息不足：缺失规则、历史、主体或同意上下文；
- 对抗边界：NPC 主动推进剧情 vs Assistant 替玩家决定；角色威胁 vs 玩家代理；可见规则冲突 vs 不可见规则猜测；安全风险 vs 普通亲密/冲突描写。

回归必须验证：

1. 新规则能否识别旧版的已知误报模式；
2. 修正误报时是否引入严重漏报；
3. 引用真实但语义不支持时，能否阻止错误 SUPPORTED；
4. 不足上下文是否稳定返回 INSUFFICIENT_CONTEXT；
5. 旧 Checkpoint、旧 SAFE、旧 manifest 不会被新版本覆盖；
6. 新输出可由现有 Quality Pipeline 消费，且能追溯本次审核输入、输出、rubric 与模型版本。

**P5 完成门槛**：回归测试通过；规则版本冻结；误报和漏报均有证据解释；Owner 审批进入 1,000 条批量审核。

## 7. 1,000 条正式批量审核（P6）

只有 P0-P5 全部通过，才执行：

1. 对冻结的 1,000 条候选按最终选定的双模型配置进行同案例审核；
2. A/B 使用同一来源池，必须 1,000/1,000 可逐案匹配；
3. 先输出完整聚合 SAFE，再由 Owner 在私有环境对分歧、严重问题和 INSUFFICIENT_CONTEXT 做定点复核；
4. 所有 SUPPORTED 严重问题和未解决的 INSUFFICIENT_CONTEXT 不准入；
5. NOT_SUPPORTED 只解除对应严重 flag，不自动授予 Quality PASS；
6. 六维文学质量与故事世界组件/历史输入证据按内容标准验收；不要求审核员提供数据来源合法性、版权/权利、数据使用授权、隐私合规或数据隔离证明，也不得把其缺失写入 missing_context 或作为案例 HOLD 理由；
7. Story 级 train/validation/test 切分仍作为系统侧训练数据防泄漏控制执行，不属于案例审核员需要提供的内容证据；
8. 生成可复用的 Quality-v1 admission receipt 和训练清单。

不得为了达到目标数量降低质量门槛；若 1,000 条中只有少量 PASS，按真实结果接受，不合成、不回填、不篡改 Gold192。

## 8. CPU 与 GPU 执行闸门（P7）

- 先运行静态测试、Prompt/Schema 测试和 CPU Tokenizer 预检；
- 仅使用组织私有 Bucket，输入 RO、输出 RW；Owner crosswalk 不挂载到 HF；
- HF CLI 提交前执行 dry-run，并确认 Job ID、namespace、flavor、volume、timeout、attempts；
- GPU 仅用于已批准的 30 条模型比较和最终 SFT；禁止将一次模型比较自动扩成 1,000 条；
- GPU SFT 必须另行获得明确授权，训练脚本、数据清单、模型 Revision、LoRA 配置、评估集和停止条件均需冻结；
- 任何 Job 失败不自动重试、不自动换 namespace、不自动切模型。

## 9. 本次交付顺序与最小下一步

按下列顺序执行，不并行启动多个未验收阶段：

1. **P0 已 PASS，不重做。**
2. **P1 v2.1 已 PASS，不回退旧 v2.0。**
3. **当前执行 P2-A**：生成 v2.1 Development-20 新包，完成 20 条 Owner 裁决 + 60 条语义复核与私有验证。
4. **随后完成 P2-B**：在 Rubric/prompt 冻结后，为 Locked20 + Severe10 建立独立 held-out Owner 参考标签；不得提前向模型/Prompt 开发者泄露。
5. **再进入 P3**：固定三模型 Revision/profile，完成 CPU Tokenizer/Template/Schema 预检。
6. **最后准备 P4**：冻结 30 条 held-out 配对清单和参考标签；完成预算申请并取得 Owner 明确授权后，才提交 GPU Job。

当前没有授权启动新 GPU Job；本计划本身不修改数据库、不访问 R50 正文、不读取全库正文、不改 RolePlay、不改写旧 A/B/C 结果。

## 10. 官方模型参数参考

- Qwen3-32B 官方模型卡：<https://huggingface.co/Qwen/Qwen3-32B>
- GLM-4-32B-0414 官方模型卡：<https://huggingface.co/zai-org/GLM-4-32B-0414>
- GLM-Z1-32B-0414 官方模型卡：<https://huggingface.co/zai-org/GLM-Z1-32B-0414>



## 2026-11-09 审核范围修订：Rubric v2.1

公开冻结标准见 [R60 Severity Evidence Rubric v2.1](R60_SEVERITY_EVIDENCE_RUBRIC_V2_1_CN.md)。本轮不审核、不要求、不推断数据来源合法性、版权/权利、数据使用授权、隐私合规或数据隔离证明；缺少这些材料不得成为 missing_context、HOLD 或质量拒绝理由。

盲包 evidence locator 仍用于定位包内原文；rule_basis 仍用于标记故事内可见规则、交互约束和安全规则类别。玩家在故事内的明确拒绝/同意/行动边界继续保留为内容语义证据。P0 hash/source binding、私有存储权限、HF Volume 权限和 Story 级训练 split 作为系统侧工程控制保留，不要求案例审核员提供相关证明。

此前按 v2.0 生成的 Development-20 包已 SUPERSEDED，不得用于裁决。Owner review 尚未开始；需按任务书 8.21 在新目录重新生成 v2.1 包后，才可开始 Owner adjudication。


## 11. 当前执行状态校正（2026-11-09）

P0/P1 已完成；当前不是从 P0 开始。上一轮核验快照 HEAD `4190c6fe895080d99901cb4c5eb3f221c6948d6d` 的五组 Actions 全部通过；后续文档提交已推进 HEAD，接手时必须实时复核。P2-A Development-20 v2.1 新包未生成，Owner 20 条裁决与 60 条语义复核未开始。P2-B Locked20 + Severe10 的 held-out Owner reference labels 是 P4 前置，须在 P2-A 和 rubric/prompt 冻结后独立准备；不得将 P2-A 20 条当作 30 条 held-out 评估标签。P3 CPU-only 准备不授权 GPU；P4 GPU 需要单独审批。

## 2026-11-09：正向优秀案例与 R60 严重问题校准分轨

Gold72 Development-20 / Locked Regression-20 是从 A V3 / B2 分歧案例冻结的 Rubric 开发/回归集，不是优秀回复集。三维严重问题 verdict 不等于六维文学质量分数，也不等于训练准入。

新增 `docs/R60_POSITIVE_GOLD_SELECTION_PLAN_CN.md`：从冻结 1,000 条技术候选池独立筛选 Positive Gold，复用现有六维分数门槛与三项严重旗标，先小批、Owner 确认、独立冻结；不设置 PASS 配额，不自动授权全量审核或 SFT。Gold87/Gold108 历史材料不得自动转为当前 Positive Gold。当前仅登记计划，没有启动任何真实审核。

P2-A 最新阻塞：4 条 SUPPORTED Player Agency 的 rule_basis 类型实际为 `player_agency`，Rubric v2.1 要求 `player_agency_boundary`。Normalizer v2 增加 fail-closed 检查，不做隐式类型替换。Owner 需先确认是否仅在派生副本中规范化这 4 个精确类型标签；原始 results 与 60 semantic checks 不得修改。
