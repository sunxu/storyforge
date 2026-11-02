# R58 GPU 文学评审：严格引用诊断与单次纠错规范

状态：候选索引引用纠错与 SAFE 严重标记诊断均已实测；旧 Prompt B Pilot 为 1/2 checkpoint、整体 HOLD。新评审策略 v2 已明确严重标记阈值并将 Prompt SHA256 纳入 checkpoint v2；HF CPU 合成测试 13/13 PASS，尚未进行 v2 GPU 评审。

## 1. 目标与边界

评审输出必须提供可复核的逐字引用。RESPONSE_NONEXACT_QUOTE 表示至少一个引用不是其允许来源中的严格连续子串。该错误是证据格式失败，不是文学评分结论。

- specific_source_quotes：每一段必须完整存在于一条可见历史 user/assistant 消息中；禁止从未批准卡片引用、跨消息拼接或意译。
- specific_target_quotes：每一段必须完整存在于目标回复中。
- 不得通过模糊匹配、去标点、Unicode 归一化、忽略空格或编辑距离放宽标准。
- 未通过严格校验的响应不写 checkpoint；不得将 HOLD 伪装为 PASS。
- 纠错最多一次，只允许修改两个引用列表。决策、评分、严重标记、卡片状态、文学评价及不确定性必须与第一次响应完全一致。

## 2. SAFE 诊断数据

QuoteValidationError 只保存结构元数据，不保存失败引用文本：

- field：specific_source_quotes 或 specific_target_quotes
- quote_index：引用数组中的 0-based 索引；数组结构错误时可为 null
- source_candidate_count：允许搜索的来源消息数；目标文本固定为 1
- case_index：13 条盲审批次中的 0-based 索引
- repair_attempted：是否已尝试唯一一次纠错

失败时 SAFE 输出允许包含上述字段和固定 reason code。严禁输出引用内容、原始模型响应、Prompt、Token ID、故事标识、私有文件路径或异常 traceback。

## 3. 受控纠错流程：候选索引，不生成引用文本

1. 对第一次 JSON 执行完整字段、评分、严重标记与严格引用校验。
2. 只有 RESPONSE_NONEXACT_QUOTE 触发纠错；其他错误直接 HOLD。
3. 程序根据失败字段构建候选句段：source quotes 仅从 visible_history 中单条 user/assistant 消息提取；target quotes 仅从 target_text 提取。永不读取 unapproved_card 作为引用来源。
4. 候选必须是允许来源的严格连续子串，长度 8–300 字；去重后最多 128 个。候选不存在或超过上限时 HOLD，不截断候选集合。
5. 将原评审 Prompt、首次响应和带索引的候选列表交给同一模型。纠错模型只能输出结构化 JSON {candidate_index: integer}，不得输出引用文本或重新评分。
6. 使用同一模型、temperature=0、独立 JSON Schema 与 64-token 输出上限生成一次；纠错 Prompt 重新计算实际 Token ID，超过 max_model_len 预算即 HOLD。
7. 程序验证索引类型必须为真正的整数（不接受 bool）且在候选范围内，然后从候选列表提取原文，只替换失败字段中对应的 quote_index。若 quote_index 为 null（列表结构错误），仅将该引用列表重置为选中的一条候选。
8. 程序原样保留第一次响应的 decision、scores、severe_flags、卡片状态、文学评价和 uncertainty；纠错模型没有修改这些字段的接口。
9. 对程序构造的结果执行完整 validate_response。若另一个引用仍失败或任何规则不满足，HOLD；不进行第二次纠错。
10. 只有全部严格校验通过后才写 checkpoint。首次失败响应和候选索引 JSON 均不保存为 checkpoint。

候选句段按中文句末标点/分号/换行切分；超过 300 字的段落再按逗号边界切分。所有裁剪只去除候选两端空白，不修改内部字符。程序最终仍以原文连续子串校验作为唯一准入标准。

SAFE 汇总只包含 quote_repair_attempts / quote_repair_successes，不包含候选文本或模型原始输出。

## 4. 固定失败码

| Reason code | 含义 |
|---|---|
| RESPONSE_NONEXACT_QUOTE | 首次或纠错后的引用仍不精确 |
| QUOTE_REPAIR_TOKEN_BUDGET_EXCEEDED | 纠错 Prompt 超出预算 |
| QUOTE_REPAIR_GENERATION_INCOMPLETE | 纠错生成被截断或未正常结束 |
| QUOTE_REPAIR_RESPONSE_INVALID | 纠错输出不是有效 JSON |
| QUOTE_REPAIR_CHANGED_NONQUOTE_FIELDS | 历史兼容码；当前索引修复接口不允许修改非引用字段 |
| QUOTE_REPAIR_SELECTION_INVALID | 候选索引 JSON 无效或索引越界 |
| QUOTE_REPAIR_CANDIDATES_UNAVAILABLE | 允许来源中没有可用候选 |
| QUOTE_REPAIR_CANDIDATE_SET_TOO_LARGE | 候选超过 128 项，直接 HOLD，不截断 |
| RESPONSE_JSON_INVALID | 首次输出不是有效 JSON |

诊断字段只帮助定位，不改变 HOLD/PASS/REJECT 语义。

### 4.1 严重标记与 decision 不一致的 SAFE 诊断

### 4.2 评审策略 v2：严重标记阈值与 NPC 主动性边界

旧 Prompt 只给出三个 severe flag 名称及概括性规则，没有逐项阈值。B case2 的 SAFE 已确认 `decision=HOLD`、`serious_player_agency=true`；可见目标回复未见替玩家决定关键行动、台词或意愿，初步疑似把 NPC 自主结束话题误判为严重越权。该结论是待验证的语义假设，不得回写旧评审结果。

新策略 `r58_literary_review_policy_v2` 明确：

- `serious_player_agency`：只有明确、实质性地替玩家决定关键行动、关键选择、台词、意愿、同意或拒绝时才为 true。NPC 自身行动、心理、提问、改变话题、结束自己的话题、未等待玩家回答或回应玩家已表达内容，不自动构成严重越权。
- `hard_fact_or_ban`：只依据可见历史中清楚陈述的硬事实/禁令；未认证的 `unapproved_card` 不能作为唯一依据。推测、缺失或无法确认时不置严重标记，必要时 HOLD。
- `safety_exclusion`：只有明确满足适用安全排除条件才为 true；单纯提及、讨论、模糊暗示或无法确认不自动触发。
- 任何 severe flag 为 true 时 decision 必须 REJECT；不确定时使用 HOLD 且不置严重标记。不得清除已经明确成立的严重标记来换取 PASS。

### 4.3 Checkpoint v2 必须绑定 Prompt 身份

Checkpoint schema 升级为 `r58_hf_gpu_pilot13_review_checkpoint_private_v2`，除 source/model/revision/slot/index 外，必须包含：

- `review_policy_version`：当前评审策略版本。
- `prompt_sha256`：由 system prompt、user prompt、严重标记定义及 response schema 计算的 SHA256。

`read_checkpoint` 必须逐项核验两者；缺失或不匹配即 `CHECKPOINT_IDENTITY_MISMATCH`。因此旧 v1 checkpoint 只能留作历史证据，不得被新策略 v2 复用。A/B 必须使用相同 Prompt 版本；Prompt 改变后，对应 A/B pilot 样本均需重新评估，禁止混用新旧 Prompt 结果。

`RESPONSE_SEVERE_MUST_REJECT` 的触发条件是至少一个 `severe_flags` 值为 true，而 `decision` 不是 `REJECT`。旧版 SAFE 只记录错误码，不能据此知道是哪一个标记或模型给出了什么 decision；旧 Job 的原始模型响应未持久化，因此不得回推或猜测。

新版 Runner 使用专用 `SevereDecisionMismatch`，SAFE 仅输出以下白名单元数据：

- `case_index`：0-based 样本索引。
- `model_decision`：仅允许 `PASS` / `HOLD` / `REJECT` 枚举值。
- `active_severe_flags`：仅允许 `serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`。
- `active_severe_flag_count`：上述标记数量。

不得输出模型原始 JSON、文学评价、故事正文、引用或私人路径。该诊断不修改 decision，不清除 severe flag，不把 HOLD/PASS 自动升级为 REJECT。下一次有界推理若再次触发该错误，可用这组元数据判断具体是哪类标记造成不一致；之后仍需人工按原始质量标准解释，不能仅凭标记名称认定样本确实有严重缺陷。

## 5. 合成回归测试

experiments/r58_quality/test_r58_hf_gpu_literary_reviewer.py 必须覆盖：

- 来源引用错误和目标引用错误分别返回字段名与 0-based 索引。
- 异常消息中不含失败引用原文。
- 一次纠错成功后只保存严格校验通过的 checkpoint。
- 纠错仍失败时不产生任何 checkpoint。
- 候选仅从允许来源生成；每个候选必须是原文严格连续子串。
- 纠错模型只返回索引；程序只替换失败引用位置，其他所有评审字段完全保留。
- 覆盖 target quote 与 source quote 的端到端成功路径、无效索引失败路径、Token 预算、候选边界和不写 checkpoint。
- checkpoint prompt fingerprint、评审策略版本绑定、身份篡改 fail-closed、不可覆盖、Token 预算及训练准入边界。

测试使用虚构样本和 FakeTokenizer/FakeEngine，不访问真实故事、不加载模型权重、不调用 GPU。

## 6. B Pilot 当前状态

2026-11-02 B 首次修复版 GPU 重试仅运行第 1 条，SAFE 为 R58_HF_GPU_REVIEW_HOLD / RESPONSE_NONEXACT_QUOTE，字段 specific_target_quotes、索引 0；一次自由文本纠错仍未通过。没有生成 checkpoint，第二条未执行。旧输入和输出均保留。

随后将纠错改为候选索引选择：模型只输出 candidate_index，程序从 target_text 或 visible_history 的单条消息中抽取原文。合成测试 12/12 PASS；新 B v2 私有 STAGE 的 CPU-only Token 预检 PASS（planned=2）。

第二次 GPU Job 6ae76fef0e0338d1bb7d87ac 运行约 109 秒：第 1 条通过候选索引纠错，checkpoint_00 写入。后续 CPU-only SAFE 审计用原始输入、模型 revision 和 read_checkpoint 复核身份及逐字引用，确认 checkpoint 有效，decision=PASS、六维评分齐全、来源/目标引用各 1 条。第 2 条未生成 checkpoint；SAFE reason 为 RESPONSE_SEVERE_MUST_REJECT，表示模型输出的严重标记与 decision 不一致。Runner 按 fail-closed 规则 HOLD，没有自动改写 decision 或放宽门禁。

**B Pilot 最终状态：1/2 checkpoint 有效，整体未完成，不能进入剩余 11 条。** Owner 批准的 ¥66.57 预算内，本次所有 H200 Job 累计约 225.8 秒（包括两次启动失败的短时运行），按 $5/h 与 6.6568 汇率估算约 ¥2.09；估算不等于最终账单。到此停止本次 GPU 重试，不再自动提交 Job。

A 已有两个有效 checkpoint，不得覆盖或用新代码重跑。B 的一个 PASS checkpoint 也不代表整个 Pilot PASS；任何 HOLD 均不构成质量准入；本工作不授予训练授权。


### 2026-11-02 严重标记诊断增强

第二条旧回执只包含 `RESPONSE_SEVERE_MUST_REJECT`，没有保留模型 decision 和 active flag 名称；原始输出未持久化，无法从旧 Job 还原。已在 Runner 中新增 `SevereDecisionMismatch`，仅把 case_index、model_decision、active_severe_flags、active_severe_flag_count 写入 SAFE。HF CPU 合成测试 12/12 PASS，覆盖 PASS/HOLD + active flag 的不一致、REJECT + active flag 的合法组合，以及 SAFE 不泄露正文。规则本身未放宽。

第三版诊断 Job `6ae7f327c78863f9c62ffcca` 只处理 case_index=1；SAFE 返回 `model_decision=HOLD`、`active_severe_flags=[serious_player_agency]`。没有写入第二个 checkpoint。该元数据只能定位模型的标记/决策组合，不能证明严重越权事实成立。对可见目标回复与历史的独立文本核查未发现模型替玩家决定台词、意愿或关键行动；当前更像是把 NPC 自主结束话题误判为严重玩家自主权侵犯，但在没有原始模型解释的情况下仍保留为待确认假设。不得据此改写评审结果。

本次诊断 Job 运行约 109 秒。B 组仍为 1/2 checkpoint，整体 HOLD；不启动剩余 11 条，不改写 A/B 已有 checkpoint，不训练。


### 2026-11-02 评审策略 v2 与 checkpoint v2

HF CPU 合成测试现为 13/13 PASS，新增覆盖三个严重标记的显式阈值、NPC 自主行动与玩家自主权的区分，以及 checkpoint 的 `review_policy_version` / `prompt_sha256` 身份绑定。新策略 v2 尚未进行 GPU 评审。此前 A/B 结果和 B 的 1 个有效 checkpoint 均属于旧 Prompt v1，仅保留作历史证据；不得复制到 v2 输出目录或用于 v2 结果统计。

## 7. 权威实现

- 运行器：experiments/r58_quality/r58_hf_gpu_literary_reviewer.py
- 合成测试：experiments/r58_quality/test_r58_hf_gpu_literary_reviewer.py
- AI 执行顺序：skills/storyforge-roleplay-sft/SKILL.md

共享 Tokenizer 算法仍唯一位于 src/storyforge_dataset/token_preflight.py；本规范不复制或替代该核心。
