# StoryForge R60 Common2 — 语义隔离与模板合同剩余门禁（2026-11-12）

> **性质：证据驱动、未签署的实施任务书；非训练准入批准。** 只记录公开可复现规则与SAFE结果，不携带私有故事文本、ID、模型评分或原始来源映射。独立工作分支 `r60/common2-cpu2-owner`；不影响其他Agent的仓库或HF作业。

## 1. 已关闭的机械证据（不得重复）

| 门禁 | 已获Owner真实SAFE | 结果 |
|---|---|---|
| 原始R50 50题与46+4分割 | `R50_ORIGINAL50_46_PLUS4_EXACT_COHORT_PASS__SEAL_R45_TRAIN_HOLD` | 冻结哈希、ID集合精确补集、46条parent行号与来源映射PASS |
| Common2两条 vs R50原始50题 | `R50_COMMON2_EXACT_KEYS_DISJOINT__SEMANTIC_R45_SEAL_HOLD` | Story/Session/Message ID三层交集 0/0/0 |
| 原R45 Train49/Val15 vs R50五世界 | `R45_EXISTING_EXACT_SOURCE_SCREEN_PASS__SEMANTIC_SEAL_HOLD` | 原历史报告SHA及49/15、世界ID/长消息/120字符窗口三项机械零碰撞PASS |
| Common2 Tokenizer/Swift Collator | `CPU2_SAFE_RECEIPT_VERIFIED__R50_TRAIN_HOLD` | 真实HF CPU：两例Tokenizer=2552/4048，Swift=2486/3982，监督Token=282/305 |

以上证据不改变`r50_complete_exclusion_verified=false`、`train_admitted=0`。原R50全部50题继续作为保守训练排除保护集，不因正式seal未执行就允许训练复用。

## 2. 语义隔离：区分三个不同的问题

### G-S1 Common2训练两条 vs R50原始50条

已排除精确UUID重叠，尚未排除**同一角色的别名、共享情节事件、相同设定或改写**。执行步骤：

1. 在Owner私有机器建立 **两条Common2故事 × R50五个完整源世界** 的语义审查矩阵（如已有来源世界连通分量证据，按已审原件逐项复用），至少覆盖人物、别名、事件、世界设定、时间版本、同源文本意译及向模型暴露历史。
2. 各项裁决只允许 `SAME_WORLD`、`INDEPENDENT`、`INSUFFICIENT_EVIDENCE`；无真实出处时必须第三类，不得仅根据名称/UUID差异设为独立。每条有Owner私有证据引用，来源内容只存本机。
3. 审核输出公开只能是已审pair数、三种裁决计数、缺证据计数、受保护集是否全覆盖，**不得出现故事/角色别名、case ID、材料正文**。
4. 只要任一 `SAME_WORLD` 或 `INSUFFICIENT_EVIDENCE`，维持Common2正式训练隔离HOLD。若全覆盖独立，也不能自动把R45/R50其它门禁或训练准入置真。

### G-S2 R45 Train49/Val15 vs R50的完整世界图

R45历史固定脚本 `scripts/v03_r50_private_r45_isolation.py` (审计commit `92828ac0e47c8f7f7307851b8e171f564fd065ed`) 已证明的是机械零碰撞，脚本自己标 `short_or_paraphrased_context_review=PENDING`、`incomplete_or_hidden_world_aliases=PENDING`。不再重跑120字符全偏移。

历史已知的具体阻塞（见 `docs/evidence/V03_R50_ROLE12_OWNER_INTAKE_SAFE_20261023.md`）：旧世界02/04/10与R50 W17三对均 `INSUFFICIENT_EVIDENCE`；后续七次完整消息核验仍 `INSUFFICIENT_CONTEXT`，审过344份消息条目、75个引用。W17在测试截止时生效的运行角色卡/规则尚未完整认证。**重复同样AI审核、只增加票数不是新证据。**

下一项真正的新证据必须是**截止时间内真实生效**的历史快照/规则版本/角色别名和事件的原始出处，以及已有R45真实来源/角色图。受控审核人员在Owner本地将其对齐到具体截点，更新私有证据引用及三值裁决；缺证据继续HOLD。不要公开上传世界原文到GitHub。

### G-S3 旧评测/开发暴露与正式 R50 封存

早期评测素材与Common2的语义/事件接近或回答复用属于独立风险，不能从 R45 vs R50零碰撞推出不存在。建立已暴露评测来源登记并单独审核。历史权威 `docs/evidence/V03_R50_46_PRESEAL_GATE_DELTA_COUNT_ONLY_20261022.json` 明确 `final_seal=NOT_PERFORMED`、正式测试准入0。这是评测使用合同，**不同于训练时保守排除原50题**。不应为了让Common2进入训练而自动签R50最终测试封存。

## 3. Qwen原生与ms-swift模板：固定合同前的最小差异定位

已通过的CPU2**只说明两种路径均可正常编排两例输入及有效label mask**。原生Tokenizer=2552/4048，Swift Collator=2486/3982，两例各差66。长度差不能证明语义/标签错位，也不能凭`66`推导是哪条token/隐藏模板。真实HF CPU Label Mask=282/305，属于可复现数据。

仅在已有同一HF CPU Job/已固定审计日志**已经记录**以下信息时直接复用；缺少其中某项，不重新提交Job：
- 相同的2条输入payload SHA、Qwen tokenizer revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`、transformers `5.16.1`、ms-swift `4.5.3`、tokenizer/chat-template SHA。
- 两个token序列的长度、首尾共同前后缀长度、差异段的**token类型/角色边界类别计数**、最后assistant监督token数及EOS标志，而不是完整token IDs或私有正文。
- 原生是否将全部11条上下文和最终assistant都视为输入，而Swift collator是否额外丢弃template前缀、增减特殊token/某种loss mask逻辑；只根据实际审计路径确认，不凭“差66”猜测。
- 最大上下文/裁剪策略、最后assistant `loss=true` 与推理端生成开头一致性。

可提交的决策草案：**用真正要训练的Swift编码+Collator和label mask作为训练侧的唯一规范实现；原生Tokenizer审计仅作为独立输入预算诊断，而不是要求未经证明的逐token完全相同。** 这只是工程建议，Owner必须先批准训练/部署模板合同，不能为了PASS强改Token序列、改变冻结输入或修改现有HF回执。需要真实推理端模板之后，再检查相同role消息的边界/生成标记是否一致。

## 4. 下一动作与停机条件

- **先语义新证据再开展新的审核**；无截止时有效快照及可信世界/别名来源时明确 `SEMANTIC_SOURCE_EVIDENCE_HOLD`，不造“独立世界”证书。
- 只读复用现有CPU2安全回执、审计日志和模板代码，整理**已证实差异 vs 待验假说**。无需新的HF Job。
- 只有上述语义闭环、固定模板/推理合同、R50评测治理或明确的训练排除政策、Owner数据准入许可全满足，才能另起明确的正式准入决策流程；目前`train_admitted=0`，不启动GPU/SFT。
