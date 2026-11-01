# StoryForge R58 — Case02 严重问题最终证据裁定

## 当前事实

Grok 网页 Case01 和 Case03 的 A/B 均暂定通过；Case02 由初审 A 报严重问题、B 未报告，第三位 Grok 仲裁者 `NOT_SUPPORTED`。模型仲裁并非原始严重标记的自动删除依据。尚无真正的、独立核实的最终事实裁定。该实验仍涉及**最初授权的 3 条私人 Gold**，不扩大样本、不调用 API、不启动训练。

目标不是持续循环调用 Grok，而是为 Case02 完成**一次证据化的最终判断**。该判断可以是确认严重问题、认为现有证据不支持，或者继续无法确定。

## Mac 上准备私人裁定材料

在 R58 分支的 StoryForge 仓库根目录运行：

~~~bash
git pull --ff-only

python3 experiments/r58_quality/gold195_case02_final_disposition.py \
  --repo-root "$PWD" \
  --private-pilot-dir "$HOME/storyforge-review-private/grok-web-pilot-v1" \
  --private-followup-dir "$HOME/storyforge-review-private/grok-web-followup-v1" \
  --private-decision-template-output "$HOME/storyforge-review-private/case02-final-disposition-v1.json"
~~~

只会新建一个 PRIVATE JSON（0600），不覆盖首轮六份审核或三份后续答复。终端仅输出 SAFE 统计。注意**此文件包含私人角色/审核文字，绝不提交 GitHub 或上传公共 CI**。

本地独立裁定时，请查看其中原始 A/B 审核、第三仲裁的相互冲突证据，并在原有 Case02 故事卡与 Gold 审题中核对。不要只凭仲裁者立场或模型投票判断事实。填写字段：

- `decision`：`CONFIRMED_SEVERE`、`NOT_SUPPORTED_WITH_EVIDENCE` 或 `UNRESOLVED`；
- `gold_exact_quotes`：从 Case02 Gold 目标正文逐字摘取的短证据；
- `actual_source_evidence`：可见世界卡/历史规则的具体依据；禁止虚构不存在的禁令；
- `independent_reasoning`：清楚说明为什么证据支持或不支持初审严重标志；
- `decision_maker`：真实执行裁定的审阅者标识（不能冒用独立人审身份）；
- 只有实际审核完成时才把 `decision_completed` 设置为 `true`。无法确认则保持 `UNRESOLVED` 和 `false`。

整理完成后只运行只读校验：

~~~bash
python3 experiments/r58_quality/gold195_case02_final_disposition.py \
  --repo-root "$PWD" \
  --private-pilot-dir "$HOME/storyforge-review-private/grok-web-pilot-v1" \
  --private-followup-dir "$HOME/storyforge-review-private/grok-web-followup-v1" \
  --private-decision-input "$HOME/storyforge-review-private/case02-final-disposition-v1.json"
~~~

校验只验证结构、绑定、引用是否逐字存在，不可能仅凭脚本证明文学、设定语义或审阅者独立性；严禁把全套证据填成虚假的 PASS。

## 后续

如裁定 `NOT_SUPPORTED_WITH_EVIDENCE`，只解除这一条严重问题争议，Card 适用性、世界保护隔离、真实质量判断仍独立 HOLD；如 `CONFIRMED_SEVERE`，Case02 排除该训练候选；如 `UNRESOLVED`，保持该候选 HOLD。

不要求重新证明历史生产 Provider 请求，R50 封存，Gold 195 目标保持冻结，Quality-v1 准入为 0，GPU 仍未获授权。
