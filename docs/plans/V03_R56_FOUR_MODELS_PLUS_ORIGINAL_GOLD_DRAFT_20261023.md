# StoryForge R55/R56 — 四模型 + 原始 Gold 五方盲评合同草案 v1

**状态：DRAFT / 未批准 / 不执行 R50 / 不提交 GPU。** 此草案是对 `docs/plans/V03_R50_FOUR_ARM_INPUT_CONTRACT_DRAFT_20261016.md` 的扩展，不覆盖旧合同、历史 R48/R55 盲审结果或 SHA。Owner 要求增加**原始 Gold 对比**。原始 Gold 属于**第五份候选回复，不是第五个生成模型，也不是无条件正确答案**。R55 现有 GO/NO-GO：`docs/evidence/V03_R55_CHECKPOINT16_CANDIDATE_GO_NO_GO_20261023.md`，R54 checkpoint-16 当前对消耗正式 R50 测试 **NO-GO**。

## 1. 五方候选与身份保管

| 匿名候选来源 | 模型/来源冻结身份 | 参与方式 |
|---|---|---|
| Base | `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | 模型生成 |
| v0.1 | 旧 checkpoint-9 adapter weights SHA256 `621d7328056758607c9d7797282ae4d5803cdb1727dab6b40a321ee959dd2478` | 模型生成 |
| v0.2 | R46 checkpoint-7 adapter weights SHA256 `bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b` | 模型生成，主质量基线 |
| v0.3-A | R54 checkpoint-16 adapter weights SHA256 `121ec8f70e66089c7c891a7052c6085de93824776aaa9a25295f612b269b60c0` | 模型生成，候选；现 NO-GO 正式 R50 |
| Original Gold | **原始同题 Assistant 回复**、来源与字节 SHA256、同一提示和截止时间核验 | 人/历史参考；不训练、不假定最优 |

对每题由独立保管方生成带盐的随机化映射，五方匿名位置逐题随机，角色与回复来源不出现在评审包。Gold 不得被标注为“标准答案”。独立 reviewer 不得接触模型标签、原始文件路径、之前 R48/R55 票数和模型晋升假说。五份回复接受完全相同的六维评分和硬性违规判定。任何模型的生成参数不同都须披露，不得据此声称受控一因素比较。

## 2. 两条不同的评估路线（切勿混淆）

### A. R55 旧 20 题，真正可进行 Gold 五方开发比较

R48 旧 20 题的 Gold 是 v0.1 Test 同题来源中原始的 Assistant 回复，在原来的四方评估已经按题源核对。R55 的 R46/R54 使用 **相同已曝光的 20 题**。因此可以仅在经过逐题 prompt/角色消息哈希、原始 Gold 目标来源、历史模型输出及运行参数归一验证后，组装 `Base / v0.1 / v0.2 / v0.3-A / Original Gold` 五方匿名任务。这是**新的 R55 开发集评分任务**，不是把历史 R48 和 R55 不同轮次打分直接相加。

- 使用已经冻结的旧 20 题与现存回复，**没有 GPU 推理或重训**。
- 任一题缺少准确匹配的 Gold 或某臂实际回复，整题不得进入五方分母；可单独记录 `UNMATCHED_DEV_CASE`，禁止补造。
- 若 R48 与 R55 的旧题提示确实不完全同字节或上下文角色不同，停止宣称“同题五方”，该题回退为不同批次开发证据。
- 在任何新的 Gold 五方评分之前冻结题目哈希、五份实际回复哈希、同题判定结果、分组随机种子和 reviewer 指南，保持三位独立审稿人的盲态；不读取 R50。
- 只得用于 R55 改进诊断、候选 GO/NO-GO 复评，不是新的正式 Held-out。

### B. R56 R50 46 题，Gold 原始对照尚不能声称存在

原 R50 在 `V03_R50_INDEPENDENT_TEST_AUTHORING_GUIDE_20261015.md` 被明确设计为 **prompt-only**、独立撰写的“新当前 User 消息”，原始文件只提供 `case_id/world_id/world_card/long_term_rules/history/user_input`（可能还有 `focus_tags`），**不提供同题 Gold Assistant 目标回复**。所以 **不可**从 Gold195 或历史聊天随意取一条原始 Assistant 作为这 46 个新问题的“原始 Gold”。对齐不了同一新 User 输入、同一历史上下文、同一规则截止时间，哪怕故事相同也不算真实 Gold。

处理规则：

1. 在保护区内只读取出处元数据，逐题判断是否存在 **exact same user_input + same preceding history + matching world/rules as-of cutoff + authenticated original Assistant reply**；有且原件哈希与截止时间可证时，标记 `ORIGINAL_GOLD_EXACT_MATCH`。不能仅用相似文本或叙事顺序替代。
2. 未证实时标记 `ORIGINAL_GOLD_UNAVAILABLE`；**保持原始四模型评估**，Gold 对照只在已匹配子集单独报告 N / 46，禁止把四臂成绩与五臂成绩同一分母混算。
3. 如 Owner 希望全部 R50 也有一个参考回复，必须在盲评和模型输出之前由独立作者**新写参考答案**、审查历史事实、冻结字节与 provenance，并明确将其命名为 `NEW_HUMAN_REFERENCE`，**不得**称作“原始 Gold”；若这个新参考的编写者已见到待比较模型输出，不能进入预注册的公正 Gold 栏目。
4. 无法保证 original-Gold 逐题同题对齐，不得因此修改现有 R50 46 题、移动训练数据、泄露受保护提问给模型开发方或假装有 46 条源 Gold。

## 3. R56 四模型一致输入合同（仍待 Owner 批准）

- 冻结 R50 46 条，原始候选 SHA256 `109642a6c0e27895ae83274bec79ec9f53d922e407ca435431acf3f31a31e1f2`; System `5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83`;五个故事组 `9/10/9/8/10`，364 条原始历史不改写。
- System = 原始 R45 generic System + 对应 R50 world card + long-term rules 原样 bracket-delimited；系统正文 hash 固定；后面历史按角色和顺序原样保留；追加一条新 User；**12 条连续 User 不合并**。此行为仍需显式 Owner 批准为正式推理语义规则。
- 公共 Qwen Tokenizer revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，tokenizer.json SHA256 `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3`，tokenizer_config `b11349aafa7cdc6a320767cf7ceb29ed82f7eda5d65e8e0819e76f0ce947bf27`，chat_template `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`. PIN with `transformers==5.16.1`, `enable_thinking=False`.
- Preliminary draft `max_context=16384`, `reserved_output=1536`, hence input cap `14848`, actual Owner-verified 46/46 within draft cap, max 8757. **No input truncation**. The previously checked length is not a guarantee of four runtime arms having identical effective context, and 12 User→User sequences must be supported in each serving runtime.
- Generation proposal: `do_sample=False`, explicit seed 42, `max_new_tokens=1536`, explicit EOS/stop, no hidden prompt differences, all four models share identical prompt bytes and template bytes and log generated response SHA and effective runtime args. If `temperature=0` is rejected/ignored by inference framework, lock the actual compatible deterministic policy **before** inference, not after outcome.
- All four model/adapter checkpoint paths, file digests, runtime load receipts and exactly equal per-case message canonical SHA and input-ID digests must be verified before any protected inference. No approval implied by this draft.

## 4. Blind-review collection, aggregation, decisions

For every fully aligned **five-way** development item, each Reviewer:

1. Scores **all five responses** independently on six dimensions (1–5): 剧情连续性、角色一致性、指令遵循、文学表现力、互动推进、玩家自主权.
2. Records hard events: player-agency serious error, source/card/timeline mismatch, explicit prohibited phrase or forbidden canonical fact; each with exact evidence quotation stored privately and adjudicated **by case/event**, not blindly counted as 3 independent errors.
3. Submits a ranked five-way preference with explicit ties; and additionally records best-of-**four model replies** independently, so Gold's presence cannot silently change the model-only denominator.
4. On a **separate** independently randomized blinded worksheet, directly compares `v0.3-A` vs `v0.2` LEFT/RIGHT/TIE; never calculate pairwise win rate from five-way/four-way rank alone.
5. Grades Original Gold without special exemption. Never assume an originally written passage guarantees player agency or other hard rules. Reports Gold-relative gap by each dimension and adjudicated critical violations.

Publish *separate* tables for: (a) five-way preferences on Gold-matched cohort, (b) four-model ranking on all otherwise eligible model-only cases, (c) direct v0.3 vs v0.2 independently adjudicated cases, (d) dimensions and severe-case counts, (e) Gold-coverage N/total. No unsupported pooling of R48 and R55 historical rounds.

Report uncertainty clustered by **world** (five R50 worlds if final test ever authorized), including shared-event sensitivity. Three reviewers × case are correlated observations; a 95% five-cluster uncertainty interval may be inconclusive; no fabricated significance. Gold is a reference, **not** fifth evaluated AI model, hard ceiling or guaranteed majority winner.

## 5. Promotion proposal and stop conditions (unapproved)

Candidate quality-GO against v0.2 would provisionally require: case-level non-tie v0.3 wins >50% in a **truly independent direct pairwise** with world-clustered 95% evidence supporting a real advantage; overall six-axis mean > v0.2; no literary/interactive-progress regression; serious player agency **adjudicated unique-case rate <=5% and <=v0.2**; zero confirmed forbidden-line quotes. Additional Gold-relative tables are descriptive, not a new way to overrule these gates. If world count or evidence fails, `INCONCLUSIVE_NO_PROMOTION` or `FAIL_NO_PROMOTION`. Contract/gates require Owner approval **before** the scarce protected test is opened; Owner's story independence attestation does not automatically waive source correctness or prior exposure checks.

**Current status:** `R55_DEV_GOLD5_PROTOCOL_DRAFT__R56_FOUR_MODEL_PLUS_ORIGINAL_GOLD_WHERE_EXACT_AVAILABLE__OWNER_SIGNOFF_PENDING__R54_R50_NO_GO_NOW__NO_FINAL_SEAL`.
