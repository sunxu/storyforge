# R58 Gold192：AI 分歧仲裁证据导入

本命令把已完成的 11 条 AI 仲裁作为独立事件层导入 Owner 私有 Manifest。它**不是 Owner 裁决**，不覆盖 Reviewer A/B、不制造六维评分、不改变 Quality-v1 准入。

## 输入

Owner 本地私有目录需要三份文件：

- `R58_GOLD192_11_AI_ARBITRATION_PRIVATE_20261102.json`
- `R58_GOLD192_11_AI_ARBITRATION_SAFE_20261102.json`
- `gold192-arbitration-11.private.json`（生成本次仲裁的原始队列）

导入器校验私有报告 SHA256 与 SAFE 收据一致、队列 SHA256 与私有报告的 source_integrity 一致，并逐条核对 11 个 Target SHA、A/B 原判定、B 匿名 ID 及分歧类型。任何不匹配都在追加前失败关闭。

## Mac 操作

```bash
cd ~/workspace/storyforge-gold-quality
git pull --ff-only
source .venv/bin/activate

PRIVATE_DIR="$HOME/.local/share/storyforge/r58/private"

storyforge-gold-quality import-ai-arbitration \
  --input "$PRIVATE_DIR/R58_GOLD192_11_AI_ARBITRATION_PRIVATE_20261102.json" \
  --safe-summary "$PRIVATE_DIR/R58_GOLD192_11_AI_ARBITRATION_SAFE_20261102.json" \
  --queue "$PRIVATE_DIR/gold192-arbitration-11.private.json" \
  --manifest "$PRIVATE_DIR/gold-quality-events.jsonl" \
  --repo-root "$PWD"

storyforge-gold-quality reconcile-gold192 \
  --manifest "$PRIVATE_DIR/gold-quality-events.jsonl"
```

首次成功预期追加 11 条 `AI_ARBITRATION`；再次运行应为 0 条追加。事件包含仲裁决定、理由、范围限制及来源 SHA，全部保留在 Owner 私有 Manifest。

## 统计语义

reconcile 额外报告 `ai_arbitration_events_present=11`、`ai_arbitration_pass=6`、`ai_arbitration_hold=5`。这些值只反映 AI 仲裁层，不会更改 A/B 的 `paired_case_count`、原始拒绝/暂缓计数或缺失 Reviewer A 数量，也不会计为 `OWNER_ARBITER`。

AI 仲裁不是独立盲审证明，也不是 Owner 批准。当前 6 条 AI PASS 仍需 Owner 审批及其余身份范围、审核独立性、语义/世界设定门禁；Quality-v1 仍为 0。不得因此启动 GPU 或训练，不访问 R50。
