# StoryForge R60 — GLM/Qwen 统一 CPU 优先执行状态（2026-11-11）

> 本文件是 2026-11-11 统一运行决策的当前摘要。历史 GLM 1–2 条 probe、12 条隔离重试、旧 Qwen 无快照重试建议仅用于追溯，**均非当前执行计划**。当前同一 Agent 独占维护 `r60/p4-generation-eval-framework`；本文件不授权 HF 付费任务、训练或 PR 合并。

## 一、不可混淆的冻结事实

- GLM 模型 `zai-org/GLM-4-32B-0414`，revision `8dea913c41b543527c2860fb6f3c15c202f24aeb`，原始输入 SHA-256 `01639568cf21a7b98356f2b3b74f567943b4a6844edb9230b58759789ab67fc9`，**GPU 运行代码 PIN 仍为 `6f2a71f12f3a2408b4082d6f8b86e69e0b5cf384`**。
- Owner 手动执行 H200 Job `adradar/6af41611ab34849891ade4fa`，RUN_ID `r60-glm-full25-snapshot-20261111T071518Z`。尝试原始25条、仅一次引擎初始化；25份独立原始 slot01 Snapshot、13个新有效 Checkpoint、12个新技术失败回执均已列出并在 Owner Mac 独立目录完成全25回放；历史13+12输出未覆盖。
- Owner `GLM_FULL25_LOCAL_INVENTORY_PASS count=25`，`CPU_SNAPSHOT_REPLAY_COMPLETE__NO_ADMISSION` / `scope=FULL25` / `replayed_cases=25`：冻结原始技术有效13、失败12；标点/空白保守修复实验技术有效17、失败8。修复后新增技术有效原始位置6、12、20、22，其质量决定均 `REJECT`。
- 剩余8个技术失败位置1、5、7、9、15、23、24、25，均为 `MODEL_NONEXACT_QUOTE_HOLD`。这与质量 REJECT 是不同问题。
- Owner 读取25份**已回放验签**原始 Snapshot 的模型 JSON，`decision` 为 `REJECT=25`、`PASS=0`、`HOLD=0`。因此不能把25次拒绝归咎于 CPU 修复改变了模型决策；**仍不能断言模型是否误拒绝**，因为缺少独立 Gold 标签/人工裁决对照。
- Owner 的 AST 探针 `GLM_REJECT_GATE_AST_PASS`，冻结 Runner `response_schema` 第118行含 REJECT 枚举，`validate_response` 第166、179行有条件；这是静态位置，不是25条拒绝的因果解释。无 GPU、无私有值输出。
- Qwen `Qwen/Qwen3-32B`，revision `9216db5781bf21249d130ec9da846c4624c16137`，A25 输入 SHA `492f24f7cb6171481e0e6d176cfa862ec6f5223bdd7abc3cfb518335dc9ab069`。Owner `QWEN_RESUME7_CPU_GATE_PASS`、`checkpoint_prefix_verified=6`、`next_position=7`、`output_modified=false`；第7条仍是 `ValueError / UNKNOWN_REVIEW_FAILURE`，**未产生新的真实第7条 Snapshot**。
- Qwen 现有 `r60_qwen_continuous_review.py`、`r60_qwen_guidance_diagnostic.py`、`r60_qwen_snapshot_cpu_replay.py` 已实现第7条诊断阶段追踪、生成后首快照立即持久化、签名快照 CPU Replay 和恰好6份历史前缀护栏；不要重造工具。
- 最新统一诊断代码 HEAD `e27bfbef740650a05e0a7a058978f8de54ba019f`，四组 GitHub CI（CI、R58 scoped synthetic、R60 Generation Eval CI、R60 P4 Runtime Image Candidate）均为 SUCCESS；这**不是** GLM 原 H200 PIN，也不意味着 Qwen 新付费运行已批准。

## 二、成本统一决策

1. **GLM 不重复 GPU 生成上述25条。** 已有25份签名快照可反复 CPU 检查；改进剩余8条引文技术覆盖率不能改变25个原始模型决定均为 REJECT 的事实。先独立 Gold/Owner 标签对照（如存在），再判断 GLM 审核器的真实误拒绝率；无 Gold 则 `CALIBRATION_GOLD_HOLD`，不猜。
2. **Qwen 不盲跑第7条。** 先 Owner Mac 对当前同源 HEAD 的阶段追踪、签名回放和0/5份前缀负面测试完成 CPU 验收。未完成之前不编制付费启动指令；需要付费时另外验证容器/入口与代码 PIN 并由 Owner 手动授权，只允许一次性第7条生成、独立结果目录、原始 slot01 写一次及签名 readback。
3. 当前两条主线 `quality_v1_admitted=0`、`training_authorized=false`。技术 `REPLAY_VALIDATED` ≠ 质量 `PASS` ≠ 训练准入。

## 三、Owner Mac 下一项：CPU-only Qwen 负面测试（零 GPU）

为防止污染工作目录、避免从历史 HEAD 误跑，固定目前四组 CI PASS 的完整 HEAD，以独立 worktree 执行合成测试，仍不访问模型权重、不提交 HF Job：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
PIN="e27bfbef740650a05e0a7a058978f8de54ba019f"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test "$(git -C "$ROOT" rev-parse origin/r60/p4-generation-eval-framework)" = "$PIN"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/r60-qwen-cpu-XXXXXX")"
git -C "$ROOT" worktree add --detach "$WORK" "$PIN"
cd "$WORK"
python3 -m pytest -q tests/test_r60_qwen_reviewer_stage_trace.py tests/test_r60_qwen_snapshot_cpu_replay.py tests/test_r60_qwen_snapshot_resume_guard.py
```

验收必须统计实际测试数量、通过/失败数，不能只声称 `py_compile` PASS。用毕可在确认无额外修改后手动 `git -C "$ROOT" worktree remove "$WORK"`。

## 四、GLM 校准门槛：不得用模型自己的判断当 Gold

真实误拒绝率需要每个原始位置的**独立 Gold 决定**（来源为已冻结人工/Owner 裁决或其他明确授权的对照），以及一致的 Rubric 版本和覆盖情况。建议 Owner 只在本机建立不含原文的25行对照索引，最少包括：
`original_position`、`gold_decision`、`gold_status`、`rubric_version`、`independent_of_glm`。在 Gold 缺失、未确认独立或 Rubric 不兼容时，必须 HOLD，不得为了创造 PASS 标签自行改写 Gold。

若 Gold 完整且独立，因25份模型原始决定全为 REJECT，只需按 Gold 的 PASS/HOLD/REJECT 分类统计：真实 Gold PASS 的每一条都是模型侧误拒绝候选；但技术审核不通过的8/12条要单独保留技术状态，不能把它们直接当可签发质量回执。

## 五、下一个付费与质量决策

- 先用已有 GLM 25 Snapshot 完成真实 Gold/Owner 对照，确定是否存在误拒绝；没有 Gold 则明确 HOL​​D，优先解决独立对照的可用性。
- Qwen 第7条先将 CPU 门槛全部验证，再检查入口镜像与 runtime PIN；**任何 GPU Job 必须 Owner 另行批准并自行在 Mac CLI 提交**。
- 更新 Issue #28 和 PR #30 SAFE 记录；PR 不合并，冻结 Runner、历史证据、模型 revision 不修改。
