# Gold192 Reviewer A 私有证据恢复（2026-11-02）

目标：恢复可验证的第一轮 AI 逐案审核，**不重审 Gold192、不虚构六维评分、不自动训练**。此工具不是 Quality-v1 准入器。

## 已固定的证据边界

- 最终 SAFE v6：188 PASS_ONLY、0 HOLD、4 REJECT（192 条全部已有首轮结论）。
- 私有逐案记录：首批 31 条、后续 51 条，共 82 个唯一 case_id。
- 其中 79 条 PASS_ONLY 有原始六维评分；3 条 REJECT 无六维评分，不可伪造。
- 另一条 REJECT 由 v6 私有拒绝分组列明，但不在这 82 条逐案记录中。
- 其余 110 条缺少本次恢复包中的逐案记录，不能依据汇总反向生成逐案评价。
- Reviewer B 的规范来源 SHA256 为 `bdd1980eacf9e21c08fb3e5ada482ea476f35c2018c6120e0f708718eda666e8`。

## 文件与信任边界

私有恢复包 `StoryForge_R58_Reviewer_A_Recovered_Private_20261102.zip` 的五个 JSON 文件均由恢复器校验固定 SHA256。它们**不得提交到 GitHub**。其中包括 Reviewer B 的原始 case_id / target_sha256 私人映射，仅用于 Owner 本地对齐；不要向 Reviewer B 会话提供。

恢复器要求本地 Manifest 先已有完整规范的 192 条 Reviewer B 记录，并检查私人映射的 target SHA256 集合与 B 完全一致，才可导入 79 个有评分的 Reviewer A 事件，以及四条**无评分、独立类型**的历史 REJECT 证据事件（`HISTORICAL_REJECT_EVIDENCE`）。输入文件、清单均不应位于 Git 仓库下。

## Owner Mac 操作

```bash
cd ~/workspace/storyforge-gold-quality
git pull --ff-only
source .venv/bin/activate

PRIVATE_DIR="$HOME/.local/share/storyforge/r58/private"
mkdir -p "$PRIVATE_DIR/reviewer-a-recovered"
chmod 700 "$PRIVATE_DIR" "$PRIVATE_DIR/reviewer-a-recovered"

unzip -q "$HOME/Downloads/StoryForge_R58_Reviewer_A_Recovered_Private_20261102.zip" \
  -d "$PRIVATE_DIR/reviewer-a-recovered"

python -m storyforge_gold_quality.recover_reviewer_a \
  --bundle-root "$PRIVATE_DIR/reviewer-a-recovered" \
  --manifest "$PRIVATE_DIR/gold-quality-events.jsonl" \
  --repo-root "$PWD"

storyforge-gold-quality reconcile-gold192 \
  --manifest "$PRIVATE_DIR/gold-quality-events.jsonl"
```

已运行过旧版恢复器的 Manifest，升级后补充导入四条历史 REJECT 事件，应得到 `events_appended=4`；全新 Manifest 一次导入为 `events_appended=83`（79 条标准评分 + 4 条无评分 REJECT），重复导入 `events_appended=0`。配对结果应仍有 `paired_case_count=79`、`missing_reviewer_a=113`，但新增 `historical_a_reject_without_scores=4`、`historical_a_reject_b_pass_disagreement=4`；这 113 包含三条已恢复的无评分 REJECT 及其余 110 条未恢复逐案记录，**不是 113 条从未判定**。

## 不应做的事

- 不以 SAFE v6 的 188/4 计数构造假的 192 条 A 评分事件。
- 不将 3 条无评分 REJECT 填成默认 1 分或 5 分。
- 不将被 A 拒绝的案例因缺少完整评分提升到 PASS。
- 不认为 A/B 已配对就意味着审核者独立性证明、世界设定清理或 Quality-v1 准入完成。
- 不读取 R50、不修改 Gold87/Gold108 冻结文件、不启动 GPU。

## 统计语义

`historical_a_reject_b_pass_disagreement=4` 代表通过私有 case_id→Target SHA-256 映射确认的历史 A 拒绝与规范 B 通过存在分歧；它们没有标准六维评分，因此**不计入** `paired_case_count`，也不会减少 `missing_reviewer_a`。`any_reject_hold_for_arbitration` 现在包含这些历史拒绝证据（按 Target SHA 去重），不能再忽略四条已知 A REJECT。

11 条已知分歧（6 条 A PASS/B HOLD、1 条 A PASS/B REJECT、4 条历史 A REJECT/B PASS）需后续私有仲裁；均不自动准入。
