# R58 Gold192 增量审核分流（只读，不触发模型）

2026-11-02。Owner 已完成 Gold192 PRIVATE 范围清单的生成，本工具使用**已有**的三个私人文件，不会重新生成或覆盖任何文件。

## 目标

对 Gold192 进行低成本结构分流，不把历史 Gold87 的双 ACCEPT 当作已验证的 Reviewer 全文；不把 Gold108 的旧五维证据当作六维审核通过。本阶段不调用模型、不读取 R50、不制作训练 JSONL。

基于现有任务中的 `source_history_starts_with_assistant` 和 `card_source_kind`，SAFE 聚合统计 Gold87 和 Gold108 的 Assistant-first / User-first 数量，以及当前故事 UUID 数量和两批交叉故事情况。检查目标文本、完整输入的 SHA256、未审核状态和排除项状态；如现有私人范围与 195 个任务不一致，则整个工具 HOLD。

世界卡原本是 `PROPOSED_OFFLINE_CARD_NOT_APPROVED`，因此本工具不判断世界卡是否历史正确，也不检查实际故事的语义连贯性。任何输出不代表训练准入。

## 在 Mac 仓库根目录执行

```bash
set -e
git pull --ff-only
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold192_incremental_review_triage.py' -v
ruff check experiments/r58_quality/gold192_incremental_review_triage.py experiments/r58_quality/test_gold192_incremental_review_triage.py
PRIVATE_ROOT="$HOME/.local/share/storyforge/r58"
python3 experiments/r58_quality/gold192_incremental_review_triage.py \
  --repo-root "$PWD" \
  --private-tasks "$PRIVATE_ROOT/gold195-review-tasks-v1.jsonl" \
  --private-queue "$PRIVATE_ROOT/legacy-reuse-queue-v1.jsonl" \
  --private-scope "$PRIVATE_ROOT/gold192-scope-v1.private.jsonl"
```

预期成功状态 `GOLD192_INCREMENTAL_REVIEW_ROUTING_READY__SEMANTIC_HOLD`。得到各批次结构分布后，按“新增世界卡硬规则/人物关系、Assistant-first 上下文起点、玩家自主权、时间线”优先补审，而非 192 条全部从头打分。真正的语义审核仍需使用此前已生成的 PRIVATE 六维任务、原有 R58 审核工作流与逐案质量证据。

## Gold87 原审核资料当前边界

Owner 在 R45 checkout 检查 `evaluations/v0.2/gold-quality-87/`，实际只有 README、Gold87 JSONL、索引 CSV、未入选 25 条 CSV。README 提及的审核汇总来自更早五故事累积包，不在此文件夹内。历史记录中的双 ACCEPT 仍有效作为历史索引事实；不能凭空补造 Reviewer 原文。另行定位历史原始 A/B 资料，不阻塞 Gold108 105 条上下文差异检查。

本轮不读取任何 R50 正文，`quality_v1_admitted=0`、`training_authorized=false`、`gpu_started=false`。
