# StoryForge R60 — Common2 两条实验性SFT输入：Owner准入裁决书（2026-11-12）

**文件性质：待Owner签批的主线决策草案；当前批准状态全部为 NOT_APPROVED，正式训练准入为0。** 不包含私有故事正文、目标ID、角色名、token IDs、密钥和原始哈希。所有此前真实SAFE与上游验证器保持不变，文档不调用训练。

## 一、决策目标与范围

Owner需要决定能否将已经独立六维质量PASS的**Common2仅两条**来源绑定衍生输入，转为一个受控的**微型正式SFT训练候选数据集**。当前不得直接生成正式`train.jsonl`、将`train_admitted`改为2或自动启动GPU。它仅为后续Real1000更大规模高质量数据准备统一准入模板。

**输入本质：** 11条已持久化来源历史+最终Assistant（12个messages），`SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`；不能说成历史真实发送给生产LLM的完整Prompt。无已认证的历史System、人物卡或动态记忆；因此严禁为了凑训练模板补造这些内容。

## 二、已验证且无需重做的事实

| 证据 | 完成状态 | 不能推出 |
|---|---|---|
| 独立质量审查 | 2条六维质量PASS | 正式Quality-v1入训已批准 |
| 实验输入manifest字节SHA、结构 | `COMMON2_INPUT_AND_CPU2_INDEPENDENT_CHECKS_PASS__ADMISSION_HOLD`，2/2 | 实际生产请求还原 |
| 真实HF CPU2实际`ms-swift` collator | 2/2 PASS，长度2486/3982、监督282/305；native tokenizer 2552/4048 | 两种模板完全等价；或已证实CPU Job与本地JSONL逐字节绑定 |
| R50原始50条保护集 | 50=46+4冻结补集PASS；Common2×原50 story/session/message交集0/0/0 PASS | 世界别名/同源事件语义隔离已审 |
| R45原始Train49/Validation15 | Common2故事ID交集0/0 PASS | 共享角色、语义情节或先前模型暴露不存在 |
| R45×R50五世界机械审计 | 原冻结报告的世界ID/长文本/120字符窗口重合0 PASS | 跨世界隐藏别名、短句改写已审 |
| R50最终正式封存 | `final_heldout_seal_verified=false` | 原50条可以从训练保护集解除 |

## 三、需要Owner独立确认的具体政策

### D1 — 训练输入策略

**建议采用（仍未批准）：** 把`SOURCE_BOUND_DERIVED_CONTEXT_NOT_ACTUAL_SENT`明确作为**真实来源绑定的衍生训练样本**，仅供有充分源完整性证据且质量达标的历史对话使用；不要追求无法恢复的历史生产实际请求逐字节还原。保留11条窗口策略作为首个实验版本、原始最终目标不重写。未来扩大窗口必须另起版本并实际CPU审核。

Owner决策：`PENDING`。若不接受衍生输入策略，则这两条持续`TRAIN_HOLD`，不为达标捏造System/世界卡。

### D2 — 训练侧模板策略

**建议采用（仍未批准）：** 训练端固定`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`、`ms-swift 4.5.3`、`transformers 5.16.1`、`template_type=qwen3_8`、`loss_scale=last_round`、`max_length=16384`、`add_non_thinking_prefix=False`；仅最后Assistant目标受监督；不补造System/世界卡；R18严格label-mask/Collator维持fail-closed。

实测原生tokenizer长度比Swift各多66，属于不同编码策略的已知差异，**不应把“要求原生token总长和Swift一致”设成无依据的训练准入条件**。但同时不能声称两模板逐token等价或66差异根因已定案。建议将Swift视为实际训练实现，native仅为预算参考；必须另核对正式部署侧的实际模板、对话头尾和最后助手生成前缀（见D3）。

Owner决策：`PENDING`。

### D3 — 部署侧输入模板兼容

目前生产/推理端模板参数、实际启用的reasoning/thinking选项及是否注入System尚未在本阶段与训练端核验。Owner可选择：
- `EXACT_SWIFT_DEPLOY`：部署使用与训练相同Qwen/Swift消息格式，提供实际运行配置+本地合成token边界证据；或
- `DIFFERENT_DEPLOY_WITH_COMPATIBILITY_TEST`：保留不同推理端模板，必须提供实际生效配置、特殊token/role边界和多轮消息兼容性检测结果，记录已知差异和性能/语义风险；
- `NOT_ESTABLISHED`（当前）。

仅提议不改变生产代码、部署版本或推理平台。D3仍`NOT_ESTABLISHED`时模板政策整体未批准，不可以只签D2让训练准入通过。

### D4 — 语义世界和保护集策略

已通过精确来源ID、来源哈希和字符串窗口检查，但必须对**Common2这两个源世界**与原R50五世界及实际有关的R45训练/验证世界做基于真实出处的角色别名、共享事件、设定同源、改写与先前开发/评测暴露审查。无充分证据时`INSUFFICIENT_EVIDENCE`，不得写`INDEPENDENT`。世界/别名审核可以单独构造私有证据与判决，仅公开总数。

**允许独立裁决的范围：** 首先仅证明本轮Common2两条不与受保护R50原50及相关既有训练/验证语义世界相交；不需要为此签署W17所有历史争议的完整正式评测封存。不得解除R50原50条保护集或使用其中任一条入训。

Owner决策：`PENDING`。在已知旧W17审查缺时点有效角色卡/规则情况下，没有新证据就明确HOLD，不重复同批文字AI复审。

### D5 — 数据集发布与GPU授权

D1-D4均获得有来源的Owner书面决定后，才能创建**新的SHA固定、版本化、单独发布授权**候选集；发布时另查训练/验证故事级划分、last-round mask、真实运行制品绑定和保护集污染。由Owner另外决定是否启动GPU及费用。**不得把本裁决书当成训练、发布或GPU授权**。

## 四、最终门禁判定（本次草案）

| Gate | 状态 |
|---|---|
| 两条质量/来源绑定实验输入 | 技术PASS，尚未正式准入 |
| CPU tokenizer/Swift collator/label mask | 已有真实证据 PASS |
| R45及R50精确来源UUID/哈希隔离 | PASS |
| D1 接受衍生输入训练策略 | NOT_APPROVED |
| D2 Swift训练侧模板策略 | NOT_APPROVED |
| D3 部署模板兼容与边界 | NOT_ESTABLISHED |
| D4 Common2相关世界语义隔离 | INSUFFICIENT_EVIDENCE |
| D5 正式数据发布和GPU授权 | NOT_APPROVED |
| `quality_v1_admitted` / `train_admitted` | **0 / 0** |

## 五、Owner签批规则及下一步

- D1接受/拒绝衍生输入SFT形式；D2批准/拒绝Swift作为训练侧唯一规范；D3提供当前真实部署模型消息模板/配置并核对边界；D4只对相关两条Common2世界的真实证据裁决；D5最后独立决策。
- 每个批准都必须注明版本、适用范围和证据链，**不接受一句“继续”作为对训练准入或启动GPU的独立授权**。
- 仅这些裁决明确之后再将相同准入机制扩大到冻结Real1000其余高质量候选；已有Wave40源位置保持冻结、不因本书改选或自动重启外部模型审核。

当前文件即为Owner的决策入口，不再重复已经PASS的CPU、R45/R50机械来源检查。
