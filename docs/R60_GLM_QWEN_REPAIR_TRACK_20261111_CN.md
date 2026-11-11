# R60 GLM 优先 + Qwen 并行故障修复任务书（2026-11-11）

## 2026-11-11 Owner Mac GLM v2 真实冻结 Runner CPU 回执：PASS

Owner 在固定版 CPU 集成测试中返回：

```json
{"frozen_runner_used":true,"gpu_started":false,"original_rejected_inexact":true,"original_response_modified":false,"private_values_emitted":false,"punctuation_repair_revalidated":true,"quality_decision_changed":false,"schema":"storyforge_r60_glm4_literal_repair_cpu_probe_safe_v1","status":"GLM_LITERAL_FROZEN_CPU_INTEGRATION_PASS"}
```

**已证实**：冻结 Runner 能拒绝合成的不精确引用，标点级引用修复候选通过冻结校验，审核质量判定及原始响应不变。没有模型推理、没有使用历史12条失败的实际模型输出验证修复率，不能据此报告新有效 Checkpoint。原 GLM 仍 **13/25 VERIFIED、12/25 TECHNICAL_FAILURE**；本次仅标记 CPU 集成门槛 PASS。

**下一优先级**：修复脚本加入安全的实际运行时覆盖率和独立保存原始模型生成诊断的机制（不输出正文），再由 Owner 决定是否进行**有预算、有限样本、独立输出**的 H200 新实验；避免一次性原样重试12条。现有 `--quote-literal-repair` 是可选功能，不代表批准付费 GPU，不代表已获得新的质量 PASS。Qwen 继续准备前6条 Checkpoint 的 CPU 身份核验及第7条 SAFE 分阶段故障定位。

---


## 2026-11-11 GLM CPU 集成预检 HOLD：安全定位 v2

Owner 实测初版 `GLM_LITERAL_FROZEN_CPU_INTEGRATION_HOLD`，初版没有 reason_code，不能判断是模型引用修复失败还是测试夹具制造了无法修复的引用。初版合成方式 `target_text[:24] + 任意标点` 不保证候选在原文中唯一、不能作为修复通过的充分前提。

修订后的 `r60_glm4_literal_repair_cpu_probe.py` 只选择**实际原文前缀的标点结尾片段**，替换末尾标点后必须事先由真实 `reconcile_quote` 确认能够唯一还原，才进入冻结 Runner 测试。HOLD 仅输出明确白名单 `reason_code`；所有私有异常和原文均隐藏。与 `r60_glm4_exact_quote_repair.py` 配套使用，不能只更新单个文件。新增 CPU 合成集成回归。

在 Owner Mac 运行**新独立目录**（不要使用上一轮 `glm-literal-cpu-tools-v1` 的旧代码）：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
SOURCE="$PILOT/input_B_quote_observer_v1"
DEST="$PILOT/glm-literal-cpu-tools-v2"
PIN="bb1e7e3de6b72093d4a387f02c89247868c0fb1f"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" cat-file -e "$PIN^{commit}"
test ! -e "$DEST"
test -f "$SOURCE/runner.py"
test -f "$SOURCE/source.private.jsonl"
umask 077
mkdir -m 700 "$DEST"
for F in r60_glm4_exact_quote_repair.py r60_glm4_literal_repair_cpu_probe.py; do
  git -C "$ROOT" show "$PIN:experiments/r58_quality/$F" > "$DEST/$F"
done
chmod 600 "$DEST"/*.py
python3 -m py_compile "$DEST"/*.py
python3 "$DEST/r60_glm4_literal_repair_cpu_probe.py" \
  --runner "$SOURCE/runner.py" \
  --input "$SOURCE/source.private.jsonl"
```

预期为 `GLM_LITERAL_FROZEN_CPU_INTEGRATION_PASS`，否则请回传包含 `reason_code` 的 SAFE JSON；**禁止打印原始私有 traceback**。本次依旧没有运行 GPU，没有改变历史回执。

---


## 现有确定事实

GLM B25：H200 定向诊断 Job `adradar/6af3f4e09737d9a9e092936e` 完成，12/12 重试 `MODEL_NONEXACT_QUOTE_HOLD`，新增有效 0，历史有效 13 保留。引文错误具体是 source 8 条/16 处、target 7 条/13 处，3 条重叠；全部字段均为合法 list，且未见数量超限或超长、空值。**模型生成引文未能逐字出现在原文**，不等于来源错误、质量本身 PASS/HOLD/REJECT，也不能擅自修复为任意其他证据。

Qwen A25：保留原始 6 个完整 Checkpoint，样本7在调用链中出现 `ValueError / UNKNOWN_REVIEW_FAILURE`。既有 Guidance 构造 CPU 预检均通过，但**仍未确认错误发生于 SamplingParams、generate、校验、修复或 checkpoint**。与 GLM 引文不匹配的运行时签名不同，不能直接认定同类错误。

## GLM P0 修复路径：只修标点空白，不修改正文证据

已新增 `experiments/r58_quality/r60_glm4_exact_quote_repair.py` 与 `tests/test_r60_glm4_exact_quote_repair.py`：

- 只有本来就已接近原文的长引用（至少10字符）、能在对应历史消息或目标正文中找到长度近似且有连续6字锚点的候选，才考虑修复。
- 编辑距离最多2，且去掉标点/空白后正文字符必须 **完全一致**；任何中文字词、否定词的增删改均不允许。候选须具有唯一最小编辑距离，否则拒绝。只能在源引用上取对应消息、在目标引用上取目标正文；禁止跨字段。
- `HOLD`/评分/严重标记/注释/不确定性等所有非引用字段绝不改。若多项引文只有一部分能修复，**整个修复回滚**，原校验器继续给出原始技术失败；不得因挑选无关原文拼凑 PASS。
- `r60_glm4_b25_continuous_review.py` 增加显式 `--quote-literal-repair`，仅允许原25条历史验证后挑出的12条隔离重试，禁止与旧 `--quote-shape-diagnostic` / `--repair-quote-shape` 同时启用；可与 `--quote-match-observer` 并用。无该参数时完全不改旧逻辑。
- 修复后的 Checkpoint 仍由 frozen `checkpoint_record` → `validate_response` 走原认证流程。试验产生的新 checkpoint 必须独立输出，不能覆盖原13个有效或12个技术失败回执。
- 这是有限、安全的字面误差修复，不是已有12条都可以救回的保证。**语义改写、虚假引用仍为技术失败。** 后续如需更广泛修复，必须设计新的证据选择/语义裁决实验并独立记录版本，不能把引用改写直接宣称质量通过。

## Qwen P0 并行路径：CPU 身份门槛 + 单位置诊断

已新增 `experiments/r58_quality/r60_qwen_resume7_cpu_gate.py` 和 `tests/test_r60_qwen_resume7_cpu_gate.py`。CPU-only：固定 A25 源文件 SHA、严格要求 6 个有效且没有外来文件的 Checkpoint、通过冻结 Runner 对原6条读取再校验。失败直接 HOLD，绝不启动 GPU。

Qwen 原 `experiments/r58_quality/r60_qwen_guidance_diagnostic.py` 已支持 SAFE 分阶段事件：`GUIDED_PARAMS_START/PASS/FAILURE`，`SAMPLING_PARAMS_START/PASS/FAILURE`，`GENERATE_START/PASS/FAILURE`，不输出原文、异常消息、模型生成文本。下一次（由 Owner Mac 明确提交）应仅 `--resume --case-limit 7 --diagnose-generation-stages`，**不要把 GLM 的引文修复引入 Qwen，也不要在错误归类前增加模型重试次数**。该路径会复用旧6个受签名约束的 checkpoint，只尝试第7条；在原6个 checkpoint 所在原输出目录操作，有新增7号回执的风险，因此需先独立复制原6个验证后的 checkpoint 到全新测试目录，并对副本再次校验，再提交新 Job。

## 执行优先级

1. GitHub CI、CPU 合成测试 PASS；Owner Mac 本地私有冻结 Runner 核对；不开 H200。
2. 优先 GLM：在本地用真实12条历史输入执行**不含 GPU 的 quote repair 静态/合成预演**，检查修复候选的覆盖率（只输出计数，不输出引文）。若覆盖率很低，应直接转向候选列表受约束的模型引用重审设计，而不是再次全量 H200 重试。
3. Qwen：CPU 验证前6个 checkpoint、冻结运行路径，再决定单条7号有明确诊断阶段的 HF Job。若复用 GLM 的某个结构化输出 API 问题被证实，优先修复 GLM 的共用工具后再迁移；否则两者分开推进。
4. **本次没有发起 GPU Job、没有改动原始回执，没有开启训练准入**。结论由 Owner 返回的 SAFE 结果再定，不能预判 GPU 实验成功。


## Owner Mac：GLM 冻结 Runner 的 CPU 集成预检

这一步使用**私有原文中的真实连续片段，合成一个仅标点错误的审核回复**，调用冻结 `checkpoint_record` 原始函数及引用修复 wrapper，核验原审核应先拒绝、修复后原审核通过；不调用 GPU、不会持久化任何 Checkpoint。每个被引用的字段均保持当前 25 条输入 SHA 约束。

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
PILOT="$HOME/.local/share/storyforge/r60/private/r60-hf-quality-pilot25-vllm0100"
SOURCE="$PILOT/input_B_quote_observer_v1"
TOOLS="$PILOT/glm-literal-cpu-tools-v1"
PIN="2d3882acb1fc0ed2aaaf853f9efc10efa5bf41a2"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
test -f "$SOURCE/runner.py"
test -f "$SOURCE/source.private.jsonl"
test ! -e "$TOOLS"
umask 077
mkdir -m 700 "$TOOLS"
for NAME in r60_glm4_exact_quote_repair.py r60_glm4_literal_repair_cpu_probe.py; do
  git -C "$ROOT" show "$PIN:experiments/r58_quality/$NAME" > "$TOOLS/$NAME"
done
chmod 600 "$TOOLS"/*.py
python3 -m py_compile "$TOOLS"/*.py
python3 "$TOOLS/r60_glm4_literal_repair_cpu_probe.py" \
  --runner "$SOURCE/runner.py" \
  --input "$SOURCE/source.private.jsonl"
```

预期 `GLM_LITERAL_FROZEN_CPU_INTEGRATION_PASS`。这只证明冻结校验器入口、源字段映射和标点修复在 CPU 合成数据上成立，**不保证上一轮 12 条真实模型引文能修复**。若 HOLD，停止新 GPU 试验，先检查私有 Runner 的结构兼容和候选唯一性，不要放宽阈值。

## Owner Mac：Qwen 前 6 个回执的 CPU 恢复门槛

必须先将原 Qwen 25 条冻结输入、Runner，以及从 HF Bucket 获取的前 6 个 Checkpoint 置于本地独立目录。运行：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
PIN="2d3882acb1fc0ed2aaaf853f9efc10efa5bf41a2"
DIR="$HOME/.local/share/storyforge/r60/private/qwen-resume7-cpu-tools-v1"
test ! -e "$DIR"
umask 077
mkdir -m 700 "$DIR"
git -C "$ROOT" fetch origin r60/p4-generation-eval-framework
git -C "$ROOT" show \
  "$PIN:experiments/r58_quality/r60_qwen_resume7_cpu_gate.py" \
  > "$DIR/r60_qwen_resume7_cpu_gate.py"
python3 -m py_compile "$DIR/r60_qwen_resume7_cpu_gate.py"

# 以下三个变量必须指向 Owner Mac 已实际准备的原始文件/目录：
# QWEN_RUNNER=/.../runner.py
# QWEN_INPUT=/.../source.private.jsonl
# QWEN_RECEIPTS=/.../six-checkpoints

python3 "$DIR/r60_qwen_resume7_cpu_gate.py" \
  --runner "$QWEN_RUNNER" \
  --input "$QWEN_INPUT" \
  --receipts "$QWEN_RECEIPTS"
```

预期 `QWEN_RESUME7_CPU_GATE_PASS`，`checkpoint_prefix_verified=6`，`next_position=7`。若 Qwen 的文件目录还未从 HF Bucket 挂载或复制，**不能**声称已通过此门槛，更不能直接进行第 7 条付费恢复。

