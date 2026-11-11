# StoryForge R60：GLM Generation Snapshot + CPU Replay v1

## 为什么改架构

GLM B25 已有 13 个有效 Checkpoint，另外 12 条因逐字引文不匹配失败。此前三次付费生成/重试中，每次冻结 Runner 在 `engine.generate()` 后直接校验，并且仅将失败状态码保存。**失败原始模型文本被丢弃**，导致调整任何引文诊断/修复算法都可能要求再次付费。现在将一次 GPU 输出的原始生成文本留在仅限 Owner 的私有目录，CPU 可重复回放（同一输入/输出/冻结验证器）验证不同修复逻辑。

## 新实现

- `experiments/r58_quality/r60_generation_snapshot.py`：纯 Python，不依赖 vLLM。对 `engine.generate()` 返回的单项输出在冻结校验之前持久化，**每个 case 两个 generation slot**：slot01 主生成、slot02 冻结 Runner 产生的二次引用修复生成。每个文件使用 `O_EXCL`、0600、flush+fsync、JSON 规范化 SHA 和绑定身份（原样行 input_digest、model/revision、frozen runner 文件 SHA、policy、position、generation_index、finish_reason、原始文本 SHA），回读验证。不可覆盖；私有正文只存入 Owner 私有目录，绝不输出到 CI/GitHub/SAFE 日志。写入失败立即终止，不会当成技术审核失败或伪造 Checkpoint。
- `r60_review_isolation_core.run_isolated(generation_snapshot_store=...)`：可选插桩；每条发起推理前设置位置，再将该条所有 `engine.generate` 调用返回的输出绑定到同一案例（两个编号）。默认 `None` 时，原始 Qwen/GLM 路径完全不变。
- `r60_glm4_b25_continuous_review.py --generation-snapshot-dir`：仅可在原25条签名基线核验、12条 GLM 隔离重试、`--quote-match-observer` 观察器启用且 `--resume` 禁用时使用。快照目录必须是**预先存在的空目录**，与原始输入、基线、技术回执输出目录相互独立。可结合 `--literal-probe-cases 1|2` 有限样本实验；不强制开启标点修复。若未显式设此参数，则不会生成快照。
- `experiments/r58_quality/r60_glm4_snapshot_replay.py`：离线 CPU 重放，核对固定原25条 B 输入 SHA，按冻结 `FAILED_POSITIONS` 映射为本地子集1..12；验证快照原始文件、槽位顺序、runner 文件 SHA 和 model/revision/row digest。先尝试冻结 `checkpoint_record()`；如果 slot02 存在且初次出现 `QuoteValidationError`，允许使用**冻结 Runner 原生 `quote_candidates` + `apply_repairs`**离线重放模型提供的修复选择；另用只允许标点/空白的 `make_reconciler` 对原主回复进行独立 CPU 对照。输出唯一新增 SAFE JSON 报告（O_EXCL、0600），只计 `REPLAY_VALIDATED` / `REPLAY_FAILED` 和单条 `PASS/HOLD/REJECT`，**仅为回放结果、不等于真实审核 Checkpoint 或训练准入**。原始模型输出绝不出现在报告。
- `tests/test_r60_generation_snapshot.py`、`tests/test_r60_glm4_snapshot_replay.py`：CPU 回归测试，覆盖 2 次生成捕捉、文本篡改拒绝、原始快照不可覆盖、非 stop 原文捕获、模型引用无法匹配与标点修复 CPU 对比、次级修复回复回放、文件目录夹杂/缺失拒绝。

## 当前状态与验收

这是**工程实现 + CPU 合成验证**。已经取得 Owner Mac 原冻结 Runner 的 `GLM_LITERAL_FROZEN_CPU_INTEGRATION_PASS`，但尚未针对这个新的快照/回放组合完成 Owner Mac 私有 Runner CPU 集成，也没有产生真实 GLM 原始生成快照。过去 12 条失败没有保留下来的完整生成文本，无法从 SAFE 诊断日志重建；不能用本工具声称修复原来已完成的 12 条。原13有效/12技术失败、Quality-v1 admitted=0 不变。

### 第一阶段：Owner Mac CPU-only 工具准备

以下命令只把 GitHub 确认版本的工具复制到 Mac 新目录并跑合成测试，不启动 Hugging Face，不运行 GPU：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BASE="$HOME/.local/share/storyforge/r60/private"
DEST="$BASE/r60-glm-snapshot-replay-tools-v1"
PIN="3cbf7c75b8f978b3476013fc4c920e72b00ac5fc"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" cat-file -e "$PIN^{commit}"
test ! -e "$DEST"
umask 077
mkdir -m 700 "$DEST"
for F in r60_generation_snapshot.py r60_glm4_snapshot_replay.py r60_glm4_snapshot_cpu_preflight.py r60_glm4_literal_repair_cpu_probe.py r60_glm4_exact_quote_repair.py r60_glm4_b25_retry_contract.py r60_review_isolation_core.py; do
  git -C "$ROOT" show "$PIN:experiments/r58_quality/$F" > "$DEST/$F"
done
chmod 600 "$DEST"/*.py
python3 -m py_compile "$DEST"/*.py
python3 -m pytest -q \
 "$ROOT/tests/test_r60_generation_snapshot.py" \
 "$ROOT/tests/test_r60_glm4_snapshot_replay.py"
```

### 第二阶段：CPU Replay 真实回执使用方式

只针对**未来已实际捕获、独立保存的 Generation Snapshot**，从 Owner Mac 或受控容器读取私有目录与原冻结 Runner：

```bash
python3 "$DEST/r60_glm4_snapshot_replay.py" \
  --runner "$GLM_INPUT_DIR/runner.py" \
  --input "$GLM_INPUT_DIR/source.private.jsonl" \
  --snapshots "$GLM_PRIVATE_SNAPSHOTS" \
  --output "$BASE/r60-glm-cpu-replay-report-v1.safe.json"
```

原始输入 SHA、Runner digest、模型 pin 与 slot 均需完全匹配。注意真实快照目录严格只允许 `generation_NNNN_SS.private.json` 文件，独立存放，不要添加 `logs` 等文件。如果不知道 `GLM_PRIVATE_SNAPSHOTS` 的真实路径，**不要推测或伪造**。本步骤没有快照时必须 HOLD，不能把过去的 SAFE 统计冒充快照。

## 下一次 GPU 实验（尚未发起）

在已经 CPU 测试 PASS、Owner 审批付费预算后：

1. 准备和冻结 Runner 相同的一套模型、revision、Tokenizer 和原25输入；所有新脚本固定在一个提交 SHA，禁止混用版本。
2. 创建独立新目录：`/bucket/evaluation-runs/r60-glm-b25-generation-snapshot-v1` 用于经过原 Runner 校验的回执；`/bucket/private-generation-snapshots/r60-glm-b25-generation-snapshot-v1` 用于含敏感原始模型回复的快照（两者需不同、只读保护旧基线）。
3. 新启用 `--generation-snapshot-dir ... --quote-match-observer --isolate-technical-failures --retry-baseline-dir ... --case-limit 12`；初次可先加 `--literal-probe-cases 1` 或直接将 Debug 拓展至多2条。**不建议先启用任何自动引用修复**：先获取原始模型输出与冻结 Validator 同样输入，防止把“重新生成”误认为算法修复收益。
4. 快照完整性验证通过后，在 CPU 多轮对照原严格校验/标点修复/后续证据引用方案；只有 GPU 生成策略本身变化时才重新生成。

**不可混淆：** Snapshot `generation_0001_01.private.json` 对应重试子集第1条，而非原25条的全部第1条位置。报告同时包含 retry_position 与原始位置，绝不直接覆写原始 `technical_failure_0001.safe.json`。生成内容受到源输入隐私范围约束，禁止复制到公开 GitHub、Issue 评论或模型 Debug 输出中。

