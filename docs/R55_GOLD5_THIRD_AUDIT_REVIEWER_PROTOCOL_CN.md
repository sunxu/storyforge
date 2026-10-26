# StoryForge R55 — 第三位独立匿名证据仲裁者任务书

你只收到：`R55_GOLD5_THIRD_AUDIT_BLIND_ITEMS_PRIVATE.json` 和 `R55_GOLD5_THIRD_AUDIT_DECISIONS_BLANK_PRIVATE.json`。任务是**独立阅读每一条匿名候选回复及其可见上下文**，判断是否存在以下两类明确问题：

1. `agency`：是否有**严重**擅自替玩家角色执行关键行动、决定核心选择、强加玩家意图等。NPC 自己的行动或心理不自动算严重侵犯；与玩家角色有关的设定和已给历史必须结合可见原文判断。
2. `hard_fact_or_ban`：是否**明确违反**本条可见故事规则、被禁止的原话／事实、明确时间线／人物硬设定等。不能仅凭个人偏好或未提供的故事常识判断。

**盲审纪律**：不能猜测候选来自哪个模型，也不能请求或访问前两位仲裁者结论、历史分数、原始匿名编号、私有映射或为什么被选中。若有既往接触或泄漏，应通知 Owner，不要假称独立。

对 `items` 中**每一个候选**，`agency` 与 `hard_fact_or_ban` **分别填写一次**，仅使用：`CONFIRMED` / `REJECTED` / `HOLD_INSUFFICIENT_EVIDENCE`。

- `CONFIRMED`：明确解释违反了哪条可见规则，给出候选回复中**逐字存在**的 `candidate_quote`，及可见故事背景、历史对话或当前用户输入中**逐字存在**的 `context_quote`；不要编造或改写引用。
- `REJECTED`：独立说明为什么可见依据不能支持该严重违规；不要因没有强制反证而草率否定。
- `HOLD_INSUFFICIENT_EVIDENCE`：说明欠缺何种可见信息或为什么存在两种合理解释；不可补造剧情、角色年龄、同意或隐含世界规则。

保留所有 `candidate_token`、模板字段、原始字符串、两类名称及完整对象数量，不得添加模型身份或修改候选原文。填写的完整 JSON 命名：

`R55_GOLD5_THIRD_AUDIT_DECISIONS_COMPLETED_PRIVATE.json`

最后一次检查：`items` 数量与原始包一致；每项两个类别均有允许的判定和具体理由；所有 `CONFIRMED` 都有两种逐字引用，且来源字段正确。你不是模型训练批准者；所有结论均属历史开发题证据复核，不批准训练、晋升或受保护测试。
