# R60 Gold192 输入谱系查证记录（2026-11-07）

> 本文记录 Owner Mac 在固定代码基线 `c071784b135c934bfe29537761300c14aa2cd818` 上完成的只读输入谱系审计。目的是让后续 Agent 直接复用已确认事实，不重复定位相同文件或重新解释 72 READY / 67 violations 的差异。
>
> 本文不包含私有 JSONL、案例 ID、故事正文、DSN、Token 或原始文件 SHA256。私有文件只用稳定的本机相对路径标识。

## 1. 审计基线与执行边界

- 仓库：`sunxu/storyforge`
- Worktree：`storyforge-r60-ledger-diagnostics`
- 分支：`r60/gold72-disagreement-reviewer-c`
- HEAD：`c071784b135c934bfe29537761300c14aa2cd818`
- 上游：`origin/r60/gold72-disagreement-reviewer-c`
- 审计时工作区：clean，分支与上游一致
- 审计类型：只读；未运行数据库操作，未修改私有源文件或 Stage 文件
- 保护状态：`gpu_started=false`、`r50_accessed=false`、`database_modified=false`、`private_values_emitted=false`

本地 SHA256（用于确认后续复现时脚本版本一致；不是 Git blob SHA）：

| 脚本 | 本地 SHA256 |
|---|---|
| `experiments/r58_quality/r59_history_structure_diagnostic.py` | `3b0f151f4c54f81f9abe51bdf7310b9c61124ac412580a603989ea4fcc371749` |
| `experiments/r58_quality/r59_owner_evidence_preflight.py` | `8efc891ea7e6ae1a93fb435973909f00655bec4776b5adf8945264114f41777c` |
| `experiments/r58_quality/gold_source_context_stage.py` | `4ed892244036ae9f2cc6b42145ad2e0966ac63f90c299cc7df1e080fb0ed4abd` |
| `experiments/r58_quality/r59_staging_receipt.py` | `a65b8910ed25e087369e8616f5953eb4fa1b7b2b2886325f060d0b20fffa211f` |

## 2. Source Context 候选文件已定位

根目录别名：

`$PRIVATE = ~/.local/share/storyforge/r59/private`

| 别名 | 相对路径 | 大小 | mtime (UTC) | 只读审计结论 |
|---|---|---:|---|---|
| priority72_1103 | `r59-source-priority72-20261103/R59_SOURCE_CONTEXT_PRIVATE.jsonl` | 127,689,101 bytes | 2026-11-02 20:14:01.678620 | 72 rows；重跑 History Diagnostic 后与既有 History SAFE 的全部聚合统计一致 |
| pilot7 | `r59-source-pilot7/R59_SOURCE_CONTEXT_PRIVATE.jsonl` | 8,610,053 bytes | 2026-11-02 19:34:56.268358 | 7 rows；不匹配既有 History SAFE |
| pilot8 | `r59-source-pilot8/R59_SOURCE_CONTEXT_PRIVATE.jsonl` | 11,845,103 bytes | 2026-11-04 18:19:56.095978 | 8 rows；不匹配既有 History SAFE |
| pilot8_paged | `r59-source-pilot8-paged-20261105/R59_SOURCE_CONTEXT_PRIVATE.jsonl` | 11,845,103 bytes | 2026-11-05 05:17:53.981103 | 8 rows；不匹配既有 History SAFE |

其他文件安全属性均通过审计：regular file、非 symlink、mode 0600、nlink 1。

**已确认的重复文件：** `pilot8` 与 `pilot8_paged` 字节完全相同。它们是同一内容的两个副本，不是两份独立数据证据。两者均与 72-row History SAFE 不匹配。

**重要边界：** 既有 History SAFE 不保存 Source Context SHA。因此，priority72_1103 与既有 SAFE 的关系是“重跑后全部聚合统计一致”，不是“历史 SAFE 中保存了该输入 SHA 的密码学绑定”。不要把统计指纹一致升级表述为历史输入链已被 SHA 证明。

## 3. History Diagnostic 的实际结果

既有文件：

`$PRIVATE/quality-v1/r60-next-gates-20261106.2oM4ET/R59_HISTORY_STRUCTURE_DIAGNOSTIC_SAFE.json`

- 文件大小：619 bytes
- mtime：2026-11-06 08:20:15.030941 UTC
- mode 0600、regular、非 symlink、nlink 1

对 `priority72_1103` 使用固定基线的 History Diagnostic 重跑，结果与既有 SAFE 的以下字段全部一致：

| 指标 | 结果 |
|---|---:|
| source_rows | 72 |
| cases_with_violations | 67 |
| cases_without_violations | 5 |
| CONTENT_EMPTY_OR_INVALID | 67 |
| STATUS_NOT_COMPLETED | 67 |
| REPEATED_ROLE | 33 |
| completed message statuses | 138,058 |
| other_string message statuses | 930 |

违规类别按 case 统计且可重叠；不能把 67 + 67 + 33 相加当作违规案例总数。67 是有至少一项违规的案例数，5 是无违规案例数。

pilot7、pilot8、pilot8_paged 分别为 7、8、8 行，均不匹配上述 72-row 结果。

## 4. 两份历史 Stage 的差异已被定位

### 4.1 原始 priority72 Stage（2026-11-03）

目录：

`$PRIVATE/source-staging-priority72-20261103/`

文件属性：

- `GOLD_SOURCE_STAGING_PRIVATE.jsonl`：823,371 bytes，mtime 2026-11-03 08:15:19.946087 UTC
- `GOLD_SOURCE_STAGING_SAFE.json`：883 bytes，mtime 2026-11-03 08:15:19.991116 UTC
- 目录 mode 0700；两个文件均为 regular、非 symlink、mode 0600、nlink 1

receipt 与 JSONL 的 staged-file SHA 匹配；receipt 的 source-context pin 唯一匹配 `priority72_1103`。

| 指标 | receipt | 实际 JSONL |
|---|---:|---:|
| source_rows | 72 | 72 |
| context_staged / READY | 5 | 5 |
| context_structure_hold / HOLD | 67 | 67 |
| 总行数 | — | 72 |

这与 History Diagnostic 的 67 violations / 5 clean 相互吻合，是原始 Source Context 经严格 `gold_source_context_stage.py` 结构检查后的结果。

### 4.2 contiguous-suffix Stage（2026-11-04）

目录：

`$PRIVATE/source-staging-suffix72-20261104-v1/`

文件属性：

- `GOLD_SOURCE_STAGING_PRIVATE.jsonl`：31,844,288 bytes，mtime 2026-11-04 03:39:45.846452 UTC
- `GOLD_SOURCE_STAGING_SAFE.json`：1,229 bytes，mtime 2026-11-04 03:39:45.895840 UTC
- 目录 mode 0700；两个文件均为 regular、非 symlink、mode 0600、nlink 1

receipt 与 JSONL 的 staged-file SHA 匹配；receipt 的 source-context pin 唯一匹配 `priority72_1103`。

| 指标 | receipt | 实际 JSONL |
|---|---:|---:|
| source_rows | 72 | 72 |
| context_staged / READY | 72 | 72 |
| context_structure_hold / HOLD | 0 | 0 |
| 总行数 | — | 72 |

### 4.3 为什么同一 Source Context 会出现 5 READY 与 72 READY？

这不是统计矛盾，而是两个不同 Stage 策略的结果：

1. `gold_source_context_stage.py` 的严格 `_history()` 检查要求**完整原始 history** 中每条消息都是合法 role、role 不连续重复、content 非空、status 为 completed，且最后一条为 user。原始 72 条中只有 5 条满足。
2. `r59_contiguous_suffix_stage.py` 是另一个“最长连续有效后缀”重建工具。它从最后一条有效 user 消息向前扫描，只保留连续、非空、completed、user/assistant 交替的尾部后缀；前面的历史前缀会被排除，再对投影后的 history 调用 `stage_source()`。
3. suffix 工具在输出每行中记录 `history_suffix_provenance`，包括原始 history hash、原始/保留消息数、排除的前缀消息数、保留后缀 hash 和选择策略 `LONGEST_COMPLETED_NONBLANK_ALTERNATING_SUFFIX`。
4. suffix receipt 明确标记 `temporal_or_semantic_validity_proven=false`。因此 72 READY 只说明 72 个**投影后后缀**通过结构 Stage，不代表 72 个**完整原始历史**通过严格结构验证，也不证明时间真实性、语义连续性或训练资格。

原始 Source Context 没有被改写；但 suffix 输出确实是不同的历史输入视图，不能与原始完整 history 等同。

## 5. 旧 Owner Evidence Preflight 的输入问题

既有文件：

`$PRIVATE/quality-v1/r60-next-gates-20261106.2oM4ET/OWNER_EVIDENCE_PREFLIGHT_SAFE.json`

- 文件大小：2,617 bytes
- mtime：2026-11-06 08:20:14.653275 UTC
- mode 0600、regular、非 symlink、nlink 1

SAFE 聚合值：

| 字段 | 结果 |
|---|---:|
| status | OWNER_EVIDENCE_PREFLIGHT_HOLD |
| staged_ready | 72 |
| owner_rows | 72 |
| identity_matched | 72 |
| rows_with_all_required_fields_present | 0 |

其 mtime 比 History SAFE 早约 0.38 秒。两份 SAFE 位于同一个 next-gates 目录，但**同目录和相近时间不能证明它们使用了同一份输入**。

Preflight SAFE 不记录实际 staged JSONL SHA、staging receipt SHA、source-context SHA 或输入路径。因此，不能从该 SAFE 本身反向证明它读取了哪份 Stage 文件。

本机发现的唯一 72-row / 72-READY 历史 Stage 候选是 `source-staging-suffix72-20261104-v1`，其输出与旧 Preflight 的 `staged_ready=72` 相符；因此它是最有力的解释候选，但由于旧 Preflight SAFE 没有输入 SHA，仍不能宣称已经完成密码学级的历史输入绑定。

## 6. 代码层面的关键机制

固定基线代码：

- `gold_source_context_stage.py`：严格检查完整 history；违规行输出 `SOURCE_STRUCTURE_HOLD`，不会伪装成 READY。
- `r59_contiguous_suffix_stage.py`：执行最长连续有效后缀投影；这是一种历史上下文重建策略，不等同于完整 history 严格验证。
- `r59_owner_evidence_preflight.py`：只按 staged 行的 READY schema/status 筛选，再检查 Owner Evidence 字段和身份匹配；它本身不重新验证完整 history。
- `r59_staging_receipt.py`：同时接受旧 source-stage receipt 和 contiguous-suffix receipt。新 suffix receipt 会检查其声明的 staged/hold 计数与若干保护字段，但这不构成完整原始 history 的验证。

因此不能把 `Preflight staged_ready=72` 解释为“72 条完整历史都通过严格 Stage”。

## 7. 后续 Agent 的执行规则（必须遵守）

1. **不要重跑或重新审核 Gold72。** Gold72 Owner 决策和导入证据保持冻结。
2. **不要把旧 suffix72 Stage 当作严格 Source Stage 输出。** 它是后缀投影产物；temporal/semantic validity 未证明。
3. 当前 Gold192 strict path 应以 `priority72_1103` 原始 Source Context 为输入候选，重新核验文件权限、内容数量和 source identity；随后用固定基线的 `gold_source_context_stage.py` 在全新、私有、create-only 输出目录中重建 Strict Stage。
4. 新 Strict Stage 必须同时保存 JSONL 与 SAFE receipt，并在 SAFE 中 pin 原始 Source Context 和 staged JSONL。
5. 运行 Owner Evidence Preflight 时，只能使用新 Strict Stage 的 JSONL 和对应 SAFE receipt。必须额外核对 JSONL 实际 READY 行数等于 receipt 的 `context_staged`，且等于 Preflight 的 `staged_ready`；不一致立即 HOLD。
6. 原有 72-row Owner Evidence 与新 Strict Stage 的身份/文件 pin 不能假定匹配。仅针对新 Strict Stage 的 READY 案例补真实 Owner Evidence；未知字段不得填默认值。
7. `rows_with_all_required_fields_present > 0` 才允许运行 Review Bind。Binder 有候选后才进入 Quality-v1。
8. 来源不明、历史不连续、Reviewer independence 未证明、protected-set completeness 未证明或输入 pin 不匹配，一律 HOLD。
9. 不触碰 R50，不修改生产 B2，不执行 DDL/DML，不启动 GPU，不自动合并 PR。

## 8. 本轮结论

- History SAFE 的 72 / 67 / 5 聚合统计可由 `priority72_1103` 重现。
- 原始严格 Stage 的 5 READY / 67 HOLD 已由实际 JSONL 与 SAFE receipt 相互验证。
- 另有一个 72 READY 的 suffix projection Stage；它通过截取最长有效后缀来恢复结构，不代表完整原始历史通过严格验证。
- 旧 Preflight 的 72 READY 最可能来自 suffix72 Stage，但由于 Preflight SAFE 未保存输入 pin，精确历史输入绑定仍是 **`HISTORICAL_LINEAGE_UNPROVEN`**。
- 当前任务的下一步是重新生成严格 Stage，并以新 Stage 的 JSONL + SAFE receipt 运行 Preflight；不是复用 suffix72 的 72 READY，也不是启动训练。

**最终门禁状态：** `HISTORICAL_LINEAGE_UNPROVEN__STRICT_STAGE_REBUILD_REQUIRED`。
