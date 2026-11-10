# R60 P2-A Owner-approved package normalizer v1

本工具用于 R60 Rubric v2 Owner adjudication 的 **20 results / 60 semantic checks** 私有包。它把 Owner 明确批准的 AI Advisory recommendation 应用到独立副本，并规范化旧版 evidence locator 元数据；原始输入只读。

## 安全边界

- 必须显式传入 `--owner-approved`。该参数表示操作者已在 ChatGPT/Owner 流程中明确确认采纳全部 AI 建议。
- AI Advisory SAFE 必须声明 35/35 全覆盖、35 条均为 `CONFIRM_HISTORY_COMPLETE_AND_KEEP_NOT_SUPPORTED`，且尚未冒充 Owner 裁决。
- 必须通过私有 SHA-256 pin 文件核对 packet、results、semantic checks、AI Advisory 四份输入。
- 仅将精确匹配 AI Advisory 的 35 个 assessment 的 `history_complete` 设为 true。
- 对 target locator 执行 `message_index=-1 -> 0`、`component_ref -> ""`；对 history locator 只清空 `component_ref`。
- quote、offset、role、verdict、reasoning、rule_basis、missing_context、其余 coverage 字段及 60 条 semantic checks 不得改变。
- 先在内存运行 `verify_owner_results()`；通过后才 create-only 写入新目录，再调用官方 CLI verifier。
- 输入目录必须 0700、输入文件必须 0600；输出目录必须此前不存在，输出文件 0600。
- 不访问数据库，不启动 GPU/HF Job，不运行 SFT，不执行 Quality-v1 admission。

## 准备私有 SHA pin 文件

在 Owner Mac 私有目录创建 JSON 文件，内容为四份输入的 SHA-256。不得提交此文件或任何私有 JSONL 到 GitHub：

```json
{
  "OWNER_ADJUDICATION_BLIND_PACKETS_PRIVATE.jsonl": "<sha256>",
  "OWNER_ADJUDICATION_RESULTS_PRIVATE.jsonl": "<sha256>",
  "OWNER_SEMANTIC_ENTAILMENT_CHECKS_PRIVATE.jsonl": "<sha256>",
  "OWNER_HISTORY_COMPLETENESS_AI_REVIEW_35_PRIVATE.jsonl": "<sha256>"
}
```

## 执行

从仓库根目录运行，替换为本机实际私有路径：

```bash
python3 scripts/r60_owner_approved_package_normalizer_v1.py \
  --repo-root "$PWD" \
  --source-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109" \
  --output-dir "$HOME/.local/share/storyforge/r60/private/owner-adjudication-dev20-rubric-v2-1-20261109-owner-approved-v1" \
  --expected-sha256-json "$HOME/.local/share/storyforge/r60/private/p2a-input-sha256.json" \
  --owner-approved
```

不带 `--owner-approved` 必须拒绝执行。输出目录存在、输入 SHA 不匹配、AI Advisory 不是全体一致建议、35 个 pair 不精确匹配、locator 形态与预期不同或 verifier 不通过，均应停止。

## 预期成功条件

- `status=OWNER_REVIEW_COMPLETE__SEMANTIC_HOLDS_PRESERVED`
- cases_verified=20
- semantic_checks_verified=60
- history_completeness_confirmed=35
- target_locators_normalized=60
- history_locators_normalized=20
- semantic HOLD 按原结果保留，不为通过验证而篡改
- 原始输入 SHA 不变
- quality_v1_admitted=0
- training_authorized=false
- gpu_started=false

任何失败都应保留原始包，先诊断原因；不得放宽 verifier 或覆盖已有目录。
