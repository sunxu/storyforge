# R60 Gold72 Reviewer C 分歧盲审包 — Owner Runbook

日期：2026-11-06  
状态：工具合成测试待 CI；本文件不代表 Reviewer C 已执行。

## 1. 目的与边界

本工具从已完成的 Gold72 A/B2 crosswalk 中提取**恰好 40 条语义决策分歧**，为全新 Reviewer C 生成新的随机盲 ID 和 Owner-only 映射。

固定分歧分布：

| A 证据 / 决策 | B2 决策 | 数量 |
|---|---|---:|
| CASE_LEVEL_SCORED_PASS | HOLD | 5 |
| CASE_LEVEL_SCORED_PASS | REJECT | 2 |
| EXPLICIT_HOLD | PASS | 30 |
| EXPLICIT_HOLD | REJECT | 3 |
| **合计** | | **40** |

32 条 A/B2 一致案例不进入 C 包。此选择规则仅由 Owner 工具使用；Reviewer C 不得获知分歧筛选原因。

工具重新执行完整 A/B2 crosswalk audit，并要求既有 Crosswalk SAFE 的来源 SHA、72/40/32 计数和配对分布与新鲜计算完全一致。任何 stale SAFE、绑定错误或数量变化均 HOLD。

本工具：
- 不重新审核 A 或 B2；
- 不修改 Gold72 staging、A/B2 原始结果、Receipt 或 Manifest；
- 不执行自动仲裁或 Owner 决策；
- 不导入任何 Manifest 事件；
- 不进行 Quality-v1 准入或训练。

## 2. 输入文件

使用现有归档，不重新生成。Owner 私有目录：

`$HOME/.local/share/storyforge/r59/private/reviewer-b2-runs/gold72-b2-20261106-v1`

其余固定输入路径见 `R60_GOLD72_REVIEWER_A_B2_CROSSWALK_RUNBOOK_CN.md`。必须传入原始 staging、staging SAFE、Owner Evidence、canonical A V3、B2 blind input、B2 instructions、Owner Map、Results、Execution Receipt、Execution Record、B2 Audit SAFE 和已归档 Crosswalk SAFE。

所有私有输入文件必须是普通文件、非 symlink、mode 0600、单硬链接；各自父目录 mode 0700。不要复制或重新生成来源文件来规避权限检查。

## 3. 生成命令

先确认代码分支已经通过 CI，并且 Owner 已按正常 Git 流程将此工具分支检出到现有 Worktree。不要新建 Worktree。

```bash
set -euo pipefail
umask 077

REPO="$HOME/workspace/storyforge-r60-ledger-diagnostics"
PYTHON="$HOME/.venvs/storyforge-r60/bin/python"
B2_OUT="$HOME/.local/share/storyforge/r59/private/reviewer-b2-runs/gold72-b2-20261106-v1"
C_PARENT="$HOME/.local/share/storyforge/r59/private/reviewer-c-runs"
C_OUT="$C_PARENT/gold72-c-20261106-v1"

STAGED="$HOME/.local/share/storyforge/r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_PRIVATE.jsonl"
STAGING_SAFE="$HOME/.local/share/storyforge/r59/private/source-staging-suffix72-20261104-v1/GOLD_SOURCE_STAGING_SAFE.json"
OWNER_EVIDENCE="$HOME/.local/share/storyforge/r59/private/quality-v1/owner-autolink-suffix72-20261104-v1/OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl"
A_V3="$HOME/.local/share/storyforge/r58/private/quality-v1/reviewer-a-v3-normalization-20261103/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED.json"

test "$(git -C "$REPO" branch --show-current)" = "r60/gold72-disagreement-reviewer-c"
test -x "$PYTHON"
test -f "$B2_OUT/R60_GOLD72_REVIEWER_A_B2_CROSSWALK_SAFE.json"
test ! -e "$C_OUT" && test ! -L "$C_OUT"

mkdir -p "$C_PARENT"
chmod 700 "$C_PARENT"
test "$(stat -f '%Lp' "$C_PARENT")" = "700"

cd "$REPO"
"$PYTHON" -m experiments.r58_quality.r60_reviewer_c_disagreement_packet \
  --staged-jsonl "$STAGED" \
  --staging-safe "$STAGING_SAFE" \
  --owner-evidence-jsonl "$OWNER_EVIDENCE" \
  --reviewer-a-v3-json "$A_V3" \
  --b2-blind-jsonl "$B2_OUT/R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl" \
  --b2-instructions "$B2_OUT/R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md" \
  --b2-owner-map-json "$B2_OUT/R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json" \
  --b2-results-json "$B2_OUT/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json" \
  --b2-execution-receipt "$B2_OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_COMPLETED.json" \
  --b2-execution-record "$B2_OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECORD_PRIVATE" \
  --b2-audit-safe "$B2_OUT/R60_GOLD72_REVIEWER_B2_AUDIT_SAFE.json" \
  --crosswalk-safe "$B2_OUT/R60_GOLD72_REVIEWER_A_B2_CROSSWALK_SAFE.json" \
  --reviewer-c-instructions "$REPO/docs/evidence/R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md" \
  --output-dir "$C_OUT" \
  --repo-root "$REPO"
```

预期 SAFE：

`REVIEWER_C_DISAGREEMENT_PACKAGE_BUILT__AWAITING_INDEPENDENT_REVIEW`

且必须是 40 条，配对计数为 5 / 2 / 30 / 3。输出目录和文件权限分别为 0700 / 0600。

## 4. Reviewer C 交付边界

**只提供给 Reviewer C：**
- `R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl`
- `R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md`

**绝不能提供：**
- `R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json`
- `R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json`
- 任意 Reviewer A/B2 文件、SAFE、分数、决策或分歧类型
- Gold72 staging、Gold192 原始包、Owner Evidence、case_id、story_uuid

必须使用全新 Temporary Chat 或无状态 API 请求。Reviewer C 不得使用已有记忆、历史对话、连接器、外部搜索或仓库工具。执行后返回完整 40 条 JSON 结果及真实执行记录；不得补造 provider/session/model 元数据。

## 5. Reviewer C 返回后

当前分支只提供**盲审包生成器**。在收到 Reviewer C Results 和真实执行记录之前，不生成完成 Receipt、不做最终 Audit、不写入 Manifest。

后续必须单独实现并通过 synthetic-only CI：
1. Reviewer C 的 40 条结果/输入/Owner Map 绑定 Audit；
2. fail-closed C Execution Receipt Builder；
3. Owner 对 40 条逐案证据决定的私有记录格式；
4. 只追加聚合 SAFE 的 Gold72 resolution Manifest importer。

不得把 Reviewer C 结果自动转成最终 Owner 决定。40 条未决期间保持 HOLD。

## 6. 永久门禁

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `r50_accessed=false`
- Reviewer A/B2 原始判断不可覆盖
- 多数票自动裁决禁止
