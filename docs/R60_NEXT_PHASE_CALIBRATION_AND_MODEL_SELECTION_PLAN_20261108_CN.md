# R60 下一阶段：质量标准校准、三模型配对评估与 1000 条批量审核计划

日期：2026-11-08  
目标分支：`r60/gold192-history-v3-adapter`  
关联主线：PR #25 / Issue #26  
当前状态：**计划已整理；尚未修改审核代码、尚未提交新 HF Job、尚未启动 GPU/SFT。**

## 0. 执行目标与当前基线

目标不是再做一次“两个模型都给出 REJECT”的演示，而是建立可重复、可审计的真实历史数据 Quality Pipeline：

1. 先修正严重问题判定标准，明确证据门槛；
2. 保留 Gold72 与 R60 两批历史校准材料，不覆盖原始 A/B/C；
3. 用相同的 30 条真实案例比较 Qwen3、GLM-4、GLM-Z1；
4. 用独立 Owner 证据裁决参照评估误报、漏报和六维评分；
5. 验收通过后，才对冻结的 1,000 条候选执行正式批量审核；
6. Quality-v1 通过、R50 隔离和世界组件证据等门槛满足后，才准备正式 SFT。

当前已知基线：

- Gold72：保留 40 条 A/B 分歧案例，作为独立校准集。
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
- 建议内部划分：20 条规则开发集 + 20 条锁定回归集；具体划分由 Owner 私有 crosswalk 固定，公开仓库只记录计数与哈希。
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

**P0 完成门槛**：Gold72=40、R60=10 来源完整；两集合分轨；去重结果已知；历史文件 SHA 与 Checkpoint 只读校验通过；原始数据没有被改写。

## 2. 三项严重问题证据标准（P1）

三个维度必须分别判断，不得互相替代。每一维输出：

- `SUPPORTED`：有足够、可定位的真实证据，达到该维度严重问题定义。
- `NOT_SUPPORTED`：已经检查了足够且相关的上下文，证据明确不满足严重问题门槛。
- `INSUFFICIENT_CONTEXT`：缺少判断所必需的历史、规则、主体、授权或安全上下文，既不能确认，也不能排除。

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

1. 可见且适用的规则/事实来源（真实历史 System、经验证世界组件、用户明确约束或其他已授权证据）；
2. 目标回复中的精确冲突行为；
3. 两者之间可解释、可复核的矛盾关系。

不得从当前 Story Draft 反向伪造历史 System/Memory；不得臆造不可见世界规则；不得把“没有看到规则”直接当作“规则没有被违反”。

如果所需规则来源不在可审范围，使用 `INSUFFICIENT_CONTEXT`。

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
| 三维均 NOT_SUPPORTED | 仅表示这三项严重问题未被证实；仍须通过六维文学质量、来源、隐私、R50 隔离和世界组件证据门槛 |

**NOT_SUPPORTED 绝不等于 Quality PASS。**

## 3. 独立 Owner 证据裁决参照（P2）

模型比较之前，先建立与模型输出隔离的参考标签。

1. 对 Gold72 开发集和 R60 Pilot10 进行证据级复核。
2. 复核者先只看必要的真实来源上下文和目标，不看 A/B/C 旧评分、严重 flags 和后验风险分层。
3. 按上述三态定义分别裁决三个严重维度，并对六维文学质量另行评分。
4. 每条参考标签必须附证据引用、适用规则、缺失上下文和裁决版本。
5. 原始 A/B/C 判断保留为历史预测，不参与参考标签生成；参考标签冻结后再做对照。
6. 对无法独立裁决的案例保留 INSUFFICIENT_CONTEXT/HOLD，不得为了提高可用样本数强行标注。

参考标签是本项目的 Owner evidence adjudication reference，不应宣传为普适真值或外部认证金标准。

**P2 完成门槛**：30 条模型对照案例均有独立参考标签或明确 HOLD；复核者未接触旧模型判断；引用可验证；标签和规则版本冻结。

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
6. 新输出可由现有 Quality Pipeline 消费，且能追溯全部来源。

**P5 完成门槛**：回归测试通过；规则版本冻结；误报和漏报均有证据解释；Owner 审批进入 1,000 条批量审核。

## 7. 1,000 条正式批量审核（P6）

只有 P0-P5 全部通过，才执行：

1. 对冻结的 1,000 条候选按最终选定的双模型配置进行同案例审核；
2. A/B 使用同一来源池，必须 1,000/1,000 可逐案匹配；
3. 先输出完整聚合 SAFE，再由 Owner 在私有环境对分歧、严重问题和 INSUFFICIENT_CONTEXT 做定点复核；
4. 所有 SUPPORTED 严重问题和未解决的 INSUFFICIENT_CONTEXT 不准入；
5. NOT_SUPPORTED 只解除对应严重 flag，不自动授予 Quality PASS；
6. 六维质量、来源完整性、R50 完整排除、隐私边界、世界组件证据分别验收；
7. 按 Story 维度进行 train/validation/test 隔离，避免同一 Story 跨集合泄漏；
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

1. **先完成 P0**：Owner 私有校准集清点、Gold72/R60 分轨、去重、哈希冻结。
2. **再完成 P1-P2**：把三态证据定义写入公共规则文档和测试；Owner 私有裁决真实案例。
3. **再完成 P3**：修复模型专属配置和 Checkpoint schema；保留旧结果。
4. **最后准备 P4**：冻结 30 条配对清单和参考标签，CPU 预检通过后再申请 GPU 授权。

当前没有授权启动新 GPU Job；本计划本身不修改数据库、不访问 R50 正文、不读取全库正文、不改 RolePlay、不改写旧 A/B/C 结果。

## 10. 官方模型参数参考

- Qwen3-32B 官方模型卡：<https://huggingface.co/Qwen/Qwen3-32B>
- GLM-4-32B-0414 官方模型卡：<https://huggingface.co/zai-org/GLM-4-32B-0414>
- GLM-Z1-32B-0414 官方模型卡：<https://huggingface.co/zai-org/GLM-Z1-32B-0414>

