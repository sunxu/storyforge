# StoryForge — 下一任 Agent 接手提示词（v3.1）

2026-11-28 · PR #44 · 上下文消融已关闭；R60 退化原因尚未定位。

你是 StoryForge 的下一任执行 Agent。唯一产品目标：让 Qwen/Qwen3.8-27B 中文互动叙事质量可证明优于 Base。不要偏离主线，不要重复开发，遵循最小化原理、最短实现路径。

1. 先读仓库 AGENTS.md、[现行任务书](../plans/STORYFORGE_CONTEXT_ABLATION_TASKBOOK_20261127_CN.md)、[最终报告](../quality/STORYFORGE_CONTEXT_ABLATION_FINAL_20261127_CN.md) 和 [资产索引](../REUSABLE_ASSET_INDEX.md) 顶部。核对 PR #44 当前 HEAD/main；历史归档 `15462b8779401833a5014846bc57318dd6bc1b1c` 不修改。未合并文档不当作 main 代码。
2. 已完成且禁止重做：R54 A/B 31/9 末三历史消融、B CPU/GPU/Gold48、失败双审与小试点、ChatGPT 96份盲态评分与48/42配对本地解盲。主分析连续性 +0.0417、推进 −0.0417、自主权 +0.2292；敏感性 −0.0476/−0.1190/+0.1667。无明确退化但未建立非劣效。短历史只是候选；不推广 B、不继续历史长度实验/评审框架。单评审、旧暴露题、先见6份 J1 评分、采样顺序未证实均保留。不要用旧诊断题或答案训练、选参、改 Prompt，不以本次替代正式双审。
3. 唯一下一任务（只读）：按任务书第2节有限定位 R60 退化原因。先读固定 [R60 最终 Owner 决议](https://github.com/sunxu/storyforge/blob/15462b8779401833a5014846bc57318dd6bc1b1c/docs/R60_BASE336_GOLD48_QUALITY_V1_FINAL_OWNER_DECISION_20261122_CN.md)、[既有 Gold3 诊断](../quality/GOLD3_OWNER_LOCAL_QUALITY_DIAGNOSIS_20261125_CN.md)、已有 P1/Gold48/数据血缘/训练回执，逐项标注已完成和证据缺口，不重复评审或全量扫描。P0 比较 R54/R60 监督目标质量与分布（仅现成可比证据）；P1 必要时有限核对已知失败模式与目标模式，兼顾对照；P2 核对 System 缺失及其余混杂因素；P3 只有必要才提出一个最小单变量验证申请。不同评审协议的数值不可直接相减。区分相关线索和因果证据，不能排除历史窗口，也不能直接认定数据质量为根因。独立高质量原始监督目标建设延期至原因定位裁决后，不预建 corpus、框架或重新采集。
4. 不回开 World04/Common2；E2 收藏预留评估不入训；221/T 已冻结、完整历史全集未证，原限定范围政策不扩大，不读 R50 sealed。不启动离线 Teacher/RolePlay 留证，不重复申请已批准的平台内容使用权；不在 Git/聊天写正文、私有 ID、映射、凭据、权重。
5. 交付简洁 SAFE 原因定位报告：候选原因、既有证据及反证、已证/未证、局限、最有价值的一个最小下一步；证据不足可 HOLD，不强求根因已证。先复用，必要补充必须限定范围/理由，不扩大私有访问授权。旧诊断题仅供诊断，不用于训练、Prompt/超参调优或独立验收。任何新采集、外发、模型调用、CPU/GPU、训练、部署或晋升须另批。R60 NO_PROMOTE；R61 未启动；`quality_v1_admitted=0`、`train_admitted=0`（新来源）、`training_authorized=false`、`model_promoted=false`。
