# R58 Gold192 Reviewer A 统一结果构建（以已验证 V3 文件为准）

**重要纠正：旧的 V6 normalizer 已停用。** 此前使用的 `R58_GOLD192_AI_REVIEW_REMAINING51_CASES_PRIVATE_20261102.json` 未验证存在，不能作为输入。SAFE 统计数量不能推导独立逐案文件。旧 `R58_GOLD192_REVIEWER_A_RESULTS.json` 及旧 7 条队列均应标记为 `UNVERIFIED_SUPERSEDED`，不得用于准入或训练。

## 只接受的 Reviewer A 原始来源

1. `R58_GOLD192_AI_REVIEW_SAFE_20261102_v3.json`：192 条汇总，140 PASS、51 HOLD、1 REJECT。
2. `R58_GOLD192_AI_REVIEW_31_CASES_PRIVATE_20261102.json`：31 条逐案六维 PASS-only。
3. `R58_GOLD192_AI_REVIEW_SUPPLEMENT_PRIVATE_20261102_v3.json`：51 条明确 HOLD 分组、1 条明确 REJECT 分组、31 条补审记录。31 条补审记录必须与 PRIVATE 31 文件逐条完全一致。

另以冻结 Gold192 私人故事包的 `case_id + target_sha256` 建立身份映射，并与规范 Reviewer B 192 条结果的 Target SHA256 集合完全一致。所有来源均固定 SHA-256。不存在也不需要任何 Remaining51 逐案文件。

## 证据粒度（192 条完整索引）

| 来源粒度 | 数量 | A 判定 | 六维评分 |
| --- | ---: | --- | --- |
| PRIVATE 31 逐案记录 | 31 | PASS_ONLY | 有 |
| Supplement 明确 HOLD 分组 | 51 | HOLD | 无，不补分 |
| Supplement 明确 REJECT 分组 | 1 | REJECT | 无，不补分 |
| SAFE V3 总量与其余明确记录互补 | 109 | PASS_ONLY（汇总推导） | 无，不视为逐案审核 |

109 条 PASS_ONLY 是根据 SAFE V3 的 140/51/1 总量、31 条逐案 PASS、51 条 HOLD ID 和 1 条 REJECT ID 做集合互补得到。它们的 `decision_for_strict_ab_decision_comparison=null`，不得作为已有逐案 PASS 评分或审核理由。

## 与规范 Reviewer B 的核对

规范 Reviewer B：178 PASS、12 HOLD、2 REJECT。

按 Reviewer A 证据粒度交叉核对后，109 条 aggregate-only PASS 中有 7 条 Reviewer B 非 PASS（6 HOLD、1 REJECT）；其余 102 条 Reviewer B PASS。另有 3 条 A 逐案 PASS / B HOLD，及 A HOLD/REJECT 与 B 判定不一致的案例。详见 PRIVATE 统一结果与 SAFE 交叉表。

旧 11 条 AI arbitration 是基于未验证的 V6 Reviewer A 证据版本形成的，不能自动套用到当前已确认的 V3 Reviewer A 判定。保留旧事件作历史审计，但在完成来源版本对齐前不得将其视为 V3 A/B 分歧已解决。

## Mac 构建

将三个已确认的 V3 Reviewer A 文件及 Gold192 packets 放在 Owner 私有目录（可放入 `reviewer-a-recovered`），规范 Reviewer B 文件放在 `$PRIVATE_DIR`。先检查实际文件位置：

```bash
PRIVATE_DIR="$HOME/.local/share/storyforge/r58/private"
find "$PRIVATE_DIR/reviewer-a-recovered" -maxdepth 2 -type f \
  \( -name 'R58_GOLD192_AI_REVIEW_SAFE_20261102_v3.json' \
  -o -name 'R58_GOLD192_AI_REVIEW_31_CASES_PRIVATE_20261102.json' \
  -o -name 'R58_GOLD192_AI_REVIEW_SUPPLEMENT_PRIVATE_20261102_v3.json' \
  -o -name 'gold192-story-review-packets-v1.private.jsonl' \) -print
```

确认路径后运行：

```bash
cd ~/workspace/storyforge-gold-quality
git pull --ff-only
source .venv/bin/activate
PRIVATE_DIR="$HOME/.local/share/storyforge/r58/private"
SOURCE_DIR="$PRIVATE_DIR/reviewer-a-recovered"
umask 077

python -m storyforge_gold_quality.normalize_reviewer_a_v3 \
  --safe-v3 "$SOURCE_DIR/R58_GOLD192_AI_REVIEW_SAFE_20261102_v3.json" \
  --cases31 "$SOURCE_DIR/R58_GOLD192_AI_REVIEW_31_CASES_PRIVATE_20261102.json" \
  --supplement-v3 "$SOURCE_DIR/R58_GOLD192_AI_REVIEW_SUPPLEMENT_PRIVATE_20261102_v3.json" \
  --packets "$SOURCE_DIR/gold192-story-review-packets-v1.private.jsonl" \
  --reviewer-b "$PRIVATE_DIR/R58_GOLD192_REVIEWER_B_RESULTS_20261102.json" \
  --output "$PRIVATE_DIR/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED_20261102.json" \
  --safe-output "$PRIVATE_DIR/R58_GOLD192_REVIEWER_A_RESULTS_V3_RECONCILED_SAFE_20261102.json" \
  --priority-output "$PRIVATE_DIR/R58_GOLD192_A_AGGREGATE_ONLY_B_NONPASS_7_PRIVATE_20261102.json" \
  --repo-root "$PWD"
```

若 packets 或 V3 来源文件不在 `SOURCE_DIR`，请把对应参数改为 `find` 确认的真实路径；不得虚构路径。命令验证五份 SHA256、192 个 case/hash 唯一性、B Target 集合、31 条补审文件一致性、51/1 分组以及所有计数。输出只写入 repo 外、权限 0700 的私人目录，文件权限 0600；拒绝覆盖。

Quality-v1 仍为 0；不授权训练、不启动 GPU、不访问 R50、不修改冻结 Gold 源数据。
