# R58 GPU 文学评审：严格引用诊断与批量纠错规范

状态：Batch Quote Repair v2 与 checkpoint v3 已完成；HF CPU 共享核心 8/8、R58/Skill 合成测试历史基线 31/31 PASS。Skill v0.1.8 职责收敛后的 PR CI 待核验。A/B v3 Token 预检双 PASS；GPU Pilot 已完成：A/Qwen 2/2 PASS，B/GLM 1 PASS + 1 HOLD；四个 checkpoint 均通过 CPU 身份/引用复核。B case1 的 card_suitable=false。仅一个内容匹配样本可配对比较；质量准入 0，训练未授权。


## 1. 目标与边界

评审输出必须提供可复核的逐字引用。RESPONSE_NONEXACT_QUOTE 表示至少一个引用不是其允许来源中的严格连续子串。该错误是证据格式失败，不是文学评分结论。

- specific_source_quotes：每一段必须完整存在于一条可见历史 user/assistant 消息中；禁止从未批准卡片引用、跨消息拼接或意译。
- specific_target_quotes：每一段必须完整存在于目标回复中。
- 不得通过模糊匹配、去标点、Unicode 归一化、忽略空格或编辑距离放宽标准。
- 未通过严格校验的响应不写 checkpoint；不得将 HOLD 伪装为 PASS。
- 每个样本最多一次批量纠错，可同时修改两个引用列表中的全部无效位置。决策、评分、严重标记、卡片状态、文学评价及不确定性必须与第一次响应完全一致。

## 2. SAFE 诊断数据

QuoteValidationError 只保存结构元数据，不保存失败引用文本：

- field：specific_source_quotes 或 specific_target_quotes
- quote_index：引用数组中的 0-based 索引；数组结构错误时可为 null
- source_candidate_count：允许搜索的来源消息数；目标文本固定为 1
- invalid_quote_count：两个引用列表中全部无效位置的数量
- invalid_quote_fields：存在无效位置的引用字段名白名单
- case_index：13 条盲审批次中的 0-based 索引
- repair_attempted：是否已尝试唯一一次纠错

失败时 SAFE 输出允许包含上述字段和固定 reason code。严禁输出引用内容、原始模型响应、Prompt、Token ID、故事标识、私有文件路径或异常 traceback。

## 3. 受控纠错流程：Batch Quote Repair v2

1. 对第一次 JSON 执行完整字段、评分、严重标记与严格引用校验。
2. 只有 `RESPONSE_NONEXACT_QUOTE` 触发纠错；其他错误直接 HOLD。
3. 程序一次性收集 `specific_source_quotes` 与 `specific_target_quotes` 中的全部无效位置。数组不是 list、长度超过 12 等结构问题不进行自动修复，直接 HOLD。
4. 来源候选仅从 visible_history 中单条 user/assistant 消息提取；目标候选仅从 target_text 提取。候选为允许来源的严格连续子串，长度 8–300 字；去重后每个字段最多 128 个。永不读取 unapproved_card 作为引用来源；候选缺失或超过上限时 HOLD，不截断候选集合。
5. 一次 repair call 同时提交所有待修复的 `field + quote_index` 和按字段分组的候选列表。模型只能输出 `{"repairs":[{"field":"...","quote_index":整数,"candidate_index":整数}]}`，不得输出引用文本或重新评分。
6. JSON Schema 将 repairs 数量固定为无效位置总数；程序进一步验证每个待修复位置恰好出现一次，不得遗漏、重复或添加额外位置，并逐字段验证 candidate_index 在该字段候选范围内。索引必须是真正整数，不接受 bool。
7. 程序从候选表逐字提取原文，一次性替换所有无效位置；PASS 响应缺少引用时只允许将空列表的索引 0 作为插入位置。其他评分、decision、严重标记、卡片状态、文学评价和 uncertainty 完全保留。
8. 纠错 Prompt 重新计算真实 Token ID；最多预留 256 个纠错输出 token，超出 max_model_len 预算即 HOLD。模型使用 temperature=0 和独立 JSON Schema。
9. 程序对构造后的完整响应执行全量 validate_response。任何引用仍不精确、位置不匹配、候选越界或其他规则不满足，均 HOLD；每个样本不进行第二次纠错。
10. 只有全部严格校验通过后才写 checkpoint。首次失败响应和候选索引 JSON 均不保存为 checkpoint。

候选句段按中文句末标点/分号/换行切分；超过 300 字的段落再按逗号边界切分。所有裁剪只去除候选两端空白，不修改内部字符。程序最终仍以原文连续子串校验作为唯一准入标准。

SAFE 汇总只包含 repair attempts/successes、invalid_quote_count、invalid_quote_fields 等白名单元数据，不包含候选文本或模型原始输出。

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
| QUOTE_REPAIR_ITEM_COUNT_INVALID | 待修复位置数量超出批量上限 |
| QUOTE_REPAIR_INDEX_INVALID | 内部待修复位置集合不合法 |
| QUOTE_REPAIR_UNSUPPORTED_QUOTE_SHAPE | 引用列表结构错误或长度超过上限，不尝试自动修复 |
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

### 4.3 Checkpoint v3 必须绑定 Prompt 与纠错协议身份

Checkpoint schema 升级为 `r58_hf_gpu_pilot13_review_checkpoint_private_v3`，除 source/model/revision/slot/index 外，必须包含：

- `review_policy_version`：当前评审策略版本。
- `prompt_sha256`：由 system prompt、user prompt、严重标记定义、response schema、quote-repair version、纠错提示模板、Schema 模板及候选/批量上限计算的 SHA256。

`read_checkpoint` 必须逐项核验两者；缺失或不匹配即 `CHECKPOINT_IDENTITY_MISMATCH`。因此旧 v1/v2 checkpoint 只能留作历史证据，不得被新策略 v2 复用。A/B 必须使用相同 Prompt 版本；Prompt 改变后，对应 A/B pilot 样本均需重新评估，禁止混用新旧 Prompt 结果。

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
- 一次批量纠错成功后只保存严格校验通过的 checkpoint。
- 纠错仍失败时不产生任何 checkpoint。
- 候选仅从允许来源生成；每个候选必须是原文严格连续子串。
- 纠错模型只返回 field/index/candidate_index；程序一次性修复全部无效位置，其他所有评审字段完全保留。
- 覆盖同一字段多个无效引用、跨 source/target 字段批量修复、重复/遗漏/额外索引拒绝、逐字段候选越界、Token 预算、候选边界和不写 checkpoint。
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


### 2026-11-02 A/B Prompt v2 CPU 预检

A/B 的盲审数据包按设计采用不同 blind_id 与独立随机顺序。去除 blind_id 后，A/B 的 13 条完整记录集合完全一致（13/13），26 个 blind_id 全部唯一；不能按数组索引比较。新 A/B Prompt v2 私有 STAGE 保留各自原始顺序和 blind_id，分别在固定 vLLM digest 的 HF CPU Sandbox 中完成 Token 预检，A/Qwen 与 B/GLM 均为 PASS、planned=2、无 GPU 推理。新输出目录为空；v1 checkpoint 不得复用。


### 2026-11-02 Prompt v2 A/B GPU 首轮实测

A/Qwen Job `6ae7f9d30e0338d1bb7dbd26` 运行 105.390 秒后按 SAFE exit 42 停止：case0 的 `specific_source_quotes` 引用纠错尝试后仍未通过精确子串校验，quote_index=1，无 checkpoint。B/GLM Job `6ae7f9d5c78863f9c62ffffb` 运行 123.231 秒后按 SAFE exit 42 停止：case0 checkpoint_00 PASS（severe flags 全 false、checkpoint v2/prompt fingerprint 正确）；case1 的 `specific_source_quotes` 纠错后仍未通过，quote_index=3，无 checkpoint_01。两边未出现 severe flag SAFE；A=0/2、B=1/2，质量准入仍为 0，不能比较模型文学能力。

代码检查发现单次 repair 只替换第一个无效 quote，然后全量重验；同一列表的其他无效 quote 会继续阻断。后续改进应在一次结构化 repair call 中批量选择所有无效 quote 的候选索引，引用文本仍只能由程序从可见来源逐字提供。还应将 quote-repair prompt、schema 与 policy version 纳入 checkpoint prompt fingerprint，避免修复机制变化却复用旧 checkpoint。

本轮 H200 wall time 合计 228.621 秒，按 $5/hour 与 6.6568 汇率估算约 ¥2.11（以最终账单为准）；未超过 ¥11.10 批准上限。



### 2026-11-02 Batch Quote Repair v2 CPU 验证

当前 Runner 已将单一 quote_index 修复扩展为一次批量位置选择：先收集 source/target 两个列表全部无效位置，再让模型返回每个位置对应的候选索引；程序严格验证位置集合与逐字段候选范围，逐字替换后全量重验。PASS 空引用列表可通过索引 0 插入一条合法候选；错误列表结构和超过 12 项不自动修复。

Checkpoint schema 升级为 `r58_hf_gpu_pilot13_review_checkpoint_private_v3`。Prompt SHA256 现在绑定 `r58_quote_repair_batch_v2`、批量纠错提示模板、Schema 模板、候选上限 128 和位置上限 24；旧 v1/v2 checkpoint 必须拒绝复用。

HF CPU synthetic tests：13/13 PASS，包含跨两个引用字段的三位置批量纠错、重复/遗漏位置拒绝、逐字段 candidate index 检查、只改引用字段、最终 checkpoint v3 身份验证。测试只使用虚构数据、FakeTokenizer/FakeEngine，无真实故事、无模型权重、无 GPU。

下一步必须在独立私人 STAGE 中刷新 runner/token_core、保留原 A/B blind_id 与顺序、创建全新空输出目录，并在 HF CPU 完成两槽 Prompt Token 预检。只有两槽都 PASS 才能使用剩余已批准预算进行 A/B 各前两条 GPU 评审。



### 2026-11-02 Batch Quote Repair v2 A/B GPU Pilot 结果

- 新 v3 私人 STAGE：A/B 原始 13 条记录分别保持原始 blind_id 与顺序，A/B 盲审 ID 唯一且互不重叠；去除 blind_id 后两边完整 13 条记录集合相同。新输入仅刷新 runner、token_core 与 CPU 预检适配器；输出目录从空目录开始，旧 v1/v2 输出未覆盖。
- HF CPU Token 预检：A/Qwen 与 B/GLM 均使用 Transformers 4.57.1、Jinja2 3.1.6、各自不可变 revision、32768 context、2400 reserved output。A prompt max 27943 / total 30343；B prompt max 26993 / total 29393；两槽 over_budget_count=0。SAFE 回执再次通过 `--verify-cache-only` 身份核验。CPU 预检未加载模型权重、未推理、未使用 GPU。
- GPU Jobs：A `6ae802c5c78863f9c6300368`（Qwen3-32B）COMPLETED；B `6ae802c8c78863f9c630036a`（GLM-4-32B-0414）COMPLETED。两者使用同一固定 vLLM image digest、H200、Prompt/repair v2、checkpoint v3、每 Job 360 秒 timeout。
- Runner SAFE：A count=2、PASS=2/HOLD=0/REJECT=0、quote_repair_attempts=2、successes=2；B count=2、PASS=1/HOLD=1/REJECT=0、quote_repair_attempts=1、successes=1。三次纠错全部成功，未再出现 RESPONSE_NONEXACT_QUOTE。
- CPU 独立复核：四个 checkpoint 均通过 `read_checkpoint`，source/model/revision/slot/index/schema v3/review_policy_version/prompt_sha256 身份一致，全部引用重新通过严格连续子串校验。四条 severe flags 全部 false，四条 card_conflict 均 false；card_suitable 分别为 A case0=true、A case1=true、B case0=true、B case1=false。B case1 仍为模型主动返回 HOLD，uncertainty 非空；仅凭可见历史无法确认待审内容的角色身份、故事线与场景对应关系。该 HOLD 不是引用校验或严重标记错误，不得改写为 PASS。
- A 的两条六维分数依次为 (Chinese 5/4, Character 5/4, NPC initiative 4/4, Player agency 5/5, Rule fidelity 5/5, Continuity 5/5)。B 两条均为 (4,4,3,4,4,4)。分数仅是模型评审结果，不代表训练准入。
- A/B 完整 13 条输入集合相同，但每槽独立生成 blind_id 且独立随机排序，pilot 前两条只有 1 条内容匹配。按内容哈希对齐：A case0 = B case0（共同配对，均 PASS；A 六维分数 5/5/4/5/5/5，B 为 4/4/3/4/4/4）；A case1 = B case9（本轮只运行 A）；B case1 = A case8（本轮只运行 B，B 决策 HOLD）。只有一个共同配对样本，不能据此断言模型整体优劣；其余未配对结果不能横向比较。
- Job wall-clock elapsed：A 144.708 秒，B 126.437 秒，合计 271.145 秒；按 H200 $5/hour、USD/CNY 6.6568 估算约 ¥2.51（以 HF 账单为准），低于 ¥7.77 批准上限。未使用预算不自动授权扩大样本。
- 最终状态：A 2/2 PASS，B 1/2 PASS、1/2 HOLD；quality_v1_admitted=0，training_authorized=false。剩余 11 条未启动，训练未启动。

## 7. 权威实现

- 运行器：experiments/r58_quality/r58_hf_gpu_literary_reviewer.py
- 合成测试：experiments/r58_quality/test_r58_hf_gpu_literary_reviewer.py
- AI 执行顺序：skills/storyforge-roleplay-sft/SKILL.md

共享 Tokenizer 算法仍唯一位于 src/storyforge_dataset/token_preflight.py；本规范不复制或替代该核心。
