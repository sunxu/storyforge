# StoryForge R50 — 四模型 + Original Gold 对照与 ROLE12 政策批准记录

**日期：** 2026-11-19  
**仓库：** `sunxu/storyforge`  
**文档分支：** `docs/r50-agent-handoff-20261119`（Draft PR #33，未合并）  
**适用范围：** R50 46-case Protected Held-out 的 PRESEAL 评估设计；本文件不构成正式评估授权。

## 1. Owner 已明确批准的 ROLE12 政策

Owner 于 2026-11-19 明确回复 **“批准”**，批准以下输入解释合同：

> 12 条历史末尾的 User 消息与新追加的 User 消息，是两条独立的连续 User turn。四个模型臂均原样保留两条消息，不合并、不改写、不删除，并将其作为统一输入合同的一部分。

机器可读状态：

```text
ROLE12_POLICY = APPROVED
CONSECUTIVE_USER_SEMANTICS = TWO_INDEPENDENT_USER_TURNS
APPLY_TO = BASE, V0.1, V0.2, V0.3-A
PRESERVE_ORIGINAL_ROLE_SEQUENCE = true
MERGE_USER_MESSAGES = false
REWRITE_USER_MESSAGES = false
DELETE_USER_MESSAGES = false
```

此批准只解决语义政策，不代表四臂实际 runtime parity 已通过，也不批准模型加载、Inference、GPU、Training、Held-out admission 或 Final Seal。

## 2. 比较对象：四个模型臂 + 一个原始回答参照

每个具备合格来源的案例，评估对象为：

| 评估对象 | 固定身份/来源 | 性质 |
|---|---|---|
| Base | `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | 原始基础模型 |
| v0.1 | Adapter SHA256 `621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478`；Base revision 仍须核实 | 第一代微调模型 |
| v0.2 | R46 checkpoint-7 Adapter SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b` | 主要质量对照模型 |
| v0.3-A | R54 checkpoint-16 Adapter SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0` | 最新候选模型；已有开发集结果不支持当前进入正式 R50 |
| Original Gold | 同题、同历史、同 cutoff 的真实历史 Assistant 原始回复；必须有来源证明及字节 SHA256 | 第五份参考回复，不是模型 |

**Original Gold 必须纳入比较，但不能伪造缺失的原始回答。** 它不是标准答案、完美答案或自动正确的 Gold label；应与模型回复接受同样的评分和严重问题审查。

### 2.1 Original Gold 的逐题准入条件

只有同时满足以下条件，某题才能进入五方比较：

1. **同一当前 User 输入：** 字节级完全相同。
2. **同一前置历史：** 所有历史消息的 role、顺序、content 完全相同；不能只凭相同故事或相似语义认定同题。
3. **同一上下文版本：** System、World Card、Long-term Rules 的内容与 cutoff 适用状态可证明一致。
4. **真实来源：** 原始 Assistant 回复能回溯到 Owner 控制的历史来源，具有可核验的 source provenance 和原始字节 SHA256。
5. **时间正确：** 回复确实对应该 User turn，且没有混入 cutoff 之后的事件或信息。
6. **未加工：** 不得改写、拼接、润色、摘要或由模型重新生成后冒充 Original Gold。

逐题结果只允许：
- `ORIGINAL_GOLD_EXACT_MATCH`
- `ORIGINAL_GOLD_UNAVAILABLE`
- `ORIGINAL_GOLD_SOURCE_AMBIGUOUS`

禁止用相似故事中的另一条回复、Gold195、同世界其他轮次、后续编辑版或人工补写替代 Original Gold。

### 2.2 R50 当前数据结构的硬限制

既有 R50 authoring/evidence 说明将 46 条设计为 **prompt-only** 输入：包含当前 User 输入和历史上下文，但没有可直接认定为同题目标的 Assistant Gold 字段。因此，当前不能宣称 46/46 均有 Original Gold。

必须在 Owner 私有环境内按上述条件检查是否存在精确匹配的历史原始回复。不得把故事相同、角色相同或时间相近当作匹配。

- 精确匹配成功的子集：执行五方比较，单独报告 `N_gold / 46`。
- 没有精确匹配的案例：只进入四模型比较；Gold 缺失原因单独计数。
- 五方与四方结果必须使用各自真实分母，不能混算、补齐或把 Gold 缺失题从四模型分母中静默删除。
- 若 Owner 希望 46/46 都有人工参考回复，必须另行批准独立作者在模型输出产生前撰写并冻结 `NEW_HUMAN_REFERENCE`。它不是 Original Gold，必须另列，不得冒名替代。

## 3. 五方评估与四模型评估必须分开报告

每个 Gold 精确匹配案例，由三名独立 Reviewer 对五份匿名回复评分：

- Original Gold
- Base
- v0.1
- v0.2
- v0.3-A

六个维度（1–5 分）：
1. 剧情连续性
2. 角色一致性
3. 指令遵循
4. 文学表现力
5. 互动推进
6. 玩家自主权

每位 Reviewer 还需：
- 对五份回复作匿名排序，允许并列；
- 对 Original Gold 与每个模型分别形成可解释的质量差异记录；
- 记录严重玩家自主权问题、世界事实/时间线错误、明确禁用内容等问题；
- 不因回复来自 Original Gold 而豁免硬规则审查。

在全部 Original Gold 精确匹配案例之外，另对所有符合四臂输入/输出对齐条件的案例执行四模型比较。单独冻结 `v0.3-A vs v0.2` 的 LEFT/RIGHT/TIE 直接配对表，不得从五方或四方排序推导直接配对胜率。

必须分别报告：
- 五方排序与维度评分（仅 Gold exact-match 子集）；
- 四模型排序与维度评分（所有合格模型案例）；
- Original Gold 对照的 Win/Tie/Loss 或维度差值（明确分母）；
- v0.3-A vs v0.2 独立直接配对结果；
- 严重问题的去重案例数与裁决状态；
- Gold coverage：`N_gold / 46` 及不可用/歧义数量。

三位 Reviewer 对同一案例的评分不是三个独立案例。统计需按五个故事世界聚类并披露不确定性；不得把 Reviewer 投票直接当独立样本扩大显著性。

## 4. 盲审与答案 custody

- 每个案例内对所有候选回复独立随机化顺序。
- 隐藏模型臂、Adapter、Original Gold 身份、原始路径和来源标签。
- 不向 Reviewer 显示 Original Gold 标签，不暗示它是正确答案。
- 三名 Reviewer 独立完成并冻结评分后，才允许由独立保管方解盲。
- 私有来源到匿名候选的映射、答案和随机化密钥只留在 Owner 控制目录。
- GitHub 仅接收脱敏 aggregate SAFE receipt、协议版本和 hash 指针。

## 5. 四模型输入和运行时一致性

四个模型臂必须使用同一份冻结输入语义：
- 相同 System / World Card / Long-term Rules 内容及顺序；
- 相同历史消息 role、顺序、content；
- 相同追加 User 输入；
- 12 条连续 User 历史按已批准政策原样保留；
- 相同 Tokenizer revision、Tokenizer 文件和 Chat Template；
- 禁止隐式 truncation；
- 相同 context/output reserve；
- 相同 EOS/stop 与 sampling/generation policy；
- 每个模型实际加载的 Base revision、Adapter SHA256、Runtime 版本及有效参数均有证据。

现有 CPU46 Tokenizer 结果只证明 Draft 长度/结构范围，不证明四臂真实运行时一致。四臂 runtime parity 必须由已有 Owner-local runtime/load/config 记录支持；若无历史运行记录，标记 `SOURCE_UNAVAILABLE`，不能为了生成收据而启动模型。

本次授权范围仅为已有证据的只读检查。不得启动模型加载来补证，不得执行 Tokenizer Job、HF Job、GPU、Inference 或 Training。

## 6. 当前模型选择与质量解释

- Base：必要的零训练基线。
- v0.1：保留历史训练代际对照；Base revision 尚待核实，不得静默假定。
- v0.2：主要质量对照。
- v0.3-A：保留为最新候选，但已有 R55 暴露开发集证据显示其六维均值低于 v0.2，且玩家自主权标记更多；当前仍为正式 R50 NO-GO。该开发集结果不是独立 Held-out 结论。
- Original Gold：真实原始回复参照，不是第五个模型，也不构成自动质量上限。

不能仅凭 v0.3-A 胜过 v0.2 就认定进步；还要报告它与 Original Gold 的差异。反之，Original Gold 也不是无条件的正确答案。任何晋升必须满足事先批准的直接配对、六维质量、严重错误和世界聚类门槛。

## 7. 本文不改变的安全门禁

```text
ROLE12_POLICY = APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
ORIGINAL_GOLD_R50_COVERAGE = NOT_ESTABLISHED
WORLD_SEMANTIC_ISOLATION = HOLD
TIMEPOINT_CARD_RULE_PROVENANCE = PENDING
HIDDEN_ALIAS_WORLD_COMPONENT_CLOSURE = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
MODEL_PROMOTED = false
```

本文件仅记录政策批准和比较设计。它不授权打开 R50、生成四臂答案、开展正式盲评、Final Seal、Held-out admission 或模型 Promotion。
