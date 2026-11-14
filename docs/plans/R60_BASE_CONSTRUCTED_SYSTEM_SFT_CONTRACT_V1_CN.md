# StoryForge R60：构造型System与Base SFT输入合同 V1（提案，尚未准入）

状态：`CONTRACT_DESIGNED__SOURCE_BINDING_AND_CPU_VALIDATION_HOLD`。依据 `docs/plans/R60_BASE_FIRST_TRAIN_READINESS_20261115_CN.md`。本文件固定设计语义，**不是**已经核实的336条正式输入，不授权GPU或模型调用。

## 唯一实验目标与基座

- Base：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，从冻结Base新建LoRA，不继承R46/R54权重或optimizer。
- 原始三条持久历史输入：`user → assistant → user`，训练目标为第四条`assistant`。只对最终Assistant计算loss；前面的历史Assistant属于上下文，不能误标成训练目标。
- R60冻结候选336条原数据仍为HOLD；已经通过的`THREE_PERSISTED_MESSAGES_NO_SYSTEM`真实Qwen Tokenizer+ms-swift Collator和R18 mask检查只是**旧技术对照**，并非本V1合同验证。

## 输入字段边界

| 块 | 形式 | 允许内容 | 禁止内容 |
|---|---|---|---|
| `system.generic_invariant` | 固定逐字模版；版本化，不随Story变化 | 文学中文、NPC合理主动、尊重玩家行动主体、遵守显式设定/安全/事实约束、避免把玩家意愿写死 | 不明来源的人名、独特规则、剧情、角色身份；历史System伪造 |
| `system.source_bound_world` | 可选，明确源字段 `v2_data.world` 的具体revision绑定 | 只提取目标之前已存在且与该Story相符的世界事实；保留字段及原文证据 | 以“当前最新World”充当目标历史设定、把别Story的共享模板扩写为具体世界、补写不存在的故事事实 |
| `system.source_bound_roles` | 可选，绑定 `v2_data.character` 或 `v2_data.characters` 的正确cardType分支 | 目标时刻有效的角色设定、与本Story关联的人物关系 | 依赖`public.user_stories.characters`旧空数组判断V2设定；错用另一cardType分支；幻想性角色设定 |
| `history` | 冻结真实历史消息 | 目标之前的 `user,assistant,user`，原顺序与字节内容 | 目标之后的下一轮、未来分支、目标回复变体 |
| `assistant_target` | 最后一条Assistant | 冻结完整目标原文（与冻结哈希相符） | 在输入System或历史部分重复答案；修改后只剩摘录 |

标记：`TRAINING_CONSTRUCTED_NOT_HISTORICAL` 必须出现在**内部数据来源元信息**中并进入完整Run Manifest；不在公开SAFE中输出Story具体内容。构造型System绝不声称是在线请求的历史原文；历史exact actual-sent不是本Base新实验必备门禁，但**源绑定的事实与版本时序**仍必须证实。

## 固定通用System模版（设计草案）

```text
你正在创作中文互动小说。保持文笔自然、角色性格与既定事实一致；让NPC在合理动机下主动行动，推动故事发生变化，但不要替玩家决定内心、台词、行动或不可撤销的选择。遵守当前故事已提供的规则、时间线和明确禁令；未知事实保持未知，不擅自补造设定。根据此前对话继续情节，回应用户当前输入，不复述指令或输出审核说明。
```

该模版不含特定Story事实，可做纯合成CPU测试；要宣称“产品世界设定兼容”的SFT，必须在本合同`source_bound_world`和`source_bound_roles`来源绑定通过后另行测试。不得直接把旧无System 336技术PASS升级为本合同PASS。

## 每条训练实例必须通过的门禁

1. `source.story_id/session_id/target_message_id`、原目标SHA及身份与原冻结清单一致。
2. `history`消息时间与目标关系可证明；无目标之后内容、无未来剧情，且标签只监督目标Assistant。
3. 若有World或角色卡，必须记录表、主键或revision ID、`cardType`分支、字段路径、有效时间依据；**无法证明历史有效的卡片只允许被丢弃，不允许塞入System**。丢弃后需评估是否影响真实产品上下文等价性。
4. 目标Story不在R50/其他本次保护评测来源或已证实共享组件中；Train与Val的任何已证实共享组件不可交叉；未知组件保留HOLD。
5. 独立Reviewer真实执行证据满足冻结六维质量门槛、严重标记规则，不能只有两个不同模型ID。
6. 通过固定revision真实Tokenizer、ms-swift actual collator、R18最后Assistant-only严格mask；每例Token上限及截断策略必须冻结，截断不可丢硬规则或偷偷遗漏目标标签。

## 下一执行：C工作线（无需等待A/B）

- 用**合成**System+历史+Assistant目标的少量虚拟样本完成结构、source字段缺失时fail-closed、tokenizer/collator/mask检验；仅在已具备真实并合法绑定的私有样本时做隔离CPU抽查，不把内容写入GitHub/CI。
- 做两种显式比较：`MINIMAL_NO_CARD`（有意保留无卡历史上下文，只能称技术/有限产品比较）与`SOURCE_BOUND_CARD`（有版本绑定才允许）；**不能合并当作同一训练合同或宣称已具产品等效性**。
- C完成后交付版本化冻结System字节与哈希、组装器调用路径和合成测试；只有通过A/B的候选才可构造正式Train/Validation输入。
- 不自动下载27B权重、不运行GPU/HF Job、不将任何私有训练文件提交GitHub。

## 未解决的关键选择

产品实际推理是否向模型传入完整World/角色设定，以及每个历史目标所适用的版本，必须通过RolePlay冻结V2 runtime `sunxu/RolePlay@ccdf2e8dc2723f481cd0392883bc359e9e341c66` 的实际分支和真实来源核验；不能简单用今天的`v2_data`填补历史空缺。若找不到足够的有卡、可证明的样本，C可交付`MINIMAL_NO_CARD`技术合同，但需标记产品等价性HOLD并交Owner决策，而非凭空补卡。


## 2026-11-15 工程落地：纯函数构造器已接入CI

已增加`experiments/r58_quality/r60_base_constructed_system_contract_v1.py`与7条合成回归`test_r60_base_constructed_system_contract_v1.py`。构造器明确输出`TRAINING_CONSTRUCTED_NOT_HISTORICAL`，强制三消息`user,assistant,user`轮次严格早于最后Assistant目标，拒绝错误角色序列、没有版本定位的`latest/current/unknown`卡片、来自不同Story的World/角色引用。无卡时只采用本文件冻结通用System，保留来源/实际collator/Reviewer/R50/世界准入标志均False且Train 0。它**不能**独立核实调用者伪造的`target_time_proof_ref`，不能替代数据库来源绑定、目标SHA或ms-swift实际collator，所以当前状态仍为`CONTRACT_DESIGNED__ACTUAL_COLLATOR_HOLD`。

[GitHub Actions #43633850974](https://github.com/sunxu/storyforge/actions/runs/43633850974) Ruff及222项合成测试PASS；不是Owner真实336条训练准入或新合同实际CPU collator PASS。C线下一步应复用已有HF CPU336模块作**有限的合成/受控私有样本**真实Tokenizer/Collator检查，并冻结编码后的System字节、输入版本、上下文时序与source hash，不再重复旧无System336全量审计。
