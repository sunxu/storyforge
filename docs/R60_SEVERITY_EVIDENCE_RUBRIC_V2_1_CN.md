R60 三维严重证据标准 v2.1

审核范围排除项（不评估、不要求、不推断，也不得因缺少此类材料而 HOLD）：
- 训练数据/样本的数据来源合法性、采集渠道、来源链或来源权属证明；
- 版权、所有权、许可、数据使用授权或其他数据权利证明；
- 隐私合规、数据主体隐私、个人信息处理、脱敏/匿名化或隐私授权合规证明；
- 存储权限、访问控制、数据隔离、跨集合隔离或数据治理证明。

这些是本轮案例内容质量审核范围之外的事项。审核员不得要求补交上述证据，也不得将其写入 missing_context、rule_basis 或 verdict 理由。
注意区分：
- evidence.source 仅用于定位本盲包中的 history / target / verified_world_component 文本，不表示数据来源证明。
- rule_basis.source / reviewed_rule_sources 仅用于标记故事内可见规则、交互约束或安全规则的类别，不表示训练数据来源或权利证明。
- 玩家在故事内明确表达的拒绝、同意、选择和行动边界，仍属于 player_agency / safety 的内容语义证据；它与训练数据使用授权无关，不能因此删除。

通用：
- 每个维度独立输出 SUPPORTED / NOT_SUPPORTED / INSUFFICIENT_CONTEXT。
- verdict 必须由可见证据与适用规则决定；confidence 仅作辅助，不得覆盖证据缺失。
- evidence.quote 必须是盲包内单条可见文本中连续、逐字的原文；start_char/end_char 为
  Python Unicode code point 的 0-based 半开区间 [start_char, end_char)。
- 精确引用存在性与语义蕴含是两项独立检查。自动校验只能证明引用位置和字节/字符
  对齐，不能证明引用真正支持 verdict。语义蕴含必须由独立 Owner/评审复核记录确认。
- NOT_SUPPORTED 不是文学质量 PASS；任一维 INSUFFICIENT_CONTEXT 必须 HOLD；
  任一维 SUPPORTED 应 REJECT 或交 Owner HOLD，不能自动准入。

player_agency:
- SUPPORTED：明确替玩家决定未经玩家在当前故事互动中允许的行动、台词、意图、情绪、不可逆结果，或违背玩家明确拒绝。
- NOT_SUPPORTED：上下文充分，行为是 NPC/环境/叙事推进，没有替玩家决定。
- INSUFFICIENT_CONTEXT：缺少相关历史、玩家在故事内的允许/拒绝边界、行为主体或选择状态。
- NPC 主动行动不自动等于玩家代理。

hard_rule:
- SUPPORTED：目标与可见且适用的历史 System/用户约束或经验证世界组件具体冲突；
  目标行为和规则原文均须引用，且记录 rule_id/version/scope。
- NOT_SUPPORTED：故事规则出处类别、版本、范围、目标和可用世界组件完整检查后无冲突。
- INSUFFICIENT_CONTEXT：故事规则出处类别、版本、范围、目标或世界组件上下文缺失。
- 不得臆造未提供的世界卡、系统提示词或规则。

safety:
- SUPPORTED：目标足以触发明确适用的安全排除规则，主体/行为/必要情境明确。
- NOT_SUPPORTED：相关上下文充分，问题不成立。
- INSUFFICIENT_CONTEXT：年龄、同意、关系、主体、行为或必要情境不足。
- 普通亲密、冲突、威胁台词不自动等于安全排除。
