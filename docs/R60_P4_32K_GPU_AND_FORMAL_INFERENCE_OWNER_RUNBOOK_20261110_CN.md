# StoryForge R60 P4：32K 合成 GPU 与后续正式推理 — Owner Mac 执行任务书（2026-11-10）

## 2026-11-10 Owner H200 A 实际提交回执

Owner Mac 已实际执行唯一一次 A H200 合成 GPU Job 提交，并回传 CLI 的 Job ID 和 URL：

- Job ID：`6af32a97ab34849891ac0461`
- Job name：`r60-p4-h200-a-20261110221534`
- URL：https://huggingface.co/jobs/adradar/6af32a97ab34849891ac0461
- 启动脚本：`/Users/keedle/.local/share/storyforge/r60/private/r60-p4-h200-a-20261110221534/launch-h200-A.sh`
- 源代码提交：`465a041a8cf23dd254099a58c74d37d321db9869`（三项 CI 已通过）
- 源码归档 SHA：`421fddfa81f072094d2282a5f2a894f8c01445c108bfcfa6037c92a5a8834df8`
- Input SHA：`a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398`
- 约束：`h200`、`--timeout 60m`、`--attempts 1`、`--synthetic-authorization`；仅 A 合成负载，无自动重试。
- **状态：`H200_A_JOB_SUBMITTED__RUNTIME_AND_SAFE_PENDING`。** 目前仅有提交回执；没有 Job 最终状态、GPU 实际启动、模型加载、推理成功、tokens、stop reason、私有输出 SHA 的证据。不得标记 GPU PASS。
- 下一步：Owner 以 Mac CLI 读取此 Job 状态和 logs，提取 SAFE 结果（不要回传生成正文），结束后按 CLI 实际给出的 sync 命令回收私有输出并核对 SHA。若失败，记录 HOLD、不要重提或启动 B/C。

---

## 2026-11-10 模型 A H200 输入包 Owner PASS 与专用脚本

Owner Mac 已在新建的本地输入包执行成功：

- `H200_A_INPUT_PACKAGE_PASS`
- `STAGING=/Users/keedle/.local/share/storyforge/r60/private/r60-p4-h200-a-20261110221534`
- `RUNID=r60-p4-h200-a-20261110221534`

注意这只是本地输入包检查，没有 GPU/推理。**不要把本地 STAGING 目录或私有正文提交到 GitHub**。

本轮新增 `src/storyforge_dataset/generation_eval/owner_h200_prepare.py`：使用 Owner Mac 的本地 `git archive` 从已审核的确切 Git SHA 提取 `src/storyforge_dataset` 和哈希锁定依赖 `requirements/hf-generation-eval.lock`，封装 `input/source.tar`，在远端执行前按 SHA 检查归档、路径及大小。脚本先验证 Owner 当时的输入包（包括旧 Frozen SHA、B/C 无关、合成仅 A）、输出目录为空、源 HEAD 精确匹配 `origin/r60/p4-generation-eval-framework`，然后**仅写出** `STAGING/launch-h200-A.sh`；不提交 HF Job。

已通过最新三个 Actions 后，在 Owner Mac 执行：

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
BRANCH="r60/p4-generation-eval-framework"
STAGING="$HOME/.local/share/storyforge/r60/private/r60-p4-h200-a-20261110221534"
git -C "$ROOT" fetch origin "$BRANCH"
REV="$(git -C "$ROOT" rev-parse "origin/$BRANCH")"
WT="$HOME/workspace/storyforge-p4-h200-plan-${REV:0:12}"
git -C "$ROOT" worktree add --detach "$WT" "$REV"
PYTHONPATH="$WT/src" python3 -m storyforge_dataset.generation_eval.owner_h200_prepare \
  --repo "$ROOT" --code-revision "$REV" --staging "$STAGING"
```

应输出 `H200_A_OWNER_LAUNCH_SCRIPT_PREPARED_NOT_SUBMITTED`，确认 `source_archive_sha256` 和 `code_revision`。**不要重新运行此生成器覆盖目录**：它强制 create-only、拒绝已有 launch script，避免隐式替换已准备的源码或输入。

Owner 再检查 `cat "$STAGING/launch-h200-A.sh"`：限定 `--flavor h200`、`--timeout 60m`、`--attempts 1`、`--model-role A`、`--synthetic-authorization /input/synthetic-authorization.json`、容器固定 digest、`/input:ro`、`/output:rw`。若与预期一致，**由 Owner 自己**执行 `bash "$STAGING/launch-h200-A.sh"`。这一步会提交真实收费 GPU Job，至多 60 分钟/$5 H200 参考价（但模型下载时间也计入计费时长），只跑一次，不自动重试。立即保存 Job ID 与 CLI 输出。不能先开始 B/C，更不能开始正式推理。

GPU 实测后用 `hf jobs logs <job_id> --namespace adradar` 查看最新 SAFE（CLI 参数以 Owner `hf jobs logs --help` 为准）；按 HF CLI 实际打印的输出 bucket sync 命令回收至 Mac，验证私人完整输出的 SHA 与 SAFE。`input_tokens` 和 `output_tokens` 是验收字段；如仅达到 28,568 输入、但生成 EOS 较短，需报告实际 decode，不得写成输出 4,096 tokens 已跑满。

---

## 2026-11-10 CPU Job 挂载执行回执（读回待验收）

Owner Mac CLI 已实际提交、执行并完成唯一一次 CPU-only 本地目录挂载探针：

- Job ID：`6af324e99737d9a9e0909d12`；名称：`r60-p4-mount-20261110220617`；链接：https://huggingface.co/jobs/adradar/6af324e99737d9a9e0909d12
- 结果：`COMPLETED`；stdout SAFE 状态：`CPU_MOUNT_RW_PASS`。
- 输入 SHA-256：`a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398`（与 A 合成输入一致）。
- `gpu_started=false`、`inference_started=false`、`training_started=false`。
- 已证明 Job 内只读输入可用及 RW 输出目录可写；**Owner 已回传 Mac 本地 output bucket sync 后的实际 `mount-safe.json` 读取和校验 PASS**；总状态更新为 `CPU_MOUNT_RW_READBACK_PASS`。
- 完成核验：Mac 输出 `CPU_MOUNT_RW_READBACK_PASS`；本地读取的 JSON 为 `{"gpu_started":false,"inference_started":false,"input_sha256":"a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398","status":"CPU_MOUNT_RW_PASS","training_started":false}`。本次读回证明 `jobs-artifacts` 能够完成输出文件回收；不能推论已验证 GPU 工作器或模型权重下载。

---


> **Owner 已分阶段授权**：首先 32K 合成 GPU 测试；通过验收后再开展正式推理。**本文件不构成已提交 HF Job 的证明。** HF Jobs 仅由 Owner 在 Mac CLI 执行；ChatGPT 不调用 Hugging Face Jobs、不测试 Bucket 或 OAuth，也不擅自合并 PR。

## 2026-11-10 三模型 CPU 校准最终收口

Owner Mac 三组 CPU Tokenizer / Chat Template 校准全部 PASS：

| Role | 实际 input_tokens | SHA-256 | 证据 |
|---|---:|---|---|
| A / Qwen3 | 28,568 | `a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398` | 初次 `SYNTHETIC_32K_INPUT_PREPARED__GPU_NOT_STARTED` |
| B / GLM-4 | 28,593 | `8cb8ddf2fc511cf957ed03510853dad94b5169334fde8d6ff153afda6640285e` | `SYNTHETIC_32K_TOKEN_RECOUNT_PASS` |
| challenger / GLM-Z1 | 28,597 | `2676b44c9e0e6ea1c8ccc1824e246d20c08fd8b7cf789a669e3bd06a1f91c28c` | `SYNTHETIC_32K_TOKEN_RECOUNT_PASS` |

B 和 challenger 已通过文件 SHA、record_count、budget 校验和固定 Tokenizer 实际重新计数。此前的 `SYNTHETIC_OUTPUT_DIR_MUST_BE_NEW` 是重复执行遇到 create-only 目录保护；实际两个目录 `inputs.jsonl` 和 `manifest.json` 已存在且完整，不是模型/Tokenizer 失败。不再重复生成、不删除已有输出。三角色真实校准前置工作现 CLOSED / PASS；**不等于 GPU 的 32K 推理 PASS**。

## 新增 synthetic-only GPU 防串用保护

- CPU-only `synthetic_gate.authorize_synthetic_profile` 在模型库导入与下载权重前检查 Frozen SHA、授权文件、固定角色、Manifest 预算、记录结构、合成重复文本模式，以及上述**各自精确 input SHA**。非该三条合成输入、角色误用、混入真实私有记录或校验不符，一律 HOLD。
- `worker_cli --synthetic-authorization <path> --profile <frozen-json>` 使用**只存在内存中的**受限执行配置，Frozen 文件仍维持 Inference/GPU 授权关闭；未提供 `--synthetic-authorization` 的原正式 Worker 行为不变，仍 fail-closed。
- 测试包含拒绝任意输入、范围负向测试与三份精准记录的正向复现；相关提交 `0e0af924b1d7eab22fcf146fdbb0052831438c8d`、`a8d276e9315cd928b5a24175d301cfe5d6d4ef71`、`4e9a472835480d9f5cebafd9b6a79e863fe1e4bd`。
- **工程仍未最终 GPU 放行**：待本次变更 CI/容器固定入口成功、Owner Mac CPU-only synthetic gate 正向回执、HF 输入/输出挂载及回收闭环核对、精确可复用 Job 命令完成后，先在 Owner Mac 提交 A 单模型 H200，需独立记录 Job ID/成本/SAFE。

原下文“B 和 challenger 尚未回传”、或重复建议重新执行 B/challenger 的段落均为**历史操作记录**，以本节最终结果为准。

---

## 2026-11-10 最新 Owner Gate 验收（3/3 PASS）

Owner Mac 已对三模型运行 `authorize_synthetic_profile` 的实际 CPU-only Gate。回执均为 `SYNTHETIC_ONLY_GATE_PASS`，无 GPU、推理或训练：

| Model | input SHA-256 | CPU Token 校准 |
|---|---|---:|
| A | `a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398` | 28,568 |
| B | `8cb8ddf2fc511cf957ed03510853dad94b5169334fde8d6ff153afda6640285e` | 28,593 |
| challenger | `2676b44c9e0e6ea1c8ccc1824e246d20c08fd8b7cf789a669e3bd06a1f91c28c` | 28,597 |

冻结 Profile 未变，合成 Gate 源码提前校验固定哈希、记录格式、授权范围，衍生 Profile 只在内存中启用 GPU/Inference。下一项是 Owner 的 `/input:ro` + `/output:rw` 实际 HF Job 挂载/回收验证；这是与三模型 Gate PASS 不同的验收，不得混用。

### Owner Mac 下一步：CPU-only HF 输入/输出挂载探针

此探针仅提交 `cpu-basic`，使用**本地专用合成数据目录**，无 GPU、无模型权重/推理。HF CLI 会先将本地目录同步到私有 `jobs-artifacts` 存储，再挂载到 Job；输出回收用 CLI 显示的 `hf buckets sync` 命令，不能假定本地目录立刻自动出现输出。该能力参考 [官方 Jobs Configuration](https://huggingface.co/docs/hub/jobs-configuration)。

```bash
set -euo pipefail
BASE="$HOME/.local/share/storyforge/r60/private/p4-synthetic-30636aa6187b"
RUNID="r60-p4-mount-$(date +%Y%m%d%H%M%S)"
STAGING="$HOME/.local/share/storyforge/r60/private/$RUNID"
mkdir -m 700 "$STAGING"
mkdir -m 700 "$STAGING/input" "$STAGING/output"
cp "$BASE/A/inputs.jsonl" "$BASE/A/manifest.json" "$STAGING/input/"
shasum -a 256 "$STAGING/input/inputs.jsonl"
hf jobs run --namespace adradar --name "$RUNID" \
  --flavor cpu-basic --timeout 5m --attempts 1 \
  -v "$STAGING/input:/input:ro" \
  -v "$STAGING/output:/output:rw" \
  python:3.12 python -c \
  'import hashlib,json,pathlib; p=pathlib.Path("/input/inputs.jsonl"); m=json.loads(pathlib.Path("/input/manifest.json").read_text()); assert hashlib.sha256(p.read_bytes()).hexdigest()==m["sha256"]; o=pathlib.Path("/output/mount-safe.json"); assert not o.exists(); o.write_text(json.dumps({"schema":"storyforge_r60_p4_mount_probe_safe_v1","status":"CPU_MOUNT_RW_PASS","input_sha256":m["sha256"],"gpu_started":False,"inference_started":False,"training_started":False})); print(o.read_text())'
```

Owner 执行后提供 Job ID、状态、stdout SAFE，以及 CLI 打印的**输出同步命令**；按该命令将远端结果读回到独立目录，验证 `mount-safe.json` 的内容后再把状态提升为 `CPU_MOUNT_RW_READBACK_PASS`。如果失败或无法回收，停止后续 H200 Job。这个探针有少量 CPU 计费（`cpu-basic` 参考约 $0.01/hour），但不应据此宣称已验证 GPU 的真实挂载或长期模型输出。

---

## 2026-11-10 synthetic-only Gate 三模型 Owner 实机回执

Owner 已在 Mac 以固定 Frozen SHA 和校准输入完成 CPU-only Gate，**3/3 PASS**：

| Role | Gate SAFE | 绑定输入 SHA-256 | 校准输入 Tokens |
|---|---|---|---:|
| A | `SYNTHETIC_ONLY_GATE_PASS` | `a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398` | 28,568 |
| B | `SYNTHETIC_ONLY_GATE_PASS` | `8cb8ddf2fc511cf957ed03510853dad94b5169334fde8d6ff153afda6640285e` | 28,593 |
| challenger | `SYNTHETIC_ONLY_GATE_PASS` | `2676b44c9e0e6ea1c8ccc1824e246d20c08fd8b7cf789a669e3bd06a1f91c28c` | 28,597 |

三个回执均声明 `gpu_started=false`、`inference_started=false`、`training_authorized=false`；检查仅验证合成输入/授权字段，不能视为 GPU 运行。已验收的执行保护代码见 `src/storyforge_dataset/generation_eval/synthetic_gate.py`，Frozen 原始 JSON 不变。

**剩余门槛：** 必须让 HF Job 的 Worker CLI 实际启用 `--synthetic-authorization`，同时对 /input:ro /output:rw 进行 Owner Mac CLI 挂载及回收确认，且单模型执行代码/预算与 Git SHA 一致。现有通用 `plan.py` 生成的普通命令**不包含 synthetic 参数**，不能直接用于本次合成 GPU。

---

## Owner Mac 实测环境确认（2026-11-10）

Owner 已实际回传以下 CLI 结果：

- `/opt/homebrew/bin/hf`，`hf version = 2.4.0`；
- `hf auth whoami` 登录：`greenkeedle`；组织：`adradar`；
- `hf jobs hardware` 列出 `h200`：1× NVIDIA H200、141 GB GPU 显存、23 vCPU、256 GB RAM、3000 GB Storage、`$0.0833/min` / `$5.00/hour`；
- `hf jobs ps --namespace adradar`：`No running jobs`（未包含已结束/失败历史 Job）；
- Owner 同一轮先前核对：远端分支 `1f98a877039f2a9a52c710f2f396be1bd2c5893f`、Frozen SHA `a58d02c757767f18deb8a4cb948a56be199c837c045d83648838868961e1037f`、`P4_STAGED_AUTHORIZATION_CHECK_PASS`。

**结论**：Mac CLI 与 H200 规格/参考价格已经实际核验，**但 GPU 资源是否能成功分配仍要以真实提交/排队结果为准**。当前没有运行中的 Job，不代表没有历史 Job。下一阻塞点是工程执行包（合成数据及真实 token 校准、synthetic-only 边界、精确可复用提交命令、SAFE 回收），不是 hf CLI 安装或 Profile Freeze。

当前不建议 Owner 手工修改 Frozen 里的授权开关。未完成工程门槛前不提交 32K GPU Job。

---

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

## 2026-11-10 Owner Qwen A 校准回执（新增）

Owner 实际在 Mac Docker/OrbStack 回传以下 SAFE（未提交 HF Job）：

- schema：`storyforge_r60_synthetic_32k_input_safe_v1`
- status：`SYNTHETIC_32K_INPUT_PREPARED__GPU_NOT_STARTED`
- Role A：**28,568 input tokens**，目标 28,600（差 32），上限 28,672；预留 4,096 output tokens；单条合成输入
- `input_sha256=a64ef7434c7f8c62720997b2d2d7d7cfe04545217fee66fc9300978cc42e7398`
- `frozen_profile_sha256=a58d02c757767f18deb8a4cb948a56be199c837c045d83648838868961e1037f`
- `tokenizer_only=true`，`hf_job_submitted=false`、`gpu_started=false`、`inference_started=false`、`training_started=false`、`private_values_emitted=false`

**裁决：模型 A CPU-only 32K 合成输入准备 PASS**。并非 32K GPU / decode / 4,096 token 实测，模型 B 与 challenger 尚未回传校准结果。本次仅证明输入构建及分词长度；正式 synthetic-only GPU 执行隔离尚 HOLD。

后续 Owner 可在原先的**同一个** `WORKTREE` / `OUT` 中执行 B、challenger 输入校准；不得重复 `git worktree add` 或 `mkdir -m 700 "$OUT"`，以免目录已存在报错。

```bash
set -euo pipefail
ROOT="$HOME/workspace/storyforge"
REV="30636aa6187b36809c7ae7a9a72f7a0d95572e01"
WORKTREE="$HOME/workspace/storyforge-p4-synthetic-${REV:0:12}"
OUT="$HOME/.local/share/storyforge/r60/private/p4-synthetic-${REV:0:12}"
IMAGE="docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"

test "$(git -C "$WORKTREE" rev-parse HEAD)" = "$REV"
test -f "$OUT/A/manifest.json"
for ROLE in B challenger; do
  docker run --rm --platform linux/amd64 \
    -v "$WORKTREE:/workspace/storyforge:ro" \
    -v "$OUT:/work" \
    -e PYTHONPATH=/workspace/storyforge/src \
    --entrypoint bash "$IMAGE" -lc "
      set -euo pipefail
      python -m pip install --disable-pip-version-check --require-hashes \
        -r /workspace/storyforge/requirements/hf-generation-eval.lock
      python -m storyforge_dataset.generation_eval.synthetic_32k \
        --frozen /workspace/storyforge/experiments/r60_quality/p4_generation_profile_frozen_v1.json \
        --authorization /workspace/storyforge/experiments/r60_quality/p4_generation_execution_authorization_20261110.json \
        --model-role $ROLE \
        --output-dir /work/$ROLE
    "
done
```

若当前 Mac 的 Worktree/OUT 实际命名与示例不同，以本地已生成 A 的真实目录为准。只回传 B 与 challenger 两份 SAFE，不要上传任何正文。它们只下载 tokenizer/config，无 GPU、无 HF Job。

---

## 3.1 CPU-only 32K 输入 Token 校准（新工具；不提交 HF Job）

工程入口 `python -m storyforge_dataset.generation_eval.synthetic_32k` 已实现，使用冻结 Profile 的三个固定 Revision、tokenizer 文件 SHA 和真实 Chat Template，单模型生成 1 条合成记录，二分校准默认目标 28,600 input tokens（允许误差 96；绝不超过 28,672），保留 4,096 generation 上限。Qwen Thinking flag 与 GLM-Z1 的 generation prefix 一并计数。

工具本身不修改 Frozen、不授予 runtime GPU/inference 开关、不下载模型权重、不发起 HF Job，也不调用 `generate()`。生成文件 `inputs.jsonl` / `manifest.json`，SAFE stdout 不包含文本。仅有 Hugging Face tokenizer/config 公开文件下载，会产生普通网络流量（Mac 本地）。

等本工具的最新 GitHub CI 通过后，在 Mac **只做 A 模型 CPU 校准**。推荐使用既有已验收的 amd64 镜像，通过 Docker/OrbStack 提供与 GPU Worker 相同的版本环境，挂载专门的新输出目录：

```bash
set -euo pipefail
ROOT="/Users/keedle/workspace/storyforge"
BRANCH="r60/p4-generation-eval-framework"
IMAGE="docker.io/pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee"

git -C "$ROOT" fetch origin "$BRANCH"
REV="$(git -C "$ROOT" rev-parse "origin/$BRANCH")"
WORKTREE="$HOME/workspace/storyforge-p4-synthetic-${REV:0:12}"
OUT="$HOME/.local/share/storyforge/r60/private/p4-synthetic-${REV:0:12}"
mkdir -p "$(dirname "$WORKTREE")" "$(dirname "$OUT")"
git -C "$ROOT" worktree add --detach "$WORKTREE" "$REV"
mkdir -m 700 "$OUT"

docker run --rm --platform linux/amd64 \
  -v "$WORKTREE:/workspace/storyforge:ro" \
  -v "$OUT:/work" \
  -e PYTHONPATH=/workspace/storyforge/src \
  -e HF_HUB_DISABLE_TELEMETRY=1 \
  --entrypoint bash "$IMAGE" -lc '
    set -euo pipefail
    python -m pip install --disable-pip-version-check --require-hashes \
      -r /workspace/storyforge/requirements/hf-generation-eval.lock
    python -m storyforge_dataset.generation_eval.synthetic_32k \
      --frozen /workspace/storyforge/experiments/r60_quality/p4_generation_profile_frozen_v1.json \
      --authorization /workspace/storyforge/experiments/r60_quality/p4_generation_execution_authorization_20261110.json \
      --model-role A \
      --output-dir /work/A
  '
```

回传只需终端最后一行 SAFE JSON（应为 `SYNTHETIC_32K_INPUT_PREPARED__GPU_NOT_STARTED`），以及 `REV`。输出 JSONL/Manifest 保存在 Mac 本地 `$OUT/A`；**不要上传合成输入或私有路径到公开日志**。若是 HOLD，保留原报错并停止，不改哈希、模型修订版或预算绕过。若目标目录已存在，该命令为保护数据将停止，不自动覆盖。

**此步骤不是 GPU 任务。** 它只是先取得真实分词长度，并没有完成合成执行器的运行范围隔离和 HF Job 的正式提交前验收。

---

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
