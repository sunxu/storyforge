# R58 Gold195 — Grok 网页独立双审试点（3 条 × A/B）

Owner 已确认改用 Grok 网页，不走 xAI API。此前 63 条 User-first 私人审核题已成功生成，文件仍在 Mac 上；本程序**不访问 Grok 网页、不使用任何 API、不自动收费**。

## 1. 本地导出六份独立审题文档

在 StoryForge 仓库根目录运行：

~~~bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_grok_web_pilot.py' -v
python3 experiments/r58_quality/gold195_grok_web_export.py \
  --repo-root "$PWD" \
  --private-tasks "$HOME/storyforge-review-private/gold195-review-tasks-user-first-v1.jsonl" \
  --private-output-dir "$HOME/storyforge-review-private/grok-web-pilot-v1"
~~~

输出目录须不存在，父目录仅自己可读（0700），7 个文件均为 0600：

- case01-reviewer-A.md 与 case01-reviewer-B.md
- case02-reviewer-A.md 与 case02-reviewer-B.md
- case03-reviewer-A.md 与 case03-reviewer-B.md
- review-manifest.private.json（**不能上传到 Grok**，内含真实 case ID、原目标及来源哈希）

只选前 3 条（稳定、可重放），不泄露其余 60 条内容，不修改 Gold。生成后终端只打印 SAFE 统计。审核文档包含真实世界卡、上下文及 Gold，是私人数据；Owner 已同意最多这 3 条发送到 Grok 网页，不要将整个 63 条文件上传。

## 2. 在 grok.com 执行六次独立审阅

确认网页可选择预期的 Grok 4.7；网页显示的模型身份以实际 UI 为准，不能把 Grok 网页自动等同于官方 API 模型版本。每次**新建一个聊天**，仅上传对应 Markdown（或者复制其全部正文），请 Grok **只返回 JSON**。不要上传 Manifest，也不要向 Reviewer B 提供 A 的评分或讨论。A/B 使用同样的样本材料，但彼此独立；同一模型独立聊天不能声称是两个不同模型。

每个回答必须包含：六维 1–5 整数评分、六条具体理由、三个严重问题 boolean、世界卡可用性 verdict、卡片与 Gold 冲突列表，以及从目标 Gold 文本中逐字引用的短证据。若网页返回包在 Markdown 代码围栏内，保存时仅保留 JSON 对象。

分别保存到本地同一私有文件夹中：

- case01-reviewer-A.json / case01-reviewer-B.json
- case02-reviewer-A.json / case02-reviewer-B.json
- case03-reviewer-A.json / case03-reviewer-B.json

每份文件权限必须为 0600。Mac 可运行 `chmod 600 "$HOME"/storyforge-review-private/grok-web-pilot-v1/case*-reviewer-*.json`；切勿提交 GitHub 或上传到 CI。

## 3. 本地验证六份输出

~~~bash
python3 experiments/r58_quality/gold195_grok_web_validate.py \
  --private-pilot-dir "$HOME/storyforge-review-private/grok-web-pilot-v1"
~~~

输出只包含 SAFE 汇总，严格校验维度、整数、严重问题标志、六条理由、世界卡冲突标记、短证据是否为当前 Gold 目标的逐字子串。缺少结果标为 MISSING_REVIEW，无法验证的评分不能伪造。模型提出的剧情事实与文学质量**尚须独立复核**；结构上的双 PASS 只叫 provisional，**不构成 Quality-v1、世界隔离或训练准入**。不得读 R50 密封题，不会调用 HF / GPU。

## 本轮范围边界

仅 3 条 × 2 轮。模型服务与数据隐私仍受 Grok 网页条款和账户设置约束：Owner 授权分享这 3 条用于试审，但不得自动扩大到 63 条。后续实际审阅质量稳定之后，再选择是否扩样，以及如何处理剩余 132 条 Assistant-first。
