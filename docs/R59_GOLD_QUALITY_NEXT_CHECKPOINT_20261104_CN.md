# R59 Gold Quality-v1 主线进展检查点（2026-11-04）

## 1. 已实证完成：五条工程 Preview

- HF CPU Job：`adradar/6aea99060e0338d1bb7f8350`，状态 `COMPLETED`。
- Job 日志验证：`R59_CONTEXT_WINDOW_VALIDATION_PASS`、`R59_PRIVATE_OUTPUT_PERSISTED`。
- 读取私有 Bucket 内 SAFE JSON，状态为 `R59_CONTEXT_WINDOW_AND_COLLATOR_PASS__NOT_ADMITTED`。
- 输入五条、重建五条、无 UNFIT；实际 ms-swift `last_round` Collator 5/5 PASS，16,384 Token 上限，Qwen 固定 revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。
- 私有 Bucket 已存在 `R59_SFT_CONTEXT_WINDOW_PRIVATE.jsonl`（291,121 bytes）和 `R59_SFT_CONTEXT_WINDOW_SAFE.json`（1,926 bytes）。两文件在 `preflight/r59/20261104/reports/context-window-mac-01/context-window-mac-01/` 下。
- Owner Mac `hf buckets sync` 报告下载两份文件、本地 SAFE 验证通过。本地计算的 SHA256：PRIVATE `876a6eaee90e64a9e5da9f6faf0814e2410fb0205e74206d8107ab0c6311c7fe`；SAFE `22c2f737db980a5b0db10b572fb1a1ed6ee5028bb8cd3c16b3b4e69143edfa5a`。这两个是 Owner 上报的本地哈希，尚未独立从 Bucket 计算校验。
- 原始 Preview 保持只读，R50 未访问，GPU 未启动，没有训练。

以上是**工程输入格式验证**，不得升级解释为审美质量、数据归属独立性、世界隔离、训练准入或冻结证据。

## 2. 当前 Gold 主线的数量边界

依据现有 Owner SAFE/PR 文档所报告的状态：
- Source Priority72：72 行中仅 5 行进入 Source Stage 可审核状态；其他 67 行为结构 HOLD。尚无逐案可恢复性判定。
- 五条候选已与冻结 Reviewer A/B 的结构及 Gold192 Story Review Packets 精确关联，其中先前报告 3 条匹配 Strict28。
- Owner Evidence 初次预检为身份和 staging/source pin 5/5 匹配，其他实质性 Owner 必需证据为 0/5；不能把 A/B 定位符视为相互独立审核证明。
- `quality_v1_admitted=0`、`dataset_frozen=false`、`training_authorized=false`。

## 3. 下一步的两个并行但相互隔离的任务

### A. 五条候选：先核对 Owner Evidence，不凭空补字段

按 `docs/R59_GOLD_QUALITY_V1_SFT_CANDIDATE_COMPILE_CN.md` 的命令，在 Owner 私有工作区运行 `r59_owner_evidence_preflight.py`。优先使用已经自动关联的 `OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl` 工作副本（如存在），不覆盖冻结证据文件。只上传 SAFE 聚合回执；不把正文、Case ID、世界 UUID、源文件内容或逐案哈希写到 GitHub/聊天。

若 `rows_with_all_required_fields_present=0`，保留 Review Bind 和 SFT 候选准入 HOLD。只补充已真实核实的质量、安全和归属信息，未知保持 null。既有批准的 R27 无世界卡 System 不等于世界卡史料核实，也不能替代 Owner 质量判断。

### B. 其余 67 条：先做结构阻塞分类

读取已有 `GOLD_SOURCE_STAGING_SAFE.json` 和 72 条候选的本地私有状态，聚合各 `reason_code` 及样本数量。优先修复可恢复的非语义结构错误（缺少字段、消息链断裂、目标角色位置不合规、源索引缺失等），但不能伪造上下文或用后期快照填补历史信息。不得把修复造成的来源改变解释成旧来源精确回放 PASS。

如果这些 67 条不能在已有证据下恢复，保留 HOLD 并寻找新的原始 Gold 候选，避免反复投入不可恢复的历史数据库定位。

## 4. 工程 Token 化应放在质量审核之后

先完成真实 Owner/Reviewer 质量准入与 Train/Validation 世界隔离，再冻结私有审核候选；之后才将经批准的训练输入应用已验证的连续历史后缀 16K 重建策略，并对 **最终冻结的 Train/Validation 精确字节** 在 HF CPU 上重跑 Tokenizer + ms-swift Collator。

禁止将现有五条工程 Preview 作为自动批准的训练集。禁止自动启动 GPU。

## 5. 下一次需要的最小 SAFE 回执

- `r59_owner_evidence_preflight.py` 的 SAFE 聚合结果：`staged_ready`、`identity_matched`、`rows_with_all_required_fields_present`、`field_checks_missing`。
- 原有 Source Stage SAFE 中的状态计数及其原因分布（不含私有文本/身份）。
- 如有 AutoLink SAFE，报告 `reviewer_a_exact_matches`、`reviewer_b_exact_matches`、`packet_exact_matches`，并明确定位符不等于独立审核证明。

以上回执决定下一步是 Review Bind、可恢复结构修复，还是补充真实 Owner 审核。此检查点不更改既有审核准入策略。

## 6. 2026-11-04 新回执：67 条共享 HISTORY_STRUCTURE_INVALID

Owner 报告 Source Stage SAFE：`source_rows=72`、`context_staged=5`、`context_structure_hold=67`，结构 HOLD 原因全为 `HISTORY_STRUCTURE_INVALID`。Owner Evidence 预检：`identity_matched=5`、`rows_with_all_required_fields_present=0`，Owner 必填字段全部未核实；本阶段不执行 Review Bind。

检查 `gold_source_context_stage.py::_history` 后确认，此错误码把以下多个条件合并在一起：消息必须为对象、角色只允许 user/assistant、角色不可连续相同、文本非空、`status == "completed"`。从现有聚合结果**无法断言**是哪一项触发 67 条 HOLD。

新工具 `r59_history_structure_diagnostic.py` 在本机只读原始 R59 Source Context，按违规原因聚合**涉及的候选数量**，另统计消息状态大类。一次候选可同时计入多个原因，故计数不能相加为 67。不会打印私有文本、ID、源路径或完整 status 原始字符串。

在 PR #11 最新代码的仓库根目录下运行：

```bash
set -euo pipefail
PRIVATE="$HOME/.local/share/storyforge/r59/private"
SOURCE="$(find "$PRIVATE" -type f -name 'R59_SOURCE_CONTEXT_PRIVATE.jsonl' -print -quit)"
test -n "$SOURCE"
.venv/bin/ruff check experiments/r58_quality/r59_history_structure_diagnostic.py experiments/r58_quality/test_r59_history_structure_diagnostic.py
.venv/bin/python -m unittest discover -s experiments/r58_quality -p 'test_r59_history_structure_diagnostic.py' -v
.venv/bin/python experiments/r58_quality/r59_history_structure_diagnostic.py --source-context-jsonl "$SOURCE"
```

只有在看到诊断分布后才能决定是否修改 Stage。若 67 条主要是 status 非 `completed`，要查明该状态的实际业务含义，并确保只选合法完成消息；不得直接剥离 status 或自动批准未完成对话。若主要为 `REPEATED_ROLE`，不得静默合并/删去消息；应回源检查消息流和边界是否确实有合法的原样历史。所有修改仅限明确可验证的结构等价变换，并需回归测试。诊断本身不能提高 `quality_v1_admitted`。
