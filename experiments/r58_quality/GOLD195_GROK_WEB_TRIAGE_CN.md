# R58 Grok 网页三案双审：SAFE 分流与人工/AI 复核

2026-11-01 第一批真实 Grok 网页输出：六份齐全，3 份暂定通过、1 份 JSON 格式异常、1 份引文不在 Gold 目标中、1 份报告严重标志；共两案 A/B 状态不一致，仅一案双审暂定通过。**不等于实际内容质量结论，更不构成训练准入**。

## 立即运行匿名分流

在 Mac 的 R58 仓库根目录：

~~~bash
git pull --ff-only
python3 experiments/r58_quality/gold195_grok_web_triage.py \
  --private-pilot-dir "$HOME/storyforge-review-private/grok-web-pilot-v1"
~~~

输出仅包含 case01/case02/case03、Reviewer A/B 结果分类与下一步操作。**不输出真实 story UUID、候选 ID、故事内容或私人文件路径。** 此命令不访问 Grok、不修改评审 JSON。

## 处理原则

- `MALFORMED`：保留原始 Grok 回复，不自行给缺失分数/字段编造答案。若仅有 Markdown 代码围栏，可忠实提取完整 JSON；若内容字段缺失，需要在独立新会话重审同一份 .md。
- `EVIDENCE_QUOTE_NOT_IN_GOLD`：检查引文必须是 Gold **目标回复**的逐字子串。禁止擅自修改成另一段看似合理的话；可要求 Grok 对同一材料重新选取确切证据并重新输出完整 JSON。原始回复必须保留备份。
- `SEVERE_FLAG`：优先针对真实原文审查标记依据。不能因另一位评审给 PASS 就自动取消严重问题，独立复核之前保持 HOLD。
- `PROVISIONAL_REVIEW_PASS`：意味着结构、数值、引用条件达到程序设定门槛，尚未验证中文文学判断、世界卡真实性或世界级训练隔离。
- 若有 `CARD_CONFLICT_OR_UNCERTAIN`、`BELOW_SCORE_FLOOR`，需要内容讨论与复核，不应将其归类为格式错误。

此分流工具不会用 A 的内容补写 B，也不会发起新的 Grok 调用。初轮只覆盖 3 条私人 Gold，**不得自动扩大到 63 条**。若重审结果替换原文件，原始文件应先归档到本机仓库外、权限 0700 的私人备份目录，确保审计可追溯。R50 不读，GPU/HF 不启动。

下一步在所有有效 JSON 恢复后，独立复核严重标志和两位分歧，并确定 Grok 网页质量是否足够扩样。Quality-v1 训练准入仍为 0。
