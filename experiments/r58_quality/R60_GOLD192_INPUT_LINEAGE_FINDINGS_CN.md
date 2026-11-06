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


## 9. 2026-11-07 Strict Stage 与 Owner Template 执行续记

本节根据 Owner Mac 返回的 SAFE 聚合结果和文件元数据追加。没有读取或写入私有案例正文。

### 9.1 Strict Stage 本轮复核

Owner Mac 本地脚本对实际 Source Context、Stage JSONL 和 Stage SAFE 做了字节级核验，返回：

- `STRICT_STAGE_BYTE_AND_COUNT_VERIFIED`
- source_rows = 72
- 实际 JSONL READY = 5
- 实际 JSONL HOLD = 67
- unique case IDs = 72
- source pin match = true
- staged pin match = true
- Quality-v1 admission = 0

该结果满足 Strict Stage 重建门槛。仍不代表 5 条案例已获得 Owner 审批或 Quality-v1 准入。

### 9.2 Owner Template 产物实际已成功创建

Owner Mac 随后对模板产物进行只读检查：

| 项目 | 结果 |
|---|---:|
| Template SAFE status | `OWNER_EVIDENCE_TEMPLATE_CREATED__NOT_EVIDENCE` |
| staged_candidates | 5 |
| template_rows | 5 |
| 实际 JSONL rows | 5 |
| template 目录 mode | 0700 |
| 两个模板文件 | regular、非 symlink、mode 0600、nlink 1 |
| Stage / Source pins | 全部匹配 |
| READY identity 对应 | 5/5 |
| 审批 / evidence / attestation 字段 | 全部保持 null |
| Quality-v1 admission | 0 |

因此，模板创建本身是成功的。模板只是空白 Owner 工作表，不是 Owner Evidence、审批或训练授权。

### 9.3 命令回执 HOLD 的时间线根因

另一个文件 `OWNER_TEMPLATE_COMMAND_OUTPUT_PRIVATE.json` 当前显示：

`OWNER_EVIDENCE_TEMPLATE_HOLD`

该命令输出没有 `reason_code`。原因是 `r59_owner_evidence_template.py` 的 CLI 异常处理会捕获异常并只输出通用 HOLD，不暴露具体异常原因。

Owner Mac 返回的 UTC mtime（由纳秒时间戳换算）：

| 文件 | mtime (UTC) |
|---|---|
| Strict Stage JSONL | 2026-11-06 16:52:50.304048 |
| Strict Stage SAFE | 2026-11-06 16:52:50.347959 |
| Owner Template JSONL | 2026-11-06 16:53:22.127939 |
| Owner Template SAFE | 2026-11-06 16:53:22.128388 |
| Template command output | 2026-11-06 17:05:21.060182 |

command output 比已经成功创建的模板文件晚约 11 分 59 秒。结合执行轨迹在 template 命令处因 `set -e` 停止，以及模板工具的 create-only 语义（输出目录已存在会触发 `OUTPUT_EXISTS`），最符合现有证据的解释是：**第一次模板创建已成功；之后再次运行模板命令，因输出目录已存在而返回通用 HOLD，并通过 shell 重定向覆盖了 command output 文件。**

这是由时间顺序和工具实现共同支持的高置信度解释，但因为 CLI 没有输出 reason code，不能声称捕获到了原始异常文本或确定的错误码。保留 HOLD 回执作为重复执行记录，不删除、不覆盖、不重建已经成功的模板产物。

### 9.4 下一步执行规则

1. 保留现有 Strict Stage 与 Owner Template 目录，不重跑 Stage 或 Template create-only 命令。
2. 先只读检查 Packet、Reviewer A、Reviewer B 文件是否存在、权限是否为 0600、nlink 是否为 1；并检查 AutoLink 输出目录不存在。
3. 确认 Owner Template SAFE 为 `OWNER_EVIDENCE_TEMPLATE_CREATED__NOT_EVIDENCE`，5 行身份与 Stage READY 5/5 对应，Stage/Source pins 匹配。
4. 仅运行一次 `r59_owner_evidence_autolink.py`，输出到全新 create-only 目录。该步骤只建立冻结 Packet / A / B 的精确证据定位符，不创建 Owner attestation。
5. AutoLink SAFE 必须明确保持 `owner_attestations_created=0`、`reviewer_independence_proven=false`、`world_component_isolation_proven=false`、`protected_set_completeness_proven=false`、`quality_v1_admitted=0`、`training_authorized=false`。
6. AutoLink 完成后仍不运行 Preflight、Review Bind 或 Quality-v1；先由 Owner 根据真实证据补全来源版本、世界身份、split、严重问题判断、保护集和独立性证据。
7. 不触碰 R50，不修改生产 B2，不执行 DDL/DML，不启动 GPU，不自动合并 PR。

**当前门禁：** `STRICT_STAGE_VERIFIED__OWNER_TEMPLATE_CREATED__AUTOLINK_PENDING`。


## 10. 2026-11-07 Owner Evidence AutoLink 验收续记

本节记录 Owner Mac 对已存在 AutoLink 目录的只读核验。没有重新运行 AutoLink，也没有修改任何私有文件。

### 10.1 已存在产物验收通过

AutoLink 目录不是符号链接，目录权限为 0700。其两个产物均为 regular file、非 symlink、mode 0600、nlink 1：

- `OWNER_EVIDENCE_AUTOLINK_SAFE.json`
- `OWNER_CASE_EVIDENCE_AUTOLINKED_PRIVATE.jsonl`

SAFE 聚合结果：

| 指标 | 结果 |
|---|---:|
| status | `OWNER_EVIDENCE_LOCATORS_AUTOLINKED__OWNER_REVIEW_STILL_REQUIRED` |
| staged_candidates | 5 |
| packet_exact_matches | 5 |
| reviewer_a_exact_matches | 5 |
| reviewer_b_exact_matches | 5 |
| owner_attestations_created | 0 |
| source_version_verified | false |
| historical_snapshot_temporality_proven | false |
| reviewer_independence_proven | false |
| world_component_isolation_proven | false |
| protected_set_completeness_proven | false |
| quality_v1_admitted | 0 |
| training_authorized | false |

JSONL 只读检查：5 rows、5 unique case IDs，Reviewer A / Reviewer B / Packet 三类 evidence locator 均存在。

### 10.2 前一轮 shell 为什么停止

前一轮 `run.sh` 在 `test ! -e "$AUTOLINK"` 处停止，是因为 AutoLink 输出目录已经存在。该命令在 AutoLink 程序启动前执行；这次只读检查发现该目录内已有完整 SAFE 和 JSONL，且两者相互符合 SAFE 所述的 5 条关联结果。

因此，前一轮脚本停止不代表 AutoLink 失败。**现有 AutoLink 结果验收通过，不得再次运行 AutoLink，不得删除或覆盖其输出。**

### 10.3 AutoLink 的语义边界

AutoLink 只为 Strict READY 的 5 个案例建立冻结 Packet、Reviewer A、Reviewer B 的精确证据定位符，并记录 Packet case / world-card snapshot 指纹。它明确不证明：

- Packet snapshot 是历史原始 source version；
- 审核快照的时间真实性或历史时点；
- Reviewer A/B 的身份独立性或盲审独立性；
- World component 的完整隔离；
- protected / held-out 集合完整性；
- Owner 对严重问题、版权、隐私、来源版本或质量的审批。

Reviewer refs 是定位符，不是独立性证明。World-card snapshot 不是 historical source version。不得把这些 locator 或 snapshot fingerprint 当作 Owner attestation。

### 10.4 Owner 真实证据补充字段

后续 Owner 只能根据真实可追溯证据填写 AutoLink JSONL 的副本，不能修改冻结 Stage、Template 或 AutoLink 原件。至少需要逐案例核实：

1. `source_version_sha256`：原始 Gold source version 的 SHA，不得用 Source Context / Stage / Packet SHA 代替。
2. `world_graph_sha256`、`world_component_id`：实际世界图谱版本和组件归属。
3. `split`：只能是 `train` 或 `validation`，必须有来源证据和跨世界冲突检查。
4. `owner_supplemental_severe_flags`：`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion` 三项均由 Owner 逐项判断为布尔值；不得将未知写成 false。
5. `owner_supplemental_severe_evidence_ref`：Owner 严重问题专项检查的私有证据定位符。
6. `evidence` 正向项全部需要真实证据支持为 true：`rights_attested`、`source_version_verified`、`context_is_coherent`、`context_no_future_leakage_reviewed`、`privacy_checked`、`world_component_reviewed`、`known_protected_metadata_checked`、`other_known_reserved_metadata_checked`、`final_heldout_metadata_checked`、`reviewers_blinded_and_independent_attested`、`owner_quality_approved`。
7. 以下负向风险字段必须由核查证据支持为 false：`known_protected_overlap`、`final_heldout_overlap`、`protected_test_body_accessed`。未知状态不得填 false。
8. Reviewer A/B refs 已由 AutoLink 提供，但仍需单独取得独立性证据；不能仅凭两个不同文件或两个不同 locator 声称 independent。

### 10.5 Preflight 与 Binder 的门禁边界

- Preflight 是字段完整性门禁，不验证证据真实性，也不证明 Reviewer independence / protected-set completeness。
- 只有 Preflight `rows_with_all_required_fields_present > 0` 才可考虑 Review Bind；如果为 0，继续 HOLD。
- Binder 还会独立检查冻结 A/B 与 exclusions 的 SHA pin、192 条 A/B 覆盖、11 条 exclusions、case-level A/B 分数、Reviewer B PASS / severe flags、Owner supplemental severe screen、来源与世界版本 pin、split、正向/负向 evidence 以及 Stage/Source pins。
- Binder 输出即使有 `review_bound_candidates > 0`，也只是 `REVIEW_EVIDENCE_BOUND__CANDIDATES_NOT_ADMITTED`，Quality-v1 admission 仍为 0。
- Quality-v1 自身声明不能判断文学质量、不能认证 Reviewer 身份，也不能证明 protected-world registry 完整。不能因为脚本结构 PASS 就自动授权训练。

### 10.6 当前门禁

**`STRICT_STAGE_VERIFIED__OWNER_TEMPLATE_CREATED__AUTOLINK_VERIFIED__OWNER_EVIDENCE_PENDING`**

不得重跑 Stage、Template 或 AutoLink；不得提前运行 Preflight / Binder；不触碰 R50，不修改生产 B2，不执行 DDL/DML，不启动 GPU，不自动合并 PR。


## 11. 2026-11-07 Owner 声明证据可用；下一阶段执行计划

Owner 已明确反馈：五条 Strict READY 案例所需的原始 Gold 来源、世界图谱登记资料、Reviewer A/B 原始审核过程记录均可找到。此处是 Owner 对材料可用性的声明，**不是材料内容、完整性、身份映射或真实性已通过独立核验的结论**。

### 11.1 当前门禁保持不变

- Strict Stage：72 total / 5 READY / 67 HOLD，字节及 receipt pin 已在 Owner Mac 核验。
- Owner Template：5 rows，仍是空白模板，不是审批。
- AutoLink：Packet / Reviewer A / Reviewer B locator 均 5/5；Owner attestations = 0。
- Owner Evidence complete rows：尚未运行新 Preflight，当前不能宣称有 complete row。
- Quality-v1 admission = 0；training_authorized = false；gpu_started = false；r50_accessed = false；database_modified = false。

### 11.2 阶段 A：五条 READY 的证据索引与原始来源核验

Owner 在本机为每条 READY 建立独立证据索引，至少包含：

1. 原始 Gold archive / source 文件的稳定私有引用、原始版本 SHA256、版本/归档元数据。
2. 能将该原始版本精确映射到当前 case / target 的 provenance 证据；不能只凭相似文本或 Stage SHA 关联。
3. 来源版本创建/冻结时间与对话、审核时间的时间顺序证据。
4. 原始 world graph 文件/快照的版本 SHA256、world_component_id，以及从 case 到 component 的可复核映射。
5. Train/Validation split 的原始登记依据和完整组件级冲突检查。
6. Reviewer A/B 原始身份/角色、独立分派记录、盲审访问边界、提交时间、修改历史或审计记录。
7. Gold / reserved / protected / final-heldout registries 的版本与完整性依据；检查 metadata overlap，且确认没有读取 protected test body。

历史 `R59_GOLD192_SOURCE_INVENTORY_SAFE.json` 曾有 5/5 pins found，但当时 `archive_inspection=false` 且 verification HOLD。不得将旧的 pin discovery 当成原始归档真实性证明；必须完成 archive inspection 与 case-level provenance 核验。

阶段 A 输出仅为本地私有 evidence index / manifest 与不含案例 ID、路径、正文或原始 SHA 的 SAFE 聚合报告。任何 source version、world mapping、历史时间或 Reviewer 独立性不明的案例继续 HOLD。

### 11.3 阶段 B：Owner 对 5 条案例逐项实质审查

只对阶段 A 中有足够来源证据的案例进行 Owner review。每个案例分别核验：

- 权利与使用授权；
- 原始来源版本真实性；
- 上下文连贯性和 future leakage；
- 隐私与安全；
- world component 与 split；
- known protected / reserved / final-heldout metadata overlap；
- protected test body access boundary；
- 11 项正向 evidence；
- 3 项负向 evidence；
- Owner supplemental severe flags：`serious_player_agency`、`hard_fact_or_ban`、`safety_exclusion`；
- 对应的专项审核 evidence ref。

未知不得填默认值。正向 evidence 只有在证据支持时填 true；负向 overlap/access 项只有在有核查证据支持时填 false；严重问题 flag 必须由 Owner 逐项判断，不能用缺少记录推断 false。发现任何严重问题时按真实结果记录，不能为了让 Binder 通过而把 true 改为 false。

Reviewer A/B 的原始过程记录用于验证实际主体、独立分派、盲审和时间线；AutoLink refs 仅是定位符。若两人共享了彼此的评分/结论，或无法证明审核时互不可见，则 `reviewers_blinded_and_independent_attested` 不得填 true。

### 11.4 阶段 C：Owner 工作副本、Preflight 与复核

- 冻结 Stage、Template、AutoLink 原件；只编辑 AutoLink JSONL 的独立 Owner work copy。
- 每个 Owner 字段必须能回指本地 evidence index 中的真实证据。
- 核验 5 条 case identity、target SHA、story/session identity、staged-file SHA、source-context SHA 与当前 Strict Stage 精确匹配。
- 运行 `r59_owner_evidence_preflight.py`，只回传 SAFE 聚合字段。
- Preflight 的 `rows_with_all_required_fields_present > 0` 是考虑 Binder 的必要条件，不是证据真实性或准入结论。
- 若完整行数为 0，依据 `field_checks_missing` 补充真实证据或保持 HOLD；不得填默认值。
- Preflight 声明 `reviewer_independence_independently_proven=false` 与 `protected_set_completeness_independently_proven=false`，这两项必须由独立证据审查另行解决。

### 11.5 阶段 D：Review Bind 与 Quality-v1

仅在 Owner 证据已经完整、Preflight 至少有 complete row，且 Reviewer independence 与 protected registry completeness 有独立证据支持后，才进入 Binder 评估。Binder 必须按代码固定 SHA 验证 Reviewer A、Reviewer B、11 条 Exclusions 的冻结输入、192 条 A/B 覆盖、case-level scores、Reviewer B PASS / severe flags、Owner severe screen、source/world/split/evidence 与 Stage pins。

Binder 的候选输出状态是 `REVIEW_EVIDENCE_BOUND__CANDIDATES_NOT_ADMITTED`，不等于 Quality-v1 admission。随后 Quality-v1 只执行结构评估；其自身明确不能认证 Reviewer 身份、不能判断文学质量、不能证明 protected-world registry 完整。任何 HOLD / REJECT 均按原样保留。

### 11.6 本阶段需要 Owner 提供的唯一回传

每轮只回传：
- evidence inventory 的 SAFE 聚合统计；
- 每类证据的 verified / unresolved 数量；
- 5 条案例的 source/world/split/reviewer coverage 计数；
- Owner severe flags 的 PASS/HOLD/REJECT 聚合；
- Preflight field_checks_passed / field_checks_missing 聚合；
- 保护状态字段。

不回传案例 ID、故事正文、原始 SHA、私有路径、Reviewer 个人身份信息、DSN 或 Token。必要时只用稳定的本地私有 evidence refs 在本机关联。

### 11.7 不变的硬约束

不重跑 Gold72；不修改 Strict Stage / Template / AutoLink 原件；不触碰 R50；不修改生产 B2；不执行 DDL/DML；不启动 GPU；不自动合并 PR。每个证据未知、来源不明、时间关系不明、世界冲突未排除、Reviewer independence 不明、protected-set completeness 不明的案例保持 HOLD。

**下一阶段门禁：** `OWNER_EVIDENCE_SOURCE_WORLD_REVIEWER_INVENTORY_PENDING`。
