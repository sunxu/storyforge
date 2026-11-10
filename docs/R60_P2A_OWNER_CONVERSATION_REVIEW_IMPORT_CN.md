# R60 P2A Owner 对话复核 Ledger 导入工具

## 目的

`scripts/r60_owner_conversation_review_import_v1.py` 将 Owner 在 ChatGPT 对话中明确给出的 60 项 A/B/C 复核意见，导入为独立的私有审计 Ledger。

它解决的是**对话意见留痕和可追溯性**，不是正式 Owner 语义复核回执生成器。

## 绝对边界

本工具：

- 保留 60 项原始顺序、blind ID、维度、原 verdict、Owner A/B/C 决定和补充意见；
- 保留 Claude Opus 5.5 的逐项结论、理由及 unresolved context，并明确标记其为 AI advisory；
- 输出私有 JSONL、SAFE 汇总和 SHA-256 manifest；
- 使用 create-only 输出目录，拒绝覆盖；
- 检查输入文件权限为 `0600`，输出父目录权限为 `0700`；
- 不写回或修改交接源文件。

本工具**不会**：

- 把 A/B/C 转换成新的正式 verdict；
- 把 Owner 对话意见转换成官方 semantic check；
- 生成 `reviewer_role`、`reviewer_ref` 或 Owner 身份 attestation；
- 把 Claude 意见标记成 Owner 意见；
- 修改原始 packet、results 或 semantic checks；
- 运行官方 verifier、Quality-v1 admission、HF Job 或 GPU 训练。

特别说明：

- A = Owner 在对话中表示支持原始裁决；
- B = Owner 在对话中表示不支持原始裁决，但没有指定替代 verdict；
- C = Owner 要求按上下文不足处理/复核，但没有完成正式 verdict 改写。

B 和 C 必须留在对话审计 Ledger 中，不能由导入工具猜测替代 verdict。

## 输入

输入必须是此前生成的：

`R60_P2A_OWNER_60_REVIEW_HANDOFF_PRIVATE.json`

文件权限必须为 `0600`。输入包应保存在 Owner 私有目录中。工具验证：

- handoff schema 和状态；
- 20 个案例、每案 3 个维度，共 60 项；
- item 顺序、case 顺序和 blind ID + dimension 唯一性；
- A/B/C 数量为 58/1/1；
- Claude 复核身份明确为 `AI_CROSS_REVIEW_ADVISORY_NOT_OWNER`；
- handoff 明确声明尚未生成正式 Owner 回执、没有伪造身份、没有启动 GPU、没有训练授权。

## Owner Mac 执行

在仓库根目录：

```bash
cd /Users/keedle/workspace/storyforge
git branch --show-current
git rev-parse HEAD
git status --short
```

确认分支为：

`r60/gold192-history-v3-adapter`

然后：

```bash
set -euo pipefail
umask 077

PRIVATE="$HOME/.local/share/storyforge/r60/private"
INPUT="$PRIVATE/owner-review-handoff-20261109/R60_P2A_OWNER_60_REVIEW_HANDOFF_PRIVATE.json"
OUT="$PRIVATE/owner-conversation-review-ledger-20261109"

test -f "$INPUT"
test ! -L "$INPUT"
test "$(stat -f '%Lp' "$INPUT")" = "600"
test "$(stat -f '%Lp' "$PRIVATE")" = "700"
test ! -e "$OUT"

python3 scripts/r60_owner_conversation_review_import_v1.py \
  --input-json "$INPUT" \
  --output-dir "$OUT"
```

输出父目录必须是 mode `0700`；工具创建新输出目录 mode `0700`，三个输出文件均为 mode `0600`。不允许覆盖已有输出目录。若失败，先保留 SAFE 错误码并检查原因，不要删除原输入或放宽权限后盲目重试。

## 预期输出

目录：

`$PRIVATE/owner-conversation-review-ledger-20261109/`

文件：

- `OWNER_CONVERSATION_REVIEW_LEDGER_PRIVATE.jsonl`
- `OWNER_CONVERSATION_REVIEW_IMPORT_SAFE.json`
- `OWNER_CONVERSATION_REVIEW_IMPORT_MANIFEST.json`

SAFE 成功状态：

`OWNER_CONVERSATION_LEDGER_CREATED__NOT_FORMAL_OWNER_RECEIPT`

关键字段应为：

- `total_items = 60`
- `decision_counts = {A: 58, B: 1, C: 1}`
- `owner_identity_attested = false`
- `formal_owner_receipt_created = false`
- `official_semantic_checks_created = false`
- `original_files_modified = false`
- `gpu_started = false`
- `training_authorized = false`

## 下一阶段

Ledger 通过核验后，再单独设计正式语义复核流程：

1. Owner 在本机逐项查看官方 packet 对应的全部 evidence indexes 和原始证据；
2. 对每个维度明确记录是否支持原 verdict；
3. B 项必须由 Owner 明确指定是否改 verdict、目标 verdict 和理由；未指定则保持 HOLD；
4. C 项必须明确是否正式改为 `INSUFFICIENT_CONTEXT)，并给出对应 missing context；
5. 只有 Owner 实际完成这些复核后，才能形成符合官方 schema 的 semantic check；
6. 再运行未修改的官方 verifier。

本 Ledger 不是正式 Owner 回执，不改变 Quality-v1 准入数，不授权训练。
