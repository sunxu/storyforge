# StoryForge — 下一任 Agent 接手提示词（v3.2）

2026-11-28 · PR #44 · 上下文消融、有限退化诊断均关闭；监督目标质量假设获支持，因果 HOLD。

你是 StoryForge 下一任执行 Agent。唯一产品目标：让 Qwen/Qwen3.8-27B 中文互动叙事质量可证明优于 Base。不要偏离主线，不要重复开发，遵循最小化原理、最短实现路径。

1. 先读 AGENTS.md、[任务书 v3.2](../plans/STORYFORGE_CONTEXT_ABLATION_TASKBOOK_20261127_CN.md)、[监督目标 SAFE 对照](../quality/STORYFORGE_R60_SUPERVISION_QUALITY_COMPARISON_20261128_CN.md)、[上下文消融最终报告](../quality/STORYFORGE_CONTEXT_ABLATION_FINAL_20261127_CN.md) 和 [资产索引](../REUSABLE_ASSET_INDEX.md) 顶部。核对 PR #44 HEAD/main；归档 15462b8779401833a5014846bc57318dd6bc1b1c 不修改；未合并文档不冒称 main 实现。
2. 不重做 R54 A/B 31/9 末三历史消融、B CPU/GPU/Gold48、失败双审/小试点、ChatGPT 96评分和48/42解盲。主分析连续性 +0.0417、推进 −0.0417、自主权 +0.2292；敏感性 −0.0476/−0.1190/+0.1667。无明确退化、非劣效未证、短历史仅候选、B 不晋升。单评审、旧题暴露、先见6份 J1、采样顺序未证保留。
3. R54/R60 实际 Train31/293 分布及10+10盲审已完成，不重评、不追加样本。Story 5/146，目标字符均值431.258/549.546，P95 575/1126，精确重复0/0；推进 FAIL 1/4，增量0/5，重复0/2，自主权0/0，连续性 UNKNOWN 1/1。R54 Owner 授权 AI 不是独立人工；本次单 AI、长度匹配小样本、长尾未覆盖、完整 System/早期历史不可见；仅支持可操作质量假设，总体差异及根因未证。System 缺失、来源分布、梯度累积/步数等混杂保留，不跨协议直接减分。Gold48/P1 既有诊断不重做。
4. 唯一下一任务：按任务书第3节 D0–D2，**只读设计监督目标质量改进方案**。先查 main 的 Quality-v1 内核、历史 Gold Quality Pipeline rubric/prompt/证据校验及 SFT Skill，记录 ref/path、真实覆盖与缺口，聚焦推进、信息增量、回放。已有规则则优先检查执行口径；缺件才提最小兼容改动。不新建框架、不改代码、阈值或运行配置、不再评审、不采集、不查 Supabase。交付一份 SAFE 覆盖矩阵、唯一方案或 HOLD；必要时只提出一次未来单变量验证申请，固定 Base/System/上下文/训练规模及参数步数，尽量平衡来源与长度，独立未曝光评估及预算/验收/停止条件先定；不可控混杂明示。无合规数据则 HOLD，不实施。
5. 不回开 World04/Common2；E2 收藏预留评估不入训；221/T 冻结、完整历史全集未证，限定政策不扩大，不读 R50 sealed。不启动离线 Teacher/RolePlay 留证，不重复申请已有权利。不将旧诊断题/输出/评语或本次抽查用于训练、目标改写、Prompt/超参调优、checkpoint 选择或独立验收；只用聚合方向。匿名外发例外仅当次20条，已用毕。Git 只 SAFE 聚合，不写正文、逐案数据、身份、映射、凭据或权重。
6. 任何新增采集、外发、模型调用、代码/门禁变更、CPU/GPU、准入、训练、部署或晋升须另批。R60 NO_PROMOTE；R61 未启动；quality_v1_admitted=0、train_admitted=0（新来源）、training_authorized=false、model_promoted=false。
