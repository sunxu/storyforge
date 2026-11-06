# R60 Gold72 Reviewer A / B2 交叉分析 Runbook

日期：2026-11-06

## 1. 目的与边界

本工具将冻结的 Gold72 staging、canonical Reviewer A V3 和已完成 Owner Audit 的 Reviewer B2 结果逐案对照。它不重新审核案例、不修改任何冻结输入、不把自我声明提升为密码学独立性证明，也不执行 Quality-v1 准入或训练。

交叉分析回答：
- A 的证据粒度和决策，与 B2 72 条结果如何对应；
- A/B2 可比较决策中的一致数和分歧数；
- A 有逐案评分的案例中，六个评分维度的精确匹配数和平均绝对差；
- B2 对 A 明确 HOLD / REJECT 案例的 PASS 数量。

A 的 PASS_ONLY 在比较时规范化为 PASS。AGGREGATE_COMPLEMENT_ONLY 没有逐案严格比较决策，不计入可比较决策分母。所有输出仅包含聚合统计。

## 2. 固定来源

- Gold72 staging SHA256：edf46b1c637ba66e697968d6bf8dbab8feb3b4ec7bee26ec85b1bfb6edeaa3df
- Canonical Reviewer A V3 report SHA256：b0356782963dd3c4f85c210bf0f1c69dc01211d818011c16754ea95e9a4fbdb8
- A V3 schema：r58_gold192_reviewer_a_results_v3_reconciled_private_v1
- B2 Audit SAFE schema：r60_gold72_reviewer_b2_audit_safe_v1
- B2 Audit SAFE status：B2_RESULT_BINDING_VALID__EXECUTION_ATTESTATION_PRESENT_NOT_PROVEN

交叉分析会重新调用现有 B2 Audit，并将结果与已归档 B2 Audit SAFE 的哈希、计数和门禁字段逐项比对；旧 SAFE 过期或不匹配时失败关闭。

## 3. Owner 本机执行

使用现有工作区，不切换或新建 Worktree：

~~~bash
set -euo pipefail
umask 077

REPO="$HOME/workspace/storyforge-r60-ledger-diagnostics"
OUT="$HOME/.local/share/storyforge/r59/private/reviewer-b2-runs/gold72-b2-20261106-v1"

# 由 Owner 从既有 staging / Owner evidence / A V3 归档中指定确切文件。
: "\${STAGED:?请设置冻结 Gold72 staging JSONL 的绝对路径}"
: "\${STAGING_SAFE:?请设置对应 staging SAFE 的绝对路径}"
: "\${OWNER_EVIDENCE:?请设置 Gold72 Owner evidence JSONL 的绝对路径}"
: "\${A_V3:?请设置 canonical Reviewer A V3 report 的绝对路径}"

test "$(git -C "$REPO" branch --show-current)" = "r60/reviewer-ab-canonical-crosswalk"
test -f "$STAGED" && test ! -L "$STAGED"
test -f "$STAGING_SAFE" && test ! -L "$STAGING_SAFE"
test -f "$OWNER_EVIDENCE" && test ! -L "$OWNER_EVIDENCE"
test -f "$A_V3" && test ! -L "$A_V3"

test "$(shasum -a 256 "$STAGED" | awk '{print $1}')" = \
  "edf46b1c637ba66e697968d6bf8dbab8feb3b4ec7bee26ec85b1bfb6edeaa3df"
test "$(shasum -a 256 "$A_V3" | awk '{print $1}')" = \
  "b0356782963dd3c4f85c210bf0f1c69dc01211d818011c16754ea95e9a4fbdb8"

SAFE="$OUT/R60_GOLD72_REVIEWER_A_B2_CROSSWALK_SAFE.json"
test ! -e "$SAFE" && test ! -L "$SAFE"

python3 "$REPO/experiments/r58_quality/r60_reviewer_ab2_gold72_crosswalk.py" \
  --staged-jsonl "$STAGED" \
  --staging-safe "$STAGING_SAFE" \
  --owner-evidence-jsonl "$OWNER_EVIDENCE" \
  --reviewer-a-v3-json "$A_V3" \
  --b2-blind-jsonl "$OUT/R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl" \
  --b2-instructions "$OUT/R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md" \
  --b2-owner-map-json "$OUT/R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json" \
  --b2-results-json "$OUT/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json" \
  --b2-execution-receipt "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_COMPLETED.json" \
  --b2-execution-record "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECORD_PRIVATE" \
  --b2-audit-safe "$OUT/R60_GOLD72_REVIEWER_B2_AUDIT_SAFE.json" \
  --safe-output "$SAFE"
~~~

若正式 Receipt 实际文件名与上方示例不同，Owner 必须先通过本机只读检查确认实际文件，再调整参数；不得将旧 PENDING 模板作为执行回执。

## 4. 预期 SAFE 与解释

成功状态：

A_B2_CROSSWALK_COMPLETE__ADMISSION_HOLD

SAFE 将报告 A 证据粒度、B2 决策、逐案配对计数、可比较决策的一致/分歧，以及 A 有逐案评分案例上的六维分数差异。

交叉分析是证据对照，不是自动裁决。B2 PASS 不会覆盖 A HOLD；分歧案例不得自动升级为 Quality-v1。需要结合原有 Owner 证据门禁处理。

## 5. 永久保持的门禁

- reviewer_a_two_independent_blinded_reviews_met=false
- reviewer_b2_independence_verified=false
- cryptographic_independence_proven=false
- quality_v1_admitted=0
- training_authorized=false
- gpu_started=false
- r50_accessed=false

不要把 B2 Owner Map、Results、Execution Record、原始案例或逐案交叉表提交 GitHub。只保留 Owner 本机私有文件和聚合 SAFE。
