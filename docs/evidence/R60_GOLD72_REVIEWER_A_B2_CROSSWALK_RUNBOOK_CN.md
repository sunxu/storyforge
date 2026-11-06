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

先使用此前已经归档的文件，不重新生成 Gold72、不重新审核 A/B2。以下是已记录的 Owner 本机路径；$HOME 对应 /Users/keedle：

~~~bash
set -euo pipefail
umask 077

STAGED="$HOME/.local/share/storyforge/r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_PRIVATE.jsonl"
STAGING_SAFE="$HOME/.local/share/storyforge/r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_SAFE.json"
OWNER_EVIDENCE="$HOME/.local/share/storyforge/r59/private/quality-v1/owner-autolink-suffix72-20261104-v1/OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl"
A_V3="$HOME/.local/share/storyforge/r58/private/quality-v1/reviewer-a-v3-normalization-20261103/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED.json"

for f in "$STAGED" "$STAGING_SAFE" "$OWNER_EVIDENCE" "$A_V3"; do
  test -f "$f"
  test ! -L "$f"
done

test "$(wc -l < "$STAGED" | tr -d ' ')" = "72"
test "$(wc -l < "$OWNER_EVIDENCE" | tr -d ' ')" = "72"
test "$(shasum -a 256 "$A_V3" | awk '{print $1}')" = \
  "b0356782963dd3c4f85c210bf0f1c69dc01211d818011c16754ea95e9a4fbdb8"

printf '%s\n' "GOLD72_INPUT_PATHS_PRESENT_AND_BASIC_COUNTS_MATCH"
~~~

该检查只验证文件存在、不是符号链接、两份 JSONL 行数和 Reviewer A 固定 SHA；它不替代交叉分析器的 Schema、内容及逐案绑定检查。若任一 test 失败，停止并只读定位现有归档，不得重建或覆盖。

使用现有工作区，不切换或新建 Worktree：

~~~bash
set -euo pipefail
umask 077

REPO="$HOME/workspace/storyforge-r60-ledger-diagnostics"
OUT="$HOME/.local/share/storyforge/r59/private/reviewer-b2-runs/gold72-b2-20261106-v1"

STAGED="$HOME/.local/share/storyforge/r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_PRIVATE.jsonl"
STAGING_SAFE="$HOME/.local/share/storyforge/r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_SAFE.json"
OWNER_EVIDENCE="$HOME/.local/share/storyforge/r59/private/quality-v1/owner-autolink-suffix72-20261104-v1/OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl"
A_V3="$HOME/.local/share/storyforge/r58/private/quality-v1/reviewer-a-v3-normalization-20261103/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED.json"

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

# 必须从仓库根目录以模块方式运行；脚本使用 package-relative imports。
PYTHON="$HOME/.venvs/storyforge-r60/bin/python"
cd "$REPO"
"$PYTHON" -m experiments.r58_quality.r60_reviewer_ab2_gold72_crosswalk \
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

### 3.1 导入共享 Quality Pipeline

交叉分析器完成后，再把聚合 SAFE 导入既有私有 append-only Manifest。此前已验证的统一账本路径如下；不要新建第二份账本：

~~~bash
MANIFEST="$HOME/.local/share/storyforge/r58/private/gold-quality-events.jsonl"

test -f "$MANIFEST" && test ! -L "$MANIFEST"
test "$(stat -f '%Lp' "$MANIFEST")" = "600"
test "$(stat -f '%Lp' "$(dirname "$MANIFEST")")" = "700"

storyforge-gold-quality import-review-reconciliation \
  --batch gold72 \
  --kind reviewer-a-b2-gold72 \
  --input "$SAFE" \
  --manifest "$MANIFEST" \
  --repo-root "$REPO"

storyforge-gold-quality report-safe --manifest "$MANIFEST"
~~~

同一 Receipt 可安全重复导入；不同 Receipt 若已占用 Gold72 canonical slot 会 HOLD。导入事件只保存批次级统计和私有来源 pins，不导入逐案行，不产生 Quality-v1 准入。

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
