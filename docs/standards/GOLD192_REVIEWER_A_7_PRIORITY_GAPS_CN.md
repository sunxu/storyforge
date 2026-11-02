# Gold192 Reviewer A：优先恢复 7 条缺失逐案证据

这是一个**只读筛选**工具，不生成新的 Reviewer A 审核，不重审 Gold192，也不自动把 V6 汇总级 PASS_ONLY 当作逐案 PASS。

输入：
- `R58_GOLD192_REVIEWER_A_RESULTS_20261102.json`：已经核验的 Reviewer A 192 条统一索引
- `gold-quality-events.jsonl`：包含 192 条规范 Reviewer B、79 条 Reviewer A 完整评分、4 条历史无评分 REJECT 和 11 条 AI 仲裁的私有 Manifest

输出：
- Owner 私有优先补证队列，按 `target_sha256` 精确关联，含 `case_id`、Reviewer B 的既有理由及评分、A 的证据缺失状态
- 仅包含计数的 SAFE 终端回执，不打印私人 ID、目标 SHA 或审核理由

## 操作

```bash
cd ~/workspace/storyforge-gold-quality
git pull --ff-only
source .venv/bin/activate

PRIVATE_DIR="$HOME/.local/share/storyforge/r58/private"
umask 077

python -m storyforge_gold_quality.reviewer_a_gap_priority \
  --reviewer-a "$PRIVATE_DIR/R58_GOLD192_REVIEWER_A_RESULTS_20261102.json" \
  --manifest "$PRIVATE_DIR/gold-quality-events.jsonl" \
  --output "$PRIVATE_DIR/gold192-reviewer-a-7-priority-gaps.private.json" \
  --repo-root "$PWD"
```

预期：`priority_case_count=7`、`priority_reviewer_b_decisions={"HOLD":6,"REJECT":1}`，其他 102 条暂不处理。输出目录必须权限 0700，生成的 PRIVATE JSON 权限 0600；已有文件不会被覆盖。

注意：这 7 条的 `reported_final_decision=PASS_ONLY` 是基于 V6 总量及完整四条 REJECT 名单的**集合互补推导**，其 `reviewer_a_actual_case_level_decision=null`、`reviewer_a_scores_1_to_5=null`。下一步优先从历史 Reviewer A 文件中查找对应逐案原始记录，找不到再决定是否进行定向补审，不能填充臆造分数。

独立 AI 仲裁原先的 11 条判定仍保存在另一个证据层，本任务不会改动它们。Quality-v1 仍 0，GPU 和训练保持关闭，不访问 R50。
