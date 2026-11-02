# R58 Gold192 Reviewer A 统一结果构建（PRIVATE）

本任务生成 `R58_GOLD192_REVIEWER_A_RESULTS.json`，统一冻结 192 条的 `case_id + target_sha256`，保留原始 Reviewer A 决策及证据层级。**统一结果不是新审核，不是全部 192 条逐案六维评分，也不自动准入。**

## 来源及校验

五个文件取自 Owner 私有 Reviewer A 恢复包（31 条首批、51 条后续、V6 补审、Reviewer B Owner 私人 ID 映射、SAFE v6），全部 SHA-256 固定。另需 SHA-256 固定的规范 Reviewer B 192 条结果，核对 Target 集合完整一致。脚本 `src/storyforge_gold_quality/normalize_reviewer_a.py` 实现此过程，不访问 R50。

## 证据层级

| 层级 | 数量 | `reported_final_decision` | `decision_for_strict_ab_pairing` |
| --- | ---: | --- | --- |
| 逐案六维评分 PASS | 79 | PASS_ONLY | PASS_ONLY |
| 有逐案拒绝、无评分 | 3 | REJECT | null |
| 仅 V6 拒绝分组 | 1 | REJECT | null |
| 仅由 V6 188/4 汇总与明确的 4 条拒绝名单推导 | 109 | PASS_ONLY | null |

最后一层的 PASS_ONLY 仅为**集合互补推导**，`v6_aggregate_complement_only=true`、`review_evidence_state=PASS_INFERRED_FROM_V6_AGGREGATE_PENDING_CASE_LEVEL_EVIDENCE`。并非原始逐案判定已经找回，**不得用于严格 A/B 评分配对或直接质量准入**。

缺少评分的 4 条拒绝保持 `scores_1_to_5=null`，不会造假分数。统一文件不覆盖现有 Reviewer A/B 事件；原 11 条仲裁与本统一结果保持不同证据层。

## Owner Mac 生成

此前已解压恢复包到 `$PRIVATE_DIR/reviewer-a-recovered`，规范 Reviewer B JSON 位于 `$PRIVATE_DIR`：

```bash
cd ~/workspace/storyforge-gold-quality
git pull --ff-only
source .venv/bin/activate

PRIVATE_DIR="$HOME/.local/share/storyforge/r58/private"
umask 077

python -m storyforge_gold_quality.normalize_reviewer_a \
  --bundle-root "$PRIVATE_DIR/reviewer-a-recovered" \
  --reviewer-b "$PRIVATE_DIR/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --output "$PRIVATE_DIR/R58_GOLD192_REVIEWER_A_RESULTS.json" \
  --safe-output "$PRIVATE_DIR/R58_GOLD192_REVIEWER_A_RESULTS_SAFE.json" \
  --repo-root "$PWD"
```

命令只向私有目录创建文件，拒绝覆盖已存在的结果；终端仅输出 SAFE 统计。已下载此对话提供的统一文件者不必重复生成（会因为文件存在而拒绝覆盖）。

预期 `reviewer_a_record_count=192`、`case_level_scored_pass=79`、`case_level_unscored_reject=3`、`group_only_unscored_reject=1`、`aggregate_only_pass_pending_case_evidence=109`、`strict_ab_pairing_eligible_from_a=79`。

## 后续复用

统一索引用于后续 Agent 的 A/B 差异定位、Reviewer A 逐案证据缺口队列及准入前复核。导出中所有私有 ID / Hash / 审核注释必须保留在 Owner 私有目录，**不得提交 GitHub**。SAFE 收据可公开，但仅保留计数和私有报告 SHA-256。

本阶段不启动 GPU、不授权训练、不修改 Gold87/Gold108 源数据、不访问 R50。
