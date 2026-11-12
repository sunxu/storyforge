# R60 P1 双模型审核结果汇总工具（2026-11-11）

## 目标与完成边界

在不进行 GPU 推理、不更改任何原始回执的前提下，汇总 A（Qwen3-32B）与 B（GLM-4-32B-0414）的 **25 条盲审**。每个模型独立记录两种正交维度：

- 技术状态：`VERIFIED`（冻结 Runner 完整验证 checkpoint）、`TECHNICAL_FAILURE`（已签名并重验的技术失败回执）、`MISSING`（没有任何原始回执）。
- 质量判定：只有 `VERIFIED` 才能为 `PASS/HOLD/REJECT`；技术失败与缺失样本必须设为 `null`，绝不转换为质量 HOLD。

质量一致性只统计两模型都为 `VERIFIED` 的样本。报告含 A/B 独立技术数、独立质量数、白名单技术失败原因计数、两模型质量一致/冲突、3×3 质量矩阵及逐位置 SAFE 结果。不能据此自动训练准入（始终 `quality_v1_admitted=0`、`training_authorized=false`）。

## 审核数据和完整性门槛

- `experiments/r58_quality/r60_dual_model_review_summary.py` 是 **CPU-only 只读**工具。
- 输入 SHA 固定：A=`492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069`；B=`01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9`；两者均固定25条。
- 分别从两模型对应的**原始冻结 Runner**加载模块，用该 Runner 的 `validate_input`、`input_digest`、`read_checkpoint` 原样核验每条 Checkpoint 的身份、模型、revision、政策、receipt SHA 和有效质量 decision。技术失败通过共享 `validate_failure` 校验摘要及技术错误白名单。
- A/B 有可能因独立盲审产生不同的 blind ID、不同文件行顺序。配对要求除 `blind_id` 外的**完整源记录内容完全一致且每条唯一**，可重排 B 后与 A 一一关联；无法唯一关联直接 `P1_SUMMARY_HOLD`，绝不靠位置、相似字符串、猜测语义配对。不输出任何盲审 ID 或私有正文，也不输出映射哈希。
- 读取目录只允许 `review_NNNN.private.json` 或 `technical_failure_NNNN.safe.json`；同位置双回执、外来文件、非法签名、模型/revision/源记录不符全部 fail-closed。无任何回执的样本是 `MISSING`，不是技术失败。
- 输出为新建 SAFE JSON 文件（`O_EXCL` 且 `0600`），已存在则拒绝覆盖。stdout 只打印聚合 SAFE 状态。
- 对失败后的重试目录，本版 P1 **不进行隐式覆盖/自动合并**：请先使用原始 A/B 基线目录核对；后续若出现有效的 B 重试 Checkpoint，应单独设计经过原位置映射核验的 v2 overlay，不得直接将局部重试编号当原始位置。

## Mac 使用方式（不会运行 HF Jobs）

先将原始 A、B 的**冻结 Runner + 原始私有输入**与**原始审核回执目录**置于 Mac 本地可读路径。A 是 Qwen 的 6 条有效前缀；B 是 GLM 首轮 13 个有效+12 个技术失败的独立目录。**本工具不负责下载 HF Bucket，也不对云端数据存在作猜测。**

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
PILOT="$BASE/r60-hf-quality-pilot25-vllm0100"
PIN="c3788b9924ce4e85f26920fe5efb6de356655084"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework

# 将下面两个目录设为已实际从 HF Bucket 下载的原始回执目录。
A_RECEIPTS="$BASE/r60-a25-original-receipts"
B_RECEIPTS="$BASE/r60-b25-original-receipts"
OUT="$BASE/r60-p1-dual-model-summary-v1.safe.json"

test -d "$A_RECEIPTS"
test -d "$B_RECEIPTS"
test ! -e "$OUT"

# 原始冻结 Runner 和独立输入必须与生成这些回执时使用的一致。
A_SOURCE="$PILOT/input_A_guidance_resume"
B_SOURCE="$PILOT/input_B_retry12_v1"

TOOL_DIR="$BASE/r60-p1-dual-summary-tool-v1"
test ! -e "$TOOL_DIR"
umask 077
mkdir -m 700 "$TOOL_DIR"
for FILE in r60_dual_model_review_summary.py r60_review_isolation_core.py; do
  git -C "$ROOT" show "$PIN:experiments/r58_quality/$FILE" > "$TOOL_DIR/$FILE"
  chmod 600 "$TOOL_DIR/$FILE"
done
python3 -m py_compile "$TOOL_DIR"/*.py

python3 "$TOOL_DIR/r60_dual_model_review_summary.py" \
  --runner-a "$A_SOURCE/runner.py" \
  --runner-b "$B_SOURCE/runner.py" \
  --input-a "$A_SOURCE/source.private.jsonl" \
  --input-b "$B_SOURCE/source.private.jsonl" \
  --reviews-a "$A_RECEIPTS" \
  --reviews-b "$B_RECEIPTS" \
  --output "$OUT"
```

注意：Python 通过进程替换 `<(git show ...)` 运行时，标准导入路径可能不包含 `r60_review_isolation_core.py`。因此正式执行时**优先将本工具与共享 core 一起复制到同一个私有工具目录**，执行 `python3 "$TOOL_DIR/r60_dual_model_review_summary.py" ...`，确保两个代码文件可被 Python 导入；勿复制或提交原始私有回执到 GitHub。

预期：若 A 为6个有效且没有签名技术失败，其余19条归为 MISSING；若 B 保留13个有效+12个签名技术失败，则 B 的 VERIFIED=13、TECHNICAL_FAILURE=12、MISSING=0。实际 PASS/HOLD/REJECT 分布必须依赖**现场重验后的 Checkpoint**，本任务书不会凭经验编造。若 A/B 内容未能唯一对齐则 HOLD，应先检查原输入差异，不可人为合并。

## 验收测试

`tests/test_r60_dual_model_review_summary.py` 为 CPU 合成测试，验证：
- PASS/HOLD/REJECT 与技术失败、缺失互斥；
- 篡改或伪造技术回执 / Checkpoint 不会被悄悄计数；
- 双模型独立盲审 ID / 不同行顺序仍可在完整内容一致时一一配对；
- 完整源内容不一致、内容重复或外来文件一律 HOLD；
- 任何输出均不得包含私有小说正文或 blind ID。

P1 仅指 **汇总能力已实现**，不表示两模型都审完 25 条，也不表示训练准入。
