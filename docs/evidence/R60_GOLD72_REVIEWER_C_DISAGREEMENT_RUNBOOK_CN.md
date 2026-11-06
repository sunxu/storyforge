# R60 Gold72 Reviewer C 分歧盲审包 — Owner Runbook

日期：2026-11-06  
状态：Reviewer C Results-only 结构验收完成；执行记录不可获得，独立性未验证。Owner 逐案裁决和 aggregate-only Manifest 导入仍待执行。

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
- `R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json`
- `R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE_TEMPLATE.json`
- 任意 Reviewer A/B2 文件、SAFE、分数、决策或分歧类型
- Gold72 staging、Gold192 原始包、Owner Evidence、case_id、story_uuid

必须使用全新 Temporary Chat 或无状态 API 请求。Reviewer C 不得使用已有记忆、历史对话、连接器、外部搜索或仓库工具。执行后返回完整 40 条 JSON 结果及真实执行记录；不得补造 provider/session/model 元数据。

## 5. Reviewer C 返回后

当前工具链提供盲审包生成、Receipt 和 Audit。Reviewer C 尚未执行；只有收到完整 Results 和真实执行记录后才能继续。

### 5.1 保存 Reviewer C 返回材料

将 Reviewer C 返回的完整 JSON 和真实执行转录/提供方记录保存到 Owner 私有输出目录：

- `R60_GOLD72_REVIEWER_C_RESULTS_PRIVATE.json`
- `R60_GOLD72_REVIEWER_C_EXECUTION_RECORD_PRIVATE`

使用 create-only 方式保存，不覆盖旧文件；文件权限 0600，父目录 0700。不得用 Results 复制品充当执行记录，不得编造 session/provider/model/timestamps。

### 5.2 只读预检并生成 Receipt

```bash
set -euo pipefail
umask 077

REPO="$HOME/workspace/storyforge-r60-ledger-diagnostics"
PYTHON="$HOME/.venvs/storyforge-r60/bin/python"
C_OUT="$HOME/.local/share/storyforge/r59/private/reviewer-c-runs/gold72-c-20261106-v1"

ARGS=(
  --package-safe "$C_OUT/R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json"
  --receipt-template "$C_OUT/R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json"
  --blind-input "$C_OUT/R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl"
  --instructions "$C_OUT/R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md"
  --owner-map "$C_OUT/R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json"
  --result "$C_OUT/R60_GOLD72_REVIEWER_C_RESULTS.json"
  --execution-record "$C_OUT/R60_GOLD72_REVIEWER_C_EXECUTION_RECORD_PRIVATE"
  --output "$C_OUT/R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_COMPLETED.json"
  --repo-root "$REPO"
)

cd "$REPO"
"$PYTHON" -m experiments.r58_quality.r60_reviewer_c_receipt_builder "${ARGS[@]}" --validate-only
```

预检 PASS 后，且 Owner 已实际打开检查完整执行记录，才运行交互式 Receipt Builder：

```bash
"$PYTHON" -m experiments.r58_quality.r60_reviewer_c_receipt_builder "${ARGS[@]}"
```

必须真实填写 provider、model、可见 session/request 标识、开始/结束时间。六项独立性声明和四项 Owner 验证逐项回答 YES / NO / UNKNOWN。只有元数据有效且十项全部 YES 时，才会 create-only 生成 `EXECUTION_COMPLETE` Receipt；否则失败关闭，不得声称完成。临时聊天未暴露 session ID 时使用 `NOT_EXPOSED_BY_PROVIDER` 并保留限制说明。

### 5.3 Owner-only Audit

```bash
"$PYTHON" -m experiments.r58_quality.r60_reviewer_c_audit \
  --blind-input "$C_OUT/R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl" \
  --instructions "$C_OUT/R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md" \
  --owner-map "$C_OUT/R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json" \
  --result "$C_OUT/R60_GOLD72_REVIEWER_C_RESULTS_PRIVATE.json" \
  --execution-receipt "$C_OUT/R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_COMPLETED.json" \
  --execution-record "$C_OUT/R60_GOLD72_REVIEWER_C_EXECUTION_RECORD_PRIVATE" \
  --safe-output "$C_OUT/R60_GOLD72_REVIEWER_C_AUDIT_SAFE.json"
```

C Audit 检查 40/40 blind-ID / Owner Map / Results 绑定、target SHA、六维评分、PASS 门槛、决策计数、四个输入哈希、六项执行声明和四项 Owner 核验。其 SAFE 仍将 Reviewer C 独立性和密码学证明标为未验证。

### 5.4 Owner 决策与 Manifest

Reviewer C Audit 通过后，40 条仍不是最终裁决。Owner-only `R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE_TEMPLATE.json` 已随盲审包生成，40 条的 Reviewer C 与 Owner 决策字段均为空。仍需实现并验证逐案决策完整性校验器和 aggregate-only Gold72 resolution importer；在这两项工具完成并通过 synthetic-only CI 之前，不把模板标记为完成，不追加 Manifest 事件，不进行 Quality-v1 准入。

不得把 Reviewer C 结果自动转成最终 Owner 决定。40 条未决期间保持 HOLD。

### 5.5 Owner 三方对照与逐案裁决

Reviewer C Results-only SAFE 可以证明结构绑定，不证明独立执行。当前 execution_record_available=false、execution_metadata_sha256=null，因此不生成伪造的 EXECUTION_COMPLETE Receipt，也不运行正式 C Audit。Owner 裁决仍可在明确保留该限制的前提下继续。

Owner 工具会重新绑定冻结的 canonical A V3、B2 Results、A/B2 Crosswalk SAFE、C Results、C Owner Map 和 C blind input。A V3 与 B2 Results 必须分别匹配本任务已冻结的 SHA256；40 条逐案只按 target SHA256 连接。输出仅留在 Owner 私有目录。

\`\`\`bash
set -euo pipefail
umask 077

REPO="$HOME/workspace/storyforge-r60-ledger-diagnostics"
PYTHON="$HOME/.venvs/storyforge-r60/bin/python"
B2_OUT="$HOME/.local/share/storyforge/r59/private/reviewer-b2-runs/gold72-b2-20261106-v1"
C_OUT="$HOME/.local/share/storyforge/r59/private/reviewer-c-runs/gold72-c-20261106-v1"

A_V3="$HOME/.local/share/storyforge/r58/private/quality-v1/reviewer-a-v3-normalization-20261103/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED.json"
B2_RESULTS="$B2_OUT/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json"
CROSSWALK="$B2_OUT/R60_GOLD72_REVIEWER_A_B2_CROSSWALK_SAFE.json"

COMMON=(
  --package-safe "$C_OUT/R60_GOLD72_REVIEWER_C_PACKAGE_SAFE.json"
  --receipt-template "$C_OUT/R60_GOLD72_REVIEWER_C_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json"
  --blind-input "$C_OUT/R60_GOLD72_REVIEWER_C_BLIND_PACKETS_PRIVATE.jsonl"
  --instructions "$C_OUT/R60_GOLD72_REVIEWER_C_INSTRUCTIONS_CN.md"
  --owner-map "$C_OUT/R60_GOLD72_REVIEWER_C_ID_MAP_PRIVATE.json"
  --result "$C_OUT/R60_GOLD72_REVIEWER_C_RESULTS_PRIVATE.json"
  --results-only-safe "$C_OUT/R60_GOLD72_REVIEWER_C_RESULTS_ONLY_AUDIT_SAFE.json"
  --resolution-template "$C_OUT/R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE_TEMPLATE.json"
  --reviewer-a-v3 "$A_V3"
  --b2-results "$B2_RESULTS"
  --crosswalk-safe "$CROSSWALK"
  --repo-root "$REPO"
)

cd "$REPO"
"$PYTHON" -m storyforge_gold_quality.cli prepare-gold72-owner-resolution \
  "\${COMMON[@]}" \
  --output "$C_OUT/R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE.json"
\`\`\`

生成的私有逐案表包含：
- A：规范化决策、原始决策标签、证据粒度、可用的六维评分；
- B2：决策、六维评分、严重问题标记、证据摘要；
- C：决策、六维评分、严重问题标记、证据摘要；
- Owner：最终决定、决定依据、中文理由、证据引用、带时区时间和逐案签署。

必须由 Owner 逐案阅读 A/B2/C 原始证据后填写。不得把 C 的 38 个 PASS 批量复制成 Owner PASS，也不得采用多数票。

每条 Owner 记录必须填写：
- owner_decision：PASS / HOLD / REJECT；
- owner_decision_basis：A_EVIDENCE_CONTROLS、B2_EVIDENCE_CONTROLS、C_EVIDENCE_CONTROLS、CROSS_REVIEWER_SYNTHESIS、SOURCE_RECHECK、INSUFFICIENT_EVIDENCE_HOLD 之一；
- owner_rationale_cn：至少 20 个字符，写明本案实际理由；
- owner_evidence_refs：至少一条可定位的证据引用，不允许绝对路径、URL 或路径穿越；
- owner_decided_at_utc：带时区 ISO8601；
- owner_signoff：必须为 true。INSUFFICIENT_EVIDENCE_HOLD 只能搭配 HOLD。

Owner 完成全部 40 条后，执行只读校验并生成聚合 SAFE：

\`\`\`bash
"$PYTHON" -m storyforge_gold_quality.cli validate-gold72-owner-resolution \
  "\${COMMON[@]}" \
  --owner-resolution "$C_OUT/R60_GOLD72_OWNER_DISAGREEMENT_RESOLUTION_PRIVATE.json" \
  --safe-output "$C_OUT/R60_GOLD72_OWNER_RESOLUTION_SAFE.json"
\`\`\`

SAFE 只包含 A/B2/C/Owner 决策计数、四维交叉矩阵、源文件 SHA256 和安全门禁；不会包含案例身份、原始文本、Owner 理由或证据引用。

**Manifest 导入是独立的写操作。** 只有 Owner 已逐案确认 SAFE、并明确批准追加时，才运行：

\`\`\`bash
"$PYTHON" -m storyforge_gold_quality.cli import-gold72-owner-resolution \
  --input "$C_OUT/R60_GOLD72_OWNER_RESOLUTION_SAFE.json" \
  --manifest "$HOME/.local/share/storyforge/r58/private/gold-quality-events.jsonl" \
  --repo-root "$REPO"
\`\`\`

Importer 仅追加一条 aggregate-only GOLD72_OWNER_RESOLUTION 事件，具备精确 SAFE 哈希幂等保护；不同 SAFE 不得覆盖已固定事件。它不会导入任何逐案行，也不会把 C 独立性升级为已验证，不会进行 Quality-v1 准入或训练。

## 6. 永久门禁

- `quality_v1_admitted=0`
- `training_authorized=false`
- `gpu_started=false`
- `r50_accessed=false`
- Reviewer A/B2 原始判断不可覆盖
- 多数票自动裁决禁止
