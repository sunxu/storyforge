# R60 Base336 — Reviewer A 静态语义审查交付（SAFE）

日期：2026-11-19；来源：Owner 提交的 `R60_BASE336_REVIEWER_A_SAFE_V2_20261119_RUN01.json` 与文字交付说明。机器 SAFE 回执已逐项读取；**原始 10 份私有裁决、Review Notes、签名/快照仅在 Owner 本机，未由本次 GitHub 变更独立复核**。

## 已完成但未获得独立资格的工作

- 审查范围：跨拆分候选 01、02、11、14、19、21、22、24、25、26（十对）；不包含另 16 条同拆分候选或全量 38 Story 语义组件图。
- 静态内容决策：10 对均为 `SAME_SEMANTIC_COMPONENT`；`INDEPENDENT_TEMPLATE_ONLY=0`，`INSUFFICIENT_EVIDENCE=0`，`PENDING=0`。
- 来源版本审阅声明：10/10；正式工具对 10/10 的 A/B 引用、证据回放、记录/版本/JSON Pointer 等绑定作过机器验收，SAFE 报告 `reference_binding_verified_for_filled=10`。文字交付报告共 33 次侧记录引用（跨 edge 可重复）、89 条非空字段引用；这两个计数不在 SAFE JSON 中，归属为**交付方报告**，尚未由 Owner 独立验证。
- `independent_execution_attested=0/10`，`reviewer_independence_independently_verified=false`。同一 AI 会话组织 Reviewer A 两个子任务及主 Agent 复核，是工作分工，**不等于经资格认证的独立审查，也不等于双 Reviewer 一致**。
- v2 `verify` 的 `REVIEW_INCOMPLETE_HOLD` 在这种情况下表示“内容填完，但独立资格不满足”而不是“十份表格空白或未审”。不能把缺失的独立性声明事后无依据改为 true。

## 正确后续处置

1. Owner 在原授权的 0700/0600 私有目录完整保留 Reviewer A 10 份 Decision、原始 Evidence、笔记、SAFE 回执、私有 delivery_snapshot 和 manifest，不覆盖、不清理；避免私有标识进入公开 GitHub。审查副本及临时文件按 Owner 合规策略归档。
2. 由此前未参与候选发现、旧 Codex 判断、Reviewer A 审查及本轮主 Agent 裁决的、**身份/执行隔离可核验**的独立 Reviewer B 在新私有 0700 目录执行一次 `prepare`（仅从同一八组已封存来源和 V2 packet 生成证据及空白表，绝不复制 A 的 Decision）。
3. B 盲审 10 对；仅提供同一任务书、10 份双侧 Evidence + v2 空白 Decision，不提供 A 的决定/文字总结、旧 Codex、SAFE 风险表、候选强度 tier 或本条事后分析。真实独立执行方可以如实声明 `independent_execution_attested=true`；单独新开聊天**本身不足以证明资格**。
4. Owner 复核 B 的来源字段绑定、v2 结构、审查笔记与执行身份；随后在 A/B 结果均冻结后比较差异。A 未独立，因此 A 与 B 的一致也不能冒充“双独立 Reviewer”；是否需要真正的第二位独立 Reviewer C，由 Owner 的政策门禁决定。B 的判断不得自动复制 A 的 10/10。
5. 有资格的独立裁决形成真实的 Story→semantic_component_id 映射后，使用既有 `src/storyforge_dataset/world_isolation.py` 校验组件与 Train/Validation 冲突；不要自动修改冻结 split 或训练。
6. 继续保持 actual-sent、R50 完整 Protected/Reserved metadata-only 排除、旧曝光集合闭合、其余评测集、Owner Freeze 为独立 HOLD。

## Owner Mac 下一步：Reviewer B 新目录（只读输入 + create-only 输出）

```bash
set -euo pipefail
umask 077
BASE="$HOME/.local/share/storyforge/r60/private"
TOOLS="$BASE/reviewer-tools-git-v2"
INPUT="$BASE/r60-base336-group-cards-opening-20261115"
PACKET="$BASE/R60_BASE336_COMPONENT_REVIEW_PACKET_PRIVATE_V2_20261119.json"
REVIEW_B="$BASE/r60-base336-independent-review-20261119-v2-reviewer-b"
test -f "$TOOLS/r60_independent_reviewer_offline.py"
test -f "$TOOLS/R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json"
test -f "$PACKET" && test -d "$INPUT"
test ! -e "$REVIEW_B" && test ! -L "$REVIEW_B"
python3 "$TOOLS/r60_independent_reviewer_offline.py" prepare \
  --inputs "$INPUT" --packet "$PACKET" --output-dir "$REVIEW_B"
```

正常 `prepare` 回执：`REVIEWER_DOSSIERS_CREATED__DECISIONS_PENDING`、`review_edges=10`、`private_files_created=20`。若现有 Reviewer B 目录已存在，不重跑、不覆盖。

B 完成之后 Owner 运行（从已受控环境可用的 Python）：

```bash
python3 "$TOOLS/r60_independent_reviewer_offline.py" verify \
  --packet "$PACKET" --inputs "$INPUT" --reviews-dir "$REVIEW_B" \
  --schema "$TOOLS/R60_BASE336_INDEPENDENT_EDGE_REVIEW_SCHEMA.json"
```

如 `jsonschema` 缺失，先在私有受控 venv 安装，不能跳过校验。脚本输出 SAFE 聚合而非私有裁决细节。

## 固定门禁

```text
REVIEWER_A_CONTENT_DECISIONS = FILLED_10_OF_10
REVIEWER_A_STATIC_SAME_COMPONENT = 10
REVIEWER_A_REFERENCE_BINDING = VERIFIED_10_OF_10_AS_SAFE_REPORTED
REVIEWER_A_SELF_ATTESTED_INDEPENDENCE = 0_OF_10
REVIEWER_A_STATUS = REVIEW_INCOMPLETE_HOLD
REVIEWER_B = NOT_SUBMITTED
FORMAL_INDEPENDENT_REVIEW = HOLD
HISTORICAL_ACTUAL_SENT = NOT_VERIFIED
R50_COMPLETE_EXCLUSION = HOLD
P2_C = HOLD
P2_B_48_PROMPTS = NOT_GENERATED
TRAIN_ADMITTED = 0
QUALITY_V1_ADMITTED = 0
```

本文件是 SAFE 状态记录，不是独立 Reviewer 的正式判断或 Owner 冻结。
