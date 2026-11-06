# R60 Gold72 Reviewer B2 — 生成、执行与验收 Runbook

日期：2026-11-06  
范围：冻结的 R60 Gold72 staging 选择；只构建独立 AI 语义复核包，不进行 Quality-v1 准入或训练。

## 1. 门禁与固定来源

本流程只接受以下两个精确来源：

- Gold192 原始故事审核包 SHA256：`ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e`
- R60 Gold72 staging SHA256：`edf46b1c637ba66e697968d6bf8dbab8feb3b4ec7bee26ec85b1bfb6edeaa3df`

同时要求对应 staging SAFE 回执：
- schema：`storyforge-r59-contiguous-suffix-stage-safe-v1`
- status：`CONTIGUOUS_SUFFIX_SOURCE_STAGE_BUILT__NOT_QUALITY_ADMITTED`
- source_rows / context_staged：72
- context_structure_hold：0
- quality_v1_admitted：0
- training_authorized / gpu_started / r50_accessed：false

生成器只从 staging 读取 72 个目标身份，再从冻结 Gold192 包取回这些目标的原始可见历史、当前 User 输入、目标 Assistant 回复和导出时世界卡快照。它不会读取 Reviewer A/B1 结果、SAFE、分歧表或 Owner 历史映射。

## 2. 本机生成命令

在 Owner Mac 的仓库工作区执行。先确认仓库已更新到本 PR 分支最新提交。

```bash
set -euo pipefail
umask 077

REPO="${REPO:-$HOME/workspace/storyforge}"
test -d "$REPO/.git"
ROOT="$HOME/.local/share/storyforge"
PRIVATE="$ROOT/r59/private"
EXPECTED_SOURCE="ae26a288382939aa79923d4a4c0602b0d575baa63f81c622ab362fbb70d56a5e"
EXPECTED_STAGE="edf46b1c637ba66e697968d6bf8dbab8feb3b4ec7bee26ec85b1bfb6edeaa3df"

find_by_sha() {
  local pattern="$1"
  local expected="$2"
  local file actual
  while IFS= read -r -d '' file; do
    actual="$(shasum -a 256 "$file" | awk '{print $1}')"
    if [[ "$actual" == "$expected" ]]; then
      printf '%s' "$file"
      return 0
    fi
  done < <(find "$ROOT" -type f -name "$pattern" -print0)
  return 1
}

SOURCE="$(find_by_sha '*.jsonl' "$EXPECTED_SOURCE")"
STAGED="$(find_by_sha 'GOLD_SOURCE_STAGING_PRIVATE.jsonl' "$EXPECTED_STAGE")"
STAGING_SAFE="$(dirname "$STAGED")/GOLD_SOURCE_STAGING_SAFE.json"
INSTRUCTIONS="$REPO/docs/evidence/R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md"

test -f "$SOURCE"
test -f "$STAGED"
test -f "$STAGING_SAFE"
test -f "$INSTRUCTIONS"
test "$(shasum -a 256 "$SOURCE" | awk '{print $1}')" = "$EXPECTED_SOURCE"
test "$(shasum -a 256 "$STAGED" | awk '{print $1}')" = "$EXPECTED_STAGE"

mkdir -p "$PRIVATE/reviewer-b2-runs"
chmod 700 "$PRIVATE/reviewer-b2-runs"
OUT="$PRIVATE/reviewer-b2-runs/gold72-b2-20261106-v1"
test ! -e "$OUT"

python3 "$REPO/experiments/r58_quality/r60_reviewer_b2_package.py" \
  --gold192-source-jsonl "$SOURCE" \
  --gold72-staged-jsonl "$STAGED" \
  --gold72-staging-safe "$STAGING_SAFE" \
  --instructions-file "$INSTRUCTIONS" \
  --output-dir "$OUT" \
  --repo-root "$REPO"

cat "$OUT/R60_GOLD72_REVIEWER_B2_PACKAGE_SAFE.json"
```

如果源文件名不同，先用 `find "$ROOT" -type f` 定位文件；不要放宽 SHA256 固定值，也不要改用“最新文件”。

## 3. 给独立 Reviewer B2 的内容

**只提供以下两个文件：**

- `R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl`
- `R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md`

推荐使用 ChatGPT Temporary Chat（临时聊天）或无会话状态的一次性 API 请求。不得在当前 StoryForge 对话或其他已有审核对话中执行。

**绝不能提供：**

- `R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json`
- `R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json`
- Reviewer A/B1 的任何文件
- Gold192 原始包、Gold72 staging、候选来源分组或筛选原因

B2 结果必须覆盖全部 72 条，并返回 instructions 中规定的 JSON。若模型上下文不足，不要截断历史或让模型自行挑选子集；应停止并返回 HOLD，再设计分批无状态执行和结果合并。

## 4. 执行回执（使用 fail-closed Receipt Builder）

Owner 的 Results 原始文件已报告为 `/private/tmp/r60_b2_independent_20261106/R60_GOLD72_REVIEWER_B2_RESULTS.json`。此位置仅是 Owner 报告，必须在本机核对。

```bash
set -euo pipefail
umask 077
REPO="${REPO:-$HOME/workspace/storyforge}"
OUT="$HOME/.local/share/storyforge/r59/private/reviewer-b2-runs/gold72-b2-20261106-v1"
SRC="/private/tmp/r60_b2_independent_20261106/R60_GOLD72_REVIEWER_B2_RESULTS.json"
DEST="$OUT/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json"
test -f "$SRC" && test ! -L "$SRC"
test -d "$OUT" && test ! -L "$OUT"
test ! -e "$DEST" && test ! -L "$DEST"
install -m 600 "$SRC" "$DEST"  # create only; 保留原件
```

随后另行保存**真实的**完整独立审核转录或提供方执行记录为 `$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECORD_PRIVATE`，并设置 `chmod 600`。不得复制 Results 充当执行记录，也不得凭空补造 session、model backend ID、执行时间或独立性声明。若记录缺失或不完整，应停止并保留 HOLD。

以下命令先只读验证 72 条绑定与文件哈希（不会生成最终 Receipt）：

```bash
ARGS=(
  --package-safe "$OUT/R60_GOLD72_REVIEWER_B2_PACKAGE_SAFE.json"
  --receipt-template "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE_TEMPLATE.json"
  --blind-input "$OUT/R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl"
  --instructions "$OUT/R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md"
  --owner-map "$OUT/R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json"
  --result "$OUT/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json"
  --execution-record "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECORD_PRIVATE"
  --output "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE.json"
  --repo-root "$REPO"
)
python3 "$REPO/experiments/r58_quality/r60_reviewer_b2_receipt_builder.py" "${ARGS[@]}" --validate-only
```

只有预检 PASS，且 Owner 已实际检查 Execution Record 后才执行交互生成：

```bash
python3 "$REPO/experiments/r58_quality/r60_reviewer_b2_receipt_builder.py" "${ARGS[@]}" \
  --draft-output "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_DRAFT_PRIVATE.json"
```

程序会收集真实 provider/model/session/timestamps，并要求六项执行者独立性声明和四项 Owner verification **分别回答 YES / NO / UNKNOWN**。仅全部 YES 且元数据真实有效时，才 create-only 写入正式 `EXECUTION_COMPLETE` Receipt。NO、UNKNOWN、缺失时间、缺少记录时均不得声称完成；已有输出不得覆盖。

临时聊天未公开 session ID 时，只能使用 `NOT_EXPOSED_BY_PROVIDER`，并记录 limitation；该哨兵值不代表真实 session ID。执行者自我声明仍不是密码学独立性证明。

## 5. Owner-only 结果验收

```bash
set -euo pipefail
umask 077

python3 "$REPO/experiments/r58_quality/r60_reviewer_b2_audit.py" \
  --blind-input "$OUT/R60_GOLD72_REVIEWER_B2_BLIND_PACKETS.jsonl" \
  --instructions "$OUT/R60_GOLD72_REVIEWER_B2_INSTRUCTIONS_CN.md" \
  --owner-map "$OUT/R60_GOLD72_REVIEWER_B2_ID_MAP_PRIVATE.json" \
  --result "$OUT/R60_GOLD72_REVIEWER_B2_RESULTS_PRIVATE.json" \
  --execution-receipt "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECEIPT_PRIVATE.json" \
  --execution-record "$OUT/R60_GOLD72_REVIEWER_B2_EXECUTION_RECORD_PRIVATE" \
  --safe-output "$OUT/R60_GOLD72_REVIEWER_B2_AUDIT_SAFE.json"
```

验收器会检查：
- 72 条 blind ID、Owner map、结果集完全一致；
- 每条 target SHA256 精确匹配；
- 72 条六维评分完整；
- PASS 必须满足六维分数下限且无 severe flags；
- 决策计数与逐案结果一致；
- 输入、说明、结果、执行记录 SHA256 与回执一致；
- 执行声明完整，且 Owner 已完成四项本地核验。

SAFE 仍明确区分“Owner 已核验执行材料”与“密码学证明 reviewer 独立”。即使通过，也不会自动准入 Quality-v1。

## 6. 当前状态与禁止事项

- B2 package builder / audit 工具：代码与合成测试。
- 实际 72 条盲审：待 Owner 本机生成后，在独立执行环境完成。
- Quality-v1 admission：0。
- Training authorization：false。
- GPU：未启动。
- R50：未访问。

不要把私有盲 ID 映射、原始案例、审核结果或执行转录提交到 GitHub。只提交代码、说明和聚合 SAFE。
