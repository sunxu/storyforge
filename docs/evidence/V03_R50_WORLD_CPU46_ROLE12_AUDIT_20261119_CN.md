# StoryForge R50 — WORLD / CPU46 / ROLE12 Owner SAFE audit reconciliation

**审计日期：** 2026-11-19  
**仓库：** `sunxu/storyforge`  
**记录类型：** Owner 提供的只读汇总结果之脱敏文档化；不是原始数据重放，也不是准入批准。  
**总体状态：** `R50_WORLD_SEMANTIC_HOLD__CPU46_LENGTHS_VERIFIED_DRAFT_ONLY__ROLE12_POLICY_HOLD__FINAL_SEAL_NOT_PERFORMED`

## 1. 范围与证据边界

本记录整理 Owner 提供的以下四类审计输出：

- Full original-source World Inventory（10,061 bytes）。
- HF CPU46 draft tokenizer receipt。
- CPU46 token-length safe aggregate。
- ROLE12 owner count-only audit。

本次文档化只使用 Owner 在会话中提供的字段和值。没有在本次操作中读取、复制或重新处理原始故事正文、46 条候选内容、逐题 Tokenizer 私有报告、Case 映射或答案。这里记录的是**Owner 提供的只读审计结果**，不能表述为本次执行环境独立重放了完整私有数据。

私有原始报告、逐题数据、Case ID、来源消息 ID、故事正文、答案和逐 Case 映射不得进入本仓库。此文件只保留必要的汇总计数和门禁结论。

## 2. WORLD：完整字节检查完成，语义闭包仍 HOLD

### 2.1 可确认的完整性与规模

| 项目 | Owner 汇总结果 |
|---|---:|
| Old full-source messages | 37,165 |
| R50 full-source messages | 11,627 |
| Source pair rows | 50 |
| Same Story ID pair count | 0 |
| Old14 numbered-chat source count | 14 |
| Old06_15 full bytes and CRC | PASS |
| Old14 full bytes and CRC | PASS |
| Extra archive source-ID conflicts with R50 | 0 |

完整字节与 CRC 检查通过，只证明相应归档字节完整性；不能替代语义世界独立性判断。

### 2.2 配对词法筛查

| 筛查项 | 结果 |
|---|---:|
| Exact long-message flagged pair rows | 3 |
| Sampled 120-character flagged pair rows | 3 |
| Pair rows with same Source ID | 0 |
| Extra archive ranks outside frozen R45 | 4 |
| New source ranks checked | 5 |
| Old source ranks checked | 10 |
| R45 source ranks checked | 9 |
| Transitive known old links | 2 |

三条被标记的配对行均同时出现长消息精确匹配标记和 120 字符采样匹配标记；每行分别报告 1 个长消息精确匹配、5 个采样匹配。这里的“匹配数”是配对行级别的筛查结果，不代表已确认三个独立故事、三个独立事件或三个语义重复世界。

**不得把以下事实混为一谈：**

- `same_story_id_pair_count=0`：本次检查没有发现相同 Story ID 配对。
- `extra_archive_source_id_conflicts_with_r50=0`：本次检查没有发现额外归档 Source ID 与 R50 的冲突。
- 3 条精确长消息 / 120 字符采样标记：仍然是需要解释的词法证据，不能因为 ID 不同就忽略，也不能仅凭词法命中直接判定为同一世界。

本记录不公开配对 Rank、来源 ID、匹配文本或逐条映射。

### 2.3 WORLD 门禁结论

| Gate | 当前状态 | 说明 |
|---|---|---|
| Full source bytes and CRC | **PASS** | 两个归档均通过 |
| Scoped lexical / identity screen | **FLAGS PRESENT** | 3 条配对行需要进一步裁决 |
| Same Story ID pair screen | **0 matches** | 仅限已检查字段 |
| Extra archive Source ID conflict screen | **0 conflicts** | 仅限已检查字段 |
| Timepoint card-field review | **PENDING** | 尚未完成 |
| Hidden alias / world-component closure | **HOLD** | 尚未证明完整语义闭包 |
| Final Held-out seal | **NOT PERFORMED** | 未执行 |

原始库存的 `screen_status` 为 `LEXICAL_OR_IDENTITY_FLAGS_REQUIRE_AI_ADJUDICATION`；`semantic_hidden_alias_and_world_component_closure` 为 `HOLD`。

**裁决：WORLD 继续 HOLD。** 现有结果不足以证明 R50 与旧来源之间完全语义独立，也不足以判定三条词法命中就是同一世界或同一事件。必须基于原始上下文及可核验的别名、角色卡时间点、事件和传递关联证据进行定向 AI 裁决；不能用不同 UUID、零 Source ID 冲突或采样未命中代替语义结论。

## 3. CPU46：46/46 Token 长度通过 Draft 预算，不构成准入

### 3.1 Receipt 状态

CPU46 receipt：

- Status：`R50_HF_CPU46_TOKENIZER_SCRIPT_COMPLETED__DRAFT_NOT_ADMITTED`
- Pre-seal candidate count：46
- Report JSON parseable：true
- `full_46_token_length_and_role_checks_independently_verified=false`
- `official_heldout_admitted=0`
- `final_seal=false`
- `gpu_used=false`
- `model_inference_run=false`
- `training_run=false`
- `semantic_world_isolation=HOLD`

Receipt 中的独立完整检查标志保持 false，不得改写为 true。

### 3.2 Token-length safe aggregate

| 项目 | 结果 |
|---|---:|
| Source count | 46 |
| Recognized 46-row collection count | 1 |
| All 46 token lengths verified | true |
| All 46 template/role semantics verified | false |
| Fitting draft input budget | 46 |
| Exceeding draft input budget | 0 |
| Draft context | 16,384 tokens |
| Reserved output | 1,536 tokens |
| Derived draft input budget | 14,848 tokens |

Token 长度统计：

| 指标 | Tokens |
|---|---:|
| Min | 558 |
| Median | 1,362 |
| Mean (rounded) | 1,963.7 |
| P95 (nearest rank) | 4,265 |
| Max | 8,757 |

因此可以确认：**Owner 提供的 Token aggregate 报告了 46/46 Token 长度验证通过，且 46/46 均不超过 14,848-token Draft 输入预算。**

但这只覆盖 Token 长度，不等于 46 条模板语义、消息角色解释或四臂运行时一致性均通过。

### 3.3 Receipt 与 Token aggregate 的边界

Receipt 的 `full_46_token_length_and_role_checks_independently_verified=false` 与 Token aggregate 的 `all_46_token_lengths_verified=true` 必须同时保留：

- Token aggregate 对 46 条 Token 长度给出 verified=true。
- 同一 aggregate 对全部模板/角色语义给出 verified=false。
- Receipt 没有声明完整的 46 条 Token 长度与角色检查已被独立验证。

这不是将 Receipt 的 false 覆盖为 true 的理由；两个字段描述的证据范围不同。另，Token aggregate 的 trailing-user-history count 缺失、report count 为 null、coverage 为 0。因此，12 条连续 User 的结论应引用 ROLE12 审计，不应声称来自该 Token aggregate。

**裁决：CPU46 Token 长度检查可记为 Draft 技术 PASS；候选仍未准入，Final Seal 仍为 false。** 不因本次结果重复提交 Tokenizer Job。

## 4. ROLE12：结构证据通过，解释政策及四臂运行时一致性未通过

ROLE12 Owner audit 提供的结果：

| 项目 | 结果 |
|---|---:|
| Frozen candidate count | 46 |
| Historical message count | 364 |
| History roles and order preserved | 46/46 |
| Trailing-user histories | 12 |
| Consecutive User appended count | 12 |
| Real tokenizer encoded count for those 12 | 12 |
| Within draft budget | 46/46 |
| Actual four-arm runtime role parity verified | false |
| Trailing-user interpretation policy approved | false |
| Official heldout admitted | 0 |
| Final seal | false |

Status：`R50_ROLE12_SOURCE_TO_DRAFT_TEMPLATE_AND_TOKEN_REPORT_STRUCTURE_PASS__NOT_SEMANTIC_APPROVAL`。

可以确认的范围是：Owner 审计报告了 46 条历史角色与顺序保留，并报告 12 条连续 User 情况均有真实 Tokenizer 编码记录。不能据此推导：

1. 连续 User → User 在四臂模型中具有一致、已批准的交互语义；
2. Base / v0.1 / v0.2 / v0.3-A 的实际运行时模板与角色解释完全一致；
3. 46 条候选已通过语义独立性审查或获得正式 Held-out 准入。

**裁决：ROLE12 结构审计结果保留；连续 User 解释政策和四臂运行时角色一致性继续 HOLD。** 不得通过合并、改写或丢弃历史 User 消息来人为消除差异。

## 5. 汇总门禁

| 维度 | 结论 | 是否允许正式准入 |
|---|---|---|
| WORLD 原始归档字节与 CRC | PASS | 否，语义闭包仍 HOLD |
| WORLD 词法命中裁决 | PENDING / HOLD | 否 |
| WORLD 隐藏别名及组件闭包 | HOLD | 否 |
| CPU46 Token 长度 46/46 | Draft PASS | 否 |
| CPU46 模板/角色语义 46/46 | 未验证 | 否 |
| ROLE12 历史角色/顺序结构 | 46/46 reported PASS | 否 |
| ROLE12 连续 User 政策批准 | NOT APPROVED | 否 |
| 四臂运行时角色一致性 | NOT VERIFIED | 否 |
| Official Held-out admitted | 0 | 否 |
| Final seal | NOT PERFORMED | 否 |
| GPU / inference / training | 未执行 | 否 |

当前总裁决：

```text
WORLD_SEMANTIC_ISOLATION = HOLD
CPU46_TOKEN_LENGTHS = VERIFIED_DRAFT_ONLY
CPU46_TEMPLATE_ROLE_SEMANTICS = NOT_VERIFIED
ROLE12_SOURCE_TO_DRAFT_STRUCTURE = PASS_AS_REPORTED
ROLE12_USER_TURN_POLICY = NOT_APPROVED
FOUR_ARM_RUNTIME_ROLE_PARITY = NOT_VERIFIED
OFFICIAL_HELDOUT_ADMITTED = 0
FINAL_SEAL = NOT_PERFORMED
GPU_USED = false
MODEL_INFERENCE_RUN = false
TRAINING_RUN = false
```

## 6. 下一步工作顺序

1. **定向处理 3 条词法命中配对行。** 使用原始上下文和可引用来源证据判断是模板/通用消息重合、共享历史事件、别名关联还是同一世界组件；保留不确定项为 HOLD。配对映射和文本留在 Owner 私有环境。
2. **完成 timepoint card-field review。** 只使用对应案例 cutoff 时点可证明有效的卡片字段；不得将导出时的后续事实回填到历史上下文。
3. **完成 hidden alias / world-component / transitive closure。** 对已知旧链接、额外归档 Rank 和跨世界关联作闭包检查；无法证明的组件继续 HOLD。
4. **单独处理 ROLE12 政策。** 由 Owner 明确批准或否决连续 User 消息的解释合同，并对四臂实际运行时构造进行独立一致性核验。
5. **保持不重复的 Tokenizer 工作。** 目前 46/46 长度已报告验证且均在 Draft 预算内；没有新的长度证据缺口要求再跑相同 CPU Tokenizer Job。
6. **只有所有准入前置证据完成并经 Owner 单独批准后，才讨论 Final Seal 和后续推理。** 本记录本身不授权任何下一阶段执行。

## 7. 安全与非授权边界

本次文档化不修改原始 R50 候选、原始历史、R45 冻结输入或任何答案/映射；不启动新 HF Job、GPU、模型推理或训练；不执行 Held-out 准入、Final Seal 或模型晋升。原有 CPU Tokenizer 结果仅按上述 Draft 范围记录。

本文件不得被引用为“R50 已完成语义隔离”“46 条已正式准入”“四臂角色一致性通过”或“Final Held-out 已封存”的证据。

**最终状态：** `R50_WORLD_SEMANTIC_HOLD__CPU46_LENGTHS_VERIFIED_DRAFT_ONLY__ROLE12_POLICY_HOLD__FINAL_SEAL_NOT_PERFORMED`
