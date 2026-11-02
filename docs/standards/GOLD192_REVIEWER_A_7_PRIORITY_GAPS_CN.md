# Gold192：7 条 Reviewer A 汇总级 PASS / Reviewer B 非 PASS 的优先补证

本队列由 `normalize_reviewer_a_v3.py` 直接从已验证的 V3 原始文件和冻结 Gold192 packets 构建。它不读取不存在的 Remaining51 文件，也不依赖旧 V6 normalizer 或旧 Manifest A 事件。

## 选择规则

在 109 条只由 SAFE V3 汇总互补推导为 PASS_ONLY、尚无逐案 A 决策/评分的案例中，选择 Reviewer B 为 HOLD/REJECT 的案例：
- Reviewer B HOLD：6
- Reviewer B REJECT：1
- Reviewer B PASS：102（暂不进入这轮优先队列）

队列保留精确 `case_id + target_sha256`、Reviewer B 匿名 ID、评分、理由和 A 侧证据缺口。A 侧明确为 `reviewer_a_actual_case_level_decision=null`、`reviewer_a_scores_1_to_5=null`。这不是 A/B 正式分歧裁决，也不自动改变任何决策。

另有 3 条 A 逐案六维 PASS / B HOLD，不属于这 7 条 aggregate-only 缺口，应单独保留为另一类已配对分歧。51 条 A HOLD 及 1 条 A REJECT 也必须按 V3 Supplement 的明确分组保留。

## 生成

该队列已由 V3 normalizer 与统一结果同时生成，无需再单独运行旧 `reviewer_a_gap_priority`：

`R58_GOLD192_A_AGGREGATE_ONLY_B_NONPASS_7_PRIVATE_20261102.json`

## 历史 11 条 AI 仲裁的兼容性

既有 11 条 AI arbitration 队列使用的 Reviewer A evidence tier 指向 `V6`（包括 `RECOVERED_SCORED_CASE_LEVEL_V6` 和 `FINAL_V6_REJECT_GROUP_ONLY`）。当前已确认的 Reviewer A 来源是 V3，二者不能自动视为同一审核版本。旧事件应保留用于审计，但必须在 V3 重新关联后才能参与当前分歧处理；不得因为 Manifest 中已有 11 条 `AI_ARBITRATION` 事件，就宣称 V3 分歧已被解决。

本阶段只恢复和对齐证据，不新增语义审核，不做 Owner 裁决。Quality-v1 仍为 0，训练未授权，GPU 未启动，R50 未访问。
