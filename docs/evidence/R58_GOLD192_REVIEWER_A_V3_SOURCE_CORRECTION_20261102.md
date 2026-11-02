# R58 Gold192 Reviewer A 来源纠正记录（2026-11-02）

## 已确认的事实

资料库中已实际读取并验证以下三个 Reviewer A 来源：

- `R58_GOLD192_AI_REVIEW_SAFE_20261102_v3.json`：192 条汇总，140 PASS、51 HOLD、1 REJECT。
- `R58_GOLD192_AI_REVIEW_31_CASES_PRIVATE_20261102.json`：31 条逐案六维审核，全部 AI Semantic PASS-only。
- `R58_GOLD192_AI_REVIEW_SUPPLEMENT_PRIVATE_20261102_v3.json`：51 条 HOLD 的五组 case ID、1 条 REJECT 分组、31 条补审记录；补审记录与 PRIVATE 31 文件逐条一致。

**未验证存在** `R58_GOLD192_AI_REVIEW_REMAINING51_CASES_PRIVATE_20261102.json`。不得根据 SAFE 汇总的 51 HOLD 数量推导该文件存在。

## 旧产物作废范围

旧 normalizer 曾使用未经验证的 Remaining51/V6 输入假设，输出 79 条逐案 PASS、3 条逐案 REJECT、1 条分组 REJECT 和 109 条汇总互补 PASS。该证据分布不受已确认 V3 文件支持。

因此旧产物：
- `R58_GOLD192_REVIEWER_A_RESULTS.json`
- `R58_GOLD192_REVIEWER_A_RESULTS_SAFE.json`
- `gold192-reviewer-a-7-priority-gaps.private.json`

必须保留原件以供审计，但标记为 `UNVERIFIED_SUPERSEDED`，禁止用于当前 A/B 对照、Quality-v1 准入和训练。不得覆盖原件或静默删除。

## V3 正确证据分布

- 31 条：逐案六维 PASS-only。
- 51 条：Supplement 明确列出的 HOLD 分组；无六维评分。
- 1 条：Supplement 明确列出的 REJECT 分组；无六维评分。
- 109 条：从 SAFE V3 140/51/1 总量与上述明确案例集合互补得到的 PASS-only；仅汇总级，缺少逐案评分和理由。

192 个 case ID 与 Target SHA256 从冻结 Gold192 packets 建立，并与规范 Reviewer B 192 个 Target SHA256 精确匹配。

## 旧 11 条 AI 仲裁

旧 11 条 AI 仲裁队列引用 V6 Reviewer A evidence tier。V6 逐案来源文件未在本次确认的三份 V3 文件中出现，故旧仲裁不能自动用于 V3 分歧结论。保留旧 Manifest 事件作历史记录；完成版本对齐前不视为当前 V3 仲裁。

## 后续要求

所有后续 Agent 必须先检查真实文件存在性，再读取内容并固定 SHA256。SAFE 汇总只能支持汇总级事实；不能生成逐案文件、逐案分数或逐案理由。缺失数据必须显式标记，不得合成。
