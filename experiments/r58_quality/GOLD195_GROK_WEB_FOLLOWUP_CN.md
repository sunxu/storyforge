# R58 Grok 网页试审 — Case02 严重问题仲裁与 Case03 定向重审

## 确认的首轮结果

- Case01：A/B 均为 `PROVISIONAL_REVIEW_PASS`，不是文学质量正式批准。
- Case02：Reviewer A 标记 `SEVERE_FLAG`，Reviewer B 为 `PROVISIONAL_REVIEW_PASS`，进入**独立严重问题仲裁**。
- Case03：Reviewer A `MALFORMED`，Reviewer B `EVIDENCE_QUOTE_NOT_IN_GOLD`，必须重审/修复有效证据，不能自行编造内容。

**只涉及原先授权的 3 个 Gold 世界样本，不扩大到 63 条。**

## Mac 本地生成 3 份定向网页审题

在 R58 仓库根目录执行：

~~~bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_grok_web_followup*.py' -v

python3 experiments/r58_quality/gold195_grok_web_followup.py \
  --repo-root "$PWD" \
  --private-pilot-dir "$HOME/storyforge-review-private/grok-web-pilot-v1" \
  --private-followup-dir "$HOME/storyforge-review-private/grok-web-followup-v1"
~~~

生成只在 Mac 仓库外的权限 0700 私人目录中，每个文件 0600：

- `case02-independent-severe-arbitration.md`：第三位仲裁者审阅原始 Case02、A 的严重问题、B 的不同意见。**两次独立初审已结束，此时允许仲裁员看到双方原始结论。** 禁止投票式撤销严重标志。
- `case03-reviewer-A-retry.md`：在全新 Grok 对话里重新审核 Case03，不包含原始 A/B 评分。
- `case03-reviewer-B-retry.md`：在另一个全新 Grok 对话里重新审核 Case03，不包含原始 A/B 评分。

请只上传与本次任务相符的单份 Markdown 到 `https://grok.com`；不要上传所有私人文件夹或 Manifest。输出原本就应为 JSON。每个重审文件只包含 Case03 这一条原有 Gold，而非新样本；不得自动增补到第四条。

将三份新答复分别保存为同目录同名 `.json`，例如 `case03-reviewer-A-retry.json`，并确保 0600 权限：

~~~bash
chmod 600 "$HOME"/storyforge-review-private/grok-web-followup-v1/*.json
~~~

**不能删除或覆盖原始六份 JSON。**

## 本地校验新的仲裁与双重审

~~~bash
python3 experiments/r58_quality/gold195_grok_web_followup_validate.py \
  --private-pilot-dir "$HOME/storyforge-review-private/grok-web-pilot-v1" \
  --private-followup-dir "$HOME/storyforge-review-private/grok-web-followup-v1"
~~~

只输出 Case02 仲裁状态、Case03 A/B 各自结构/逐字引证状态，不输出故事正文、世界 UUID、个案原始 ID 或真实证据文本。

重点：`ARBITER_DISPUTES_SEVERE__MANUAL_RESOLUTION_REQUIRED` **不是**自动撤销初审的严重违规；`ARBITER_CONFIRMED_SEVERE__HOLD` 也必须保留来源证据。只有经过实际文本的独立内容复核，才能确定 Case02 的性质。Case03 不能把旧的引用错误直接当成文学不合格，也不能把 JSON 格式修好视为文学合格。

所有脚本仅做本地文件处理，不调用模型 API、不启动 HF/GPU、不触及 R50。Quality-v1 准入仍为 0。后续是否将 Grok 网页扩到 63 条，要根据本轮实际文学质量和独立仲裁效果另行确定。
