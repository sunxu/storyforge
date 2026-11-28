# StoryForge — 上下文消融实验收口与质量主线任务书

**版本：** v3.2 · 2026-11-28  
**状态：** `CONTEXT_ABLATION_CLOSED__NO_CLEAR_DEGRADATION__NONINFERIORITY_NOT_ESTABLISHED`  
**文档入口：** [PR #44](https://github.com/sunxu/storyforge/pull/44)（未合并；接手时核对 HEAD）。  
**当前执行状态：** `SUPERVISION_QUALITY_HYPOTHESIS_SUPPORTED__CAUSAL_HOLD__DESIGN_ONLY`  
**唯一产品目标：** 使 Qwen/Qwen3.8-27B 中文互动叙事质量可证明优于 Base。

## 1. 已关闭，不再执行

Owner 已批准收口。完整实验过程、统计与限制见 [最终 SAFE 报告](../quality/STORYFORGE_CONTEXT_ABLATION_FINAL_20261127_CN.md)；原设计与原有证据链接见 [冻结 v2.1](https://github.com/sunxu/storyforge/blob/0e03154ce0ef32e0d78673eed7e8ef11be15fe88/docs/plans/STORYFORGE_CONTEXT_ABLATION_TASKBOOK_20261127_CN.md)。A 原 R54 31/9；B 同 System/目标、末三条历史消息；CPU40、16步训练、Gold48、96份匿名配对评分及 Owner-local 解盲均完成。无明确实质退化，未证明非劣效；B 不晋升。Train token 降65%，不等于实际费用降幅。禁止重新训练、生成、评审或扫描历史，以追求更强结论。

## 2. R60 退化原因有限定位已收口（不再执行）

v3.1 的 P0–P3 完成有限证据裁决；根因仍 HOLD。Owner 已批准10+10目标抽查及限定当次匿名外发，盲态冻结后解盲完成。详见 [监督目标有限对照 SAFE 报告](../quality/STORYFORGE_R60_SUPERVISION_QUALITY_COMPARISON_20261128_CN.md)；原 v3.1 保留于 [固定历史版本](https://github.com/sunxu/storyforge/blob/9b2a2fcccc7d5276616a607293fa220a2cb37dac/docs/plans/STORYFORGE_CONTEXT_ABLATION_TASKBOOK_20261127_CN.md)。

实际 Train31/293 来源绑定回执通过，Story 5/146，目标字符均值431.258/549.546、P95 575/1126，两批精确重复0。盲审 n=10/10，推进 FAIL 1/4、增量 FAIL 0/5、实质重复 FAIL 0/2、自主权 FAIL 0/0、可见连续性 UNKNOWN 1/1（FAIL 0/0）；推进或增量 FAIL 1/5。有限证据支持监督目标有效性假设，非全量质量胜率、非因果、非独立双审。R54 是 Owner 授权 AI 审核，不是独立人工；单评审、定向长度匹配、长尾未覆盖、较早历史/System 不可见、来源分布不同均保留。System 缺失仍高优先候选，训练规模/来源、梯度累积2/8、步数16/37 等混杂保留。历史窗口影响未排除；不支持普遍过短。Gold48 既有退化证据仅为诊断，不重复十案例、Gold48/42、盲审20、全量审核/历史扫描、隔离、CPU/GPU，不继续收集历史资料代替分析。

## 3. 当前唯一任务：监督目标质量改进方案设计（只读）

不改变唯一产品目标，不预建数据或评审系统。先查 main 已有 Quality-v1 内核与测试，再查资产索引所指固定 Gold Quality Pipeline/rubric/prompt/证据校验、RolePlay SFT Skill；记录 ref@commit:path、已有覆盖、执行口径及具体缺口。仅聚焦有效剧情推进、实质信息增量、历史回放/内部重复；保留玩家自主权、连续性、自然中文与硬规则。合理的日常互动也可推进，不要求重大事件，不以字符长度机械筛选。

| 步骤 | 最小交付 |
|---|---|
| D0 | 已有规则覆盖矩阵：三项各自的真实判定定义、证据/阈值、执行口径及缺口；区分规则缺失、执行/证据不足、无法判断。只读代码/合同/既有 SAFE；不重评或读取暴露逐案材料来调 Prompt。 |
| D1 | 优先复用已有规则与证据校验；若已覆盖，明确执行口径改进提案；仅证实缺件才提出最小兼容修改及复用路径，不实施、不增加 Reviewer、工具或第二套 rubric。无明确缺口则 HOLD。 |
| D2 | 至多一个未来监督目标质量单变量对照申请：比较合同、同 Base/System/历史/规模/训练参数与步数、尽量平衡来源/长度，剩余混杂显式声明；合规未暴露独立评估、预算、验收与停止条件预定。不具备可比数据则 HOLD。仅设计，不执行。 |

交付简洁 SAFE 方案：现成能力和缺口、唯一推荐改动或 HOLD、是否值得申请一次最小验证；没有合规候选/授权则停止。不得直接剔除本次发现的缺陷样本重训 R60，不启动 R61、不为验证追求新数据规模。旧 Gold48、E1/E4、消融题/输出/评语及本次抽查正文/逐案评价只作诊断，不作训练素材、目标改写、Prompt/超参调优、checkpoint 选择或独立最终验收。只用聚合缺陷方向指导设计；新独立未曝光测试需训练前冻结用途、按世界隔离。

现行来源政策仍见[新来源任务书](./STORYFORGE_NEW_SOURCE_QUALITY_MAINLINE_TASKBOOK_20261126_CN.md)（历史证据与政策，非待办）。221/T 已冻结，完整历史全集仍未证。任何后续采集、外发、模型调用、CPU/GPU、门禁/代码变更、数据准入、训练、部署或晋升须另批；原许可不延伸。正式准入仍采用原合同及独立双审。

## 4. 安全与授权

World04 一条质量已批准但来源隔离 HOLD，Common2 两条质量/CPU通过但准入 HOLD，唯一收藏 E2 为预留评估，均不回开、不入训。保护范围221/T与历史政策不变，R50 sealed 不读，已批准平台内容使用权不重复申请。离线 Teacher 仍暂停；不为采集启动生产留证、不改 RolePlay 或 Supabase（若未来专项需要，沿用 STORYFORGE_SUPABASE_DSN，凭据不入 Git）。

R60 NO_PROMOTE；R61 未启动；`quality_v1_admitted=0`、`train_admitted=0`（新来源）、`training_authorized=false`、`model_promoted=false`。私有原件、权重、逐案数据、映射不入 Git。本次仅落实 SAFE 诊断结论与方案设计入口；下一阶段仅限第3节只读设计。没有新增采集、模型调用、代码变更、训练或部署授权。

新 Agent 唯一入口：[接手提示词](../handoffs/STORYFORGE_CONTEXT_ABLATION_NEXT_AGENT_20261127_CN.md)。
