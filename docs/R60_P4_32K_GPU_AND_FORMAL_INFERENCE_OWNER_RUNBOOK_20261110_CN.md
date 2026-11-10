# StoryForge R60 P4：32K 合成 GPU 与后续正式推理 — Owner Mac 执行任务书（2026-11-10）

> **Owner 已分阶段授权**：首先 32K 合成 GPU 测试；通过验收后再开展正式推理。**本文件不构成已提交 HF Job 的证明。** HF Jobs 仅由 Owner 在 Mac CLI 执行；ChatGPT 不调用 Hugging Face Jobs、不测试 Bucket 或 OAuth，也不擅自合并 PR。

## 1. 授权记录与不变量

机器可读授权：`experiments/r60_quality/p4_generation_execution_authorization_20261110.json`。

- 冻结配置：`experiments/r60_quality/p4_generation_profile_frozen_v1.json`；SHA-256 `a58d02c757767f18deb8a4cb948a56be199c837c045d83648838868961e1037f`。
- 原 Frozen Profile **不修改**。候选配置也保持不变；运行时使用另行生成的、带明确任务范围的**授权执行副本**，不得覆盖 Frozen。
- 阶段 1（合成）：Owner 已授权 GPU 与合成推理；正式执行包尚待 CPU 入口/输入和输出闭环验收。合成实验不能读取 Development20、Locked30、真实历史案例或训练集。
- 阶段 2（正式）：Owner 已原则批准正式推理，但**仅在阶段 1 验收通过且数据清单、输出私有存储、预算确定后激活**；不是对任意数据和无限次数运行的许可。
- SFT/Training、1000 条批量审核、自动重试、自动扩大预算、自动合并 PR：未授权。
- 旧一次性短上下文 Smoke 授权已消费，不可作为本次 GPU Job 的执行凭据。
- Frozen 文件 `profile_freeze_authorized=true`、`inference_authorized=false`、`gpu_authorized=false`、`training_authorized=false`；在准备好合规执行副本前，Worker 必须继续 fail-closed。
- 当前执行器 `worker_cli.py` 的 `assess_profile(..., purpose="generation")` 同时要求三个开关为 true。仅将本授权 JSON 放在工作目录 **不会自动授权** Worker；必须使用新版本隔离的、范围绑定的执行副本并先完成合成输入防串用控制。

## 2. 32K 合成任务固定契约

| 约束 | 固定要求 |
|---|---|
| 模型 | A = Qwen3-32B；B = GLM-4-32B-0414；challenger = GLM-Z1-32B-0414，精确 revisions 见 Frozen |
| GPU | 首选 H200 141GB，`h200`；BF16，单卡、batch=1，三模型**串行** |
| Context | 32,768 tokens，总预算 = input 28,672 + generation 4,096（包括 Thinking） |
| 输入 | 仅确定性生成的合成中文消息，不含真实用户、故事、审阅标签、私有文本 |
| 生成 | 模型采样、EOS、stop、seed 完全服从 Frozen；不临时调参、量化或截断输入 |
| 每 Job | 1 模型、1 attempt，硬超时最多 60 分钟；前一模型 SAFE 验收后再开始下一模型 |
| 合成阶段价格 | HF 官方 H200 参考 $5/GPU-hour；三模型串行首轮最多 3 GPU-hours、约 $15 GPU 费用，不含其他收费 |
| 输出 | `/input` 只读、`/output` 新的专用前缀可写；正文仅私有目录，stdout 仅 SAFE |
| 禁止 | 更换模型 revision、改变 Frozen、无预算继续重试、无人工 SAFE 检查自动进入正式推理 |

**输入预算是上限而非实际实测长度。** 32K 有效验收必须报告三模型的实际 `input_tokens`、`output_tokens`，确认确实接近目标上下文；仅在 Profile 写 `max_input_tokens=28672` 不构成 32K 实测。使用不同实际长度做边界阶梯测试时应标为前置诊断，不能宣称 32K PASS。若无法令 4,096 generation 实际跑满，应清楚区分实际 decode 与配置上限。

计费证据：<https://huggingface.co/docs/hub/en/jobs-pricing>（2026-11-10 复核）；提交之前 Owner 再用 `hf jobs hardware` 检查当前价格、flavor 与可用性。

## 3. Owner Mac 准备（不提交 Job）

先确认 Git 工作区无未保存改动，不能覆盖 Owner 工作；使用已有 `r60/p4-generation-eval-framework` 工作区：

```bash
git status --short --branch
git fetch origin
git rev-parse origin/r60/p4-generation-eval-framework
git rev-parse HEAD
git diff --exit-code
```

自行检查和更新到当前分支 HEAD，按提交记录核对 Frozen 的 SHA；**禁止**未经确认 `reset --hard`、`clean`、`stash`。在匹配仓库根目录时运行：

```bash
shasum -a 256 experiments/r60_quality/p4_generation_profile_frozen_v1.json
python3 - <<'PY'
import json
from pathlib import Path
p=json.loads(Path("experiments/r60_quality/p4_generation_profile_frozen_v1.json").read_text())
a=json.loads(Path("experiments/r60_quality/p4_generation_execution_authorization_20261110.json").read_text())
assert p["profile_freeze_authorized"] is True
assert all(p[k] is False for k in ("inference_authorized","gpu_authorized","training_authorized"))
assert a["stages"]["synthetic_32k"]["owner_authorized"] is True
assert a["stages"]["formal_inference"]["owner_authorized"] is True
assert a["stages"]["formal_inference"]["execution_activated"] is False
print("P4_STAGED_AUTHORIZATION_STATIC_CHECK_PASS")
PY
hf jobs hardware
```

以上为**只读核对**，不会创建 HF Job、运行 GPU、连接 Bucket 或访问私有案例。

## 4. 真正提交前的工程门槛（当前 HOLD）

现有通用 `build_generation_plan` 与 `worker_cli` 可以接受三个开关全 true 的任意有效 Profile + Manifest，尚无独立的 `synthetic_only` 身份/记录防串用保护。因此不能只是把 Frozen 中 `gpu_authorized/inference_authorized` 改成 true 后直接投入正式 Job。应先在工程分支实施并通过 CPU-only 测试：

1. 从 Frozen 内容派生**不改模型参数的合成授权 Profile**，绑定 Frozen SHA、授权记录 SHA、任务 ID、`synthetic_only`、数量上限、数据 manifest SHA，且保持 `training_authorized=false`；原 Frozen 不可修改。
2. 输入生成脚本使用公开的合成文字，固定 seed，记录内容文件 SHA、record_count、每个模型实际 tokenizer token 数及 target 差距；同时生成 Worker 所需 `/input/{generation-profile.json,manifest.json,inputs.jsonl}`。
3. 对执行器加 fail-closed：任何测试记录越过实际 tokens 预算、合成任务挂了私有数据、输出目录已有文件或 mount 不正确，均不下载权重、不启动 GPU；报告 SAFE HOLD。
4. 对三模型合成任务进行 **CPU-only plan review** 和严格预算检查。冻结的 revision、Prompt/Schema、dependency lock SHA、container digest 不得漂移。
5. HF Job 输出 RW 挂载与 SAFE 回收由 Owner Mac 负责；历史 Owner Bucket RW 成功并不直接证明新的 P4 输出前缀可写。
6. 先执行**一个**合成模型，分析真实峰值显存、首 token / 总时长、实际输入/生成 tokens、finish_reason、Thinking/Schema 和输出可读回性，再决定下一模型是否符合已授予预算与规则。

## 5. 32K 合成验收和自动停止

任何 OOM、GPU 初始化失败、依赖版本/文件 SHA 不符、unexpected stop、SAFE 丢失、生成正文进入日志、无法回收私有输出、超时/预算上限，均停止当前及后续阶段，保留可核查的 SAFE，并请求 Owner 对修复/继续的明确决定。

合成成功需要三模型都留下：Job ID/精确运行代码 commit/Frozen SHA/Role/Hub revision/runtime digest/lock SHA/输入 manifest SHA/实际 token 长度/GPU name/峰值显存/模型加载与 prefill+decode 时间/finish_reason/私有输出 SHA 与回收证明/实费。不得把短输入 Runtime Smoke、CPU CI 或 H200 理论内存当成 32K 实测。

若达到单任务 60 分钟或合成阶段总 3 GPU-hours/$15 上限，停止且不得自动提升到整个先前的 $55 估计预算。更大 synthetic pilot 或失败重试须按其任务预算明确单独处理。

## 6. 正式推理（获原则批准，尚未激活）

合成验收 3/3 通过后，才可准备正式任务的受控执行副本。必须至少固定：

- 输入案例范围与计数：Development20 / Locked30 各自是否包含、是否仅 primary / sensitivity，关联输入 manifest SHA、访问边界；
- 盲化、模型执行顺序、Schema/Rubric v2.1、输出归档与回读策略；Locked30 不调参；
- 每模型 Job 数、batch/record_count、最大预算、总 GPU-hours/美元上限、故障处理、重试限制；
- 不暴露原文和模型生成到 GitHub/Actions/公开 SAFE，Owner 仅带回必要脱敏聚合回执。

正式执行成本不包含在合成阶段 $15 中，尚无已确认的独立上限，因此**当前不生成可立即启动的正式 Job 命令**；Owner 已原则授权目标，但尚不能证明任意具体正式任务已满足执行门槛。训练仍未授权。

## 7. ChatGPT / Agent 的后续职责

继续开发可复用合成输入、授权执行副本和 CPU-only 测试，维护 PR #30 / Issue #28；出具固定代码 commit 的 Owner Mac `hf jobs run` 最终命令与 SAFE 核对标准，**仅在提交前工程门槛全通过后**交付。HF Job 的实际提交、取消、日志与输出回收，均由 Owner 的 Mac CLI 执行。PR 保持 Open / Draft，不自动合并。
