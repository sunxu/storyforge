# StoryForge — 上下文消融实验收口与质量主线任务书

**版本：** v3.0 · 2026-11-27  
**状态：** `CONTEXT_ABLATION_CLOSED__NO_CLEAR_DEGRADATION__NONINFERIORITY_NOT_ESTABLISHED`  
**文档入口：** [PR #44](https://github.com/sunxu/storyforge/pull/44)（未合并；接手时核对 HEAD）。  
**唯一产品目标：** 使 Qwen/Qwen3.8-27B 中文互动叙事质量可证明优于 Base。

## 1. 已关闭，不再执行

Owner 已批准收口。完整实验过程、统计与限制见 [最终 SAFE 报告](../quality/STORYFORGE_CONTEXT_ABLATION_FINAL_20261127_CN.md)；原设计与原有证据链接见 [冻结 v2.1](https://github.com/sunxu/storyforge/blob/0e03154ce0ef32e0d78673eed7e8ef11be15fe88/docs/plans/STORYFORGE_CONTEXT_ABLATION_TASKBOOK_20261127_CN.md)。A 原 R54 31/9；B 同 System/目标、末三条历史消息；CPU40、16步训练、Gold48、96份匿名配对评分及 Owner-local 解盲均完成。无明确实质退化，未证明非劣效；B 不晋升。Train token 降65%，不等于实际费用降幅。禁止重新训练、生成、评审或扫描历史，以追求更强结论。

## 2. 下一阶段：监督目标质量与独立数据

当前不批准任何实际新采集、外发或训练。唯一下一任务是基于既有证据给出一次最小可执行的数据建设决策/提案，先确认是否存在已获许可、来源可验证且未暴露的原始互动目标可满足现有门禁；没有明确候选/授权则 HOLD，不批量查库、不重开旧候选。重点是目标本身具备真正的信息增量、合理 NPC 行动、玩家选择空间、连续性/事实边界及自然中文；只把 Gold48 的聚合诊断作为问题方向，不将暴露题、回答、评分样本用于数据构造、提示调优、选参或独立测试。

复用现有 Source Stage、World Isolation、Quality-v1、SFT/CPU mask 与 HF Runtime；先看 [资产索引](../REUSABLE_ASSET_INDEX.md) 与既有 [新来源任务书及限定范围政策](./STORYFORGE_NEW_SOURCE_QUALITY_MAINLINE_TASKBOOK_20261126_CN.md)（历史证据及政策，非待办清单）。221/T 已冻结、完整历史全集仍未证；保留限定范围政策原约束，不将其扩大到旧 HOLD。若存在合格新来源，先提交单个最小候选的来源/权限/时间绑定/隔离/内容质量/独立评估计划和必要预算，再由 Owner 批准具体操作。不足则写明实际阻塞及替代选择，停止，不预建新 corpus、采集系统或评审框架。正式准入仍采用原合同与独立双审，不能把本次探索性单评审替代正式门禁。新的独立未曝光测试必须在训练前固定用途、按独立世界隔离。

## 3. 安全与授权

World04 一条质量已批准但来源隔离 HOLD，Common2 两条质量/CPU通过但准入 HOLD，唯一收藏 E2 为预留评估，均不回开、不入训。保护范围221/T与历史政策不变，R50 sealed 不读，已批准平台内容使用权不重复申请。离线 Teacher 仍暂停；不为采集启动生产留证、不改 RolePlay 或 Supabase（若未来专项需要，沿用 STORYFORGE_SUPABASE_DSN，凭据不入 Git）。

R60 NO_PROMOTE；R61 未启动；`quality_v1_admitted=0`、`train_admitted=0`（新来源）、`training_authorized=false`、`model_promoted=false`。私有原件、权重、逐案数据、映射不入 Git。本次只做文档收口及私有归档定位；新增执行授权为0。

新 Agent 唯一入口：[接手提示词](../handoffs/STORYFORGE_CONTEXT_ABLATION_NEXT_AGENT_20261127_CN.md)。
