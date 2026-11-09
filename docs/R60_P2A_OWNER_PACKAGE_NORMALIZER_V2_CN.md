# R60 P2-A Owner-approved package normalizer v2

本版本扩展 v1，严格处理 Owner 已明确采纳的两批 AI Advisory：35 条 NOT_SUPPORTED + 4 条 SUPPORTED。只生成全新私有副本，不覆盖 v1、原始输入或旧审核材料。

## 固定输入

- 原始盲包、20 行 Owner results、60 行 semantic checks、原始 schema。
- 35 行 AI Advisory JSONL + SAFE。
- 4 行 SUPPORTED 历史完整性 worksheet + AI Advisory JSONL + SAFE。

六份关键 JSONL 使用 SHA pin：packet、results、semantic checks、AI35、4-row worksheet、AI4。两个 SAFE 和 schema 也执行严格结构/权限检查。所有私有文件 0600，输入目录及输出父目录 0700。

## Owner 已批准范围

- 35 条 NOT_SUPPORTED：Player Agency 16、Safety 19；保持原 verdict。
- 4 条 SUPPORTED：全部 Player Agency；保持原 verdict。
- 合计 39 条 history_complete 从 false 变为 true。
- Verdict changes=0，semantic rechecks=0。
- 不扩大到任何其他维度或案例。

## 4 条 SUPPORTED AI Advisory 合同

每行必须精确绑定 worksheet 的原始 result_row、calibration_id、dimension、current_verdict、current_assessment 和 current_semantic_check；必须标记 `reviewer_type=AI_ADVISORY_NOT_OWNER`，推荐 `CONFIRM_HISTORY_COMPLETE_AND_KEEP_SUPPORTED`，`owner_review.history_completeness_confirmed=true`，不得建议改 verdict 或重新语义复核。四行必须保持原顺序 [5, 6, 11, 19]。SAFE 必须声明 4 条全覆盖、SUPPORTED 4 条、推荐分布 4/0/0、未冒充 Owner 最终裁决。

## SHA pin 文件

创建私有 JSON，六个键必须精确如下（以下为当前冻结输入的预期 SHA-256）：

```json
{
  "OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl": "3ef24edbf070a1d4579e3d583ae3149254c2acbe242c6b3306869526f524d7c8",
  "OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl": "21ffa40b4e35e3587bfa6eb790f4ae7f3c791a423c93b615a26b42b606c840ed",
  "OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl": "038e069a35510cc4fd1bfcb7deec3c69a99e2d93f596617b37f7a689b969336a",
  "OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_PRIVATE.jsonl": "6c0141009b8f4efa0b1d63b752ebbaefbe084b75122e6481de1d930965b54067",
  "OWNER_SUPPORTED_HISTORY_COMPLETENESS_REVIEW_4_PRIVATE.jsonl": "ac45a2ca9ca7b0d3c6711d5b6211263dc6a656fc49529c60f5bd7fc9d6dfdec2",
  "OWNER_SUPPORTED_HISTORY_COMPLETENESS_AI_REVIEW_4_PRIVATE.jsonl": "bf291fba640ab43ca7ec9f057fbf163cdcae4ca9f5f2f47799ec5981dc4dcf4a"
}
```

SHA pin 文件本身放在 Owner 私有目录，权限 0600，不得提交 GitHub。

## 执行

```bash
python3 scripts/r60_owner_approved_package_normalizer_v2.py \
  --repo-root "$PWD" \
  --source-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109-owner-approved-v2" \
  --expected-sha256-json "$HOME/.local/share/storyforge/r60/private/p2a-input-sha256-v2.json" \
  --owner-approved
```

输出目录必须此前不存在。v2 会先校验全部输入、35+4 条建议和精确 pair set；然后在内存运行完整原版 verifier；通过后 create-only 写入新目录，并调用未修改的官方 CLI verifier。

## 成功验收

- cases_verified=20
- semantic_checks_verified=60
- history_completeness_confirmed=39
- target_locators_normalized=60
- history_locators_normalized=20
- verdict changes=0
- 原始 semantic checks SHA 不变；派生包只补充 60 行 reviewer_role/ref 元数据，语义结论、证据索引、理由和所有原 HOLD 保持不变
- 原始 SHA 不变
- quality_v1_admitted=0
- training_authorized=false
- gpu_started=false

任何输入 SHA、行序、ID、维度、verdict、SAFE 或权限不匹配均停止，不得放宽 Rubric 或覆盖已有文件。

### 新增 HOLD 说明：SUPPORTED rule_basis 类型不匹配

实际诊断发现 4 条 SUPPORTED / Player Agency 的原始 `basis_type=player_agency`，但 Rubric v2.1 要求 `player_agency_boundary`。Normalizer v2 只允许对 Owner 已批准的 history completeness 字段和 locator 做规范化，不得擅自改写 rule_basis。脚本已增加显式 fail-closed guard：`SUPPORTED_RULE_BASIS_TYPE_REQUIRES_OWNER_REVIEW`。需 Owner 明确批准精确 4 条的派生副本类型标签映射后，才可新增版本化规范化步骤；原始文件不变。


## 2026-11-09 Owner 明确批准：四条 SUPPORTED Player Agency basis_type 派生副本规范化

Owner 已在 ChatGPT 明确批准：仅在派生副本中，将四条 SUPPORTED / Player Agency 的 `rule_basis[].basis_type` 从 `player_agency` 改为 `player_agency_boundary`。

实现约束：
- 只接受 Owner 已批准的 4 个精确 `(case_ref, player_agency)` pair；必须恰好 4 个。
- 每条原始 basis item 必须仍为 `basis_type=player_agency`，否则 HOLD；不得做宽泛替换。
- 仅修改派生 `normalized` 对象的 `basis_type` 字段；原始输入 JSONL 不写入、不覆盖。
- 不修改 `verdict`、`source`、`rule_id`、`rule_version`、`scope`、`applicability`、`coverage_complete`、evidence 或 60 条 semantic checks。
- 输出 Owner approval 私有记录明确写入映射方向、4 条数量、derived-copy-only 和各项未修改断言；SAFE 另报 `basis_type_normalized=4`。
- 完成规范化后仍必须通过 Rubric v2.1 官方 verifier；任何不匹配都 HOLD。

这项批准不代表 P2-A 已 PASS。必须在 Owner Mac 私有目录运行 create-only normalizer，检查原始文件 SHA 不变、派生输出只有批准字段变化，再由官方 CLI verifier 验证完整包。不得将私有正文或 Owner-only crosswalk 上传 GitHub。


### 真实执行验收补充

在上述成功验收列表中另须满足：
- `basis_type_normalized=4`
- 私有 Owner approval 的 `basis_type_normalization.owner_approved=true`
- `approved_pair_count=4`、`normalized_pair_count=4`
- `derived_copy_only=true`
- `original_results_modified=false`
- `other_rule_basis_fields_modified=false`
- `verdicts_modified=false`
- `evidence_modified=false`
- `original_semantic_checks_modified=false`；派生包 `derived_semantic_reviewer_binding_rows=60`；`semantic_conclusions_modified=false`；`semantic_reviewed_evidence_indexes_modified=false`；`semantic_reasoning_modified=false`

执行后必须对比原始与派生 JSONL：除已批准的 39 条 history_complete 断言、既有 locator 规范化以及四条 SUPPORTED Player Agency 的 `basis_type` 映射外，不允许出现其他字段差异。原始输入文件的 SHA-256 必须与执行前完全一致。


### 2026-11-09：60 条 semantic check 缺失 reviewer binding 的修复

Owner Mac 只读诊断：60 行全部缺少 `check.reviewer_role` 与 `check.reviewer_ref`（两者均为 null），其余行数为 60；原文件未修改。此前 Owner 已明确陈述这 60 项是在 20 条独立 Owner 裁决之后由 Owner 完成的语义复核。

Normalizer v2 现对派生 semantic-check 副本执行严格回填：
- `reviewer_role=OWNER_INDEPENDENT`
- `reviewer_ref=owner-independent-r60-p2a-dev20-20261109`
- 必须恰好 60 行；
- 如任何行已有冲突的 role/ref，不覆盖，立即 HOLD；
- 原始 60 行 JSONL 不修改；
- approval 私有记录注明 `RETROSPECTIVE_DERIVED_COPY_METADATA`，SAFE 明确 `cryptographic_identity_attested=false`。

此标识是本轮 Owner 复核的项目内稳定引用，不是密码学身份认证，也不证明 reviewer independence 的密码学真实性。该处理只补齐既已完成的 Owner 复核的缺失元数据，不重新执行或改变任何语义判断。必须继续通过官方 v2 verifier。真实私有包执行前，P2-A 仍 HOLD。


### 2026-11-09 执行输出修正：必须写入派生 semantic checks

Normalizer 在内存中补齐 60 行 reviewer binding 后，必须将 `semantic_checks_derived_raw` 写入新输出目录的 `OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl`，并由官方 CLI 对该派生文件验收。不得把原始 semantic JSONL 再复制到输出包，否则 manifest 与包内文件不一致，官方 CLI 必然 HOLD。

因此：
- 原始 semantic 文件保持原字节及 SHA-256；
- 派生 semantic 文件 SHA 与原始文件不同，唯一允许差异是每行增加 `reviewer_role` 和 `reviewer_ref`；
- 60 条 `conclusion`、`reviewed_evidence_indexes`、`reasoning_summary` 逐字段不变；
- SAFE 应分别报告 `original_semantic_checks_modified=false` 与 `derived_semantic_reviewer_binding_rows=60`，不得用含糊的 `semantic_checks_modified=false` 表述派生文件；
- 输出摘要须提供输入与输出 semantic SHA，便于 Owner 独立比对。


### 2026-11-09：OWNER_SEMANTIC_CHECK_INVALID 的安全诊断修复

此前 Owner verifier 将所有非 `SEMANTIC_ENTAILMENT_NOT_ESTABLISHED` 的语义校验错误统一包装为 `OWNER_SEMANTIC_CHECK_INVALID`，导致无法区分 schema、evidence index 等具体失败类型。

现在仅暴露验证器内部固定的 allowlist reason code：
- `OWNER_SEMANTIC_CHECK_INVALID:SEMANTIC_ENTAILMENT_CHECK_HOLD`
- `OWNER_SEMANTIC_CHECK_INVALID:SEMANTIC_ENTAILMENT_EVIDENCE_INDEX_HOLD`
- `OWNER_SEMANTIC_CHECK_INVALID:SEMANTIC_ENTAILMENT_DIMENSION_HOLD`
- `SEMANTIC_ENTAILMENT_NOT_ESTABLISHED_HOLD`

未知异常统一映射为 `OWNER_SEMANTIC_CHECK_INVALID:UNCLASSIFIED`，绝不回显异常文本或私有输入。新增测试覆盖安全 reason、原有 NOT_ESTABLISHED 语义和未知异常不泄露。

请先更新 Owner Mac worktree 到最新分支 HEAD，再对已生成的派生包运行官方 CLI verifier。该诊断步骤只读现有包，不重新生成、不修改包内文件。将返回的 SAFE reason_code 原样反馈；再针对具体原因修复。禁止直接改 60 条 conclusion、reviewed_evidence_indexes 或 reasoning_summary。


### 2026-11-09：Normalizer 捕获 AdjudicationHold

真实私有包预验证会由 `verify_owner_results` 抛出 `AdjudicationHold`（而不是 `EvidenceHold`）。Normalizer v2 此前只捕获后者，导致前者直接显示 Python traceback。现已同时捕获两类异常，并通过 allowlist 输出稳定 SAFE reason_code；未知原因统一降级为 `OFFICIAL_VERIFIER_ADJUDICATION_HOLD` / `OFFICIAL_VERIFIER_EVIDENCE_HOLD`，不回显异常文本或私有值。

因此，最新代码更新后应重新运行 normalizer（不是对不存在的 OUT 目录运行 verifier）。如果纯验证通过，将 create-only 写出新派生包并自动运行官方 CLI；如果仍失败，将在创建 OUT 前给出安全 reason_code，原始输入不变。
