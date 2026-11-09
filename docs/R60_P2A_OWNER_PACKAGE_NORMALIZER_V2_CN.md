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
- semantic checks 原样保留，所有原 HOLD 保留
- 原始 SHA 不变
- quality_v1_admitted=0
- training_authorized=false
- gpu_started=false

任何输入 SHA、行序、ID、维度、verdict、SAFE 或权限不匹配均停止，不得放宽 Rubric 或覆盖已有文件。
